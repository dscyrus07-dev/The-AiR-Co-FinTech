"""
Airco Insights — Kotak Bank Formula Excel Engine
"""

import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class FormulaExcelEngine:
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def generate(
        self,
        transactions: List[Dict[str, Any]],
        metadata: Dict[str, Any],
        output_path: str,
    ) -> str:
        from .report_generator import generate_report
        user_info = {
            "full_name":    metadata.get("name", ""),
            "account_type": metadata.get("account_type", ""),
            "bank_name":    "Kotak Mahindra Bank",
        }
        self.logger.info("FormulaExcelEngine: generating Kotak report for %d transactions", len(transactions))
        generate_report(transactions=transactions, output_path=output_path, user_info=user_info)
        return output_path
