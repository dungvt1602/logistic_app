import requests
import os

def test_api():
    pdf_path = "INV_IG_ETD 21.05.PDF"
    
    if not os.path.exists(pdf_path):
        print(f"Error: {pdf_path} not found.")
        return
        
    # 1. Test Preview API
    url_preview = "http://127.0.0.1:8000/preview/"
    print(f"Testing stamp removal preview on {pdf_path}...")
    
    with open(pdf_path, "rb") as f:
        files = {"file": (pdf_path, f, "application/pdf")}
        data = {
            "page_num": 0,
            "preset": "red",
            "dilation": 1,
            "dpi": 150
        }
        
        try:
            response = requests.post(url_preview, files=files, data=data)
            if response.status_code == 200:
                res_data = response.json()
                print("Preview API call successful!")
                print(f"Total pages: {res_data['total_pages']}")
                print(f"Original image base64 length: {len(res_data['original'])}")
                print(f"Cleaned image base64 length: {len(res_data['cleaned'])}")
            else:
                print(f"Preview API call failed: {response.status_code}: {response.text}")
                return
        except Exception as e:
            print(f"Could not connect to Preview API: {e}")
            return

    # 2. Test Full Processing API
    url_process = "http://127.0.0.1:8000/process/"
    print(f"\nTesting full document processing on {pdf_path}...")
    
    with open(pdf_path, "rb") as f:
        files = {"file": (pdf_path, f, "application/pdf")}
        data = {
            "preset": "red",
            "dilation": 1,
            "dpi": 150
        }
        
        try:
            response = requests.post(url_process, files=files, data=data)
            if response.status_code == 200:
                output_pdf = "cleaned_test.pdf"
                with open(output_pdf, "wb") as out_f:
                    out_f.write(response.content)
                print("Full processing API call successful!")
                print(f"Saved cleaned PDF to: {output_pdf}")
                print(f"Original file size: {os.path.getsize(pdf_path)} bytes")
                print(f"Cleaned file size: {os.path.getsize(output_pdf)} bytes")
                print("Full PDF Processing Verification PASSED!")
            else:
                print(f"Process API call failed: {response.status_code}: {response.text}")
        except Exception as e:
            print(f"Could not connect to Process API: {e}")

if __name__ == "__main__":
    test_api()
