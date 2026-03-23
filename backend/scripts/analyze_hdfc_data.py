"""
Analyze all HDFC PDFs to identify missing categorization patterns.
"""
import sys
sys.path.insert(0, "x:/FinTech SAAS/FinTech SAAS/backend")

from pathlib import Path
from collections import Counter
from app.services.banks.hdfc.parser import HDFCParser
from app.services.banks.hdfc.rule_engine import HDFCRuleEngine

HDFC_DATA_DIR = Path(r"x:\FinTech SAAS\FinTech SAAS\HDFC DATA")

def main():
    parser = HDFCParser()
    rule_engine = HDFCRuleEngine()
    
    all_transactions = []
    all_unclassified = []
    
    print("="*100)
    print("HDFC DATA FOLDER ANALYSIS")
    print("="*100)
    
    pdf_files = sorted(HDFC_DATA_DIR.glob("*.pdf"))
    print(f"\nTotal HDFC PDFs: {len(pdf_files)}\n")
    
    for i, pdf_path in enumerate(pdf_files, 1):
        print(f"[{i}/{len(pdf_files)}] {pdf_path.name}")
        
        try:
            # Parse
            result = parser.parse(str(pdf_path))
            transactions = [t.to_dict() for t in result.transactions]
            
            # Classify
            classified, unclassified = rule_engine.classify(transactions)
            
            total = len(classified) + len(unclassified)
            accuracy = len(classified) / total * 100 if total > 0 else 0
            
            print(f"  Transactions: {total} | Classified: {len(classified)} ({accuracy:.1f}%) | Unclassified: {len(unclassified)}")
            
            all_transactions.extend(transactions)
            all_unclassified.extend(unclassified)
            
            if len(unclassified) > 0:
                print(f"  [!] Unclassified samples:")
                for txn in unclassified[:3]:
                    side = 'DR' if txn.get('debit') else 'CR'
                    desc = txn['description'][:80]
                    print(f"    [{side}] {desc}")
            print()
            
        except Exception as e:
            print(f"  [ERROR] {str(e)}\n")
    
    # Overall stats
    total_txns = len(all_transactions)
    total_unclassified = len(all_unclassified)
    total_classified = total_txns - total_unclassified
    overall_accuracy = total_classified / total_txns * 100 if total_txns > 0 else 0
    
    print("="*100)
    print("OVERALL STATISTICS")
    print("="*100)
    print(f"Total Transactions:   {total_txns}")
    print(f"Classified:           {total_classified} ({overall_accuracy:.1f}%)")
    print(f"Unclassified:         {total_unclassified} ({100-overall_accuracy:.1f}%)")
    
    # Find missing patterns
    if all_unclassified:
        print("\n" + "="*100)
        print("MISSING PATTERNS ANALYSIS")
        print("="*100)
        
        # Keyword frequency
        keywords = Counter()
        debit_patterns = []
        credit_patterns = []
        
        for txn in all_unclassified:
            desc = txn['description'].upper()
            is_debit = txn.get('debit') is not None
            
            # Extract keywords (words > 3 chars)
            words = [w for w in desc.split() if len(w) > 3 and not w.isdigit()]
            keywords.update(words)
            
            # Store full description
            if is_debit:
                debit_patterns.append(desc[:100])
            else:
                credit_patterns.append(desc[:100])
        
        print("\nTop 30 missing keywords:")
        for kw, cnt in keywords.most_common(30):
            print(f"  {kw:30s}: {cnt:3d}")
        
        print(f"\n\nUnclassified DEBIT patterns ({len(debit_patterns)}):")
        seen = set()
        for pattern in debit_patterns[:20]:
            if pattern not in seen:
                seen.add(pattern)
                print(f"  {pattern}")
        
        print(f"\n\nUnclassified CREDIT patterns ({len(credit_patterns)}):")
        seen = set()
        for pattern in credit_patterns[:20]:
            if pattern not in seen:
                seen.add(pattern)
                print(f"  {pattern}")
        
        # Save to file for reference
        with open("x:/FinTech SAAS/FinTech SAAS/backend/temp/unclassified_patterns.txt", "w", encoding="utf-8") as f:
            f.write("UNCLASSIFIED DEBIT PATTERNS\n")
            f.write("="*100 + "\n\n")
            for pattern in set(debit_patterns):
                f.write(f"{pattern}\n")
            
            f.write("\n\nUNCLASSIFIED CREDIT PATTERNS\n")
            f.write("="*100 + "\n\n")
            for pattern in set(credit_patterns):
                f.write(f"{pattern}\n")
        
        print(f"\n\n[SAVED] Full patterns saved to: backend/temp/unclassified_patterns.txt")

if __name__ == "__main__":
    main()
