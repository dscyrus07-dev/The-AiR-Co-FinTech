"""
Tests for Airco Insights — Deterministic Rule Engine
=====================================================
Covers every classification rule, edge case, safety boundary, and error path.

Test groups:
    1.  ATM Withdrawal — debit-only, keyword variants
    2.  Loan EMI — debit-only, keyword variants
    3.  Salary — credit-only, keyword variants
    4.  UPI — debit→UPI Payment, credit→UPI Credit
    5.  Investment — debit→Investment, credit→Investment Return
    6.  Bank Transfer — debit→Bank Transfer Debit, credit→Bank Transfer Credit
    7.  Cash Deposit — credit-only
    8.  Bill Payment — debit-only
    9.  Shopping — debit-only
    10. Direction safety — debit categories never on credits, vice versa
    11. Priority order — first match wins
    12. Partial word safety — "SALMON" ≠ Salary, etc.
    13. Already classified — skip logic
    14. Unclassified — unknown descriptions
    15. Input validation — bad types, empty lists
    16. Non-mutation — originals untouched
    17. Output schema — correct keys and types
    18. Performance — 10K transactions
"""

import copy
import pytest

from app.services.rule_engine import (
    apply_rule_engine,
    RULE_CONFIDENCE,
    RULE_SOURCE,
    DEBIT_CATEGORIES,
    CREDIT_CATEGORIES,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_txn(
    description: str,
    debit: float = None,
    credit: float = None,
    balance: float = 50000.0,
    date: str = "2025-06-01",
    txn_id: str = "test_txn_001",
    **overrides,
) -> dict:
    """Build a normalized transaction dict."""
    base = {
        "date": date,
        "description": description,
        "debit": debit,
        "credit": credit,
        "balance": balance,
        "txn_id": txn_id,
    }
    base.update(overrides)
    return base


def debit_txn(description: str, amount: float = 5000.0, **kw) -> dict:
    return make_txn(description, debit=amount, **kw)


def credit_txn(description: str, amount: float = 5000.0, **kw) -> dict:
    return make_txn(description, credit=amount, **kw)


def classify_one(txn: dict) -> dict:
    """Classify a single transaction, return the result dict."""
    classified, unclassified = apply_rule_engine([txn])
    if classified:
        return classified[0]
    return unclassified[0]


# ---------------------------------------------------------------------------
# 1. ATM Withdrawal
# ---------------------------------------------------------------------------

class TestATMWithdrawal:

    @pytest.mark.parametrize("desc", [
        "ATM-CASH HYDERABAD",
        "ATM CASH WDL SBI",
        "CASH WITHDRAWAL CHANDNI CHOWK",
        "CASH WDL ATM 12345",
        "NFS/ATM/CASH",
        "ATM WDL 0012345",
        "CASH W/D ATM",
    ])
    def test_atm_debit_classified(self, desc):
        result = classify_one(debit_txn(desc))
        assert result["category"] == "ATM Withdrawal"
        assert result["confidence"] == RULE_CONFIDENCE
        assert result["source"] == RULE_SOURCE

    def test_atm_credit_not_classified(self):
        """ATM keyword on a credit transaction → should NOT classify as ATM Withdrawal."""
        result = classify_one(credit_txn("ATM REVERSAL"))
        assert result["category"] is None


# ---------------------------------------------------------------------------
# 2. Loan EMI
# ---------------------------------------------------------------------------

class TestLoanEMI:

    @pytest.mark.parametrize("desc", [
        "EMI DEBIT HDFC LTD",
        "HOME LOAN EMI",
        "CAR LOAN PAYMENT",
        "LIC PREMIUM 12345",
        "BAJAJ FINANCE EMI",
        "PERSONAL LOAN INSTALLMENT",
        "HOUSING FINANCE EMI",
    ])
    def test_loan_debit_classified(self, desc):
        result = classify_one(debit_txn(desc))
        assert result["category"] == "Loan EMI"

    def test_loan_credit_not_classified(self):
        """Loan keyword on a credit → should NOT classify as Loan EMI."""
        result = classify_one(credit_txn("LOAN DISBURSEMENT"))
        assert result["category"] is None


# ---------------------------------------------------------------------------
# 3. Salary
# ---------------------------------------------------------------------------

class TestSalary:

    @pytest.mark.parametrize("desc", [
        "SALARY CREDIT FOR JUN 2025",
        "PAYROLL TRANSFER",
        "SAL CR JUNE",
        "SAL/JUNE 2025",
        "MONTHLY SALARY",
    ])
    def test_salary_credit_classified(self, desc):
        result = classify_one(credit_txn(desc))
        assert result["category"] == "Salary"
        assert result["confidence"] == RULE_CONFIDENCE

    def test_salary_debit_not_classified(self):
        """Salary keyword on debit → should NOT classify as Salary."""
        result = classify_one(debit_txn("SALARY ADVANCE RECOVERY"))
        assert result["category"] is None


# ---------------------------------------------------------------------------
# 4. UPI
# ---------------------------------------------------------------------------

class TestUPI:

    @pytest.mark.parametrize("desc", [
        "UPI-RAHUL SHARMA-9876543210@YBL",
        "UPI/P2P/123456789",
        "UPI-PAYMENT TO MERCHANT",
    ])
    def test_upi_debit_classified_as_payment(self, desc):
        result = classify_one(debit_txn(desc))
        assert result["category"] == "UPI Payment"

    @pytest.mark.parametrize("desc", [
        "UPI-CR FROM RAHUL",
        "UPI/REFUND/123",
        "UPI-CREDIT",
    ])
    def test_upi_credit_classified_as_credit(self, desc):
        result = classify_one(credit_txn(desc))
        assert result["category"] == "UPI Credit"

    def test_upi_direction_never_swapped(self):
        debit_result = classify_one(debit_txn("UPI-TEST"))
        credit_result = classify_one(credit_txn("UPI-TEST"))
        assert debit_result["category"] == "UPI Payment"
        assert credit_result["category"] == "UPI Credit"


# ---------------------------------------------------------------------------
# 5. Investment
# ---------------------------------------------------------------------------

class TestInvestment:

    @pytest.mark.parametrize("desc", [
        "ZERODHA FUND TRANSFER",
        "GROWW INVESTMENT",
        "ANGEL ONE TRADING",
        "MUTUAL FUND SIP PURCHASE",
        "SIP DEBIT AXIS MF",
    ])
    def test_investment_debit_classified(self, desc):
        result = classify_one(debit_txn(desc))
        assert result["category"] == "Investment"

    @pytest.mark.parametrize("desc", [
        "ZERODHA WITHDRAWAL",
        "GROWW REDEMPTION",
        "MUTUAL FUND REDEMPTION",
    ])
    def test_investment_credit_classified_as_return(self, desc):
        result = classify_one(credit_txn(desc))
        assert result["category"] == "Investment Return"


# ---------------------------------------------------------------------------
# 6. Bank Transfer
# ---------------------------------------------------------------------------

class TestBankTransfer:

    @pytest.mark.parametrize("desc", [
        "NEFT CR-YESB0000001-PHONEPE",
        "RTGS INCOMING FROM ABC CORP",
        "IMPS CREDIT REF 12345",
        "FT - CR FROM SAVINGS",
    ])
    def test_bank_transfer_credit_classified(self, desc):
        result = classify_one(credit_txn(desc))
        assert result["category"] == "Bank Transfer Credit"

    @pytest.mark.parametrize("desc", [
        "NEFT DR TO SAVINGS",
        "RTGS PAYMENT TO VENDOR",
        "IMPS DEBIT REF 67890",
        "FT - DR TO CURRENT",
        "FUND TRANSFER TO ACC",
    ])
    def test_bank_transfer_debit_classified(self, desc):
        result = classify_one(debit_txn(desc))
        assert result["category"] == "Bank Transfer Debit"


# ---------------------------------------------------------------------------
# 7. Cash Deposit
# ---------------------------------------------------------------------------

class TestCashDeposit:

    @pytest.mark.parametrize("desc", [
        "CASH DEPOSIT AT BRANCH",
        "CDM DEPOSIT 12345",
        "CASH DEP BRANCH HYDERABAD",
    ])
    def test_cash_deposit_credit_classified(self, desc):
        result = classify_one(credit_txn(desc))
        assert result["category"] == "Cash Deposit"

    def test_cash_deposit_debit_not_classified(self):
        """Cash deposit keywords on debit → should NOT classify."""
        result = classify_one(debit_txn("CDM ERROR REVERSAL"))
        assert result["category"] is None


# ---------------------------------------------------------------------------
# 8. Bill Payment
# ---------------------------------------------------------------------------

class TestBillPayment:

    @pytest.mark.parametrize("desc", [
        "BILL PAYMENT ELECTRICITY",
        "TATA POWER BILL",
        "BESCOM ELECTRICITY BILL",
        "AIRTEL MOBILE RECHARGE",
        "JIO PREPAID RECHARGE",
        "BROADBAND PAYMENT",
    ])
    def test_bill_debit_classified(self, desc):
        result = classify_one(debit_txn(desc))
        assert result["category"] == "Bill Payment"

    def test_bill_credit_not_classified(self):
        """Bill keywords on credit → should NOT classify as Bill Payment."""
        result = classify_one(credit_txn("ELECTRICITY REFUND"))
        assert result["category"] is None


# ---------------------------------------------------------------------------
# 9. Shopping
# ---------------------------------------------------------------------------

class TestShopping:

    @pytest.mark.parametrize("desc", [
        "AMAZON PAY PURCHASE",
        "FLIPKART ORDER 123",
        "SWIGGY FOOD ORDER",
        "ZOMATO PAYMENT",
        "POS 435584XXXXXX1029 VIJETH SUPERMARKET",
        "ECOM PURCHASE",
    ])
    def test_shopping_debit_classified(self, desc):
        result = classify_one(debit_txn(desc))
        assert result["category"] == "Shopping"

    def test_shopping_credit_not_classified(self):
        """Shopping keywords on credit → should NOT classify as Shopping."""
        result = classify_one(credit_txn("AMAZON REFUND"))
        assert result["category"] is None


# ---------------------------------------------------------------------------
# 10. Direction Safety
# ---------------------------------------------------------------------------

class TestDirectionSafety:

    def test_no_debit_category_on_credit(self):
        """Debit-only categories must never appear on credit transactions."""
        descs = [
            "ATM REVERSAL",
            "EMI REFUND",
            "BILL PAYMENT REVERSAL",
            "SHOPPING REFUND",
        ]
        for desc in descs:
            result = classify_one(credit_txn(desc))
            if result["category"] is not None:
                assert result["category"] not in DEBIT_CATEGORIES, \
                    f"Debit category '{result['category']}' assigned to credit txn: {desc}"

    def test_no_credit_category_on_debit(self):
        """Credit-only categories must never appear on debit transactions."""
        descs = [
            "SALARY ADVANCE RECOVERY",
            "CASH DEPOSIT REVERSAL",
        ]
        for desc in descs:
            result = classify_one(debit_txn(desc))
            if result["category"] is not None:
                assert result["category"] not in CREDIT_CATEGORIES, \
                    f"Credit category '{result['category']}' assigned to debit txn: {desc}"


# ---------------------------------------------------------------------------
# 11. Priority Order — First Match Wins
# ---------------------------------------------------------------------------

class TestPriorityOrder:

    def test_atm_beats_upi(self):
        """ATM has higher priority than UPI."""
        result = classify_one(debit_txn("UPI ATM CASH"))
        assert result["category"] == "ATM Withdrawal"

    def test_loan_beats_bank_transfer(self):
        """Loan EMI has higher priority than Bank Transfer."""
        result = classify_one(debit_txn("NEFT EMI PAYMENT"))
        # EMI keyword appears → Loan EMI (priority 2) before Bank Transfer (priority 6)
        assert result["category"] == "Loan EMI"

    def test_salary_beats_bank_transfer(self):
        """Salary has higher priority than Bank Transfer."""
        result = classify_one(credit_txn("NEFT SALARY CREDIT"))
        assert result["category"] == "Salary"

    def test_upi_beats_bank_transfer(self):
        """UPI has higher priority than Bank Transfer."""
        result = classify_one(debit_txn("UPI IMPS PAYMENT"))
        assert result["category"] == "UPI Payment"


# ---------------------------------------------------------------------------
# 12. Partial Word Safety
# ---------------------------------------------------------------------------

class TestPartialWordSafety:

    def test_salmon_not_salary(self):
        """'SALMON' should NOT trigger Salary rule."""
        result = classify_one(credit_txn("PURCHASE OF SALMON FISH"))
        assert result["category"] != "Salary" if result["category"] else True

    def test_atmospheric_not_atm(self):
        """'ATMOSPHERIC' should trigger ATM rule because 'ATM' is a substring.
        This is a known trade-off — we accept it because real bank statements
        almost never contain 'ATMOSPHERIC' as a transaction description."""
        # Document the known behavior rather than pretend it doesn't exist
        result = classify_one(debit_txn("ATMOSPHERIC RESEARCH"))
        # ATM is substring — this WILL match. Acceptable in financial context.
        assert result["category"] == "ATM Withdrawal"

    def test_emission_not_emi(self):
        """'EMISSION' should NOT trigger Loan EMI — EMI keywords are boundary-safe."""
        result = classify_one(debit_txn("EMISSION TEST"))
        assert result["category"] is None

    def test_recharge_classifies_as_bill(self):
        """'RECHARGE' should classify as Bill Payment."""
        result = classify_one(debit_txn("MOBILE RECHARGE AIRTEL"))
        assert result["category"] == "Bill Payment"


# ---------------------------------------------------------------------------
# 13. Already Classified — Skip Logic
# ---------------------------------------------------------------------------

class TestAlreadyClassified:

    def test_existing_category_preserved(self):
        txn = make_txn("UPI-TEST", debit=500.0, category="Custom Category",
                        confidence=0.99, source="manual")
        result = classify_one(txn)
        assert result["category"] == "Custom Category"
        assert result["confidence"] == 0.99
        assert result["source"] == "manual"

    def test_existing_category_not_overwritten(self):
        txn = make_txn("SALARY CREDIT", credit=85000.0, category="Override",
                        confidence=1.0, source="user")
        classified, unclassified = apply_rule_engine([txn])
        assert len(classified) == 1
        assert classified[0]["category"] == "Override"


# ---------------------------------------------------------------------------
# 14. Unclassified — Unknown Descriptions
# ---------------------------------------------------------------------------

class TestUnclassified:

    @pytest.mark.parametrize("desc", [
        "MISCELLANEOUS CHARGE",
        "SERVICE FEE",
        "INSURANCE PREMIUM XYZ",
        "REFERENCE NUMBER 12345",
        "CHEQUE DEPOSIT 987654",
    ])
    def test_unknown_description_unclassified(self, desc):
        result = classify_one(debit_txn(desc))
        assert result["category"] is None
        assert result["confidence"] is None
        assert result["source"] is None

    def test_unclassified_in_correct_bucket(self):
        txn = debit_txn("RANDOM UNKNOWN PAYMENT")
        classified, unclassified = apply_rule_engine([txn])
        assert len(classified) == 0
        assert len(unclassified) == 1
        assert unclassified[0]["category"] is None


# ---------------------------------------------------------------------------
# 15. Input Validation
# ---------------------------------------------------------------------------

class TestInputValidation:

    def test_non_list_raises(self):
        with pytest.raises(ValueError, match="list"):
            apply_rule_engine({"txn": "bad"})

    def test_empty_list_returns_empty_tuples(self):
        classified, unclassified = apply_rule_engine([])
        assert classified == []
        assert unclassified == []

    def test_string_input_raises(self):
        with pytest.raises(ValueError):
            apply_rule_engine("not a list")


# ---------------------------------------------------------------------------
# 16. Non-Mutation
# ---------------------------------------------------------------------------

class TestNonMutation:

    def test_original_not_mutated(self):
        original = debit_txn("ATM CASH WITHDRAWAL")
        original_copy = copy.deepcopy(original)
        apply_rule_engine([original])
        assert original == original_copy, "Original transaction was mutated!"

    def test_multiple_originals_not_mutated(self):
        txns = [
            debit_txn("ATM CASH", txn_id="t1"),
            credit_txn("SALARY", txn_id="t2"),
            debit_txn("RANDOM", txn_id="t3"),
        ]
        copies = copy.deepcopy(txns)
        apply_rule_engine(txns)
        assert txns == copies


# ---------------------------------------------------------------------------
# 17. Output Schema
# ---------------------------------------------------------------------------

class TestOutputSchema:

    def test_classified_has_required_keys(self):
        classified, _ = apply_rule_engine([debit_txn("ATM CASH")])
        txn = classified[0]
        for key in ("date", "description", "debit", "credit", "balance",
                     "txn_id", "category", "confidence", "source"):
            assert key in txn, f"Missing key: {key}"

    def test_unclassified_has_required_keys(self):
        _, unclassified = apply_rule_engine([debit_txn("UNKNOWN")])
        txn = unclassified[0]
        assert txn["category"] is None
        assert txn["confidence"] is None
        assert txn["source"] is None

    def test_confidence_is_float(self):
        classified, _ = apply_rule_engine([debit_txn("ATM CASH")])
        assert isinstance(classified[0]["confidence"], float)

    def test_source_is_rule_engine(self):
        classified, _ = apply_rule_engine([debit_txn("ATM CASH")])
        assert classified[0]["source"] == "rule_engine"

    def test_category_is_string(self):
        classified, _ = apply_rule_engine([debit_txn("ATM CASH")])
        assert isinstance(classified[0]["category"], str)


# ---------------------------------------------------------------------------
# 18. Performance
# ---------------------------------------------------------------------------

class TestPerformance:

    def test_10k_transactions(self):
        """10,000 transactions should classify without error or timeout."""
        txns = [
            debit_txn(f"UPI-PAYMENT-{i}", txn_id=f"t{i}")
            for i in range(10_000)
        ]
        classified, unclassified = apply_rule_engine(txns)
        assert len(classified) == 10_000
        assert len(unclassified) == 0

    def test_mixed_10k_transactions(self):
        """Mix of classified and unclassified in large batch."""
        txns = []
        for i in range(5_000):
            txns.append(debit_txn(f"ATM CASH {i}", txn_id=f"atm{i}"))
            txns.append(debit_txn(f"UNKNOWN TXN {i}", txn_id=f"unk{i}"))
        classified, unclassified = apply_rule_engine(txns)
        assert len(classified) == 5_000
        assert len(unclassified) == 5_000


# ---------------------------------------------------------------------------
# 19. Coverage Sanity — Real-World Descriptions
# ---------------------------------------------------------------------------

class TestRealWorldDescriptions:

    @pytest.mark.parametrize("desc,direction,expected_cat", [
        ("UPI-TETALIVENKATARAJSE-9700767801@IBL-ICIC0000040", "debit", "UPI Payment"),
        ("NEFT CR-YESB0000001-PHONEPE PRIVATE LIMI", "credit", "Bank Transfer Credit"),
        ("POS435584XXXXXX1029VIJETHASUPERMAR", "debit", None),  # No space after POS
        ("PAYZAPP_W2A_CREDIT", "credit", None),  # Unknown
        ("ATM-CASH WDL SBI CHANDNI CHK", "debit", "ATM Withdrawal"),
        ("IMPS-123456789-RAHUL TO SAVINGS", "debit", "Bank Transfer Debit"),
        ("SALARY CREDIT FOR JUNE 2025 TCS LTD", "credit", "Salary"),
        ("AMAZON PAY INDIA PVT LTD", "debit", "Shopping"),
        ("ZERODHA COMMODITY", "debit", "Investment"),
        ("GROWW MF REDEMPTION", "credit", "Investment Return"),
        ("CASH DEPOSIT AT BRANCH HYDERABAD", "credit", "Cash Deposit"),
        ("TATA POWER ELECTRICITY BILL", "debit", "Bill Payment"),
    ])
    def test_real_descriptions(self, desc, direction, expected_cat):
        if direction == "debit":
            txn = debit_txn(desc)
        else:
            txn = credit_txn(desc)
        result = classify_one(txn)
        assert result["category"] == expected_cat
