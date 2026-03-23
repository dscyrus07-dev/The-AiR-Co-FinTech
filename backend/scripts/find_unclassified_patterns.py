"""Find patterns in unclassified transactions."""
import sys
sys.path.insert(0, ".")
from pathlib import Path
from collections import Counter
from app.services.pdf_detector import detect_pdf_type
from app.services.bank_detector import detect_bank
from app.services.parsers.hdfc_parser import parse as hdfc_parse
from app.services.parsers.icici_parser import parse as icici_parse
from app.services.parsers.kotak_parser import parse as kotak_parse
from app.services.parsers.axis_parser import parse as axis_parse
from app.services.parsers.hsbc_parser import parse as hsbc_parse
from app.services.rule_engine import apply_rule_engine

DATA_DIR = Path(r"x:\FinTech SAAS\FinTech SAAS\Data")
all_unclassified = []

for pdf in DATA_DIR.glob("*.pdf"):
    try:
        result = detect_pdf_type(str(pdf))
        bank = detect_bank(result['first_page_text'])
        
        if bank == 'hdfc':
            txns = hdfc_parse(str(pdf), result['text_content'])
        elif bank == 'icici':
            txns = icici_parse(str(pdf), result['text_content'])
        elif bank == 'kotak':
            txns = kotak_parse(str(pdf), result['text_content'])
        elif bank == 'axis':
            txns = axis_parse(str(pdf), result['text_content'])
        elif bank == 'hsbc':
            txns = hsbc_parse(str(pdf), result['text_content'])
        else:
            continue
        
        classified, unclassified = apply_rule_engine(txns)
        
        for t in unclassified:
            side = 'DR' if t.get('debit') else 'CR'
            all_unclassified.append((bank, t['description'], side))
    except Exception as e:
        print(f"Error processing {pdf.name}: {e}")

print(f"Total unclassified: {len(all_unclassified)}\n")

# Find common keywords
keywords = Counter()
for bank, desc, side in all_unclassified:
    words = [w for w in desc.upper().split() if len(w) > 3]
    keywords.update(words)

print("Top missing keywords:")
for kw, cnt in keywords.most_common(30):
    print(f"  {kw:20s}: {cnt}")

# Show samples by bank
print("\n\nSamples by bank:")
by_bank = {}
for bank, desc, side in all_unclassified:
    if bank not in by_bank:
        by_bank[bank] = []
    by_bank[bank].append((desc[:70], side))

for bank, samples in by_bank.items():
    print(f"\n{bank.upper()} ({len(samples)} unclassified):")
    seen = set()
    for desc, side in samples[:10]:
        if desc not in seen:
            seen.add(desc)
            print(f"  [{side}] {desc}")
