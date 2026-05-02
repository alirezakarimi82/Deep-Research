#Requires -Version 5.1
<#
.SYNOPSIS
    DeepResearch Framework -- Windows PowerShell setup script.
.DESCRIPTION
    Creates a virtual environment, installs all dependencies,
    runs an import smoke test, and prints next steps.
.NOTES
    Run from the deep-research directory:
        Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
        .\setup.ps1
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

function Write-OK   { param($msg) Write-Host "  [OK]  $msg" -ForegroundColor Green }
function Write-Warn { param($msg) Write-Host "  [!!]  $msg" -ForegroundColor Yellow }
function Write-Err  { param($msg) Write-Host "  [XX]  $msg" -ForegroundColor Red }

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  DeepResearch Framework - Setup (Win)"   -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# -- Python version check ------------------------------------------------------
$PyCmd = $null
foreach ($candidate in @("python", "python3", "py")) {
    try {
        $ver = & $candidate --version 2>&1
        if ($ver -match "Python (\d+)\.(\d+)") {
            $major = [int]$Matches[1]; $minor = [int]$Matches[2]
            # Accept Python 3.10+ OR any future 4.x
            if (($major -gt 3) -or ($major -eq 3 -and $minor -ge 10)) {
                $PyCmd = $candidate
                break
            }
        }
    } catch {}
}
if (-not $PyCmd) {
    Write-Err "Python 3.10+ not found. Install from https://python.org (check 'Add to PATH')"
    exit 1
}
$PyVersion = (& $PyCmd --version 2>&1) -replace "Python ", ""
Write-OK "Python $PyVersion ($PyCmd)"

# -- Virtual environment -------------------------------------------------------
if (-not (Test-Path ".venv")) {
    Write-Host "  Creating virtual environment ..."
    & $PyCmd -m venv .venv
    Write-OK "Created .venv"
} else {
    Write-OK ".venv already exists -- skipping"
}

# Activate
$ActivateScript = ".\.venv\Scripts\Activate.ps1"
if (-not (Test-Path $ActivateScript)) {
    Write-Err "Activate script not found at $ActivateScript"
    exit 1
}
. $ActivateScript
Write-OK "Virtual environment activated"

# -- Pip upgrade ---------------------------------------------------------------
python -m pip install -q --upgrade pip

# -- Python dependencies -------------------------------------------------------
Write-Host "  Installing Python dependencies ..."
pip install -q -r requirements.txt
Write-OK "Python packages installed"

# -- Reports directory ---------------------------------------------------------
if (-not (Test-Path "reports")) {
    New-Item -ItemType Directory -Path "reports" | Out-Null
}
Write-OK "reports\ directory ready"

# -- Config file ---------------------------------------------------------------
if (-not (Test-Path "config.yaml")) {
    if (Test-Path "config.example.yaml") {
        Copy-Item "config.example.yaml" "config.yaml"
        Write-OK "Created config.yaml from config.example.yaml (placeholder values)"
    } else {
        Write-Warn "config.yaml missing and no template found"
    }
} else {
    Write-OK "config.yaml present"
}

# -- Secret check --------------------------------------------------------------
$HaveAny = $false
foreach ($v in @("SEMANTIC_SCHOLAR_KEY", "OPENALEX_API_KEY", "UNPAYWALL_EMAIL")) {
    if ([Environment]::GetEnvironmentVariable($v)) { $HaveAny = $true; break }
}
if (-not $HaveAny) {
    Write-Warn "No API-key env vars detected (SEMANTIC_SCHOLAR_KEY, OPENALEX_API_KEY, UNPAYWALL_EMAIL)"
    Write-Warn "The pipeline will still run, but rate limits will be lower."
    Write-Warn "See the 'Next steps' section below to configure keys."
}

# -- Smoke test: stdout must be clean on import --------------------------------
# The MCP server speaks stdio; any accidental print() to stdout corrupts the
# JSON-RPC stream. This test catches regressions of that class of bug.
Write-Host "  Running import smoke test ..."
$smokeCode = "import sys; sys.path.insert(0,'.'); import mcp_server"
$smokeOut = python -c $smokeCode 2>$null
if ([string]::IsNullOrEmpty($smokeOut)) {
    Write-OK "Smoke test passed (stdout clean on import)"
} else {
    Write-Err "Smoke test FAILED -- mcp_server wrote to stdout during import:"
    Write-Host $smokeOut
    Write-Err "This WILL corrupt the MCP JSON-RPC protocol. Fix before using."
    exit 1
}

# -- Optional: run unit tests --------------------------------------------------
try {
    python -c "import pytest" 2>$null
    $pytestOk = ($LASTEXITCODE -eq 0)
} catch {
    $pytestOk = $false
}
if ($pytestOk -and (Test-Path "tests")) {
    Write-Host "  Running unit tests ..."
    python -m pytest tests/ -q --no-header
    if ($LASTEXITCODE -eq 0) {
        Write-OK "Tests passed"
    } else {
        Write-Warn "Some tests failed -- the install may still be usable but investigate"
    }
}

# -- Next steps ----------------------------------------------------------------
Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-OK "Setup complete!"
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:"
Write-Host ""
Write-Host "  1. Activate the virtual environment before starting your agent:"
Write-Host '       .\.venv\Scripts\Activate.ps1'
Write-Host ""
Write-Host "  2. (Optional but recommended) set API keys as environment variables."
Write-Host "     This is the preferred path; env vars override config.yaml:"
Write-Host ""
Write-Host '       $env:UNPAYWALL_EMAIL      = "you@example.com"'
Write-Host '       $env:SEMANTIC_SCHOLAR_KEY = "..."'
Write-Host '       $env:OPENALEX_API_KEY     = "..."'
Write-Host ""
Write-Host "     To persist across sessions, use [Environment]::SetEnvironmentVariable"
Write-Host "     or add them to your PowerShell `$PROFILE`."
Write-Host "     IMPORTANT: never commit config.yaml with live keys."
Write-Host ""
Write-Host "  3. Start your agent. MCP servers are launched automatically:"
Write-Host "       opencode                             # reads opencode.json"
Write-Host "       claude                               # reads .mcp.json"
Write-Host ""
Write-Host "  4. Verify the MCP server is reachable from inside your agent:"
Write-Host "       /mcp                                 # Claude Code"
Write-Host "       :mcp                                 # OpenCode"
Write-Host ""
Write-Host "  5. To deactivate the virtual environment:"
Write-Host "       deactivate"
Write-Host ""
