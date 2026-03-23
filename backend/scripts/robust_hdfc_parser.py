"""
Robust HDFC PDF Parser - Text-based line-by-line approach.
Handles multi-line narrations by detecting transaction start lines (DD/MM/YY + closing balance).
"""
import sys
import os
import re
import pdfplumber
from typing import List, Dict, Optional, Tuple

# Date pattern: DD/MM/YY at start of line
DATE_RE = re.compile(r'^(\d{2}/\d{2}/\d{2})\s+')

# Amount pattern: comma-separated number like 1,234.56 or 500,000.00
AMOUNT_RE = re.compile(r'[\d,]+\.\d{2}')

# Page header/footer patterns to skip
SKIP_PATTERNS = [
    'PageNo', 'Statementofaccount', 'AccountBranch', 'Address',
    'GROUNDFLR', 'SECTOR17', 'City', 'M/S.', 'State', 'C/O',
    'KAROTRANIW', 'Email', 'ANDHERI', 'CustID', 'MUMBAI',
    'MAHARASHTRA', 'AccountStatus', 'JOINTHOLDERS', 'BranchCode',
    'AccountType', 'Nomination', 'StatementFrom', 'Date Narration',
    'Closingbalance', 'Contentsofthis', 'StateaccountbranchGSTN',
    'HDFCBankGSTIN', 'RegisteredOfficeAddress', 'thisstatement',
    'ODLimit', 'Phoneno', 'A/COpenDate', 'RTGS/NEFT',
    'Currency', 'AccountNo',
]

def is_skip_line(line: str) -> bool:
    """Check if line is a header/footer that should be skipped."""
    line_stripped = line.strip()
    if not line_stripped:
        return True
    for pattern in SKIP_PATTERNS:
        if pattern.lower() in line_stripped.lower().replace(' ', ''):
            return True
    return False

def parse_amount(s: str) -> Optional[float]:
    """Parse comma-formatted amount string to float."""
    if not s:
        return None
    try:
        return float(s.replace(',', ''))
    except ValueError:
        return None

def is_transaction_line(line: str) -> bool:
    """Check if line starts a new transaction (starts with date, ends with amount)."""
    line = line.strip()
    if not DATE_RE.match(line):
        return False
    # Must have at least one amount (closing balance) at the end
    amounts = AMOUNT_RE.findall(line)
    return len(amounts) >= 1

def parse_transaction_line(line: str) -> Optional[Dict]:
    """
    Parse a transaction start line into components.
    Format: DATE NARRATION REF_NO VALUE_DATE [WITHDRAWAL] [DEPOSIT] CLOSING_BALANCE
    
    The closing balance is ALWAYS the last amount.
    Before it: either withdrawal OR deposit (sometimes both if refund scenario).
    We need the VALUE_DATE (DD/MM/YY) to separate narration from amounts.
    """
    line = line.strip()
    
    # Extract the leading date
    m = DATE_RE.match(line)
    if not m:
        return None
    date = m.group(1)
    rest = line[m.end():]
    
    # Find ALL amounts in the line
    amounts_with_pos = [(m.start(), m.end(), m.group()) for m in AMOUNT_RE.finditer(rest)]
    
    if not amounts_with_pos:
        return None
    
    # Closing balance is the LAST amount
    closing_balance_str = amounts_with_pos[-1][2]
    closing_balance = parse_amount(closing_balance_str)
    
    # Find value date - it's a DD/MM/YY pattern before the amounts
    # Look for the LAST date pattern before the first amount
    date_positions = [(m.start(), m.group()) for m in re.finditer(r'\d{2}/\d{2}/\d{2}', rest)]
    
    value_date = date  # Default to transaction date
    
    # The amounts section starts from the position of the first amount that's part of the
    # withdrawal/deposit/balance group at the end
    # We need to find where the "numbers section" begins
    
    # Strategy: Find the value date (last DD/MM/YY before amounts), 
    # then everything after value_date is amounts
    
    first_amount_pos = amounts_with_pos[0][0]
    
    # Find the last date before the first amount
    for pos, dt in date_positions:
        if pos < first_amount_pos:
            value_date = dt
            narration_and_ref = rest[:pos].strip()
    
    # If no date found before amounts, the narration is everything before amounts
    if 'narration_and_ref' not in dir():
        # Find where the amount section starts
        # Look backwards from the last amount to find all consecutive amounts
        narration_and_ref = rest[:first_amount_pos].strip()
    
    # Parse amounts: could be 1, 2, or 3 amounts
    # 1 amount = closing balance only (no withdrawal/deposit on this line - rare)
    # 2 amounts = withdrawal OR deposit + closing balance
    # 3 amounts = withdrawal + deposit + closing balance (very rare)
    
    withdrawal = None
    deposit = None
    
    if len(amounts_with_pos) == 1:
        # Only closing balance
        pass
    elif len(amounts_with_pos) == 2:
        # One amount + closing balance
        amt = parse_amount(amounts_with_pos[0][2])
        # We'll determine debit/credit later using balance comparison
        # For now store as "amount"
        withdrawal = amt  # Placeholder - will be resolved later
        deposit = amt     # Placeholder
    elif len(amounts_with_pos) >= 3:
        # withdrawal + deposit + closing balance OR other combinations
        withdrawal = parse_amount(amounts_with_pos[-3][2])
        deposit = parse_amount(amounts_with_pos[-2][2])
    
    # Split narration_and_ref into narration and ref_no
    # Ref number is typically a long alphanumeric string
    # For now, keep them together - we'll split later
    
    return {
        'date': date,
        'narration_and_ref': narration_and_ref,
        'value_date': value_date,
        'amounts': [parse_amount(a[2]) for a in amounts_with_pos],
        'closing_balance': closing_balance,
        'raw_line': line,
    }

def extract_all_text_lines(pdf_path: str) -> List[str]:
    """Extract all text lines from PDF, skipping headers/footers."""
    all_lines = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                for line in text.split('\n'):
                    line = line.strip()
                    if line and not is_skip_line(line):
                        all_lines.append(line)
    return all_lines

def parse_hdfc_pdf(pdf_path: str) -> List[Dict]:
    """
    Main parser: Extract transactions from HDFC PDF.
    
    Strategy:
    1. Get all text lines (skip headers/footers)
    2. Identify transaction start lines (start with date, end with amounts)
    3. Append continuation lines to previous transaction's narration
    4. Determine debit/credit using balance comparison
    """
    lines = extract_all_text_lines(pdf_path)
    
    # Phase 1: Group lines into transactions
    raw_transactions = []  # List of {'first_line': ..., 'continuation': [...]}
    
    for line in lines:
        if is_transaction_line(line):
            raw_transactions.append({
                'first_line': line,
                'continuation': []
            })
        elif raw_transactions:
            # Continuation line - append to previous transaction
            raw_transactions[-1]['continuation'].append(line)
    
    # Phase 2: Parse each transaction
    transactions = []
    prev_balance = None
    
    for raw_txn in raw_transactions:
        parsed = parse_transaction_line(raw_txn['first_line'])
        if not parsed:
            continue
        
        # Build full narration from first line + continuations
        full_narration = parsed['narration_and_ref']
        for cont_line in raw_txn['continuation']:
            full_narration += ' ' + cont_line
        
        # Determine debit/credit using balance comparison
        balance = parsed['closing_balance']
        amounts = parsed['amounts']
        
        debit = None
        credit = None
        
        if prev_balance is not None and len(amounts) >= 2:
            # amounts[-1] is closing balance
            # amounts[-2] is the transaction amount (or deposit if 3 amounts)
            
            if balance < prev_balance:
                # Balance decreased = DEBIT (withdrawal)
                debit = amounts[-2]  # The amount before closing balance
                credit = None
            elif balance > prev_balance:
                # Balance increased = CREDIT (deposit)
                credit = amounts[-2]
                debit = None
            else:
                # Same balance (shouldn't happen normally)
                pass
        elif prev_balance is None and len(amounts) >= 2:
            # First transaction - assume credit if positive movement from opening
            credit = amounts[-2]
        
        # Try to split narration and ref_no
        # The ref_no is typically embedded in the narration line
        # For HDFC: it appears after the main narration text
        narration = full_narration.strip()
        
        transactions.append({
            'date': parsed['date'],
            'narration': narration,
            'value_date': parsed['value_date'],
            'withdrawal': debit,
            'deposit': credit,
            'closing_balance': balance,
        })
        
        prev_balance = balance
    
    return transactions

def main():
    pdf_path = sys.argv[1] if len(sys.argv) > 1 else "HDFC DATA/Hdfc Bank 1 June to 24 Jan 26.pdf"
    
    if not os.path.exists(pdf_path):
        print(f"File not found: {pdf_path}")
        sys.exit(1)
    
    print("=" * 120)
    print("ROBUST HDFC PDF PARSER - TEST RUN")
    print("=" * 120)
    
    transactions = parse_hdfc_pdf(pdf_path)
    
    print(f"\nTotal transactions parsed: {len(transactions)}")
    
    # Count by month
    from collections import defaultdict
    month_counts = defaultdict(int)
    for txn in transactions:
        month = txn['date'][3:5]
        month_counts[month] += 1
    
    print("\nTransactions by month:")
    for month in sorted(month_counts.keys()):
        print(f"  Month {month}: {month_counts[month]} transactions")
    
    # Show first 30 transactions with full details
    print(f"\n{'='*120}")
    print("FIRST 30 TRANSACTIONS")
    print(f"{'='*120}")
    
    for i, txn in enumerate(transactions[:30]):
        w = f"{txn['withdrawal']:>12,.2f}" if txn['withdrawal'] else "            "
        d = f"{txn['deposit']:>12,.2f}" if txn['deposit'] else "            "
        b = f"{txn['closing_balance']:>14,.2f}" if txn['closing_balance'] else "              "
        print(f"{i+1:3d}. {txn['date']} | W:{w} | D:{d} | B:{b} | {txn['narration'][:70]}")

if __name__ == "__main__":
    main()
