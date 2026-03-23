"""
Analyze the balance sequence to understand the actual transaction count.
"""

import sys
import os
import pdfplumber

def analyze_balance_sequence(pdf_path: str):
    """Analyze balance sequence to understand the issue."""
    
    print("=" * 80)
    print("BALANCE SEQUENCE ANALYSIS")
    print("=" * 80)
    
    all_balances = []
    
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            tables = page.extract_tables()
            
            for table in tables:
                if not table:
                    continue
                
                for row in table:
                    if not row or len(row) < 7:
                        continue
                    
                    # Get balance column
                    balance_str = str(row[6] or "")
                    balances = [b.strip() for b in balance_str.split('\n') if b.strip()]
                    
                    # Skip header
                    if not balances or any(b.upper() in ['CLOSINGBALANCE', 'CLOSING BALANCE'] for b in balances):
                        continue
                    
                    all_balances.extend(balances)
    
    print(f"Total balance values found: {len(all_balances)}")
    
    # Show first 20 balances
    print("\nFirst 20 balance values:")
    for i, bal in enumerate(all_balances[:20]):
        print(f"{i+1:2d}. {bal}")
    
    # Check for duplicates
    unique_balances = list(set(all_balances))
    print(f"\nUnique balance values: {len(unique_balances)}")
    print(f"Duplicate balance values: {len(all_balances) - len(unique_balances)}")
    
    # Find duplicates
    from collections import Counter
    balance_counts = Counter(all_balances)
    duplicates = {bal: count for bal, count in balance_counts.items() if count > 1}
    
    if duplicates:
        print("\nDuplicate balances:")
        for bal, count in sorted(duplicates.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"  {bal}: {count} times")
    
    # Analyze June specifically
    print("\n" + "=" * 80)
    print("JUNE BALANCE ANALYSIS")
    print("=" * 80)
    
    # Extract June balances (first page)
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[0]  # First page should be June
        tables = page.extract_tables()
        
        if tables:
            row = tables[0][1]  # Skip header row
            balance_str = str(row[6] or "")
            june_balances = [b.strip() for b in balance_str.split('\n') if b.strip()]
            
            print(f"June balances on page 1: {len(june_balances)}")
            for i, bal in enumerate(june_balances):
                print(f"{i+1:2d}. {bal}")
            
            # Check if balances are unique
            unique_june = list(set(june_balances))
            print(f"\nUnique June balances: {len(unique_june)}")
            print(f"Expected: 65 transactions")
            
            if len(unique_june) == 65:
                print("✓ June has 65 unique balances!")
            else:
                print(f"✗ June has {len(unique_june)} unique balances, expected 65")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python analyze_balance_sequence.py <path_to_hdfc_pdf>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    if not os.path.exists(pdf_path):
        print(f"Error: File not found: {pdf_path}")
        sys.exit(1)
    
    analyze_balance_sequence(pdf_path)
