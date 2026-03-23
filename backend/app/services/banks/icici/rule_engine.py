"""
Airco Insights — ICICI Bank Rule Engine
========================================
Deterministic classification for ICICI Bank transactions.

ICICI-specific prefixes:
- UPI/VPA@bank/   — UPI transfers (credit/debit)
- NEFT/           — NEFT transfers
- B/F             — Opening balance (not a transaction)
- ECS             — ECS/mandate debits
- ATM             — ATM withdrawals
"""

import logging
import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ClassificationResult:
    category: str
    confidence: float
    source: str
    matched_rule: Optional[str] = None
    matched_keyword: Optional[str] = None


class ICICIRuleEngine:
    """ICICI Bank-specific deterministic rule engine."""

    CONF_EXACT   = 0.99
    CONF_PATTERN = 0.95
    CONF_UPI     = 0.85
    CONF_AMOUNT  = 0.70

    DEBIT_RULES = {
        "ATM Withdrawal": {
            "exact": [
                "ATM", "CASH WITHDRAWAL", "ATM CASH", "ATM WDL",
                "ATM-WDL", "CASHWDL", "ATM WITHDL",
            ],
            "patterns": [
                r"ATM.*",
                r"CASH.*WITHDRA.*",
            ],
        },
        "Food": {
            "exact": [
                "SWIGGY", "ZOMATO", "DOMINOS", "MCDONALDS", "KFC",
                "PIZZA", "SUBWAY", "STARBUCKS", "CAFE", "RESTAURANT",
                "HALDIRAM", "FAASOS", "REBEL FOODS", "BIRYANI",
            ],
            "patterns": [
                r"UPI.*SWIGGY.*",
                r"UPI.*ZOMATO.*",
            ],
        },
        "Shopping": {
            "exact": [
                "AMAZON", "FLIPKART", "MYNTRA", "AJIO", "NYKAA",
                "DMART", "BIGBASKET", "BLINKIT", "ZEPTO", "JIOMART",
                "DECATHLON", "CROMA", "VIJAY SALES",
            ],
            "patterns": [
                r"UPI.*AMAZON.*",
                r"UPI.*FLIPKART.*",
            ],
        },
        "Transport": {
            "exact": [
                "UBER", "OLA", "RAPIDO", "PETROL", "DIESEL",
                "IRCTC", "METRO", "FASTAG", "TOLL",
                "REDBUS", "MAKEMYTRIP", "INDIGO", "SPICEJET",
            ],
            "patterns": [
                r"UPI.*UBER.*",
                r"UPI.*OLA.*",
                r"FASTAG.*",
                r"IRCTC.*",
            ],
        },
        "Bill Payment": {
            "exact": [
                "ELECTRICITY", "WATER", "GAS", "BROADBAND",
                "RECHARGE", "AIRTEL", "JIO", "VI", "BSNL",
                "PHARMACY", "APOLLO", "MEDPLUS", "HOSPITAL",
                "GST", "CBDT", "TDS", "INCOME TAX",
            ],
            "patterns": [
                r"BILL.*PAYMENT.*",
                r".*RECHARGE.*",
                r".*ELECTRICITY.*",
                r".*PHARMACY.*",
            ],
        },
        "Entertainment": {
            "exact": [
                "NETFLIX", "HOTSTAR", "AMAZON PRIME", "DISNEY",
                "SONYLIV", "ZEE5", "SPOTIFY", "GAANA",
            ],
            "patterns": [
                r"UPI.*NETFLIX.*",
                r"PRIME.*MEMBER.*",
            ],
        },
        "Loan Payments": {
            "exact": [
                "EMI", "LOAN", "LIC HOUSING", "HOME LOAN",
                "BAJAJ FINANCE",
            ],
            "patterns": [
                r"ECS.*DEBIT.*",
                r"NACH.*DEBIT.*",
                r".*EMI.*",
                r"ACH.*DR.*",
            ],
        },
        "Transfer": {
            "exact": ["NEFT", "RTGS", "IMPS", "UPI", "TRANSFER"],
            "patterns": [
                r"UPI/.*@.*",
                r"NEFT.*",
                r"RTGS.*",
                r"IMPS.*",
            ],
        },
    }

    CREDIT_RULES = {
        "Salary Credits": {
            "exact": ["SALARY", "SAL", "PAYROLL", "WAGES"],
            "patterns": [
                r"SALARY.*",
                r"SAL.*CREDIT.*",
                r"PAYROLL.*",
            ],
        },
        "Interest": {
            "exact": ["INTEREST", "INT", "INT.PD", "CREDIT INTEREST"],
            "patterns": [
                r"INTEREST.*CREDIT.*",
                r".*INTEREST.*",
            ],
        },
        "Refund": {
            "exact": ["REFUND", "REVERSAL", "CASHBACK", "NEFT RETURN"],
            "patterns": [
                r"REFUND.*",
                r".*REVERSAL.*",
                r"NEFT.*RETURN.*",
            ],
        },
        "Bank Transfer In": {
            "exact": ["NEFT CR", "RTGS CR", "IMPS CR"],
            "patterns": [
                r"UPI/.*@.*/.*",
                r"NEFT.*CR.*",
                r"RTGS.*CR.*",
                r"IMPS.*CR.*",
            ],
        },
    }

    UPI_MERCHANTS = {
        "swiggy": "Food",
        "zomato": "Food",
        "amazon": "Shopping",
        "flipkart": "Shopping",
        "uber": "Transport",
        "ola": "Transport",
        "netflix": "Entertainment",
        "hotstar": "Entertainment",
    }

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._compile_patterns()

    def _compile_patterns(self):
        self._debit_compiled  = {}
        self._credit_compiled = {}
        for cat, rules in self.DEBIT_RULES.items():
            self._debit_compiled[cat] = {
                "exact":    set(kw.upper() for kw in rules.get("exact", [])),
                "patterns": [re.compile(p, re.IGNORECASE) for p in rules.get("patterns", [])],
            }
        for cat, rules in self.CREDIT_RULES.items():
            self._credit_compiled[cat] = {
                "exact":    set(kw.upper() for kw in rules.get("exact", [])),
                "patterns": [re.compile(p, re.IGNORECASE) for p in rules.get("patterns", [])],
            }

    def classify(
        self, transactions: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        classified   = []
        unclassified = []
        for txn in transactions:
            result   = self._classify_single(txn)
            txn_copy = dict(txn)
            txn_copy["category"]     = result.category
            txn_copy["confidence"]   = result.confidence
            txn_copy["source"]       = result.source
            txn_copy["matched_rule"] = result.matched_rule
            if result.category.startswith("Others"):
                unclassified.append(txn_copy)
            else:
                classified.append(txn_copy)
        return classified, unclassified

    def _classify_single(self, txn: Dict[str, Any]) -> ClassificationResult:
        description = (txn.get("description") or "").upper()
        is_debit    = (txn.get("debit") or 0) > 0
        rules       = self._debit_compiled if is_debit else self._credit_compiled
        default     = "Others Debit" if is_debit else "Others Credit"

        for category, compiled in rules.items():
            for keyword in compiled["exact"]:
                if keyword in description:
                    return ClassificationResult(
                        category=category, confidence=self.CONF_EXACT,
                        source="rule_engine", matched_rule="exact_keyword",
                        matched_keyword=keyword,
                    )

        for category, compiled in rules.items():
            for pattern in compiled["patterns"]:
                if pattern.search(description):
                    return ClassificationResult(
                        category=category, confidence=self.CONF_PATTERN,
                        source="rule_engine", matched_rule="pattern_match",
                        matched_keyword=pattern.pattern,
                    )

        if is_debit:
            upi_result = self._classify_upi(description)
            if upi_result:
                return upi_result

        return ClassificationResult(
            category=default, confidence=0.5,
            source="rule_engine", matched_rule="default",
        )

    def _classify_upi(self, description: str) -> Optional[ClassificationResult]:
        desc_lower = description.lower()
        if "upi" not in desc_lower:
            return None
        for merchant, category in self.UPI_MERCHANTS.items():
            if merchant in desc_lower:
                return ClassificationResult(
                    category=category, confidence=self.CONF_UPI,
                    source="rule_engine", matched_rule="upi_merchant",
                    matched_keyword=merchant,
                )
        return None

    def get_statistics(self) -> Dict[str, Any]:
        dr = sum(len(r["exact"]) + len(r["patterns"]) for r in self._debit_compiled.values())
        cr = sum(len(r["exact"]) + len(r["patterns"]) for r in self._credit_compiled.values())
        return {"debit_rules": dr, "credit_rules": cr, "total_rules": dr + cr}
