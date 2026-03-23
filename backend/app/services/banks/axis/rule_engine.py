"""
Airco Insights — Axis Bank Rule Engine
=======================================
Deterministic classification engine for Axis Bank transactions.
Bank-specific rules optimized for Axis statement patterns.

Axis-specific transaction prefixes:
- ATM-CASH/   — ATM cash withdrawal
- ATM-CASH-AXIS/ — Axis ATM
- IMPS/P2A/   — IMPS credit transfer
- IMPS/P2M/   — IMPS merchant payment
- UPI/P2A/    — UPI transfer
- UPI/P2M/    — UPI merchant payment
- ACH-DR-     — Mandate/EMI debit
- CreditCard Payment — credit card bill payment
- NEFT/       — NEFT transfer
"""

import logging
import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ClassificationResult:
    """Classification result for a transaction."""
    category: str
    confidence: float
    source: str
    matched_rule: Optional[str] = None
    matched_keyword: Optional[str] = None


class AxisRuleEngine:
    """Axis Bank-specific deterministic rule engine."""

    CONF_EXACT   = 0.99
    CONF_PATTERN = 0.95
    CONF_MERCHANT = 0.90
    CONF_UPI     = 0.85
    CONF_AMOUNT  = 0.70

    DEBIT_RULES = {
        "ATM Withdrawal": {
            "exact": [
                "ATM-CASH", "ATM CASH", "ATM WDL", "CASH WITHDRAWAL",
                "ATM-CASH-AXIS", "ATM-CASH/HYDERABAD", "ATM-CASH/MUMBAI",
                "ATM-CASH/DELHI", "ATM-CASH/BANGALORE", "ATM-CASH/CHENNAI",
                "ATM-CASH/KOLKATA", "ATM-CASH/PUNE", "ATM-CASH/NCBI",
                "ATM-CASH/KANDI", "ATM-CASH/BANDLAGU", "ATM OFFSITE",
            ],
            "patterns": [
                r"ATM-CASH.*",
                r"ATM.*CASH.*",
                r"CASH.*WITHDRA.*",
                r"ATM-CASH-AXIS.*",
            ],
        },
        "Food": {
            "exact": [
                "SWIGGY", "ZOMATO", "DOMINOS", "MCDONALDS", "KFC", "BURGER",
                "PIZZA", "PIZZAHUT", "SUBWAY", "STARBUCKS", "CCD", "CAFE",
                "RESTAURANT", "FOOD", "DINING", "EATERY", "BIRYANI",
                "HALDIRAM", "BARBEQUE", "CHAAYOS", "FAASOS", "REBEL FOODS",
            ],
            "patterns": [
                r"UPI/P2M.*SWIGGY.*",
                r"UPI/P2M.*ZOMATO.*",
                r"IMPS/P2M.*FOOD.*",
            ],
        },
        "Shopping": {
            "exact": [
                "AMAZON", "FLIPKART", "MYNTRA", "AJIO", "NYKAA", "MEESHO",
                "SNAPDEAL", "TATACLIQ", "DMART", "BIGBASKET", "BLINKIT",
                "ZEPTO", "INSTAMART", "JIOMART", "DECATHLON", "IKEA",
                "SHOPPERS STOP", "LIFESTYLE", "WESTSIDE", "PANTALOONS",
                "MAX", "ZARA", "H&M", "MINISO", "CROMA", "VIJAY SALES",
                "RELIANCE DIGITAL",
            ],
            "patterns": [
                r"UPI/P2M.*AMAZON.*",
                r"UPI/P2M.*FLIPKART.*",
                r"IMPS/P2M.*SHOP.*",
            ],
        },
        "Transport": {
            "exact": [
                "UBER", "OLA", "RAPIDO", "PETROL", "DIESEL", "FUEL",
                "IOCL", "BPCL", "HPCL", "INDIAN OIL", "BHARAT PETROLEUM",
                "IRCTC", "RAILWAY", "METRO", "TOLL", "FASTAG", "PARKING",
                "REDBUS", "MAKEMYTRIP", "GOIBIBO", "YATRA", "CLEARTRIP",
                "INDIGO", "SPICEJET", "AIRINDIA", "VISTARA", "AKASA",
            ],
            "patterns": [
                r"UPI/P2M.*UBER.*",
                r"UPI/P2M.*OLA.*",
                r"UPI/P2M.*IRCTC.*",
                r"FASTAG.*",
            ],
        },
        "Bill Payment": {
            "exact": [
                "ELECTRICITY", "WATER", "GAS", "BROADBAND", "MOBILE",
                "RECHARGE", "AIRTEL", "JIO", "VI", "BSNL", "ACT",
                "TATA SKY", "DISH", "HATHWAY",
                "PHARMACY", "APOLLO", "MEDPLUS", "NETMEDS", "PHARMEASY",
                "1MG", "TATA 1MG", "HOSPITAL", "CLINIC", "DIAGNOSTIC",
                "THYROCARE", "METROPOLIS", "DR LAL", "PRACTO",
                "GST", "CBDT", "TDS", "INCOME TAX",
            ],
            "patterns": [
                r"BILL.*PAYMENT.*",
                r".*RECHARGE.*",
                r"MOBILE.*BILL.*",
                r".*ELECTRICITY.*BILL.*",
                r".*PHARMACY.*",
                r".*HOSPITAL.*",
            ],
        },
        "Entertainment": {
            "exact": [
                "NETFLIX", "AMAZON PRIME", "HOTSTAR", "DISNEY", "SONYLIV",
                "ZEE5", "VOOT", "ALTBALAJI", "SPOTIFY", "GAANA", "WYNK",
                "APPLE MUSIC", "YOUTUBE", "PLAYSTATION", "XBOX", "STEAM",
                "GOOGLE PLAY", "APP STORE",
            ],
            "patterns": [
                r"UPI/P2M.*NETFLIX.*",
                r"PRIME.*MEMBER.*",
                r"HOTSTAR.*PREMIUM.*",
            ],
        },
        "Loan Payments": {
            "exact": [
                "EMI", "LOAN", "BAJAJ FINANCE", "HOME LOAN", "CAR LOAN",
                "PERSONAL LOAN", "LIC HOUSING", "HDFC HOME LOAN",
                "ICICI HOME LOAN",
            ],
            "patterns": [
                r"ACH-DR-.*",           # Axis mandate debit
                r"ACH-DR-LIC.*",        # LIC Housing mandate
                r"EMI.*DEBIT.*",
                r"LOAN.*REPAYMENT.*",
                r".*EMI.*\d+/\d+.*",
                r"NACH.*DEBIT.*",
                r"ECS.*DEBIT.*",
            ],
        },
        "Credit Card Payment": {
            "exact": [
                "CREDITCARD PAYMENT", "CREDIT CARD PAYMENT",
                "CC PAYMENT", "CCPAYMENT",
            ],
            "patterns": [
                r"CreditCard\s*Payment.*",
                r"Credit\s*Card\s*Payment.*",
                r"CC\s*PAYMENT.*",
                r".*Ref#[A-Z0-9]{10,}.*",   # CC payment reference
            ],
        },
        "Transfer": {
            "exact": [
                "NEFT", "RTGS", "IMPS", "UPI", "TRANSFER", "TRF",
            ],
            "patterns": [
                r"NEFT.*DR.*",
                r"RTGS.*DR.*",
                r"IMPS/P2A.*",
                r"IMPS/P2M.*",
                r"UPI/P2A.*",
                r"UPI/P2M.*",
            ],
        },
    }

    CREDIT_RULES = {
        "Salary Credits": {
            "exact": [
                "SALARY", "SAL", "PAYROLL", "WAGES", "STIPEND",
            ],
            "patterns": [
                r"SALARY.*CR.*",
                r"SAL.*CREDIT.*",
                r"PAYROLL.*",
                r".*SALARY.*",
            ],
        },
        "Loan": {
            "exact": [
                "LIC HOUSING", "HOME LOAN CREDIT", "LOAN DISBURSAL",
            ],
            "patterns": [
                r"LOAN.*CREDIT.*",
                r"DISBURS.*",
            ],
        },
        "Interest": {
            "exact": [
                "INTEREST", "INT", "INT.PD", "INTPD", "INT PAID",
                "CREDIT INTEREST",
            ],
            "patterns": [
                r"INTEREST.*CREDIT.*",
                r".*INTEREST.*",
            ],
        },
        "Refund": {
            "exact": [
                "REFUND", "REVERSAL", "CASHBACK", "CASH BACK",
                "NEFT RETURN", "ACH RETURN",
            ],
            "patterns": [
                r"REFUND.*",
                r".*REVERSAL.*",
                r".*CASHBACK.*",
                r"NEFT.*RETURN.*",
                r"ACH.*RETURN.*",
            ],
        },
        "Bank Transfer In": {
            "exact": [
                "NEFT CR", "RTGS CR", "IMPS CR", "NEFTCR", "RTGSCR",
            ],
            "patterns": [
                r"IMPS/P2A.*",           # IMPS credit to account
                r"NEFT.*CR.*",
                r"RTGS.*CR.*",
                r"UPI/P2A.*",            # UPI credit to account
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
        "paytm": "Others Debit",
        "phonepe": "Others Debit",
        "gpay": "Others Debit",
    }

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._compile_patterns()

    def _compile_patterns(self):
        self._debit_compiled = {}
        for cat, rules in self.DEBIT_RULES.items():
            self._debit_compiled[cat] = {
                "exact": set(kw.upper() for kw in rules.get("exact", [])),
                "patterns": [re.compile(p, re.IGNORECASE) for p in rules.get("patterns", [])],
            }

        self._credit_compiled = {}
        for cat, rules in self.CREDIT_RULES.items():
            self._credit_compiled[cat] = {
                "exact": set(kw.upper() for kw in rules.get("exact", [])),
                "patterns": [re.compile(p, re.IGNORECASE) for p in rules.get("patterns", [])],
            }

    def classify(
        self,
        transactions: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Classify all transactions. Returns (classified, unclassified)."""
        classified = []
        unclassified = []

        for txn in transactions:
            result = self._classify_single(txn)
            txn_copy = dict(txn)
            txn_copy["category"] = result.category
            txn_copy["confidence"] = result.confidence
            txn_copy["source"] = result.source
            txn_copy["matched_rule"] = result.matched_rule

            if result.category.startswith("Others"):
                unclassified.append(txn_copy)
            else:
                classified.append(txn_copy)

        self.logger.info(
            "Classification: %d classified, %d unclassified",
            len(classified), len(unclassified)
        )
        return classified, unclassified

    def _classify_single(self, txn: Dict[str, Any]) -> ClassificationResult:
        description = (txn.get("description") or "").upper()
        is_debit = txn.get("debit") is not None and txn.get("debit", 0) > 0

        rules = self._debit_compiled if is_debit else self._credit_compiled
        default_category = "Others Debit" if is_debit else "Others Credit"

        # Layer 1: Exact keyword match
        for category, compiled in rules.items():
            for keyword in compiled["exact"]:
                if keyword in description:
                    return ClassificationResult(
                        category=category,
                        confidence=self.CONF_EXACT,
                        source="rule_engine",
                        matched_rule="exact_keyword",
                        matched_keyword=keyword,
                    )

        # Layer 2: Pattern match
        for category, compiled in rules.items():
            for pattern in compiled["patterns"]:
                if pattern.search(description):
                    return ClassificationResult(
                        category=category,
                        confidence=self.CONF_PATTERN,
                        source="rule_engine",
                        matched_rule="pattern_match",
                        matched_keyword=pattern.pattern,
                    )

        # Layer 3: UPI merchant detection (debits only)
        if is_debit:
            upi_result = self._classify_upi(description)
            if upi_result:
                return upi_result

        return ClassificationResult(
            category=default_category,
            confidence=0.5,
            source="rule_engine",
            matched_rule="default",
        )

    def _classify_upi(self, description: str) -> Optional[ClassificationResult]:
        desc_lower = description.lower()
        if "upi" not in desc_lower:
            return None
        for merchant, category in self.UPI_MERCHANTS.items():
            if merchant in desc_lower:
                return ClassificationResult(
                    category=category,
                    confidence=self.CONF_UPI,
                    source="rule_engine",
                    matched_rule="upi_merchant",
                    matched_keyword=merchant,
                )
        return None

    def get_statistics(self) -> Dict[str, Any]:
        debit_rules = sum(
            len(r["exact"]) + len(r["patterns"])
            for r in self._debit_compiled.values()
        )
        credit_rules = sum(
            len(r["exact"]) + len(r["patterns"])
            for r in self._credit_compiled.values()
        )
        return {
            "debit_categories": len(self._debit_compiled),
            "credit_categories": len(self._credit_compiled),
            "debit_rules": debit_rules,
            "credit_rules": credit_rules,
            "total_rules": debit_rules + credit_rules,
        }
