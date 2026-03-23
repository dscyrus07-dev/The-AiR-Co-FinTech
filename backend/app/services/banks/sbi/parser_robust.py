"""
Robust SBI Bank Statement Parser
================================
Enhanced parser that handles multiple SBI PDF formats.
"""

import logging
import re
from datetime import datetime
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

import pdfplumber

logger = logging.getLogger(__name__)


@dataclass
class SBITransaction:
    """Represents a single SBI transaction."""
    date: str  # DD-MM-YYYY format
    description: str
    ref_no: str
    debit: Optional[float]
    credit: Optional[float]
    balance: float

    def to_dict(self):
        return {
            "date": self.date,
            "description": self.description,
            "ref_no": self.ref_no,
            "debit": self.debit,
            "credit": self.credit,
            "balance": self.balance,
        }


@dataclass
class SBIParseResult:
    """Result of parsing an SBI statement."""
    transactions: List[SBITransaction]
    total_count: int
    parse_method: str
    opening_balance: Optional[float] = None
    closing_balance: Optional[float] = None
    total_credits: float = 0.0
    total_debits: float = 0.0


class SBIParseError(Exception):
    """Custom exception for SBI parsing errors."""
    def __init__(self, message: str, error_code: str = "UNKNOWN", details: dict = None):
        self.error_code = error_code
        self.details = details or {}
        super().__init__(message)


class SBIParser:
    """
    Robust SBI Bank statement parser with multiple format support.
    """

    # Column boundaries (based on actual PDF analysis)
    _REFERENCE_WIDTH = 595.0
    _COL_TXN_DATE_MAX = 90       # Txn Date column
    _COL_VALUE_DATE_MAX = 143    # Value Date column
    _COL_DESC_MAX = 222          # Description column
    _COL_REF_MAX = 302           # Ref No./Cheque No. column
    _COL_BRANCH_MAX = 384         # Branch Code column
    _COL_DEBIT_MAX = 443          # Debit column
    _COL_CREDIT_MAX = 511         # Credit column
    # Balance is everything after CREDIT

    # Y-axis filtering (adjusted based on analysis)
    _DATA_Y_MIN_PAGE1 = 300      # First page starts after headers
    _DATA_Y_MIN_OTHERS = 70      # Other pages start higher
    _DATA_Y_MAX = 800            # Maximum Y coordinate for data

    # Date bucketing tolerance
    _Y_BUCKET = 6

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def parse(self, file_path: str, text_content: str = "") -> SBIParseResult:
        """Parse SBI statement PDF."""
        self.logger.info("Parsing SBI Bank statement: %s", file_path)

        # Check for scanned PDFs
        if self._is_image_only_pdf(file_path):
            raise SBIParseError(
                "This PDF appears to be a scanned image and cannot be processed. "
                "Please upload a text-based PDF downloaded directly from SBI's internet banking portal.",
                error_code="SCANNED_PDF",
                details={"file": file_path}
            )

        # Try coordinate-based parsing first
        try:
            result = self._parse_with_coordinates(file_path)
            if result.total_count > 0:
                self.logger.info("Coordinate parsing succeeded: %d transactions", result.total_count)
                return result
        except SBIParseError:
            raise
        except Exception as e:
            self.logger.warning("Coordinate parsing failed: %s", str(e))

        # Try text-based parsing as fallback
        try:
            result = self._parse_with_text_extraction(file_path)
            if result.total_count > 0:
                self.logger.info("Text parsing succeeded: %d transactions", result.total_count)
                return result
        except Exception as e:
            self.logger.warning("Text parsing failed: %s", str(e))

        # If we get here, no transactions found
        raise SBIParseError(
            "Could not extract transactions from this PDF. Please ensure it is a valid SBI statement.",
            error_code="NO_TRANSACTIONS",
            details={"file": file_path}
        )

    def _is_image_only_pdf(self, file_path: str) -> bool:
        """Check if PDF is scanned/image-only."""
        try:
            with pdfplumber.open(file_path) as pdf:
                for page_num in range(min(3, len(pdf.pages))):
                    words = pdf.pages[page_num].extract_words()
                    if words and len(words) > 10:
                        return False
                return True
        except Exception as e:
            self.logger.warning("Error checking PDF type: %s", str(e))
            return False

    def _get_scaled_boundaries(self, page_width: float) -> dict:
        """Scale column boundaries based on actual page width."""
        scale = page_width / self._REFERENCE_WIDTH
        return {
            "txn_date_max": self._COL_TXN_DATE_MAX * scale,
            "value_date_max": self._COL_VALUE_DATE_MAX * scale,
            "desc_max": self._COL_DESC_MAX * scale,
            "ref_max": self._COL_REF_MAX * scale,
            "branch_max": self._COL_BRANCH_MAX * scale,
            "debit_max": self._COL_DEBIT_MAX * scale,
            "credit_max": self._COL_CREDIT_MAX * scale,
        }

    def _parse_with_coordinates(self, file_path: str) -> SBIParseResult:
        """Parse using coordinate-based extraction."""
        transactions = []
        opening_balance = None

        with pdfplumber.open(file_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                page_width = page.width
                bounds = self._get_scaled_boundaries(page_width)
                
                # Different Y-min for first page vs others
                y_min = self._DATA_Y_MIN_PAGE1 if page_num == 0 else self._DATA_Y_MIN_OTHERS
                
                # Extract page lines
                page_txns = self._extract_page_lines(page, bounds, y_min, self._DATA_Y_MAX)
                transactions.extend(page_txns)
                
                # Get opening balance from first transaction on first page
                if page_num == 0 and not opening_balance and page_txns:
                    first_txn = page_txns[0]
                    opening_balance = first_txn.balance
                    if first_txn.credit:
                        opening_balance -= first_txn.credit
                    if first_txn.debit:
                        opening_balance += first_txn.debit

        total_credits = sum(t.credit or 0 for t in transactions)
        total_debits = sum(t.debit or 0 for t in transactions)
        closing = transactions[-1].balance if transactions else None

        return SBIParseResult(
            transactions=transactions,
            total_count=len(transactions),
            parse_method="coordinate",
            opening_balance=opening_balance,
            closing_balance=closing,
            total_credits=total_credits,
            total_debits=total_debits,
        )

    def _parse_with_text_extraction(self, file_path: str) -> SBIParseResult:
        """Parse using text extraction as fallback."""
        transactions = []
        
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                lines = text.split('\n')
                
                for line in lines:
                    # Look for transaction lines with date pattern
                    if self._is_transaction_line(line):
                        txn = self._parse_transaction_line(line)
                        if txn:
                            transactions.append(txn)
        
        if not transactions:
            raise SBIParseError("No transactions found in text extraction")
        
        total_credits = sum(t.credit or 0 for t in transactions)
        total_debits = sum(t.debit or 0 for t in transactions)
        closing = transactions[-1].balance if transactions else None
        
        return SBIParseResult(
            transactions=transactions,
            total_count=len(transactions),
            parse_method="text",
            opening_balance=None,
            closing_balance=closing,
            total_credits=total_credits,
            total_debits=total_debits,
        )

    def _extract_page_lines(self, page, bounds: dict, y_min: float, y_max: float) -> List[SBITransaction]:
        """Extract transactions from a single page using coordinate-based grouping."""
        words = page.extract_words()
        
        # Filter words by Y coordinate
        data_words = [w for w in words if y_min <= w["top"] <= y_max]
        
        if not data_words:
            return []

        # Group words by Y coordinate (bucketing)
        lines = {}
        for word in data_words:
            y_bucket = round(word["top"] / self._Y_BUCKET) * self._Y_BUCKET
            if y_bucket not in lines:
                lines[y_bucket] = {
                    "txn_date": [],
                    "value_date": [],
                    "description": [],
                    "ref_no": [],
                    "branch": [],
                    "debit": [],
                    "credit": [],
                    "balance": [],
                }
            
            x0 = word["x0"]
            text = word["text"]
            
            # Assign to columns based on X coordinate
            if x0 < bounds["txn_date_max"]:
                lines[y_bucket]["txn_date"].append(text)
            elif x0 < bounds["value_date_max"]:
                lines[y_bucket]["value_date"].append(text)
            elif x0 < bounds["desc_max"]:
                lines[y_bucket]["description"].append(text)
            elif x0 < bounds["ref_max"]:
                lines[y_bucket]["ref_no"].append(text)
            elif x0 < bounds["branch_max"]:
                lines[y_bucket]["branch"].append(text)
            elif x0 < bounds["debit_max"]:
                lines[y_bucket]["debit"].append(text)
            elif x0 < bounds["credit_max"]:
                lines[y_bucket]["credit"].append(text)
            else:
                lines[y_bucket]["balance"].append(text)

        # Parse lines into transactions
        transactions = []
        sorted_y = sorted(lines.keys())
        
        i = 0
        while i < len(sorted_y):
            y = sorted_y[i]
            row = lines[y]
            
            # Check if this looks like a transaction line (has balance)
            balance_text = " ".join(row["balance"])
            if not balance_text or not self._looks_like_amount(balance_text):
                i += 1
                continue
            
            # Extract date (SBI format: DD Mon YY)
            txn_date_parts = row["txn_date"]
            value_date_parts = row["value_date"]
            
            # Combine date parts
            txn_date_str = " ".join(txn_date_parts)
            
            # Skip if no valid date
            if not self._is_date_like(txn_date_str):
                i += 1
                continue
            
            # Parse date to DD-MM-YYYY
            date = self._normalize_sbi_date(txn_date_str)
            
            # Description (may span multiple lines)
            description_parts = row["description"]
            j = i + 1
            while j < len(sorted_y):
                next_y = sorted_y[j]
                next_row = lines[next_y]
                # Continue while we have description but no balance
                if next_row["description"] and not next_row["balance"]:
                    description_parts.extend(next_row["description"])
                    j += 1
                else:
                    break
            
            description = " ".join(description_parts)
            
            # Ref no
            ref_no = " ".join(row["ref_no"])
            
            # Parse amounts
            debit = self._parse_amount(" ".join(row["debit"]))
            credit = self._parse_amount(" ".join(row["credit"]))
            balance = self._parse_amount(balance_text)
            
            if balance is not None:
                transactions.append(SBITransaction(
                    date=date,
                    description=description,
                    ref_no=ref_no,
                    debit=debit,
                    credit=credit,
                    balance=balance,
                ))
            
            i = j if j > i + 1 else i + 1

        return transactions

    def _is_transaction_line(self, line: str) -> bool:
        """Check if a line looks like a transaction."""
        # Must have a date and an amount
        has_date = bool(re.search(r'\d{1,2}\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)', line, re.IGNORECASE))
        has_amount = bool(re.search(r'\d{1,3}(?:,\d{3})*(?:\.\d{2})?', line))
        return has_date and has_amount

    def _parse_transaction_line(self, line: str) -> Optional[SBITransaction]:
        """Parse a transaction line from text."""
        try:
            # Extract date
            date_match = re.search(r'(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{2,4})', line, re.IGNORECASE)
            if not date_match:
                return None
            
            date_str = date_match.group(1)
            date = self._normalize_sbi_date(date_str)
            
            # Extract amounts
            amounts = re.findall(r'(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', line)
            if len(amounts) < 2:
                return None
            
            # Last amount is balance, others are debit/credit
            balance = float(amounts[-1].replace(',', ''))
            
            # Determine if debit or credit
            debit = None
            credit = None
            if len(amounts) >= 3:
                # Check for debit/credit indicators
                if 'DR' in line.upper() or 'BY' in line.upper():
                    debit = float(amounts[-2].replace(',', ''))
                else:
                    credit = float(amounts[-2].replace(',', ''))
            
            # Extract description (everything between date and amounts)
            desc_start = line.find(date_str) + len(date_str)
            desc_end = line.rfind(amounts[-1])
            description = line[desc_start:desc_end].strip()
            
            return SBITransaction(
                date=date,
                description=description,
                ref_no="",
                debit=debit,
                credit=credit,
                balance=balance,
            )
        except Exception as e:
            self.logger.warning("Error parsing transaction line: %s", str(e))
            return None

    def _looks_like_amount(self, text: str) -> bool:
        """Check if text looks like an amount."""
        # Remove commas and check if it's a number
        cleaned = text.replace(",", "").replace("-", "").strip()
        if not cleaned:
            return False
        try:
            float(cleaned)
            return True
        except ValueError:
            return False

    def _is_date_like(self, text: str) -> bool:
        """Check if text looks like a date."""
        # SBI format: "22 Jan 22" or "22 Jan"
        pattern = r'\d{1,2}\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)(?:\s+\d{2,4})?'
        return bool(re.search(pattern, text, re.IGNORECASE))

    def _normalize_sbi_date(self, date_str: str) -> str:
        """Convert SBI date format (DD Mon YY) to DD-MM-YYYY."""
        try:
            # Handle "22 Jan 22" format
            match = re.match(r'(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{2,4})', date_str.strip(), re.IGNORECASE)
            if match:
                day, month, year = match.groups()
                # Convert 2-digit year to 4-digit
                if len(year) == 2:
                    year = f"20{year}" if int(year) >= 0 else f"19{year}"
                # Convert month name to number
                month_map = {
                    'Jan': '01', 'Feb': '02', 'Mar': '03', 'Apr': '04',
                    'May': '05', 'Jun': '06', 'Jul': '07', 'Aug': '08',
                    'Sep': '09', 'Oct': '10', 'Nov': '11', 'Dec': '12'
                }
                month_num = month_map.get(month.capitalize(), '01')
                return f"{day.zfill(2)}-{month_num}-{year}"
            
            # Fallback for other formats
            for fmt in ["%d %b %Y", "%d %b %y"]:
                try:
                    dt = datetime.strptime(date_str.strip(), fmt)
                    return dt.strftime("%d-%m-%Y")
                except:
                    continue
            
            self.logger.warning("Could not parse date: %s", date_str)
            return date_str
        except Exception as e:
            self.logger.warning("Date parsing error for '%s': %s", date_str, str(e))
            return date_str

    def _parse_amount(self, text: str) -> Optional[float]:
        """Parse amount from text, handling Indian number format."""
        if not text or not text.strip():
            return None
        
        try:
            # Remove commas, handle negative values
            cleaned = text.replace(",", "").replace("-", "").strip()
            if cleaned == "" or cleaned == "0" or not any(c.isdigit() for c in cleaned):
                return None
            return float(cleaned)
        except ValueError:
            return None
