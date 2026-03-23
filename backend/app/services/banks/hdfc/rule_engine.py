"""
Airco Insights — HDFC Rule Engine
==================================
Deterministic classification engine for HDFC transactions.
Bank-specific rules optimized for HDFC statement patterns.

Classification Hierarchy:
1. Exact keyword match (confidence 0.99)
2. Pattern match (confidence 0.95)
3. Merchant mapping (confidence 0.90)
4. UPI pattern (confidence 0.85)
5. Amount-based heuristics (confidence 0.70)

Categories:
- Debit: ATM, Shopping, Food, Transport, Bills, Entertainment, Health, Education, Investment, Transfer, EMI, Others Debit
- Credit: Salary, Interest, Refund, Cashback, Investment Return, Transfer, Others Credit

Design: Deterministic first, AI is last resort.
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


class HDFCRuleEngine:
    """
    HDFC-specific deterministic rule engine.
    """
    
    # Confidence levels
    CONF_EXACT = 0.99
    CONF_PATTERN = 0.95
    CONF_MERCHANT = 0.90
    CONF_UPI = 0.85
    CONF_AMOUNT = 0.70
    
    # ==========================================================================
    # DEBIT RULES - HDFC Specific
    # ==========================================================================
    
    DEBIT_RULES = {
        # ATM Withdrawals
        "ATM Withdrawal": {
            "exact": [
                "ATW", "ATM WDL", "ATM CASH", "ATMWDL", "ATM/CASH",
                "CASH WITHDRAWAL", "ATM-WDL", "NFS ATM", "CASHWITHDRAWAL",
            ],
            "patterns": [
                r"ATW-\d+",
                r"ATM.*WDL",
                r"CASH\s*W/D",
                r"NFS.*ATM",
            ],
        },
        
        # Withdrawals & Self Transfers
        "Withdrawal": {
            "exact": [
                "JARIKOWORLD", "ROHIT ENTERPRISES", "JMD ENTERPRISES", 
                "NK ENTERPRISES", "VISHAL INTERNATIONAL", "DEEPAK ENTERPRISES",
                "PRIYANSHI", "VIKASH TRADING", "WINTAGGLOBAL", "RITHUM ENTERPRISES",
                "KINDBURY", "WINTOY", "ROMAXES", "JJ ENTERPRISES", "AS ENTERPRISES",
                "UMESH TRADING", "HOBBY TRADING", "DELIGHT TRADERS", "NOMINEXTRADE",
                "KUSHWAHA", "SHARMA ENTERPRISES", "EJINICONNECTIONS", "TARITECH",
                "SELF-CHQPAID", "SELF-CHQ", "CHQPAID",
                "SAMEERHOTELS", "SAMEERGIFTCORNER", "HOTELSUPPLIES",
            ],
            "patterns": [
                r"IMPS.*SELF",
                r"RTGS DR.*SELF",
                r"NEFT DR.*SELF",
                r".*ENTERPRISES.*",
                r".*TRADING.*",
                r"SELF-CHQPAID.*",
                r"TPT-PAYMENT.*",
                r"TPT-DEC.*",
                r"TPT-SALARY.*",
                r"TPT-ADVANCESALARY.*",
                r"TPT-PAY.*",
                r"TPT-TRAVELINGFARE.*",
                r"TPT-COMMISSION.*",
                r"TPT-ADVSALARY.*",
                r"TPT-BILL.*",
                r"TPT-DUEBILL.*",
                r"CHQPAID-CTSS.*",
                r"CHQPAID-MICRCTS.*",
                r"CHQPAID.*",
                r"TPT-SAMEERHOTELS.*",
                r"TPT-SAMEERGIFTCORNER.*",
                r"TPT-SAMEERGIFTCOR.*",
                r"TPT-COFEEMACHINE.*",
                r"TPT-INVNO.*",
                r"TPT-FUNDTRANSFAR.*",
                r"TPT-CROCKERYPAYMENT.*",
                r"TPT-TAPROOTHOSPAUDITOR.*",
                r"TPT-REPAIRPAYMENT.*",
                r"TPT-AUDITING.*",
                r"TPT-ADVENCEPAYMENT.*",
                r"TPT-TRASFER.*",
                r"TPT-\d+.*",
                r"TPT-RENTDEPOSIT.*",
            ],
        },
        
        # Food & Dining
        "Food": {
            "exact": [
                "SWIGGY", "ZOMATO", "DOMINOS", "MCDONALDS", "KFC", "BURGER",
                "PIZZA", "PIZZAHUT", "SUBWAY", "STARBUCKS", "CCD", "CAFE",
                "RESTAURANT", "FOOD", "DINING", "EATERY", "BIRYANI",
                "HALDIRAM", "BARBEQUE", "CHAAYOS", "FAASOS", "FRESHMENU",
                "REBEL FOODS", "JUBILANT", "DUNKIN", "BASKIN", "KEVENTERS",
            ],
            "patterns": [
                r"SWIGGY.*INSTAMART",
                r"ZOMATO.*ORDER",
                r"FOOD.*PANDA",
                r"UBER.*EATS",
            ],
        },
        
        # Shopping
        "Shopping": {
            "exact": [
                "AMAZON", "FLIPKART", "MYNTRA", "AJIO", "NYKAA", "MEESHO",
                "SNAPDEAL", "TATACLIQ", "RELIANCE", "DMART", "BIGBASKET",
                "GROFERS", "BLINKIT", "ZEPTO", "INSTAMART", "JIOMART",
                "DECATHLON", "IKEA", "SHOPPERS STOP", "LIFESTYLE", "WESTSIDE",
                "PANTALOONS", "MAX", "ZARA", "H&M", "MINISO", "CROMA",
                "VIJAY SALES", "RELIANCE DIGITAL", "POORVIKA", "SANGEETHA",
                "ADITYA BIRLA FASHION", "NITU CLOTHES", "SMART TS", "VIJETHA SUPERMAR",
                "BEEJAPURI DAIRY", "MAPLE TOWN", "TEJ TIFFEN", "TEA TIME", "DESI TEA",
                "RAZORPAY", "EASEMYTRIP", "EASETRIP",
                "IBIBOWEBPRIVAT", "ATHARVASWEETS", "CYBASEINDIA",
            ],
            "patterns": [
                r"AMAZON.*PAY",
                r"FLIPKART.*INTERNET",
                r"AMZN.*MKTP",
                r"POS.*\d+.*VIJETHA",
                r".*SUPERMAR.*",
                r"WWW\..*\.COM",
                r".*/RAZPE.*",
                r".*RAZORPAY.*",
                r"POS.*EASYTRIPPLANNE.*",
                r"POS.*IBIBOWEBPRIVAT.*",
                r"POS.*ATHARVASWEETS.*",
                r"POS.*RAZ\*CYBASE.*",
                r".*TERMINALDACVT.*",
            ],
        },
        
        # Transport
        "Transport": {
            "exact": [
                "UBER", "OLA", "RAPIDO", "PETROL", "DIESEL", "FUEL",
                "IOCL", "BPCL", "HPCL", "INDIAN OIL", "BHARAT PETROLEUM",
                "IRCTC", "RAILWAY", "METRO", "TOLL", "FASTAG", "PARKING",
                "REDBUS", "MAKEMYTRIP", "GOIBIBO", "YATRA", "CLEARTRIP",
                "INDIGO", "SPICEJET", "AIRINDIA", "VISTARA", "AKASA",
                "IBIBOGROUP",
            ],
            "patterns": [
                r"UBER.*TRIP",
                r"OLA.*CAB",
                r"IRCTC.*TICKET",
                r"TOLL.*PLAZA",
                r"FASTAG.*RECHARGE",
                r"MAKEMYTRIPIND.*",
                r"POS.*IBIBOGROUP.*",
                r"POS.*REDBUS.*",
            ],
        },
        
        # Bills & Utilities
        "Bill Payment": {
            "exact": [
                "ELECTRICITY", "WATER", "GAS", "BROADBAND", "MOBILE",
                "RECHARGE", "BILL PAYMENT", "AIRTEL", "JIO", "VI", "BSNL",
                "ACT", "TATA SKY", "DISH", "HATHWAY", "DEN", "VIDEOCON",
                "PVR", "INOX", "CINEPOLIS", "AAA CINEMAS", "IRCTC", "OYO",
                "METRO", "JIOIN", "FLEXSALARY",
                "PHARMACY", "APOLLO", "MEDPLUS", "NETMEDS", "PHARMEASY",
                "1MG", "TATA 1MG", "HOSPITAL", "CLINIC", "DIAGNOSTIC",
                "LAB", "THYROCARE", "METROPOLIS", "DR LAL", "SRL",
                "PRACTO", "DOCTOR", "MEDICAL", "HEALTH", "WELLNESS",
                "ADITYA PHARMACY", "ADITYAPHARMACY", "CRAYONS HOSPITAL",
                "HOMEOPAT", "DOCTORC", "LICIOUS",
                "GST", "CBDT", "TDS", "INCOME TAX",
                "SETTLEMENTCHARGE", "LOWUSAGECHARGES", "EDC RENTAL", "EDCRENTAL",
                "MEDCSI", "YANOLJA", "RAZ*YANOLJA",
                "ADANIELECTR", "PUBLICWORKSDEPARTME", "FEE-ATMCASH",
                "EGOVGOASBIEPAY", "EGOV",
            ],
            "patterns": [
                r"BILL.*PAYMENT",
                r".*RECHARGE.*",
                r"MOBILE.*BILL",
                r".*CINEMA.*",
                r".*METRO.*",
                r"APOLLO.*PHARMACY",
                r"HEALTH.*INSURANCE",
                r"MEDICAL.*BILL",
                r".*PHARMACY.*",
                r".*HOSPITAL.*",
                r"GST/BANKREFERENCENO.*",
                r"CBDT/BANKREFERENCENO.*",
                r".*TAX.*PAYMENT.*",
                r"SETTLEMENTCHARGE.*",
                r"LOWUSAGECHARGES.*",
                r"EDCRENTAL.*",
                r"EDC.*RENTAL.*",
                r"MEDCSI.*RAZ.*",
                r"RAZ\*YANOLJA.*",
                r".*ADANIELECTR.*BILLPAY.*",
                r".*PUBLICWORKSDEPARTME.*",
                r"FEE-ATMCASH.*",
                r"POS.*EGOVGOASBIEPAY.*",
                r"POS.*EGOV.*",
            ],
        },
        
        # Entertainment
        "Entertainment": {
            "exact": [
                "NETFLIX", "AMAZON PRIME", "HOTSTAR", "DISNEY", "SONYLIV",
                "ZEE5", "VOOT", "ALTBALAJI", "EROS", "MX PLAYER",
                "SPOTIFY", "GAANA", "WYNK", "APPLE MUSIC", "YOUTUBE",
                "PLAYSTATION", "XBOX", "STEAM", "GOOGLE PLAY", "APP STORE",
            ],
            "patterns": [
                r"NETFLIX.*SUBSCRIPTION",
                r"PRIME.*MEMBER",
                r"HOTSTAR.*PREMIUM",
            ],
        },
        
        # Education
        "Education": {
            "exact": [
                "SCHOOL", "COLLEGE", "UNIVERSITY", "TUITION", "COACHING",
                "BYJU", "UNACADEMY", "VEDANTU", "UDEMY", "COURSERA",
                "UPGRAD", "SIMPLILEARN", "GREAT LEARNING", "SCALER",
                "EXAM", "FEES", "EDUCATION", "BOOKS", "STATIONERY",
            ],
            "patterns": [
                r"SCHOOL.*FEES",
                r"TUITION.*FEE",
                r"COLLEGE.*FEE",
            ],
        },
        
        # EMI & Loans
        "Loan Payments": {
            "exact": [
                "EMI", "LOAN", "BAJAJ FINANCE", "HDFC LTD", "HOME LOAN",
                "CAR LOAN", "PERSONAL LOAN", "CREDIT CARD", "CC PAYMENT",
                "VIVIFI", "NAVI FINSERV", "GOLDEN LEGAND", "RAZPCREDCLUB",
                "IBG ECHIT", "MYPAISAA", "HEROFINCORP", "FEDBANKFINANCIAL",
                "CC000", "AUTOPAYSI",
            ],
            "patterns": [
                r"EMI.*DEBIT",
                r"LOAN.*REPAYMENT",
                r".*EMI.*\d+/\d+",
                r"VIVIFI.*FINANCE",
                r"ACHD-.*",
                r"CC000.*AUTOPAYSI.*",
                r"HEROFINCORP.*",
                r"FEDBANKFINANCIAL.*",
            ],
        },
        
        # Investment
        "Investments": {
            "exact": [
                "MUTUAL FUND", "MF", "SIP", "ZERODHA", "GROWW", "UPSTOX",
                "ANGEL", "5PAISA", "KITE", "COIN", "PAYTM MONEY", "ET MONEY",
                "KUVERA", "SCRIPBOX", "FD", "RD", "PPF", "NPS", "EPFO",
                "SUBHAGRUHA", "KONDETI",
            ],
            "patterns": [
                r"SIP.*PURCHASE",
                r"MF.*PURCHASE",
                r"MUTUAL.*FUND",
                r"RTGS DR.*SUBHAGRUHA",
                r"SUBHAGRUHA.*PROJECTS",
                r"CHRE.*EPFO",
                r".*EPFO.*",
            ],
        },
        
        # Transfers
        "Transfer": {
            "exact": [
                "NEFT", "RTGS", "IMPS", "UPI", "TRANSFER", "TRF",
            ],
            "patterns": [
                r"NEFT.*DR",
                r"RTGS.*DR",
                r"IMPS.*DR",
                r"UPI.*DR",
                r"FT.*DR",
            ],
        },
    }
    
    # ==========================================================================
    # CREDIT RULES - HDFC Specific
    # ==========================================================================
    
    CREDIT_RULES = {
        # Salary
        "Salary Credits": {
            "exact": [
                "SALARY", "SAL", "PAYROLL", "WAGES", "STIPEND",
                "TAVANT", "TAVANT TECHNOLOGIES",
            ],
            "patterns": [
                r"SALARY.*CR",
                r"SAL.*CREDIT",
                r"PAYROLL.*",
                r".*SALARY.*",
                r"NEFT CR.*TAVANT.*",
            ],
        },
        
        # Loan Credits
        "Loan": {
            "exact": [
                "LIC HOUSING", "VIVIFI", "HINDUSTAN INST", "HOME LOAN",
            ],
            "patterns": [
                r"LIC HOUSING.*FI",
                r"VIVIFI.*INDIA",
                r"HINDUSTAN.*INST",
            ],
        },
        
        # Interest (mapped to Bank Transfer)
        "Bank Transfer": {
            "exact": [
                "INTEREST", "INT", "INT.PD", "INTPD", "INT PAID",
                "CREDIT INTEREST",
            ],
            "patterns": [
                r"INT\.PD.*",
                r"INTEREST.*CREDIT",
                r".*INTEREST.*",
                r"CREDIT INTEREST.*",
            ],
        },
        
        # Cash Deposit
        "Cash Deposit": {
            "exact": [
                "CASH DEPOSIT", "CASH DEP", "CDM", "CASHDEPOSITBY",
            ],
            "patterns": [
                r"CASH DEPOSIT.*",
                r"CDM.*",
                r"CASHDEPOSITBY.*",
            ],
        },
        
        # Refund
        "Refund": {
            "exact": [
                "REFUND", "REVERSAL", "CASHBACK", "CASH BACK",
                "MAKEMYTRIPIND", "HAIGHTASHBURY", "MORJIMHOTELS",
                "PHONEPE", "PHONEPEPRIVATE", "CASHFREE", "HOTNOTPRIVATE",
                "NEFTRETURN", "SERVICECHARGES", "I/WCHQRET",
            ],
            "patterns": [
                r"REFUND.*CR",
                r".*REFUND.*",
                r".*REVERSAL.*",
                r"MAKEMYTRIPIND.*",
                r"HAIGHTASHBURY.*",
                r"IMPS.*HAIGHTASHBURY.*",
                r".*HOTEL.*",
                r"POS\d+.*",
                r"IMPS.*PHONEPE.*",
                r"CRVPOS-.*",
                r"REV-GED.*",
                r"REV-RELI.*",
                r"NEFTRETURN.*",
                r"NEFT.*RETURN.*",
                r"IMPS.*CASHFREE.*",
                r"IMPS.*HOTNOTPRIVATE.*",
                r"ATW-.*-.*",
                r"SERVICECHARGES-.*",
                r"EDCANNUALRENTAL.*",
                r"I/WCHQRET.*",
                r"LOWUSAGECHARGES-.*",
            ],
        },
        
        # Bank Transfer In
        "Bank Transfer": {
            "exact": [
                "NEFTCR", "NEFT CR", "RTGSCR", "IMPS CR", "TERMINAL1CARDSSETTL",
                "UPISETTLEMENT", "SETTLEMENT",
            ],
            "patterns": [
                r"NEFT CR.*",
                r"RTGS CR.*",
                r"IMPS.*CR.*TETALI.*",
                r"FT.*CR",
                r".*TERMINAL1CARDSSETTL.*",
                r"UPISETTLEMENT.*",
                r"\d+TERMINAL1CARDSSETTL.*",
                r"\d+-TPT-.*HOSTEL.*",
                r".*TPT-TRANSFER.*",
                r"\d+-TPT-.*ZOSTEL.*",
            ],
        },
        
        # UPI Credits
        "UPI": {
            "exact": [],
            "patterns": [
                r"^UPI-.*",
            ],
        },
    }
    
    # UPI Merchant Mapping
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
        """Pre-compile regex patterns for performance."""
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
        """
        Classify all transactions.
        
        Args:
            transactions: List of validated transaction dicts
            
        Returns:
            Tuple of (classified_transactions, unclassified_transactions)
        """
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
            "Classification complete: %d classified, %d unclassified",
            len(classified), len(unclassified)
        )
        
        return classified, unclassified
    
    def _classify_single(self, txn: Dict[str, Any]) -> ClassificationResult:
        """Classify a single transaction."""
        description = (txn.get("description") or "").upper()
        is_debit = txn.get("debit") is not None
        
        # Select appropriate rules
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
        
        # Layer 3: UPI merchant detection (for debits)
        if is_debit:
            upi_result = self._classify_upi(description)
            if upi_result:
                return upi_result
        
        # Layer 4: Amount-based heuristics
        amount = txn.get("debit") or txn.get("credit") or 0
        amount_result = self._classify_by_amount(amount, is_debit, description)
        if amount_result:
            return amount_result
        
        # Default: Others
        return ClassificationResult(
            category=default_category,
            confidence=0.5,
            source="rule_engine",
            matched_rule="default",
        )
    
    def _classify_upi(self, description: str) -> Optional[ClassificationResult]:
        """Classify UPI transactions by merchant."""
        description_lower = description.lower()
        
        # Check for UPI pattern
        if "upi" not in description_lower and "@" not in description_lower:
            return None
        
        # Check merchant mapping
        for merchant, category in self.UPI_MERCHANTS.items():
            if merchant in description_lower:
                return ClassificationResult(
                    category=category,
                    confidence=self.CONF_UPI,
                    source="rule_engine",
                    matched_rule="upi_merchant",
                    matched_keyword=merchant,
                )
        
        return None
    
    def _classify_by_amount(
        self,
        amount: float,
        is_debit: bool,
        description: str
    ) -> Optional[ClassificationResult]:
        """Classify based on amount patterns."""
        
        # ATM typically round numbers
        if is_debit and amount > 0:
            if amount % 100 == 0 and amount >= 500 and amount <= 50000:
                if "ATM" in description.upper() or "ATW" in description.upper():
                    return ClassificationResult(
                        category="ATM",
                        confidence=self.CONF_AMOUNT,
                        source="rule_engine",
                        matched_rule="amount_atm",
                    )
        
        # Small recurring amounts might be subscriptions
        if is_debit and 99 <= amount <= 999:
            if any(kw in description.upper() for kw in ["SUB", "MEMBERSHIP", "PREMIUM"]):
                return ClassificationResult(
                    category="Entertainment",
                    confidence=self.CONF_AMOUNT,
                    source="rule_engine",
                    matched_rule="amount_subscription",
                )
        
        return None
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get rule engine statistics."""
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
            "upi_merchants": len(self.UPI_MERCHANTS),
            "total_rules": debit_rules + credit_rules,
        }
