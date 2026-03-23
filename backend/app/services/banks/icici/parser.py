"""
Airco Insights — ICICI Bank Parser (Accuracy-First)
=====================================================
Extracts transactions from ICICI Bank PDF statements with 100% row capture.

ICICI Statement Format:
- Columns: DATE | MODE** | PARTICULARS | DEPOSITS | WITHDRAWALS | BALANCE
- Date format: DD-MM-YYYY
- Opening balance: B/F (Brought Forward) entry
- Amounts in Indian format: 1,06,649.66
- Multi-line narrations (UPI IDs span multiple lines)

Column X-Coordinate Boundaries (from PDF analysis):
  Date:         x0 <  70
  Mode:        70 <= x0 < 130
  Particulars: 130 <= x0 < 380
  Deposits:    380 <= x0 < 435   (Credit)
  Withdrawals: 435 <= x0 < 540   (Debit)
  Balance:     x0 >= 540

Strategy:
1. Coordinate-based column detection (primary)
2. Text-based fallback
3. Balance continuity → debit vs credit determination
"""

import logging
import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


class ICICIParseError(Exception):
    def __init__(self, message: str, error_code: str, details: dict = None):
        self.error_code = error_code
        self.details    = details or {}
        super().__init__(message)


@dataclass
class ICICITransaction:
    """Single ICICI Bank transaction."""
    date: str
    description: str
    debit: Optional[float]
    credit: Optional[float]
    balance: float
    mode: str = ""
    raw_line: str = ""
    line_number: int = 0

    def to_dict(self) -> dict:
        return {
            "date":        self.date,
            "description": self.description,
            "debit":       self.debit,
            "credit":      self.credit,
            "balance":     self.balance,
            "ref_no":      self.mode,
        }


@dataclass
class ICICIParseResult:
    transactions: List[ICICITransaction]
    total_count: int
    parse_method: str
    opening_balance: Optional[float] = None
    closing_balance: Optional[float] = None
    total_credits: float = 0.0
    total_debits: float = 0.0
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "total_count":     self.total_count,
            "parse_method":    self.parse_method,
            "opening_balance": self.opening_balance,
            "closing_balance": self.closing_balance,
            "total_credits":   self.total_credits,
            "total_debits":    self.total_debits,
            "warnings":        self.warnings,
        }


class ICICIParser:
    """
    Accuracy-first ICICI Bank statement parser.
    Uses coordinate-based column detection from pdfplumber word positions.
    """

    # Date pattern: DD-MM-YYYY
    DATE_RE       = re.compile(r'^(\d{2}-\d{2}-\d{4})\s*')
    DATE_EXACT_RE = re.compile(r'^\d{2}-\d{2}-\d{4}$')

    # Amount pattern: Indian format
    AMOUNT_RE = re.compile(r'(\d[\d,]*\.\d{2})')

    # ── Column X-coordinate boundaries (ICICI PDF — standard 595-unit width) ──
    # These are REFERENCE values calibrated for a 595-unit wide PDF.
    # The parser auto-scales them to the actual page width at runtime.
    _COL_DATE_MAX = 70         # Date:         x0 <  70
    _COL_MODE_MAX = 130        # Mode:        70 <= x0 < 130
    _COL_PART_MAX = 380        # Particulars: 130 <= x0 < 380
    _COL_DEP_MAX  = 435        # Deposits:    380 <= x0 < 435  (Credit)
    _COL_WDR_MAX  = 540        # Withdrawals: 435 <= x0 < 540  (Debit)
                                # Balance:     x0 >= 540
    _REFERENCE_WIDTH = 595.0  # Standard A4 portrait width in PDF units

    _DATA_Y_MIN_PAGE1 = 350    # first page: skip account summary section at top
    _DATA_Y_MIN_OTHERS = 120   # other pages: start from near top
    _DATA_Y_MAX = 900          # widened from 820

    SKIP_PATTERNS = [
        "ICICI BANK", "ICICI Bank Limited", "Summary of Accounts",
        "ACCOUNT DETAILS", "ACCOUNT TYPE", "FIXED DEPOSITS",
        "TOTAL BALANCE", "NOMINATION", "Savings A/c",
        "Statement of Transactions", "DATE", "MODE**", "PARTICULARS",
        "DEPOSITS", "WITHDRAWALS", "BALANCE",
        "Page", "Did you know", "KYC", "Visit www.icicibank",
        "Dial your Bank", "This is a computer", "CustID",
        "Customer ID", "Branch", "IFSC",
    ]

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def parse(self, file_path: str, text_content: str = "") -> ICICIParseResult:
        """Parse ICICI Bank statement and extract all transactions."""
        self.logger.info("Parsing ICICI Bank statement: %s", file_path)

        # Detect scanned/image-only PDFs early
        if self._is_image_only_pdf(file_path):
            raise ICICIParseError(
                "This PDF appears to be a scanned image and cannot be processed. "
                "Please upload a text-based PDF downloaded directly from ICICI Bank's internet banking portal.",
                error_code="SCANNED_PDF",
                details={"file": file_path}
            )

        # Check if this is a "Detailed Statement" format (online banking export)
        if not text_content:
            text_content = self._extract_text(file_path)
        
        if "DETAILED STATEMENT" in text_content and "Transaction Remarks" in text_content:
            self.logger.info("Detected ICICI Detailed Statement format")
            try:
                result = self._parse_detailed_statement(file_path, text_content)
                if result.total_count > 0:
                    self.logger.info("Detailed Statement parsing succeeded: %d transactions", result.total_count)
                    return result
            except Exception as e:
                self.logger.warning("Detailed Statement parsing failed: %s", str(e))

        try:
            result = self._parse_with_coordinates(file_path)
            if result.total_count > 0:
                self.logger.info("Coordinate parsing succeeded: %d transactions", result.total_count)
                return result
        except ICICIParseError:
            raise
        except Exception as e:
            self.logger.warning("Coordinate parsing failed: %s — falling back to text", str(e))

        if not text_content:
            text_content = self._extract_text(file_path)

        result = self._parse_with_text(text_content)

        if result.total_count == 0:
            raise ICICIParseError(
                "No transactions extracted from ICICI Bank statement. "
                "Please ensure this is a valid text-based ICICI Bank statement PDF.",
                error_code="NO_TRANSACTIONS",
                details={"file": file_path}
            )

        self.logger.info("Text parsing succeeded: %d transactions", result.total_count)
        return result

    def _is_image_only_pdf(self, file_path: str) -> bool:
        """Return True if the PDF has no extractable text (scanned image)."""
        try:
            import pdfplumber
            with pdfplumber.open(file_path) as pdf:
                pages_to_check = min(3, len(pdf.pages))
                for page in pdf.pages[:pages_to_check]:
                    words = page.extract_words()
                    if words:
                        return False
            return True
        except Exception:
            return False

    def _extract_text(self, file_path: str) -> str:
        try:
            import pdfplumber
            pages = []
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text() or ""
                    pages.append(text)
            return "\n".join(pages)
        except Exception as e:
            raise ICICIParseError(
                f"Failed to extract text from PDF: {str(e)}",
                error_code="TEXT_EXTRACTION_FAILED",
                details={"error": str(e)}
            )

    def _get_scaled_boundaries(self, page_width: float) -> dict:
        """Scale column boundaries proportionally to actual page width."""
        scale = page_width / self._REFERENCE_WIDTH
        return {
            "date_max": self._COL_DATE_MAX * scale,
            "mode_max": self._COL_MODE_MAX * scale,
            "part_max": self._COL_PART_MAX * scale,
            "dep_max":  self._COL_DEP_MAX  * scale,
            "wdr_max":  self._COL_WDR_MAX  * scale,
        }

    def _get_column_dynamic(self, x0: float, bounds: dict) -> str:
        if x0 < bounds["date_max"]: return "date"
        if x0 < bounds["mode_max"]: return "mode"
        if x0 < bounds["part_max"]: return "particulars"
        if x0 < bounds["dep_max"]:  return "deposits"
        if x0 < bounds["wdr_max"]:  return "withdrawals"
        return "balance"

    @staticmethod
    def _get_column(x0: float) -> str:
        if x0 < ICICIParser._COL_DATE_MAX: return "date"
        if x0 < ICICIParser._COL_MODE_MAX: return "mode"
        if x0 < ICICIParser._COL_PART_MAX: return "particulars"
        if x0 < ICICIParser._COL_DEP_MAX:  return "deposits"
        if x0 < ICICIParser._COL_WDR_MAX:  return "withdrawals"
        return "balance"

    def _extract_page_lines(self, page, bounds: dict = None, page_num: int = 1) -> list:
        from collections import defaultdict

        words = page.extract_words(keep_blank_chars=True, x_tolerance=2, y_tolerance=2)
        if not words:
            return []

        use_dynamic = bounds is not None
        y_min = self._DATA_Y_MIN_PAGE1 if page_num == 0 else self._DATA_Y_MIN_OTHERS
        y_groups = defaultdict(list)
        for w in words:
            y_key = round(w["top"] / 5) * 5
            y_groups[y_key].append(w)

        lines = []
        for y_key in sorted(y_groups.keys()):
            if y_key < y_min or y_key > self._DATA_Y_MAX:
                continue

            line_words = sorted(y_groups[y_key], key=lambda w: w["x0"])
            col_words  = defaultdict(list)
            for w in line_words:
                if use_dynamic:
                    col = self._get_column_dynamic(w["x0"], bounds)
                else:
                    col = self._get_column(w["x0"])
                col_words[col].append(w["text"])

            lines.append({
                "y":           y_key,
                "date":        " ".join(col_words.get("date",        [])).strip(),
                "mode":        " ".join(col_words.get("mode",        [])).strip(),
                "particulars": " ".join(col_words.get("particulars", [])).strip(),
                "deposits":    " ".join(col_words.get("deposits",    [])).strip(),
                "withdrawals": " ".join(col_words.get("withdrawals", [])).strip(),
                "balance":     " ".join(col_words.get("balance",     [])).strip(),
            })

        return lines

    def _parse_with_coordinates(self, file_path: str) -> ICICIParseResult:
        """
        Parse ICICI Bank PDF using coordinate-based column detection.

        ICICI-specific handling:
        - B/F entry = opening balance (no date in some pages, balance only)
        - Each transaction line has a date + particulars that can span multiple rows
        - Deposits = Credit, Withdrawals = Debit
        - Long UPI/NEFT narrations continue on next lines (particulars column only)
        """
        import pdfplumber

        transactions  = []
        prev_balance  = None
        opening_balance = None

        with pdfplumber.open(file_path) as pdf:
            first_page = pdf.pages[0] if pdf.pages else None
            page_width = float(first_page.width) if first_page else self._REFERENCE_WIDTH
            bounds = self._get_scaled_boundaries(page_width)
            self.logger.info("ICICI PDF width=%.1f, scale=%.3f", page_width, page_width / self._REFERENCE_WIDTH)

            for page_num, page in enumerate(pdf.pages):
                lines = self._extract_page_lines(page, bounds, page_num=page_num)

                for line in lines:
                    date_text    = line["date"].strip()
                    balance_text = line["balance"].strip()
                    particulars  = line["particulars"].strip()
                    mode_text    = line["mode"].strip()

                    # Detect B/F (Brought Forward = opening balance)
                    if "B/F" in particulars.upper() or "B/F" in mode_text.upper():
                        bal = self._clean_amount(balance_text)
                        if bal is not None:
                            opening_balance = bal
                            prev_balance    = bal
                        continue

                    # Skip header/footer lines
                    if self._should_skip_line(particulars) or self._should_skip_line(date_text):
                        continue

                    is_date   = bool(self.DATE_EXACT_RE.match(date_text))
                    balance_val = self._clean_amount(balance_text)

                    if is_date and balance_val is not None:
                        dep_val = self._clean_amount(line["deposits"])
                        wdr_val = self._clean_amount(line["withdrawals"])

                        # Determine debit/credit from balance movement
                        if prev_balance is not None:
                            balance_change = balance_val - prev_balance
                            if balance_change < -0.005:
                                if not wdr_val:
                                    wdr_val = round(abs(balance_change), 2)
                                dep_val = None
                            elif balance_change > 0.005:
                                if not dep_val:
                                    dep_val = round(balance_change, 2)
                                wdr_val = None
                            else:
                                dep_val = None
                                wdr_val = None
                        else:
                            if dep_val and not wdr_val:
                                pass
                            elif wdr_val and not dep_val:
                                pass
                            elif dep_val and wdr_val:
                                dep_val = dep_val
                                wdr_val = None

                        txn = ICICITransaction(
                            date=date_text,
                            description=particulars,
                            debit=wdr_val,
                            credit=dep_val,
                            balance=balance_val,
                            mode=mode_text,
                        )
                        transactions.append(txn)
                        prev_balance = balance_val

                    elif transactions and particulars:
                        # Continuation line — append to previous transaction narration
                        transactions[-1].description += " " + particulars

        # Normalize whitespace and clean long UPI IDs from descriptions
        for txn in transactions:
            txn.description = self._clean_description(txn.description)

        self.logger.info("Coordinate parsing: %d transactions", len(transactions))

        total_credits = sum(t.credit or 0 for t in transactions)
        total_debits  = sum(t.debit  or 0 for t in transactions)
        closing       = transactions[-1].balance if transactions else None

        if opening_balance is None and transactions:
            first = transactions[0]
            if first.credit:
                opening_balance = first.balance - first.credit
            elif first.debit:
                opening_balance = first.balance + first.debit

        return ICICIParseResult(
            transactions=transactions,
            total_count=len(transactions),
            parse_method="coordinate",
            opening_balance=opening_balance,
            closing_balance=closing,
            total_credits=total_credits,
            total_debits=total_debits,
        )

    def _parse_detailed_statement(self, file_path: str, text_content: str) -> ICICIParseResult:
        """
        Parse ICICI Detailed Statement format (online banking export).
        Format: S No. | Value Date | Transaction Date | Cheque Number | Transaction Remarks | Withdrawal Amount | Deposit Amount | Balance (INR)
        Handles both date formats: DD-MMM-YY (11-Mar-22) and DD/MM/YYYY (10/09/2021)
        """
        import pdfplumber
        
        transactions = []
        opening_balance = None
        
        # Date patterns for both formats
        date_pattern_dmy = re.compile(r'\d{2}-[A-Z][a-z]{2}-\d{2,4}')  # DD-MMM-YY or DD-MMM-YYYY
        date_pattern_slash = re.compile(r'\d{2}/\d{2}/\d{4}')  # DD/MM/YYYY
        
        with pdfplumber.open(file_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                text = page.extract_text() or ""
                lines = text.split('\n')
                
                i = 0
                while i < len(lines):
                    line = lines[i].strip()
                    
                    # Skip headers and metadata
                    if any(skip in line for skip in ["DETAILED STATEMENT", "Account Number", "Transaction Date from",
                                                     "Transaction Period", "Advanced Search", "Amount from",
                                                     "Cheque number from", "Transaction remarks", "Transaction type",
                                                     "Transactions List", "S No.", "Value Date", "Transaction Date",
                                                     "Cheque Number", "Transaction Remarks", "Withdrawal Amount",
                                                     "Deposit Amount", "Balance", "(INR )"]):
                        i += 1
                        continue
                    
                    # Look for transaction lines with dates (both formats)
                    dates_dmy = date_pattern_dmy.findall(line)
                    dates_slash = date_pattern_slash.findall(line)
                    dates = dates_dmy if dates_dmy else dates_slash
                    
                    if dates and len(dates) >= 2:  # Value Date and Transaction Date
                        # Extract transaction info
                        parts = line.split()
                        
                        # Try to find amounts and balance
                        amounts = []
                        for part in parts:
                            cleaned = part.replace(',', '')
                            try:
                                val = float(cleaned)
                                amounts.append(val)
                            except:
                                pass
                        
                        if len(amounts) >= 2:  # At least withdrawal/deposit and balance
                            # Find transaction date (second date in line)
                            txn_date = dates[1] if len(dates) >= 2 else dates[0]
                            
                            # Get description (between second date and first amount)
                            desc_start = line.find(txn_date) + len(txn_date)
                            first_amount_idx = -1
                            for amt in amounts:
                                amt_str = f"{amt:.1f}"
                                idx = line.find(amt_str, desc_start)
                                if idx > 0:
                                    first_amount_idx = idx
                                    break
                            
                            if first_amount_idx > 0:
                                description = line[desc_start:first_amount_idx].strip()
                                # Remove leading dash and cheque number placeholder
                                description = description.lstrip('- ')
                            else:
                                description = line[desc_start:].strip()
                            
                            # Collect continuation lines
                            j = i + 1
                            while j < len(lines):
                                next_line = lines[j].strip()
                                if not next_line:
                                    j += 1
                                    continue
                                # Stop if we hit another transaction (has dates)
                                if date_pattern_dmy.search(next_line) or date_pattern_slash.search(next_line):
                                    break
                                # Check if it's a continuation (no amounts, or very small number like serial number)
                                has_decimal = '.' in next_line and any(c.isdigit() for c in next_line)
                                # If line has numbers with decimals, it might be amounts - skip
                                if has_decimal:
                                    # Check if these are actual transaction amounts (> 0.1)
                                    try:
                                        nums = [float(p.replace(',','')) for p in next_line.split() if p.replace(',','').replace('.','').isdigit()]
                                        if any(n > 0.1 for n in nums):
                                            break
                                    except:
                                        pass
                                description += " " + next_line
                                j += 1
                            
                            i = j - 1
                            
                            # Parse amounts: last is balance, before that is deposit or withdrawal
                            balance = amounts[-1]
                            withdrawal = None
                            deposit = None
                            
                            if len(amounts) == 3:
                                # Format: Withdrawal | Deposit | Balance
                                # Only ONE of withdrawal or deposit should be non-zero
                                wdr_amt = amounts[0]
                                dep_amt = amounts[1]
                                
                                if wdr_amt > 0.01 and dep_amt < 0.01:
                                    withdrawal = wdr_amt
                                elif dep_amt > 0.01 and wdr_amt < 0.01:
                                    deposit = dep_amt
                                elif wdr_amt > 0.01 and dep_amt > 0.01:
                                    # Both non-zero - determine from balance change
                                    if transactions:
                                        prev_bal = transactions[-1].balance
                                        change = balance - prev_bal
                                        if abs(change + wdr_amt) < 0.01:
                                            withdrawal = wdr_amt
                                        elif abs(change - dep_amt) < 0.01:
                                            deposit = dep_amt
                                        else:
                                            # Default: use the one that matches balance change better
                                            if change < 0:
                                                withdrawal = wdr_amt
                                            else:
                                                deposit = dep_amt
                                    else:
                                        deposit = dep_amt
                            elif len(amounts) == 2:
                                # One amount + balance
                                # Determine if it's withdrawal or deposit from balance change
                                if transactions:
                                    prev_bal = transactions[-1].balance
                                    change = balance - prev_bal
                                    if change < -0.01:
                                        withdrawal = amounts[0]
                                    elif change > 0.01:
                                        deposit = amounts[0]
                                else:
                                    # First transaction, assume deposit if positive
                                    deposit = amounts[0] if amounts[0] > 0 else None
                            
                            # Normalize date to DD-MM-YYYY
                            normalized_date = self._normalize_date(txn_date)
                            
                            txn = ICICITransaction(
                                date=normalized_date,
                                description=description,
                                debit=withdrawal,
                                credit=deposit,
                                balance=balance,
                            )
                            transactions.append(txn)
                            
                            # Set opening balance from first transaction
                            if opening_balance is None and len(transactions) == 1:
                                if deposit:
                                    opening_balance = balance - deposit
                                elif withdrawal:
                                    opening_balance = balance + withdrawal
                                else:
                                    opening_balance = balance
                    
                    i += 1
        
        self.logger.info("Detailed Statement parsing: %d transactions", len(transactions))
        
        total_credits = sum(t.credit or 0 for t in transactions)
        total_debits = sum(t.debit or 0 for t in transactions)
        closing = transactions[-1].balance if transactions else None
        
        return ICICIParseResult(
            transactions=transactions,
            total_count=len(transactions),
            parse_method="detailed_statement",
            opening_balance=opening_balance,
            closing_balance=closing,
            total_credits=total_credits,
            total_debits=total_debits,
        )
    
    def _normalize_date(self, date_str: str) -> str:
        """Convert DD-MMM-YY, DD-MMM-YYYY, or DD/MM/YYYY to DD-MM-YYYY."""
        try:
            # Parse formats like 11-Mar-22, 11-Mar-2022, or 10/09/2021
            for fmt in ["%d-%b-%y", "%d-%b-%Y", "%d/%m/%Y"]:
                try:
                    dt = datetime.strptime(date_str, fmt)
                    return dt.strftime("%d-%m-%Y")
                except:
                    continue
            return date_str
        except:
            return date_str
    
    def _parse_with_text(self, text_content: str) -> ICICIParseResult:
        """Text-based fallback parser for ICICI Bank statements."""
        lines           = text_content.split("\n")
        raw_entries     = []
        current_entry   = None
        opening_balance = None

        for line_num, line in enumerate(lines):
            stripped = line.strip()
            if not stripped:
                continue

            # B/F = opening balance
            if "B/F" in stripped.upper():
                amounts = self._extract_amounts(stripped)
                if amounts:
                    opening_balance = amounts[-1]
                continue

            if self._should_skip_line(stripped):
                continue

            date_match = self.DATE_RE.match(stripped)
            if date_match:
                date_str = date_match.group(1)
                rest     = stripped[date_match.end():].strip()
                amounts  = self._extract_amounts(rest)

                if amounts:
                    if current_entry:
                        raw_entries.append(current_entry)

                    amount_positions = list(self.AMOUNT_RE.finditer(rest))
                    narration_part   = rest[:amount_positions[0].start()].strip() if amount_positions else rest

                    current_entry = {
                        "date":           date_str,
                        "narration_parts": [narration_part] if narration_part else [],
                        "amounts":        amounts,
                        "line_number":    line_num,
                    }
                else:
                    if current_entry:
                        raw_entries.append(current_entry)
                    current_entry = {
                        "date":           date_str,
                        "narration_parts": [rest] if rest else [],
                        "amounts":        [],
                        "line_number":    line_num,
                    }
            else:
                if current_entry:
                    amounts = self._extract_amounts(stripped)
                    if amounts and not current_entry["amounts"]:
                        amount_positions = list(self.AMOUNT_RE.finditer(stripped))
                        if amount_positions:
                            narration_part = stripped[:amount_positions[0].start()].strip()
                            if narration_part:
                                current_entry["narration_parts"].append(narration_part)
                        current_entry["amounts"] = amounts
                    else:
                        current_entry["narration_parts"].append(stripped)

        if current_entry:
            raw_entries.append(current_entry)

        transactions = []
        prev_balance = None

        for entry in raw_entries:
            amounts = entry["amounts"]
            if not amounts:
                continue

            balance  = amounts[-1]
            narration = " ".join(entry["narration_parts"]).strip()
            narration = self._clean_description(narration)

            debit  = None
            credit = None

            if prev_balance is not None:
                if balance > prev_balance:
                    credit = round(balance - prev_balance, 2)
                elif balance < prev_balance:
                    debit = round(prev_balance - balance, 2)
            else:
                if len(amounts) >= 2:
                    txn_amount = amounts[-2]
                    narration_upper = narration.upper()
                    if any(kw in narration_upper for kw in ["CREDIT", "SALARY", "NEFT CR", "UPI"]):
                        credit = txn_amount
                    else:
                        debit = txn_amount

            prev_balance = balance

            transactions.append(ICICITransaction(
                date=entry["date"],
                description=narration,
                debit=debit,
                credit=credit,
                balance=balance,
                line_number=entry.get("line_number", 0),
            ))

        total_credits = sum(t.credit or 0 for t in transactions)
        total_debits  = sum(t.debit  or 0 for t in transactions)
        closing       = transactions[-1].balance if transactions else None

        return ICICIParseResult(
            transactions=transactions,
            total_count=len(transactions),
            parse_method="text",
            opening_balance=opening_balance,
            closing_balance=closing,
            total_credits=total_credits,
            total_debits=total_debits,
        )

    def _should_skip_line(self, line: str) -> bool:
        upper = line.upper()
        for pattern in self.SKIP_PATTERNS:
            if pattern.upper() in upper:
                return True
        return False

    def _clean_description(self, desc: str) -> str:
        """
        Clean ICICI narration:
        - Collapse whitespace
        - Remove pure hex transaction IDs (IBL...) at end
        """
        desc = " ".join(desc.split())
        # Remove trailing ICICI transaction ID (IBL + 32 hex chars)
        desc = re.sub(r'\s*IBL[0-9a-f]{20,}\s*$', '', desc, flags=re.IGNORECASE)
        return desc.strip()

    def _extract_amounts(self, text: str) -> List[float]:
        matches = self.AMOUNT_RE.findall(text)
        amounts = []
        for m in matches:
            val = self._clean_amount(m)
            if val is not None:
                amounts.append(val)
        return amounts

    def _clean_amount(self, val: str) -> Optional[float]:
        if not val or not val.strip():
            return None
        cleaned = val.strip().replace(",", "").replace(" ", "")
        try:
            result = float(cleaned)
            return result if result >= 0 else None
        except (ValueError, TypeError):
            return None
