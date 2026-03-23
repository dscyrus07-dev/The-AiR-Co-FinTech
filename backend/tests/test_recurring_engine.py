"""
Tests for Airco Insights — Recurring Engine (Deterministic Pattern Detection)
==============================================================================
Covers merchant normalization, amount consistency, interval consistency,
recurring detection, non-mutation, edge cases, and performance.

Test groups:
    1.  Merchant key normalization
    2.  Amount consistency
    3.  Interval consistency
    4.  Monthly EMI recurring
    5.  Monthly SIP recurring
    6.  Weekly subscription recurring
    7.  Salary monthly recurring
    8.  Same amount random dates — NOT recurring
    9.  Same merchant varying amount >5% — NOT recurring
    10. Single occurrence — NOT recurring
    11. Non-mutation
    12. Input validation
    13. Output schema
    14. Mixed recurring and non-recurring
    15. Performance (10K rows)
"""

import copy
import pytest
from datetime import datetime, timedelta

from app.services.recurring_engine import (
    detect_recurring,
    normalize_merchant_key,
    _amounts_consistent,
    _intervals_consistent,
    MIN_OCCURRENCES,
    AMOUNT_TOLERANCE_PERCENT,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_txn(
    description: str,
    date: str,
    debit: float = None,
    credit: float = None,
    balance: float = 50000.0,
    category: str = "Others Debit",
    confidence: float = 0.95,
    txn_id: str = "test_001",
) -> dict:
    return {
        "date": date,
        "description": description,
        "debit": debit,
        "credit": credit,
        "balance": balance,
        "category": category,
        "confidence": confidence,
        "txn_id": txn_id,
    }


def monthly_series(
    description: str,
    amount: float,
    start_date: str = "2025-01-05",
    count: int = 3,
    is_debit: bool = True,
    category: str = "Loan EMI",
) -> list[dict]:
    """Generate a series of monthly transactions ~30 days apart."""
    dt = datetime.strptime(start_date, "%Y-%m-%d")
    txns = []
    for i in range(count):
        d = dt + timedelta(days=30 * i)
        txns.append(make_txn(
            description=description,
            date=d.strftime("%Y-%m-%d"),
            debit=amount if is_debit else None,
            credit=amount if not is_debit else None,
            category=category,
            txn_id=f"txn_{i}",
        ))
    return txns


def weekly_series(
    description: str,
    amount: float,
    start_date: str = "2025-01-07",
    count: int = 4,
    is_debit: bool = True,
    category: str = "Others Debit",
) -> list[dict]:
    """Generate a series of weekly transactions ~7 days apart."""
    dt = datetime.strptime(start_date, "%Y-%m-%d")
    txns = []
    for i in range(count):
        d = dt + timedelta(days=7 * i)
        txns.append(make_txn(
            description=description,
            date=d.strftime("%Y-%m-%d"),
            debit=amount if is_debit else None,
            credit=amount if not is_debit else None,
            category=category,
            txn_id=f"txn_{i}",
        ))
    return txns


# ---------------------------------------------------------------------------
# 1. Merchant Key Normalization
# ---------------------------------------------------------------------------

class TestMerchantKeyNormalization:

    def test_basic_uppercase(self):
        assert normalize_merchant_key("hdfc home loan") == "HDFC HOME LOAN"

    def test_removes_upi_reference(self):
        result = normalize_merchant_key("UPI/123456789/HDFC HOME LOAN EMI")
        assert "123456789" not in result
        assert "HDFC HOME LOAN EMI" in result

    def test_removes_digits(self):
        result = normalize_merchant_key("LOAN EMI 25000")
        assert "25000" not in result
        assert "LOAN EMI" in result

    def test_removes_phone_numbers(self):
        result = normalize_merchant_key("UPI-JOHN-9876543210@paytm")
        assert "9876543210" not in result

    def test_collapses_spaces(self):
        result = normalize_merchant_key("HDFC   HOME   LOAN")
        assert "  " not in result

    def test_empty_string(self):
        assert normalize_merchant_key("") == ""

    def test_none_like(self):
        assert normalize_merchant_key("") == ""

    def test_upi_slash_format(self):
        result = normalize_merchant_key("UPI/987654321/SWIGGY FOOD")
        assert "SWIGGY FOOD" in result

    def test_upi_dash_format(self):
        result = normalize_merchant_key("UPI-654321-ZOMATO ORDER")
        assert "ZOMATO ORDER" in result


# ---------------------------------------------------------------------------
# 2. Amount Consistency
# ---------------------------------------------------------------------------

class TestAmountConsistency:

    def test_exact_match(self):
        assert _amounts_consistent([10000.0, 10000.0, 10000.0]) is True

    def test_within_5_percent(self):
        # 10000 ± 5% = 9500 to 10500
        assert _amounts_consistent([10000.0, 10100.0, 9950.0]) is True

    def test_exceeds_5_percent(self):
        # 10000 and 8000 → 20% deviation
        assert _amounts_consistent([10000.0, 8000.0]) is False

    def test_single_amount(self):
        assert _amounts_consistent([10000.0]) is False

    def test_empty(self):
        assert _amounts_consistent([]) is False

    def test_zero_amounts(self):
        assert _amounts_consistent([0.0, 0.0]) is True

    def test_barely_within_tolerance(self):
        # 5% of 10000 = 500, so 10500 should be at the boundary
        assert _amounts_consistent([10000.0, 10500.0]) is True

    def test_barely_exceeds_tolerance(self):
        # Median of [10000, 11000] = 11000; 10000/11000 = 9.09% deviation → exceeds 5%
        assert _amounts_consistent([10000.0, 11000.0]) is False


# ---------------------------------------------------------------------------
# 3. Interval Consistency
# ---------------------------------------------------------------------------

class TestIntervalConsistency:

    def test_monthly_30_days(self):
        base = datetime(2025, 1, 5)
        dates = [base + timedelta(days=30 * i) for i in range(3)]
        assert _intervals_consistent(dates) is True

    def test_monthly_28_days(self):
        base = datetime(2025, 1, 5)
        dates = [base + timedelta(days=28 * i) for i in range(3)]
        assert _intervals_consistent(dates) is True

    def test_monthly_35_days(self):
        base = datetime(2025, 1, 5)
        dates = [base + timedelta(days=35 * i) for i in range(3)]
        assert _intervals_consistent(dates) is True

    def test_weekly_7_days(self):
        base = datetime(2025, 1, 7)
        dates = [base + timedelta(days=7 * i) for i in range(4)]
        assert _intervals_consistent(dates) is True

    def test_biweekly_14_days(self):
        base = datetime(2025, 1, 1)
        dates = [base + timedelta(days=14 * i) for i in range(3)]
        assert _intervals_consistent(dates) is True

    def test_random_intervals_not_consistent(self):
        dates = [
            datetime(2025, 1, 1),
            datetime(2025, 1, 10),   # 9 days
            datetime(2025, 2, 20),   # 41 days
        ]
        assert _intervals_consistent(dates) is False

    def test_single_date(self):
        assert _intervals_consistent([datetime(2025, 1, 1)]) is False

    def test_empty(self):
        assert _intervals_consistent([]) is False

    def test_mixed_intervals_not_consistent(self):
        dates = [
            datetime(2025, 1, 1),
            datetime(2025, 1, 8),    # 7 days (weekly)
            datetime(2025, 2, 7),    # 30 days (monthly)
        ]
        assert _intervals_consistent(dates) is False


# ---------------------------------------------------------------------------
# 4. Monthly EMI Recurring
# ---------------------------------------------------------------------------

class TestMonthlyEMI:

    def test_3_month_emi_is_recurring(self):
        txns = monthly_series("HDFC HOME LOAN EMI", 25000.0, count=3)
        result = detect_recurring(txns)
        assert all(t["is_recurring"] for t in result)

    def test_4_month_emi_is_recurring(self):
        txns = monthly_series("SBI CAR LOAN EMI", 15000.0, count=4)
        result = detect_recurring(txns)
        assert all(t["is_recurring"] for t in result)

    def test_emi_with_slight_amount_variance(self):
        txns = [
            make_txn("LOAN EMI HDFC", "2025-01-05", debit=25000.0, category="Loan EMI", txn_id="t1"),
            make_txn("LOAN EMI HDFC", "2025-02-04", debit=25100.0, category="Loan EMI", txn_id="t2"),
            make_txn("LOAN EMI HDFC", "2025-03-06", debit=24950.0, category="Loan EMI", txn_id="t3"),
        ]
        result = detect_recurring(txns)
        assert all(t["is_recurring"] for t in result)


# ---------------------------------------------------------------------------
# 5. Monthly SIP Recurring
# ---------------------------------------------------------------------------

class TestMonthlySIP:

    def test_sip_3_months(self):
        txns = monthly_series("ZERODHA SIP MUTUAL FUND", 5000.0, count=3, category="Investment")
        result = detect_recurring(txns)
        assert all(t["is_recurring"] for t in result)

    def test_sip_exact_amounts(self):
        txns = monthly_series("GROWW SIP", 10000.0, count=4, category="Investment")
        result = detect_recurring(txns)
        assert all(t["is_recurring"] for t in result)


# ---------------------------------------------------------------------------
# 6. Weekly Subscription Recurring
# ---------------------------------------------------------------------------

class TestWeeklySubscription:

    def test_weekly_subscription(self):
        txns = weekly_series("NETFLIX WEEKLY", 199.0, count=4)
        result = detect_recurring(txns)
        assert all(t["is_recurring"] for t in result)

    def test_weekly_with_6_day_gap(self):
        base = datetime(2025, 1, 7)
        txns = []
        for i in range(3):
            d = base + timedelta(days=6 * i)
            txns.append(make_txn(
                "SPOTIFY SUB", d.strftime("%Y-%m-%d"),
                debit=149.0, txn_id=f"t{i}",
            ))
        result = detect_recurring(txns)
        assert all(t["is_recurring"] for t in result)


# ---------------------------------------------------------------------------
# 7. Salary Monthly Recurring
# ---------------------------------------------------------------------------

class TestSalaryRecurring:

    def test_salary_3_months(self):
        txns = monthly_series(
            "SALARY CREDIT TCS LTD", 85000.0,
            count=3, is_debit=False, category="Salary",
        )
        result = detect_recurring(txns)
        assert all(t["is_recurring"] for t in result)

    def test_salary_with_slight_variation(self):
        txns = [
            make_txn("SALARY TCS", "2025-01-01", credit=85000.0, category="Salary", txn_id="t1"),
            make_txn("SALARY TCS", "2025-01-31", credit=85500.0, category="Salary", txn_id="t2"),
            make_txn("SALARY TCS", "2025-03-02", credit=84800.0, category="Salary", txn_id="t3"),
        ]
        result = detect_recurring(txns)
        assert all(t["is_recurring"] for t in result)


# ---------------------------------------------------------------------------
# 8. Same Amount Random Dates — NOT Recurring
# ---------------------------------------------------------------------------

class TestSameAmountRandomDates:

    def test_not_recurring_random_dates(self):
        txns = [
            make_txn("RANDOM MERCHANT", "2025-01-05", debit=5000.0, txn_id="t1"),
            make_txn("RANDOM MERCHANT", "2025-01-15", debit=5000.0, txn_id="t2"),  # 10 days
            make_txn("RANDOM MERCHANT", "2025-03-20", debit=5000.0, txn_id="t3"),  # 64 days
        ]
        result = detect_recurring(txns)
        assert not any(t["is_recurring"] for t in result)

    def test_not_recurring_irregular_gaps(self):
        txns = [
            make_txn("STORE XYZ", "2025-01-01", debit=2000.0, txn_id="t1"),
            make_txn("STORE XYZ", "2025-01-20", debit=2000.0, txn_id="t2"),  # 19 days
            make_txn("STORE XYZ", "2025-02-25", debit=2000.0, txn_id="t3"),  # 36 days
        ]
        result = detect_recurring(txns)
        assert not any(t["is_recurring"] for t in result)


# ---------------------------------------------------------------------------
# 9. Same Merchant Varying Amount >5% — NOT Recurring
# ---------------------------------------------------------------------------

class TestVaryingAmountNotRecurring:

    def test_large_amount_variance(self):
        txns = [
            make_txn("ELECTRICITY BILL", "2025-01-05", debit=1500.0, txn_id="t1"),
            make_txn("ELECTRICITY BILL", "2025-02-04", debit=3200.0, txn_id="t2"),
            make_txn("ELECTRICITY BILL", "2025-03-06", debit=800.0, txn_id="t3"),
        ]
        result = detect_recurring(txns)
        assert not any(t["is_recurring"] for t in result)

    def test_20_percent_variance(self):
        txns = [
            make_txn("WATER BILL", "2025-01-05", debit=1000.0, txn_id="t1"),
            make_txn("WATER BILL", "2025-02-04", debit=1200.0, txn_id="t2"),  # 20% off
        ]
        result = detect_recurring(txns)
        assert not any(t["is_recurring"] for t in result)


# ---------------------------------------------------------------------------
# 10. Single Occurrence — NOT Recurring
# ---------------------------------------------------------------------------

class TestSingleOccurrence:

    def test_single_transaction(self):
        txns = [make_txn("ONE TIME PURCHASE", "2025-01-05", debit=9999.0)]
        result = detect_recurring(txns)
        assert len(result) == 1
        assert result[0]["is_recurring"] is False

    def test_multiple_unique_merchants(self):
        txns = [
            make_txn("MERCHANT A", "2025-01-05", debit=1000.0, txn_id="t1"),
            make_txn("MERCHANT B", "2025-02-04", debit=1000.0, txn_id="t2"),
            make_txn("MERCHANT C", "2025-03-06", debit=1000.0, txn_id="t3"),
        ]
        result = detect_recurring(txns)
        assert not any(t["is_recurring"] for t in result)


# ---------------------------------------------------------------------------
# 11. Non-Mutation
# ---------------------------------------------------------------------------

class TestNonMutation:

    def test_original_not_mutated(self):
        original = make_txn("HDFC LOAN EMI", "2025-01-05", debit=25000.0)
        original_copy = copy.deepcopy(original)
        detect_recurring([original])
        assert original == original_copy

    def test_no_new_keys_on_original(self):
        original = make_txn("TEST", "2025-01-05", debit=5000.0)
        detect_recurring([original])
        assert "is_recurring" not in original


# ---------------------------------------------------------------------------
# 12. Input Validation
# ---------------------------------------------------------------------------

class TestInputValidation:

    def test_non_list_raises(self):
        with pytest.raises(ValueError, match="list"):
            detect_recurring({"bad": "input"})

    def test_empty_list(self):
        result = detect_recurring([])
        assert result == []

    def test_string_input_raises(self):
        with pytest.raises(ValueError, match="list"):
            detect_recurring("not a list")


# ---------------------------------------------------------------------------
# 13. Output Schema
# ---------------------------------------------------------------------------

class TestOutputSchema:

    def test_has_is_recurring_key(self):
        txns = [make_txn("TEST", "2025-01-05", debit=5000.0)]
        result = detect_recurring(txns)
        assert "is_recurring" in result[0]

    def test_is_recurring_is_bool(self):
        txns = [make_txn("TEST", "2025-01-05", debit=5000.0)]
        result = detect_recurring(txns)
        assert isinstance(result[0]["is_recurring"], bool)

    def test_preserves_original_fields(self):
        txns = [make_txn("TEST", "2025-01-05", debit=5000.0, category="Loan EMI")]
        result = detect_recurring(txns)
        assert result[0]["category"] == "Loan EMI"
        assert result[0]["confidence"] == 0.95
        assert result[0]["description"] == "TEST"

    def test_does_not_change_category(self):
        txns = monthly_series("LOAN EMI", 25000.0, count=3, category="Loan EMI")
        result = detect_recurring(txns)
        for t in result:
            assert t["category"] == "Loan EMI"

    def test_does_not_change_confidence(self):
        txns = monthly_series("LOAN EMI", 25000.0, count=3, category="Loan EMI")
        result = detect_recurring(txns)
        for t in result:
            assert t["confidence"] == 0.95


# ---------------------------------------------------------------------------
# 14. Mixed Recurring and Non-Recurring
# ---------------------------------------------------------------------------

class TestMixedRecurring:

    def test_mixed_recurring_and_one_offs(self):
        recurring = monthly_series("HDFC LOAN EMI", 25000.0, count=3)
        one_off = [make_txn("RANDOM PURCHASE", "2025-01-10", debit=3000.0, txn_id="one_off")]
        txns = recurring + one_off

        result = detect_recurring(txns)
        assert len(result) == 4

        recurring_results = [t for t in result if t["description"] == "HDFC LOAN EMI"]
        one_off_results = [t for t in result if t["description"] == "RANDOM PURCHASE"]

        assert all(t["is_recurring"] for t in recurring_results)
        assert not any(t["is_recurring"] for t in one_off_results)

    def test_two_recurring_groups(self):
        emi = monthly_series("HOME LOAN EMI", 25000.0, count=3)
        sip = monthly_series("ZERODHA SIP", 5000.0, count=3, category="Investment")
        txns = emi + sip

        result = detect_recurring(txns)
        assert all(t["is_recurring"] for t in result)

    def test_debit_and_credit_recurring_separate(self):
        """Same merchant as debit and credit should be separate groups."""
        debit_txns = monthly_series("BANK TRANSFER", 10000.0, is_debit=True, count=3)
        credit_txns = monthly_series("BANK TRANSFER", 10000.0, is_debit=False, count=3, category="Bank Transfer Credit")
        txns = debit_txns + credit_txns

        result = detect_recurring(txns)
        assert all(t["is_recurring"] for t in result)


# ---------------------------------------------------------------------------
# 15. Performance
# ---------------------------------------------------------------------------

class TestPerformance:

    def test_10k_transactions(self):
        """Must handle 10K transactions without error."""
        txns = []
        base = datetime(2025, 1, 1)
        for i in range(10000):
            d = base + timedelta(days=i % 365)
            txns.append(make_txn(
                description=f"MERCHANT {i % 50}",
                date=d.strftime("%Y-%m-%d"),
                debit=1000.0 + (i % 100),
                txn_id=f"t{i}",
            ))
        result = detect_recurring(txns)
        assert len(result) == 10000
        assert all("is_recurring" in t for t in result)
