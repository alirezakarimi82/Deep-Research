#!/usr/bin/env bash
# =============================================================================
#  DeepResearch Framework -- Unix / macOS setup
#  Works on bash and zsh.
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; CYAN='\033[0;36m'; NC='\033[0m'
info()  { echo -e "${GREEN}[ok]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[!]${NC}  $*"; }
error() { echo -e "${RED}[x]${NC}  $*" >&2; }
head_()  { echo -e "${CYAN}$*${NC}"; }

echo ""
head_ "==========================================="
head_ "   DeepResearch Framework -- Setup (Unix)"
head_ "==========================================="
echo ""

# ==============================================================================
# PART 1 -- Python environment and dependencies
# ==============================================================================

# -- Python version check ------------------------------------------------------
PY=$(command -v python3 || command -v python || true)
if [ -z "$PY" ]; then
    error "Python not found. Install Python 3.10+ from https://python.org"
    exit 1
fi
PY_VER=$("$PY" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PY_OK=$("$PY"  -c "import sys; print(int(sys.version_info >= (3,10)))")
if [ "$PY_OK" != "1" ]; then
    error "Python 3.10+ required (found $PY_VER)"
    exit 1
fi
info "Python $PY_VER"

# -- Virtual environment -------------------------------------------------------
if [ ! -d ".venv" ]; then
    "$PY" -m venv .venv
    info "Created .venv"
else
    info ".venv already exists -- skipping"
fi

# shellcheck disable=SC1091
source .venv/bin/activate
pip install -q --upgrade pip

# -- Python dependencies -------------------------------------------------------
info "Installing Python dependencies ..."
pip install -q -r requirements.txt
info "Python packages installed"

# -- reports directory ---------------------------------------------------------
mkdir -p reports
info "reports/ directory ready"

# -- .env file -----------------------------------------------------------------
if [ ! -f ".env" ] && [ -f ".env.example" ]; then
    cp .env.example .env
    info "Created .env from .env.example — fill in your API keys"
elif [ -f ".env" ]; then
    info ".env present"
else
    warn "No .env.example found — create .env manually with your API keys"
fi

# -- config.yaml ---------------------------------------------------------------
if [ ! -f "config.yaml" ]; then
    if [ -f "config.example.yaml" ]; then
        cp config.example.yaml config.yaml
        info "Created config.yaml from config.example.yaml"
    else
        warn "config.yaml missing and no template found"
    fi
else
    info "config.yaml present"
fi

# -- API key check -------------------------------------------------------------
HAVE_KEYS=false
for v in SEMANTIC_SCHOLAR_KEY OPENALEX_API_KEY UNPAYWALL_EMAIL; do
    if [ -n "${!v:-}" ]; then HAVE_KEYS=true; break; fi
done
# Also check .env file
if [ "$HAVE_KEYS" = false ] && [ -f ".env" ]; then
    if grep -qE '^(SEMANTIC_SCHOLAR_KEY|OPENALEX_API_KEY|UNPAYWALL_EMAIL)=.+' .env 2>/dev/null; then
        HAVE_KEYS=true
    fi
fi
if [ "$HAVE_KEYS" = false ]; then
    warn "No API keys found in env vars or .env — the pipeline works without them"
    warn "but rate limits will be lower. Edit .env to add keys."
fi

# -- Smoke test ----------------------------------------------------------------
info "Running import smoke test ..."
SMOKE_OUT=$(python -c "import sys; sys.path.insert(0,'.'); import mcp_server" 2>/dev/null || true)
if [ -z "$SMOKE_OUT" ]; then
    info "Smoke test passed (stdout clean on import)"
else
    error "Smoke test FAILED -- mcp_server wrote to stdout during import:"
    echo "$SMOKE_OUT"
    error "This WILL corrupt the MCP JSON-RPC protocol. Fix before using."
    exit 1
fi

# -- Unit tests ----------------------------------------------------------------
if python -c "import pytest" 2>/dev/null && [ -d "tests" ]; then
    info "Running unit tests ..."
    if python -m pytest tests/ -q --no-header 2>&1 | tail -5; then
        info "Tests passed"
    else
        warn "Some tests failed — the install may still be usable but investigate"
    fi
fi

# ==============================================================================
# PART 2 -- Platform selection and skill installation
# ==============================================================================

echo ""
head_ "==========================================="
head_ "   Platform setup"
head_ "==========================================="
echo ""
echo "Which agent platform(s) do you want to configure?"
echo ""
echo "  1) Claude Code"
echo "  2) OpenCode"
echo "  3) Copilot CLI"
echo "  4) Copilot VS Code"
echo "  5) All platforms"
echo "  6) Skip (manual setup later)"
echo ""
printf "Enter numbers separated by spaces (e.g. 1 2): "
read -r PLATFORM_INPUT

# Parse selections
DO_CLAUDE=false; DO_OPENCODE=false; DO_COPILOT_CLI=false; DO_COPILOT_VSCODE=false

if echo "$PLATFORM_INPUT" | grep -qw "5"; then
    DO_CLAUDE=true; DO_OPENCODE=true; DO_COPILOT_CLI=true; DO_COPILOT_VSCODE=true
else
    echo "$PLATFORM_INPUT" | grep -qw "1" && DO_CLAUDE=true      || true
    echo "$PLATFORM_INPUT" | grep -qw "2" && DO_OPENCODE=true     || true
    echo "$PLATFORM_INPUT" | grep -qw "3" && DO_COPILOT_CLI=true  || true
    echo "$PLATFORM_INPUT" | grep -qw "4" && DO_COPILOT_VSCODE=true || true
fi

SKILL_NAME="deep-research"
INSTALLED_ANY=false

# -- Skill installation helper -------------------------------------------------
install_skill() {
    local dest_dir="$1"   # full path to skill directory (no trailing slash)
    local overlay="$2"    # which overlay to install as SKILL.md

    mkdir -p "$dest_dir"
    cp "$overlay"     "$dest_dir/SKILL.md"
    cp "SKILL-core.md" "$dest_dir/SKILL-core.md"
    info "Skill installed → $dest_dir/"
}

# -- Claude Code ---------------------------------------------------------------
if [ "$DO_CLAUDE" = true ]; then
    echo ""
    head_ "--- Claude Code ---"
    echo "Install scope:"
    echo "  1) Personal  -- ~/.claude/skills/   (all projects, recommended)"
    echo "  2) Project   -- .claude/skills/      (this repo only)"
    printf "Choice [1]: "
    read -r CC_SCOPE
    CC_SCOPE="${CC_SCOPE:-1}"

    if [ "$CC_SCOPE" = "2" ]; then
        DEST=".claude/skills/$SKILL_NAME"
    else
        DEST="$HOME/.claude/skills/$SKILL_NAME"
    fi
    install_skill "$DEST" "SKILL-claude-code.md"

    # Generate .mcp.json template if it doesn't exist
    if [ ! -f ".mcp.json" ]; then
        ABS_DIR="$SCRIPT_DIR"
        cat > .mcp.json <<MCPJSON
{
  "mcpServers": {
    "deep-research": {
      "command": "python",
      "args": ["mcp_server.py"],
      "cwd": "$ABS_DIR"
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
MCPJSON
        info "Created .mcp.json for Claude Code (project-scoped MCP config)"
    else
        info ".mcp.json already exists — skipping (add deep-research entry manually if needed)"
    fi

    INSTALLED_ANY=true
fi

# -- OpenCode ------------------------------------------------------------------
if [ "$DO_OPENCODE" = true ]; then
    echo ""
    head_ "--- OpenCode ---"
    echo "Install scope:"
    echo "  1) Project  -- .opencode/skills/              (this repo, recommended)"
    echo "  2) Global   -- ~/.config/opencode/skills/     (all projects)"
    printf "Choice [1]: "
    read -r OC_SCOPE
    OC_SCOPE="${OC_SCOPE:-1}"

    if [ "$OC_SCOPE" = "2" ]; then
        DEST="$HOME/.config/opencode/skills/$SKILL_NAME"
    else
        DEST=".opencode/skills/$SKILL_NAME"
    fi
    install_skill "$DEST" "SKILL-opencode.md"

    # opencode.json already exists in the repo; note it
    if [ -f "opencode.json" ]; then
        info "opencode.json present — MCP config already registered for OpenCode"
    else
        warn "opencode.json not found — copy the template from the repo root"
    fi

    INSTALLED_ANY=true
fi

# -- Copilot CLI ---------------------------------------------------------------
if [ "$DO_COPILOT_CLI" = true ]; then
    echo ""
    head_ "--- Copilot CLI ---"
    echo "Install scope:"
    echo "  1) Personal -- ~/.copilot/skills/   (all projects, recommended)"
    echo "  2) Project  -- .github/skills/       (this repo only)"
    printf "Choice [1]: "
    read -r CCLI_SCOPE
    CCLI_SCOPE="${CCLI_SCOPE:-1}"

    if [ "$CCLI_SCOPE" = "2" ]; then
        DEST=".github/skills/$SKILL_NAME"
    else
        DEST="$HOME/.copilot/skills/$SKILL_NAME"
    fi
    install_skill "$DEST" "SKILL-copilot.md"

    # MCP config
    if [ "$CCLI_SCOPE" = "2" ]; then
        info ".copilot/mcp-config.json already exists in repo for project-scoped use"
    else
        mkdir -p "$HOME/.copilot"
        if [ ! -f "$HOME/.copilot/mcp-config.json" ]; then
            # Patch the cwd in the MCP config to the absolute path of this repo
            sed "s|\"cwd\": \"\${workspaceFolder}\"|\"cwd\": \"$SCRIPT_DIR\"|g" \
                .copilot/mcp-config.json > "$HOME/.copilot/mcp-config.json"
            info "Copied MCP config → ~/.copilot/mcp-config.json (with absolute path patched)"
        else
            warn "~/.copilot/mcp-config.json already exists — skipping (merge deep-research entry manually)"
        fi
    fi

    INSTALLED_ANY=true
fi

# -- Copilot VS Code -----------------------------------------------------------
if [ "$DO_COPILOT_VSCODE" = true ]; then
    echo ""
    head_ "--- Copilot VS Code ---"
    echo "Install scope:"
    echo "  1) Workspace -- .github/skills/              (this repo, recommended)"
    echo "  2) Global    -- ~/.config/copilot/skills/    (all workspaces)"
    printf "Choice [1]: "
    read -r CVSC_SCOPE
    CVSC_SCOPE="${CVSC_SCOPE:-1}"

    if [ "$CVSC_SCOPE" = "2" ]; then
        DEST="$HOME/.config/copilot/skills/$SKILL_NAME"
    else
        DEST=".github/skills/$SKILL_NAME"
    fi
    install_skill "$DEST" "SKILL-copilot.md"

    # .vscode/mcp.json already exists in the repo; note it
    if [ -f ".vscode/mcp.json" ]; then
        info ".vscode/mcp.json present — MCP config already registered for VS Code"
    else
        warn ".vscode/mcp.json not found — copy the template from the repo"
    fi

    INSTALLED_ANY=true
fi

if [ "$INSTALLED_ANY" = false ]; then
    warn "No platforms configured — skill files were not installed"
    warn "Re-run setup.sh to install skills, or copy them manually (see README)"
fi

# ==============================================================================
# PART 3 -- Next steps (tailored to what was installed)
# ==============================================================================

echo ""
head_ "==========================================="
info "Setup complete!"
head_ "==========================================="
echo ""
echo "───────────────────────────────────────────"
echo "REQUIRED: activate the virtual environment"
echo "before starting any agent in this project:"
echo ""
echo "  source .venv/bin/activate"
echo ""
echo "───────────────────────────────────────────"
echo "API keys (all optional, improve rate limits)"
echo ""
echo "  Edit .env and fill in any of:"
echo "    UNPAYWALL_EMAIL=you@example.com"
echo "    SEMANTIC_SCHOLAR_KEY=your_key_here"
echo "    OPENALEX_API_KEY=your_key_here"
echo ""
echo "───────────────────────────────────────────"
echo "Verify the MCP server starts cleanly:"
echo ""
echo "  python mcp_server.py"
echo "  # Expected: startup message on stderr, then waits"
echo "  # Ctrl-C to exit"
echo ""

if [ "$DO_CLAUDE" = true ]; then
    echo "───────────────────────────────────────────"
    echo "CLAUDE CODE"
    echo ""
    echo "  1. Start Claude Code in this directory."
    echo "  2. Run /mcp to confirm all servers are connected."
    echo "  3. Run /deep-research to invoke the skill."
    echo "  4. Authenticate alphaxiv (OAuth, first use only):"
    echo "       claude mcp auth alphaxiv"
    echo "     Or use /mcp inside a session."
    echo ""
fi

if [ "$DO_OPENCODE" = true ]; then
    echo "───────────────────────────────────────────"
    echo "OPENCODE"
    echo ""
    echo "  1. Run: opencode"
    echo "  2. Run /mcp to confirm all servers are connected."
    echo "  3. Run /deep-research to invoke the skill."
    echo "  4. Authenticate alphaxiv (OAuth, first use only):"
    echo "       opencode mcp auth alphaxiv"
    echo ""
fi

if [ "$DO_COPILOT_CLI" = true ]; then
    echo "───────────────────────────────────────────"
    echo "COPILOT CLI"
    echo ""
    echo "  1. Run: copilot"
    echo "  2. Run /mcp show to confirm servers are registered."
    echo "  3. Run /skills list to confirm deep-research is visible."
    echo "  4. Invoke: /deep-research <your research question>"
    echo "  5. alphaxiv OAuth triggers automatically on first use."
    echo ""
fi

if [ "$DO_COPILOT_VSCODE" = true ]; then
    echo "───────────────────────────────────────────"
    echo "COPILOT VS CODE"
    echo ""
    echo "  1. Open this folder in VS Code."
    echo "  2. Open Copilot Chat → mode dropdown → Agent."
    echo "  3. Click Start in .vscode/mcp.json to launch servers."
    echo "  4. Click the Auth CodeLens above the alphaxiv entry"
    echo "     in mcp.json to complete OAuth."
    echo "  5. Type: /deep-research <your research question>"
    echo ""
fi

echo "───────────────────────────────────────────"
echo "Full documentation: README.md"
echo ""
