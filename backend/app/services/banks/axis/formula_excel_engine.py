"""
Airco Insights — Axis Bank Formula Excel Engine
================================================
Formula-based Excel generation for Axis Bank statements.
Generates the same 5-sheet report as report_generator but using
raw transaction data (no pre-classification required).
"""

import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class FormulaExcelEngine:
    """Formula-based Excel engine for Axis Bank."""

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def generate(
        self,
        transactions: List[Dict[str, Any]],
        metadata: Dict[str, Any],
        output_path: str,
    ) -> str:
        """
        Generate Excel report from transaction list.

        Args:
            transactions: List of dicts with date, description, debit, credit, balance, category
            metadata:     Dict with name, account_no, bank
            output_path:  Output file path

        Returns:
            output_path on success
        """
        from .report_generator import generate_report

        user_info = {
            "full_name":    metadata.get("name", ""),
            "account_type": metadata.get("account_type", ""),
            "bank_name":    "Axis Bank",
        }

        self.logger.info(
            "FormulaExcelEngine: generating Axis report for %d transactions",
            len(transactions)
        )

        generate_report(
            transactions=transactions,
            output_path=output_path,
            user_info=user_info,
        )
        return output_path
