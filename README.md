# PDF Stamp & Signature Remover (logistic_app)

A modern, high-performance web application designed to automatically clean up scanned PDF documents by removing stamps, handwritten signatures, and specific document lines (like "Bill No:") while preserving the original document layout and all other text.

## Tech Stack
- **Backend:** FastAPI (Python), PyMuPDF (fitz), OpenCV (cv2)
- **Frontend:** Streamlit
- **Automation:** PowerShell runner script

## Key Features
- **Precise Stamp Removal:** Supports presets (Red, Blue, Purple) and custom HSV thresholds. Uses a refined black text protection algorithm to prevent letters overlapping with stamps from being deleted or faded.
- **Smart Signature Removal:** Uses blue color masking to target and remove only the handwritten blue pen strokes, keeping printed black labels (e.g. company names, signee names, and "(Signature)" text) fully intact.
- **Text-based Redactions:** Automatically locates specific text regions (like "Bill No:") and clears them without affecting adjacent lines.
- **Real-time Previews:** Side-by-side view (Original vs Cleaned) with DPI adjustment.

## How to Set Up & Run

### 1. Requirements
Ensure you have Python 3.10+ installed.

### 2. Install Dependencies
Create a virtual environment and install the required packages:
```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```
*(Note: OpenCV and PyMuPDF are required)*

### 3. Run the Application
Start both the FastAPI backend and Streamlit frontend using the PowerShell runner script:
```powershell
powershell -ExecutionPolicy Bypass -File .\run.ps1
```
The application will open automatically in your browser at `http://localhost:8501`.
