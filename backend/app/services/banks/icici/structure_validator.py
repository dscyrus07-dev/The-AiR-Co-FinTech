"""
Airco Insights — ICICI Bank Structure Validator
================================================
Validates PDF matches ICICI Bank statement format.
Extracts metadata: account number, period, opening/closing balance.

ICICI Statement Structure:
- Header: MR./MS. Name, address block
- Summary of Accounts under Cust ID
- Statement of Transactions in Savings Account Number: XXXXXXXXXXXXXXX
- Column headers: DATE | MODE** | PARTICULARS | DEPOSITS | WITHDRAWALS | BALANCE
- IFSC starts with ICIC (ICICI Bank)
- Date format: DD-MM-YYYY
"""

import logging
import re
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class ICICIStructureError(Exception):
    def __init__(self, message: str, error_code: str, details: dict = None):
        self.error_code = error_code
        self.details    = details or {}
        super().__init__(message)


@dataclass
class ICICIStatementMetadata:
    account_number: Optional[str] = None
    account_holder: Optional[str] = None
    statement_from: Optional[str] = None
    statement_to:   Optional[str] = None
    opening_balance: Optional[float] = None
    closing_balance: Optional[float] = None
    customer_id:    Optional[str] = None
    ifsc:           Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "account_number":  self.account_number,
            "account_holder":  self.account_holder,
            "statement_from":  self.statement_from,
            "statement_to":    self.statement_to,
            "opening_balance": self.opening_balance,
            "closing_balance": self.closing_balance,
            "customer_id":     self.customer_id,
            "ifsc":            self.ifsc,
        }

    @property
    def expected_transaction_count(self) -> Optional[int]:
        return None


@dataclass
class ICICIStructureResult:
    is_valid:     bool
    confidence:   float
    metadata:     ICICIStatementMetadata
    text_content: str
    error_code:   Optional[str] = None
    error_message: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "is_valid":     self.is_valid,
            "confidence":   self.confidence,
            "metadata":     self.metadata.to_dict(),
            "error_code":   self.error_code,
            "error_message": self.error_message,
        }


class ICICIStructureValidator:
    """Validates ICICI Bank statement structure and extracts metadata."""

    ICICI_MARKERS = [
        r"ICICI\s*BANK",
        r"icicibank\.com",
        r"ICIC\d{7}",          # ICICI IFSC prefix
        r"Statement\s*of\s*Transactions\s*in\s*Savings\s*Account",
        r"Summary\s*of\s*Accounts\s*held\s*under\s*Cust\s*ID",
        r"Cust\s*ID[:\s]*\d+",
    ]

    ACCOUNT_PATTERNS = [
        r"Savings\s*Account\s*Number[:\s]*(\d{12,18})",
        r"Account\s*Number[:\s]*(\d{12,18})",
        r"A/c\s*No[:\s]*(\d{12,18})",
        r"(\d{12,18})\s*in\s*INR",
        r"Savings\s*A/c\s+(\d{12,18})",
    ]

    PERIOD_PATTERNS = [
        r"for\s+the\s+period\s+(\w+\s+\d+,?\s*\d{4})\s*[-–]\s*(\w+\s+\d+,?\s*\d{4})",
        r"for\s+the\s+period\s+(\w+\s+\d+\s*\d{4})\s*[-–]\s*(\w+\s+\d+\s*\d{4})",
        r"(\d{2}-\d{2}-\d{4})\s*[-–]\s*(\d{2}-\d{2}-\d{4})",
        r"(\w+\s+\d{2},\s*\d{4})\s*-\s*(\w+\s+\d{2},\s*\d{4})",
        # Format: "February 21, 2025 - August 21, 2025"
        r"((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d+,?\s+\d{4})\s*-\s*((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d+,?\s+\d{4})",
    ]

    CUSTOMER_ID_PATTERNS = [
        r"Cust\s*ID[:\s]*(\d{6,12})",
        r"Customer\s*ID[:\s]*(\d{6,12})",
    ]

    IFSC_PATTERNS = [
        r"(ICIC\d{7})",
        r"IFSC[:\s]*(ICIC\d{7})",
    ]

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def validate(self, text_content: str, first_page_text: str = "") -> ICICIStructureResult:
        self.logger.info("Validating ICICI Bank statement structure")

        header_text = first_page_text if first_page_text else text_content[:6000]
        confidence  = self._check_icici_markers(header_text)

        if confidence < 0.4:
            raise ICICIStructureError(
                "PDF does not appear to be an ICICI Bank statement",
                error_code="NOT_ICICI_STATEMENT",
                details={"confidence": confidence}
            )

        metadata = self._extract_metadata(text_content, header_text)

        has_table = self._check_transaction_table(text_content)
        if not has_table:
            raise ICICIStructureError(
                "Could not identify transaction table in ICICI Bank statement",
                error_code="NO_TRANSACTION_TABLE",
            )

        self.logger.info(
            "ICICI structure validated: account=%s, period=%s to %s",
            metadata.account_number,
            metadata.statement_from,
            metadata.statement_to,
        )

        return ICICIStructureResult(
            is_valid=True,
            confidence=confidence,
            metadata=metadata,
            text_content=text_content,
        )

    def _check_icici_markers(self, text: str) -> float:
        markers_found = sum(
            1 for p in self.ICICI_MARKERS
            if re.search(p, text, re.IGNORECASE)
        )
        return min(markers_found / 2, 1.0)

    def _check_transaction_table(self, text: str) -> bool:
        date_matches = re.findall(r'\d{2}-\d{2}-\d{4}', text)
        header_patterns = [
            r"DEPOSITS",
            r"WITHDRAWALS",
            r"PARTICULARS",
            r"B/F",
        ]
        has_headers = any(re.search(p, text, re.IGNORECASE) for p in header_patterns)
        return has_headers or len(date_matches) > 2

    def _extract_metadata(self, full_text: str, header_text: str) -> ICICIStatementMetadata:
        metadata = ICICIStatementMetadata()

        for pattern in self.ACCOUNT_PATTERNS:
            m = re.search(pattern, full_text, re.IGNORECASE)
            if m:
                metadata.account_number = m.group(1)
                break

        for pattern in self.PERIOD_PATTERNS:
            m = re.search(pattern, full_text, re.IGNORECASE | re.DOTALL)
            if m:
                metadata.statement_from = m.group(1).strip()
                metadata.statement_to   = m.group(2).strip()
                break

        for pattern in self.CUSTOMER_ID_PATTERNS:
            m = re.search(pattern, full_text, re.IGNORECASE)
            if m:
                metadata.customer_id = m.group(1)
                break

        for pattern in self.IFSC_PATTERNS:
            m = re.search(pattern, full_text, re.IGNORECASE)
            if m:
                metadata.ifsc = m.group(1)
                break

        # Opening balance from B/F entry
        bf_match = re.search(r'B/F\s+([\d,]+\.\d{2})', full_text, re.IGNORECASE)
        if bf_match:
            try:
                metadata.opening_balance = float(bf_match.group(1).replace(",", ""))
            except ValueError:
                pass

        return metadata

    def _parse_amount(self, amount_str: str) -> Optional[float]:
        if not amount_str:
            return None
        try:
            return float(amount_str.replace(",", ""))
        except (ValueError, TypeError):
            return None
