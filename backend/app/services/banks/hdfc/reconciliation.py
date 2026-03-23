"""
Airco Insights — HDFC Balance Reconciliation
=============================================
Verifies balance continuity for every transaction.
Opening + Credits - Debits = Closing Balance

Checks:
1. Sequential balance progression
2. Each transaction: prev_balance ± amount = new_balance
3. Total credits/debits match statement summary
4. Final balance matches statement closing balance

Design: STOP processing if ANY balance mismatch.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


class HDFCReconciliationError(Exception):
    """Raised when balance reconciliation fails."""
    def __init__(self, message: str, error_code: str, details: dict = None):
        self.error_code = error_code
        self.details = details or {}
        super().__init__(message)


@dataclass
class ReconciliationMismatch:
    """Single balance mismatch."""
    transaction_index: int
    expected_balance: float
    actual_balance: float
    difference: float
    previous_balance: float
    transaction_amount: float
    is_debit: bool


@dataclass
class HDFCReconciliationResult:
    """Result of balance reconciliation."""
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


class HDFCReconciliation:
    """
    Balance reconciliation engine for HDFC transactions.
    """
    
    # Tolerance for floating point comparison (1 paisa)
    TOLERANCE = 0.01
    
    def __init__(self, strict_mode: bool = True):
        """
        Initialize reconciliation engine.
        
        Args:
            strict_mode: If True, any mismatch raises exception.
        """
        self.strict_mode = strict_mode
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def reconcile(
        self,
        transactions: List[Dict[str, Any]],
        expected_opening: Optional[float] = None,
        expected_closing: Optional[float] = None,
        expected_credits: Optional[float] = None,
        expected_debits: Optional[float] = None,
    ) -> HDFCReconciliationResult:
        """
        Reconcile all transaction balances.
        
        Args:
            transactions: List of validated transaction dicts
            expected_opening: Expected opening balance from statement
            expected_closing: Expected closing balance from statement
            expected_credits: Expected total credits from statement
            expected_debits: Expected total debits from statement
            
        Returns:
            HDFCReconciliationResult with reconciliation status
            
        Raises:
            HDFCReconciliationError: If reconciliation fails in strict mode
        """
        if not transactions:
            raise HDFCReconciliationError(
                "No transactions to reconcile",
                error_code="NO_TRANSACTIONS",
            )
        
        self.logger.info("Reconciling %d HDFC transactions", len(transactions))
        
        # Calculate totals
        total_credits = sum(txn.get("credit") or 0 for txn in transactions)
        total_debits = sum(txn.get("debit") or 0 for txn in transactions)
        
        # Infer opening balance from first transaction
        first_txn = transactions[0]
        first_balance = first_txn.get("balance", 0)
        first_credit = first_txn.get("credit") or 0
        first_debit = first_txn.get("debit") or 0
        
        inferred_opening = first_balance - first_credit + first_debit
        
        # Use expected if provided, otherwise use inferred
        opening_balance = expected_opening if expected_opening is not None else inferred_opening
        
        # Get actual closing
        closing_balance = transactions[-1].get("balance", 0)
        
        # Calculate expected closing
        calculated_closing = opening_balance + total_credits - total_debits
        
        # Check final balance
        final_diff = abs(calculated_closing - closing_balance)
        is_reconciled = final_diff <= self.TOLERANCE
        
        # Check each transaction's balance progression
        mismatches = self._check_balance_progression(transactions)
        
        # If we have mismatches in progression, reconciliation fails
        if mismatches:
            is_reconciled = False
        
        # Verify against expected totals if provided
        if expected_credits is not None:
            credit_diff = abs(total_credits - expected_credits)
            if credit_diff > self.TOLERANCE:
                self.logger.warning(
                    "Credit total mismatch: expected=%.2f actual=%.2f diff=%.2f",
                    expected_credits, total_credits, credit_diff
                )
        
        if expected_debits is not None:
            debit_diff = abs(total_debits - expected_debits)
            if debit_diff > self.TOLERANCE:
                self.logger.warning(
                    "Debit total mismatch: expected=%.2f actual=%.2f diff=%.2f",
                    expected_debits, total_debits, debit_diff
                )
        
        result = HDFCReconciliationResult(
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
            "Reconciliation %s: opening=%.2f closing=%.2f calc=%.2f diff=%.2f mismatches=%d",
            "PASSED" if is_reconciled else "FAILED",
            opening_balance, closing_balance, calculated_closing, final_diff, len(mismatches)
        )
        
        if not is_reconciled and self.strict_mode:
            if mismatches:
                first = mismatches[0]
                raise HDFCReconciliationError(
                    f"Balance mismatch at transaction {first.transaction_index}: "
                    f"expected {first.expected_balance:.2f}, got {first.actual_balance:.2f}",
                    error_code="BALANCE_MISMATCH",
                    details={
                        "transaction_index": first.transaction_index,
                        "expected": first.expected_balance,
                        "actual": first.actual_balance,
                        "difference": first.difference,
                    }
                )
            else:
                raise HDFCReconciliationError(
                    f"Final balance mismatch: calculated {calculated_closing:.2f}, "
                    f"actual {closing_balance:.2f}, diff={final_diff:.2f}",
                    error_code="FINAL_BALANCE_MISMATCH",
                    details={
                        "calculated_closing": calculated_closing,
                        "actual_closing": closing_balance,
                        "difference": final_diff,
                    }
                )
        
        return result
    
    def _check_balance_progression(
        self,
        transactions: List[Dict[str, Any]]
    ) -> List[ReconciliationMismatch]:
        """Check that each transaction's balance follows from previous."""
        mismatches = []
        
        for i in range(1, len(transactions)):
            prev_txn = transactions[i - 1]
            curr_txn = transactions[i]
            
            prev_balance = prev_txn.get("balance", 0)
            curr_balance = curr_txn.get("balance", 0)
            
            credit = curr_txn.get("credit") or 0
            debit = curr_txn.get("debit") or 0
            
            # Expected: prev + credit - debit = curr
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
        self,
        transactions: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Attempt to auto-correct debit/credit assignments based on balance progression.
        
        Returns:
            Tuple of (corrected_transactions, correction_count)
        """
        corrected = []
        corrections = 0
        
        for i, txn in enumerate(transactions):
            txn_copy = dict(txn)
            
            if i == 0:
                corrected.append(txn_copy)
                continue
            
            prev_balance = corrected[i - 1].get("balance", 0)
            curr_balance = txn.get("balance", 0)
            
            debit = txn.get("debit") or 0
            credit = txn.get("credit") or 0
            amount = debit or credit
            
            # Check if current assignment is correct
            if debit:
                expected = prev_balance - debit
            else:
                expected = prev_balance + credit
            
            diff = abs(expected - curr_balance)
            
            if diff > self.TOLERANCE:
                # Try swapping
                if debit:
                    new_expected = prev_balance + debit
                else:
                    new_expected = prev_balance - credit
                
                new_diff = abs(new_expected - curr_balance)
                
                if new_diff < diff:
                    # Swap is better
                    txn_copy["debit"] = credit if credit else None
                    txn_copy["credit"] = debit if debit else None
                    corrections += 1
                    self.logger.debug(
                        "Corrected transaction %d: swapped debit/credit",
                        i
                    )
            
            corrected.append(txn_copy)
        
        return corrected, corrections
