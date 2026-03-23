"""
Test AI classification directly on parsed transactions.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.banks.hdfc.parser import HDFCParser
from app.services.banks.hdfc.rule_engine import HDFCRuleEngine
from app.services.banks.hdfc.ai_fallback import HDFCAIFallback

def test_ai_direct(pdf_path: str):
    """Test AI classification directly."""
    
    print("=" * 80)
    print("DIRECT AI CLASSIFICATION TEST")
    print("=" * 80)
    print(f"PDF: {pdf_path}\n")
    
    # Parse the PDF
    parser = HDFCParser()
    parse_result = parser.parse(pdf_path)
    
    print(f"Parsed {parse_result.total_count} transactions")
    
    # Initialize rule engine and AI classifier
    rule_engine = HDFCRuleEngine()
    ai_classifier = HDFCAIFallback(api_key=None)  # No API key for testing
    
    # Process transactions
    processed_transactions = []
    uncategorized = []
    
    # Convert to dict format for rule engine
    txn_dicts = []
    for txn in parse_result.transactions:
        txn_dicts.append({
            'date': txn.date,
            'description': txn.description,
            'debit': txn.debit,
            'credit': txn.credit,
            'balance': txn.balance,
            'ref_no': txn.ref_no,
            'value_date': txn.value_date
        })
    
    # Rule-based classification (batch)
    classified, uncategorized_raw = rule_engine.classify(txn_dicts)
    
    # Convert to our format
    processed_transactions = []
    uncategorized = []
    
    for i, txn in enumerate(classified):
        processed_txn = {
            'date': txn['date'],
            'description': txn['description'],
            'debit': txn['debit'],
            'credit': txn['credit'],
            'balance': txn['balance'],
            'category': txn.get('category'),
            'confidence': txn.get('confidence', 0.95),
            'ai_classified': False,
            'rule_classified': True
        }
        processed_transactions.append(processed_txn)
    
    # Prepare uncategorized for AI
    for i, txn in enumerate(uncategorized_raw):
        uncategorized.append({
            'date': txn['date'],
            'description': txn['description'],
            'debit': txn['debit'],
            'credit': txn['credit'],
            'balance': txn['balance'],
            'index': len(processed_transactions) + i
        })
    
    # Process uncategorized transactions with AI
    if uncategorized:
        print(f"\nProcessing {len(uncategorized)} uncategorized transactions with AI...")
        ai_results, ai_metrics = ai_classifier.classify(uncategorized)
        
        # Update transactions with AI results
        for ai_result in ai_results:
            idx = ai_result.get('index')
            if idx is not None and idx < len(processed_transactions):
                processed_transactions[idx]['category'] = ai_result.get('category', 'Others')
                processed_transactions[idx]['confidence'] = ai_result.get('confidence', 0.5)
                processed_transactions[idx]['ai_classified'] = True
                processed_transactions[idx]['rule_classified'] = False
        
        print(f"AI classified {ai_metrics.classified_count}/{ai_metrics.total_sent} transactions")
        print(f"Estimated cost: ${ai_metrics.estimated_cost_usd:.4f} (₹{ai_metrics.estimated_cost_inr:.2f})")
    
    # Statistics
    total = len(processed_transactions)
    rule_classified = sum(1 for t in processed_transactions if t['rule_classified'])
    ai_classified = sum(1 for t in processed_transactions if t['ai_classified'])
    uncategorized_count = sum(1 for t in processed_transactions if not t['category'])
    
    print(f"\nClassification Results:")
    print(f"  Total transactions: {total}")
    print(f"  Rule-based: {rule_classified} ({rule_classified/total:.1%})")
    print(f"  AI-based: {ai_classified} ({ai_classified/total:.1%})")
    print(f"  Uncategorized: {uncategorized_count} ({uncategorized_count/total:.1%})")
    
    # AI confidence analysis
    if ai_classified > 0:
        ai_txns = [t for t in processed_transactions if t['ai_classified']]
        avg_confidence = sum(t['confidence'] for t in ai_txns) / len(ai_txns)
        
        high_conf = sum(1 for t in ai_txns if t['confidence'] > 0.8)
        med_conf = sum(1 for t in ai_txns if 0.5 <= t['confidence'] <= 0.8)
        low_conf = sum(1 for t in ai_txns if t['confidence'] < 0.5)
        
        print(f"\nAI Confidence Analysis:")
        print(f"  Average confidence: {avg_confidence:.1%}")
        print(f"  High confidence (>80%): {high_conf} ({high_conf/len(ai_txns):.1%})")
        print(f"  Medium confidence (50-80%): {med_conf} ({med_conf/len(ai_txns):.1%})")
        print(f"  Low confidence (<50%): {low_conf} ({low_conf/len(ai_txns):.1%})")
    
    # Show AI classifications
    print("\n" + "=" * 80)
    print("AI CLASSIFICATIONS (First 15)")
    print("=" * 80)
    
    ai_examples = [t for t in processed_transactions if t['ai_classified']][:15]
    for i, txn in enumerate(ai_examples):
        print(f"{i+1:2d}. {txn['date']} | {txn['category']:<20} | {txn['confidence']:.1%} | {txn['description'][:40]}")
    
    # Category distribution
    print("\n" + "=" * 80)
    print("CATEGORY DISTRIBUTION")
    print("=" * 80)
    
    from collections import Counter
    categories = Counter(t['category'] for t in processed_transactions if t['category'])
    
    for category, count in categories.most_common(10):
        print(f"  {category:<20}: {count:3d} transactions")
    
    # Test AI on specific patterns
    print("\n" + "=" * 80)
    print("AI PERFORMANCE ON SPECIFIC PATTERNS")
    print("=" * 80)
    
    test_cases = [
        ("PHONEPE", "Transfers"),
        ("NEFTCR", "Transfers"),
        ("NEFTDR", "Transfers"),
        ("ATM", "ATM Withdrawal"),
        ("SALARY", "Salary"),
        ("EMI", "Loan Payment")
    ]
    
    for pattern, expected in test_cases:
        matching = [t for t in processed_transactions if pattern in t['description'].upper() and t['ai_classified']]
        if matching:
            correct = sum(1 for t in matching if t['category'] == expected)
            print(f"{pattern:<10}: {correct}/{len(matching)} correct ({correct/len(matching):.1%})")
    
    # Overall assessment
    print("\n" + "=" * 80)
    print("AI PERFORMANCE ASSESSMENT")
    print("=" * 80)
    
    if ai_classified == 0:
        print("❌ AI did not classify any transactions")
        print("   - AI classifier may not be working")
        print("   - Check AI service configuration")
    elif ai_classified / total > 0.3:
        print("✅ AI is performing WELL")
        print(f"   - Classified {ai_classified} transactions ({ai_classified/total:.1%})")
        if ai_classified > 0:
            ai_txns = [t for t in processed_transactions if t['ai_classified']]
            avg_conf = sum(t['confidence'] for t in ai_txns) / len(ai_txns)
            print(f"   - Average confidence: {avg_conf:.1%}")
    else:
        print("⚠️  AI performance is MODERATE")
        print(f"   - Classified only {ai_classified} transactions ({ai_classified/total:.1%})")
        print("   - May need improvement in classification rules")
    
    return processed_transactions

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_ai_direct.py <path_to_hdfc_pdf>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    if not os.path.exists(pdf_path):
        print(f"Error: File not found: {pdf_path}")
        sys.exit(1)
    
    test_ai_direct(pdf_path)
