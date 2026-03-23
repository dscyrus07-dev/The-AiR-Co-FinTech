"""Quick verification of report generation with updated sheets."""
import sys, os
sys.path.insert(0, r'X:\FinTech SAAS\FinTech SAAS\backend')

from app.services.banks.hdfc import HDFCProcessor

processor = HDFCProcessor(strict_mode=False, enable_ai=False)
user_info = {'full_name': 'VIJAY SIR', 'account_type': 'Salaried', 'bank_name': 'HDFC Bank'}

try:
    result = processor.process(
        file_path=r'X:\FinTech SAAS\FinTech SAAS\data\Hdfc Bank 1 June to 24 Jan 26.pdf',
        user_info=user_info,
        output_dir=r'X:\FinTech SAAS\FinTech SAAS\Updates',
    )
    print(f'Status: {result.status}')
    print(f'Excel: {result.excel_path}')
    print(f'Transactions: {result.metrics.transaction_count}')
    print(f'Time: {result.metrics.total_time_ms}ms')
    print('SUCCESS - Report generated!')
except Exception as e:
    import traceback
    traceback.print_exc()
    print(f'ERROR: {e}')
