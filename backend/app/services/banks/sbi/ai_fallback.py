"""
Airco Insights — SBI Bank AI Fallback (stub)
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class AIClassificationResult:
    classified_count: int
    total_sent: int
    api_calls: int
    estimated_cost_usd: float
    estimated_cost_inr: float


class SBIAIFallback:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.logger  = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def classify(
        self,
        transactions: List[Dict[str, Any]],
        bank_name: str = "SBI",
        account_type: str = "Salaried",
    ) -> Tuple[List[Dict[str, Any]], AIClassificationResult]:
        result = []
        for txn in transactions:
            txn_copy = dict(txn)
            is_debit = (txn_copy.get("debit") or 0) > 0
            if not txn_copy.get("category") or txn_copy["category"].startswith("Others"):
                txn_copy["category"]   = "Others Debit" if is_debit else "Others Credit"
                txn_copy["confidence"] = 0.5
                txn_copy["source"]     = "ai_fallback_stub"
            result.append(txn_copy)
        stats = AIClassificationResult(
            classified_count=0, total_sent=len(transactions),
            api_calls=0, estimated_cost_usd=0.0, estimated_cost_inr=0.0,
        )
        return result, stats
