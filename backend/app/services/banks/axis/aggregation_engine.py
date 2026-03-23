"""
Airco Insights — Axis Bank Aggregation Engine
==============================================
Financial analytics and aggregation for Axis Bank transactions.
"""

import logging
from typing import List, Dict, Any, Optional
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
class AxisAggregationResult:
    debit_categories: List[CategorySummary]
    credit_categories: List[CategorySummary]
    monthly_summaries: List[MonthlySummary]
    weekly_credits: Dict[str, float]
    weekly_debits: Dict[str, float]
    recurring_total: float
    one_time_total: float
    recurring_count: int
    one_time_count: int
    top_debit_merchants: List[Dict[str, Any]]
    top_credit_merchants: List[Dict[str, Any]]
    total_credits: float
    total_debits: float
    opening_balance: float
    closing_balance: float

    def to_dict(self) -> dict:
        return {
            "debit_categories": [
                {"category": c.category, "total": c.total_amount,
                 "count": c.transaction_count, "avg": c.avg_amount, "percentage": c.percentage}
                for c in self.debit_categories
            ],
            "credit_categories": [
                {"category": c.category, "total": c.total_amount,
                 "count": c.transaction_count, "avg": c.avg_amount, "percentage": c.percentage}
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
                "credits": self.total_credits,
                "debits":  self.total_debits,
                "opening": self.opening_balance,
                "closing": self.closing_balance,
            },
        }


class AxisAggregationEngine:
    """Aggregation engine for Axis Bank transactions."""

    TOP_MERCHANTS_LIMIT = 10

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def aggregate(
        self,
        transactions: List[Dict[str, Any]],
        opening_balance: float = 0,
        closing_balance: float = 0,
    ) -> AxisAggregationResult:
        self.logger.info("Aggregating %d transactions", len(transactions))

        total_credits = sum(t.get("credit") or 0 for t in transactions)
        total_debits  = sum(t.get("debit")  or 0 for t in transactions)

        debit_categories  = self._aggregate_categories(transactions, is_debit=True)
        credit_categories = self._aggregate_categories(transactions, is_debit=False)
        monthly_summaries = self._aggregate_monthly(transactions)
        weekly_credits, weekly_debits = self._aggregate_weekly(transactions)
        recurring_stats = self._aggregate_recurring(transactions)
        top_debit  = self._get_top_merchants(transactions, is_debit=True)
        top_credit = self._get_top_merchants(transactions, is_debit=False)

        return AxisAggregationResult(
            debit_categories=debit_categories,
            credit_categories=credit_categories,
            monthly_summaries=monthly_summaries,
            weekly_credits=weekly_credits,
            weekly_debits=weekly_debits,
            recurring_total=recurring_stats["recurring_total"],
            one_time_total=recurring_stats["one_time_total"],
            recurring_count=recurring_stats["recurring_count"],
            one_time_count=recurring_stats["one_time_count"],
            top_debit_merchants=top_debit,
            top_credit_merchants=top_credit,
            total_credits=total_credits,
            total_debits=total_debits,
            opening_balance=opening_balance,
            closing_balance=closing_balance,
        )

    def _aggregate_categories(self, transactions, is_debit):
        category_data = defaultdict(lambda: {"total": 0, "count": 0})
        for txn in transactions:
            if is_debit and txn.get("debit"):
                cat    = txn.get("category", "Others Debit")
                amount = txn["debit"]
            elif not is_debit and txn.get("credit"):
                cat    = txn.get("category", "Others Credit")
                amount = txn["credit"]
            else:
                continue
            category_data[cat]["total"] += amount
            category_data[cat]["count"] += 1

        grand_total = sum(d["total"] for d in category_data.values())
        summaries = []
        for cat, data in category_data.items():
            avg = data["total"] / data["count"] if data["count"] > 0 else 0
            pct = (data["total"] / grand_total * 100) if grand_total > 0 else 0
            summaries.append(CategorySummary(
                category=cat,
                total_amount=round(data["total"], 2),
                transaction_count=data["count"],
                avg_amount=round(avg, 2),
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
            if not date_str:
                continue
            try:
                if "-" in date_str:
                    parts = date_str.split("-")
                    if len(parts[0]) == 4:
                        month_key = date_str[:7]
                    else:
                        month_key = f"20{parts[2]}-{parts[1]}" if len(parts[2]) == 2 else f"{parts[2]}-{parts[1]}"
                else:
                    continue
            except (IndexError, ValueError):
                continue

            credit = txn.get("credit") or 0
            debit  = txn.get("debit")  or 0
            monthly_data[month_key]["credits"] += credit
            monthly_data[month_key]["debits"]  += debit
            monthly_data[month_key]["count"]   += 1
            if credit > 0:
                monthly_data[month_key]["credit_count"] += 1
            if debit > 0:
                monthly_data[month_key]["debit_count"]  += 1

        summaries = []
        for month, data in sorted(monthly_data.items()):
            summaries.append(MonthlySummary(
                month=month,
                total_credits=round(data["credits"], 2),
                total_debits=round(data["debits"], 2),
                net_flow=round(data["credits"] - data["debits"], 2),
                transaction_count=data["count"],
                credit_count=data["credit_count"],
                debit_count=data["debit_count"],
            ))
        return summaries

    def _aggregate_weekly(self, transactions):
        weekly_credits = defaultdict(float)
        weekly_debits  = defaultdict(float)
        for txn in transactions:
            date_str = txn.get("date", "")
            if not date_str:
                continue
            try:
                if len(date_str) == 10 and date_str[4] == "-":
                    dt = datetime.strptime(date_str, "%Y-%m-%d")
                else:
                    continue
                year, week, _ = dt.isocalendar()
                week_key = f"{year}-W{week:02d}"
            except ValueError:
                continue
            weekly_credits[week_key] += txn.get("credit") or 0
            weekly_debits[week_key]  += txn.get("debit")  or 0
        return dict(weekly_credits), dict(weekly_debits)

    def _aggregate_recurring(self, transactions):
        recurring_total = one_time_total = 0.0
        recurring_count = one_time_count = 0
        for txn in transactions:
            amount = (txn.get("debit") or 0) + (txn.get("credit") or 0)
            if txn.get("is_recurring"):
                recurring_total += amount
                recurring_count += 1
            else:
                one_time_total += amount
                one_time_count += 1
        return {
            "recurring_total": round(recurring_total, 2),
            "one_time_total":  round(one_time_total,  2),
            "recurring_count": recurring_count,
            "one_time_count":  one_time_count,
        }

    def _get_top_merchants(self, transactions, is_debit):
        merchant_data = defaultdict(lambda: {"total": 0, "count": 0})
        for txn in transactions:
            if is_debit and not txn.get("debit"):
                continue
            if not is_debit and not txn.get("credit"):
                continue
            merchant = (txn.get("description") or "Unknown")[:35].strip()
            amount = txn.get("debit") or txn.get("credit") or 0
            merchant_data[merchant]["total"] += amount
            merchant_data[merchant]["count"] += 1

        sorted_merchants = sorted(
            merchant_data.items(), key=lambda x: x[1]["total"], reverse=True
        )[:self.TOP_MERCHANTS_LIMIT]

        return [
            {"merchant": m[0], "total": round(m[1]["total"], 2), "count": m[1]["count"]}
            for m in sorted_merchants
        ]
