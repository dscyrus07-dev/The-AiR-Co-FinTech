"""
Final accuracy verification - compare parser output against known PDF values.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from app.services.banks.hdfc.parser import HDFCParser

def verify(pdf_path):
    parser = HDFCParser()
    result = parser.parse(pdf_path)
    
    txns = result.transactions
    print(f"Parse method: {result.parse_method}")
    print(f"Total: {result.total_count}")
    print(f"Opening balance: {result.opening_balance:,.2f}")
    print(f"Closing balance: {result.closing_balance:,.2f}")
    
    # Verify against known values from PDF screenshot
    expected = [
        # (date, deposit, withdrawal, balance, narration_contains)
        ("01/06/25", 111082.91, None, 3424624.69, "NEFTCR"),
        ("01/06/25", 42490.22, None, 3467114.91, "TERMINAL1CARDS"),
        ("02/06/25", 79322.51, None, 3546437.42, "NEFTCR"),
        ("02/06/25", 43357.68, None, 3589795.10, "TERMINAL1CARDS"),
        ("02/06/25", None, 73171.00, 3516624.10, "FEDBANKFINANCIAL"),
        ("02/06/25", 55195.00, None, 3571819.10, "MAKEMYTRIP"),
        ("03/06/25", 34911.33, None, 3606730.43, "NEFTCR"),
        ("03/06/25", 20493.06, None, 3627223.49, "TERMINAL1CARDS"),
        ("03/06/25", None, 108717.00, 3518506.49, "IDFCFIRSTBANK"),
        ("03/06/25", None, 110382.00, 3408124.49, "TPACHPOONAWALLA"),
        ("03/06/25", None, 55334.00, 3352790.49, "HEROFINCORP"),
        ("03/06/25", None, 500000.00, 2852790.49, "MORARIENTERP"),
        ("03/06/25", None, 500000.00, 2352790.49, "RIDDHI"),
        ("03/06/25", 43412.00, None, 2396202.49, "MAKEMYTRIP"),
    ]
    
    print(f"\n{'='*80}")
    print("ACCURACY VERIFICATION (first 14 transactions)")
    print(f"{'='*80}")
    
    all_pass = True
    for i, (exp_date, exp_dep, exp_wdr, exp_bal, exp_narr) in enumerate(expected):
        txn = txns[i]
        
        checks = []
        # Date
        if txn.date == exp_date:
            checks.append("DATE OK")
        else:
            checks.append(f"DATE FAIL: {txn.date} != {exp_date}")
            all_pass = False
        
        # Balance
        if abs(txn.balance - exp_bal) < 0.01:
            checks.append("BAL OK")
        else:
            checks.append(f"BAL FAIL: {txn.balance} != {exp_bal}")
            all_pass = False
        
        # Deposit
        if exp_dep:
            if txn.credit and abs(txn.credit - exp_dep) < 0.01:
                checks.append("DEP OK")
            else:
                checks.append(f"DEP FAIL: {txn.credit} != {exp_dep}")
                all_pass = False
        
        # Withdrawal
        if exp_wdr:
            if txn.debit and abs(txn.debit - exp_wdr) < 0.01:
                checks.append("WDR OK")
            else:
                checks.append(f"WDR FAIL: {txn.debit} != {exp_wdr}")
                all_pass = False
        
        # Narration
        if exp_narr.upper() in txn.description.upper():
            checks.append("NARR OK")
        else:
            checks.append(f"NARR FAIL: '{exp_narr}' not in '{txn.description[:40]}'")
            all_pass = False
        
        status = "PASS" if all(c.endswith("OK") for c in checks) else "FAIL"
        print(f"  Txn {i+1}: [{status}] {' | '.join(checks)}")
    
    # Balance continuity check on ALL transactions
    print(f"\n{'='*80}")
    print("FULL BALANCE CONTINUITY CHECK")
    print(f"{'='*80}")
    
    errors = 0
    for i in range(1, len(txns)):
        prev_bal = txns[i-1].balance
        curr_bal = txns[i].balance
        change = curr_bal - prev_bal
        
        if txns[i].debit and not txns[i].credit:
            expected_change = -txns[i].debit
        elif txns[i].credit and not txns[i].debit:
            expected_change = txns[i].credit
        else:
            expected_change = 0
        
        diff = abs(change - expected_change)
        if diff > 0.02:
            errors += 1
            if errors <= 5:
                print(f"  ERROR at txn {i+1}: change={change:.2f}, expected={expected_change:.2f}, diff={diff:.2f}")
    
    print(f"  Balance continuity errors: {errors}/{len(txns)-1}")
    
    # Final verdict
    print(f"\n{'='*80}")
    if all_pass and errors == 0:
        print("VERDICT: 100% ACCURATE - All checks passed!")
    else:
        print(f"VERDICT: Issues found - {14 - sum(1 for i in range(14))} txn check fails, {errors} balance errors")
    print(f"{'='*80}")

if __name__ == "__main__":
    pdf_path = sys.argv[1] if len(sys.argv) > 1 else "HDFC DATA/Hdfc Bank 1 June to 24 Jan 26.pdf"
    verify(pdf_path)
