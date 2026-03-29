$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonExe = [System.IO.Path]::GetFullPath((Join-Path $projectRoot ".venv\Scripts\python.exe"))
$backendUrl = "http://127.0.0.1:8000/api/health"
$frontendUrl = "http://127.0.0.1:5500/index.html"

if (-not (Test-Path $pythonExe)) {
    Write-Error "Python virtual environment not found at $pythonExe"
}

Write-Host "Starting backend on port 8000..."
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "[Console]::InputEncoding = [System.Text.Encoding]::UTF8; [Console]::OutputEncoding = [System.Text.Encoding]::UTF8; chcp 65001 > `$null; Set-Location '$projectRoot'; & '$pythonExe' -m uvicorn api_server:app --host 127.0.0.1 --port 8000"
)

Write-Host "Starting frontend on port 5500..."
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "[Console]::InputEncoding = [System.Text.Encoding]::UTF8; [Console]::OutputEncoding = [System.Text.Encoding]::UTF8; chcp 65001 > `$null; Set-Location '$projectRoot'; & '$pythonExe' -m http.server 5500"
)

Write-Host ""
Write-Host "Backend health:" $backendUrl
Write-Host "Frontend:" $frontendUrl
Write-Host "If your API keys are set in .env, open the frontend URL in your browser."
