"""
Debug script to analyze HDFC PDF parsing and identify why 127 transactions instead of 65.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.banks.hdfc.parser import HDFCParser
import pdfplumber

def debug_parse(pdf_path: str):
    """Debug the parsing process step by step."""
    
    print("=" * 80)
    print("HDFC PARSER DEBUG ANALYSIS")
    print("=" * 80)
    print(f"PDF: {pdf_path}\n")
    
    # Step 1: Extract raw table rows
    print("STEP 1: Extracting raw table rows...")
    raw_rows = []
    
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            tables = page.extract_tables()
            
            for table_idx, table in enumerate(tables):
                if not table:
                    continue
                
                print(f"\nPage {page_num + 1}, Table {table_idx + 1}: {len(table)} rows")
                
                for row_idx, row in enumerate(table):
                    if not row or len(row) < 7:
                        continue
                    
                    raw_rows.append({
                        'page': page_num + 1,
                        'table': table_idx + 1,
                        'row': row_idx + 1,
                        'data': row
                    })
    
    print(f"\nTotal raw rows extracted: {len(raw_rows)}")
    
    # Step 2: Analyze each row
    print("\n" + "=" * 80)
    print("STEP 2: Analyzing each row...")
    print("=" * 80)
    
    import re
    DATE_RE = re.compile(r'^(\d{2}/\d{2}/\d{2,4})\s*')
    
    valid_transactions = []
    continuation_rows = []
    invalid_rows = []
    
    for item in raw_rows:
        row = item['data']
        
        date_str = str(row[0] or "").strip()
        narration = str(row[1] or "").strip()
        withdrawal_str = str(row[4] or "").strip()
        deposit_str = str(row[5] or "").strip()
        balance_str = str(row[6] or "").strip()
        
        has_date = bool(DATE_RE.match(date_str))
        has_withdrawal = bool(withdrawal_str and withdrawal_str.replace(',', '').replace('.', '').isdigit())
        has_deposit = bool(deposit_str and deposit_str.replace(',', '').replace('.', '').isdigit())
        has_balance = bool(balance_str and balance_str.replace(',', '').replace('.', '').isdigit())
        
        # Classify row
        if has_date and has_balance and (has_withdrawal or has_deposit):
            valid_transactions.append(item)
            status = "✓ VALID TRANSACTION"
        elif has_date and not has_balance:
            continuation_rows.append(item)
            status = "→ CONTINUATION (date but no balance)"
        else:
            invalid_rows.append(item)
            status = "✗ INVALID/HEADER"
        
        # Print first 20 rows for inspection
        if len(valid_transactions) + len(continuation_rows) + len(invalid_rows) <= 20:
            print(f"\nRow {item['row']} (Page {item['page']}, Table {item['table']}): {status}")
            print(f"  Date: '{date_str}' | Has Date: {has_date}")
            print(f"  Narration: '{narration[:50]}...' " if len(narration) > 50 else f"  Narration: '{narration}'")
            print(f"  Withdrawal: '{withdrawal_str}' | Deposit: '{deposit_str}' | Balance: '{balance_str}'")
            print(f"  Has Amount: {has_withdrawal or has_deposit} | Has Balance: {has_balance}")
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total raw rows:          {len(raw_rows)}")
    print(f"Valid transactions:      {len(valid_transactions)}")
    print(f"Continuation rows:       {len(continuation_rows)}")
    print(f"Invalid/Header rows:     {len(invalid_rows)}")
    print()
    
    # Step 3: Show sample valid transactions
    print("=" * 80)
    print("SAMPLE VALID TRANSACTIONS (First 10)")
    print("=" * 80)
    
    for i, item in enumerate(valid_transactions[:10]):
        row = item['data']
        print(f"\n{i+1}. Date: {row[0]} | Narration: {str(row[1])[:40]}...")
        print(f"   W: {row[4]} | D: {row[5]} | Bal: {row[6]}")
    
    # Step 4: Check for duplicates
    print("\n" + "=" * 80)
    print("CHECKING FOR DUPLICATES")
    print("=" * 80)
    
    seen_balances = {}
    duplicates = []
    
    for item in valid_transactions:
        row = item['data']
        date_str = str(row[0] or "").strip()
        balance_str = str(row[6] or "").strip()
        key = f"{date_str}_{balance_str}"
        
        if key in seen_balances:
            duplicates.append({
                'key': key,
                'first': seen_balances[key],
                'duplicate': item
            })
        else:
            seen_balances[key] = item
    
    if duplicates:
        print(f"Found {len(duplicates)} duplicate transactions!")
        for dup in duplicates[:5]:
            print(f"\nDuplicate key: {dup['key']}")
            print(f"  First occurrence: Page {dup['first']['page']}, Row {dup['first']['row']}")
            print(f"  Duplicate: Page {dup['duplicate']['page']}, Row {dup['duplicate']['row']}")
    else:
        print("No duplicates found based on date+balance key.")
    
    unique_count = len(seen_balances)
    print(f"\nUnique transactions (after dedup): {unique_count}")
    
    # Step 5: Run actual parser
    print("\n" + "=" * 80)
    print("RUNNING ACTUAL PARSER")
    print("=" * 80)
    
    parser = HDFCParser()
    result = parser.parse(pdf_path)
    
    print(f"Parser returned: {result.total_count} transactions")
    print(f"Parse method: {result.parse_method}")
    print(f"Opening balance: {result.opening_balance}")
    print(f"Closing balance: {result.closing_balance}")
    
    return {
        'raw_rows': len(raw_rows),
        'valid_transactions': len(valid_transactions),
        'continuation_rows': len(continuation_rows),
        'invalid_rows': len(invalid_rows),
        'unique_count': unique_count,
        'parser_count': result.total_count
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python debug_hdfc_parser.py <path_to_hdfc_pdf>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    if not os.path.exists(pdf_path):
        print(f"Error: File not found: {pdf_path}")
        sys.exit(1)
    
    results = debug_parse(pdf_path)
    
    print("\n" + "=" * 80)
    print("FINAL ANALYSIS")
    print("=" * 80)
    print(f"Expected: 65 transactions (manual count)")
    print(f"Got:      {results['parser_count']} transactions")
    print(f"Unique:   {results['unique_count']} unique date+balance combinations")
    print()
    
    if results['parser_count'] == 65:
        print("✓ SUCCESS! Parser is working correctly.")
    else:
        print("✗ ISSUE: Parser count doesn't match expected count.")
        print("\nPossible causes:")
        print(f"  - Multi-line narrations: {results['continuation_rows']} continuation rows found")
        print(f"  - Duplicate entries: {results['valid_transactions'] - results['unique_count']} duplicates")
        print(f"  - Invalid rows counted: Check if headers/footers are being parsed")
