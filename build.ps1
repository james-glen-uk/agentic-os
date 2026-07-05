# Build the Agentic OS desktop app into a single versioned installer exe (Windows).
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$version = (Get-Content "VERSION" -Raw).Trim()
$py = if (Get-Command py -ErrorAction SilentlyContinue) { @("py", "-3") } else { @("python") }

Write-Host "Building Agentic OS v$version ..." -ForegroundColor Cyan
Write-Host "Installing build + desktop dependencies..." -ForegroundColor Cyan
& $py[0] $py[1..($py.Count)] -m pip install -r requirements-desktop.txt pyinstaller --quiet --disable-pip-version-check

Write-Host "Running PyInstaller (this can take a few minutes)..." -ForegroundColor Cyan
& $py[0] $py[1..($py.Count)] -m PyInstaller AgenticOS.spec --noconfirm --clean

$exe = "dist/AgenticOS-Setup-v$version.exe"
if (Test-Path $exe) {
    $size = [math]::Round((Get-Item $exe).Length / 1MB, 1)
    Write-Host "`n✓ Built installer: $exe ($size MB)" -ForegroundColor Green
    Write-Host "  Double-click to run. It installs its data to %LOCALAPPDATA%\AgenticOS on first launch."
    Write-Host "  Optional voice add-on (Hey Jarvis): pip install -r requirements-voice.txt"
} else {
    Write-Host "Build did not produce $exe. Check PyInstaller output above." -ForegroundColor Red
    exit 1
}
