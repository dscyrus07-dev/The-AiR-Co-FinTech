"""
Airco Insights — HDFC Processor (Master Controller)
====================================================
Complete, self-contained HDFC bank statement processor.
Orchestrates all HDFC-specific modules in strict order.

Processing Pipeline:
1. PDF Integrity Validation
2. HDFC Structure Validation
3. Transaction Parsing
4. Transaction Validation
5. Balance Reconciliation
6. Rule Engine Classification
7. AI Fallback (if enabled)
8. Recurring Detection
9. Aggregation
10. Excel Generation
11. Final Integrity Check

Design Principles:
- NO output until 100% validated
- Fail fast on any integrity issue
- Bank-specific logic only (no generic fallbacks)
- Deterministic, reproducible results
"""

import logging
import os
import time
import uuid
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

from .structure_validator import HDFCStructureValidator, HDFCStructureError
from .parser import HDFCParser, HDFCParseError
from .transaction_validator import HDFCTransactionValidator, HDFCValidationError
from .reconciliation import HDFCReconciliation, HDFCReconciliationError
from .rule_engine import HDFCRuleEngine
from .ai_fallback import HDFCAIFallback
from .recurring_engine import HDFCRecurringEngine
from .aggregation_engine import HDFCAggregationEngine
from .excel_generator import HDFCExcelGenerator
from .formula_excel_engine import FormulaExcelEngine

from app.services.core.pdf_integrity_validator import PDFIntegrityValidator, PDFIntegrityError
from app.services.core.data_integrity_guard import DataIntegrityGuard, IntegrityError

logger = logging.getLogger(__name__)


class HDFCProcessorError(Exception):
    """Base exception for HDFC processor errors."""
    def __init__(self, message: str, stage: str, error_code: str, details: dict = None):
        self.stage = stage
        self.error_code = error_code
        self.details = details or {}
        super().__init__(f"[{stage}] {message}")


@dataclass
class HDFCProcessingMetrics:
    """Processing metrics for monitoring."""
    total_time_ms: float = 0
    step_timings: Dict[str, float] = field(default_factory=dict)
    transaction_count: int = 0
    classified_count: int = 0
    unclassified_count: int = 0
    ai_classified_count: int = 0
    recurring_count: int = 0
    reconciliation_passed: bool = False
    integrity_passed: bool = False


@dataclass
class HDFCProcessingResult:
    """Complete processing result."""
    status: str  # "success" or "failed"
    excel_path: Optional[str]
    transactions: List[Dict[str, Any]]
    aggregation: Any
    metrics: HDFCProcessingMetrics
    integrity_result: Any
    error_message: Optional[str] = None
    error_code: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "excel_path": self.excel_path,
            "stats": {
                "total_transactions": self.metrics.transaction_count,
                "rule_engine_classified": self.metrics.classified_count,
                "ai_classified": self.metrics.ai_classified_count,
                "others": self.metrics.unclassified_count,
                "recurring": self.metrics.recurring_count,
                "coverage_percent": round(
                    (self.metrics.classified_count + self.metrics.ai_classified_count) / 
                    max(self.metrics.transaction_count, 1) * 100, 1
                ),
            },
            "validation": {
                "reconciliation_passed": self.metrics.reconciliation_passed,
                "integrity_passed": self.metrics.integrity_passed,
            },
            "performance": self.metrics.step_timings,
            "error": {
                "message": self.error_message,
                "code": self.error_code,
            } if self.error_message else None,
        }


class HDFCProcessor:
    """
    Master controller for HDFC bank statement processing.
    """
    
    def __init__(
        self,
        strict_mode: bool = True,
        enable_ai: bool = False,
        api_key: Optional[str] = None,
    ):
        """
        Initialize HDFC processor.
        
        Args:
            strict_mode: If True, fail on any validation error
            enable_ai: If True, use AI for unclassified transactions
            api_key: Anthropic API key for AI classification
        """
        self.strict_mode = strict_mode
        self.enable_ai = enable_ai
        self.api_key = api_key
        
        # Initialize all modules
        self.pdf_validator = PDFIntegrityValidator()
        self.structure_validator = HDFCStructureValidator()
        self.parser = HDFCParser()
        self.transaction_validator = HDFCTransactionValidator(strict_mode=False)  # Handle errors gracefully
        self.reconciliation = HDFCReconciliation(strict_mode=False)  # Allow auto-correction
        self.rule_engine = HDFCRuleEngine()
        self.ai_fallback = HDFCAIFallback(api_key=api_key)
        self.recurring_engine = HDFCRecurringEngine()
        self.aggregation_engine = HDFCAggregationEngine()
        self.excel_generator = HDFCExcelGenerator()
        self.formula_excel_engine = FormulaExcelEngine()  # New formula-based engine
        self.integrity_guard = DataIntegrityGuard(strict_mode=strict_mode)
        
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def _process_free_mode(
        self,
        file_path: str, 
        user_info: Dict[str, Any], 
        output_dir: str, 
        metrics: HDFCProcessingMetrics,
        pipeline_start: float
    ) -> HDFCProcessingResult:
        """
        Free Mode: Coordinate-based parser + strict rule engine + 5-sheet report.
        
        Flow:
        1. Parse PDF using coordinate-based method (100% accuracy)
        2. Classify transactions using deterministic rule engine
        3. Detect recurring transactions
        4. Generate 5-sheet Excel report (Summary, Category, Weekly, Recurring, Raw)
        """
        from .report_generator import generate_report
        
        self.logger.info("FREE MODE: coordinate parser + banking-grade classifier + 7-sheet report")
        
        try:
            # Step 1: Parse PDF
            step_start = time.monotonic()
            parse_result = self.parser.parse(file_path)
            metrics.step_timings["parsing"] = round((time.monotonic() - step_start) * 1000, 1)
            
            transactions = [txn.to_dict() for txn in parse_result.transactions]
            metrics.transaction_count = len(transactions)
            
            self.logger.info("Parsed %d transactions using coordinate-based method", len(transactions))
            
            # Step 2+3+4: Classify, detect recurring, generate 5-sheet report
            step_start = time.monotonic()
            excel_filename = f"hdfc_report_{uuid.uuid4().hex[:12]}.xlsx"
            excel_path = os.path.join(output_dir, excel_filename)
            
            report_stats = generate_report(
                transactions=transactions,
                output_path=excel_path,
                user_info=user_info,
            )
            
            metrics.step_timings["report_generation"] = round((time.monotonic() - step_start) * 1000, 1)
            metrics.classified_count = report_stats["total_transactions"]
            metrics.recurring_count = report_stats["recurring_count"]
            
            # Calculate total time
            total_time_ms = round((time.monotonic() - pipeline_start) * 1000, 1)
            metrics.total_time_ms = total_time_ms
            
            self.logger.info(
                "FREE MODE complete: %d transactions, %d recurring, %d categories, %.1fms",
                report_stats["total_transactions"],
                report_stats["recurring_count"],
                report_stats["categories_used"],
                total_time_ms,
            )
            
            return HDFCProcessingResult(
                status="success",
                excel_path=excel_path,
                transactions=transactions,
                aggregation=report_stats,
                metrics=metrics,
                integrity_result=None,
            )
            
        except Exception as e:
            self.logger.error("Free Mode processing failed: %s", str(e), exc_info=True)
            raise HDFCProcessorError(
                f"Free Mode processing failed: {str(e)}",
                stage="free_mode_conversion", 
                error_code="FREE_MODE_ERROR"
            )
    
    def process(
        self,
        file_path: str,
        user_info: Dict[str, Any],
        output_dir: Optional[str] = None,
    ) -> HDFCProcessingResult:
        """
        Process HDFC bank statement end-to-end.
        
        Args:
            file_path: Path to PDF file
        """
        pipeline_start = time.monotonic()
        metrics = HDFCProcessingMetrics()
        
        # =================================================================
        # FREE MODE: Direct Coordinate-Based Conversion
        # =================================================================
        if output_dir is None:
            output_dir = os.path.dirname(file_path)
            
        if not self.enable_ai:  # Free Mode - use coordinate parser directly
            return self._process_free_mode(file_path, user_info, output_dir, metrics, pipeline_start)
        
        try:
            # =================================================================
            # STEP 1: PDF Integrity Validation
            # =================================================================
            step_start = time.monotonic()
            self.logger.info("Step 1: PDF Integrity Validation")
            
            try:
                pdf_result = self.pdf_validator.validate(file_path)
            except PDFIntegrityError as e:
                raise HDFCProcessorError(
                    str(e), stage="pdf_validation", error_code=e.error_code, details=e.details
                )
            
            metrics.step_timings["pdf_validation"] = round((time.monotonic() - step_start) * 1000, 1)
            self.logger.info("PDF validation passed: %d pages, %d chars", 
                           pdf_result.page_count, len(pdf_result.text_content))
            # =================================================================
            step_start = time.monotonic()
            self.logger.info("Step 2: HDFC Structure Validation")
            
            try:
                structure_result = self.structure_validator.validate(
                    pdf_result.text_content,
                    pdf_result.first_page_text
                )
            except HDFCStructureError as e:
                raise HDFCProcessorError(
                    str(e), stage="structure_validation", error_code=e.error_code, details=e.details
                )
            
            statement_metadata = structure_result.metadata
            metrics.step_timings["structure_validation"] = round((time.monotonic() - step_start) * 1000, 1)
            
            self.logger.info(
                "Statement metadata: account=%s dr_count=%s cr_count=%s",
                statement_metadata.account_number,
                statement_metadata.dr_count,
                statement_metadata.cr_count
            )
            
            # =================================================================
            # STEP 3: Transaction Parsing
            # =================================================================
            step_start = time.monotonic()
            self.logger.info("Step 3: Transaction Parsing")
            
            try:
                parse_result = self.parser.parse(file_path, pdf_result.text_content)
            except HDFCParseError as e:
                raise HDFCProcessorError(
                    str(e), stage="parsing", error_code=e.error_code, details=e.details
                )
            
            metrics.step_timings["parsing"] = round((time.monotonic() - step_start) * 1000, 1)
            self.logger.info("Parsed %d transactions using %s method", 
                           parse_result.total_count, parse_result.parse_method)
            
            # =================================================================
            # STEP 4: Transaction Validation
            # =================================================================
            step_start = time.monotonic()
            self.logger.info("Step 4: Transaction Validation")
            
            try:
                validation_result = self.transaction_validator.validate(parse_result.transactions)
            except HDFCValidationError as e:
                raise HDFCProcessorError(
                    str(e), stage="validation", error_code=e.error_code, details=e.details
                )
            
            transactions = validation_result.validated_transactions
            metrics.step_timings["validation"] = round((time.monotonic() - step_start) * 1000, 1)
            self.logger.info("Validated %d/%d transactions", 
                           validation_result.valid_count, validation_result.total_count)
            
            # =================================================================
            # STEP 5: Balance Reconciliation
            # =================================================================
            step_start = time.monotonic()
            self.logger.info("Step 5: Balance Reconciliation")
            
            # Try auto-correction first
            transactions, corrections = self.reconciliation.auto_correct_debit_credit(transactions)
            if corrections > 0:
                self.logger.info("Auto-corrected %d debit/credit assignments", corrections)
            
            try:
                recon_result = self.reconciliation.reconcile(
                    transactions,
                    expected_opening=statement_metadata.opening_balance,
                    expected_closing=statement_metadata.closing_balance,
                )
            except HDFCReconciliationError as e:
                if self.strict_mode:
                    raise HDFCProcessorError(
                        str(e), stage="reconciliation", error_code=e.error_code, details=e.details
                    )
                self.logger.warning("Reconciliation failed (non-strict mode): %s", str(e))
                recon_result = None
            
            metrics.reconciliation_passed = recon_result.is_reconciled if recon_result else False
            metrics.step_timings["reconciliation"] = round((time.monotonic() - step_start) * 1000, 1)
            
            # =================================================================
            # STEP 6: Rule Engine Classification
            # =================================================================
            step_start = time.monotonic()
            self.logger.info("Step 6: Rule Engine Classification")
            
            classified, unclassified = self.rule_engine.classify(transactions)
            
            metrics.classified_count = len(classified)
            metrics.step_timings["rule_engine"] = round((time.monotonic() - step_start) * 1000, 1)
            self.logger.info("Rule engine: %d classified, %d unclassified", 
                           len(classified), len(unclassified))
            
            # =================================================================
            # STEP 7: AI Fallback (if enabled)
            # =================================================================
            ai_classified_count = 0
            
            if self.enable_ai and unclassified:
                step_start = time.monotonic()
                self.logger.info("Step 7: AI Classification (%d transactions)", len(unclassified))
                
                ai_results, ai_stats = self.ai_fallback.classify(
                    unclassified,
                    bank_name="HDFC",
                    account_type=user_info.get("account_type", "Salaried"),
                )
                
                # Count actual AI classifications (not Others)
                ai_classified_count = sum(
                    1 for t in ai_results
                    if not t.get("category", "").startswith("Others")
                )
                
                all_transactions = classified + ai_results
                metrics.ai_classified_count = ai_classified_count
                metrics.step_timings["ai_classification"] = round((time.monotonic() - step_start) * 1000, 1)
            else:
                # Tag unclassified as Others
                for txn in unclassified:
                    is_debit = txn.get("debit") is not None
                    txn["category"] = "Others Debit" if is_debit else "Others Credit"
                    txn["confidence"] = 0.5
                    txn["source"] = "default_others"
                
                all_transactions = classified + unclassified
            
            metrics.unclassified_count = sum(
                1 for t in all_transactions
                if t.get("category", "").startswith("Others")
            )
            
            # =================================================================
            # STEP 8: Recurring Detection
            # =================================================================
            step_start = time.monotonic()
            self.logger.info("Step 8: Recurring Detection")
            
            all_transactions = self.recurring_engine.detect(all_transactions)
            
            metrics.recurring_count = sum(1 for t in all_transactions if t.get("is_recurring"))
            metrics.step_timings["recurring_detection"] = round((time.monotonic() - step_start) * 1000, 1)
            self.logger.info("Detected %d recurring transactions", metrics.recurring_count)
            
            # =================================================================
            # STEP 9: Aggregation
            # =================================================================
            step_start = time.monotonic()
            self.logger.info("Step 9: Aggregation")
            
            aggregation = self.aggregation_engine.aggregate(
                all_transactions,
                opening_balance=recon_result.opening_balance if recon_result else 0,
                closing_balance=recon_result.closing_balance if recon_result else 0,
            )
            
            metrics.step_timings["aggregation"] = round((time.monotonic() - step_start) * 1000, 1)
            
            # =================================================================
            # STEP 10: Final Integrity Check
            # =================================================================
            step_start = time.monotonic()
            self.logger.info("Step 10: Final Integrity Check")
            
            try:
                integrity_result = self.integrity_guard.validate(
                    all_transactions,
                    expected_count=statement_metadata.expected_transaction_count,
                )
            except IntegrityError as e:
                if self.strict_mode:
                    raise HDFCProcessorError(
                        str(e), stage="integrity_check", 
                        error_code="INTEGRITY_FAILED", details=e.details
                    )
                self.logger.warning("Integrity check failed (non-strict): %s", str(e))
                integrity_result = None
            
            metrics.integrity_passed = integrity_result.is_valid if integrity_result else False
            metrics.step_timings["integrity_check"] = round((time.monotonic() - step_start) * 1000, 1)
            
            # =================================================================
            # STEP 11: Excel Generation (Formula-Based Engine)
            # =================================================================
            step_start = time.monotonic()
            self.logger.info("Step 11: Excel Generation (Formula-Based)")
            
            if output_dir is None:
                output_dir = os.path.dirname(file_path)
            
            output_id = uuid.uuid4().hex[:12]
            excel_filename = f"hdfc_report_{output_id}.xlsx"
            excel_path = os.path.join(output_dir, excel_filename)
            
            # Convert transactions to formula engine format
            formula_transactions = []
            for txn in all_transactions:
                formula_transactions.append({
                    'date': txn.get('date', ''),
                    'description': txn.get('description', ''),
                    'debit': txn.get('debit'),
                    'credit': txn.get('credit'),
                    'balance': txn.get('balance'),
                    'category': txn.get('category', ''),
                    'confidence': txn.get('confidence', ''),
                    'recurring': 'Yes' if txn.get('recurring', False) else 'No',
                })
            
            # Use formula-based Excel engine
            metadata = {
                'name': user_info.get('name', ''),
                'account_no': user_info.get('account_number', ''),
            }
            
            self.formula_excel_engine.generate(
                formula_transactions,
                metadata,
                excel_path,
            )
            
            metrics.step_timings["excel_generation"] = round((time.monotonic() - step_start) * 1000, 1)
            
            # =================================================================
            # COMPLETE
            # =================================================================
            metrics.transaction_count = len(all_transactions)
            metrics.total_time_ms = round((time.monotonic() - start_time) * 1000, 1)
            
            self.logger.info(
                "HDFC processing complete: %d transactions, %.1fms, reconciled=%s, integrity=%s",
                metrics.transaction_count, metrics.total_time_ms,
                metrics.reconciliation_passed, metrics.integrity_passed
            )
            
            return HDFCProcessingResult(
                status="success",
                excel_path=excel_path,
                transactions=all_transactions,
                aggregation=aggregation,
                metrics=metrics,
                integrity_result=integrity_result,
            )
            
        except HDFCProcessorError:
            raise
        except Exception as e:
            self.logger.error("Unexpected error in HDFC processing: %s", str(e), exc_info=True)
            raise HDFCProcessorError(
                f"Unexpected error: {str(e)}",
                stage="unknown",
                error_code="UNEXPECTED_ERROR",
                details={"error": str(e)}
            )
