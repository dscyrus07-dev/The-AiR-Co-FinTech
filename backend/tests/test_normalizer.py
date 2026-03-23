"""
Tests for Airco Insights — Canonical Schema Normalizer
========================================================
Covers every validation rule, edge case, and error path defined in the spec.

Test groups:
    1.  Date parsing — all formats + edge cases
    2.  Description cleaning — unicode, whitespace, empty
    3.  Amount cleaning — all formats, currency symbols, edge cases
    4.  Row structure validation — missing fields, bad types
    5.  Debit/credit resolution — aliases, conflicts, sign handling
    6.  Balance validation — missing, negative, overdraft
    7.  Transaction ID — determinism, uniqueness, consistency
    8.  Balance flow validation — continuity, tolerance, mismatch
    9.  Full normalize_transactions() — integration + corruption policy
    10. Output schema contract — types, keys, invariants
"""

import pytest
from unittest.mock import patch

from app.services.normalizer import (
    parse_date,
    clean_description,
    clean_amount,
    validate_row_structure,
    validate_balance,
    validate_balance_flow,
    generate_txn_id,
    normalize_transactions,
    # Exceptions
    InvalidDateError,
    InvalidAmountError,
    InvalidRowStructureError,
    InvalidBalanceError,
    DebitCreditConflictError,
    ExcessiveDataCorruptionError,
    # Constants
    MAX_CORRUPTION_RATE,
)


# ---------------------------------------------------------------------------
# Fixtures & Factories
# ---------------------------------------------------------------------------

def make_row(
    date="01/06/25",
    description="NEFT CR-YESB0000001-PHONEPE",
    withdrawal="",
    deposit="5000.00",
    balance="100000.00",
    **overrides,
) -> dict:
    """Build a standard raw row with sensible defaults."""
    base = {
        "date": date,
        "description": description,
        "withdrawal": withdrawal,
        "deposit": deposit,
        "balance": balance,
    }
    base.update(overrides)
    return base


def make_debit_row(**overrides) -> dict:
    """Standard debit (withdrawal) row."""
    return make_row(withdrawal="2500.00", deposit="", **overrides)


# ---------------------------------------------------------------------------
# 1. Date Parsing
# ---------------------------------------------------------------------------

class TestParseDate:

    @pytest.mark.parametrize("raw,expected", [
        ("01/06/25",    "2025-06-01"),
        ("01/06/2025",  "2025-06-01"),
        ("01-06-2025",  "2025-06-01"),
        ("2025-06-01",  "2025-06-01"),
        ("01.06.2025",  "2025-06-01"),
        ("01 Jun 2025", "2025-06-01"),
        ("01 June 2025","2025-06-01"),
        ("01-Jun-2025", "2025-06-01"),
        ("01/Jun/2025", "2025-06-01"),
        ("01 Jun 25",   "2025-06-01"),
        ("2025/06/01",  "2025-06-01"),
    ])
    def test_all_supported_formats(self, raw, expected):
        assert parse_date(raw) == expected

    def test_already_iso_passthrough(self):
        assert parse_date("2024-12-31") == "2024-12-31"

    def test_strips_whitespace(self):
        assert parse_date("  01/06/2025  ") == "2025-06-01"

    def test_none_raises(self):
        with pytest.raises(InvalidDateError, match="None"):
            parse_date(None)

    def test_empty_string_raises(self):
        with pytest.raises(InvalidDateError, match="empty"):
            parse_date("")

    def test_gibberish_raises(self):
        with pytest.raises(InvalidDateError):
            parse_date("not-a-date")

    def test_unrealistic_year_past_raises(self):
        with pytest.raises(InvalidDateError, match="unrealistic"):
            parse_date("01/01/1850")  # year 1850

    def test_invalid_iso_value_raises(self):
        with pytest.raises(InvalidDateError):
            parse_date("2025-13-01")  # month 13

    def test_integer_input_treated_as_string(self):
        # Should not crash — gets stringified then fails gracefully
        with pytest.raises(InvalidDateError):
            parse_date(20250601)


# ---------------------------------------------------------------------------
# 2. Description Cleaning
# ---------------------------------------------------------------------------

class TestCleanDescription:

    def test_basic_string(self):
        assert clean_description("NEFT CR HDFC") == "NEFT CR HDFC"

    def test_strips_whitespace(self):
        assert clean_description("  NEFT  ") == "NEFT"

    def test_collapses_internal_whitespace(self):
        assert clean_description("NEFT   CR   HDFC") == "NEFT CR HDFC"

    def test_removes_newlines(self):
        assert clean_description("NEFT\nCR\r\nHDFC") == "NEFT CR HDFC"

    def test_removes_tabs(self):
        assert clean_description("NEFT\tCR\tHDFC") == "NEFT CR HDFC"

    def test_removes_zero_width_space(self):
        desc = "NEFT\u200bCR"   # zero-width space
        result = clean_description(desc)
        assert "\u200b" not in result

    def test_removes_bom(self):
        desc = "\ufeffNEFT CR"  # BOM character
        result = clean_description(desc)
        assert result == "NEFT CR"

    def test_preserves_case(self):
        assert clean_description("UPI/Rahul Sharma") == "UPI/Rahul Sharma"

    def test_preserves_special_chars(self):
        assert clean_description("NEFT CR-YESB0000001/ACC#123") == "NEFT CR-YESB0000001/ACC#123"

    def test_none_raises(self):
        with pytest.raises(InvalidRowStructureError, match="None"):
            clean_description(None)

    def test_empty_raises(self):
        with pytest.raises(InvalidRowStructureError, match="empty"):
            clean_description("")

    def test_only_whitespace_raises(self):
        with pytest.raises(InvalidRowStructureError, match="empty"):
            clean_description("   \t\n  ")

    def test_only_invisible_chars_raises(self):
        with pytest.raises(InvalidRowStructureError, match="empty"):
            clean_description("\u200b\u200c\u200d")

    def test_unicode_nfc_normalization(self):
        # café decomposed vs composed — should normalize to NFC
        decomposed = "caf\u0065\u0301"   # e + combining accent
        composed   = "caf\u00e9"          # é
        result = clean_description(decomposed)
        assert result == clean_description(composed)


# ---------------------------------------------------------------------------
# 3. Amount Cleaning
# ---------------------------------------------------------------------------

class TestCleanAmount:

    @pytest.mark.parametrize("raw,expected", [
        ("5,596.61",        5596.61),
        (" 5,596.61 ",      5596.61),
        ("₹5,596.61",       5596.61),
        ("0.00",            0.0),
        ("0",               0.0),
        ("100",             100.0),
        ("1,00,000.00",     100000.0),   # Indian lakh format
        ("10,00,000.00",    1000000.0),  # Ten lakh
        ("-500.00",         -500.0),     # Overdraft/reversal
        ("500.",            500.0),      # Trailing decimal
    ])
    def test_valid_amounts(self, raw, expected):
        assert clean_amount(raw) == pytest.approx(expected)

    @pytest.mark.parametrize("raw", [
        "",
        "-",
        "--",
        "—",
        "N/A",
        "n/a",
        "nil",
        "NIL",
        None,
    ])
    def test_blank_values_return_none(self, raw):
        assert clean_amount(raw) is None

    def test_non_numeric_string_raises(self):
        with pytest.raises(InvalidAmountError):
            clean_amount("INVALID")

    def test_excessive_amount_raises(self):
        with pytest.raises(InvalidAmountError, match="realistic"):
            clean_amount("999,999,999,999.00")  # >> 10 crore

    def test_integer_input_converts(self):
        assert clean_amount(5000) == 5000.0

    def test_float_input_passthrough(self):
        assert clean_amount(123.45) == pytest.approx(123.45)


# ---------------------------------------------------------------------------
# 4. Row Structure Validation
# ---------------------------------------------------------------------------

class TestValidateRowStructure:

    def test_valid_row_passes(self):
        validate_row_structure(make_row())  # should not raise

    def test_missing_date_raises(self):
        row = make_row()
        del row["date"]
        with pytest.raises(InvalidRowStructureError, match="date"):
            validate_row_structure(row)

    def test_missing_description_raises(self):
        row = make_row()
        del row["description"]
        with pytest.raises(InvalidRowStructureError, match="description"):
            validate_row_structure(row)

    def test_missing_balance_raises(self):
        row = make_row()
        del row["balance"]
        with pytest.raises(InvalidRowStructureError, match="balance"):
            validate_row_structure(row)

    def test_no_amount_field_raises(self):
        row = {"date": "01/06/25", "description": "TEST", "balance": "1000"}
        with pytest.raises(InvalidRowStructureError, match="no debit or credit"):
            validate_row_structure(row)

    def test_non_dict_input_raises(self):
        with pytest.raises(InvalidRowStructureError, match="dict"):
            validate_row_structure(["date", "desc", "balance"])

    def test_case_insensitive_key_matching(self):
        row = {
            "Date": "01/06/25",
            "DESCRIPTION": "TEST",
            "Balance": "1000",
            "Withdrawal": "500",
        }
        validate_row_structure(row)  # should not raise

    def test_debit_alias_accepted(self):
        row = {"date": "01/06/25", "description": "TEST", "balance": "1000", "debit": "500"}
        validate_row_structure(row)

    def test_credit_alias_accepted(self):
        row = {"date": "01/06/25", "description": "TEST", "balance": "1000", "credit": "500"}
        validate_row_structure(row)


# ---------------------------------------------------------------------------
# 5. Debit / Credit Resolution
# ---------------------------------------------------------------------------

class TestDebitCreditResolution:

    def test_withdrawal_maps_to_debit(self):
        row = make_debit_row()
        result = normalize_transactions([row])
        assert result[0]["debit"] == pytest.approx(2500.0)
        assert result[0]["credit"] is None

    def test_deposit_maps_to_credit(self):
        row = make_row()
        result = normalize_transactions([row])
        assert result[0]["credit"] == pytest.approx(5000.0)
        assert result[0]["debit"] is None

    def test_debit_alias_works(self):
        row = {"date": "01/06/25", "description": "ATM WDL",
               "debit": "1000", "balance": "50000"}
        result = normalize_transactions([row])
        assert result[0]["debit"] == pytest.approx(1000.0)

    def test_credit_alias_works(self):
        row = {"date": "01/06/25", "description": "SALARY",
               "credit": "85000", "balance": "185000"}
        result = normalize_transactions([row])
        assert result[0]["credit"] == pytest.approx(85000.0)

    def test_both_nonzero_raises(self):
        row = make_row(withdrawal="1000", deposit="2000")
        # Single row with both non-null → row skipped, returns empty
        result = normalize_transactions([row])
        assert len(result) == 0

    def test_both_null_raises(self):
        row = make_row(withdrawal="", deposit="")
        # Single row with both null → row skipped, returns empty
        result = normalize_transactions([row])
        assert len(result) == 0

    def test_negative_debit_converted_to_positive(self):
        row = {"date": "01/06/25", "description": "CHARGE",
               "debit": "-500", "balance": "9500"}
        result = normalize_transactions([row])
        assert result[0]["debit"] == pytest.approx(500.0)

    def test_negative_credit_converted_to_positive(self):
        row = {"date": "01/06/25", "description": "REVERSAL",
               "credit": "-200", "balance": "10200"}
        result = normalize_transactions([row])
        assert result[0]["credit"] == pytest.approx(200.0)


# ---------------------------------------------------------------------------
# 6. Balance Validation
# ---------------------------------------------------------------------------

class TestValidateBalance:

    def test_valid_balance(self):
        assert validate_balance("1,00,000.00") == pytest.approx(100000.0)

    def test_zero_balance(self):
        assert validate_balance("0.00") == pytest.approx(0.0)

    def test_none_raises(self):
        with pytest.raises(InvalidBalanceError, match="None"):
            validate_balance(None)

    def test_empty_raises(self):
        with pytest.raises(InvalidBalanceError):
            validate_balance("")

    def test_dash_raises(self):
        with pytest.raises(InvalidBalanceError):
            validate_balance("-")

    def test_non_numeric_raises(self):
        with pytest.raises(InvalidBalanceError):
            validate_balance("INVALID")

    def test_negative_balance_allowed_with_warning(self, caplog):
        import logging
        with caplog.at_level(logging.WARNING):
            result = validate_balance("-5000")
        assert result == pytest.approx(-5000.0)
        assert "overdraft" in caplog.text.lower() or "negative" in caplog.text.lower()


# ---------------------------------------------------------------------------
# 7. Transaction ID
# ---------------------------------------------------------------------------

class TestGenerateTxnId:

    def test_returns_string(self):
        txn_id = generate_txn_id("2025-06-01", "NEFT CR", 500.0, None, 10000.0)
        assert isinstance(txn_id, str)

    def test_16_chars(self):
        txn_id = generate_txn_id("2025-06-01", "NEFT CR", 500.0, None, 10000.0)
        assert len(txn_id) == 16

    def test_deterministic_same_inputs(self):
        a = generate_txn_id("2025-06-01", "NEFT CR", 500.0, None, 10000.0)
        b = generate_txn_id("2025-06-01", "NEFT CR", 500.0, None, 10000.0)
        assert a == b

    def test_different_date_different_id(self):
        a = generate_txn_id("2025-06-01", "NEFT CR", 500.0, None, 10000.0)
        b = generate_txn_id("2025-06-02", "NEFT CR", 500.0, None, 10000.0)
        assert a != b

    def test_different_amount_different_id(self):
        a = generate_txn_id("2025-06-01", "NEFT CR", 500.0, None, 10000.0)
        b = generate_txn_id("2025-06-01", "NEFT CR", 501.0, None, 10000.0)
        assert a != b

    def test_debit_vs_credit_different_id(self):
        a = generate_txn_id("2025-06-01", "TXN", 500.0, None,  10000.0)
        b = generate_txn_id("2025-06-01", "TXN", None,  500.0, 10000.0)
        assert a != b

    def test_only_hex_chars(self):
        txn_id = generate_txn_id("2025-06-01", "TEST", None, 100.0, 5000.0)
        assert all(c in "0123456789abcdef" for c in txn_id)


# ---------------------------------------------------------------------------
# 8. Balance Flow Validation
# ---------------------------------------------------------------------------

class TestValidateBalanceFlow:

    def test_exact_match_no_warning(self, caplog):
        import logging
        with caplog.at_level(logging.WARNING):
            validate_balance_flow(10000.0, 500.0, None, 9500.0, "abc123")
        assert "mismatch" not in caplog.text.lower()

    def test_within_tolerance_no_warning(self, caplog):
        import logging
        with caplog.at_level(logging.WARNING):
            validate_balance_flow(10000.0, 500.0, None, 9500.50, "abc123")
        assert "mismatch" not in caplog.text.lower()

    def test_exceeds_tolerance_logs_warning(self, caplog):
        import logging
        with caplog.at_level(logging.WARNING):
            validate_balance_flow(10000.0, 500.0, None, 9600.0, "abc123")
        assert "mismatch" in caplog.text.lower()

    def test_does_not_raise_on_mismatch(self):
        # Must ONLY warn, never abort
        validate_balance_flow(10000.0, 500.0, None, 0.0, "abc123")  # no raise

    def test_credit_flow_correct(self, caplog):
        import logging
        with caplog.at_level(logging.WARNING):
            validate_balance_flow(10000.0, None, 5000.0, 15000.0, "abc123")
        assert "mismatch" not in caplog.text.lower()


# ---------------------------------------------------------------------------
# 9. Full normalize_transactions() Integration
# ---------------------------------------------------------------------------

class TestNormalizeTransactions:

    def test_single_credit_row_normalized(self):
        rows = [make_row()]
        result = normalize_transactions(rows)
        assert len(result) == 1
        assert result[0]["credit"] == pytest.approx(5000.0)
        assert result[0]["debit"] is None

    def test_single_debit_row_normalized(self):
        rows = [make_debit_row()]
        result = normalize_transactions(rows)
        assert result[0]["debit"] == pytest.approx(2500.0)
        assert result[0]["credit"] is None

    def test_mixed_date_formats_in_same_statement(self):
        rows = [
            make_row(date="01/06/25"),
            make_row(date="02-06-2025"),
            make_row(date="2025-06-03"),
            make_row(date="04.06.2025"),
        ]
        result = normalize_transactions(rows)
        assert len(result) == 4
        assert result[0]["date"] == "2025-06-01"
        assert result[1]["date"] == "2025-06-02"
        assert result[2]["date"] == "2025-06-03"
        assert result[3]["date"] == "2025-06-04"

    def test_blank_withdrawal_field_skipped(self):
        # blank withdrawal = None → only credit counted
        row = make_row(withdrawal="", deposit="3000")
        result = normalize_transactions([row])
        assert result[0]["credit"] == pytest.approx(3000.0)
        assert result[0]["debit"] is None

    def test_blank_deposit_field_skipped(self):
        row = make_row(withdrawal="1500", deposit="")
        result = normalize_transactions([row])
        assert result[0]["debit"] == pytest.approx(1500.0)
        assert result[0]["credit"] is None

    def test_unicode_description_preserved(self):
        row = make_row(description="UPI/रोहित शर्मा/99XXXXXXXX")
        result = normalize_transactions([row])
        assert "रोहित शर्मा" in result[0]["description"]

    def test_trailing_spaces_stripped(self):
        row = make_row(
            date="  01/06/25  ",
            description="  NEFT CR  ",
            balance="  100000.00  ",
            deposit="  5000.00  ",
        )
        result = normalize_transactions([row])
        assert result[0]["date"] == "2025-06-01"
        assert result[0]["description"] == "NEFT CR"

    def test_empty_list_returns_empty(self):
        assert normalize_transactions([]) == []

    def test_non_list_input_raises(self):
        with pytest.raises(ValueError):
            normalize_transactions({"key": "value"})

    def test_one_bad_row_skipped_rest_processed(self):
        rows = [
            make_row(date="01/06/25"),     # good
            make_row(date="INVALID"),       # bad date
            make_row(date="03/06/25"),      # good
        ]
        result = normalize_transactions(rows)
        assert len(result) == 2
        assert result[0]["date"] == "2025-06-01"
        assert result[1]["date"] == "2025-06-03"

    def test_exceeds_corruption_threshold_raises(self):
        # 5 rows, 4 bad = 80% corruption > 20% threshold
        rows = [
            make_row(date="01/06/25"),       # good
            make_row(date="INVALID"),         # bad
            make_row(date="INVALID"),         # bad
            make_row(date="INVALID"),         # bad
            make_row(date="INVALID"),         # bad
        ]
        with pytest.raises(ExcessiveDataCorruptionError):
            normalize_transactions(rows)

    def test_exactly_at_threshold_does_not_raise(self):
        # 10 rows, 2 bad = 20% — exactly at threshold, should NOT raise
        good = make_row()
        bad  = make_row(date="INVALID")
        rows = [good] * 8 + [bad] * 2
        result = normalize_transactions(rows)
        assert len(result) == 8

    def test_large_batch_performance(self):
        """10,000 rows should normalize without error or timeout."""
        rows = [make_row(date="01/06/25") for _ in range(10_000)]
        result = normalize_transactions(rows)
        assert len(result) == 10_000

    def test_balance_continuity_logged_not_raised(self, caplog):
        """Balance mismatch should log warning but not abort."""
        import logging
        rows = [
            {"date": "01/06/25", "description": "SALARY",
             "credit": "85000", "balance": "100000"},  # opening
            {"date": "02/06/25", "description": "RENT",
             "debit": "15000",  "balance": "999999"},  # wrong balance
        ]
        with caplog.at_level(logging.WARNING):
            result = normalize_transactions(rows)
        assert len(result) == 2  # both rows pass
        assert "mismatch" in caplog.text.lower()

    def test_lakh_formatted_amounts_parsed(self):
        row = make_row(deposit="1,00,000.00", balance="2,00,000.00")
        result = normalize_transactions([row])
        assert result[0]["credit"] == pytest.approx(100000.0)
        assert result[0]["balance"] == pytest.approx(200000.0)

    def test_currency_symbol_stripped(self):
        row = make_row(deposit="₹5,596.61", balance="₹1,00,000.00")
        result = normalize_transactions([row])
        assert result[0]["credit"] == pytest.approx(5596.61)

    def test_zero_balance_row_accepted(self):
        row = make_row(balance="0.00", deposit="100")
        result = normalize_transactions([row])
        assert result[0]["balance"] == 0.0


# ---------------------------------------------------------------------------
# 10. Output Schema Contract
# ---------------------------------------------------------------------------

class TestOutputSchemaContract:

    def test_output_has_exactly_six_keys(self):
        result = normalize_transactions([make_row()])
        assert set(result[0].keys()) == {"date", "description", "debit", "credit", "balance", "txn_id"}

    def test_date_is_iso_format(self):
        result = normalize_transactions([make_row()])
        import re
        assert re.match(r"^\d{4}-\d{2}-\d{2}$", result[0]["date"])

    def test_description_is_string(self):
        result = normalize_transactions([make_row()])
        assert isinstance(result[0]["description"], str)

    def test_debit_is_float_or_none(self):
        result = normalize_transactions([make_row()])
        val = result[0]["debit"]
        assert val is None or isinstance(val, float)

    def test_credit_is_float_or_none(self):
        result = normalize_transactions([make_row()])
        val = result[0]["credit"]
        assert val is None or isinstance(val, float)

    def test_balance_is_float(self):
        result = normalize_transactions([make_row()])
        assert isinstance(result[0]["balance"], float)

    def test_txn_id_is_16char_hex_string(self):
        result = normalize_transactions([make_row()])
        txn_id = result[0]["txn_id"]
        assert isinstance(txn_id, str)
        assert len(txn_id) == 16
        assert all(c in "0123456789abcdef" for c in txn_id)

    def test_debit_and_credit_never_both_nonull(self):
        rows = [make_row(), make_debit_row()]
        result = normalize_transactions(rows)
        for row in result:
            assert not (row["debit"] is not None and row["credit"] is not None)

    def test_debit_and_credit_never_both_null(self):
        rows = [make_row(), make_debit_row()]
        result = normalize_transactions(rows)
        for row in result:
            assert not (row["debit"] is None and row["credit"] is None)

    def test_no_string_amounts_in_output(self):
        rows = [make_row(), make_debit_row()]
        result = normalize_transactions(rows)
        for row in result:
            for key in ("debit", "credit", "balance"):
                val = row[key]
                assert not isinstance(val, str), f"{key} is a string: {val!r}"
