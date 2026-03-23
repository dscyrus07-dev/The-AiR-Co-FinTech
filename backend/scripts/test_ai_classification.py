"""
Test AI classification accuracy on HDFC transactions.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.banks.hdfc.parser import HDFCParser
from app.services.banks.hdfc.processor import HDFCProcessor

def test_ai_classification(pdf_path: str):
    """Test AI classification accuracy."""
    
    print("=" * 80)
    print("AI CLASSIFICATION TEST")
    print("=" * 80)
    print(f"PDF: {pdf_path}\n")
    
    # Parse the PDF
    parser = HDFCParser()
    parse_result = parser.parse(pdf_path)
    
    print(f"Parsed {parse_result.total_count} transactions")
    
    # Process with AI classification
    processor = HDFCProcessor()
    
    # Convert to transaction format
    transactions = []
    for txn in parse_result.transactions:
        transactions.append({
            'date': txn.date,
            'description': txn.description,
            'debit': txn.debit,
            'credit': txn.credit,
            'balance': txn.balance,
            'ref_no': txn.ref_no,
            'value_date': txn.value_date
        })
    
    # Process transactions
    result = processor.process(transactions, {})
    
    print(f"\nProcessing completed:")
    print(f"  Total transactions: {result['summary']['total_transactions']}")
    print(f"  Categorized: {result['summary']['categorized_count']}")
    print(f"  Uncategorized: {result['summary']['uncategorized_count']}")
    print(f"  AI classified: {result['summary']['ai_classified_count']}")
    
    # Show AI classifications
    print("\n" + "=" * 80)
    print("AI CLASSIFICATIONS (First 20)")
    print("=" * 80)
    
    ai_count = 0
    for i, txn in enumerate(result['transactions'][:20]):
        if txn.get('ai_classified'):
            ai_count += 1
            print(f"{i+1:2d}. {txn['date']} | {txn['category']:<20} | {txn['confidence']:.1%} | {txn['description'][:40]}")
    
    print(f"\nAI classifications in first 20: {ai_count}/20")
    
    # Check confidence levels
    print("\n" + "=" * 80)
    print("CONFIDENCE ANALYSIS")
    print("=" * 80)
    
    high_conf = sum(1 for t in result['transactions'] if t.get('confidence', 0) > 0.8)
    med_conf = sum(1 for t in result['transactions'] if 0.5 <= t.get('confidence', 0) <= 0.8)
    low_conf = sum(1 for t in result['transactions'] if t.get('confidence', 0) < 0.5)
    
    print(f"High confidence (>80%): {high_conf}")
    print(f"Medium confidence (50-80%): {med_conf}")
    print(f"Low confidence (<50%): {low_conf}")
    
    # Category distribution
    print("\n" + "=" * 80)
    print("CATEGORY DISTRIBUTION")
    print("=" * 80)
    
    from collections import Counter
    categories = Counter(t['category'] for t in result['transactions'] if t['category'])
    
    for category, count in categories.most_common(10):
        print(f"  {category:<20}: {count:3d} transactions")
    
    # Test accuracy on known patterns
    print("\n" + "=" * 80)
    print("ACCURACY TEST ON KNOWN PATTERNS")
    print("=" * 80)
    
    test_patterns = {
        'PHONEPE': 'Transfers',
        'NEFTCR': 'Transfers',
        'NEFTDR': 'Transfers',
        'ATM': 'ATM Withdrawal',
        'SALARY': 'Salary',
        'EMI': 'Loan Payment',
        'CHQPAID': 'Cheque'
    }
    
    pattern_results = {}
    
    for pattern, expected_category in test_patterns.items():
        matching_txns = [t for t in result['transactions'] if pattern in t['description'].upper()]
        if matching_txns:
            correct = sum(1 for t in matching_txns if t['category'] == expected_category)
            accuracy = correct / len(matching_txns) if matching_txns else 0
            pattern_results[pattern] = {
                'count': len(matching_txns),
                'correct': correct,
                'accuracy': accuracy
            }
            print(f"{pattern:<10}: {correct}/{len(matching_txns)} correct ({accuracy:.1%})")
    
    # Overall assessment
    print("\n" + "=" * 80)
    print("AI PERFORMANCE ASSESSMENT")
    print("=" * 80)
    
    ai_classified = result['summary']['ai_classified_count']
    total = result['summary']['total_transactions']
    ai_rate = ai_classified / total if total else 0
    
    avg_confidence = sum(t.get('confidence', 0) for t in result['transactions']) / total if total else 0
    
    print(f"AI classification rate: {ai_rate:.1%} ({ai_classified}/{total})")
    print(f"Average confidence: {avg_confidence:.1%}")
    
    # Determine if AI is working well
    if ai_rate > 0.7 and avg_confidence > 0.6:
        print("\n✅ AI is performing WELL")
        print("   - High classification rate")
        print("   - Good confidence levels")
    elif ai_rate > 0.5 and avg_confidence > 0.5:
        print("\n⚠️  AI is performing MODERATELY")
        print("   - Decent classification rate")
        print("   - Moderate confidence levels")
    else:
        print("\n❌ AI needs IMPROVEMENT")
        print("   - Low classification rate")
        print("   - Poor confidence levels")
    
    return result

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_ai_classification.py <path_to_hdfc_pdf>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    if not os.path.exists(pdf_path):
        print(f"Error: File not found: {pdf_path}")
        sys.exit(1)
    
    test_ai_classification(pdf_path)
