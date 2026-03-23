"""
Count exactly what's in June to understand the discrepancy.
"""

import sys
import os
import pdfplumber

def count_june_transactions(pdf_path: str):
    """Count June transactions in detail."""
    
    print("=" * 80)
    print("JUNE TRANSACTION COUNT ANALYSIS")
    print("=" * 80)
    
    june_transactions = []
    
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages[:3]):  # Check first 3 pages for June
            tables = page.extract_tables()
            
            for table in tables:
                if not table:
                    continue
                
                for row in table:
                    if not row or len(row) < 7:
                        continue
                    
                    # Split each column by newlines
                    dates = [d.strip() for d in str(row[0] or "").split('\n') if d.strip()]
                    balances = [b.strip() for b in str(row[6] or "").split('\n') if b.strip()]
                    
                    # Skip header rows
                    if not balances or any(b.upper() in ['CLOSINGBALANCE', 'CLOSING BALANCE'] for b in balances):
                        continue
                    
                    # Process each balance
                    for i, balance_str in enumerate(balances):
                        if i < len(dates):
                            date_str = dates[i]
                            
                            # Check if it's June
                            if date_str.startswith('01/06/') or date_str.startswith('02/06/') or \
                               date_str.startswith('03/06/') or date_str.startswith('04/06/') or \
                               date_str.startswith('05/06/') or date_str.startswith('06/06/') or \
                               date_str.startswith('07/06/') or date_str.startswith('08/06/') or \
                               date_str.startswith('09/06/') or date_str.startswith('10/06/') or \
                               date_str.startswith('11/06/') or date_str.startswith('12/06/') or \
                               date_str.startswith('13/06/') or date_str.startswith('14/06/') or \
                               date_str.startswith('15/06/') or date_str.startswith('16/06/') or \
                               date_str.startswith('17/06/') or date_str.startswith('18/06/') or \
                               date_str.startswith('19/06/') or date_str.startswith('20/06/') or \
                               date_str.startswith('21/06/') or date_str.startswith('22/06/') or \
                               date_str.startswith('23/06/') or date_str.startswith('24/06/') or \
                               date_str.startswith('25/06/') or date_str.startswith('26/06/') or \
                               date_str.startswith('27/06/') or date_str.startswith('28/06/') or \
                               date_str.startswith('29/06/') or date_str.startswith('30/06/'):
                                
                                june_transactions.append({
                                    'date': date_str,
                                    'balance': balance_str,
                                    'page': page_num + 1
                                })
    
    print(f"Total June transactions found: {len(june_transactions)}")
    
    # Group by date
    from collections import defaultdict
    dates_count = defaultdict(int)
    
    for txn in june_transactions:
        dates_count[txn['date']] += 1
    
    print(f"\nUnique dates in June: {len(dates_count)}")
    
    # Show all dates with counts
    print("\nTransactions by date:")
    for date in sorted(dates_count.keys()):
        print(f"  {date}: {dates_count[date]} transactions")
    
    # Show all transactions
    print("\nAll June transactions:")
    for i, txn in enumerate(june_transactions):
        print(f"{i+1:3d}. {txn['date']} | {txn['balance']} | Page {txn['page']}")
    
    # Check for multiple transactions on same date
    multiple_same_date = {date: count for date, count in dates_count.items() if count > 1}
    
    if multiple_same_date:
        print(f"\nDates with multiple transactions:")
        for date, count in multiple_same_date.items():
            print(f"  {date}: {count} transactions")
    
    return len(june_transactions)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python count_june_transactions.py <path_to_hdfc_pdf>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    if not os.path.exists(pdf_path):
        print(f"Error: File not found: {pdf_path}")
        sys.exit(1)
    
    count = count_june_transactions(pdf_path)
    
    print(f"\n{'='*80}")
    print(f"FINAL COUNT: {count} June transactions")
    print(f"Expected: 65")
    if count == 65:
        print("✓ MATCH!")
    else:
        print(f"✗ DISCREPANCY: {count - 65} extra transactions")
