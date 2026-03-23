"""
Tests for Airco Insights — AI Classifier (Claude Fallback Layer)
=================================================================
Covers cost estimation, batch preparation, response validation,
direction safety, overflow handling, and integration.

Test groups:
    1.  Cost estimation — correct math, limits
    2.  Batch preparation — correct structure
    3.  Response validation — category safety, direction enforcement
    4.  Overflow handling — MAX_AI_TRANSACTIONS and MAX_AI_CALLS
    5.  Input validation — bad types, empty lists, missing API key
    6.  Non-mutation — originals untouched
    7.  Output schema — correct keys and types
    8.  Claude call mock — end-to-end with mocked API
"""

import copy
import json
import pytest
from unittest.mock import patch, MagicMock

from app.services.ai_classifier import (
    estimate_ai_cost,
    _prepare_batch,
    _validate_ai_response,
    classify_with_ai,
    BATCH_SIZE,
    MAX_AI_CALLS,
    MAX_AI_TRANSACTIONS,
    AI_CONFIDENCE_DEFAULT,
    AI_SOURCE,
    ALLOWED_CREDIT_CATEGORIES,
    ALLOWED_DEBIT_CATEGORIES,
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
) -> dict:
    return {
        "date": date,
        "description": description,
        "debit": debit,
        "credit": credit,
        "balance": balance,
        "txn_id": txn_id,
    }


def debit_txn(desc: str, **kw) -> dict:
    return make_txn(desc, debit=5000.0, **kw)


def credit_txn(desc: str, **kw) -> dict:
    return make_txn(desc, credit=5000.0, **kw)


# ---------------------------------------------------------------------------
# 1. Cost Estimation
# ---------------------------------------------------------------------------

class TestCostEstimation:

    def test_small_batch(self):
        result = estimate_ai_cost(10)
        assert result["ai_transactions"] == 10
        assert result["remaining_as_others"] == 0
        assert result["estimated_batches"] == 1
        assert result["estimated_claude_calls"] == 1
        assert result["estimated_cost_inr"] >= 0

    def test_exact_batch_size(self):
        result = estimate_ai_cost(25)
        assert result["estimated_batches"] == 1

    def test_multiple_batches(self):
        result = estimate_ai_cost(60)
        assert result["estimated_batches"] == 3  # ceil(60/25) = 3

    def test_exceeds_max_transactions(self):
        result = estimate_ai_cost(500)
        assert result["ai_transactions"] == MAX_AI_TRANSACTIONS
        assert result["remaining_as_others"] == 200

    def test_exceeds_max_calls(self):
        result = estimate_ai_cost(300)
        # 300/25 = 12, but capped at 10
        assert result["estimated_batches"] == 10

    def test_zero_transactions(self):
        result = estimate_ai_cost(0)
        assert result["ai_transactions"] == 0
        assert result["estimated_cost_inr"] == 0.0

    def test_returns_all_required_keys(self):
        result = estimate_ai_cost(50)
        required_keys = {
            "total_transactions", "ai_transactions", "remaining_as_others",
            "estimated_batches", "estimated_claude_calls",
            "estimated_cost_usd", "estimated_cost_inr",
            "max_ai_calls", "max_ai_transactions", "batch_size",
        }
        assert set(result.keys()) == required_keys


# ---------------------------------------------------------------------------
# 2. Batch Preparation
# ---------------------------------------------------------------------------

class TestBatchPreparation:

    def test_debit_transaction(self):
        batch = _prepare_batch([debit_txn("ATM CASH")])
        assert len(batch) == 1
        assert batch[0]["type"] == "debit"
        assert batch[0]["amount"] == 5000.0
        assert batch[0]["description"] == "ATM CASH"
        assert batch[0]["id"] == 1

    def test_credit_transaction(self):
        batch = _prepare_batch([credit_txn("SALARY")])
        assert batch[0]["type"] == "credit"
        assert batch[0]["amount"] == 5000.0

    def test_multiple_transactions(self):
        txns = [debit_txn("A"), credit_txn("B"), debit_txn("C")]
        batch = _prepare_batch(txns)
        assert len(batch) == 3
        assert batch[0]["id"] == 1
        assert batch[1]["id"] == 2
        assert batch[2]["id"] == 3

    def test_empty_list(self):
        assert _prepare_batch([]) == []


# ---------------------------------------------------------------------------
# 3. Response Validation
# ---------------------------------------------------------------------------

class TestResponseValidation:

    def test_valid_debit_category(self):
        txns = [debit_txn("TEST")]
        response = [{"id": 1, "category": "Shopping", "confidence": 0.90}]
        result = _validate_ai_response(response, txns)
        assert len(result) == 1
        assert result[0]["category"] == "Shopping"

    def test_valid_credit_category(self):
        txns = [credit_txn("TEST")]
        response = [{"id": 1, "category": "Salary", "confidence": 0.90}]
        result = _validate_ai_response(response, txns)
        assert result[0]["category"] == "Salary"

    def test_invalid_category_falls_back_to_others(self):
        txns = [debit_txn("TEST")]
        response = [{"id": 1, "category": "MADE UP CATEGORY", "confidence": 0.90}]
        result = _validate_ai_response(response, txns)
        assert result[0]["category"] == "Others Debit"

    def test_credit_category_on_debit_corrected(self):
        txns = [debit_txn("TEST")]
        response = [{"id": 1, "category": "Salary", "confidence": 0.90}]
        result = _validate_ai_response(response, txns)
        assert result[0]["category"] == "Others Debit"

    def test_debit_category_on_credit_corrected(self):
        txns = [credit_txn("TEST")]
        response = [{"id": 1, "category": "ATM Withdrawal", "confidence": 0.90}]
        result = _validate_ai_response(response, txns)
        assert result[0]["category"] == "Others Credit"

    def test_invalid_id_skipped(self):
        txns = [debit_txn("TEST")]
        response = [{"id": 999, "category": "Shopping", "confidence": 0.90}]
        result = _validate_ai_response(response, txns)
        assert len(result) == 0

    def test_missing_confidence_uses_default(self):
        txns = [debit_txn("TEST")]
        response = [{"id": 1, "category": "Shopping"}]
        result = _validate_ai_response(response, txns)
        assert result[0]["confidence"] == AI_CONFIDENCE_DEFAULT

    def test_confidence_clamped_to_0_1(self):
        txns = [debit_txn("TEST")]
        response = [{"id": 1, "category": "Shopping", "confidence": 1.5}]
        result = _validate_ai_response(response, txns)
        assert result[0]["confidence"] == 1.0

    def test_negative_confidence_clamped(self):
        txns = [debit_txn("TEST")]
        response = [{"id": 1, "category": "Shopping", "confidence": -0.5}]
        result = _validate_ai_response(response, txns)
        assert result[0]["confidence"] == 0.0

    def test_others_credit_allowed(self):
        txns = [credit_txn("TEST")]
        response = [{"id": 1, "category": "Others Credit", "confidence": 0.5}]
        result = _validate_ai_response(response, txns)
        assert result[0]["category"] == "Others Credit"

    def test_others_debit_allowed(self):
        txns = [debit_txn("TEST")]
        response = [{"id": 1, "category": "Others Debit", "confidence": 0.5}]
        result = _validate_ai_response(response, txns)
        assert result[0]["category"] == "Others Debit"


# ---------------------------------------------------------------------------
# 4. Input Validation
# ---------------------------------------------------------------------------

class TestInputValidation:

    def test_non_list_raises(self):
        with pytest.raises(ValueError, match="list"):
            classify_with_ai({"bad": "input"}, api_key="sk-test")

    def test_empty_list_returns_empty(self):
        result = classify_with_ai([], api_key="sk-test")
        assert result == []

    def test_missing_api_key_raises(self):
        with pytest.raises(ValueError, match="API key"):
            classify_with_ai([debit_txn("TEST")], api_key="")

    def test_none_api_key_raises(self):
        with pytest.raises(ValueError, match="API key"):
            classify_with_ai([debit_txn("TEST")], api_key=None)


# ---------------------------------------------------------------------------
# 5. Non-Mutation
# ---------------------------------------------------------------------------

class TestNonMutation:

    @patch("app.services.ai_classifier._call_claude")
    def test_original_not_mutated(self, mock_claude):
        mock_claude.return_value = [
            {"id": 1, "category": "Shopping", "confidence": 0.85}
        ]
        original = debit_txn("RANDOM PURCHASE")
        original_copy = copy.deepcopy(original)
        classify_with_ai([original], api_key="sk-test")
        assert original == original_copy


# ---------------------------------------------------------------------------
# 6. Output Schema
# ---------------------------------------------------------------------------

class TestOutputSchema:

    @patch("app.services.ai_classifier._call_claude")
    def test_classified_has_required_keys(self, mock_claude):
        mock_claude.return_value = [
            {"id": 1, "category": "Shopping", "confidence": 0.85}
        ]
        result = classify_with_ai([debit_txn("TEST")], api_key="sk-test")
        txn = result[0]
        for key in ("date", "description", "debit", "credit", "balance",
                     "txn_id", "category", "confidence", "source"):
            assert key in txn, f"Missing key: {key}"

    @patch("app.services.ai_classifier._call_claude")
    def test_source_is_ai_classifier(self, mock_claude):
        mock_claude.return_value = [
            {"id": 1, "category": "Shopping", "confidence": 0.85}
        ]
        result = classify_with_ai([debit_txn("TEST")], api_key="sk-test")
        assert result[0]["source"] == AI_SOURCE


# ---------------------------------------------------------------------------
# 7. End-to-End with Mock
# ---------------------------------------------------------------------------

class TestEndToEnd:

    @patch("app.services.ai_classifier._call_claude")
    def test_single_batch_classification(self, mock_claude):
        mock_claude.return_value = [
            {"id": 1, "category": "Shopping", "confidence": 0.88},
            {"id": 2, "category": "Salary", "confidence": 0.92},
        ]
        txns = [
            debit_txn("SOME STORE PURCHASE", txn_id="t1"),
            credit_txn("MONTHLY INCOME", txn_id="t2"),
        ]
        result = classify_with_ai(txns, api_key="sk-test")
        assert len(result) == 2
        assert result[0]["category"] == "Shopping"
        assert result[1]["category"] == "Salary"
        mock_claude.assert_called_once()

    @patch("app.services.ai_classifier._call_claude")
    def test_multiple_batches(self, mock_claude):
        # Create 60 transactions → should trigger 3 batches (25+25+10)
        txns = [debit_txn(f"TXN {i}", txn_id=f"t{i}") for i in range(60)]
        mock_claude.return_value = [
            {"id": i + 1, "category": "Others Debit", "confidence": 0.80}
            for i in range(BATCH_SIZE)
        ]
        result = classify_with_ai(txns, api_key="sk-test")
        assert len(result) == 60
        assert mock_claude.call_count == 3

    @patch("app.services.ai_classifier._call_claude")
    def test_api_failure_tags_as_error(self, mock_claude):
        mock_claude.side_effect = RuntimeError("API down")
        txns = [debit_txn("TEST", txn_id="t1")]
        result = classify_with_ai(txns, api_key="sk-test")
        assert len(result) == 1
        assert result[0]["category"] == "Others Debit"
        assert result[0]["source"] == "ai_error"

    @patch("app.services.ai_classifier._call_claude")
    def test_direction_safety_enforced(self, mock_claude):
        """AI returns wrong direction → system corrects it."""
        mock_claude.return_value = [
            {"id": 1, "category": "Salary", "confidence": 0.90},  # Wrong! debit txn
        ]
        txns = [debit_txn("TEST", txn_id="t1")]
        result = classify_with_ai(txns, api_key="sk-test")
        assert result[0]["category"] == "Others Debit"  # Corrected

    @patch("app.services.ai_classifier._call_claude")
    def test_overflow_tagged_correctly(self, mock_claude):
        """Transactions beyond MAX_AI_TRANSACTIONS → Others."""
        mock_claude.return_value = [
            {"id": i + 1, "category": "Others Debit", "confidence": 0.80}
            for i in range(BATCH_SIZE)
        ]
        txns = [debit_txn(f"TXN {i}", txn_id=f"t{i}") for i in range(MAX_AI_TRANSACTIONS + 50)]
        result = classify_with_ai(txns, api_key="sk-test")
        assert len(result) == MAX_AI_TRANSACTIONS + 50
        # Last 50 should be limit_overflow
        for txn in result[MAX_AI_TRANSACTIONS:]:
            assert txn["source"] == "limit_overflow"

    @patch("app.services.ai_classifier._call_claude")
    def test_missed_transactions_tagged(self, mock_claude):
        """If AI doesn't return all IDs, missed ones get Others."""
        mock_claude.return_value = [
            {"id": 1, "category": "Shopping", "confidence": 0.85},
            # ID 2 missing from response
        ]
        txns = [
            debit_txn("STORE", txn_id="t1"),
            debit_txn("RANDOM", txn_id="t2"),
        ]
        result = classify_with_ai(txns, api_key="sk-test")
        assert result[0]["category"] == "Shopping"
        assert result[1]["category"] == "Others Debit"
        assert result[1]["source"] == "ai_missed"
