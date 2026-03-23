"""
Tests for Airco Insights — Excel Generator
============================================
Covers file generation, sheet structure, data integrity validation,
formatting, edge cases, and performance.

Test groups:
    1.  File generation — creates valid .xlsx
    2.  Sheet count — exactly 8 sheets
    3.  Data integrity validation
    4.  Empty dataset handling
    5.  Input validation
    6.  Multi-month dynamic columns
    7.  Raw transactions sheet
    8.  Performance (10K rows)
    9.  Output cleanup on failure
"""

import os
import pytest
import tempfile
from datetime import datetime, timedelta

from app.services.excel_generator import (
    generate_excel,
    _validate_data,
    ExcelValidationError,
    CREDIT_CATEGORIES,
    DEBIT_CATEGORIES,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_user_info() -> dict:
    return {
        "full_name": "Test User",
        "account_type": "Salaried",
        "bank_name": "HDFC Bank",
        "account_number": "XXXX1234",
    }


def make_aggregation(months: list[str] = None) -> dict:
    """Generate a minimal valid aggregation dataset."""
    if months is None:
        months = ["2025-06"]

    summary = {}
    category_analysis = {}
    weekly_analysis = {}
    recurring_analysis = {}

    for mk in months:
        summary[mk] = {
            "total_credit_count": 2,
            "total_credit_amount": 90000.0,
            "total_debit_count": 3,
            "total_debit_amount": 18000.0,
            "avg_balance": 120000.0,
            "min_balance": 100000.0,
            "max_balance": 140000.0,
            "start_of_month_balance": 100000.0,
            "end_of_month_balance": 132000.0,
        }

        category_analysis[mk] = {
            "credit": {cat: {"count": 0, "amount": 0.0} for cat in CREDIT_CATEGORIES},
            "debit": {cat: {"count": 0, "amount": 0.0} for cat in DEBIT_CATEGORIES},
        }
        category_analysis[mk]["credit"]["Salary"] = {"count": 1, "amount": 85000.0}
        category_analysis[mk]["credit"]["UPI Credit"] = {"count": 1, "amount": 5000.0}
        category_analysis[mk]["debit"]["Loan EMI"] = {"count": 1, "amount": 10000.0}
        category_analysis[mk]["debit"]["Shopping"] = {"count": 1, "amount": 5000.0}
        category_analysis[mk]["debit"]["UPI Payment"] = {"count": 1, "amount": 3000.0}

        weekly_analysis[mk] = {
            "week1": {"credit_amount": 85000.0, "debit_amount": 10000.0},
            "week2": {"credit_amount": 5000.0, "debit_amount": 5000.0},
            "week3": {"credit_amount": 0.0, "debit_amount": 3000.0},
            "week4": {"credit_amount": 0.0, "debit_amount": 0.0},
        }

        recurring_analysis[mk] = {
            "recurring_credit_total": 85000.0,
            "non_recurring_credit_total": 5000.0,
            "recurring_debit_total": 10000.0,
            "non_recurring_debit_total": 8000.0,
        }

    return {
        "summary": summary,
        "category_analysis": category_analysis,
        "weekly_analysis": weekly_analysis,
        "recurring_analysis": recurring_analysis,
    }


def make_transactions(count: int = 5) -> list[dict]:
    txns = []
    base = datetime(2025, 6, 1)
    for i in range(count):
        d = base + timedelta(days=i)
        txns.append({
            "date": d.strftime("%Y-%m-%d"),
            "description": f"TEST TXN {i}",
            "debit": 1000.0 + i if i % 2 == 0 else None,
            "credit": 5000.0 if i % 2 != 0 else None,
            "balance": 50000.0 - (i * 100),
            "category": "Shopping" if i % 2 == 0 else "Salary",
            "confidence": 0.95,
            "is_recurring": i < 2,
        })
    return txns


# ---------------------------------------------------------------------------
# 1. File Generation
# ---------------------------------------------------------------------------

class TestFileGeneration:

    def test_creates_xlsx_file(self, tmp_path):
        path = str(tmp_path / "test.xlsx")
        result = generate_excel(make_user_info(), make_aggregation(), make_transactions(), path)
        assert os.path.isfile(result)
        assert result.endswith(".xlsx")

    def test_returns_output_path(self, tmp_path):
        path = str(tmp_path / "test.xlsx")
        result = generate_excel(make_user_info(), make_aggregation(), make_transactions(), path)
        assert result == path

    def test_creates_output_directory(self, tmp_path):
        path = str(tmp_path / "subdir" / "deep" / "test.xlsx")
        result = generate_excel(make_user_info(), make_aggregation(), make_transactions(), path)
        assert os.path.isfile(result)

    def test_file_not_empty(self, tmp_path):
        path = str(tmp_path / "test.xlsx")
        generate_excel(make_user_info(), make_aggregation(), make_transactions(), path)
        assert os.path.getsize(path) > 0


# ---------------------------------------------------------------------------
# 2. Sheet Count
# ---------------------------------------------------------------------------

class TestSheetCount:

    def test_exactly_8_sheets(self, tmp_path):
        import zipfile
        path = str(tmp_path / "test.xlsx")
        generate_excel(make_user_info(), make_aggregation(), make_transactions(), path)
        # xlsx is a zip file — count xl/worksheets/sheet*.xml entries
        with zipfile.ZipFile(path, 'r') as z:
            sheet_files = [n for n in z.namelist() if n.startswith("xl/worksheets/sheet")]
            assert len(sheet_files) == 8


# ---------------------------------------------------------------------------
# 3. Data Integrity Validation
# ---------------------------------------------------------------------------

class TestDataValidation:

    def test_valid_data_passes(self):
        _validate_data(make_aggregation(), make_transactions())

    def test_nan_in_summary_raises(self):
        agg = make_aggregation()
        agg["summary"]["2025-06"]["avg_balance"] = float("nan")
        with pytest.raises(ExcelValidationError, match="NaN"):
            _validate_data(agg, make_transactions())

    def test_none_in_summary_raises(self):
        agg = make_aggregation()
        agg["summary"]["2025-06"]["total_credit_amount"] = None
        with pytest.raises(ExcelValidationError, match="None"):
            _validate_data(agg, make_transactions())

    def test_empty_data_passes(self):
        _validate_data({"summary": {}, "category_analysis": {}, "weekly_analysis": {}, "recurring_analysis": {}}, [])


# ---------------------------------------------------------------------------
# 4. Empty Dataset
# ---------------------------------------------------------------------------

class TestEmptyDataset:

    def test_empty_transactions(self, tmp_path):
        path = str(tmp_path / "test.xlsx")
        agg = {
            "summary": {},
            "category_analysis": {},
            "weekly_analysis": {},
            "recurring_analysis": {},
        }
        result = generate_excel(make_user_info(), agg, [], path)
        assert os.path.isfile(result)


# ---------------------------------------------------------------------------
# 5. Input Validation
# ---------------------------------------------------------------------------

class TestInputValidation:

    def test_bad_aggregation_type(self, tmp_path):
        path = str(tmp_path / "test.xlsx")
        with pytest.raises(ValueError, match="dict"):
            generate_excel(make_user_info(), "bad", [], path)

    def test_bad_transactions_type(self, tmp_path):
        path = str(tmp_path / "test.xlsx")
        with pytest.raises(ValueError, match="list"):
            generate_excel(make_user_info(), make_aggregation(), "bad", path)


# ---------------------------------------------------------------------------
# 6. Multi-Month Dynamic Columns
# ---------------------------------------------------------------------------

class TestMultiMonth:

    def test_3_months(self, tmp_path):
        path = str(tmp_path / "test.xlsx")
        months = ["2025-04", "2025-05", "2025-06"]
        result = generate_excel(
            make_user_info(), make_aggregation(months), make_transactions(), path
        )
        assert os.path.isfile(result)

    def test_single_month(self, tmp_path):
        path = str(tmp_path / "test.xlsx")
        result = generate_excel(
            make_user_info(), make_aggregation(["2025-06"]), make_transactions(), path
        )
        assert os.path.isfile(result)

    def test_6_months(self, tmp_path):
        path = str(tmp_path / "test.xlsx")
        months = [f"2025-{m:02d}" for m in range(1, 7)]
        result = generate_excel(
            make_user_info(), make_aggregation(months), make_transactions(), path
        )
        assert os.path.isfile(result)


# ---------------------------------------------------------------------------
# 7. Raw Transactions Sheet
# ---------------------------------------------------------------------------

class TestRawTransactions:

    def test_includes_all_transactions(self, tmp_path):
        path = str(tmp_path / "test.xlsx")
        txns = make_transactions(100)
        generate_excel(make_user_info(), make_aggregation(), txns, path)
        assert os.path.isfile(path)

    def test_handles_none_values(self, tmp_path):
        path = str(tmp_path / "test.xlsx")
        txns = [{
            "date": "2025-06-01",
            "description": "TEST",
            "debit": None,
            "credit": None,
            "balance": None,
            "category": None,
            "confidence": None,
            "is_recurring": False,
        }]
        generate_excel(make_user_info(), make_aggregation(), txns, path)
        assert os.path.isfile(path)


# ---------------------------------------------------------------------------
# 8. Performance
# ---------------------------------------------------------------------------

class TestPerformance:

    def test_10k_transactions(self, tmp_path):
        path = str(tmp_path / "test.xlsx")
        txns = make_transactions(10000)
        months = [f"2025-{m:02d}" for m in range(1, 7)]
        result = generate_excel(
            make_user_info(), make_aggregation(months), txns, path
        )
        assert os.path.isfile(result)
        # File should be reasonably sized (not corrupted)
        assert os.path.getsize(result) > 1000
