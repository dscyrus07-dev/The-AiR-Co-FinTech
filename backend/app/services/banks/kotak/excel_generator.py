"""
Airco Insights — Kotak Bank Excel Generator
=============================================
Delegates to report_generator for 5-sheet Excel output.
"""

import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class KotakExcelGenerator:
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def generate(
        self,
        transactions: List[Dict[str, Any]],
        output_path: str,
        user_info: Optional[Dict[str, Any]] = None,
    ) -> str:
        from .report_generator import generate_report
        self.logger.info("KotakExcelGenerator: delegating to report_generator")
        generate_report(transactions=transactions, output_path=output_path, user_info=user_info)
        return output_path
