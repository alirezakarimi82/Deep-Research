#Requires -Version 5.1
<#
.SYNOPSIS
    DeepResearch Framework -- Windows PowerShell setup script.
.DESCRIPTION
    Creates a virtual environment, installs dependencies, runs smoke tests,
    and installs the skill files into the correct directory for your chosen
    agent platform(s).
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
function Write-Head { param($msg) Write-Host $msg -ForegroundColor Cyan }
function Write-Sep  { Write-Host "-------------------------------------------" }

Write-Host ""
Write-Head "=========================================="
Write-Head "  DeepResearch Framework - Setup (Win)"
Write-Head "=========================================="
Write-Host ""

# ==============================================================================
# PART 1 -- Python environment and dependencies
# ==============================================================================

# -- Python version check ------------------------------------------------------
$PyCmd = $null
foreach ($candidate in @("python", "python3", "py")) {
    try {
        $ver = & $candidate --version 2>&1
        if ($ver -match "Python (\d+)\.(\d+)") {
            $major = [int]$Matches[1]; $minor = [int]$Matches[2]
            if (($major -gt 3) -or ($major -eq 3 -and $minor -ge 10)) {
                $PyCmd = $candidate; break
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

$ActivateScript = ".\.venv\Scripts\Activate.ps1"
if (-not (Test-Path $ActivateScript)) {
    Write-Err "Activate script not found at $ActivateScript"
    exit 1
}
. $ActivateScript
Write-OK "Virtual environment activated"

python -m pip install -q --upgrade pip

# -- Python dependencies -------------------------------------------------------
Write-Host "  Installing Python dependencies ..."
pip install -q -r requirements.txt
Write-OK "Python packages installed"

# -- reports directory ---------------------------------------------------------
if (-not (Test-Path "reports")) { New-Item -ItemType Directory -Path "reports" | Out-Null }
Write-OK "reports\ directory ready"

# -- .env file -----------------------------------------------------------------
if (-not (Test-Path ".env") -and (Test-Path ".env.example")) {
    Copy-Item ".env.example" ".env"
    Write-OK "Created .env from .env.example -- fill in your API keys"
} elseif (Test-Path ".env") {
    Write-OK ".env present"
} else {
    Write-Warn "No .env.example found -- create .env manually with your API keys"
}

# -- config.yaml ---------------------------------------------------------------
if (-not (Test-Path "config.yaml")) {
    if (Test-Path "config.example.yaml") {
        Copy-Item "config.example.yaml" "config.yaml"
        Write-OK "Created config.yaml from config.example.yaml"
    } else {
        Write-Warn "config.yaml missing and no template found"
    }
} else {
    Write-OK "config.yaml present"
}

# -- API key check -------------------------------------------------------------
$haveKeys = $false
foreach ($v in @("SEMANTIC_SCHOLAR_KEY", "OPENALEX_API_KEY", "UNPAYWALL_EMAIL")) {
    if ([Environment]::GetEnvironmentVariable($v)) { $haveKeys = $true; break }
}
if (-not $haveKeys -and (Test-Path ".env")) {
    $envContent = Get-Content ".env" -Raw
    if ($envContent -match '(?m)^(SEMANTIC_SCHOLAR_KEY|OPENALEX_API_KEY|UNPAYWALL_EMAIL)=.+') {
        $haveKeys = $true
    }
}
if (-not $haveKeys) {
    Write-Warn "No API keys found in env vars or .env -- pipeline works without them"
    Write-Warn "but rate limits will be lower. Edit .env to add keys."
}

# -- Smoke test ----------------------------------------------------------------
Write-Host "  Running import smoke test ..."
$smokeCode = "import sys; sys.path.insert(0,'.'); import mcp_server"
$smokeOut  = python -c $smokeCode 2>$null
if ([string]::IsNullOrEmpty($smokeOut)) {
    Write-OK "Smoke test passed (stdout clean on import)"
} else {
    Write-Err "Smoke test FAILED -- mcp_server wrote to stdout during import:"
    Write-Host $smokeOut
    Write-Err "This WILL corrupt the MCP JSON-RPC protocol. Fix before using."
    exit 1
}

# -- Optional unit tests -------------------------------------------------------
try { python -c "import pytest" 2>$null; $pytestOk = ($LASTEXITCODE -eq 0) }
catch { $pytestOk = $false }
if ($pytestOk -and (Test-Path "tests")) {
    Write-Host "  Running unit tests ..."
    python -m pytest tests/ -q --no-header
    if ($LASTEXITCODE -eq 0) { Write-OK "Tests passed" }
    else { Write-Warn "Some tests failed -- investigate before use" }
}

# ==============================================================================
# PART 2 -- Platform selection and skill installation
# ==============================================================================

Write-Host ""
Write-Head "=========================================="
Write-Head "   Platform setup"
Write-Head "=========================================="
Write-Host ""
Write-Host "Which agent platform(s) do you want to configure?"
Write-Host ""
Write-Host "  1) Claude Code"
Write-Host "  2) Codex CLI"
Write-Host "  3) OpenCode"
Write-Host "  4) Copilot CLI"
Write-Host "  5) Copilot VS Code"
Write-Host "  6) All platforms"
Write-Host "  7) Skip (manual setup later)"
Write-Host ""
$platformInput = Read-Host "Enter numbers separated by spaces (e.g. 1 2)"

# Parse selections — "6" means all
$doClaudeCode    = $platformInput -match "\b(1|6)\b"
$doCodex         = $platformInput -match "\b(2|6)\b"
$doOpenCode      = $platformInput -match "\b(3|6)\b"
$doCopilotCLI    = $platformInput -match "\b(4|6)\b"
$doCopilotVSCode = $platformInput -match "\b(5|6)\b"

$skillName    = "deep-research"
$installedAny = $false

# -- Standard skill installer (overlay + core only) ----------------------------
function Install-Skill {
    param([string]$DestDir, [string]$OverlayFile)
    New-Item -ItemType Directory -Path $DestDir -Force | Out-Null
    Copy-Item (Join-Path $ScriptDir $OverlayFile) (Join-Path $DestDir "SKILL.md")   -Force
    Copy-Item (Join-Path $ScriptDir "SKILL-core.md") (Join-Path $DestDir "SKILL-core.md") -Force
    Write-OK "Skill installed -> $DestDir\"
}

# -- Claude Code ---------------------------------------------------------------
if ($doClaudeCode) {
    Write-Host ""
    Write-Head "--- Claude Code ---"
    Write-Host "Install scope:"
    Write-Host "  1) Personal -- $env:USERPROFILE\.claude\skills\   (all projects, recommended)"
    Write-Host "  2) Project  -- .claude\skills\                     (this repo only)"
    $ccScope = Read-Host "Choice [1]"
    if ([string]::IsNullOrEmpty($ccScope)) { $ccScope = "1" }

    $dest = if ($ccScope -eq "2") { ".claude\skills\$skillName" }
            else { Join-Path $env:USERPROFILE ".claude\skills\$skillName" }
    Install-Skill $dest "SKILL-claude-code.md"

    if (-not (Test-Path ".mcp.json")) {
        $escapedDir = $ScriptDir.Replace('\', '\\')
        $mcpJson = @"
{
  "mcpServers": {
    "deep-research": {
      "command": "python",
      "args": ["mcp_server.py"],
      "cwd": "$escapedDir"
    },
    "alphaxiv": {
      "type": "sse",
      "url": "https://api.alphaxiv.org/mcp/v1"
    },
    "ddgs": {
      "command": "ddgs",
      "args": ["mcp"]
    },
    "playwright": {
      "command": "npx",
      "args": ["@playwright/mcp@latest", "--headless"]
    }
  }
}
"@
        $mcpJson | Set-Content ".mcp.json" -Encoding UTF8
        Write-OK "Created .mcp.json for Claude Code"
    } else {
        Write-OK ".mcp.json already exists -- skipping"
    }
    $installedAny = $true
}

# -- Codex CLI -----------------------------------------------------------------
if ($doCodex) {
    Write-Host ""
    Write-Head "--- Codex CLI ---"
    Write-Host "Install scope:"
    Write-Host "  1) Personal -- $env:USERPROFILE\.codex\skills\   (all projects, recommended)"
    Write-Host "  2) Project  -- .codex\skills\                     (this repo, trusted project required)"
    $codexScope = Read-Host "Choice [1]"
    if ([string]::IsNullOrEmpty($codexScope)) { $codexScope = "1" }

    $dest = if ($codexScope -eq "2") { ".codex\skills\$skillName" }
            else { Join-Path $env:USERPROFILE ".codex\skills\$skillName" }

    # Verify source files exist before copying
    $skillSrc  = Join-Path $ScriptDir "SKILL-codex.md"
    $coreSrc   = Join-Path $ScriptDir "SKILL-core.md"
    $yamlSrc   = Join-Path $ScriptDir "openai.yaml"
    $tomlSrc   = Join-Path $ScriptDir "codex-config.toml"

    if (-not (Test-Path $skillSrc)) {
        Write-Err "SKILL-codex.md not found in $ScriptDir -- cannot install Codex skill"
    } elseif (-not (Test-Path $yamlSrc)) {
        Write-Err "openai.yaml not found in $ScriptDir -- cannot install Codex skill"
    } else {
        # Install skill files
        New-Item -ItemType Directory -Path $dest -Force | Out-Null
        Copy-Item $skillSrc  (Join-Path $dest "SKILL.md")          -Force
        Copy-Item $coreSrc   (Join-Path $dest "SKILL-core.md")     -Force
        Copy-Item $yamlSrc   (Join-Path $dest "openai.yaml")       -Force
        Write-OK "Skill installed -> $dest\"

        # MCP config (TOML)
        if (-not (Test-Path $tomlSrc)) {
            Write-Warn "codex-config.toml not found in repo -- skipping MCP config copy"
            Write-Warn "Run: codex mcp add deep-research -- python $ScriptDir\mcp_server.py"
        } elseif ($codexScope -eq "2") {
            # Project-scoped: copy codex-config.toml → .codex/config.toml
            New-Item -ItemType Directory -Path ".codex" -Force | Out-Null
            $projectToml = ".codex\config.toml"
            if (-not (Test-Path $projectToml)) {
                Copy-Item $tomlSrc $projectToml -Force
                Write-OK "Copied codex-config.toml -> .codex\config.toml (project-scoped, trusted project required)"
            } else {
                Write-OK ".codex\config.toml already exists -- skipping"
            }
        } else {
            $globalToml = Join-Path $env:USERPROFILE ".codex\config.toml"
            if (-not (Test-Path $globalToml)) {
                New-Item -ItemType Directory -Path (Split-Path $globalToml) -Force | Out-Null
                $tomlContent = Get-Content $tomlSrc -Raw
                # Replace ${workspaceFolder} with the absolute project path.
                # Escape backslashes for TOML string literals.
                $escapedDir  = $ScriptDir.Replace('\', '\\')
                $tomlContent = $tomlContent -replace '\$\{workspaceFolder\}', $escapedDir
                $tomlContent | Set-Content $globalToml -Encoding UTF8
                Write-OK "Copied config.toml -> $globalToml (path patched)"
            } else {
                Write-Warn "$globalToml already exists -- skipping"
                Write-Warn "Run: codex mcp add deep-research -- python $ScriptDir\mcp_server.py"
            }
        }
    }
    $installedAny = $true
}

# -- OpenCode ------------------------------------------------------------------
if ($doOpenCode) {
    Write-Host ""
    Write-Head "--- OpenCode ---"
    Write-Host "Install scope:"
    Write-Host "  1) Project -- .opencode\skills\             (this repo, recommended)"
    Write-Host "  2) Global  -- $env:USERPROFILE\.config\opencode\skills\"
    $ocScope = Read-Host "Choice [1]"
    if ([string]::IsNullOrEmpty($ocScope)) { $ocScope = "1" }

    $dest = if ($ocScope -eq "2") { Join-Path $env:USERPROFILE ".config\opencode\skills\$skillName" }
            else { ".opencode\skills\$skillName" }
    Install-Skill $dest "SKILL-opencode.md"

    if (Test-Path "opencode.json") { Write-OK "opencode.json present -- MCP config ready" }
    else { Write-Warn "opencode.json not found -- copy the template from the repo root" }
    $installedAny = $true
}

# -- Copilot CLI ---------------------------------------------------------------
if ($doCopilotCLI) {
    Write-Host ""
    Write-Head "--- Copilot CLI ---"
    Write-Host "Install scope:"
    Write-Host "  1) Personal -- $env:USERPROFILE\.copilot\skills\   (all projects, recommended)"
    Write-Host "  2) Project  -- .github\skills\                      (this repo only)"
    $ccliScope = Read-Host "Choice [1]"
    if ([string]::IsNullOrEmpty($ccliScope)) { $ccliScope = "1" }

    $dest = if ($ccliScope -eq "2") { ".github\skills\$skillName" }
            else { Join-Path $env:USERPROFILE ".copilot\skills\$skillName" }
    Install-Skill $dest "SKILL-copilot.md"

    if ($ccliScope -eq "2") {
        Write-OK ".copilot\mcp-config.json in repo used for project-scoped MCP"
    } else {
        $globalMcp = Join-Path $env:USERPROFILE ".copilot\mcp-config.json"
        if (-not (Test-Path $globalMcp)) {
            $mcpContent = Get-Content (Join-Path $ScriptDir ".copilot\mcp-config.json") -Raw
            $escapedDir  = $ScriptDir.Replace('\', '\\')
            $mcpContent  = $mcpContent -replace '"\$\{workspaceFolder\}"', "`"$escapedDir`""
            New-Item -ItemType Directory -Path (Split-Path $globalMcp) -Force | Out-Null
            $mcpContent | Set-Content $globalMcp -Encoding UTF8
            Write-OK "Copied MCP config -> $globalMcp (path patched)"
        } else {
            Write-Warn "$globalMcp already exists -- skipping"
        }
    }
    $installedAny = $true
}

# -- Copilot VS Code -----------------------------------------------------------
if ($doCopilotVSCode) {
    Write-Host ""
    Write-Head "--- Copilot VS Code ---"
    Write-Host "Install scope:"
    Write-Host "  1) Workspace -- .github\skills\              (this repo, recommended)"
    Write-Host "  2) Global    -- $env:USERPROFILE\.config\copilot\skills\"
    $cvscScope = Read-Host "Choice [1]"
    if ([string]::IsNullOrEmpty($cvscScope)) { $cvscScope = "1" }

    $dest = if ($cvscScope -eq "2") { Join-Path $env:USERPROFILE ".config\copilot\skills\$skillName" }
            else { ".github\skills\$skillName" }
    Install-Skill $dest "SKILL-copilot.md"

    if (Test-Path ".vscode\mcp.json") { Write-OK ".vscode\mcp.json present -- MCP config ready" }
    else { Write-Warn ".vscode\mcp.json not found -- copy the template from the repo" }
    $installedAny = $true
}

if (-not $installedAny) {
    Write-Warn "No platforms configured -- skill files were not installed"
    Write-Warn "Re-run setup.ps1 to install skills, or copy them manually (see README)"
}

# ==============================================================================
# PART 3 -- Next steps
# ==============================================================================

Write-Host ""
Write-Head "=========================================="
Write-OK "Setup complete!"
Write-Head "=========================================="
Write-Host ""
Write-Sep
Write-Host "REQUIRED: activate the virtual environment"
Write-Host "before starting any agent in this project:"
Write-Host ""
Write-Host '  .\.venv\Scripts\Activate.ps1'
Write-Host ""
Write-Sep
Write-Host "API keys (all optional, improve rate limits)"
Write-Host ""
Write-Host "  Edit .env and fill in any of:"
Write-Host "    UNPAYWALL_EMAIL=you@example.com"
Write-Host "    SEMANTIC_SCHOLAR_KEY=your_key_here"
Write-Host "    OPENALEX_API_KEY=your_key_here"
Write-Host ""
Write-Sep
Write-Host "Verify the MCP server starts cleanly:"
Write-Host ""
Write-Host "  python mcp_server.py"
Write-Host "  # Expected: startup message on stderr, then waits"
Write-Host "  # Ctrl-C to exit"
Write-Host ""

if ($doClaudeCode) {
    Write-Sep
    Write-Host "CLAUDE CODE"
    Write-Host ""
    Write-Host "  1. Start Claude Code in this directory."
    Write-Host "  2. Run /mcp to confirm all servers are connected."
    Write-Host "  3. Run /deep-research to invoke the skill."
    Write-Host "  4. Authenticate alphaxiv (OAuth, first use only):"
    Write-Host "       claude mcp auth alphaxiv"
    Write-Host "     Or use /mcp inside a session."
    Write-Host ""
}

if ($doCodex) {
    Write-Sep
    Write-Host "CODEX CLI"
    Write-Host ""
    Write-Host "  1. Ensure Codex is installed:"
    Write-Host "       npm install -g @github/codex"
    Write-Host "       # or: winget install OpenAI.Codex"
    Write-Host "  2. Run: codex"
    Write-Host "  3. Run /mcp to confirm all servers are connected."
    Write-Host "  4. Run /skills to browse; invoke with: `$deep-research"
    Write-Host "  5. Authenticate alphaxiv (OAuth, first use only):"
    Write-Host "       codex mcp login alphaxiv"
    Write-Host "  6. Example:"
    Write-Host "       `$deep-research research BESS arbitrage strategies in CAISO"
    Write-Host ""
}

if ($doOpenCode) {
    Write-Sep
    Write-Host "OPENCODE"
    Write-Host ""
    Write-Host "  1. Run: opencode"
    Write-Host "  2. Run /mcp to confirm all servers are connected."
    Write-Host "  3. Run /deep-research to invoke the skill."
    Write-Host "  4. Authenticate alphaxiv (OAuth, first use only):"
    Write-Host "       opencode mcp auth alphaxiv"
    Write-Host ""
}

if ($doCopilotCLI) {
    Write-Sep
    Write-Host "COPILOT CLI"
    Write-Host ""
    Write-Host "  1. Run: copilot"
    Write-Host "  2. Run /mcp show to confirm servers are registered."
    Write-Host "  3. Run /skills list to confirm deep-research is visible."
    Write-Host "  4. Invoke: /deep-research <your research question>"
    Write-Host "  5. alphaxiv OAuth triggers automatically on first use."
    Write-Host ""
}

if ($doCopilotVSCode) {
    Write-Sep
    Write-Host "COPILOT VS CODE"
    Write-Host ""
    Write-Host "  1. Open this folder in VS Code."
    Write-Host "  2. Open Copilot Chat -> mode dropdown -> Agent."
    Write-Host "  3. Click Start in .vscode\mcp.json to launch servers."
    Write-Host "  4. Click the Auth CodeLens above the alphaxiv entry"
    Write-Host "     in mcp.json to complete OAuth."
    Write-Host "  5. Type: /deep-research <your research question>"
    Write-Host ""
}

Write-Sep
Write-Host "Full documentation: README.md"
Write-Host ""
Write-Host "To deactivate the virtual environment when done:"
Write-Host "  deactivate"
Write-Host ""
