"""
Analyze word positions in HDFC PDF to understand exact column boundaries.
"""
import sys
import os
import pdfplumber

def analyze_word_positions(pdf_path: str):
    """Extract words with their x-coordinates to determine column boundaries."""
    
    with pdfplumber.open(pdf_path) as pdf:
        # Analyze first page
        page = pdf.pages[0]
        
        # Get page width
        print(f"Page width: {page.width}")
        print(f"Page height: {page.height}")
        
        # Extract words with positions
        words = page.extract_words(keep_blank_chars=True, x_tolerance=2, y_tolerance=2)
        
        print(f"\nTotal words on page 1: {len(words)}")
        
        # Find the header row to determine column boundaries
        print("\n=== HEADER ANALYSIS ===")
        header_words = []
        for w in words:
            if any(h in w['text'] for h in ['Date', 'Narration', 'Chq', 'Ref', 'Value', 'Withdrawal', 'Deposit', 'Closing', 'Balance']):
                header_words.append(w)
                print(f"  Header word: '{w['text']}' at x0={w['x0']:.1f}, x1={w['x1']:.1f}, top={w['top']:.1f}")
        
        # Show all words for first few transactions (by y position)
        print("\n=== FIRST TRANSACTION WORDS (sorted by y, then x) ===")
        sorted_words = sorted(words, key=lambda w: (round(w['top'], 0), w['x0']))
        
        current_y = None
        line_count = 0
        for w in sorted_words:
            y = round(w['top'], 0)
            if y != current_y:
                if line_count > 40:  # Show first 40 lines
                    break
                current_y = y
                line_count += 1
                print(f"\n  LINE {line_count} (y={y}):")
            print(f"    x={w['x0']:6.1f}-{w['x1']:6.1f}: '{w['text']}'")
        
        # Try to determine column boundaries from header
        print("\n\n=== COLUMN BOUNDARY ANALYSIS ===")
        
        # Group words by approximate y-position to find lines
        lines_dict = {}
        for w in words:
            y_key = round(w['top'] / 3) * 3  # Group within 3 units
            if y_key not in lines_dict:
                lines_dict[y_key] = []
            lines_dict[y_key].append(w)
        
        # Sort lines by y
        sorted_lines = sorted(lines_dict.items())
        
        # Show first 20 reconstructed lines
        print("\nFirst 20 reconstructed lines:")
        for i, (y, line_words) in enumerate(sorted_lines[:20]):
            line_words.sort(key=lambda w: w['x0'])
            text = ' '.join(w['text'] for w in line_words)
            print(f"  y={y:6.1f}: {text[:120]}")

if __name__ == "__main__":
    pdf_path = sys.argv[1] if len(sys.argv) > 1 else "HDFC DATA/Hdfc Bank 1 June to 24 Jan 26.pdf"
    if not os.path.exists(pdf_path):
        print(f"File not found: {pdf_path}")
        sys.exit(1)
    analyze_word_positions(pdf_path)
