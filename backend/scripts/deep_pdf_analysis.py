"""
Deep analysis of HDFC PDF to understand exact raw text structure.
"""
import sys
import os
import re
import pdfplumber

def analyze_pdf(pdf_path: str):
    """Extract and analyze raw text from PDF."""
    
    print("=" * 100)
    print("DEEP PDF RAW TEXT ANALYSIS")
    print("=" * 100)
    
    with pdfplumber.open(pdf_path) as pdf:
        print(f"Total pages: {len(pdf.pages)}")
        
        # Analyze first 3 pages in detail
        for page_num in range(min(3, len(pdf.pages))):
            page = pdf.pages[page_num]
            
            print(f"\n{'='*100}")
            print(f"PAGE {page_num + 1} - RAW TEXT")
            print(f"{'='*100}")
            
            text = page.extract_text()
            if text:
                lines = text.split('\n')
                for i, line in enumerate(lines):
                    print(f"LINE {i+1:3d}: [{line}]")
            
            print(f"\n{'='*100}")
            print(f"PAGE {page_num + 1} - TABLE EXTRACTION")
            print(f"{'='*100}")
            
            tables = page.extract_tables()
            for t_idx, table in enumerate(tables):
                print(f"\n  TABLE {t_idx + 1}: {len(table)} rows")
                for r_idx, row in enumerate(table):
                    print(f"    ROW {r_idx + 1}: {row}")

    # Now try extracting with extract_text() for all pages
    print(f"\n{'='*100}")
    print("FULL PDF TEXT - LINE BY LINE (first 200 lines)")
    print(f"{'='*100}")
    
    all_lines = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                for line in text.split('\n'):
                    all_lines.append(line)
    
    for i, line in enumerate(all_lines[:200]):
        print(f"{i+1:4d}: [{line}]")
    
    print(f"\nTotal lines: {len(all_lines)}")

if __name__ == "__main__":
    pdf_path = sys.argv[1] if len(sys.argv) > 1 else "HDFC DATA/Hdfc Bank 1 June to 24 Jan 26.pdf"
    if not os.path.exists(pdf_path):
        print(f"File not found: {pdf_path}")
        sys.exit(1)
    analyze_pdf(pdf_path)
