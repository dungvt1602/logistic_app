# Set Python Path
$env:PYTHONPATH = "."

# Check if .venv exists
if (-not (Test-Path ".venv")) {
    Write-Error "Virtual environment '.venv' not found. Please run 'python -m venv .venv' first."
    exit 1
}

# Run FastAPI backend in the background (within the same terminal window, or in a new window)
Write-Host "--------------------------------------------------" -ForegroundColor Cyan
Write-Host "🚀 Khởi động FastAPI Backend (Port 8000)..." -ForegroundColor Green
Write-Host "--------------------------------------------------" -ForegroundColor Cyan

# We start it in a separate window so the user can easily see its logs and close it when done
Start-Process -FilePath ".venv\Scripts\python.exe" -ArgumentList "-m uvicorn backend.main:app --host 127.0.0.1 --port 8000" -WindowStyle Normal

# Wait 2 seconds for backend to start up
Start-Sleep -Seconds 2

# Run Streamlit frontend in the foreground
Write-Host "--------------------------------------------------" -ForegroundColor Cyan
Write-Host "🚀 Khởi động Streamlit Frontend (Port 8501)..." -ForegroundColor Green
Write-Host "--------------------------------------------------" -ForegroundColor Cyan
.venv\Scripts\streamlit run frontend/app.py
