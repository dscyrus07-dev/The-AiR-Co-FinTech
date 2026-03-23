"""
Test the new balance-anchored parser directly.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.banks.hdfc.parser import HDFCParser

def test_balance_parser(pdf_path: str):
    """Test the balance-anchored parser."""
    
    print("=" * 80)
    print("TESTING BALANCE-ANCHORED PARSER")
    print("=" * 80)
    print(f"PDF: {pdf_path}\n")
    
    parser = HDFCParser()
    result = parser.parse(pdf_path)
    
    print(f"Parse method: {result.parse_method}")
    print(f"Total transactions: {result.total_count}")
    print(f"Opening balance: {result.opening_balance}")
    print(f"Closing balance: {result.closing_balance}")
    print(f"Total credits: {result.total_credits}")
    print(f"Total debits: {result.total_debits}")
    
    # Show first 10 transactions
    print("\n" + "=" * 80)
    print("FIRST 10 TRANSACTIONS")
    print("=" * 80)
    
    for i, txn in enumerate(result.transactions[:10]):
        print(f"{i+1}. {txn.date} | {txn.debit or 0:>12} | {txn.credit or 0:>12} | {txn.balance or 0:>12} | {txn.description[:40]}")
    
    # Count by month
    print("\n" + "=" * 80)
    print("TRANSACTIONS BY MONTH")
    print("=" * 80)
    
    from collections import defaultdict
    month_counts = defaultdict(int)
    
    for txn in result.transactions:
        month = txn.date[3:5]  # Extract MM from DD/MM/YY
        month_counts[month] += 1
    
    for month in sorted(month_counts.keys()):
        month_name = f"20{txn.date[6:8]}-{month}"
        print(f"{month_name}: {month_counts[month]} transactions")
    
    # Check June specifically
    june_count = month_counts.get('06', 0)
    print(f"\nJUNE 2025: {june_count} transactions")
    
    if june_count == 65:
        print("✓ SUCCESS: June has exactly 65 transactions!")
    else:
        print(f"✗ ISSUE: Expected 65 transactions in June, got {june_count}")
    
    return result

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_balance_parser.py <path_to_hdfc_pdf>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    if not os.path.exists(pdf_path):
        print(f"Error: File not found: {pdf_path}")
        sys.exit(1)
    
    test_balance_parser(pdf_path)
