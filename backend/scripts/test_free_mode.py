"""Test the Free Mode pipeline (PDF -> 5-sheet categorized Excel)."""
import requests
import sys
import json

def test_free_mode(pdf_path: str, base_url: str = "http://localhost:8000"):
    endpoint = f"{base_url}/process"
    
    print(f"Testing Free Mode: {endpoint}")
    print(f"PDF: {pdf_path}")
    
    with open(pdf_path, 'rb') as f:
        files = {'file': (pdf_path.split('\\')[-1].split('/')[-1], f, 'application/pdf')}
        data = {
            'full_name': 'Test User',
            'account_type': 'Business',
            'bank_name': 'HDFC Bank',
            'mode': 'free',
        }
        
        print("\nUploading and processing...")
        response = requests.post(endpoint, files=files, data=data)
    
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"\nResult:")
        print(json.dumps(result.get('stats', {}), indent=2))
        print(f"\nExcel URL: {result.get('excel_url', 'N/A')}")
        print(f"Mode: {result.get('mode', 'N/A')}")
        print(f"Status: {result.get('status', 'N/A')}")
        
        # Download the Excel file
        excel_url = result.get('excel_url', '')
        if excel_url:
            dl_url = f"{base_url}{excel_url}"
            print(f"\nDownloading: {dl_url}")
            dl_resp = requests.get(dl_url)
            if dl_resp.status_code == 200:
                out = pdf_path.replace('.pdf', '_report.xlsx')
                with open(out, 'wb') as f:
                    f.write(dl_resp.content)
                print(f"Saved: {out} ({len(dl_resp.content)} bytes)")
            else:
                print(f"Download failed: {dl_resp.status_code}")
    else:
        print(f"Error: {response.text}")

if __name__ == "__main__":
    pdf = sys.argv[1] if len(sys.argv) > 1 else "HDFC DATA/Hdfc Bank 1 June to 24 Jan 26.pdf"
    test_free_mode(pdf)
