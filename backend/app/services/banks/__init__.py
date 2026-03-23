"""
Airco Insights — Bank-Specific Processing Modules
=================================================
Each bank has its own dedicated processing module with:
- Structure validator
- Parser
- Transaction validator
- Balance reconciliation
- Rule engine
- AI fallback
- Recurring engine
- Aggregation engine
- Excel generator

No generic fallbacks. Each bank is a self-contained, accuracy-first processor.
"""

from .hdfc import HDFCProcessor
from .axis import AxisProcessor
from .icici import ICICIProcessor
from .kotak import KotakProcessor

__all__ = [
    "HDFCProcessor",
    "AxisProcessor",
    "ICICIProcessor",
    "KotakProcessor",
]
