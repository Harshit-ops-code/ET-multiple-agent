# =====================================================================
# LEGACY SCRIPT: This script is legacy and kept for local development.
# We recommend using Docker for running the application.
# =====================================================================

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptDir
$venvPython = [System.IO.Path]::GetFullPath((Join-Path $projectRoot "venv\Scripts\python.exe"))
$pythonExe = "python"
$useVenvPython = $false

if (Test-Path $venvPython) {
    try {
        # Check if venv python runs and is not blocked by permissions
        $testRun = Start-Process $venvPython -ArgumentList "-V" -NoNewWindow -PassThru -Wait -ErrorAction Stop
        if ($testRun.ExitCode -eq 0) {
            $useVenvPython = $true
            $pythonExe = $venvPython
        } else {
            Write-Host "Virtual environment Python is blocked or returned exit code $($testRun.ExitCode). Falling back to system python."
        }
    } catch {
        Write-Host "Virtual environment Python is not runnable (Access is denied or blocked). Falling back to system python."
    }
} else {
    Write-Host "Virtual environment Python not found. Using system python."
}

$backendUrl = "http://127.0.0.1:8000/api/health"
$frontendUrl = "http://127.0.0.1:5500/index.html"
$portsToClear = @(8000, 5500)

foreach ($port in $portsToClear) {
    $listeners = netstat -ano | Select-String ":$port\s+.*LISTENING\s+(\d+)$"
    foreach ($listener in $listeners) {
        $procId = [int]$listener.Matches[0].Groups[1].Value
        try {
            Stop-Process -Id $procId -Force -ErrorAction Stop
            Write-Host "Stopped existing process on port $port (PID $procId)"
        } catch {
            Write-Host "Could not stop PID $procId on port $port"
        }
    }
}

Start-Sleep -Seconds 1

Write-Host "Starting backend on port 8000..."
$backendCmd = ""
if (-not $useVenvPython) {
    $backendCmd = "`$env:PYTHONPATH = '$projectRoot\venv\Lib\site-packages'; python -m uvicorn api_server:app --host 127.0.0.1 --port 8000"
} else {
    $backendCmd = "& '$pythonExe' -m uvicorn api_server:app --host 127.0.0.1 --port 8000"
}

Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "[Console]::InputEncoding = [System.Text.Encoding]::UTF8; [Console]::OutputEncoding = [System.Text.Encoding]::UTF8; chcp 65001 > `$null; Set-Location '$projectRoot'; $backendCmd"
)

Write-Host "Starting frontend on port 5500..."
$frontendCmd = ""
if (-not $useVenvPython) {
    $frontendCmd = "python -m http.server 5500 --directory frontend"
} else {
    $frontendCmd = "& '$pythonExe' -m http.server 5500 --directory frontend"
}

Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "[Console]::InputEncoding = [System.Text.Encoding]::UTF8; [Console]::OutputEncoding = [System.Text.Encoding]::UTF8; chcp 65001 > `$null; Set-Location '$projectRoot'; $frontendCmd"
)

Write-Host ""
Write-Host "Backend health:" $backendUrl
Write-Host "Frontend:" $frontendUrl
Write-Host "If your API keys are set in .env, open the frontend URL in your browser."
