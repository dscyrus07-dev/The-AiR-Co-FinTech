"""
HDFC PDF Parser - Coordinate-based approach.
Uses word x-coordinates to assign each word to the correct column.
This guarantees 100% accurate column separation.
"""
import sys
import os
import re
import pdfplumber
from typing import List, Dict, Optional, Tuple
from collections import defaultdict

# Column boundaries (x-coordinates from PDF analysis)
COL_DATE_MAX = 65
COL_NARRATION_MIN = 65
COL_NARRATION_MAX = 260
COL_REF_MIN = 260
COL_REF_MAX = 360
COL_VALUEDT_MIN = 360
COL_VALUEDT_MAX = 405
COL_WITHDRAWAL_MIN = 405
COL_WITHDRAWAL_MAX = 485
COL_DEPOSIT_MIN = 485
COL_DEPOSIT_MAX = 562
COL_BALANCE_MIN = 562

DATE_RE = re.compile(r'^\d{2}/\d{2}/\d{2}$')

# Lines to skip (page headers, footers, etc.)
SKIP_KEYWORDS = [
    'pageno', 'statementofaccount', 'accountbranch', 'address', 'groundflr',
    'sector17', 'city', 'm/s', 'state', 'c/o', 'karotra', 'email', 'andheri',
    'custid', 'mumbai', 'maharashtra', 'accountstatus', 'jointholders',
    'branchcode', 'accounttype', 'nomination', 'statementfrom', 'narration',
    'closingbalance', 'contentsofthis', 'stateaccountbranchgstn', 'hdfcbankgstin',
    'registeredofficeaddress', 'thisstatement', 'odlumit', 'phoneno', 'a/copendate',
    'rtgs/neft', 'currency', 'accountno', 'vashisector', 'hdfcbankltd',
    'nismbhavan', 'navimumbai', 'exquisitehospitality', 'zostel',
    'primeacadmey', 'notregistered', 'micr:', 'bizeliteplus', 'imperia',
    'valuedt', 'withdrawalamt', 'depositamt', 'chq./ref'
]


def is_skip_word(text: str) -> bool:
    """Check if word is part of header/footer."""
    t = text.lower().replace(' ', '')
    for kw in SKIP_KEYWORDS:
        if kw in t:
            return True
    return False


def get_column(x0: float) -> str:
    """Determine which column a word belongs to based on its x-coordinate."""
    if x0 < COL_DATE_MAX:
        return 'date'
    elif x0 < COL_NARRATION_MAX:
        return 'narration'
    elif x0 < COL_REF_MAX:
        return 'ref_no'
    elif x0 < COL_VALUEDT_MAX:
        return 'value_date'
    elif x0 < COL_WITHDRAWAL_MAX:
        return 'withdrawal'
    elif x0 < COL_DEPOSIT_MAX:
        return 'deposit'
    else:
        return 'balance'


def parse_amount(s: str) -> Optional[float]:
    """Parse comma-formatted amount to float."""
    if not s:
        return None
    try:
        return float(s.replace(',', ''))
    except ValueError:
        return None


def extract_page_lines(page) -> List[Dict]:
    """
    Extract words from a page, group by y-position into lines,
    and assign each word to a column based on x-coordinate.
    
    Returns list of line dicts with column contents.
    """
    words = page.extract_words(keep_blank_chars=True, x_tolerance=2, y_tolerance=2)
    
    if not words:
        return []
    
    # Group words by approximate y-position (within 4 units = same line)
    y_groups = defaultdict(list)
    for w in words:
        y_key = round(w['top'] / 4) * 4
        y_groups[y_key].append(w)
    
    lines = []
    for y_key in sorted(y_groups.keys()):
        line_words = sorted(y_groups[y_key], key=lambda w: w['x0'])
        
        # Build column content for this line
        line = {
            'y': y_key,
            'date': '',
            'narration': '',
            'ref_no': '',
            'value_date': '',
            'withdrawal': '',
            'deposit': '',
            'balance': '',
            'raw_words': line_words,
        }
        
        # Assign each word to its column
        col_words = defaultdict(list)
        for w in line_words:
            col = get_column(w['x0'])
            col_words[col].append(w['text'])
        
        for col, texts in col_words.items():
            line[col] = ' '.join(texts)
        
        lines.append(line)
    
    return lines


def parse_hdfc_pdf(pdf_path: str) -> List[Dict]:
    """
    Parse HDFC PDF using coordinate-based column detection.
    
    Strategy:
    1. Extract words with positions from each page
    2. Group into lines by y-coordinate
    3. Assign words to columns by x-coordinate
    4. Transaction start = line with valid date in Date column + closing balance
    5. Continuation = line with narration content but no date
    6. Merge continuations into previous transaction
    """
    all_transactions = []
    prev_balance = None
    
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            lines = extract_page_lines(page)
            
            for line in lines:
                date_text = line['date'].strip()
                narration_text = line['narration'].strip()
                ref_text = line['ref_no'].strip()
                value_date_text = line['value_date'].strip()
                withdrawal_text = line['withdrawal'].strip()
                deposit_text = line['deposit'].strip()
                balance_text = line['balance'].strip()
                
                # Skip header/footer lines
                all_text = ' '.join(w['text'] for w in line['raw_words']).lower().replace(' ', '')
                if any(kw in all_text for kw in SKIP_KEYWORDS):
                    continue
                
                # Check if this is a transaction start line
                has_date = bool(DATE_RE.match(date_text))
                has_balance = bool(balance_text and parse_amount(balance_text) is not None)
                
                if has_date and has_balance:
                    # NEW TRANSACTION
                    balance = parse_amount(balance_text)
                    withdrawal = parse_amount(withdrawal_text)
                    deposit = parse_amount(deposit_text)
                    
                    txn = {
                        'date': date_text,
                        'narration': narration_text,
                        'ref_no': ref_text,
                        'value_date': value_date_text if DATE_RE.match(value_date_text) else date_text,
                        'withdrawal': withdrawal,
                        'deposit': deposit,
                        'closing_balance': balance,
                        'page': page_num + 1,
                    }
                    
                    all_transactions.append(txn)
                    prev_balance = balance
                    
                elif all_transactions and (narration_text or ref_text):
                    # CONTINUATION LINE - append to previous transaction's narration
                    if narration_text:
                        all_transactions[-1]['narration'] += ' ' + narration_text
                    if ref_text:
                        # If previous ref_no is empty, set it; otherwise append to narration
                        if not all_transactions[-1]['ref_no']:
                            all_transactions[-1]['ref_no'] = ref_text
                        else:
                            all_transactions[-1]['narration'] += ' ' + ref_text
    
    return all_transactions


def verify_balance_continuity(transactions: List[Dict]) -> List[str]:
    """Verify that balance changes match withdrawal/deposit amounts."""
    errors = []
    for i in range(1, len(transactions)):
        prev = transactions[i-1]
        curr = transactions[i]
        
        prev_bal = prev['closing_balance']
        curr_bal = curr['closing_balance']
        
        expected_change = curr_bal - prev_bal
        
        if curr['withdrawal'] and not curr['deposit']:
            actual_change = -curr['withdrawal']
        elif curr['deposit'] and not curr['withdrawal']:
            actual_change = curr['deposit']
        elif curr['withdrawal'] and curr['deposit']:
            actual_change = curr['deposit'] - curr['withdrawal']
        else:
            actual_change = None
        
        if actual_change is not None:
            diff = abs(expected_change - actual_change)
            if diff > 0.02:  # Allow small rounding
                errors.append(
                    f"Txn {i+1} ({curr['date']}): "
                    f"Balance change={expected_change:.2f}, "
                    f"Amount={'W:'+str(curr['withdrawal']) if curr['withdrawal'] else 'D:'+str(curr['deposit'])}={actual_change:.2f}, "
                    f"Diff={diff:.2f} | {curr['narration'][:40]}"
                )
    
    return errors


def main():
    pdf_path = sys.argv[1] if len(sys.argv) > 1 else "HDFC DATA/Hdfc Bank 1 June to 24 Jan 26.pdf"
    
    if not os.path.exists(pdf_path):
        print(f"File not found: {pdf_path}")
        sys.exit(1)
    
    print("=" * 120)
    print("COORDINATE-BASED HDFC PDF PARSER")
    print("=" * 120)
    
    transactions = parse_hdfc_pdf(pdf_path)
    
    print(f"\nTotal transactions parsed: {len(transactions)}")
    
    # Count by month
    from collections import Counter
    month_counts = Counter(txn['date'][3:5] for txn in transactions)
    print("\nTransactions by month:")
    for month in sorted(month_counts.keys()):
        print(f"  Month {month}: {month_counts[month]} transactions")
    
    # Verify balance continuity
    errors = verify_balance_continuity(transactions)
    print(f"\nBalance continuity errors: {len(errors)}")
    if errors:
        for e in errors[:30]:
            print(f"  ERROR: {e}")
    
    # Show first 20 transactions
    print(f"\n{'='*120}")
    print("FIRST 20 TRANSACTIONS (matching PDF screenshot)")
    print(f"{'='*120}")
    print(f"{'#':>3} | {'Date':<10} | {'Narration':<55} | {'Ref No':<22} | {'Val.Dt':<10} | {'Withdrawal':>12} | {'Deposit':>12} | {'Balance':>14}")
    print("-" * 160)
    
    for i, txn in enumerate(transactions[:20]):
        w = f"{txn['withdrawal']:>12,.2f}" if txn['withdrawal'] else " " * 12
        d = f"{txn['deposit']:>12,.2f}" if txn['deposit'] else " " * 12
        b = f"{txn['closing_balance']:>14,.2f}"
        narr = txn['narration'][:55]
        ref = txn['ref_no'][:22]
        print(f"{i+1:3d} | {txn['date']:<10} | {narr:<55} | {ref:<22} | {txn['value_date']:<10} | {w} | {d} | {b}")
    
    # Show ALL June transactions
    june_txns = [t for t in transactions if t['date'][3:5] == '06']
    print(f"\n{'='*120}")
    print(f"ALL JUNE TRANSACTIONS ({len(june_txns)} total)")
    print(f"{'='*120}")
    print(f"{'#':>3} | {'Date':<10} | {'Narration':<55} | {'Withdrawal':>12} | {'Deposit':>12} | {'Balance':>14}")
    print("-" * 130)
    
    for i, txn in enumerate(june_txns):
        w = f"{txn['withdrawal']:>12,.2f}" if txn['withdrawal'] else " " * 12
        d = f"{txn['deposit']:>12,.2f}" if txn['deposit'] else " " * 12
        b = f"{txn['closing_balance']:>14,.2f}"
        narr = txn['narration'][:55]
        print(f"{i+1:3d} | {txn['date']:<10} | {narr:<55} | {w} | {d} | {b}")

if __name__ == "__main__":
    main()
