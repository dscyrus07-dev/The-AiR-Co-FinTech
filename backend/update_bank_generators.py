import os

HDFC_FILE = r"X:\FinTech SAAS\FinTech SAAS\backend\app\services\banks\hdfc\report_generator.py"

with open(HDFC_FILE, "r", encoding="utf-8") as f:
    hdfc_code = f.read()

def migrate_bank(bank_name_proper, bank_name_upper, bank_name_lower, filepath, summary_title):
    global hdfc_code
    code = hdfc_code.replace("HDFC Bank", f"{bank_name_proper} Bank")
    code = code.replace("HDFC", bank_name_upper)
    code = code.replace("hdfc", bank_name_lower)
    
    # Also replace KOTAK BANK for sheet title
    code = code.replace(f"{bank_name_upper} BANK — STATEMENT SUMMARY", summary_title)
    
    old_col_map = """    col_map = {
        "date": "Date",
        "description": "Description",
        "narration": "Description",
        "ref_no": "RefNo",
        "value_date": "ValueDate",
        "debit": "Debit",
        "credit": "Credit",
        "withdrawal": "Debit",
        "deposit": "Credit",
        "balance": "Balance",
        "closing_balance": "Balance",
    }"""

    new_col_map = """    col_map = {
        "date": "Date",
        "description": "Description",
        "narration": "Description",
        "ref_no": "RefNo",
        "value_date": "ValueDate",
        "debit": "Debit",
        "credit": "Credit",
        "withdrawal": "Debit",
        "deposit": "Credit",
        "balance": "Balance",
        "closing_balance": "Balance",
        "withdrawals": "Debit",
        "deposits": "Credit",
        "chq_no": "RefNo",
        "mode": "RefNo",
    }"""
    
    code = code.replace(old_col_map, new_col_map)
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(code)
    print(f"Migrated {bank_name_proper} to {filepath}")


base_dir = r"X:\FinTech SAAS\FinTech SAAS\backend\app\services\banks"
migrate_bank("Kotak", "Kotak", "kotak", os.path.join(base_dir, "kotak", "report_generator.py"), "KOTAK MAHINDRA BANK — STATEMENT SUMMARY")
migrate_bank("ICICI", "ICICI", "icici", os.path.join(base_dir, "icici", "report_generator.py"), "ICICI BANK — STATEMENT SUMMARY")
migrate_bank("Axis", "Axis", "axis", os.path.join(base_dir, "axis", "report_generator.py"), "AXIS BANK — STATEMENT SUMMARY")

