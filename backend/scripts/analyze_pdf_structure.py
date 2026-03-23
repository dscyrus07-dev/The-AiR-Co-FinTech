"""
Analyze the exact structure of HDFC PDF to understand cell alignment.
"""

import sys
import os
import pdfplumber

def analyze_structure(pdf_path: str):
    """Analyze PDF structure in detail."""
    
    print("=" * 80)
    print("DETAILED PDF STRUCTURE ANALYSIS")
    print("=" * 80)
    
    with pdfplumber.open(pdf_path) as pdf:
        # Analyze first few pages
        for page_num in range(min(3, len(pdf.pages))):
            page = pdf.pages[page_num]
            tables = page.extract_tables()
            
            print(f"\n{'='*80}")
            print(f"PAGE {page_num + 1}")
            print(f"{'='*80}")
            print(f"Number of tables: {len(tables)}")
            
            for table_idx, table in enumerate(tables):
                if not table:
                    continue
                
                print(f"\nTable {table_idx + 1}: {len(table)} rows")
                
                # Show first 5 rows in detail
                for row_idx in range(min(5, len(table))):
                    row = table[row_idx]
                    if not row or len(row) < 7:
                        continue
                    
                    print(f"\n  Row {row_idx + 1}:")
                    print(f"    Columns: {len(row)}")
                    
                    for col_idx, cell in enumerate(row):
                        cell_str = str(cell or "")
                        lines = cell_str.split('\n')
                        
                        if len(lines) > 1:
                            print(f"    Col {col_idx} ({len(lines)} lines):")
                            for line_idx, line in enumerate(lines[:5]):  # Show first 5 lines
                                print(f"      [{line_idx}] {line[:60]}")
                            if len(lines) > 5:
                                print(f"      ... and {len(lines) - 5} more lines")
                        else:
                            print(f"    Col {col_idx}: {cell_str[:60]}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python analyze_pdf_structure.py <path_to_pdf>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    if not os.path.exists(pdf_path):
        print(f"Error: File not found: {pdf_path}")
        sys.exit(1)
    
    analyze_structure(pdf_path)
