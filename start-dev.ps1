# AInovel dev: start backend (FastAPI) + frontend (Vite)
# Run: .\start-dev.ps1  or  double-click start-dev.bat

$root = $PSScriptRoot
if (-not $root) { $root = Get-Location.Path }

Write-Host "Root: $root" -ForegroundColor Cyan
Write-Host "Starting backend (8000) and frontend (Vite)..." -ForegroundColor Green

Start-Process powershell -ArgumentList @(
  "-NoExit",
  "-Command",
  "Set-Location '$root\backend'; Write-Host '=== Backend API (FastAPI) ===' -ForegroundColor Yellow; python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"
)

Start-Sleep -Seconds 1

Start-Process powershell -ArgumentList @(
  "-NoExit",
  "-Command",
  "Set-Location '$root\frontend'; Write-Host '=== Frontend (Vite) ===' -ForegroundColor Yellow; npm run dev"
)

Write-Host ""
Write-Host "Two windows opened:" -ForegroundColor Green
Write-Host "  Backend:  http://127.0.0.1:8000"
Write-Host "  Frontend: see Vite window (usually http://localhost:5173)"
Write-Host "Close each window to stop that service." -ForegroundColor Gray
