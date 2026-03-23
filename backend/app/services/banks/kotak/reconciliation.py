"""
Airco Insights — Kotak Bank Balance Reconciliation
===================================================
Verifies balance continuity: Opening + Credits - Debits = Closing Balance.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


class KotakReconciliationError(Exception):
    def __init__(self, message: str, error_code: str, details: dict = None):
        self.error_code = error_code
        self.details    = details or {}
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
class KotakReconciliationResult:
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
            "is_reconciled":     self.is_reconciled,
            "opening_balance":   self.opening_balance,
            "closing_balance":   self.closing_balance,
            "total_credits":     self.total_credits,
            "total_debits":      self.total_debits,
            "calculated_closing": self.calculated_closing,
            "final_difference":  self.final_difference,
            "transaction_count": self.transaction_count,
            "mismatch_count":    len(self.mismatches),
        }


class KotakReconciliation:
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
        expected_debits:  Optional[float] = None,
    ) -> KotakReconciliationResult:
        if not transactions:
            raise KotakReconciliationError("No transactions to reconcile", error_code="NO_TRANSACTIONS")

        self.logger.info("Reconciling %d Kotak transactions", len(transactions))

        total_credits = sum(t.get("credit") or 0 for t in transactions)
        total_debits  = sum(t.get("debit")  or 0 for t in transactions)

        first          = transactions[0]
        inferred_open  = first.get("balance", 0) - (first.get("credit") or 0) + (first.get("debit") or 0)
        opening_balance = expected_opening if expected_opening is not None else inferred_open

        closing_balance    = transactions[-1].get("balance", 0)
        calculated_closing = opening_balance + total_credits - total_debits
        final_diff         = abs(calculated_closing - closing_balance)
        is_reconciled      = final_diff <= self.TOLERANCE

        mismatches = self._check_balance_progression(transactions)
        if mismatches:
            is_reconciled = False

        self.logger.info(
            "Kotak reconciliation %s: opening=%.2f closing=%.2f diff=%.4f mismatches=%d",
            "PASSED" if is_reconciled else "FAILED",
            opening_balance, closing_balance, final_diff, len(mismatches),
        )

        return KotakReconciliationResult(
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

    def _check_balance_progression(self, transactions):
        mismatches = []
        for i in range(1, len(transactions)):
            prev     = transactions[i - 1]
            curr     = transactions[i]
            prev_bal = prev.get("balance", 0)
            curr_bal = curr.get("balance", 0)
            credit   = curr.get("credit") or 0
            debit    = curr.get("debit")  or 0
            expected = prev_bal + credit - debit
            diff     = abs(expected - curr_bal)
            if diff > self.TOLERANCE:
                mismatches.append(ReconciliationMismatch(
                    transaction_index=i,
                    expected_balance=expected,
                    actual_balance=curr_bal,
                    difference=diff,
                    previous_balance=prev_bal,
                    transaction_amount=credit if credit else debit,
                    is_debit=debit > 0,
                ))
        return mismatches

    def auto_correct_debit_credit(
        self, transactions: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], int]:
        corrected   = []
        corrections = 0
        for i, txn in enumerate(transactions):
            txn_copy = dict(txn)
            if i == 0:
                corrected.append(txn_copy)
                continue
            prev_bal = corrected[i - 1].get("balance", 0)
            curr_bal = txn.get("balance", 0)
            debit    = txn.get("debit")  or 0
            credit   = txn.get("credit") or 0
            expected = (prev_bal - debit) if debit else (prev_bal + credit)
            diff     = abs(expected - curr_bal)
            if diff > self.TOLERANCE:
                new_expected = (prev_bal + debit) if debit else (prev_bal - credit)
                if abs(new_expected - curr_bal) < diff:
                    txn_copy["debit"]  = credit if credit else None
                    txn_copy["credit"] = debit  if debit  else None
                    corrections += 1
            corrected.append(txn_copy)
        return corrected, corrections
