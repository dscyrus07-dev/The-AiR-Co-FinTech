"""
Airco Insights — HDFC Structure Validator
==========================================
Validates that PDF structure matches HDFC Bank statement format.
Extracts statement metadata (account number, period, summary counts).

HDFC Statement Structure:
- Header: HDFC BANK LIMITED, Account details
- Statement period: From/To dates
- Account summary: Opening balance, Dr Count, Cr Count, Closing balance
- Transaction table with specific column layout

Design: Fail if structure doesn't match HDFC format.
"""

import logging
import re
from typing import Optional, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class HDFCStructureError(Exception):
    """Raised when PDF structure doesn't match HDFC format."""
    def __init__(self, message: str, error_code: str, details: dict = None):
        self.error_code = error_code
        self.details = details or {}
        super().__init__(message)


@dataclass
class HDFCStatementMetadata:
    """Extracted metadata from HDFC statement."""
    account_number: Optional[str] = None
    account_holder: Optional[str] = None
    statement_from: Optional[str] = None
    statement_to: Optional[str] = None
    opening_balance: Optional[float] = None
    closing_balance: Optional[float] = None
    dr_count: Optional[int] = None
    cr_count: Optional[int] = None
    total_debits: Optional[float] = None
    total_credits: Optional[float] = None
    branch: Optional[str] = None
    ifsc: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "account_number": self.account_number,
            "account_holder": self.account_holder,
            "statement_from": self.statement_from,
            "statement_to": self.statement_to,
            "opening_balance": self.opening_balance,
            "closing_balance": self.closing_balance,
            "dr_count": self.dr_count,
            "cr_count": self.cr_count,
            "total_debits": self.total_debits,
            "total_credits": self.total_credits,
            "branch": self.branch,
            "ifsc": self.ifsc,
        }
    
    @property
    def expected_transaction_count(self) -> Optional[int]:
        """Total expected transactions (Dr + Cr)."""
        if self.dr_count is not None and self.cr_count is not None:
            return self.dr_count + self.cr_count
        return None


@dataclass
class HDFCStructureResult:
    """Result of HDFC structure validation."""
    is_valid: bool
    confidence: float
    metadata: HDFCStatementMetadata
    text_content: str
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "is_valid": self.is_valid,
            "confidence": self.confidence,
            "metadata": self.metadata.to_dict(),
            "error_code": self.error_code,
            "error_message": self.error_message,
        }


class HDFCStructureValidator:
    """
    Validates HDFC Bank statement structure and extracts metadata.
    """
    
    # HDFC identification patterns
    HDFC_MARKERS = [
        r"HDFC\s*BANK",
        r"HDFCBANK",
        r"HDFC\s*Bank\s*Limited",
        r"HDFCBANKLIMITED",
    ]
    
    # Account number patterns
    ACCOUNT_PATTERNS = [
        r"Account\s*No[:\.]?\s*(\d{10,14})",
        r"AccountNo[:\.]?\s*(\d{10,14})",
        r"A/c\s*No[:\.]?\s*(\d{10,14})",
        r"Account\s*Number[:\.]?\s*(\d{10,14})",
    ]
    
    # Statement period patterns
    PERIOD_PATTERNS = [
        r"Statement\s*From[:\s]*(\d{2}/\d{2}/\d{2,4})\s*(?:To|to|TO)[:\s]*(\d{2}/\d{2}/\d{2,4})",
        r"StatementFrom[:\s]*(\d{2}/\d{2}/\d{2,4})\s*(?:To|to|TO)[:\s]*(\d{2}/\d{2}/\d{2,4})",
        r"From[:\s]*(\d{2}/\d{2}/\d{2,4})\s*To[:\s]*(\d{2}/\d{2}/\d{2,4})",
        r"Period[:\s]*(\d{2}/\d{2}/\d{2,4})\s*-\s*(\d{2}/\d{2}/\d{2,4})",
    ]
    
    # Summary patterns (HDFC-specific)
    OPENING_BAL_PATTERNS = [
        r"Opening\s*Balance[:\s]*([\d,]+\.\d{2})",
        r"OpeningBalance[:\s]*([\d,]+\.\d{2})",
    ]
    
    CLOSING_BAL_PATTERNS = [
        r"Closing\s*Bal(?:ance)?[:\s]*([\d,]+\.\d{2})",
        r"ClosingBal(?:ance)?[:\s]*([\d,]+\.\d{2})",
    ]
    
    DR_COUNT_PATTERNS = [
        r"Dr\s*Count[:\s]*(\d+)",
        r"DrCount[:\s]*(\d+)",
        r"Debit\s*Count[:\s]*(\d+)",
    ]
    
    CR_COUNT_PATTERNS = [
        r"Cr\s*Count[:\s]*(\d+)",
        r"CrCount[:\s]*(\d+)",
        r"Credit\s*Count[:\s]*(\d+)",
    ]
    
    TOTAL_DEBITS_PATTERNS = [
        r"Debits[:\s]*([\d,]+\.\d{2})",
        r"Total\s*Debits?[:\s]*([\d,]+\.\d{2})",
    ]
    
    TOTAL_CREDITS_PATTERNS = [
        r"Credits[:\s]*([\d,]+\.\d{2})",
        r"Total\s*Credits?[:\s]*([\d,]+\.\d{2})",
    ]
    
    IFSC_PATTERNS = [
        r"IFSC[:\s]*(HDFC\d{7})",
        r"RTGS/NEFT\s*IFSC[:\s]*(HDFC\d{7})",
    ]
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def validate(self, text_content: str, first_page_text: str = "") -> HDFCStructureResult:
        """
        Validate that text content is from HDFC Bank statement.
        
        Args:
            text_content: Full extracted text from PDF
            first_page_text: First page text for header validation
            
        Returns:
            HDFCStructureResult with validation status and metadata
            
        Raises:
            HDFCStructureError: If structure doesn't match HDFC format
        """
        self.logger.info("Validating HDFC statement structure")
        
        # Use first page for header checks if available
        header_text = first_page_text if first_page_text else text_content[:5000]
        
        # Step 1: Verify HDFC bank markers
        confidence = self._check_hdfc_markers(header_text)
        
        if confidence < 0.5:
            raise HDFCStructureError(
                "PDF does not appear to be an HDFC Bank statement",
                error_code="NOT_HDFC_STATEMENT",
                details={"confidence": confidence}
            )
        
        # Step 2: Extract metadata
        metadata = self._extract_metadata(text_content, header_text)
        
        # Step 3: Validate minimum required fields
        if not metadata.account_number:
            self.logger.warning("Could not extract account number")
        
        # Check for transaction table markers
        has_table = self._check_transaction_table(text_content)
        if not has_table:
            raise HDFCStructureError(
                "Could not identify transaction table in HDFC statement",
                error_code="NO_TRANSACTION_TABLE",
                details={"has_date_column": False}
            )
        
        self.logger.info(
            "HDFC structure validated: account=%s, period=%s to %s, dr=%s cr=%s",
            metadata.account_number,
            metadata.statement_from,
            metadata.statement_to,
            metadata.dr_count,
            metadata.cr_count,
        )
        
        return HDFCStructureResult(
            is_valid=True,
            confidence=confidence,
            metadata=metadata,
            text_content=text_content,
        )
    
    def _check_hdfc_markers(self, text: str) -> float:
        """Check for HDFC bank markers and return confidence score."""
        text_upper = text.upper()
        
        markers_found = 0
        for pattern in self.HDFC_MARKERS:
            if re.search(pattern, text, re.IGNORECASE):
                markers_found += 1
        
        # Check for IFSC code starting with HDFC
        if re.search(r"HDFC\d{7}", text):
            markers_found += 1
        
        # Calculate confidence based on markers found
        confidence = min(markers_found / 2, 1.0)
        
        return confidence
    
    def _check_transaction_table(self, text: str) -> bool:
        """Check if text contains HDFC transaction table structure."""
        # Look for date patterns that indicate transaction rows
        date_pattern = r'\d{2}/\d{2}/\d{2,4}'
        date_matches = re.findall(date_pattern, text)
        
        # HDFC statements typically have column headers
        header_patterns = [
            r"Date\s*Narration",
            r"DateNarration",
            r"Withdrawal.*Deposit.*Balance",
            r"Chq\./Ref\.No",
        ]
        
        has_headers = any(re.search(p, text, re.IGNORECASE) for p in header_patterns)
        has_dates = len(date_matches) > 2
        
        return has_headers or has_dates
    
    def _extract_metadata(self, full_text: str, header_text: str) -> HDFCStatementMetadata:
        """Extract statement metadata from text."""
        metadata = HDFCStatementMetadata()
        
        # Account number
        for pattern in self.ACCOUNT_PATTERNS:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                metadata.account_number = match.group(1)
                break
        
        # Statement period
        for pattern in self.PERIOD_PATTERNS:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                metadata.statement_from = match.group(1)
                metadata.statement_to = match.group(2)
                break
        
        # Opening balance
        for pattern in self.OPENING_BAL_PATTERNS:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                metadata.opening_balance = self._parse_amount(match.group(1))
                break
        
        # Closing balance
        for pattern in self.CLOSING_BAL_PATTERNS:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                metadata.closing_balance = self._parse_amount(match.group(1))
                break
        
        # Dr count
        for pattern in self.DR_COUNT_PATTERNS:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                try:
                    metadata.dr_count = int(match.group(1))
                except ValueError:
                    pass
                break
        
        # Cr count
        for pattern in self.CR_COUNT_PATTERNS:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                try:
                    metadata.cr_count = int(match.group(1))
                except ValueError:
                    pass
                break
        
        # IFSC
        for pattern in self.IFSC_PATTERNS:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                metadata.ifsc = match.group(1)
                break
        
        # Total debits
        for pattern in self.TOTAL_DEBITS_PATTERNS:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                metadata.total_debits = self._parse_amount(match.group(1))
                break
        
        # Total credits
        for pattern in self.TOTAL_CREDITS_PATTERNS:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                metadata.total_credits = self._parse_amount(match.group(1))
                break
        
        return metadata
    
    def _parse_amount(self, amount_str: str) -> Optional[float]:
        """Parse Indian format amount string to float."""
        if not amount_str:
            return None
        try:
            cleaned = amount_str.replace(",", "")
            return float(cleaned)
        except (ValueError, TypeError):
            return None
