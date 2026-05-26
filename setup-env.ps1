# TestForge Environment Setup
# Run this ONCE before your first testforge run to ensure all dependencies are ready.
# Usage: .\setup-env.ps1

param(
    [string]$VenvPath = ".venv"
)

$ErrorActionPreference = "Stop"
$script:failed = @()

function Write-Step($msg) { Write-Host "`n>> $msg" -ForegroundColor Cyan }
function Write-Ok($msg) { Write-Host "   OK: $msg" -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "   WARN: $msg" -ForegroundColor Yellow }
function Write-Fail($msg) { 
    Write-Host "   FAIL: $msg" -ForegroundColor Red 
    $script:failed += $msg
}

Write-Host "============================================================" -ForegroundColor Magenta
Write-Host "  TestForge — Environment Setup" -ForegroundColor Magenta
Write-Host "============================================================" -ForegroundColor Magenta

# ─── 1. Python ───────────────────────────────────────────────────────────────
Write-Step "Checking Python..."
$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) { $py = Get-Command py -ErrorAction SilentlyContinue }
if (-not $py) {
    Write-Fail "Python not found. Install Python 3.11+ from https://python.org"
} else {
    $pyVersion = & $py.Source --version 2>&1
    Write-Ok "$pyVersion"
}

# ─── 2. Node.js / npm / npx ─────────────────────────────────────────────────
Write-Step "Checking Node.js..."
$node = Get-Command node -ErrorAction SilentlyContinue
if (-not $node) {
    Write-Fail "Node.js not found. Install from https://nodejs.org (LTS recommended)"
} else {
    $nodeVersion = & node --version
    Write-Ok "Node $nodeVersion"
}

$npx = Get-Command npx -ErrorAction SilentlyContinue
if (-not $npx) {
    Write-Fail "npx not found. Comes with Node.js — reinstall Node"
} else {
    Write-Ok "npx available"
}

# ─── 3. Virtual environment ─────────────────────────────────────────────────
Write-Step "Setting up Python virtual environment..."
if (-not (Test-Path $VenvPath)) {
    Write-Host "   Creating venv at $VenvPath..."
    & python -m venv $VenvPath
    Write-Ok "Created $VenvPath"
} else {
    Write-Ok "Venv exists at $VenvPath"
}

# Activate
$activateScript = Join-Path $VenvPath "Scripts\Activate.ps1"
if (Test-Path $activateScript) {
    . $activateScript
    Write-Ok "Venv activated"
} else {
    Write-Fail "Could not find venv activate script at $activateScript"
}

# ─── 4. Python dependencies ─────────────────────────────────────────────────
Write-Step "Installing Python dependencies..."
& pip install --upgrade pip --quiet 2>$null
& pip install -e ".[dev]" --quiet 2>$null
if ($LASTEXITCODE -ne 0) {
    # Fallback without [dev] extras
    & pip install -e . --quiet
}
Write-Ok "testforge package installed"

# Install mcp package explicitly (crewai auto-install is broken)
Write-Step "Installing MCP package..."
& pip install mcp --quiet 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Ok "mcp package installed"
} else {
    Write-Warn "mcp install failed — Playwright MCP tools won't be available"
}

# Install python-dotenv for .env loading
& pip install python-dotenv --quiet 2>$null

# ─── 5. Playwright browsers ─────────────────────────────────────────────────
Write-Step "Installing Playwright browsers..."
& npx playwright install chromium 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Ok "Playwright Chromium installed"
} else {
    Write-Warn "Playwright browser install failed — tests won't run"
}

# ─── 6. .env file ───────────────────────────────────────────────────────────
Write-Step "Checking .env file..."
if (Test-Path ".env") {
    $envContent = Get-Content ".env" -Raw
    if ($envContent -match "GITHUB_TOKEN=.+") {
        Write-Ok ".env exists with GITHUB_TOKEN"
    } else {
        Write-Warn ".env exists but GITHUB_TOKEN not set — add it before running"
    }
} else {
    Write-Warn ".env not found — creating template..."
    @"
# TestForge Environment Variables
GITHUB_TOKEN=your_github_token_here
# GITHUB_MODELS_ENDPOINT=https://models.github.ai/inference
"@ | Set-Content ".env"
    Write-Warn "Created .env template — edit it and add your GITHUB_TOKEN"
}

# ─── 7. credentials.json ────────────────────────────────────────────────────
Write-Step "Checking credentials.json..."
if (Test-Path "credentials.json") {
    try {
        $creds = Get-Content "credentials.json" | ConvertFrom-Json
        $roleCount = $creds.roles.Count
        Write-Ok "credentials.json valid ($roleCount roles)"
    } catch {
        Write-Fail "credentials.json is invalid JSON"
    }
} else {
    Write-Warn "credentials.json not found — copy from credentials.example.json"
}

# ─── 8. Verify key packages import ──────────────────────────────────────────
Write-Step "Verifying Python imports..."
$importCheck = & python -c "import crewai; import mcp; import click; import yaml; print('OK')" 2>&1
if ($importCheck -match "OK") {
    Write-Ok "All core packages import successfully"
} else {
    Write-Fail "Import check failed: $importCheck"
}

# ─── 9. Test output directory ────────────────────────────────────────────────
Write-Step "Preparing test-output directory..."
if (-not (Test-Path "test-output")) {
    New-Item -ItemType Directory -Path "test-output" | Out-Null
}
Write-Ok "test-output/ ready"

# ─── Summary ─────────────────────────────────────────────────────────────────
Write-Host "`n============================================================" -ForegroundColor Magenta
if ($script:failed.Count -eq 0) {
    Write-Host "  ALL CHECKS PASSED — Ready to run TestForge!" -ForegroundColor Green
    Write-Host "============================================================" -ForegroundColor Magenta
    Write-Host "`n  Run:" -ForegroundColor White
    Write-Host "    python -m testforge --repo <PATH> --url <URL> --creds credentials.json --demo" -ForegroundColor Yellow
} else {
    Write-Host "  $($script:failed.Count) ISSUE(S) FOUND:" -ForegroundColor Red
    Write-Host "============================================================" -ForegroundColor Magenta
    foreach ($f in $script:failed) {
        Write-Host "  - $f" -ForegroundColor Red
    }
    Write-Host "`n  Fix the above issues before running TestForge."
}
Write-Host ""
