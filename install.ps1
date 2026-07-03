# Agentic OS Installer (Windows)
$ErrorActionPreference = "Stop"

Write-Host "=== Agentic OS Installer ===" -ForegroundColor Cyan
Write-Host ""

Set-Location $PSScriptRoot

# Find Python 3.10+ (prefer the py launcher)
$python = $null
if (Get-Command py -ErrorAction SilentlyContinue) {
    $python = @("py", "-3")
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $python = @("python")
}
if (-not $python) {
    Write-Host "ERROR: Python 3.10+ required. Install from https://www.python.org/downloads/ or 'winget install Python.Python.3.12'" -ForegroundColor Red
    exit 1
}
$verText = & $python[0] $python[1..($python.Count)] -c "import sys; print('%d.%d' % sys.version_info[:2])"
$ver = [version]$verText
if ($ver -lt [version]"3.10") {
    Write-Host "ERROR: Python 3.10+ required, found $verText. Install a newer Python (e.g. 'winget install Python.Python.3.12')" -ForegroundColor Red
    exit 1
}
Write-Host "Python: $verText"

# Install Python deps
Write-Host "Installing Python dependencies..."
& $python[0] $python[1..($python.Count)] -m pip install -r requirements.txt --quiet --disable-pip-version-check

# Check Node.js (for opencode / gemini CLIs)
if (Get-Command node -ErrorAction SilentlyContinue) {
    Write-Host "Node.js: $(node --version)"
} else {
    Write-Host "WARNING: Node.js not found. opencode and Gemini CLI require Node 18+." -ForegroundColor Yellow
    Write-Host "  Install via: winget install OpenJS.NodeJS.LTS"
}

# Check agent CLIs (all optional — dashboard works with any subset)
$agentClis = @(
    @{ Name = "opencode";  Hint = "npm install -g @opencode/cli" },
    @{ Name = "hermes";    Hint = "see https://github.com/NousResearch/hermes-agent" },
    @{ Name = "gemini";    Hint = "npm install -g @google/gemini-cli" },
    @{ Name = "claude";    Hint = "see https://claude.com/claude-code" }
)
foreach ($cli in $agentClis) {
    if (Get-Command $cli.Name -ErrorAction SilentlyContinue) {
        Write-Host "$($cli.Name): found"
    } else {
        Write-Host "WARNING: $($cli.Name) not found. Install via: $($cli.Hint)" -ForegroundColor Yellow
    }
}

# Create required directories
foreach ($dir in @("backups", "audit")) {
    if (-not (Test-Path $dir)) { New-Item -ItemType Directory $dir | Out-Null }
}

Write-Host ""
Write-Host "=== Installation complete! ===" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. Edit data/settings.json with your API keys"
Write-Host "  2. Run ./start.ps1 to launch the dashboard"
Write-Host "  3. Open http://127.0.0.1:8080 in your browser"
