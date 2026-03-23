"""
Airco Insights — Kotak Bank Recurring Engine
=============================================
Detects recurring transactions for Kotak Bank.
"""

import logging
import re
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict
from datetime import datetime
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class RecurringPattern:
    merchant_key: str
    transaction_count: int
    avg_amount: float
    frequency: str
    recurring_type: str


class KotakRecurringEngine:
    SUBSCRIPTION_MERCHANTS = {
        "netflix", "hotstar", "prime", "spotify", "apple", "youtube",
        "gaana", "wynk", "zee5", "sonyliv", "google", "microsoft",
    }
    EMI_PATTERNS     = [r"NACH.*DEBIT.*", r"ECS.*DEBIT.*", r".*EMI.*", r"LIC.*HOUSING"]
    UTILITY_PATTERNS = [r"ELECTRICITY", r"BROADBAND", r"RECHARGE", r"DTH", r"INSURANCE.*PREMIUM"]
    SALARY_PATTERNS  = [r"SALARY", r"SAL\s*CR", r"PAYROLL"]

    WEEKLY_RANGE     = (5, 9)
    MONTHLY_RANGE    = (25, 35)
    QUARTERLY_RANGE  = (85, 95)
    AMOUNT_TOLERANCE = 0.05

    def __init__(self):
        self.logger            = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._emi_compiled     = [re.compile(p, re.IGNORECASE) for p in self.EMI_PATTERNS]
        self._utility_compiled = [re.compile(p, re.IGNORECASE) for p in self.UTILITY_PATTERNS]
        self._salary_compiled  = [re.compile(p, re.IGNORECASE) for p in self.SALARY_PATTERNS]

    def detect(self, transactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        self.logger.info("Detecting recurring patterns in %d Kotak transactions", len(transactions))
        merchant_groups   = self._group_by_merchant(transactions)
        recurring_patterns = self._detect_patterns(merchant_groups)
        result = []
        for txn in transactions:
            txn_copy     = dict(txn)
            merchant_key = self._get_merchant_key(txn)
            known        = self._check_known_patterns(txn)
            if known:
                txn_copy["is_recurring"]       = True
                txn_copy["recurring_type"]      = known[0]
                txn_copy["recurring_frequency"] = known[1]
            elif merchant_key in recurring_patterns:
                p = recurring_patterns[merchant_key]
                txn_copy["is_recurring"]       = True
                txn_copy["recurring_type"]      = p.recurring_type
                txn_copy["recurring_frequency"] = p.frequency
            else:
                txn_copy["is_recurring"]       = False
                txn_copy["recurring_type"]      = None
                txn_copy["recurring_frequency"] = None
            result.append(txn_copy)
        self.logger.info("Detected %d recurring transactions", sum(1 for t in result if t.get("is_recurring")))
        return result

    def _group_by_merchant(self, transactions):
        groups = defaultdict(list)
        for txn in transactions:
            key = self._get_merchant_key(txn)
            if key:
                groups[key].append(txn)
        return dict(groups)

    def _get_merchant_key(self, txn: Dict[str, Any]) -> str:
        desc = (txn.get("description") or "").upper()
        # Extract merchant from UPI/MerchantName/... pattern
        upi_match = re.match(r'UPI/([^/]+)/', desc)
        if upi_match:
            merchant = upi_match.group(1)
            words    = re.findall(r"[A-Z]+", merchant)
            key_words = [w for w in words[:2] if len(w) > 2]
            if key_words:
                return "_".join(key_words[:2]).lower()
        words     = re.findall(r"[A-Z]+", desc)
        key_words = [w for w in words[:3] if len(w) > 2]
        return "_".join(key_words[:2]).lower()

    def _detect_patterns(self, merchant_groups):
        patterns = {}
        for key, txns in merchant_groups.items():
            if len(txns) < 2:
                continue
            sorted_txns  = sorted(txns, key=lambda t: t.get("date", ""))
            intervals    = self._calculate_intervals(sorted_txns)
            if not intervals:
                continue
            avg_interval = sum(intervals) / len(intervals)
            frequency    = self._determine_frequency(avg_interval)
            if not frequency:
                continue
            amounts    = [t.get("debit") or t.get("credit") or 0 for t in txns]
            avg_amount = sum(amounts) / len(amounts)
            if not self._check_amount_consistency(amounts, avg_amount):
                continue
            patterns[key] = RecurringPattern(
                merchant_key=key,
                transaction_count=len(txns),
                avg_amount=avg_amount,
                frequency=frequency,
                recurring_type=self._determine_type(key, txns),
            )
        return patterns

    def _calculate_intervals(self, sorted_txns):
        intervals = []
        for i in range(1, len(sorted_txns)):
            try:
                prev  = datetime.strptime(sorted_txns[i-1]["date"], "%Y-%m-%d")
                curr  = datetime.strptime(sorted_txns[i]["date"],   "%Y-%m-%d")
                delta = (curr - prev).days
                if delta > 0:
                    intervals.append(delta)
            except (ValueError, KeyError):
                continue
        return intervals

    def _determine_frequency(self, avg_interval: float) -> Optional[str]:
        if self.WEEKLY_RANGE[0]    <= avg_interval <= self.WEEKLY_RANGE[1]:    return "weekly"
        if self.MONTHLY_RANGE[0]   <= avg_interval <= self.MONTHLY_RANGE[1]:   return "monthly"
        if self.QUARTERLY_RANGE[0] <= avg_interval <= self.QUARTERLY_RANGE[1]: return "quarterly"
        return None

    def _check_amount_consistency(self, amounts, avg_amount) -> bool:
        if avg_amount == 0:
            return False
        return all(abs(a - avg_amount) / avg_amount <= self.AMOUNT_TOLERANCE for a in amounts)

    def _determine_type(self, merchant_key, txns) -> str:
        if merchant_key in self.SUBSCRIPTION_MERCHANTS:
            return "subscription"
        desc = txns[0].get("description", "").upper()
        for p in self._emi_compiled:
            if p.search(desc): return "emi"
        for p in self._utility_compiled:
            if p.search(desc): return "utility"
        for p in self._salary_compiled:
            if p.search(desc): return "salary"
        return "recurring"

    def _check_known_patterns(self, txn) -> Optional[Tuple[str, str]]:
        desc = (txn.get("description") or "").upper()
        for p in self._emi_compiled:
            if p.search(desc): return ("emi", "monthly")
        if txn.get("credit"):
            for p in self._salary_compiled:
                if p.search(desc): return ("salary", "monthly")
        for m in self.SUBSCRIPTION_MERCHANTS:
            if m in desc.lower(): return ("subscription", "monthly")
        for p in self._utility_compiled:
            if p.search(desc): return ("utility", "monthly")
        return None
