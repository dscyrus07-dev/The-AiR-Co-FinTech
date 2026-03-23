"""
Check narration quality - look for page header/footer text bleeding into narrations.
"""
import sys, os, re, pdfplumber
from collections import defaultdict

# Known header/footer text fragments that should NOT appear in narrations
HEADER_FRAGMENTS = [
    'NIWASMAR', 'KAROTRA', 'HDFCBANKLTD', 'NISMBHAVAN', 'NAVIMUMBAI',
    'MAHARASHTRA', 'ZOSTEL', 'ACADMEY', 'MILLTARYROAD', 'VASHISECTOR',
    'EXQUISITEHOSPITALITYMANAGEMENT', 'GROUNDFLR', 'NotRegistered',
    'BIZELITEPLUS', 'StatementFrom', 'AccountBranch',
]

def check_narration_quality(pdf_path):
    """Find narrations contaminated with header/footer text."""
    
    # First, find the y-bounds of the data area on page 1
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[0]
        words = page.extract_words(keep_blank_chars=True, x_tolerance=2, y_tolerance=2)
        
        # Find the "Date" header word
        header_y = None
        footer_y = None
        for w in words:
            if w['text'] == 'Date' and w['x0'] < 65:
                header_y = w['top']
                print(f"Header row y-position: {header_y:.1f}")
            if 'Closingbalanceincludesfunds' in w['text']:
                footer_y = w['top']
                print(f"Footer y-position: {footer_y:.1f}")
        
        # Check for continuation lines outside data area
        print(f"\nData area: y > {header_y + 10:.0f} and y < {footer_y - 10:.0f}")
        
        # Look at ALL y-positions of words in narration column
        print("\nAll lines in narration column (x 65-260):")
        y_groups = defaultdict(list)
        for w in words:
            if 65 <= w['x0'] < 260:
                y_key = round(w['top'] / 5) * 5
                y_groups[y_key].append(w)
        
        for y in sorted(y_groups.keys()):
            ws = sorted(y_groups[y], key=lambda w: w['x0'])
            text = ' '.join(w['text'] for w in ws)
            in_data = 'YES' if header_y and footer_y and header_y + 5 < y < footer_y - 5 else 'NO '
            print(f"  y={y:6.1f} [{in_data}]: {text[:80]}")
    
    # Check all pages for y-bounds consistency
    print("\n\nPAGE-BY-PAGE DATA AREA BOUNDS:")
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages[:5]):
            words = page.extract_words(keep_blank_chars=True, x_tolerance=2, y_tolerance=2)
            
            header_y = None
            footer_y = None
            for w in words:
                if w['text'] == 'Date' and w['x0'] < 65:
                    header_y = w['top']
                if 'Closingbalance' in w['text'] and w['x0'] < 300:
                    footer_y = w['top']
            
            print(f"  Page {page_num+1}: header_y={header_y}, footer_y={footer_y}")

if __name__ == "__main__":
    pdf_path = sys.argv[1] if len(sys.argv) > 1 else "HDFC DATA/Hdfc Bank 1 June to 24 Jan 26.pdf"
    check_narration_quality(pdf_path)
