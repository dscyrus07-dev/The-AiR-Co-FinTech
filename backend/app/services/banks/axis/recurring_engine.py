"""
Airco Insights — Axis Bank Recurring Engine
============================================
Detects recurring transactions (subscriptions, EMIs, salary, utilities).
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


class AxisRecurringEngine:
    """Recurring transaction detection for Axis Bank."""

    SUBSCRIPTION_MERCHANTS = {
        "netflix", "hotstar", "prime", "spotify", "apple", "youtube",
        "gaana", "wynk", "jiosaavn", "zee5", "sonyliv", "discovery",
        "linkedin", "microsoft", "google", "adobe", "dropbox",
    }

    EMI_PATTERNS = [
        r"ACH-DR-.*",           # Axis mandate prefix
        r"EMI.*\d+/\d+",
        r"LOAN.*EMI",
        r".*EMI.*DEBIT",
        r"LIC\s*HOUSING",
        r"HOME\s*LOAN",
        r"CAR\s*LOAN",
    ]

    UTILITY_PATTERNS = [
        r"ELECTRICITY", r"POWER", r"GAS", r"WATER", r"BROADBAND",
        r"MOBILE.*RECHARGE", r"DTH", r"INSURANCE.*PREMIUM",
    ]

    SALARY_PATTERNS = [
        r"SALARY", r"SAL\s*CR", r"PAYROLL", r"WAGES",
    ]

    WEEKLY_RANGE    = (5, 9)
    MONTHLY_RANGE   = (25, 35)
    QUARTERLY_RANGE = (85, 95)
    AMOUNT_TOLERANCE = 0.05

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._emi_compiled     = [re.compile(p, re.IGNORECASE) for p in self.EMI_PATTERNS]
        self._utility_compiled = [re.compile(p, re.IGNORECASE) for p in self.UTILITY_PATTERNS]
        self._salary_compiled  = [re.compile(p, re.IGNORECASE) for p in self.SALARY_PATTERNS]

    def detect(self, transactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Detect recurring transactions and add flags."""
        self.logger.info("Detecting recurring patterns in %d transactions", len(transactions))

        merchant_groups = self._group_by_merchant(transactions)
        recurring_patterns = self._detect_patterns(merchant_groups)

        result = []
        for txn in transactions:
            txn_copy = dict(txn)
            merchant_key = self._get_merchant_key(txn)

            pattern_match = self._check_known_patterns(txn)
            if pattern_match:
                txn_copy["is_recurring"]       = True
                txn_copy["recurring_type"]      = pattern_match[0]
                txn_copy["recurring_frequency"] = pattern_match[1]
            elif merchant_key in recurring_patterns:
                pattern = recurring_patterns[merchant_key]
                txn_copy["is_recurring"]       = True
                txn_copy["recurring_type"]      = pattern.recurring_type
                txn_copy["recurring_frequency"] = pattern.frequency
            else:
                txn_copy["is_recurring"]       = False
                txn_copy["recurring_type"]      = None
                txn_copy["recurring_frequency"] = None

            result.append(txn_copy)

        recurring_count = sum(1 for t in result if t.get("is_recurring"))
        self.logger.info("Detected %d recurring transactions", recurring_count)
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
        for prefix in ["UPI/P2A/", "UPI/P2M/", "IMPS/P2A/", "IMPS/P2M/",
                        "NEFT-", "RTGS-", "ACH-DR-"]:
            if desc.startswith(prefix):
                desc = desc[len(prefix):]
        words = re.findall(r"[A-Z]+", desc)
        key_words = [w for w in words[:3] if len(w) > 2]
        return "_".join(key_words[:2]).lower()

    def _detect_patterns(self, merchant_groups):
        patterns = {}
        for merchant_key, txns in merchant_groups.items():
            if len(txns) < 2:
                continue
            sorted_txns = sorted(txns, key=lambda t: t.get("date", ""))
            intervals = self._calculate_intervals(sorted_txns)
            if not intervals:
                continue
            avg_interval = sum(intervals) / len(intervals)
            frequency = self._determine_frequency(avg_interval)
            if not frequency:
                continue
            amounts = [t.get("debit") or t.get("credit") or 0 for t in txns]
            avg_amount = sum(amounts) / len(amounts)
            if not self._check_amount_consistency(amounts, avg_amount):
                continue
            recurring_type = self._determine_type(merchant_key, txns)
            patterns[merchant_key] = RecurringPattern(
                merchant_key=merchant_key,
                transaction_count=len(txns),
                avg_amount=avg_amount,
                frequency=frequency,
                recurring_type=recurring_type,
            )
        return patterns

    def _calculate_intervals(self, sorted_txns):
        intervals = []
        for i in range(1, len(sorted_txns)):
            try:
                prev = datetime.strptime(sorted_txns[i-1]["date"], "%Y-%m-%d")
                curr = datetime.strptime(sorted_txns[i]["date"],   "%Y-%m-%d")
                delta = (curr - prev).days
                if delta > 0:
                    intervals.append(delta)
            except (ValueError, KeyError):
                continue
        return intervals

    def _determine_frequency(self, avg_interval: float) -> Optional[str]:
        if self.WEEKLY_RANGE[0] <= avg_interval <= self.WEEKLY_RANGE[1]:
            return "weekly"
        if self.MONTHLY_RANGE[0] <= avg_interval <= self.MONTHLY_RANGE[1]:
            return "monthly"
        if self.QUARTERLY_RANGE[0] <= avg_interval <= self.QUARTERLY_RANGE[1]:
            return "quarterly"
        return None

    def _check_amount_consistency(self, amounts, avg_amount) -> bool:
        if avg_amount == 0:
            return False
        return all(
            abs(a - avg_amount) / avg_amount <= self.AMOUNT_TOLERANCE
            for a in amounts
        )

    def _determine_type(self, merchant_key, txns) -> str:
        if merchant_key in self.SUBSCRIPTION_MERCHANTS:
            return "subscription"
        sample_desc = txns[0].get("description", "").upper()
        for pattern in self._emi_compiled:
            if pattern.search(sample_desc):
                return "emi"
        for pattern in self._utility_compiled:
            if pattern.search(sample_desc):
                return "utility"
        for pattern in self._salary_compiled:
            if pattern.search(sample_desc):
                return "salary"
        return "recurring"

    def _check_known_patterns(self, txn) -> Optional[Tuple[str, str]]:
        desc = (txn.get("description") or "").upper()
        for pattern in self._emi_compiled:
            if pattern.search(desc):
                return ("emi", "monthly")
        if txn.get("credit"):
            for pattern in self._salary_compiled:
                if pattern.search(desc):
                    return ("salary", "monthly")
        desc_lower = desc.lower()
        for merchant in self.SUBSCRIPTION_MERCHANTS:
            if merchant in desc_lower:
                return ("subscription", "monthly")
        for pattern in self._utility_compiled:
            if pattern.search(desc):
                return ("utility", "monthly")
        return None
