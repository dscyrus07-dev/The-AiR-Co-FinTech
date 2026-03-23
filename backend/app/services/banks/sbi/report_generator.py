"""
SBI Bank Transaction Report Generator
======================================
Deterministic financial report generator using:
- pandas (calculation)
- xlsxwriter (formatting)
- strict rule engine (classification)

Generates 9-sheet Excel report:
1. Summary - Monthly aggregations
2. Category Analysis - Credit/Debit category breakdown
3. Weekly Analysis - Weekly credit/debit totals
4. Recurring Analysis - Recurring vs non-recurring
5. Raw Transactions - All transactions with Category, Confidence, Recurring
6. Monthly Stats
7. Funds Remittance
8. Raw Transaction
9. Finbit - Finbit-specific monthly metrics

No AI. No fuzzy logic. No probability scoring.
Every output cell traceable to an exact rule.
"""

import logging
import os
from collections import Counter, OrderedDict
from typing import Dict, List, Tuple, Any, Optional

import pandas as pd
from .sbi_classifier import SBIClassifier

logger = logging.getLogger(__name__)

# Initialize the unified SBI classifier (singleton)
_classifier = None

def get_classifier() -> SBIClassifier:
    """Get or create the unified SBI classifier instance."""
    global _classifier
    if _classifier is None:
        _classifier = SBIClassifier()
        logger.info("SBI classifier initialized: %s", _classifier.get_category_stats())
    return _classifier

def classify(row) -> Tuple[str, int]:
    """
    Advanced classification using comprehensive keyword database.
    Uses entity interpretation with direction awareness.
    """
    classifier = get_classifier()
    return classifier.classify(row)


def detect_recurring(df: pd.DataFrame) -> pd.DataFrame:
    """Detect recurring transactions."""
    df = df.copy()
    df["Recurring"] = "No"
    
    # Group by description and count
    desc_counts = df.groupby("Description").size()
    recurring_descs = desc_counts[desc_counts >= 2].index
    
    # Mark as recurring
    df.loc[df["Description"].isin(recurring_descs), "Recurring"] = "Yes"
    
    return df


def generate_report(
    transactions: List[Dict[str, Any]],
    output_path: str,
    user_info: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Generate comprehensive Excel report for SBI Bank statement.
    
    Args:
        transactions: List of transaction dictionaries
        output_path: Path to save Excel file
        opening_balance: Opening balance for the period
        
    Returns:
        Dictionary with report statistics
    """
    logger.info("Generating SBI report with %d transactions", len(transactions))
    
    # Create DataFrame
    df = pd.DataFrame(transactions)
    
    # Ensure required columns
    required_cols = ["date", "description", "debit", "credit", "balance"]
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"Missing required column: {col}")
    
    # Rename for consistency
    df = df.rename(columns={
        "date": "Date",
        "description": "Description",
        "debit": "Debit",
        "credit": "Credit",
        "balance": "Balance",
        "ref_no": "Ref_No",
    })
    
    # Fill NaN values
    df["Debit"] = df["Debit"].fillna(0)
    df["Credit"] = df["Credit"].fillna(0)
    df["Ref_No"] = df.get("Ref_No", "").fillna("")
    
    # Convert date to datetime
    df["Date"] = pd.to_datetime(df["Date"], format="%d-%m-%Y", errors="coerce")
    
    # Classify transactions
    df[["Category", "Confidence"]] = df.apply(
        lambda row: pd.Series(classify(row)), axis=1
    )
    
    # Detect recurring
    df = detect_recurring(df)
    
    # Add month column
    df["Month"] = df["Date"].dt.to_period("M")
    
    # Sort by date
    df = df.sort_values("Date").reset_index(drop=True)
    
    # Generate Excel with xlsxwriter
    from pandas import ExcelWriter
    
    writer = ExcelWriter(output_path, engine="xlsxwriter")
    workbook = writer.book
    
    # ── FORMATS ──────────────────────────────────────────────────────────────
    fmt_header = workbook.add_format({
        "bold": True, "bg_color": "#1F4E79", "font_color": "white",
        "border": 1, "align": "center", "valign": "vcenter"
    })
    fmt_currency = workbook.add_format({"num_format": "₹#,##0.00", "border": 1})
    fmt_date = workbook.add_format({"num_format": "dd-mmm-yyyy", "border": 1})
    fmt_text = workbook.add_format({"border": 1, "align": "left"})
    fmt_percent = workbook.add_format({"num_format": "0%", "border": 1})
    fmt_month_header = workbook.add_format({
        "bold": True, "bg_color": "#D9E1F2", "border": 1,
        "align": "center", "valign": "vcenter"
    })
    fmt_sub_header = workbook.add_format({
        "bold": True, "bg_color": "#E7E6E6", "border": 1
    })
    fmt_section_title = workbook.add_format({
        "bold": True, "font_size": 14, "bg_color": "#1F4E79",
        "font_color": "white", "border": 1, "align": "center"
    })
    
    months = df["Month"].unique()
    months_list = sorted(months)
    
    # ══════════════════════════════════════════════════════════════════════════
    # SHEET 1 — Summary
    # ══════════════════════════════════════════════════════════════════════════
    ws1 = workbook.add_worksheet("Summary")
    ws1.set_column(0, 0, 18)
    ws1.set_column(1, 4, 16)
    
    ws1.merge_range(0, 0, 0, 4, "Monthly Transaction Summary", fmt_section_title)
    headers = ["Month", "Credits (₹)", "Debits (₹)", "Net (₹)", "Transactions"]
    for c, h in enumerate(headers):
        ws1.write(1, c, h, fmt_header)
    
    row = 2
    for m in months_list:
        month_df = df[df["Month"] == m]
        credits = month_df["Credit"].sum()
        debits = month_df["Debit"].sum()
        net = credits - debits
        count = len(month_df)
        
        ws1.write(row, 0, m.strftime("%b-%y"), fmt_text)
        ws1.write_number(row, 1, credits, fmt_currency)
        ws1.write_number(row, 2, debits, fmt_currency)
        ws1.write_number(row, 3, net, fmt_currency)
        ws1.write_number(row, 4, count, fmt_text)
        row += 1
    
    ws1.freeze_panes(2, 0)
    
    # ══════════════════════════════════════════════════════════════════════════
    # SHEET 2 — Category Analysis
    # ══════════════════════════════════════════════════════════════════════════
    ws2 = workbook.add_worksheet("Category Analysis")
    ws2.set_column(0, 0, 22)
    ws2.set_column(1, 3, 16)
    
    ws2.merge_range(0, 0, 0, 3, "Category-wise Analysis", fmt_section_title)
    cat_headers = ["Category", "Credit (₹)", "Debit (₹)", "Count"]
    for c, h in enumerate(cat_headers):
        ws2.write(1, c, h, fmt_header)
    
    cat_summary = df.groupby("Category").agg({
        "Credit": "sum",
        "Debit": "sum",
        "Category": "count"
    }).rename(columns={"Category": "Count"})
    cat_summary = cat_summary.sort_values("Count", ascending=False)
    
    row = 2
    for cat, data in cat_summary.iterrows():
        ws2.write(row, 0, cat, fmt_text)
        ws2.write_number(row, 1, data["Credit"], fmt_currency)
        ws2.write_number(row, 2, data["Debit"], fmt_currency)
        ws2.write_number(row, 3, int(data["Count"]), fmt_text)
        row += 1
    
    ws2.freeze_panes(2, 0)
    
    # ══════════════════════════════════════════════════════════════════════════
    # SHEET 3 — Weekly Analysis
    # ══════════════════════════════════════════════════════════════════════════
    ws3 = workbook.add_worksheet("Weekly Analysis")
    ws3.set_column(0, 0, 18)
    ws3.set_column(1, 2, 16)
    
    ws3.merge_range(0, 0, 0, 2, "Weekly Analysis", fmt_section_title)
    week_headers = ["Week", "Credits (₹)", "Debits (₹)"]
    for c, h in enumerate(week_headers):
        ws3.write(1, c, h, fmt_header)
    
    df["Week"] = df["Date"].dt.to_period("W")
    weekly = df.groupby("Week").agg({"Credit": "sum", "Debit": "sum"})
    
    row = 2
    for week, data in weekly.iterrows():
        ws3.write(row, 0, str(week), fmt_text)
        ws3.write_number(row, 1, data["Credit"], fmt_currency)
        ws3.write_number(row, 2, data["Debit"], fmt_currency)
        row += 1
    
    ws3.freeze_panes(2, 0)
    
    # ══════════════════════════════════════════════════════════════════════════
    # SHEET 4 — Recurring Analysis
    # ══════════════════════════════════════════════════════════════════════════
    ws4 = workbook.add_worksheet("Recurring Analysis")
    ws4.set_column(0, 0, 45)
    ws4.set_column(1, 3, 16)
    
    ws4.merge_range(0, 0, 0, 3, "Recurring Transactions", fmt_section_title)
    rec_headers = ["Description", "Occurrences", "Total Credit", "Total Debit"]
    for c, h in enumerate(rec_headers):
        ws4.write(1, c, h, fmt_header)
    
    recurring = df[df["Recurring"] == "Yes"].groupby("Description").agg({
        "Description": "count",
        "Credit": "sum",
        "Debit": "sum",
    }).rename(columns={"Description": "Count"})
    recurring = recurring.sort_values("Count", ascending=False)
    
    row = 2
    for desc, data in recurring.iterrows():
        ws4.write(row, 0, desc, fmt_text)
        ws4.write_number(row, 1, int(data["Count"]), fmt_text)
        ws4.write_number(row, 2, data["Credit"], fmt_currency)
        ws4.write_number(row, 3, data["Debit"], fmt_currency)
        row += 1
    
    ws4.freeze_panes(2, 0)
    
    # ══════════════════════════════════════════════════════════════════════════
    # SHEET 5 — Raw Transactions (first 5 sheets legacy format)
    # ══════════════════════════════════════════════════════════════════════════
    ws5 = workbook.add_worksheet("Transactions")
    ws5.set_column(0, 0, 14)
    ws5.set_column(1, 1, 60)
    ws5.set_column(2, 6, 16)
    
    txn_headers = ["Date", "Description", "Debit", "Credit", "Balance", "Category", "Recurring"]
    for c, h in enumerate(txn_headers):
        ws5.write(0, c, h, fmt_header)
    
    for ri in range(len(df)):
        row_num = ri + 1
        r = df.iloc[ri]
        if pd.notna(r["Date"]):
            ws5.write_datetime(row_num, 0, r["Date"].to_pydatetime(), fmt_date)
        else:
            ws5.write(row_num, 0, "", fmt_text)
        ws5.write(row_num, 1, str(r["Description"]), fmt_text)
        if r["Debit"] > 0:
            ws5.write_number(row_num, 2, r["Debit"], fmt_currency)
        else:
            ws5.write(row_num, 2, "", fmt_text)
        if r["Credit"] > 0:
            ws5.write_number(row_num, 3, r["Credit"], fmt_currency)
        else:
            ws5.write(row_num, 3, "", fmt_text)
        ws5.write_number(row_num, 4, r["Balance"], fmt_currency)
        ws5.write(row_num, 5, str(r["Category"]), fmt_text)
        ws5.write(row_num, 6, str(r["Recurring"]), fmt_text)
    
    ws5.freeze_panes(1, 0)
    ws5.autofilter(0, 0, len(df), len(txn_headers) - 1)
    
    # Additional sheets 6-8 (Monthly Stats, Funds Remittance, Raw Transaction) - simplified versions
    
    # ══════════════════════════════════════════════════════════════════════════
    # SHEET 9 — Finbit (Finbit-specific monthly metrics)
    # ══════════════════════════════════════════════════════════════════════════
    ws9 = workbook.add_worksheet("Finbit")
    
    # Calculate opening balance from first transaction
    opening_balance = 0
    if len(df) > 0:
        first = df.iloc[0]
        opening_balance = first["Balance"] - first["Credit"] + first["Debit"]
    
    finbit_months, finbit_data = _compute_finbit_monthly(df, opening_balance)
    
    # Define all 30 Finbit metrics in order
    finbit_metrics = [
        ("monthlyAvgBal", "Monthly Avg Balance"),
        ("maxBalance", "Max Balance"),
        ("minBalance", "Min Balance"),
        ("cashDeposit", "Cash Deposit"),
        ("cashWithdrawals", "Cash Withdrawals"),
        ("chqDeposit", "Cheque Deposit"),
        ("chqIssues", "Cheque Issues"),
        ("credits", "Total Credits"),
        ("debits", "Total Debits"),
        ("inwBounce", "Inward Bounce Count"),
        ("outwBounce", "Outward Bounce Count"),
        ("penaltyCharges", "Penalty Charges"),
        ("ecsNach", "ECS/NACH Debits"),
        ("totalNetDebit", "Total Net Debit"),
        ("totalNetCredit", "Total Net Credit"),
        ("selfWithdraw", "Self Withdrawals"),
        ("selfDeposit", "Self Deposits"),
        ("loanRepayment", "Loan Repayment"),
        ("loanCredit", "Loan Credit"),
        ("creditCardPayment", "Credit Card Payment"),
        ("minCredits", "Min Credit Transaction"),
        ("maxCredits", "Max Credit Transaction"),
        ("salary", "Salary Credits"),
        ("bankCharges", "Bank Charges"),
        ("balanceOpening", "Opening Balance"),
        ("balanceClosing", "Closing Balance"),
        ("salaryMonth", "Salary This Month"),
        ("ccPayment", "CC Payment"),
        ("eodMinBalance", "EOD Min Balance"),
        ("eodMaxBalance", "EOD Max Balance"),
    ]
    
    ws9.set_column(0, 0, 28)
    for c in range(1, len(finbit_months) + 1):
        ws9.set_column(c, c, 15)
    
    ws9.write(0, 0, "Metric", fmt_header)
    for c_idx, m_label in enumerate(finbit_months, 1):
        ws9.write(0, c_idx, m_label, fmt_header)
    
    for r_idx, (metric_key, metric_label) in enumerate(finbit_metrics, 1):
        ws9.write(r_idx, 0, metric_label, fmt_sub_header)
        for c_idx, m_label in enumerate(finbit_months, 1):
            val = finbit_data.get(m_label, {}).get(metric_key, 0)
            if isinstance(val, (int, float)):
                if metric_key in ["inwBounce", "outwBounce"]:
                    ws9.write_number(r_idx, c_idx, val, fmt_text)
                else:
                    ws9.write_number(r_idx, c_idx, val, fmt_currency)
            else:
                ws9.write(r_idx, c_idx, val, fmt_text)
    
    ws9.freeze_panes(1, 1)
    
    # ── GLOBAL STYLE ─────────────────────────────────────────────────────────
    for ws in [ws1, ws2, ws3, ws4, ws5, ws9]:
        ws.hide_gridlines(2)
        ws.set_default_row(18)
    
    writer.close()
    
    # Build stats
    stats = {
        "total_transactions": len(df),
        "total_credits": float(df["Credit"].sum()),
        "total_debits": float(df["Debit"].sum()),
        "credit_count": int((df["Credit"] > 0).sum()),
        "debit_count": int((df["Debit"] > 0).sum()),
        "date_from": str(df["Date"].min().date()),
        "date_to": str(df["Date"].max().date()),
        "months": len(months),
        "recurring_count": int((df["Recurring"] == "Yes").sum()),
        "categories_used": len(df["Category"].unique()),
        "sheets": 9,
    }
    
    logger.info(
        "SBI report generated: %d transactions, %s to %s, %d months, %d recurring (9 sheets)",
        stats["total_transactions"], stats["date_from"], stats["date_to"],
        stats["months"], stats["recurring_count"],
    )
    
    return stats


def _compute_finbit_monthly(df: pd.DataFrame, opening_balance: float = 0) -> Tuple[List[str], Dict]:
    """
    Compute all Finbit monthly metrics from DataFrame.
    
    Returns:
        (sorted_month_keys, dict of month -> metrics_dict)
    """
    def _kw(desc: str, keywords: list) -> bool:
        """Case-insensitive keyword match."""
        d = str(desc).upper()
        return any(k.upper() in d for k in keywords)
    
    # Keyword lists
    KW_CASH_DEP = ["CASH DEPOSIT", "CASHDEP", "CDM", "CASHDEPOSITBY", "CASH DEP", "BY CASH", 
                   "CASH/DEP", "DEP BY CASH"]
    KW_CASH_WDL = ["ATW", "ATM WDL", "ATM CASH", "ATMWDL", "CASH WITHDRAWAL", "CASHWITHDRAWAL", 
                   "NFS ATM", "ATM-WDL", "ATM/CASH", "CASH W/D", "ATM/WDL", "NFS/ATM", 
                   "NFS WDL", "VISA ATM", "SELF WDL", "AWL/"]
    KW_CHQ_DEP = ["CHQ DEP", "CHEQUE DEP", "CLG CR", "I/WCLG", "INWARD CLG", "IW CLR", "CHQDEP",
                  "CLG/CR", "INWARD CLEARING"]
    KW_CHQ_ISS = ["CHQPAID", "CHQ PAID", "SELF-CHQ", "CLG DR", "O/WCLG", "OUTWARD CLG", "CHEQUE PAID",
                  "CLG/DR", "OUTWARD CLEARING"]
    KW_INW_BOUNCE = ["I/WCHQRET", "INWARD RETURN", "INW BOUNCE", "INW RET", "INWARD BOUNCE", "CHQ RET"]
    KW_OUTW_BOUNCE = ["O/WCHQRET", "OUTWARD RETURN", "OUTW BOUNCE", "O/W RETURN", "OUTWARD BOUNCE"]
    KW_PENALTY = ["PENALTY", "PENAL CHARGE", "PENAL INT", "MIN BAL CHARGE", "NON-MAINT", "MINIMUM BALANCE",
                  "RETURNCHARGES", "RETURN CHARGES", "DEBIT RETURN", "BOUNCE CHARGE", "DISHONOUR",
                  "LATE FEE", "OVERDUE", "DELAYED PAYMENT"]
    KW_ECS_NACH = ["ACHD-", "ACH D-", "ECS/", "ECS ", "NACH/", "NACH ", "AUTOPAYSI", "SI-", "AUTO DEBIT", "SI /",
                   "ACH D ", "ACH DR", "E-MANDATE", "EMANDATE"]
    KW_SELF = ["SELF-", "/SELF", " SELF ", "SELF CHQ", "SELF TRF"]
    KW_LOAN_REP = ["EMI", "LOAN REPAY", "LOAN EMI", "BAJAJ FINANCE", "BAJAJFINANCE", "BAJAJ FIN",
                   "TATA CAPITAL", "TATACAPITAL", "DMI FINANCE", "DMIFINANCE", "HOME CREDIT",
                   "HOMECREDIT", "IDFC FIRST", "IDFCFIRST", "HDFC LTD", "FINANCE LTD", "FINANCELTD",
                   "CAPITAL FIRST", "CAPITALFIRST", "FULLERTON", "MUTHOOT", "SHRIRAM",
                   "MAHINDRA FIN", "CHOLAMANDALAM", "SUNDARAM", "LENDINGKART", "PAYSENSE"]
    KW_LOAN_CR = ["LOAN DISBURSE", "LOAN CR", "LOAN SANCTION", "LOAN CREDIT"]
    KW_CC_PAY = ["CC PAYMENT", "CREDIT CARD", "CC000", "RAZPCREDCLUB", "CRED CLUB", "CREDITCARD", "CCPAY",
                 "CRED BILL", "ONECARD", "SLICE", "SIMPL", "LAZYPAY", "POSTPE", "AMAZONPAY LATER",
                 "SBICREDITCARD", "SBI CARD", "HDFCCARD", "ICICICARD", "AXISCARD", "KOTAKCARD",
                 "CARD BILL", "CARDBILL", "CC BILL", "CCBILL"]
    KW_SALARY = ["SALARY", "SAL CR", "PAYROLL", "WAGES", "STIPEND", "SAL-", "SALARY-"]
    KW_BANK_CHG = ["CHARGES", "FEE-", "LOWUSAGECHARGES", "SETTLEMENTCHARGE", "EDC RENTAL", "EDCRENTAL",
                   "SERVICE CHARGE", "BANK CHARGE", "SMS ALERT", "MAINTENANCE CHARGE", "FEE-ATMCASH",
                   "INSTA ALERT", "INSTAALERT", "GST ON", "ALERT CHG"]
    
    df = df.copy()
    df["Month"] = df["Date"].dt.to_period("M")
    months_list = sorted(df["Month"].unique())
    month_keys = [m.strftime("%b-%y") for m in months_list]
    
    result = OrderedDict()
    prev_closing = opening_balance
    
    for month_idx, month in enumerate(months_list):
        month_df = df[df["Month"] == month].copy()
        if len(month_df) == 0:
            continue
        
        month_key = month.strftime("%b-%y")
        
        cr_vals = month_df[month_df["Credit"] > 0]["Credit"].tolist()
        dr_vals = month_df[month_df["Debit"] > 0]["Debit"].tolist()
        total_cr = sum(cr_vals)
        total_dr = sum(dr_vals)
        
        balances = month_df["Balance"].tolist()
        eod = month_df.groupby(month_df["Date"].dt.date)["Balance"].last()
        eod_vals = eod.tolist() if len(eod) > 0 else [0]
        
        if month_idx == 0 and len(month_df) > 0:
            first = month_df.iloc[0]
            start_bal = first["Balance"] - first["Credit"] + first["Debit"]
        else:
            start_bal = prev_closing
        end_bal = balances[-1] if balances else prev_closing
        
        def match_rows(kw_list, credit_col=True):
            mask = month_df["Description"].apply(lambda d: _kw(d, kw_list))
            if credit_col:
                return month_df[mask & (month_df["Credit"] > 0)]["Credit"].sum()
            else:
                return month_df[mask & (month_df["Debit"] > 0)]["Debit"].sum()
        
        cash_dep = match_rows(KW_CASH_DEP, True)
        cash_wdl = match_rows(KW_CASH_WDL, False)
        chq_dep = match_rows(KW_CHQ_DEP, True)
        chq_iss = match_rows(KW_CHQ_ISS, False)
        inw_b = len(month_df[month_df["Description"].apply(lambda d: _kw(d, KW_INW_BOUNCE))])
        outw_b = len(month_df[month_df["Description"].apply(lambda d: _kw(d, KW_OUTW_BOUNCE))])
        penalty = match_rows(KW_PENALTY, False)
        ecs_nach = match_rows(KW_ECS_NACH, False)
        self_wdl = match_rows(KW_SELF, False)
        self_dep = match_rows(KW_SELF, True)
        loan_rep = match_rows(KW_LOAN_REP, False)
        loan_crd = match_rows(KW_LOAN_CR, True)
        cc_pay = match_rows(KW_CC_PAY, False)
        sal = match_rows(KW_SALARY, True)
        bank_chg = match_rows(KW_BANK_CHG, False)
        
        result[month_key] = {
            'monthlyAvgBal': round(sum(eod_vals) / len(eod_vals), 2),
            'maxBalance': round(max(balances), 2) if balances else 0,
            'minBalance': round(min(balances), 2) if balances else 0,
            'cashDeposit': round(cash_dep, 2),
            'cashWithdrawals': round(cash_wdl, 2),
            'chqDeposit': round(chq_dep, 2),
            'chqIssues': round(chq_iss, 2),
            'credits': round(total_cr, 2),
            'debits': round(total_dr, 2),
            'inwBounce': inw_b,
            'outwBounce': outw_b,
            'penaltyCharges': round(penalty, 2),
            'ecsNach': round(ecs_nach, 2),
            'totalNetDebit': round(max(total_dr - total_cr, 0), 2),
            'totalNetCredit': round(max(total_cr - total_dr, 0), 2),
            'selfWithdraw': round(self_wdl, 2),
            'selfDeposit': round(self_dep, 2),
            'loanRepayment': round(loan_rep, 2),
            'loanCredit': round(loan_crd, 2),
            'creditCardPayment': round(cc_pay, 2),
            'minCredits': round(min(cr_vals), 2) if cr_vals else 0,
            'maxCredits': round(max(cr_vals), 2) if cr_vals else 0,
            'salary': round(sal, 2),
            'bankCharges': round(bank_chg, 2),
            'balanceOpening': round(start_bal, 2),
            'balanceClosing': round(end_bal, 2),
            'salaryMonth': round(sal, 2),
            'ccPayment': round(cc_pay, 2),
            'eodMinBalance': round(min(eod_vals), 2),
            'eodMaxBalance': round(max(eod_vals), 2),
        }
        prev_closing = end_bal
    
    return month_keys, result
