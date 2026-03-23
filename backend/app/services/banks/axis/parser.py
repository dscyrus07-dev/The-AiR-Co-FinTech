"""
Airco Insights — Axis Bank Parser (Accuracy-First)
====================================================
Extracts transactions from Axis Bank PDF statements with 100% row capture.

Axis Statement Format:
- Columns: Tran Date | Chq No | Particulars | Debit | Credit | Balance | Init.Br
- Date format: DD-MM-YYYY
- Amounts in Indian format: 1,03,766.81
- Multi-line narrations wrapped across lines
- Opening Balance shown as separate row

Column X-Coordinate Boundaries (from PDF analysis):
  Date:         x0 <  90
  Chq No:      90 <= x0 < 132
  Particulars: 132 <= x0 < 340
  Debit:       340 <= x0 < 400
  Credit:      400 <= x0 < 460
  Balance:     460 <= x0 < 535
  Init/Br:     x0 >= 535

Strategy:
1. Coordinate-based column detection (primary)
2. Text-based fallback
3. Balance continuity → debit vs credit determination
4. 100% extraction or fail
"""

import logging
import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


class AxisParseError(Exception):
    """Raised when Axis Bank parsing fails."""
    def __init__(self, message: str, error_code: str, details: dict = None):
        self.error_code = error_code
        self.details = details or {}
        super().__init__(message)


@dataclass
class AxisTransaction:
    """Single Axis Bank transaction."""
    date: str
    description: str
    debit: Optional[float]
    credit: Optional[float]
    balance: float
    chq_no: str = ""
    raw_line: str = ""
    line_number: int = 0

    def to_dict(self) -> dict:
        return {
            "date": self.date,
            "description": self.description,
            "debit": self.debit,
            "credit": self.credit,
            "balance": self.balance,
            "ref_no": self.chq_no,
        }


@dataclass
class AxisParseResult:
    """Result of Axis Bank parsing."""
    transactions: List[AxisTransaction]
    total_count: int
    parse_method: str
    opening_balance: Optional[float] = None
    closing_balance: Optional[float] = None
    total_credits: float = 0.0
    total_debits: float = 0.0
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "total_count": self.total_count,
            "parse_method": self.parse_method,
            "opening_balance": self.opening_balance,
            "closing_balance": self.closing_balance,
            "total_credits": self.total_credits,
            "total_debits": self.total_debits,
            "warnings": self.warnings,
        }


class AxisParser:
    """
    Accuracy-first Axis Bank statement parser.
    Uses coordinate-based column detection from pdfplumber word positions.
    """

    # Date pattern: DD-MM-YYYY
    DATE_RE = re.compile(r'^(\d{2}-\d{2}-\d{4})\s*')
    DATE_EXACT_RE = re.compile(r'^\d{2}-\d{2}-\d{4}$')

    # Amount pattern: Indian format
    AMOUNT_RE = re.compile(r'(\d[\d,]*\.\d{2})')

    # ── Column X-coordinate boundaries (Axis PDF — standard 595-unit width) ────
    # NOTE: Axis debit amounts are right-justified in the debit column; small
    # amounts (e.g. '   30.00') start at x0≈323 due to leading whitespace
    # captured by pdfplumber. Setting _COL_PART_MAX=318 ensures these land
    # in the debit bucket rather than the particulars bucket.
    # These are REFERENCE values for a 595-unit wide PDF.
    # The parser auto-scales them to the actual page width.
    _COL_DATE_MAX   = 90      # Date column:    x0 < 90
    _COL_CHQ_MAX    = 132     # Chq No:        90 <= x0 < 132
    _COL_PART_MAX   = 318     # Particulars:  132 <= x0 < 318
    _COL_DEBIT_MAX  = 400     # Debit:        318 <= x0 < 400
    _COL_CREDIT_MAX = 460     # Credit:       400 <= x0 < 460
    _COL_BAL_MAX    = 535     # Balance:      460 <= x0 < 535
                               # Init/Br:      x0 >= 535
    _REFERENCE_WIDTH = 595.0  # Standard A4 portrait width in PDF units

    # Skip page-header/footer y-zones
    _DATA_Y_MIN = 100          # widened from 200 to catch statements with header at lower y
    _DATA_Y_MAX = 900          # widened from 820
    # Y-bucket size: 8 units merges values 5px apart (opening balance text
    # at y=275 and its balance number at y=270 land in the same bucket)
    _Y_BUCKET = 8

    # Patterns to skip
    SKIP_PATTERNS = [
        "AXIS BANK", "Axis Bank Limited", "Account No", "Customer ID",
        "IFSC Code", "MICR Code", "Nominee Registered", "Registered Mobile",
        "Registered Email", "Scheme", "Statement of Axis", "Statement of Account",
        "Tran Date", "Chq No", "Particulars", "Debit", "Credit", "Balance", "Init.",
        "OPENING BALANCE", "CLOSING BALANCE",
        "This is a computer", "does not require signature",
        "Generated On", "Page", "Continued on", "Branch",
    ]

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def parse(self, file_path: str, text_content: str = "") -> AxisParseResult:
        """Parse Axis Bank statement and extract all transactions."""
        self.logger.info("Parsing Axis Bank statement: %s", file_path)

        # Detect scanned/image-only PDFs early
        if self._is_image_only_pdf(file_path):
            raise AxisParseError(
                "This PDF appears to be a scanned image and cannot be processed. "
                "Please upload a text-based PDF downloaded directly from Axis Bank's internet banking portal.",
                error_code="SCANNED_PDF",
                details={"file": file_path}
            )

        try:
            result = self._parse_with_coordinates(file_path)
            if result.total_count > 0:
                self.logger.info("Coordinate parsing succeeded: %d transactions", result.total_count)
                return result
        except AxisParseError:
            raise
        except Exception as e:
            self.logger.warning("Coordinate parsing failed: %s, falling back to text", str(e))

        if not text_content:
            text_content = self._extract_text(file_path)

        result = self._parse_with_text(text_content)

        if result.total_count == 0:
            raise AxisParseError(
                "No transactions extracted from Axis Bank statement. "
                "Please ensure this is a valid text-based Axis Bank statement PDF.",
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
        """Extract text from PDF using pdfplumber."""
        try:
            import pdfplumber
            pages = []
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text() or ""
                    pages.append(text)
            return "\n".join(pages)
        except Exception as e:
            raise AxisParseError(
                f"Failed to extract text from PDF: {str(e)}",
                error_code="TEXT_EXTRACTION_FAILED",
                details={"error": str(e)}
            )

    def _get_scaled_boundaries(self, page_width: float) -> dict:
        """Scale column boundaries proportionally to actual page width."""
        scale = page_width / self._REFERENCE_WIDTH
        return {
            "date_max":   self._COL_DATE_MAX   * scale,
            "chq_max":    self._COL_CHQ_MAX    * scale,
            "part_max":   self._COL_PART_MAX   * scale,
            "debit_max":  self._COL_DEBIT_MAX  * scale,
            "credit_max": self._COL_CREDIT_MAX * scale,
            "bal_max":    self._COL_BAL_MAX    * scale,
        }

    def _get_column_dynamic(self, x0: float, bounds: dict) -> str:
        """Assign a word to its column based on dynamically scaled x-coordinate."""
        if x0 < bounds["date_max"]:   return "date"
        if x0 < bounds["chq_max"]:    return "chq_no"
        if x0 < bounds["part_max"]:   return "particulars"
        if x0 < bounds["debit_max"]:  return "debit"
        if x0 < bounds["credit_max"]: return "credit"
        if x0 < bounds["bal_max"]:    return "balance"
        return "init_br"

    @staticmethod
    def _get_column(x0: float) -> str:
        """Assign a word to its column based on x-coordinate (legacy static)."""
        if x0 < AxisParser._COL_DATE_MAX:    return "date"
        if x0 < AxisParser._COL_CHQ_MAX:    return "chq_no"
        if x0 < AxisParser._COL_PART_MAX:   return "particulars"
        if x0 < AxisParser._COL_DEBIT_MAX:  return "debit"
        if x0 < AxisParser._COL_CREDIT_MAX: return "credit"
        if x0 < AxisParser._COL_BAL_MAX:    return "balance"
        return "init_br"

    def _extract_page_lines(self, page, bounds: dict = None) -> list:
        """Extract words from a PDF page, group by y into lines, assign to columns."""
        from collections import defaultdict

        words = page.extract_words(keep_blank_chars=True, x_tolerance=2, y_tolerance=2)
        if not words:
            return []

        # Use dynamic bounds if provided, else fall back to static
        use_dynamic = bounds is not None

        y_groups = defaultdict(list)
        for w in words:
            y_key = round(w["top"] / self._Y_BUCKET) * self._Y_BUCKET
            y_groups[y_key].append(w)

        lines = []
        for y_key in sorted(y_groups.keys()):
            if y_key < self._DATA_Y_MIN or y_key > self._DATA_Y_MAX:
                continue

            line_words = sorted(y_groups[y_key], key=lambda w: w["x0"])

            col_words = defaultdict(list)
            for w in line_words:
                if use_dynamic:
                    col = self._get_column_dynamic(w["x0"], bounds)
                else:
                    col = self._get_column(w["x0"])
                col_words[col].append(w["text"])

            lines.append({
                "y": y_key,
                "date": " ".join(col_words.get("date", [])).strip(),
                "chq_no": " ".join(col_words.get("chq_no", [])).strip(),
                "particulars": " ".join(col_words.get("particulars", [])).strip(),
                "debit": " ".join(col_words.get("debit", [])).strip(),
                "credit": " ".join(col_words.get("credit", [])).strip(),
                "balance": " ".join(col_words.get("balance", [])).strip(),
            })

        return lines

    def _parse_with_coordinates(self, file_path: str) -> AxisParseResult:
        """
        Parse Axis Bank PDF using coordinate-based column detection.

        STRATEGY:
        1. Extract words with x,y positions from each page
        2. Group by y-position into visual lines
        3. Assign words to columns by x-coordinate boundaries
        4. Transaction start = valid DD-MM-YYYY in Date col + valid Balance
        5. Continuation = particulars content without date → append to previous txn
        6. Balance continuity determines withdrawal vs deposit
        """
        import pdfplumber

        transactions = []
        prev_balance = None
        opening_balance = None

        with pdfplumber.open(file_path) as pdf:
            # Determine page width from first page and scale column boundaries
            first_page = pdf.pages[0] if pdf.pages else None
            page_width = float(first_page.width) if first_page else self._REFERENCE_WIDTH
            bounds = self._get_scaled_boundaries(page_width)
            self.logger.info("Axis PDF width=%.1f, scale=%.3f", page_width, page_width / self._REFERENCE_WIDTH)

            for page_num, page in enumerate(pdf.pages):
                lines = self._extract_page_lines(page, bounds)

                for line in lines:
                    date_text = line["date"].strip()
                    balance_text = line["balance"].strip()
                    particulars = line["particulars"].strip()

                    # Check for OPENING BALANCE line
                    if "OPENING" in particulars.upper() or "OPENING" in date_text.upper():
                        bal = self._clean_amount(balance_text)
                        if bal is not None:
                            opening_balance = bal
                            prev_balance = bal
                        continue

                    # Check if this is a transaction start line
                    is_date = bool(self.DATE_EXACT_RE.match(date_text))
                    balance_val = self._clean_amount(balance_text) if balance_text else None

                    if is_date and balance_val is not None:
                        debit_val = self._clean_amount(line["debit"])
                        credit_val = self._clean_amount(line["credit"])

                        # Determine debit/credit from balance movement
                        if prev_balance is not None:
                            balance_change = balance_val - prev_balance
                            if balance_change < -0.005:
                                if not debit_val:
                                    debit_val = round(abs(balance_change), 2)
                                credit_val = None
                            elif balance_change > 0.005:
                                if not credit_val:
                                    credit_val = round(balance_change, 2)
                                debit_val = None
                            else:
                                debit_val = None
                                credit_val = None
                        else:
                            if credit_val and not debit_val:
                                pass
                            elif debit_val and not credit_val:
                                pass
                            elif credit_val and debit_val:
                                credit_val = credit_val
                                debit_val = None

                        txn = AxisTransaction(
                            date=date_text,
                            description=particulars,
                            debit=debit_val,
                            credit=credit_val,
                            balance=balance_val,
                            chq_no=line["chq_no"],
                        )
                        transactions.append(txn)
                        prev_balance = balance_val

                    elif transactions and particulars:
                        # Continuation line — append to previous transaction
                        transactions[-1].description += " " + particulars
                        if line["chq_no"] and not transactions[-1].chq_no:
                            transactions[-1].chq_no = line["chq_no"]

        # Normalize whitespace
        for txn in transactions:
            txn.description = " ".join(txn.description.split())

        self.logger.info("Coordinate parsing: %d transactions", len(transactions))

        total_credits = sum(t.credit or 0 for t in transactions)
        total_debits = sum(t.debit or 0 for t in transactions)
        closing = transactions[-1].balance if transactions else None

        if opening_balance is None and transactions:
            first = transactions[0]
            if first.credit:
                opening_balance = first.balance - first.credit
            elif first.debit:
                opening_balance = first.balance + first.debit

        return AxisParseResult(
            transactions=transactions,
            total_count=len(transactions),
            parse_method="coordinate",
            opening_balance=opening_balance,
            closing_balance=closing,
            total_credits=total_credits,
            total_debits=total_debits,
        )

    def _parse_with_text(self, text_content: str) -> AxisParseResult:
        """Text-based fallback parser for Axis Bank statements."""
        lines = text_content.split("\n")
        raw_entries = []
        current_entry = None
        opening_balance = None

        for line_num, line in enumerate(lines):
            stripped = line.strip()
            if not stripped:
                continue

            if self._should_skip_line(stripped):
                # Check for opening balance
                if "OPENING BALANCE" in stripped.upper():
                    amounts = self._extract_amounts(stripped)
                    if amounts:
                        opening_balance = amounts[-1]
                continue

            date_match = self.DATE_RE.match(stripped)
            if date_match:
                date_str = date_match.group(1)
                rest = stripped[date_match.end():].strip()
                amounts = self._extract_amounts(rest)

                if len(amounts) >= 1:
                    if current_entry:
                        raw_entries.append(current_entry)

                    amount_positions = list(self.AMOUNT_RE.finditer(rest))
                    narration_part = rest[:amount_positions[0].start()].strip() if amount_positions else rest

                    current_entry = {
                        "date": date_str,
                        "narration_parts": [narration_part] if narration_part else [],
                        "amounts": amounts,
                        "line_number": line_num,
                    }
                else:
                    if current_entry:
                        raw_entries.append(current_entry)
                    current_entry = {
                        "date": date_str,
                        "narration_parts": [rest] if rest else [],
                        "amounts": [],
                        "line_number": line_num,
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

        # Convert to transactions
        transactions = []
        prev_balance = None

        for entry in raw_entries:
            amounts = entry["amounts"]
            if not amounts:
                continue

            balance = amounts[-1]
            narration = " ".join(entry["narration_parts"]).strip()

            debit = None
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
                    if any(kw in narration_upper for kw in ["IMPS/P2A", "CREDIT", "SALARY"]):
                        credit = txn_amount
                    else:
                        debit = txn_amount

            prev_balance = balance

            transactions.append(AxisTransaction(
                date=entry["date"],
                description=narration,
                debit=debit,
                credit=credit,
                balance=balance,
                line_number=entry.get("line_number", 0),
            ))

        total_credits = sum(t.credit or 0 for t in transactions)
        total_debits = sum(t.debit or 0 for t in transactions)
        closing = transactions[-1].balance if transactions else None

        return AxisParseResult(
            transactions=transactions,
            total_count=len(transactions),
            parse_method="text",
            opening_balance=opening_balance,
            closing_balance=closing,
            total_credits=total_credits,
            total_debits=total_debits,
        )

    def _should_skip_line(self, line: str) -> bool:
        """Check if line is header/footer/metadata."""
        upper = line.upper()
        for pattern in self.SKIP_PATTERNS:
            if pattern.upper() in upper:
                return True
        return False

    def _extract_amounts(self, text: str) -> List[float]:
        """Extract all Indian-format amounts from text."""
        matches = self.AMOUNT_RE.findall(text)
        amounts = []
        for m in matches:
            val = self._clean_amount(m)
            if val is not None:
                amounts.append(val)
        return amounts

    def _clean_amount(self, val: str) -> Optional[float]:
        """Convert Indian-format amount string to float."""
        if not val or not val.strip():
            return None
        cleaned = val.strip().replace(",", "").replace(" ", "")
        try:
            result = float(cleaned)
            return result if result >= 0 else None
        except (ValueError, TypeError):
            return None
