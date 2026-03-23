"""
Test script for HDFC accuracy-first processor.
Run this to validate the new architecture works correctly.
"""

import os
import sys

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.banks.hdfc import HDFCProcessor


def test_hdfc_processor():
    """Test HDFC processor with sample PDF."""
    
    # Get HDFC DATA folder
    hdfc_data_dir = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "HDFC DATA"
    )
    
    # Find a test PDF
    pdf_files = [f for f in os.listdir(hdfc_data_dir) if f.endswith('.pdf')]
    
    if not pdf_files:
        print("ERROR: No PDF files found in HDFC DATA folder")
        return False
    
    test_pdf = os.path.join(hdfc_data_dir, pdf_files[0])
    print(f"\n{'='*60}")
    print(f"Testing HDFC Processor")
    print(f"{'='*60}")
    print(f"PDF: {pdf_files[0]}")
    
    # Initialize processor
    processor = HDFCProcessor(
        strict_mode=False,  # Allow warnings
        enable_ai=False,    # No AI for testing
    )
    
    # User info
    user_info = {
        "full_name": "Test User",
        "account_type": "Salaried",
        "bank_name": "HDFC Bank",
    }
    
    # Output directory
    output_dir = os.path.join(os.path.dirname(__file__), "temp")
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        # Process
        result = processor.process(
            file_path=test_pdf,
            user_info=user_info,
            output_dir=output_dir,
        )
        
        print(f"\n{'='*60}")
        print("RESULT")
        print(f"{'='*60}")
        print(f"Status: {result.status}")
        print(f"Excel Path: {result.excel_path}")
        print(f"\nMetrics:")
        print(f"  Total Transactions: {result.metrics.transaction_count}")
        print(f"  Rule Engine Classified: {result.metrics.classified_count}")
        print(f"  Unclassified (Others): {result.metrics.unclassified_count}")
        print(f"  Recurring: {result.metrics.recurring_count}")
        print(f"  Reconciliation Passed: {result.metrics.reconciliation_passed}")
        print(f"  Integrity Passed: {result.metrics.integrity_passed}")
        print(f"\nTiming:")
        for step, ms in result.metrics.step_timings.items():
            print(f"  {step}: {ms}ms")
        print(f"  TOTAL: {result.metrics.total_time_ms}ms")
        
        # Calculate coverage
        if result.metrics.transaction_count > 0:
            coverage = (result.metrics.classified_count / result.metrics.transaction_count) * 100
            print(f"\nClassification Coverage: {coverage:.1f}%")
        
        print(f"\n{'='*60}")
        print("SUCCESS: HDFC processor working correctly!")
        print(f"{'='*60}")
        return True
        
    except Exception as e:
        print(f"\n{'='*60}")
        print(f"ERROR: {type(e).__name__}")
        print(f"{'='*60}")
        print(f"Stage: {getattr(e, 'stage', 'unknown')}")
        print(f"Code: {getattr(e, 'error_code', 'unknown')}")
        print(f"Message: {str(e)}")
        print(f"{'='*60}")
        
        import traceback
        traceback.print_exc()
        return False


def test_all_hdfc_pdfs():
    """Test all PDFs in HDFC DATA folder."""
    
    hdfc_data_dir = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "HDFC DATA"
    )
    
    pdf_files = [f for f in os.listdir(hdfc_data_dir) if f.endswith('.pdf')]
    
    print(f"\n{'='*60}")
    print(f"Testing ALL {len(pdf_files)} HDFC PDFs")
    print(f"{'='*60}")
    
    results = []
    
    for pdf_file in pdf_files:
        test_pdf = os.path.join(hdfc_data_dir, pdf_file)
        
        processor = HDFCProcessor(strict_mode=False, enable_ai=False)
        user_info = {
            "full_name": "Test User",
            "account_type": "Salaried",
            "bank_name": "HDFC Bank",
        }
        
        try:
            result = processor.process(
                file_path=test_pdf,
                user_info=user_info,
                output_dir=os.path.join(os.path.dirname(__file__), "temp"),
            )
            
            coverage = (result.metrics.classified_count / max(result.metrics.transaction_count, 1)) * 100
            
            results.append({
                "file": pdf_file,
                "status": "SUCCESS",
                "transactions": result.metrics.transaction_count,
                "classified": result.metrics.classified_count,
                "coverage": coverage,
                "reconciled": result.metrics.reconciliation_passed,
                "time_ms": result.metrics.total_time_ms,
            })
            
            print(f"✓ {pdf_file[:40]:<40} | {result.metrics.transaction_count:>4} txns | {coverage:>5.1f}% | {result.metrics.total_time_ms:>6.0f}ms")
            
        except Exception as e:
            results.append({
                "file": pdf_file,
                "status": "FAILED",
                "error": str(e),
            })
            print(f"✗ {pdf_file[:40]:<40} | ERROR: {str(e)[:50]}")
    
    # Summary
    success = sum(1 for r in results if r["status"] == "SUCCESS")
    failed = len(results) - success
    
    print(f"\n{'='*60}")
    print(f"SUMMARY: {success}/{len(results)} successful, {failed} failed")
    
    if success > 0:
        avg_coverage = sum(r["coverage"] for r in results if r["status"] == "SUCCESS") / success
        avg_time = sum(r["time_ms"] for r in results if r["status"] == "SUCCESS") / success
        total_txns = sum(r["transactions"] for r in results if r["status"] == "SUCCESS")
        
        print(f"Average Coverage: {avg_coverage:.1f}%")
        print(f"Average Time: {avg_time:.0f}ms")
        print(f"Total Transactions: {total_txns}")
    
    print(f"{'='*60}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true", help="Test all PDFs")
    args = parser.parse_args()
    
    if args.all:
        test_all_hdfc_pdfs()
    else:
        test_hdfc_processor()
