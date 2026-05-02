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
head()  { echo -e "${CYAN}$*${NC}"; }

echo ""
head "==========================================="
head "   DeepResearch Framework -- Setup (Unix)"
head "==========================================="
echo ""

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

# -- Config file ---------------------------------------------------------------
if [ ! -f "config.yaml" ]; then
    if [ -f "config.example.yaml" ]; then
        cp config.example.yaml config.yaml
        info "Created config.yaml from config.example.yaml (placeholder values)"
    else
        warn "config.yaml missing and no template found"
    fi
else
    info "config.yaml present"
fi

# -- Secret check --------------------------------------------------------------
# Secrets can come from either env vars (preferred) OR config.yaml.
# We don't demand any -- the pipeline works without keys, just slower/limited.
HAVE_SS_ENV="${SEMANTIC_SCHOLAR_KEY:-}"
HAVE_OA_ENV="${OPENALEX_API_KEY:-}"
HAVE_UP_ENV="${UNPAYWALL_EMAIL:-}"
if [ -z "$HAVE_SS_ENV" ] && [ -z "$HAVE_OA_ENV" ] && [ -z "$HAVE_UP_ENV" ]; then
    warn "No API-key env vars detected (SEMANTIC_SCHOLAR_KEY, OPENALEX_API_KEY, UNPAYWALL_EMAIL)"
    warn "The pipeline will still run, but rate limits will be lower."
    warn "See the 'Next steps' section below to configure keys."
fi

# -- Smoke test: stdout must be clean on import --------------------------------
# The MCP server speaks stdio; any accidental print() to stdout corrupts the
# JSON-RPC stream. This test catches regressions of that class of bug.
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

# -- Optional: run unit tests --------------------------------------------------
if python -c "import pytest" 2>/dev/null && [ -d "tests" ]; then
    info "Running unit tests ..."
    if python -m pytest tests/ -q --no-header 2>&1 | tail -5; then
        info "Tests passed"
    else
        warn "Some tests failed -- the install may still be usable but investigate"
    fi
fi

# -- Next steps ----------------------------------------------------------------
echo ""
head "==========================================="
info "Setup complete!"
head "==========================================="
echo ""
echo "Next steps:"
echo ""
echo "  1. Activate the virtual environment before starting your agent:"
echo "       source .venv/bin/activate"
echo ""
echo "  2. (Optional but recommended) set API keys as environment variables."
echo "     This is the preferred path; env vars override config.yaml:"
echo ""
echo "       export UNPAYWALL_EMAIL=\"you@example.com\"     # polite-pool access"
echo "       export SEMANTIC_SCHOLAR_KEY=\"...\"             # 10k req/min vs 100/5min"
echo "       export OPENALEX_API_KEY=\"...\"                 # semantic search + PDFs"
echo ""
echo "     Add them to your shell profile (~/.zshrc, ~/.bashrc) to persist."
echo "     IMPORTANT: never commit config.yaml with live keys."
echo ""
echo "  3. Start your agent. MCP servers are launched automatically:"
echo "       opencode                             # reads opencode.json"
echo "       claude                               # reads .mcp.json"
echo ""
echo "  4. Verify the MCP server is reachable from inside your agent:"
echo "       /mcp                                 # Claude Code"
echo "       :mcp                                 # OpenCode"
echo ""
