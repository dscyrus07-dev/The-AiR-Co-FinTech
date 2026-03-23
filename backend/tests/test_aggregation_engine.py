"""
Tests for Airco Insights — Aggregation Engine (Financial Math Core)
====================================================================
Covers monthly summary, category analysis, weekly split, recurring split,
edge cases, input validation, and performance.

Test groups:
    1.  Monthly summary — single month
    2.  Monthly summary — multiple months
    3.  Category analysis
    4.  Weekly split
    5.  Recurring split
    6.  Only debit transactions
    7.  Only credit transactions
    8.  Empty dataset
    9.  Input validation
    10. Output structure
    11. Rounding
    12. Large dataset (10K rows)
    13. Aggregate main function
"""

import pytest
from datetime import datetime, timedelta

from app.services.aggregation_engine import (
    aggregate,
    compute_monthly_summary,
    compute_category_analysis,
    compute_weekly_split,
    compute_recurring_split,
    CREDIT_CATEGORIES,
    DEBIT_CATEGORIES,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_txn(
    date: str,
    debit: float = None,
    credit: float = None,
    balance: float = 50000.0,
    category: str = "Others Debit",
    is_recurring: bool = False,
    description: str = "TEST",
) -> dict:
    return {
        "date": date,
        "description": description,
        "debit": debit,
        "credit": credit,
        "balance": balance,
        "category": category,
        "is_recurring": is_recurring,
    }


# ---------------------------------------------------------------------------
# 1. Monthly Summary — Single Month
# ---------------------------------------------------------------------------

class TestMonthlySummarySingle:

    def test_single_month_totals(self):
        txns = [
            make_txn("2025-06-01", debit=10000.0, balance=90000.0),
            make_txn("2025-06-05", credit=50000.0, balance=140000.0, category="Salary"),
            make_txn("2025-06-15", debit=5000.0, balance=135000.0),
            make_txn("2025-06-25", debit=3000.0, balance=132000.0),
        ]
        result = compute_monthly_summary(txns)
        assert "2025-06" in result

        m = result["2025-06"]
        assert m["total_credit_count"] == 1
        assert m["total_credit_amount"] == 50000.0
        assert m["total_debit_count"] == 3
        assert m["total_debit_amount"] == 18000.0

    def test_start_and_end_balance(self):
        txns = [
            make_txn("2025-06-01", debit=1000.0, balance=99000.0),
            make_txn("2025-06-15", credit=5000.0, balance=104000.0, category="Salary"),
            make_txn("2025-06-30", debit=2000.0, balance=102000.0),
        ]
        result = compute_monthly_summary(txns)
        m = result["2025-06"]
        assert m["start_of_month_balance"] == 99000.0
        assert m["end_of_month_balance"] == 102000.0

    def test_avg_min_max_balance(self):
        txns = [
            make_txn("2025-06-01", debit=1000.0, balance=10000.0),
            make_txn("2025-06-10", debit=2000.0, balance=8000.0),
            make_txn("2025-06-20", credit=5000.0, balance=13000.0, category="Salary"),
        ]
        result = compute_monthly_summary(txns)
        m = result["2025-06"]
        assert m["min_balance"] == 8000.0
        assert m["max_balance"] == 13000.0
        # avg = (10000 + 8000 + 13000) / 3 = 10333.33
        assert m["avg_balance"] == round((10000 + 8000 + 13000) / 3, 2)


# ---------------------------------------------------------------------------
# 2. Monthly Summary — Multiple Months
# ---------------------------------------------------------------------------

class TestMonthlySummaryMultiple:

    def test_two_months(self):
        txns = [
            make_txn("2025-06-01", debit=5000.0, balance=95000.0),
            make_txn("2025-06-15", credit=20000.0, balance=115000.0, category="Salary"),
            make_txn("2025-07-01", debit=8000.0, balance=107000.0),
            make_txn("2025-07-10", debit=3000.0, balance=104000.0),
        ]
        result = compute_monthly_summary(txns)
        assert "2025-06" in result
        assert "2025-07" in result

        assert result["2025-06"]["total_credit_count"] == 1
        assert result["2025-07"]["total_debit_count"] == 2

    def test_months_sorted_in_output(self):
        txns = [
            make_txn("2025-08-01", debit=1000.0),
            make_txn("2025-06-01", debit=1000.0),
            make_txn("2025-07-01", debit=1000.0),
        ]
        result = compute_monthly_summary(txns)
        keys = list(result.keys())
        assert keys == sorted(keys)


# ---------------------------------------------------------------------------
# 3. Category Analysis
# ---------------------------------------------------------------------------

class TestCategoryAnalysis:

    def test_single_debit_category(self):
        txns = [
            make_txn("2025-06-01", debit=10000.0, category="Loan EMI"),
            make_txn("2025-06-15", debit=5000.0, category="Loan EMI"),
        ]
        result = compute_category_analysis(txns)
        assert "2025-06" in result
        assert result["2025-06"]["debit"]["Loan EMI"]["count"] == 2
        assert result["2025-06"]["debit"]["Loan EMI"]["amount"] == 15000.0

    def test_single_credit_category(self):
        txns = [
            make_txn("2025-06-01", credit=85000.0, category="Salary"),
        ]
        result = compute_category_analysis(txns)
        assert result["2025-06"]["credit"]["Salary"]["count"] == 1
        assert result["2025-06"]["credit"]["Salary"]["amount"] == 85000.0

    def test_multiple_categories(self):
        txns = [
            make_txn("2025-06-01", debit=10000.0, category="Loan EMI"),
            make_txn("2025-06-05", debit=5000.0, category="Shopping"),
            make_txn("2025-06-10", credit=85000.0, category="Salary"),
            make_txn("2025-06-15", debit=2000.0, category="UPI Payment"),
        ]
        result = compute_category_analysis(txns)
        m = result["2025-06"]
        assert m["debit"]["Loan EMI"]["count"] == 1
        assert m["debit"]["Shopping"]["count"] == 1
        assert m["debit"]["UPI Payment"]["count"] == 1
        assert m["credit"]["Salary"]["count"] == 1

    def test_all_categories_initialized(self):
        txns = [make_txn("2025-06-01", debit=1000.0, category="Shopping")]
        result = compute_category_analysis(txns)
        m = result["2025-06"]
        for cat in CREDIT_CATEGORIES:
            assert cat in m["credit"]
        for cat in DEBIT_CATEGORIES:
            assert cat in m["debit"]

    def test_uncategorized_ignored(self):
        txns = [make_txn("2025-06-01", debit=1000.0, category=None)]
        result = compute_category_analysis(txns)
        # No month should be created since category is None
        assert len(result) == 0

    def test_multi_month_category(self):
        txns = [
            make_txn("2025-06-05", debit=25000.0, category="Loan EMI"),
            make_txn("2025-07-05", debit=25000.0, category="Loan EMI"),
        ]
        result = compute_category_analysis(txns)
        assert result["2025-06"]["debit"]["Loan EMI"]["count"] == 1
        assert result["2025-07"]["debit"]["Loan EMI"]["count"] == 1


# ---------------------------------------------------------------------------
# 4. Weekly Split
# ---------------------------------------------------------------------------

class TestWeeklySplit:

    def test_week1(self):
        txns = [make_txn("2025-06-03", debit=5000.0)]
        result = compute_weekly_split(txns)
        assert result["2025-06"]["week1"]["debit_amount"] == 5000.0
        assert result["2025-06"]["week2"]["debit_amount"] == 0.0

    def test_week2(self):
        txns = [make_txn("2025-06-10", credit=20000.0, category="Salary")]
        result = compute_weekly_split(txns)
        assert result["2025-06"]["week2"]["credit_amount"] == 20000.0

    def test_week3(self):
        txns = [make_txn("2025-06-18", debit=3000.0)]
        result = compute_weekly_split(txns)
        assert result["2025-06"]["week3"]["debit_amount"] == 3000.0

    def test_week4(self):
        txns = [make_txn("2025-06-25", debit=2000.0)]
        result = compute_weekly_split(txns)
        assert result["2025-06"]["week4"]["debit_amount"] == 2000.0

    def test_day_22_is_week4(self):
        txns = [make_txn("2025-06-22", debit=1000.0)]
        result = compute_weekly_split(txns)
        assert result["2025-06"]["week4"]["debit_amount"] == 1000.0

    def test_day_7_is_week1(self):
        txns = [make_txn("2025-06-07", debit=1000.0)]
        result = compute_weekly_split(txns)
        assert result["2025-06"]["week1"]["debit_amount"] == 1000.0

    def test_day_8_is_week2(self):
        txns = [make_txn("2025-06-08", debit=1000.0)]
        result = compute_weekly_split(txns)
        assert result["2025-06"]["week2"]["debit_amount"] == 1000.0

    def test_day_14_is_week2(self):
        txns = [make_txn("2025-06-14", debit=1000.0)]
        result = compute_weekly_split(txns)
        assert result["2025-06"]["week2"]["debit_amount"] == 1000.0

    def test_day_15_is_week3(self):
        txns = [make_txn("2025-06-15", debit=1000.0)]
        result = compute_weekly_split(txns)
        assert result["2025-06"]["week3"]["debit_amount"] == 1000.0

    def test_day_21_is_week3(self):
        txns = [make_txn("2025-06-21", debit=1000.0)]
        result = compute_weekly_split(txns)
        assert result["2025-06"]["week3"]["debit_amount"] == 1000.0

    def test_day_31_is_week4(self):
        txns = [make_txn("2025-01-31", debit=1000.0)]
        result = compute_weekly_split(txns)
        assert result["2025-01"]["week4"]["debit_amount"] == 1000.0

    def test_accumulates_within_week(self):
        txns = [
            make_txn("2025-06-01", debit=1000.0),
            make_txn("2025-06-03", debit=2000.0),
            make_txn("2025-06-05", credit=500.0, category="UPI Credit"),
        ]
        result = compute_weekly_split(txns)
        assert result["2025-06"]["week1"]["debit_amount"] == 3000.0
        assert result["2025-06"]["week1"]["credit_amount"] == 500.0

    def test_all_four_weeks_initialized(self):
        txns = [make_txn("2025-06-15", debit=1000.0)]
        result = compute_weekly_split(txns)
        m = result["2025-06"]
        for w in ["week1", "week2", "week3", "week4"]:
            assert w in m
            assert "credit_amount" in m[w]
            assert "debit_amount" in m[w]

    def test_no_overlapping(self):
        """Each transaction goes to exactly one week."""
        txns = [
            make_txn("2025-06-07", debit=100.0),   # week1
            make_txn("2025-06-08", debit=200.0),   # week2
            make_txn("2025-06-14", debit=300.0),   # week2
            make_txn("2025-06-15", debit=400.0),   # week3
            make_txn("2025-06-21", debit=500.0),   # week3
            make_txn("2025-06-22", debit=600.0),   # week4
        ]
        result = compute_weekly_split(txns)
        m = result["2025-06"]
        assert m["week1"]["debit_amount"] == 100.0
        assert m["week2"]["debit_amount"] == 500.0
        assert m["week3"]["debit_amount"] == 900.0
        assert m["week4"]["debit_amount"] == 600.0
        total = sum(m[f"week{w}"]["debit_amount"] for w in range(1, 5))
        assert total == 2100.0


# ---------------------------------------------------------------------------
# 5. Recurring Split
# ---------------------------------------------------------------------------

class TestRecurringSplit:

    def test_all_recurring(self):
        txns = [
            make_txn("2025-06-01", debit=25000.0, is_recurring=True),
            make_txn("2025-06-05", credit=85000.0, is_recurring=True, category="Salary"),
        ]
        result = compute_recurring_split(txns)
        m = result["2025-06"]
        assert m["recurring_debit_total"] == 25000.0
        assert m["recurring_credit_total"] == 85000.0
        assert m["non_recurring_debit_total"] == 0.0
        assert m["non_recurring_credit_total"] == 0.0

    def test_all_non_recurring(self):
        txns = [
            make_txn("2025-06-01", debit=5000.0, is_recurring=False),
            make_txn("2025-06-05", credit=3000.0, is_recurring=False, category="UPI Credit"),
        ]
        result = compute_recurring_split(txns)
        m = result["2025-06"]
        assert m["recurring_debit_total"] == 0.0
        assert m["non_recurring_debit_total"] == 5000.0
        assert m["non_recurring_credit_total"] == 3000.0

    def test_mixed_recurring(self):
        txns = [
            make_txn("2025-06-01", debit=25000.0, is_recurring=True),
            make_txn("2025-06-05", debit=3000.0, is_recurring=False),
            make_txn("2025-06-10", credit=85000.0, is_recurring=True, category="Salary"),
            make_txn("2025-06-15", credit=2000.0, is_recurring=False, category="UPI Credit"),
        ]
        result = compute_recurring_split(txns)
        m = result["2025-06"]
        assert m["recurring_debit_total"] == 25000.0
        assert m["non_recurring_debit_total"] == 3000.0
        assert m["recurring_credit_total"] == 85000.0
        assert m["non_recurring_credit_total"] == 2000.0

    def test_multi_month_recurring(self):
        txns = [
            make_txn("2025-06-01", debit=25000.0, is_recurring=True),
            make_txn("2025-07-01", debit=25000.0, is_recurring=True),
        ]
        result = compute_recurring_split(txns)
        assert result["2025-06"]["recurring_debit_total"] == 25000.0
        assert result["2025-07"]["recurring_debit_total"] == 25000.0

    def test_default_is_recurring_false(self):
        """If is_recurring is missing, treat as non-recurring."""
        txns = [{"date": "2025-06-01", "debit": 5000.0, "credit": None, "balance": 50000.0}]
        result = compute_recurring_split(txns)
        assert result["2025-06"]["non_recurring_debit_total"] == 5000.0


# ---------------------------------------------------------------------------
# 6. Only Debit Transactions
# ---------------------------------------------------------------------------

class TestOnlyDebit:

    def test_summary_only_debits(self):
        txns = [
            make_txn("2025-06-01", debit=10000.0, balance=90000.0),
            make_txn("2025-06-15", debit=5000.0, balance=85000.0),
        ]
        result = compute_monthly_summary(txns)
        m = result["2025-06"]
        assert m["total_credit_count"] == 0
        assert m["total_credit_amount"] == 0.0
        assert m["total_debit_count"] == 2
        assert m["total_debit_amount"] == 15000.0

    def test_category_only_debits(self):
        txns = [
            make_txn("2025-06-01", debit=10000.0, category="Loan EMI"),
        ]
        result = compute_category_analysis(txns)
        for cat in CREDIT_CATEGORIES:
            assert result["2025-06"]["credit"][cat]["count"] == 0


# ---------------------------------------------------------------------------
# 7. Only Credit Transactions
# ---------------------------------------------------------------------------

class TestOnlyCredit:

    def test_summary_only_credits(self):
        txns = [
            make_txn("2025-06-01", credit=85000.0, balance=185000.0, category="Salary"),
            make_txn("2025-06-10", credit=5000.0, balance=190000.0, category="UPI Credit"),
        ]
        result = compute_monthly_summary(txns)
        m = result["2025-06"]
        assert m["total_credit_count"] == 2
        assert m["total_credit_amount"] == 90000.0
        assert m["total_debit_count"] == 0
        assert m["total_debit_amount"] == 0.0


# ---------------------------------------------------------------------------
# 8. Empty Dataset
# ---------------------------------------------------------------------------

class TestEmptyDataset:

    def test_empty_summary(self):
        assert compute_monthly_summary([]) == {}

    def test_empty_category(self):
        assert compute_category_analysis([]) == {}

    def test_empty_weekly(self):
        assert compute_weekly_split([]) == {}

    def test_empty_recurring(self):
        assert compute_recurring_split([]) == {}

    def test_aggregate_empty(self):
        result = aggregate([])
        assert result["summary"] == {}
        assert result["category_analysis"] == {}
        assert result["weekly_analysis"] == {}
        assert result["recurring_analysis"] == {}


# ---------------------------------------------------------------------------
# 9. Input Validation
# ---------------------------------------------------------------------------

class TestInputValidation:

    def test_non_list_raises(self):
        with pytest.raises(ValueError, match="list"):
            aggregate({"bad": "input"})

    def test_string_raises(self):
        with pytest.raises(ValueError, match="list"):
            aggregate("not a list")


# ---------------------------------------------------------------------------
# 10. Output Structure
# ---------------------------------------------------------------------------

class TestOutputStructure:

    def test_aggregate_has_four_keys(self):
        txns = [make_txn("2025-06-01", debit=1000.0)]
        result = aggregate(txns)
        # Enhanced: 4 original keys + 4 new analytics keys
        expected = {
            "summary", "category_analysis", "weekly_analysis", "recurring_analysis",
            "statistics", "trends", "cash_flow", "top_merchants",
        }
        assert set(result.keys()) == expected

    def test_summary_has_required_keys(self):
        txns = [make_txn("2025-06-01", debit=1000.0, balance=99000.0)]
        result = compute_monthly_summary(txns)
        m = result["2025-06"]
        required = {
            "total_credit_count", "total_credit_amount",
            "total_debit_count", "total_debit_amount",
            "avg_balance", "min_balance", "max_balance",
            "start_of_month_balance", "end_of_month_balance",
        }
        assert set(m.keys()) == required

    def test_weekly_has_four_weeks(self):
        txns = [make_txn("2025-06-01", debit=1000.0)]
        result = compute_weekly_split(txns)
        assert set(result["2025-06"].keys()) == {"week1", "week2", "week3", "week4"}

    def test_recurring_has_four_fields(self):
        txns = [make_txn("2025-06-01", debit=1000.0)]
        result = compute_recurring_split(txns)
        required = {
            "recurring_credit_total", "non_recurring_credit_total",
            "recurring_debit_total", "non_recurring_debit_total",
        }
        assert set(result["2025-06"].keys()) == required


# ---------------------------------------------------------------------------
# 11. Rounding
# ---------------------------------------------------------------------------

class TestRounding:

    def test_amounts_rounded_to_2_decimals(self):
        txns = [
            make_txn("2025-06-01", debit=10000.123456, balance=89999.876544),
        ]
        result = compute_monthly_summary(txns)
        m = result["2025-06"]
        assert m["total_debit_amount"] == 10000.12
        assert m["avg_balance"] == 89999.88

    def test_weekly_amounts_rounded(self):
        txns = [
            make_txn("2025-06-01", debit=1000.005),
            make_txn("2025-06-02", debit=2000.009),
        ]
        result = compute_weekly_split(txns)
        assert result["2025-06"]["week1"]["debit_amount"] == 3000.01

    def test_category_amounts_rounded(self):
        txns = [
            make_txn("2025-06-01", debit=1234.567, category="Shopping"),
        ]
        result = compute_category_analysis(txns)
        assert result["2025-06"]["debit"]["Shopping"]["amount"] == 1234.57


# ---------------------------------------------------------------------------
# 12. Large Dataset (10K rows)
# ---------------------------------------------------------------------------

class TestPerformance:

    def test_10k_aggregate(self):
        txns = []
        base = datetime(2025, 1, 1)
        for i in range(10000):
            d = base + timedelta(days=i % 365)
            is_credit = i % 3 == 0
            txns.append(make_txn(
                date=d.strftime("%Y-%m-%d"),
                debit=None if is_credit else 1000.0 + (i % 100),
                credit=5000.0 if is_credit else None,
                balance=50000.0 + (i % 1000),
                category="Salary" if is_credit else "Shopping",
                is_recurring=i % 5 == 0,
            ))
        result = aggregate(txns)
        assert len(result["summary"]) > 0
        assert len(result["category_analysis"]) > 0
        assert len(result["weekly_analysis"]) > 0
        assert len(result["recurring_analysis"]) > 0

    def test_10k_summary_math(self):
        """Verify totals are correct for a known large set."""
        txns = [
            make_txn(
                date="2025-06-01",
                debit=100.0,
                balance=50000.0,
            )
            for _ in range(1000)
        ]
        result = compute_monthly_summary(txns)
        m = result["2025-06"]
        assert m["total_debit_count"] == 1000
        assert m["total_debit_amount"] == 100000.0


# ---------------------------------------------------------------------------
# 13. Aggregate Main Function
# ---------------------------------------------------------------------------

class TestAggregateMain:

    def test_full_pipeline(self):
        txns = [
            make_txn("2025-06-01", debit=25000.0, balance=75000.0, category="Loan EMI", is_recurring=True),
            make_txn("2025-06-05", credit=85000.0, balance=160000.0, category="Salary", is_recurring=True),
            make_txn("2025-06-10", debit=5000.0, balance=155000.0, category="Shopping", is_recurring=False),
            make_txn("2025-06-20", debit=2000.0, balance=153000.0, category="UPI Payment", is_recurring=False),
            make_txn("2025-07-01", debit=25000.0, balance=128000.0, category="Loan EMI", is_recurring=True),
            make_txn("2025-07-05", credit=85000.0, balance=213000.0, category="Salary", is_recurring=True),
        ]
        result = aggregate(txns)

        # Summary checks
        assert "2025-06" in result["summary"]
        assert "2025-07" in result["summary"]
        assert result["summary"]["2025-06"]["total_debit_count"] == 3
        assert result["summary"]["2025-06"]["total_credit_count"] == 1

        # Category checks
        assert result["category_analysis"]["2025-06"]["debit"]["Loan EMI"]["count"] == 1
        assert result["category_analysis"]["2025-06"]["credit"]["Salary"]["amount"] == 85000.0

        # Weekly checks
        assert result["weekly_analysis"]["2025-06"]["week1"]["debit_amount"] == 25000.0

        # Recurring checks
        assert result["recurring_analysis"]["2025-06"]["recurring_debit_total"] == 25000.0
        assert result["recurring_analysis"]["2025-06"]["non_recurring_debit_total"] == 7000.0

    def test_deterministic(self):
        """Same input → same output."""
        txns = [
            make_txn("2025-06-01", debit=10000.0, category="Loan EMI"),
            make_txn("2025-06-10", credit=50000.0, category="Salary"),
        ]
        result1 = aggregate(txns)
        result2 = aggregate(txns)
        assert result1 == result2
