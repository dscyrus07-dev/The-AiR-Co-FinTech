"""
Test the HDFC PDF upload endpoint.
"""
import requests
import sys

def test_upload(pdf_path: str, base_url: str = "http://localhost:8000"):
    """Test the upload endpoint with a PDF file."""
    
    endpoint = f"{base_url}/api/upload/hdfc-pdf"
    
    print(f"Testing endpoint: {endpoint}")
    print(f"PDF file: {pdf_path}")
    
    # Open and upload the file
    with open(pdf_path, 'rb') as f:
        files = {'file': (pdf_path.split('/')[-1], f, 'application/pdf')}
        
        print("\nUploading PDF...")
        response = requests.post(endpoint, files=files)
    
    print(f"\nStatus code: {response.status_code}")
    
    if response.status_code == 200:
        # Save the Excel file
        output_path = pdf_path.replace('.pdf', '_output.xlsx')
        with open(output_path, 'wb') as f:
            f.write(response.content)
        
        print(f"✓ Success! Excel saved to: {output_path}")
        print(f"  File size: {len(response.content)} bytes")
        
        # Check headers
        if 'content-disposition' in response.headers:
            print(f"  Filename: {response.headers['content-disposition']}")
    else:
        print(f"✗ Error: {response.text}")

if __name__ == "__main__":
    pdf_path = sys.argv[1] if len(sys.argv) > 1 else "HDFC DATA/Hdfc Bank 1 June to 24 Jan 26.pdf"
    test_upload(pdf_path)
