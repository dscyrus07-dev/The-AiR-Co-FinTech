"""
Airco Insights — Axis Bank Excel Generator
===========================================
Legacy Excel generator (kept for backward compatibility).
Primary report generation is handled by report_generator.py.
"""

import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class AxisExcelGenerator:
    """Axis Bank Excel generator — delegates to report_generator."""

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def generate(
        self,
        transactions: List[Dict[str, Any]],
        output_path: str,
        user_info: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Generate Excel report from classified transactions."""
        from .report_generator import generate_report

        self.logger.info("AxisExcelGenerator: delegating to report_generator")
        generate_report(
            transactions=transactions,
            output_path=output_path,
            user_info=user_info,
        )
        return output_path
