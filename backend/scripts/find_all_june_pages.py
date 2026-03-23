"""
Find all pages that contain June transactions.
"""

import sys
import os
import pdfplumber

def find_all_june_pages(pdf_path: str):
    """Find all pages with June transactions."""
    
    print("=" * 80)
    print("FINDING ALL JUNE PAGES")
    print("=" * 80)
    
    june_pages = []
    
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            tables = page.extract_tables()
            
            has_june = False
            june_count = 0
            
            for table in tables:
                if not table:
                    continue
                
                for row in table:
                    if not row or len(row) < 7:
                        continue
                    
                    # Check if any cell contains June dates
                    for cell in row:
                        cell_str = str(cell or "")
                        if '/06/25' in cell_str:
                            has_june = True
                            # Count June dates
                            dates = [d.strip() for d in cell_str.split('\n') if d.strip()]
                            for date in dates:
                                if '/06/25' in date:
                                    june_count += 1
            
            if has_june:
                june_pages.append({
                    'page_num': page_num + 1,
                    'june_count': june_count
                })
    
    print(f"Pages with June transactions: {len(june_pages)}")
    
    for page_info in june_pages:
        print(f"  Page {page_info['page_num']}: {page_info['june_count']} June dates")
    
    # Total June dates across all pages
    total_june = sum(p['june_count'] for p in june_pages)
    print(f"\nTotal June dates found: {total_june}")
    
    return june_pages

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python find_all_june_pages.py <path_to_hdfc_pdf>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    if not os.path.exists(pdf_path):
        print(f"Error: File not found: {pdf_path}")
        sys.exit(1)
    
    find_all_june_pages(pdf_path)
