"""
Airco Insights — ICICI Bank Aggregation Engine
===============================================
Financial analytics and aggregation for ICICI Bank transactions.
"""

import logging
from typing import List, Dict, Any
from collections import defaultdict
from datetime import datetime
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class CategorySummary:
    category: str
    total_amount: float
    transaction_count: int
    avg_amount: float
    percentage: float


@dataclass
class MonthlySummary:
    month: str
    total_credits: float
    total_debits: float
    net_flow: float
    transaction_count: int
    credit_count: int
    debit_count: int


@dataclass
class ICICIAggregationResult:
    debit_categories:    List[CategorySummary]
    credit_categories:   List[CategorySummary]
    monthly_summaries:   List[MonthlySummary]
    weekly_credits:      Dict[str, float]
    weekly_debits:       Dict[str, float]
    recurring_total:     float
    one_time_total:      float
    recurring_count:     int
    one_time_count:      int
    top_debit_merchants: List[Dict[str, Any]]
    top_credit_merchants: List[Dict[str, Any]]
    total_credits:       float
    total_debits:        float
    opening_balance:     float
    closing_balance:     float

    def to_dict(self) -> dict:
        return {
            "debit_categories":  [
                {"category": c.category, "total": c.total_amount,
                 "count": c.transaction_count, "avg": c.avg_amount,
                 "percentage": c.percentage}
                for c in self.debit_categories
            ],
            "credit_categories": [
                {"category": c.category, "total": c.total_amount,
                 "count": c.transaction_count, "avg": c.avg_amount,
                 "percentage": c.percentage}
                for c in self.credit_categories
            ],
            "monthly": [
                {"month": m.month, "credits": m.total_credits, "debits": m.total_debits,
                 "net": m.net_flow, "count": m.transaction_count}
                for m in self.monthly_summaries
            ],
            "weekly_credits": self.weekly_credits,
            "weekly_debits":  self.weekly_debits,
            "recurring":      {"total": self.recurring_total, "count": self.recurring_count},
            "one_time":       {"total": self.one_time_total,  "count": self.one_time_count},
            "totals": {
                "credits": self.total_credits, "debits": self.total_debits,
                "opening": self.opening_balance, "closing": self.closing_balance,
            },
        }


class ICICIAggregationEngine:
    TOP_MERCHANTS_LIMIT = 10

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def aggregate(
        self,
        transactions: List[Dict[str, Any]],
        opening_balance: float = 0,
        closing_balance: float = 0,
    ) -> ICICIAggregationResult:
        self.logger.info("Aggregating %d ICICI transactions", len(transactions))

        total_credits     = sum(t.get("credit") or 0 for t in transactions)
        total_debits      = sum(t.get("debit")  or 0 for t in transactions)
        debit_categories  = self._aggregate_categories(transactions, is_debit=True)
        credit_categories = self._aggregate_categories(transactions, is_debit=False)
        monthly_summaries = self._aggregate_monthly(transactions)
        weekly_credits, weekly_debits = self._aggregate_weekly(transactions)
        recurring_stats   = self._aggregate_recurring(transactions)

        return ICICIAggregationResult(
            debit_categories=debit_categories,
            credit_categories=credit_categories,
            monthly_summaries=monthly_summaries,
            weekly_credits=weekly_credits,
            weekly_debits=weekly_debits,
            recurring_total=recurring_stats["recurring_total"],
            one_time_total=recurring_stats["one_time_total"],
            recurring_count=recurring_stats["recurring_count"],
            one_time_count=recurring_stats["one_time_count"],
            top_debit_merchants=self._get_top_merchants(transactions, True),
            top_credit_merchants=self._get_top_merchants(transactions, False),
            total_credits=total_credits,
            total_debits=total_debits,
            opening_balance=opening_balance,
            closing_balance=closing_balance,
        )

    def _aggregate_categories(self, transactions, is_debit):
        cat_data = defaultdict(lambda: {"total": 0, "count": 0})
        for txn in transactions:
            if is_debit and txn.get("debit"):
                cat_data[txn.get("category", "Others Debit")]["total"] += txn["debit"]
                cat_data[txn.get("category", "Others Debit")]["count"] += 1
            elif not is_debit and txn.get("credit"):
                cat_data[txn.get("category", "Others Credit")]["total"] += txn["credit"]
                cat_data[txn.get("category", "Others Credit")]["count"] += 1
        grand_total = sum(d["total"] for d in cat_data.values())
        summaries = []
        for cat, data in cat_data.items():
            avg = data["total"] / data["count"] if data["count"] > 0 else 0
            pct = (data["total"] / grand_total * 100) if grand_total > 0 else 0
            summaries.append(CategorySummary(
                category=cat, total_amount=round(data["total"], 2),
                transaction_count=data["count"], avg_amount=round(avg, 2),
                percentage=round(pct, 1),
            ))
        summaries.sort(key=lambda x: x.total_amount, reverse=True)
        return summaries

    def _aggregate_monthly(self, transactions):
        monthly_data = defaultdict(lambda: {
            "credits": 0, "debits": 0, "count": 0,
            "credit_count": 0, "debit_count": 0
        })
        for txn in transactions:
            date_str = txn.get("date", "")
            if not date_str or len(date_str) < 7:
                continue
            try:
                month_key = date_str[:7] if date_str[4] == "-" else None
                if not month_key:
                    continue
            except IndexError:
                continue
            monthly_data[month_key]["credits"] += txn.get("credit") or 0
            monthly_data[month_key]["debits"]  += txn.get("debit")  or 0
            monthly_data[month_key]["count"]   += 1
            if (txn.get("credit") or 0) > 0: monthly_data[month_key]["credit_count"] += 1
            if (txn.get("debit")  or 0) > 0: monthly_data[month_key]["debit_count"]  += 1
        return [
            MonthlySummary(
                month=m,
                total_credits=round(d["credits"], 2),
                total_debits=round(d["debits"],   2),
                net_flow=round(d["credits"] - d["debits"], 2),
                transaction_count=d["count"],
                credit_count=d["credit_count"],
                debit_count=d["debit_count"],
            )
            for m, d in sorted(monthly_data.items())
        ]

    def _aggregate_weekly(self, transactions):
        weekly_credits = defaultdict(float)
        weekly_debits  = defaultdict(float)
        for txn in transactions:
            date_str = txn.get("date", "")
            if not date_str:
                continue
            try:
                dt   = datetime.strptime(date_str, "%Y-%m-%d")
                y, w, _ = dt.isocalendar()
                key  = f"{y}-W{w:02d}"
                weekly_credits[key] += txn.get("credit") or 0
                weekly_debits[key]  += txn.get("debit")  or 0
            except ValueError:
                continue
        return dict(weekly_credits), dict(weekly_debits)

    def _aggregate_recurring(self, transactions):
        rt = ot = 0.0
        rc = oc = 0
        for txn in transactions:
            amount = (txn.get("debit") or 0) + (txn.get("credit") or 0)
            if txn.get("is_recurring"):
                rt += amount; rc += 1
            else:
                ot += amount; oc += 1
        return {
            "recurring_total": round(rt, 2), "one_time_total": round(ot, 2),
            "recurring_count": rc,           "one_time_count": oc,
        }

    def _get_top_merchants(self, transactions, is_debit):
        data = defaultdict(lambda: {"total": 0, "count": 0})
        for txn in transactions:
            if is_debit and not txn.get("debit"):  continue
            if not is_debit and not txn.get("credit"): continue
            merchant = (txn.get("description") or "Unknown")[:35].strip()
            amount   = txn.get("debit") or txn.get("credit") or 0
            data[merchant]["total"] += amount
            data[merchant]["count"] += 1
        return [
            {"merchant": m, "total": round(d["total"], 2), "count": d["count"]}
            for m, d in sorted(data.items(), key=lambda x: x[1]["total"], reverse=True)[:self.TOP_MERCHANTS_LIMIT]
        ]
