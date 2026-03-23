"""
Comprehensive analysis of all PDFs in Data folder.
Identifies banks, transaction counts, classification rates, and gaps.
"""
import sys
import os
sys.path.insert(0, ".")

import pdfplumber
from pathlib import Path
from collections import Counter, defaultdict

from app.services.pdf_detector import detect_pdf_type
from app.services.bank_detector import detect_bank
from app.services.parsers.hdfc_parser import parse as hdfc_parse
from app.services.parsers.icici_parser import parse as icici_parse
from app.services.parsers.kotak_parser import parse as kotak_parse
from app.services.parsers.axis_parser import parse as axis_parse
from app.services.parsers.hsbc_parser import parse as hsbc_parse
from app.services.rule_engine import apply_rule_engine

DATA_DIR = Path(r"x:\FinTech SAAS\FinTech SAAS\Data")

def analyze_pdf(pdf_path: Path):
    """Analyze single PDF and return statistics."""
    try:
        # Detect PDF type
        result = detect_pdf_type(str(pdf_path))
        full_text = result['text_content']
        first_page = result['first_page_text']
        
        # Detect bank
        bank_name = detect_bank(first_page)
        
        # Parse based on bank
        transactions = []
        parser_used = None
        
        if bank_name == "hdfc":
            transactions = hdfc_parse(str(pdf_path), full_text)
            parser_used = "hdfc_parser"
        elif bank_name == "icici":
            transactions = icici_parse(str(pdf_path), full_text)
            parser_used = "icici_parser"
        elif bank_name == "kotak":
            transactions = kotak_parse(str(pdf_path), full_text)
            parser_used = "kotak_parser"
        elif bank_name == "axis":
            transactions = axis_parse(str(pdf_path), full_text)
            parser_used = "axis_parser"
        elif bank_name == "hsbc":
            transactions = hsbc_parse(str(pdf_path), full_text)
            parser_used = "hsbc_parser"
        else:
            bank_name = "unknown"
            parser_used = None
        
        # Classify transactions
        if transactions:
            classified, unclassified = apply_rule_engine(transactions)
            total = len(classified) + len(unclassified)
            
            # Category distribution
            categories = Counter(t.get('category') for t in classified)
            
            # Unclassified samples
            unclassified_samples = [
                {
                    'desc': t['description'][:80],
                    'side': 'DR' if t.get('debit') else 'CR',
                    'amount': t.get('debit') or t.get('credit')
                }
                for t in unclassified[:5]
            ]
            
            return {
                'status': 'success',
                'bank': bank_name,
                'parser': parser_used,
                'total_pages': result['total_pages'],
                'total_txns': total,
                'classified': len(classified),
                'unclassified': len(unclassified),
                'accuracy': len(classified) / total * 100 if total > 0 else 0,
                'categories': dict(categories.most_common()),
                'unclassified_samples': unclassified_samples
            }
        else:
            return {
                'status': 'no_transactions',
                'bank': bank_name,
                'parser': parser_used,
                'total_pages': result['total_pages'],
                'total_txns': 0,
                'error': 'No transactions extracted'
            }
            
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e)
        }

def main():
    """Analyze all PDFs and print comprehensive report."""
    pdf_files = sorted([f for f in DATA_DIR.glob("*.pdf")])
    
    print("="*100)
    print("COMPREHENSIVE ANALYSIS OF ALL BANK STATEMENTS")
    print("="*100)
    print(f"\nTotal PDFs: {len(pdf_files)}\n")
    
    results = []
    bank_stats = defaultdict(lambda: {'count': 0, 'total_txns': 0, 'classified': 0, 'unclassified': 0})
    
    for i, pdf_path in enumerate(pdf_files, 1):
        print(f"\n[{i}/{len(pdf_files)}] {pdf_path.name}")
        print("-" * 100)
        
        result = analyze_pdf(pdf_path)
        result['filename'] = pdf_path.name
        results.append(result)
        
        if result['status'] == 'success':
            bank = result['bank']
            print(f"  Bank:         {bank.upper() if bank != 'unknown' else '[!] UNKNOWN'}")
            print(f"  Parser:       {result['parser'] or '[X] NO PARSER'}")
            print(f"  Pages:        {result['total_pages']}")
            print(f"  Transactions: {result['total_txns']}")
            print(f"  Classified:   {result['classified']} ({result['accuracy']:.1f}%)")
            print(f"  Unclassified: {result['unclassified']}")
            
            if result['accuracy'] < 100:
                print(f"\n  [!] Unclassified Samples:")
                for sample in result['unclassified_samples']:
                    print(f"    [{sample['side']}] {sample['desc']}")
            
            # Update bank stats
            bank_stats[bank]['count'] += 1
            bank_stats[bank]['total_txns'] += result['total_txns']
            bank_stats[bank]['classified'] += result['classified']
            bank_stats[bank]['unclassified'] += result['unclassified']
            
        elif result['status'] == 'no_transactions':
            print(f"  Bank:         {result['bank'].upper() if result['bank'] != 'unknown' else '[!] UNKNOWN'}")
            print(f"  [X] ERROR:    {result['error']}")
        else:
            print(f"  [X] ERROR:    {result['error']}")
    
    # Summary report
    print("\n" + "="*100)
    print("SUMMARY BY BANK")
    print("="*100)
    
    total_files = len(results)
    total_success = len([r for r in results if r['status'] == 'success'])
    total_failed = total_files - total_success
    
    for bank, stats in sorted(bank_stats.items()):
        accuracy = stats['classified'] / stats['total_txns'] * 100 if stats['total_txns'] > 0 else 0
        print(f"\n{bank.upper()}:")
        print(f"  Files:        {stats['count']}")
        print(f"  Transactions: {stats['total_txns']}")
        print(f"  Classified:   {stats['classified']} ({accuracy:.1f}%)")
        print(f"  Unclassified: {stats['unclassified']}")
    
    # Overall stats
    total_txns = sum(s['total_txns'] for s in bank_stats.values())
    total_classified = sum(s['classified'] for s in bank_stats.values())
    total_unclassified = sum(s['unclassified'] for s in bank_stats.values())
    overall_accuracy = total_classified / total_txns * 100 if total_txns > 0 else 0
    
    print("\n" + "="*100)
    print("OVERALL STATISTICS")
    print("="*100)
    print(f"Total PDFs:           {total_files}")
    print(f"Successfully Parsed:  {total_success}")
    print(f"Failed:               {total_failed}")
    print(f"Total Transactions:   {total_txns}")
    print(f"Classified:           {total_classified} ({overall_accuracy:.1f}%)")
    print(f"Unclassified:         {total_unclassified}")
    
    # Identify gaps
    print("\n" + "="*100)
    print("GAPS & ACTION ITEMS")
    print("="*100)
    
    unknown_banks = [r for r in results if r.get('bank') == 'unknown']
    no_parser = [r for r in results if r.get('parser') is None and r.get('bank') != 'unknown']
    low_accuracy = [r for r in results if r.get('accuracy', 0) < 100 and r['status'] == 'success']
    
    if unknown_banks:
        print(f"\n[X] {len(unknown_banks)} PDFs with UNKNOWN bank:")
        for r in unknown_banks:
            print(f"   - {r['filename']}")
    
    if no_parser:
        print(f"\n[X] {len(no_parser)} PDFs without parser:")
        for r in no_parser:
            print(f"   - {r['filename']} (Bank: {r.get('bank', 'N/A')})")
    
    if low_accuracy:
        print(f"\n[!] {len(low_accuracy)} PDFs with <100% accuracy:")
        for r in low_accuracy:
            print(f"   - {r['filename']}: {r['accuracy']:.1f}% ({r['unclassified']} unclassified)")
    
    if not unknown_banks and not no_parser and not low_accuracy:
        print("\n[OK] All PDFs processed with 100% accuracy!")
    else:
        print(f"\n[ACTION REQUIRED]:")
        print(f"   1. Create parsers for {len(unknown_banks) + len(no_parser)} missing banks")
        print(f"   2. Add rules for {total_unclassified} unclassified transactions")
        print(f"   3. Implement adaptive learning to auto-fix these gaps")

if __name__ == "__main__":
    main()
