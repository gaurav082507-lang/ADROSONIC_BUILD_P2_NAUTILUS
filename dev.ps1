$ErrorActionPreference = "Stop"
Write-Host "Starting Lucen AI dev servers..." -ForegroundColor Cyan

# Backend
Start-Process powershell -ArgumentList "-NoExit", "-Command", `
    "Set-Location '$PSScriptRoot\backend'; " + `
    ".\.venv\Scripts\Activate.ps1; " + `
    "uvicorn app.main:app --reload --port 8000"

# Frontend
Start-Process powershell -ArgumentList "-NoExit", "-Command", `
    "Set-Location '$PSScriptRoot\frontend'; " + `
    "npm run dev"

Write-Host "Backend: http://localhost:8000/docs" -ForegroundColor Green
Write-Host "Frontend: http://localhost:5173" -ForegroundColor Green
