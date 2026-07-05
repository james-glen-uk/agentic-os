# Build the Agentic OS desktop app into dist/AgenticOS/ (Windows).
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$py = if (Get-Command py -ErrorAction SilentlyContinue) { @("py", "-3") } else { @("python") }

Write-Host "Installing build + desktop dependencies..." -ForegroundColor Cyan
& $py[0] $py[1..($py.Count)] -m pip install -r requirements-desktop.txt pyinstaller --quiet --disable-pip-version-check

Write-Host "Building AgenticOS.exe (this can take a few minutes)..." -ForegroundColor Cyan
& $py[0] $py[1..($py.Count)] -m PyInstaller AgenticOS.spec --noconfirm --clean

if (Test-Path "dist/AgenticOS/AgenticOS.exe") {
    Write-Host "`n✓ Built: dist/AgenticOS/AgenticOS.exe" -ForegroundColor Green
    Write-Host "  Run it, or zip dist/AgenticOS for distribution."
    Write-Host "  Voice (Hey Jarvis) is an optional add-on: pip install -r requirements-voice.txt"
} else {
    Write-Host "Build did not produce the expected exe. Check PyInstaller output above." -ForegroundColor Red
    exit 1
}
