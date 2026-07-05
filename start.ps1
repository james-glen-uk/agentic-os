# Agentic OS Dashboard launcher (Windows)
$ErrorActionPreference = "Stop"

Write-Host "Starting Agentic OS Dashboard..."
Write-Host ""

Set-Location $PSScriptRoot

if (-not (Test-Path "server.py")) {
    Write-Host "ERROR: server.py not found. Are you in the right directory?" -ForegroundColor Red
    exit 1
}

# Find Python (prefer the py launcher)
$python = $null
if (Get-Command py -ErrorAction SilentlyContinue) {
    $python = @("py", "-3")
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $python = @("python")
}
if (-not $python) {
    Write-Host "ERROR: Python not found. Run ./install.ps1 first." -ForegroundColor Red
    exit 1
}

# Ensure dependencies (no stderr redirect: PS 5.1 turns redirected native
# stderr into terminating NativeCommandError under ErrorActionPreference=Stop)
& $python[0] $python[1..($python.Count)] -m pip install -r requirements.txt --quiet --disable-pip-version-check

# Get port from settings or default
$port = 8080
if (Test-Path "data/settings.json") {
    try {
        $settings = Get-Content "data/settings.json" -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($settings.dashboard.port) { $port = $settings.dashboard.port }
    } catch {}
}

Write-Host "Dashboard: http://127.0.0.1:$port"
Write-Host "Press Ctrl+C to stop"
Write-Host ""

# UTF-8 everywhere (belt and suspenders; file I/O is already explicit UTF-8)
$env:PYTHONUTF8 = "1"

& $python[0] $python[1..($python.Count)] server.py --port $port
