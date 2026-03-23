"""
Airco Insights — Axis Bank Balance Reconciliation
==================================================
Verifies balance continuity: Opening + Credits - Debits = Closing Balance.
Shared logic with HDFC, renamed for Axis Bank module isolation.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


class AxisReconciliationError(Exception):
    def __init__(self, message: str, error_code: str, details: dict = None):
        self.error_code = error_code
        self.details = details or {}
        super().__init__(message)


@dataclass
class ReconciliationMismatch:
    transaction_index: int
    expected_balance: float
    actual_balance: float
    difference: float
    previous_balance: float
    transaction_amount: float
    is_debit: bool


@dataclass
class AxisReconciliationResult:
    is_reconciled: bool
    opening_balance: float
    closing_balance: float
    total_credits: float
    total_debits: float
    calculated_closing: float
    final_difference: float
    transaction_count: int
    mismatches: List[ReconciliationMismatch] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "is_reconciled": self.is_reconciled,
            "opening_balance": self.opening_balance,
            "closing_balance": self.closing_balance,
            "total_credits": self.total_credits,
            "total_debits": self.total_debits,
            "calculated_closing": self.calculated_closing,
            "final_difference": self.final_difference,
            "transaction_count": self.transaction_count,
            "mismatch_count": len(self.mismatches),
        }


class AxisReconciliation:
    """Balance reconciliation engine for Axis Bank transactions."""

    TOLERANCE = 0.01

    def __init__(self, strict_mode: bool = True):
        self.strict_mode = strict_mode
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def reconcile(
        self,
        transactions: List[Dict[str, Any]],
        expected_opening: Optional[float] = None,
        expected_closing: Optional[float] = None,
        expected_credits: Optional[float] = None,
        expected_debits: Optional[float] = None,
    ) -> AxisReconciliationResult:
        """Reconcile all transaction balances."""
        if not transactions:
            raise AxisReconciliationError("No transactions to reconcile", error_code="NO_TRANSACTIONS")

        self.logger.info("Reconciling %d Axis Bank transactions", len(transactions))

        total_credits = sum(txn.get("credit") or 0 for txn in transactions)
        total_debits  = sum(txn.get("debit")  or 0 for txn in transactions)

        first_txn = transactions[0]
        first_balance = first_txn.get("balance", 0)
        first_credit  = first_txn.get("credit") or 0
        first_debit   = first_txn.get("debit")  or 0
        inferred_opening = first_balance - first_credit + first_debit

        opening_balance = expected_opening if expected_opening is not None else inferred_opening
        closing_balance = transactions[-1].get("balance", 0)
        calculated_closing = opening_balance + total_credits - total_debits
        final_diff = abs(calculated_closing - closing_balance)
        is_reconciled = final_diff <= self.TOLERANCE

        mismatches = self._check_balance_progression(transactions)
        if mismatches:
            is_reconciled = False

        result = AxisReconciliationResult(
            is_reconciled=is_reconciled,
            opening_balance=opening_balance,
            closing_balance=closing_balance,
            total_credits=total_credits,
            total_debits=total_debits,
            calculated_closing=calculated_closing,
            final_difference=final_diff,
            transaction_count=len(transactions),
            mismatches=mismatches,
        )

        self.logger.info(
            "Reconciliation %s: opening=%.2f closing=%.2f diff=%.4f mismatches=%d",
            "PASSED" if is_reconciled else "FAILED",
            opening_balance, closing_balance, final_diff, len(mismatches)
        )

        if not is_reconciled and self.strict_mode and mismatches:
            first = mismatches[0]
            raise AxisReconciliationError(
                f"Balance mismatch at transaction {first.transaction_index}: "
                f"expected {first.expected_balance:.2f}, got {first.actual_balance:.2f}",
                error_code="BALANCE_MISMATCH",
                details={"transaction_index": first.transaction_index},
            )

        return result

    def _check_balance_progression(
        self, transactions: List[Dict[str, Any]]
    ) -> List[ReconciliationMismatch]:
        mismatches = []
        for i in range(1, len(transactions)):
            prev = transactions[i - 1]
            curr = transactions[i]
            prev_balance = prev.get("balance", 0)
            curr_balance = curr.get("balance", 0)
            credit = curr.get("credit") or 0
            debit  = curr.get("debit")  or 0
            expected_balance = prev_balance + credit - debit
            diff = abs(expected_balance - curr_balance)
            if diff > self.TOLERANCE:
                mismatches.append(ReconciliationMismatch(
                    transaction_index=i,
                    expected_balance=expected_balance,
                    actual_balance=curr_balance,
                    difference=diff,
                    previous_balance=prev_balance,
                    transaction_amount=credit if credit else debit,
                    is_debit=debit > 0,
                ))
        return mismatches

    def auto_correct_debit_credit(
        self, transactions: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Auto-correct debit/credit assignments based on balance progression."""
        corrected = []
        corrections = 0

        for i, txn in enumerate(transactions):
            txn_copy = dict(txn)
            if i == 0:
                corrected.append(txn_copy)
                continue

            prev_balance = corrected[i - 1].get("balance", 0)
            curr_balance = txn.get("balance", 0)
            debit  = txn.get("debit")  or 0
            credit = txn.get("credit") or 0

            if debit:
                expected = prev_balance - debit
            else:
                expected = prev_balance + credit

            diff = abs(expected - curr_balance)

            if diff > self.TOLERANCE:
                if debit:
                    new_expected = prev_balance + debit
                else:
                    new_expected = prev_balance - credit

                new_diff = abs(new_expected - curr_balance)
                if new_diff < diff:
                    txn_copy["debit"]  = credit if credit else None
                    txn_copy["credit"] = debit  if debit  else None
                    corrections += 1

            corrected.append(txn_copy)

        return corrected, corrections
