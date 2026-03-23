"""
Airco Insights — Kotak Bank Processor (Master Controller)
==========================================================
Complete, self-contained Kotak Bank statement processor.
"""

import logging
import os
import time
import uuid
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

from .structure_validator import KotakStructureValidator, KotakStructureError
from .parser import KotakParser, KotakParseError
from .transaction_validator import KotakTransactionValidator, KotakValidationError
from .reconciliation import KotakReconciliation, KotakReconciliationError
from .rule_engine import KotakRuleEngine
from .ai_fallback import KotakAIFallback
from .recurring_engine import KotakRecurringEngine
from .aggregation_engine import KotakAggregationEngine
from .excel_generator import KotakExcelGenerator
from .formula_excel_engine import FormulaExcelEngine

logger = logging.getLogger(__name__)


class KotakProcessorError(Exception):
    def __init__(self, message: str, stage: str, error_code: str, details: dict = None):
        self.stage      = stage
        self.error_code = error_code
        self.details    = details or {}
        super().__init__(f"[{stage}] {message}")


@dataclass
class KotakProcessingMetrics:
    total_time_ms:         float = 0
    step_timings:          Dict[str, float] = field(default_factory=dict)
    transaction_count:     int = 0
    classified_count:      int = 0
    unclassified_count:    int = 0
    recurring_count:       int = 0
    reconciliation_passed: bool = False


@dataclass
class KotakProcessingResult:
    status:        str
    excel_path:    Optional[str]
    transactions:  List[Dict[str, Any]]
    aggregation:   Any
    metrics:       KotakProcessingMetrics
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


class KotakProcessor:
    """Master controller for Kotak Bank statement processing."""

    def __init__(
        self,
        strict_mode: bool = True,
        enable_ai:   bool = False,
        api_key:     Optional[str] = None,
    ):
        self.strict_mode = strict_mode
        self.enable_ai   = enable_ai
        self.api_key     = api_key

        self.structure_validator   = KotakStructureValidator()
        self.parser                = KotakParser()
        self.transaction_validator = KotakTransactionValidator(strict_mode=False)
        self.reconciliation        = KotakReconciliation(strict_mode=False)
        self.rule_engine           = KotakRuleEngine()
        self.ai_fallback           = KotakAIFallback(api_key=api_key)
        self.recurring_engine      = KotakRecurringEngine()
        self.aggregation_engine    = KotakAggregationEngine()
        self.excel_generator       = KotakExcelGenerator()
        self.formula_excel_engine  = FormulaExcelEngine()

        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def process(
        self,
        file_path:  str,
        user_info:  Dict[str, Any],
        output_dir: Optional[str] = None,
    ) -> KotakProcessingResult:
        """Process Kotak Bank statement end-to-end."""
        pipeline_start = time.monotonic()
        metrics        = KotakProcessingMetrics()
        return self._process_free_mode(file_path, user_info, output_dir, metrics, pipeline_start)

    def _process_free_mode(
        self,
        file_path:      str,
        user_info:      Dict[str, Any],
        output_dir:     Optional[str],
        metrics:        KotakProcessingMetrics,
        pipeline_start: float,
    ) -> KotakProcessingResult:
        from .report_generator import generate_report

        self.logger.info("KOTAK FREE MODE: coordinate parser + classifier + 5-sheet report")

        try:
            step_start   = time.monotonic()
            parse_result = self.parser.parse(file_path)
            metrics.step_timings["parsing"] = round((time.monotonic() - step_start) * 1000, 1)

            transactions = [txn.to_dict() for txn in parse_result.transactions]
            metrics.transaction_count = len(transactions)
            self.logger.info("Parsed %d Kotak transactions", len(transactions))

            if output_dir is None:
                output_dir = os.path.dirname(file_path) or "."

            step_start     = time.monotonic()
            excel_filename = f"kotak_report_{uuid.uuid4().hex[:12]}.xlsx"
            excel_path     = os.path.join(output_dir, excel_filename)

            report_stats = generate_report(
                transactions=transactions,
                output_path=excel_path,
                user_info=user_info,
            )

            metrics.step_timings["report_generation"] = round(
                (time.monotonic() - step_start) * 1000, 1
            )
            metrics.classified_count = report_stats["total_transactions"]
            metrics.recurring_count  = report_stats["recurring_count"]
            metrics.total_time_ms    = round((time.monotonic() - pipeline_start) * 1000, 1)

            self.logger.info(
                "KOTAK FREE MODE complete: %d transactions, %d recurring, %.1fms",
                report_stats["total_transactions"],
                report_stats["recurring_count"],
                metrics.total_time_ms,
            )

            return KotakProcessingResult(
                status="success",
                excel_path=excel_path,
                transactions=transactions,
                aggregation=report_stats,
                metrics=metrics,
            )

        except Exception as e:
            self.logger.error("Kotak processing failed: %s", str(e), exc_info=True)
            raise KotakProcessorError(
                f"Kotak processing failed: {str(e)}",
                stage="free_mode",
                error_code="KOTAK_PROCESSING_ERROR",
            )
