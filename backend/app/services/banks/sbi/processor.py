"""
Airco Insights — SBI Bank Processor (Master Controller)
========================================================
Complete, self-contained SBI Bank statement processor.
"""

import logging
import os
import time
import uuid
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

from .structure_validator import SBIStructureValidator, SBIStructureError
from .parser import SBIParser, SBIParseError
from .transaction_validator import SBITransactionValidator, SBIValidationError
from .reconciliation import SBIReconciliation, SBIReconciliationError
from .rule_engine import SBIRuleEngine
from .ai_fallback import SBIAIFallback
from .recurring_engine import SBIRecurringEngine
from .aggregation_engine import SBIAggregationEngine
from .excel_generator import SBIExcelGenerator
from .formula_excel_engine import FormulaExcelEngine

logger = logging.getLogger(__name__)


class SBIProcessorError(Exception):
    def __init__(self, message: str, stage: str, error_code: str, details: dict = None):
        self.stage      = stage
        self.error_code = error_code
        self.details    = details or {}
        super().__init__(f"[{stage}] {message}")


@dataclass
class SBIProcessingMetrics:
    total_time_ms:         float = 0
    step_timings:          Dict[str, float] = field(default_factory=dict)
    transaction_count:     int = 0
    classified_count:      int = 0
    unclassified_count:    int = 0
    recurring_count:       int = 0
    reconciliation_passed: bool = False


@dataclass
class SBIProcessingResult:
    status:        str
    excel_path:    Optional[str]
    transactions:  List[Dict[str, Any]]
    aggregation:   Any
    metrics:       SBIProcessingMetrics
    error_message: Optional[str] = None
    error_code:    Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "status":     self.status,
            "excel_path": self.excel_path,
            "stats": {
                "total_transactions": self.metrics.transaction_count,
                "classified":         self.metrics.classified_count,
                "others":             self.metrics.unclassified_count,
                "recurring":          self.metrics.recurring_count,
                "coverage_percent": round(
                    self.metrics.classified_count /
                    max(self.metrics.transaction_count, 1) * 100, 1
                ),
            },
            "validation": {"reconciliation_passed": self.metrics.reconciliation_passed},
            "performance": self.metrics.step_timings,
            "error": {"message": self.error_message, "code": self.error_code}
            if self.error_message else None,
        }


class SBIProcessor:
    """Master controller for SBI Bank statement processing."""

    def __init__(
        self,
        strict_mode: bool = True,
        enable_ai:   bool = False,
        api_key:     Optional[str] = None,
    ):
        self.strict_mode = strict_mode
        self.enable_ai   = enable_ai
        self.api_key     = api_key

        self.structure_validator   = SBIStructureValidator()
        self.parser                = SBIParser()
        self.transaction_validator = SBITransactionValidator(strict_mode=False)
        self.reconciliation        = SBIReconciliation(strict_mode=False)
        self.rule_engine           = SBIRuleEngine()
        self.ai_fallback           = SBIAIFallback(api_key=api_key)
        self.recurring_engine      = SBIRecurringEngine()
        self.aggregation_engine    = SBIAggregationEngine()
        self.excel_generator       = SBIExcelGenerator()
        self.formula_excel_engine  = FormulaExcelEngine()

        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def process(
        self,
        file_path: str,
        user_info: Dict[str, Any],
        output_dir: Optional[str] = None,
    ) -> SBIProcessingResult:
        """Process SBI Bank statement end-to-end."""
        pipeline_start = time.monotonic()
        metrics = SBIProcessingMetrics()
        return self._process_free_mode(file_path, user_info, output_dir, metrics, pipeline_start)

    def _process_free_mode(
        self,
        file_path: str,
        user_info: Dict[str, Any],
        output_dir: Optional[str],
        metrics: SBIProcessingMetrics,
        pipeline_start: float,
    ) -> SBIProcessingResult:
        """Process SBI statement in free mode."""
        t0 = time.time()

        try:
            # Stage 1: Structure validation
            import pdfplumber
            with pdfplumber.open(file_path) as pdf:
                text_content = ""
                for page in pdf.pages:
                    text_content += page.extract_text() + "\n"
            
            structure_result = self._time_step(
                "structure_validation",
                lambda: self.structure_validator.validate(text_content, text_content[:6000]),
                metrics
            )

            # Stage 2: Parse transactions
            parse_result = self._time_step(
                "parsing",
                lambda: self.parser.parse(file_path),
                metrics
            )

            if parse_result.total_count <= 0:
                raise SBIParseError(
                    "Could not extract any transactions from this SBI PDF. Please upload a text-based SBI statement downloaded from internet banking.",
                    error_code="NO_TRANSACTIONS",
                )
            
            metrics.transaction_count = parse_result.total_count
            transactions = [t.to_dict() for t in parse_result.transactions]

            # Stage 3: Transaction validation
            self._time_step(
                "transaction_validation",
                lambda: self.transaction_validator.validate(transactions),
                metrics
            )

            # Stage 4: Reconciliation
            try:
                self._time_step(
                    "reconciliation",
                    lambda: self.reconciliation.reconcile(
                        transactions,
                        parse_result.opening_balance,
                        parse_result.closing_balance,
                        parse_result.total_credits,
                        parse_result.total_debits,
                    ),
                    metrics
                )
                metrics.reconciliation_passed = True
            except SBIReconciliationError as e:
                self.logger.warning("Reconciliation warning: %s", str(e))
                metrics.reconciliation_passed = False

            # Stage 5: Rule-based classification
            classified_txns, _ = self._time_step(
                "classification",
                lambda: self.rule_engine.classify(transactions),
                metrics
            )

            # Stage 6: AI fallback (if enabled)
            if self.enable_ai and self.api_key:
                classified_txns = self._time_step(
                    "ai_fallback",
                    lambda: self.ai_fallback.classify_unclassified(classified_txns),
                    metrics
                )

            # Stage 7: Recurring detection
            classified_txns = self._time_step(
                "recurring_detection",
                lambda: self.recurring_engine.detect(classified_txns),
                metrics
            )

            # Update metrics
            metrics.classified_count = sum(
                1 for t in classified_txns if t.get("Category") != "Others"
            )
            metrics.unclassified_count = sum(
                1 for t in classified_txns if t.get("Category") == "Others"
            )
            metrics.recurring_count = sum(
                1 for t in classified_txns if t.get("is_recurring")
            )

            # Stage 8: Aggregation
            aggregation = self._time_step(
                "aggregation",
                lambda: self.aggregation_engine.aggregate(classified_txns),
                metrics
            )

            # Stage 9: Excel generation
            if output_dir is None:
                output_dir = os.path.dirname(file_path) or "."
            
            excel_filename = f"sbi_report_{uuid.uuid4().hex[:12]}.xlsx"
            excel_path = os.path.join(output_dir, excel_filename)
            
            self._time_step(
                "excel_generation",
                lambda: self.excel_generator.generate(
                    classified_txns,
                    excel_path,
                    user_info=user_info,
                ),
                metrics
            )

            metrics.total_time_ms = (time.monotonic() - pipeline_start) * 1000

            self.logger.info(
                "SBI processing complete: %d txns, %.1f%% coverage, %.0f ms",
                metrics.transaction_count,
                metrics.classified_count / max(metrics.transaction_count, 1) * 100,
                metrics.total_time_ms,
            )

            return SBIProcessingResult(
                status="success",
                excel_path=excel_path,
                transactions=classified_txns,
                aggregation=aggregation,
                metrics=metrics,
            )

        except (SBIStructureError, SBIParseError, SBIValidationError) as e:
            metrics.total_time_ms = (time.monotonic() - pipeline_start) * 1000
            error_code = getattr(e, "error_code", "UNKNOWN")
            self.logger.error("SBI processing failed: %s", str(e))
            return SBIProcessingResult(
                status="failed",
                excel_path=None,
                transactions=[],
                aggregation=None,
                metrics=metrics,
                error_message=str(e),
                error_code=error_code,
            )

    def _time_step(self, step_name: str, func, metrics: SBIProcessingMetrics):
        """Time a processing step and store in metrics."""
        t0 = time.time()
        result = func()
        metrics.step_timings[step_name] = (time.time() - t0) * 1000
        return result
