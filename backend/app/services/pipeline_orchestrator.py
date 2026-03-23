"""
Airco Insights — Pipeline Orchestrator (Bank-Specific Architecture)
=======================================================================
Accuracy-first pipeline that routes to bank-specific processors.

NEW ARCHITECTURE:
- User selects bank → No auto-detection needed
- Each bank has its own complete processor
- 100% validation before output
- No generic fallbacks

Supported Banks:
- HDFC (complete)
- ICICI (planned)
- Axis (planned)
- Kotak (planned)

Design Principles:
- Bank-specific intelligence
- Deterministic parsing
- Strict validation at every step
- NO partial output
- Accuracy > Speed
"""

import logging
import os
import time
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class PipelineError(Exception):
    """Base exception for pipeline errors."""
    def __init__(self, message: str, stage: str = "unknown", error_code: str = "UNKNOWN"):
        self.stage = stage
        self.error_code = error_code
        super().__init__(f"[{stage}] {message}")


class PipelineValidationError(PipelineError):
    """Input validation failed."""
    pass


class PipelineAbortError(PipelineError):
    """Non-recoverable failure."""
    pass


class UnsupportedBankError(PipelineError):
    """Bank not supported in new architecture."""
    pass


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_MODES = ("free", "hybrid")
MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024  # 20 MB
ALLOWED_EXTENSIONS = (".pdf",)

# Supported banks with their processor modules
SUPPORTED_BANKS = {
    "hdfc": "HDFC Bank",
    "hdfc bank": "HDFC Bank",
    "icici": "ICICI Bank",
    "icici bank": "ICICI Bank",
    "axis": "Axis Bank",
    "axis bank": "Axis Bank",
    "kotak": "Kotak Bank",
    "kotak bank": "Kotak Bank",
    "hsbc": "HSBC",
    "sbi": "SBI",
    "state bank": "SBI",
}


# ---------------------------------------------------------------------------
# Input Validation
# ---------------------------------------------------------------------------

def _validate_input(
    file_path: str,
    user_info: dict,
    mode: str,
    api_key: Optional[str],
) -> None:
    """Validate all inputs before processing."""
    
    # File existence
    if not file_path or not isinstance(file_path, str):
        raise PipelineValidationError(
            "file_path must be a non-empty string",
            stage="input_validation",
            error_code="INVALID_FILE_PATH"
        )
    
    if not os.path.isfile(file_path):
        raise PipelineValidationError(
            f"File not found: {file_path}",
            stage="input_validation",
            error_code="FILE_NOT_FOUND"
        )
    
    # File extension
    if not file_path.lower().endswith(ALLOWED_EXTENSIONS):
        raise PipelineValidationError(
            "Invalid file type. Only PDF files are accepted.",
            stage="input_validation",
            error_code="INVALID_FILE_TYPE"
        )
    
    # File size
    file_size = os.path.getsize(file_path)
    if file_size == 0:
        raise PipelineValidationError(
            "Uploaded file is empty (0 bytes).",
            stage="input_validation",
            error_code="EMPTY_FILE"
        )
    if file_size > MAX_FILE_SIZE_BYTES:
        raise PipelineValidationError(
            f"File exceeds maximum size of {MAX_FILE_SIZE_BYTES // (1024*1024)}MB.",
            stage="input_validation",
            error_code="FILE_TOO_LARGE"
        )
    
    # Mode
    if mode not in VALID_MODES:
        raise PipelineValidationError(
            f"Invalid mode '{mode}'. Must be one of: {VALID_MODES}",
            stage="input_validation",
            error_code="INVALID_MODE"
        )
    
    # API key for hybrid mode
    if mode == "hybrid" and (not api_key or not api_key.strip()):
        raise PipelineValidationError(
            "Anthropic API key is required for hybrid mode.",
            stage="input_validation",
            error_code="MISSING_API_KEY"
        )
    
    # User info
    if not isinstance(user_info, dict):
        raise PipelineValidationError(
            "user_info must be a dict.",
            stage="input_validation",
            error_code="INVALID_USER_INFO"
        )
    
    # Bank name required
    bank_name = user_info.get("bank_name", "").lower().strip()
    if not bank_name:
        raise PipelineValidationError(
            "Bank name is required. Please select a bank.",
            stage="input_validation",
            error_code="MISSING_BANK_NAME"
        )
    
    logger.info(
        "Input validation passed: file=%s mode=%s bank=%s size=%d",
        os.path.basename(file_path), mode, bank_name, file_size
    )


def _normalize_bank_name(bank_name: str) -> str:
    """Normalize bank name to standard key."""
    bank_lower = bank_name.lower().strip()
    
    # Direct mapping
    if bank_lower in SUPPORTED_BANKS:
        return bank_lower.split()[0]  # Return first word (hdfc, icici, etc.)
    
    # Check if bank name contains known bank
    for key in SUPPORTED_BANKS:
        if key in bank_lower:
            return key.split()[0]
    
    return bank_lower.split()[0] if bank_lower else ""


def _get_bank_processor(bank_key: str):
    """Get the appropriate bank processor."""

    if bank_key == "hdfc":
        from app.services.banks.hdfc import HDFCProcessor
        return HDFCProcessor

    if bank_key == "axis":
        from app.services.banks.axis import AxisProcessor
        return AxisProcessor

    if bank_key == "icici":
        from app.services.banks.icici import ICICIProcessor
        return ICICIProcessor

    if bank_key in ("kotak", "kotakmahindra"):
        from app.services.banks.kotak import KotakProcessor
        return KotakProcessor

    if bank_key == "sbi":
        from app.services.banks.sbi import SBIProcessor
        return SBIProcessor

    return None


# ---------------------------------------------------------------------------
# Main Processing Function
# ---------------------------------------------------------------------------

def process_statement(
    file_path: str,
    user_info: dict,
    mode: str = "free",
    api_key: Optional[str] = None,
    output_dir: Optional[str] = None,
) -> dict:
    """
    Process bank statement using bank-specific processor.
    
    This is the accuracy-first entry point.
    
    Args:
        file_path: Absolute path to the uploaded PDF file
        user_info: Dict with full_name, account_type, bank_name
        mode: Processing mode — "free" or "hybrid"
        api_key: Anthropic API key (required for hybrid mode)
        output_dir: Output directory for generated files
        
    Returns:
        {
            "status": "success",
            "excel_path": str,
            "stats": {...},
            "validation": {...},
            "performance": {...},
        }
        
    Raises:
        PipelineValidationError: If input validation fails
        PipelineAbortError: If processing fails
        UnsupportedBankError: If bank is not supported
    """
    pipeline_start = time.monotonic()
    
    # =================================================================
    # STEP 1: Validate Input
    # =================================================================
    _validate_input(file_path, user_info, mode, api_key)
    
    # Extract and normalize bank name
    bank_name = user_info.get("bank_name", "")
    bank_key = _normalize_bank_name(bank_name)
    
    logger.info("Processing %s statement: bank_key=%s", bank_name, bank_key)
    
    # =================================================================
    # STEP 2: Get Bank-Specific Processor
    # =================================================================
    ProcessorClass = _get_bank_processor(bank_key)
    
    if ProcessorClass is None:
        raise UnsupportedBankError(
            f"Bank '{bank_name}' is not yet supported. "
            f"Supported banks: {', '.join(SUPPORTED_BANKS.values())}",
            stage="bank_routing",
            error_code="UNSUPPORTED_BANK"
        )
    
    # =================================================================
    # STEP 3: Initialize Processor
    # =================================================================
    enable_ai = mode == "hybrid"
    
    processor = ProcessorClass(
        strict_mode=False,  # Allow processing to continue with warnings
        enable_ai=enable_ai,
        api_key=api_key if enable_ai else None,
    )
    
    # =================================================================
    # STEP 4: Run Bank-Specific Processing
    # =================================================================
    try:
        if output_dir is None:
            from app.utils.file_handler import get_temp_dir
            output_dir = get_temp_dir()
        
        result = processor.process(
            file_path=file_path,
            user_info=user_info,
            output_dir=output_dir,
        )
        
    except Exception as e:
        logger.error("Bank processor failed: %s", str(e), exc_info=True)
        
        # Convert to pipeline error
        if hasattr(e, 'stage') and hasattr(e, 'error_code'):
            raise PipelineAbortError(
                str(e),
                stage=e.stage,
                error_code=e.error_code
            )
        else:
            raise PipelineAbortError(
                f"Processing failed: {str(e)}",
                stage="bank_processor",
                error_code="PROCESSOR_ERROR"
            )
    
    # =================================================================
    # STEP 5: Build Response
    # =================================================================
    total_time_ms = round((time.monotonic() - pipeline_start) * 1000, 1)
    
    response = result.to_dict()
    response["performance"]["total_pipeline_ms"] = total_time_ms
    response["bank_key"] = bank_key
    response["mode"] = mode
    
    logger.info(
        "Pipeline complete: bank=%s transactions=%d time=%.1fms",
        bank_key,
        result.metrics.transaction_count,
        total_time_ms
    )
    
    return response


# ---------------------------------------------------------------------------
# Legacy Compatibility Function (for unsupported banks)
# ---------------------------------------------------------------------------

def process_statement_legacy(
    file_path: str,
    user_info: dict,
    mode: str = "free",
    api_key: Optional[str] = None,
    db_session=None,
) -> dict:
    """
    Legacy processing function for unsupported banks.
    Falls back to generic processing.
    """
    bank_name = user_info.get("bank_name", "")
    bank_key = _normalize_bank_name(bank_name)
    
    # Fall back to legacy orchestrator for unsupported banks
    logger.info("Falling back to legacy processor for bank: %s", bank_key)
    
    # Import legacy processor (assuming it exists)
    # from app.services.legacy_orchestrator import process_statement as legacy_process
    # return legacy_process(file_path, user_info, mode, api_key, db_session)
    
    # For now, return unsupported error
    raise UnsupportedBankError(f"Bank '{bank_name}' is not supported yet")
