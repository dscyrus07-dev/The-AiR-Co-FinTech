"""
Find exactly which transactions are missing from the coordinate parser.
Compare balance values from raw table extraction vs coordinate parser.
"""
import sys, os, re, pdfplumber
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def get_all_balances_from_tables(pdf_path):
    """Get ALL unique balance values from table extraction."""
    balances = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                if not table:
                    continue
                for row in table:
                    if not row or len(row) < 7:
                        continue
                    bal_str = str(row[6] or "")
                    for b in bal_str.split('\n'):
                        b = b.strip()
                        if b and b.replace(',','').replace('.','').isdigit():
                            balances.append(float(b.replace(',', '')))
    return balances

def get_all_balances_from_text(pdf_path):
    """Get all closing balances from text extraction with line context."""
    AMOUNT_RE = re.compile(r'[\d,]+\.\d{2}')
    DATE_RE = re.compile(r'^\d{2}/\d{2}/\d{2}\s+')
    
    results = []
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            text = page.extract_text()
            if not text:
                continue
            for line in text.split('\n'):
                line = line.strip()
                if DATE_RE.match(line):
                    amounts = AMOUNT_RE.findall(line)
                    if amounts:
                        last_amount = float(amounts[-1].replace(',', ''))
                        results.append({
                            'balance': last_amount,
                            'page': page_num + 1,
                            'line': line[:80]
                        })
    return results

def get_coordinate_parser_balances(pdf_path):
    """Get balances from coordinate parser."""
    # Import and run the coordinate parser
    COL_DATE_MAX = 65
    COL_BALANCE_MIN = 562
    DATE_RE = re.compile(r'^\d{2}/\d{2}/\d{2}$')
    
    balances = []
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            words = page.extract_words(keep_blank_chars=True, x_tolerance=2, y_tolerance=2)
            if not words:
                continue
            
            # Group by y
            y_groups = defaultdict(list)
            for w in words:
                y_key = round(w['top'] / 4) * 4
                y_groups[y_key].append(w)
            
            for y_key in sorted(y_groups.keys()):
                line_words = sorted(y_groups[y_key], key=lambda w: w['x0'])
                
                date_words = [w for w in line_words if w['x0'] < COL_DATE_MAX]
                balance_words = [w for w in line_words if w['x0'] >= COL_BALANCE_MIN]
                
                date_text = ' '.join(w['text'] for w in date_words).strip()
                balance_text = ' '.join(w['text'] for w in balance_words).strip()
                
                if DATE_RE.match(date_text) and balance_text:
                    try:
                        bal = float(balance_text.replace(',', ''))
                        balances.append({
                            'balance': bal,
                            'page': page_num + 1,
                            'y': y_key,
                            'date': date_text
                        })
                    except:
                        pass
    
    return balances

def main():
    pdf_path = sys.argv[1] if len(sys.argv) > 1 else "HDFC DATA/Hdfc Bank 1 June to 24 Jan 26.pdf"
    
    print("Extracting balances from text...")
    text_results = get_all_balances_from_text(pdf_path)
    text_balances = set(r['balance'] for r in text_results)
    
    print("Extracting balances from coordinates...")
    coord_results = get_coordinate_parser_balances(pdf_path)
    coord_balances = set(r['balance'] for r in coord_results)
    
    print(f"\nText extraction: {len(text_results)} transactions ({len(text_balances)} unique balances)")
    print(f"Coordinate parser: {len(coord_results)} transactions ({len(coord_balances)} unique balances)")
    
    # Find missing balances
    missing = text_balances - coord_balances
    extra = coord_balances - text_balances
    
    print(f"\nMissing from coordinate parser: {len(missing)}")
    print(f"Extra in coordinate parser: {len(extra)}")
    
    if missing:
        print("\nMISSING TRANSACTIONS (in text but not in coordinates):")
        for bal in sorted(missing):
            # Find context
            for r in text_results:
                if r['balance'] == bal:
                    print(f"  Balance: {bal:>14,.2f} | Page {r['page']} | {r['line']}")
                    break
    
    # Now check what's happening around missing balances in word extraction
    if missing:
        print("\n\nDEBUG: Word analysis around missing transactions:")
        with pdfplumber.open(pdf_path) as pdf:
            for bal in sorted(list(missing)[:5]):  # Check first 5 missing
                # Find which page
                for r in text_results:
                    if r['balance'] == bal:
                        page_num = r['page'] - 1
                        break
                
                page = pdf.pages[page_num]
                words = page.extract_words(keep_blank_chars=True, x_tolerance=2, y_tolerance=2)
                
                # Find the balance word
                for w in words:
                    try:
                        w_val = float(w['text'].replace(',', ''))
                        if abs(w_val - bal) < 0.01:
                            # Found it - show all words at this y-position
                            y = w['top']
                            nearby = [ww for ww in words if abs(ww['top'] - y) < 6]
                            nearby.sort(key=lambda x: x['x0'])
                            print(f"\n  Balance {bal:,.2f} at y={y:.1f}, page {page_num+1}:")
                            for nw in nearby:
                                print(f"    x={nw['x0']:6.1f}-{nw['x1']:6.1f} (y={nw['top']:6.1f}): '{nw['text']}'")
                            break
                    except:
                        pass

if __name__ == "__main__":
    main()
