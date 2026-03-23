"""
Deep analysis of June structure to understand the 65 vs 127 discrepancy.
"""

import sys
import os
import pdfplumber

def analyze_june_structure(pdf_path: str):
    """Analyze June structure in detail."""
    
    print("=" * 80)
    print("DEEP JUNE STRUCTURE ANALYSIS")
    print("=" * 80)
    
    all_june_balances = []
    unique_balances = set()
    
    with pdfplumber.open(pdf_path) as pdf:
        for page_num in range(9):  # First 9 pages have June
            page = pdf.pages[page_num]
            tables = page.extract_tables()
            
            print(f"\n--- PAGE {page_num + 1} ---")
            
            for table_idx, table in enumerate(tables):
                if not table:
                    continue
                
                for row_idx, row in enumerate(table):
                    if not row or len(row) < 7:
                        continue
                    
                    # Get dates and balances
                    dates = [d.strip() for d in str(row[0] or "").split('\n') if d.strip()]
                    balances = [b.strip() for b in str(row[6] or "").split('\n') if b.strip()]
                    
                    # Skip headers
                    if not balances or any(b.upper() in ['CLOSINGBALANCE', 'CLOSING BALANCE'] for b in balances):
                        continue
                    
                    # Find June entries
                    for i, date in enumerate(dates):
                        if '/06/25' in date and i < len(balances):
                            balance = balances[i]
                            balance_key = f"{date}_{balance}"
                            
                            all_june_balances.append({
                                'date': date,
                                'balance': balance,
                                'page': page_num + 1,
                                'table': table_idx + 1,
                                'row': row_idx + 1
                            })
                            
                            unique_balances.add(balance_key)
    
    print(f"\nTotal June entries found: {len(all_june_balances)}")
    print(f"Unique date+balance combinations: {len(unique_balances)}")
    
    # Group by date
    from collections import defaultdict
    date_groups = defaultdict(list)
    
    for entry in all_june_balances:
        date_groups[entry['date']].append(entry)
    
    print(f"\nUnique dates in June: {len(date_groups)}")
    
    # Show date distribution
    print("\nDate distribution:")
    for date in sorted(date_groups.keys()):
        entries = date_groups[date]
        print(f"  {date}: {len(entries)} entries")
        
        # Show if they have different balances
        balances = set(e['balance'] for e in entries)
        if len(balances) > 1:
            print(f"    -> Multiple balances: {balances}")
    
    # Check for exact 65 unique balances
    if len(unique_balances) == 65:
        print("\n✓ Found exactly 65 unique date+balance combinations!")
        print("This matches your manual count.")
    elif len(unique_balances) > 65:
        print(f"\n⚠ Found {len(unique_balances)} unique combinations, more than 65")
        print("Some entries might be duplicates or the PDF has extra data.")
    else:
        print(f"\n✗ Found only {len(unique_balances)} unique combinations, less than 65")
    
    # Show first 20 unique entries
    print("\nFirst 20 unique June entries:")
    unique_list = []
    seen = set()
    
    for entry in all_june_balances:
        key = f"{entry['date']}_{entry['balance']}"
        if key not in seen:
            unique_list.append(entry)
            seen.add(key)
            if len(unique_list) <= 20:
                print(f"{len(unique_list):2d}. {entry['date']} | {entry['balance']} | Page {entry['page']}")
    
    return len(unique_balances)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python analyze_june_structure.py <path_to_hdfc_pdf>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    if not os.path.exists(pdf_path):
        print(f"Error: File not found: {pdf_path}")
        sys.exit(1)
    
    unique_count = analyze_june_structure(pdf_path)
    
    print(f"\n{'='*80}")
    print(f"CONCLUSION:")
    print(f"  Unique June transactions: {unique_count}")
    print(f"  Your manual count: 65")
    print(f"  Parser count: 127")
    
    if unique_count == 65:
        print("  ✓ The PDF actually contains 65 unique transactions")
        print("  ✗ The parser is creating duplicates")
    elif unique_count == 127:
        print("  ✓ The PDF actually contains 127 unique transactions")
        print("  ⚠ Your manual count might be missing some entries")
    else:
        print(f"  ? The PDF contains {unique_count} unique transactions")
        print("  Need further investigation")
