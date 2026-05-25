# DeepResearch Framework

A multi-source, agentic research pipeline that turns any question into a
fully-cited Markdown or LaTeX report. Runs inside **Claude Code**,
**OpenCode**, **GitHub Copilot CLI**, and **GitHub Copilot in VS Code**.

```
User request → Plan → Gather (MCP tools) → Rank → Retrieve → Synthesise → Report
```

---

## Contents

**Setup**
[Platform compatibility](#platform-compatibility) ·
[Quick start](#quick-start) ·
[Installation — all platforms](#installation--all-platforms) ·
[API keys](#step-2--api-keys) ·
[Ranker tuning](#step-3--ranker-tuning-optional)

**Platform guides**
[Claude Code](#platform-setup--claude-code) ·
[OpenCode](#platform-setup--opencode) ·
[Copilot CLI](#platform-setup--copilot-cli) ·
[Copilot VS Code](#platform-setup--copilot-in-vs-code) ·
[Codex CLI](#platform-setup--codex-cli)

**MCP & authentication**
[Pipeline tools](#mcp-pipeline-tools) ·
[External servers](#external-mcp-servers) ·
[alphaxiv authentication](#alphaxiv-authentication)

**Reference**
[Skill architecture](#skill-architecture) ·
[Workflow summary](#workflow-summary) ·
[Tests](#tests) ·
[Verifying the install](#verifying-the-install) ·
[Troubleshooting](#troubleshooting) ·
[File structure](#file-structure)

---

## Platform compatibility

| Feature | Claude Code | OpenCode | Copilot CLI | Copilot VS Code | Codex CLI |
|---|:---:|:---:|:---:|:---:|:---:|
| Local stdio MCP servers | ✅ | ✅ | ✅ | ✅ | ✅ |
| Remote SSE MCP servers | ✅ | ✅ | ✅ | ✅ | ✅ |
| Skill files (SKILL.md) | ✅ | ✅ | ✅ | ✅ | ✅ |
| `agents/openai.yaml` metadata | — | — | — | — | ✅ |
| AGENTS.md project context | ✅ | ✅ | — | — | ✅ |
| MCP config format | JSON | JSON | JSON | JSON | **TOML** |
| Structured `askUser` tool | ✅ | ✅ | prose only | prose only | prose only |
| Native plan mode | ✅ | — | ✅ (Shift+Tab) | — | — |
| Parallel subagents | ✅ (`Agent`) | ✅ (`Task`) | ✅ (`/fleet`) | limited | Agents SDK |
| Native task tracker | ✅ | ✅ | — | — | — |
| `.tasks.md` fallback tracker | — | — | ✅ | ✅ | ✅ |

> **Copilot org prerequisite:** MCP is disabled by default for Copilot
> Business and Enterprise plans. An org admin must enable it under
> Organization → Settings → Copilot → MCP. Individual Free and Pro plans
> have MCP available without any additional toggle.

---

## Quick start

```bash
# 1. Install Python dependencies
bash setup.sh          # macOS / Linux
.\setup.ps1            # Windows PowerShell

# 2. Set API keys
export UNPAYWALL_EMAIL="you@example.com"
export SEMANTIC_SCHOLAR_KEY="..."    # optional
export OPENALEX_API_KEY="..."        # optional

# 3. Start your agent
opencode               # OpenCode    — reads opencode.json
claude                 # Claude Code — reads .mcp.json / .claude/mcp.json
copilot                # Copilot CLI — reads .copilot/mcp-config.json
# VS Code: open workspace, Copilot Chat → mode dropdown → Agent

# 4. Verify MCP servers are live
/mcp                   # Claude Code
/mcp                   # OpenCode
/mcp show              # Copilot CLI
# VS Code: Agent mode → tools icon → server list
```

---

## MCP pipeline tools

These tools are exposed by `mcp_server.py` and are identical on all
four platforms.

| Tool | Signature | Notes |
|---|---|---|
| `search_openalex` | `(query, max_results=20)` | 250 M+ works; two-pass (recent + seminal). Full-text PDF gate on **both** passes when API key is set. |
| `search_semantic_scholar` | `(query, max_results=20)` | AI TLDRs, citation graph, OA PDFs. Two-pass. |
| `search_crossref` | `(query, max_results=20, from_year=None)` | DOI metadata + **parallel** Unpaywall OA PDF enrichment (8 concurrent workers). |
| `search_wikipedia` | `(query, max_results=5)` | Real article leads via REST API (not just snippets). |
| `search_hackernews` | `(query, max_results=10)` | Practitioner discussions via Algolia. |
| `search_reddit` | `(query, subreddit="all", max_results=10)` | Community knowledge; subreddit routing available. |
| `rank_and_filter` | `(sources_json, query, key_concepts_json, top_n=None)` | DOI-exact dedup with field-level merge → fuzzy title dedup → full-text gate → relevance score → temporal balance. `top_n` defaults to `analysis.max_sources_for_synthesis` in `config.yaml`. |
| `extract_content` | `(url)` | Jina Reader → trafilatura → BeautifulSoup fallback. |
| `parse_pdf` | `(url)` | **Streamed download, 50 MB hard cap**; pdfplumber → PyMuPDF fallback. |

**Server-side guarantees:**

- Abstract-only and closed-access papers are dropped by the full-text
  gate before returning — no pre-filtering needed.
- DOI duplicates across sources are merged at the field level: the
  ranked output carries the PDF URL from OpenAlex, the TLDR from
  Semantic Scholar, and the venue from Crossref as a single entry.
- Web sources must carry either a URL or a ≥200-char snippet to pass
  the gate.
- `parse_pdf` returning empty string means the file exceeded the 50 MB
  cap or contained only scanned images — treat as inaccessible and
  move on.

### External MCP servers

| Server | Type | Auth | Key tools |
|---|---|---|---|
| `alphaxiv` | remote SSE | **OAuth 2.0 required** | `alphaxiv_embedding_similarity_search`, `alphaxiv_full_text_papers_search`, `alphaxiv_agentic_paper_retrieval`, `alphaxiv_get_paper_content`, `alphaxiv_answer_pdf_queries` |
| `ddgs` | local stdio | none | `ddgs_search_text`, `ddgs_search_news`, `ddgs_search_books`, `ddgs_extract_content` |
| `playwright` | local stdio | none | `browser_navigate`, `browser_snapshot` — last-resort JS-heavy page fallback only |

> **Note on alphaxiv transport:** alphaxiv uses SSE (Server-Sent Events), which was
> deprecated in the MCP specification in mid-2025 in favor of streamable HTTP. SSE
> still works and all four platforms support it, but expect alphaxiv to migrate to
> HTTP transport in a future release. No action needed on your part until they do.

### alphaxiv authentication

alphaxiv requires **OAuth 2.0** before any of its tools can be used. Each platform
handles this differently. Authentication is a one-time step per machine; tokens are
stored locally and refreshed automatically.

**OpenCode**

OpenCode automatically detects the OAuth requirement on first use and opens a browser
window. To manually trigger the flow (e.g. after a token expires):

```bash
opencode mcp auth alphaxiv
```

The `opencode.json` entry must include `"oauth": {}` to signal that OAuth is expected:

```json
"alphaxiv": {
  "type": "remote",
  "url": "https://api.alphaxiv.org/mcp/v1",
  "oauth": {}
}
```

Check auth status for all OAuth-capable servers:

```bash
opencode mcp auth list    # or: opencode mcp auth ls
```

Debug connection and OAuth flow if something is wrong:

```bash
opencode mcp debug alphaxiv
```

Tokens are stored in `~/.local/share/opencode/mcp-auth.json`.

**Claude Code**

Claude Code auto-discovers OAuth metadata and handles Dynamic Client Registration
(DCR) automatically. Add the server with the legacy SSE transport (alphaxiv has not
yet migrated to HTTP):

```bash
claude mcp add --transport sse alphaxiv https://api.alphaxiv.org/mcp/v1
```

On first use, Claude Code launches a browser for authorization. To manually
re-authenticate from the CLI:

```bash
claude mcp auth alphaxiv
```

Or re-authenticate from inside a running session without restarting:

```
/mcp
```

**Codex CLI**

Codex CLI handles OAuth via the `codex mcp login` command. Run this once
per machine after adding the alphaxiv server:

```bash
codex mcp login alphaxiv
```

A browser window opens for authorization. Tokens are stored in
`~/.codex/` and refreshed automatically. Check status with:

```bash
codex mcp show alphaxiv
```

**Copilot CLI**

Copilot CLI triggers OAuth automatically via Dynamic Client Registration when you
first call an alphaxiv tool. No extra command is needed — the browser opens and
tokens are stored in `~/.copilot/mcp-oauth-config/`. To check the status of all
OAuth-protected servers:

```bash
copilot
/mcp show
```

If the automatic flow fails (e.g. the server does not support DCR), add the server
interactively with `/mcp add` and supply a pre-registered client ID when prompted.

**Copilot VS Code**

After adding alphaxiv to `.vscode/mcp.json` and clicking **Start**, VS Code detects
the OAuth requirement and shows a CodeLens **Auth** button directly above the server
entry in the file. Click **Auth** — a popup window opens for browser-based
authorization. Once complete, tools become available in agent mode immediately.

If the Auth button does not appear, open Copilot Chat (agent mode) → tools icon →
find `alphaxiv` in the list → click the key icon next to it.

---

## Installation — all platforms

### Step 1 — Python dependencies

```bash
# macOS / Linux
bash setup.sh
source .venv/bin/activate

# Windows (PowerShell)
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\setup.ps1
.\.venv\Scripts\Activate.ps1
```

The setup script creates `.venv`, installs `requirements.txt`, copies
`config.example.yaml` → `config.yaml` if missing, runs an import smoke
test (verifies the MCP server writes nothing to stdout), and optionally
runs the 29-test unit suite.

### Step 2 — API keys

All keys are optional but improve rate limits and unlock features.

Keys are resolved in this order — use whichever approach suits your workflow:

| Priority | Method | Best for |
|---|---|---|
| 1 (highest) | Shell environment variables | CI, Docker, shared machines |
| 2 | `.env` file in project root | Local dev without touching shell profile |
| 3 | `config.yaml` top-level fields | Non-secret values like `unpaywall_email` |
| 4 (lowest) | Hard-coded defaults | Zero-config fallback |

| Variable | Where to get | Effect |
|---|---|---|
| `UNPAYWALL_EMAIL` | Your own email, no registration needed | Polite-pool access, 100k OA PDF lookups/day |
| `SEMANTIC_SCHOLAR_KEY` | semanticscholar.org/product/api | 10k req/min (vs 100/5 min unauthenticated) |
| `OPENALEX_API_KEY` | openalex.org/api-key | Semantic embedding search + full-text PDFs |

**Option A — `.env` file (recommended for local dev):**

```bash
cp .env.example .env
# Edit .env and fill in your values — it is gitignored
```

`.env` is loaded automatically by `config.py` via `python-dotenv`. Shell
environment variables always override `.env` values, so CI/CD secrets
set at the system level are never clobbered by a local `.env` file.

**Option B — Shell environment variables:**

```bash
# macOS / Linux
export UNPAYWALL_EMAIL="you@example.com"
export SEMANTIC_SCHOLAR_KEY="your_key_here"
export OPENALEX_API_KEY="your_key_here"
# Add to ~/.zshrc or ~/.bashrc to persist across sessions
```

```powershell
# Windows (PowerShell)
$env:UNPAYWALL_EMAIL      = "you@example.com"
$env:SEMANTIC_SCHOLAR_KEY = "your_key_here"
$env:OPENALEX_API_KEY     = "your_key_here"
# For persistence:
[Environment]::SetEnvironmentVariable("UNPAYWALL_EMAIL","you@example.com","User")
```

**Option C — `config.yaml` fallback:**

Copy `config.example.yaml` to `config.yaml` and fill in the top-level
fields. **Never commit `config.yaml` with live keys.**

### Step 3 — Ranker tuning (optional)

Edit the `analysis:` block in `config.yaml`. Changes take effect on
the next server restart.

```yaml
analysis:
  max_sources_for_synthesis: 30   # default top_n for rank_and_filter
  dedup_threshold: 0.85           # fuzzy title similarity cutoff (0–1)
  recent_years: 3                 # "recent" bucket: papers within N years
  seminal_threshold: 100          # "seminal" bucket: cited_by_count >= N
  recent_share: 0.40              # fraction of top_n from recent bucket
  seminal_share: 0.30             # fraction from seminal (rest goes to middle)
```

---

## Platform setup — Claude Code

### MCP configuration

Create `.mcp.json` in the repo root (project-scoped) or add to
`~/.claude/settings.json` (global):

```json
{
  "mcpServers": {
    "deep-research": {
      "command": "python",
      "args": ["mcp_server.py"],
      "cwd": "/absolute/path/to/deep-research"
    },
    "alphaxiv": {
      "type": "sse",
      "url": "https://api.alphaxiv.org/mcp/v1"
      // OAuth required: run `claude mcp auth alphaxiv` or use /mcp in-session
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
```

### Skill installation

Both the overlay and the core must be in the same directory.

```bash
# Project-scoped
mkdir -p .claude/skills/deep-research
cp SKILL-claude-code.md .claude/skills/deep-research/SKILL.md
cp SKILL-core.md        .claude/skills/deep-research/

# Global (all projects)
mkdir -p ~/.claude/skills/deep-research
cp SKILL-claude-code.md ~/.claude/skills/deep-research/SKILL.md
cp SKILL-core.md        ~/.claude/skills/deep-research/
```

### Usage

```
/deep-research  write a report on BESS degradation and bidding in CAISO
```

Plan mode activates automatically at Step 1. Confirm the plan to begin
gathering. Verify MCP servers: `/mcp`.

---

## Platform setup — OpenCode

### MCP configuration

OpenCode reads `opencode.json` from the project root automatically.
The shipped `opencode.json` is ready to use:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "permission": { "skill": { "*": "allow" } },
  "mcp": {
    "deep-research": { "type": "local", "command": ["python", "mcp_server.py"] },
    "alphaxiv":      { "type": "remote", "url": "https://api.alphaxiv.org/mcp/v1", "oauth": {} },
    "ddgs":          { "type": "local",  "command": ["ddgs", "mcp"] },
    "playwright":    { "type": "local",  "command": ["npx", "@playwright/mcp@latest", "--headless"] }
  }
}
```

For global config, merge into `~/.config/opencode/config.json`.

### Skill installation

```bash
# Project-scoped
mkdir -p .opencode/skills/deep-research
cp SKILL-opencode.md .opencode/skills/deep-research/SKILL.md
cp SKILL-core.md     .opencode/skills/deep-research/

# Global
mkdir -p ~/.config/opencode/skills/deep-research
cp SKILL-opencode.md ~/.config/opencode/skills/deep-research/SKILL.md
cp SKILL-core.md     ~/.config/opencode/skills/deep-research/
```

### Usage

```
/deep-research  research solid electrolyte interphase formation mechanisms
```

Use the **Plan** tab (Tab key) to review the plan before confirming.
Switch to **Build** to begin gathering. Verify MCP: `/mcp`. Toggle
`/dcp` to prune context on long Extensive-length runs.

---

## Platform setup — Copilot CLI

### Installation

Copilot CLI is a standalone npm package. Node.js 22 or later is
required.

```bash
# npm (all platforms)
npm install -g @github/copilot

# macOS (Homebrew)
brew install github-copilot

# Windows (WinGet)
winget install GitHub.CopilotCLI
```

Authenticate on first launch:

```bash
copilot
/login     # browser flow; token stored in ~/.copilot/
```

For headless or CI use, set `COPILOT_GITHUB_TOKEN` (or `GH_TOKEN` /
`GITHUB_TOKEN`) to a fine-grained PAT with the "Copilot Requests"
permission instead of using the browser flow.

> **Organization accounts:** an org admin must enable the Copilot CLI
> policy under Organization → Settings → Copilot before members can
> use it.

### MCP configuration

The shipped `.copilot/mcp-config.json` is ready for project-scoped use.
For global setup:

```bash
cp .copilot/mcp-config.json ~/.copilot/mcp-config.json
# Edit the deep-research "cwd" to the absolute path of this directory
```

Config precedence (highest → lowest):
1. `--additional-mcp-config <path>` flag on the `copilot` command
2. Project `.copilot/mcp-config.json`
3. User `~/.copilot/mcp-config.json`

Add or modify servers interactively from inside a session:

```
/mcp add
```

Verify all registered servers and their tools:

```
/mcp show
```

> **Note:** if you already have `.vscode/mcp.json` for VS Code, the
> `servers` root key needs to be renamed to `mcpServers` for Copilot
> CLI. The shipped `.copilot/mcp-config.json` already uses the correct
> format — use it directly.

### Skill installation

Copilot CLI picks up skills from the following locations (first match
wins for duplicate names):

| Location | Scope |
|---|---|
| `~/.copilot/skills/<name>/SKILL.md` | Personal / all projects |
| `.github/skills/<name>/SKILL.md` | Project |
| `.claude/skills/<name>/SKILL.md` | Also auto-discovered |
| `.agents/skills/<name>/SKILL.md` | Project |

If the skill is already installed for Claude Code in `.claude/skills/`,
Copilot CLI picks it up automatically — just ensure `SKILL-core.md` is
alongside the overlay file.

```bash
# Personal (recommended)
mkdir -p ~/.copilot/skills/deep-research
cp SKILL-copilot.md ~/.copilot/skills/deep-research/SKILL.md
cp SKILL-core.md    ~/.copilot/skills/deep-research/

# Project-scoped
mkdir -p .github/skills/deep-research
cp SKILL-copilot.md .github/skills/deep-research/SKILL.md
cp SKILL-core.md    .github/skills/deep-research/
```

Verify:

```
/skills list
/skills info deep-research
```

### Usage

Interactive session:

```bash
copilot
/deep-research  research lithium dendrite suppression in solid-state batteries
```

Non-interactive (scripting / CI):

```bash
copilot -p "Use the deep-research skill to write a report on BESS arbitrage in CAISO"
```

**Plan mode:** Shift+Tab to enter, Shift+Tab again to switch to
autopilot and confirm. Use `/model` to switch models mid-session. Use
`/fleet` for parallel subagent branches on broad topics — the skill
triggers this automatically when the query warrants it.

---

## Platform setup — Copilot in VS Code

### Prerequisites

- VS Code 1.99 or later (current release: 1.116, May 2026)
- GitHub Copilot + Copilot Chat extensions, signed in
- Agent mode: Copilot Chat → mode dropdown → **Agent**

MCP tools are only active in **Agent mode**. They are invisible in
Ask and Edit modes.

> **Organization accounts:** for Copilot Business or Enterprise plans,
> an org admin must enable the "MCP servers in Copilot" policy under
> Organization → Settings → Copilot → MCP. Individual Free and Pro plans
> have MCP available without any additional toggle.

### MCP configuration

The shipped `.vscode/mcp.json` is ready for workspace use. VS Code uses
`"servers"` as the root key (different from Claude Code's
`"mcpServers"`):

```json
{
  "servers": {
    "deep-research": {
      "type": "stdio",
      "command": "python",
      "args": ["${workspaceFolder}/mcp_server.py"]
    },
    "alphaxiv": { "type": "sse",   "url": "https://api.alphaxiv.org/mcp/v1" },  // OAuth required — click Auth CodeLens after Start
    "ddgs":     { "type": "stdio", "command": "ddgs", "args": ["mcp"] },
    "playwright": {
      "type":    "stdio",
      "command": "npx",
      "args":    ["@playwright/mcp@latest", "--headless"]
    }
  }
}
```

For user-level config (all workspaces): Command Palette →
**MCP: Open User Configuration** → add the same `servers` block.

You can also use Command Palette → **MCP: Add Server** for a guided
flow, or browse the built-in MCP gallery: Extensions view → search
`@mcp`.

After adding or editing `mcp.json`, a **Start** button appears at the
top of the file — click it to start the servers and discover their
tools. Enable `chat.mcp.autoStart` in settings to have VS Code restart
servers automatically on config changes.

Verify: Agent mode → tools icon (top-left of chat box) → all configured
servers and tools appear in the list.

### Skill installation

```bash
# Workspace-scoped
mkdir -p .github/skills/deep-research
cp SKILL-copilot.md .github/skills/deep-research/SKILL.md
cp SKILL-core.md    .github/skills/deep-research/

# Global
mkdir -p ~/.config/copilot/skills/deep-research
cp SKILL-copilot.md ~/.config/copilot/skills/deep-research/SKILL.md
cp SKILL-core.md    ~/.config/copilot/skills/deep-research/
```

### Usage

In Copilot Chat (Agent mode):

```
/deep-research  comprehensive review of hydrogen storage materials
```

The skill writes the plan to `reports/.plans/<slug>.md`, presents it in
chat, and waits for your explicit "yes" before gathering begins.

MCP tools are only active in Agent mode. If tool calls are not
executing, check the mode dropdown.


---

## Platform setup — Codex CLI

### Installation

Codex CLI is a standalone npm package. Node.js 18 or later is required.

```bash
# npm (all platforms)
npm install -g @github/codex

# macOS (Homebrew)
brew install openai-codex

# Windows (WinGet)
winget install OpenAI.Codex
```

Authenticate on first launch:

```bash
codex
/login      # browser flow; credentials stored in ~/.codex/
```

For headless or CI use, set an `OPENAI_API_KEY` environment variable
and pass `--no-interactive`.

### MCP configuration

Codex uses **TOML** for MCP config — the only platform in this stack
that doesn't use JSON. The shipped `.codex/config.toml` is ready for
project-scoped use (trusted projects only). For global setup:

```bash
cp .codex/config.toml ~/.codex/config.toml
# Edit the deep-research cwd to the absolute path of this directory
```

Or register servers interactively (recommended for first setup):

```bash
codex mcp add deep-research -- python /absolute/path/to/mcp_server.py
codex mcp add ddgs -- ddgs mcp
codex mcp add alphaxiv --url https://api.alphaxiv.org/mcp/v1
```

Config precedence (highest → lowest):
1. `~/.codex/config.toml` (global)
2. `.codex/config.toml` in a trusted project (project-scoped)

Trust a project so project-scoped config is read:

```bash
codex trust         # in the project root
```

Verify all registered servers:

```
/mcp
```

> **TOML syntax notes:** arrays use `["val1", "val2"]`, strings always
> need quotes, and section names use dot notation
> `[mcp_servers.server-name]`. Use `codex mcp list` to validate after
> editing — a silent config error means the server simply won't appear.

### Skill installation

Skills go in `~/.codex/skills/` (personal) or `.codex/skills/`
(project, trusted projects only). Codex also reads `~/.agents/skills/`
for cross-platform skill sharing.

Unlike other platforms, Codex skills support an optional
`agents/openai.yaml` alongside `SKILL.md` for UI metadata and
invocation policy. This repo ships it at `agents/openai.yaml`.

```bash
# Personal (recommended)
mkdir -p ~/.codex/skills/deep-research/agents
cp SKILL-codex.md     ~/.codex/skills/deep-research/SKILL.md
cp SKILL-core.md      ~/.codex/skills/deep-research/SKILL-core.md
cp agents/openai.yaml ~/.codex/skills/deep-research/agents/openai.yaml

# Project-scoped (trusted project required)
mkdir -p .codex/skills/deep-research/agents
cp SKILL-codex.md     .codex/skills/deep-research/SKILL.md
cp SKILL-core.md      .codex/skills/deep-research/SKILL-core.md
cp agents/openai.yaml .codex/skills/deep-research/agents/openai.yaml
```

Restart Codex after installing. Verify with `/skills`.

> **Shared install tip:** because Codex also reads `~/.agents/skills/`,
> a single install there is discovered by Codex, Claude Code, OpenCode,
> and any other SKILL.md-compatible agent — the right overlay for each
> platform just needs to be installed in that platform's own directory.

### AGENTS.md (optional but recommended)

`AGENTS.md` gives Codex always-on project context without consuming
skill slot budget. Add one to the repo root with facts a new contributor
needs on day one:

```markdown
# DeepResearch project

- Python 3.10+, virtual environment at `.venv/`
- Activate: `source .venv/bin/activate`
- Run tests: `pytest tests/`
- MCP server: `python mcp_server.py` (stdio, must not write to stdout)
- API keys: set in `.env` or as shell env vars (see `.env.example`)
- Reports output to `reports/`
```

This is separate from the deep-research skill — AGENTS.md is for
coding tasks (tests, debugging, refactoring); the skill is for research
tasks.

### Usage

```bash
codex

# Explicit invocation (required — see agents/openai.yaml)
$deep-research  research BESS degradation and bidding strategies in CAISO

# Or reference the skill by description
use the deep-research skill to write a report on solid electrolyte
interphase formation mechanisms
```

Select the skill from the `/skills` browser if auto-detection doesn't
trigger. The skill presents the plan in chat and waits for "yes" before
gathering begins.

**Approval mode for research tasks:** research writes many intermediate
files. Set `approval_mode = "auto-edit"` in `config.toml` (already set
in the shipped config) so Codex edits notes and drafts without
per-file confirmation. Review the final report before accepting.

---

## Skill architecture

| File | Purpose |
|---|---|
| `SKILL-core.md` | Shared platform-agnostic playbook — integrity commandments, full MCP tool reference, source quality tiers, workflow Steps 0–7, source note format, LaTeX conventions. Uses abstract verbs only. |
| `SKILL-claude-code.md` | Claude Code overlay — verb → tool mapping, plan-mode flow, `AskUserQuestion` schema, `Agent` subagents. |
| `SKILL-opencode.md` | OpenCode overlay — verb → tool mapping, write-plan-then-confirm flow, `question` schema, `Task` subagents. |
| `SKILL-copilot.md` | Copilot overlay covering both CLI and VS Code — verb → tool mapping, prose-question flow, `/fleet` and `.agent.md` subagents, `.tasks.md` tracker. |
| `SKILL-codex.md` | Codex CLI overlay — verb → tool mapping, prose-question flow, Agents SDK subagents, `.tasks.md` tracker, `agents/openai.yaml` invocation policy. |

Each overlay's first instruction is to read `SKILL-core.md` from the
same directory. Both files **must** be installed together.

For Codex CLI, the skill directory must also contain
`agents/openai.yaml` (shipped in `agents/openai.yaml` at the repo root).

---

## Workflow summary

Full playbook in `SKILL-core.md`. In brief:

1. **Confirm** — format, length, depth mode, source count, source types
2. **Plan** — sub-questions with per-question queries, acceptance criteria, slug
3. **Gather** — parallel MCP calls per sub-question; up to 3 rounds
4. **Rank** — merge all results → `rank_and_filter` → deduplicated, scored, balanced corpus
5. **Read** — snippet scan; targeted full-text fetch for unanswered questions (Full mode only)
6. **Write** — incremental section-by-section draft from source notes
7. **Review** — citation coverage → URL verification → adversarial coherence
8. **Deliver** — final report + provenance sidecar; offer expansion options

---

## Tests

```bash
pytest tests/
```

29 pure-logic unit tests for the ranker: full-text gate, DOI dedup with
field merge, fuzzy title dedup, temporal bucketing, year extraction edge
cases, `top_n` boundary conditions, and end-to-end ranking on a mixed
multi-source corpus. Run automatically by the setup scripts when pytest
is available.

---

## Verifying the install

**1. Import smoke test:**

```bash
python -c "import sys; sys.path.insert(0,'.'); import mcp_server" >/dev/null
# Any stdout output = broken (corrupts the MCP JSON-RPC protocol)
```

**2. Live server check:**

```bash
python mcp_server.py
# Expected stderr:
# [INFO] deep_research: deep-research MCP starting (openalex=on, ss=off, ...)
# Server waits on stdin. Ctrl-C to exit.
```

**3. In-agent check:**

| Platform | Command |
|---|---|
| Claude Code | `/mcp` |
| OpenCode | `/mcp` |
| Copilot CLI | `/mcp show` |
| VS Code Copilot | Agent mode → tools icon → server list |
| Codex CLI | `/mcp` (also `/skills` for skill list) |

---

## Troubleshooting

**MCP tools not appearing**

- Confirm `python mcp_server.py` starts with nothing on stdout.
- Claude Code / OpenCode: verify the `cwd` or server path is absolute
  and correct.
- Copilot CLI: run `/mcp show`. Check the `deep-research` entry points
  to the right directory.
- VS Code: MCP tools are **only visible in Agent mode**. Check the mode
  dropdown. Click the **Start** button in `mcp.json` if servers haven't
  launched. If servers share a name with another configured server, VS
  Code will disable the less-specific one — check for name collisions
  under Extensions → `@mcp @installed`.
- All platforms: restart the agent after any MCP config change.

**`rank_and_filter` returns fewer sources than expected**

The full-text gate dropped abstract-only entries. Check stderr for
`Dropped N abstract-only / inaccessible sources`. To widen the pool:
add `from_year` to `search_crossref`, or lower `dedup_threshold` in
`config.yaml`.

**Unpaywall enrichment is slow**

The 8-worker concurrent enrichment is already active. Reduce
`max_results` in `search_crossref` or add `from_year` to shrink the
batch.

**`parse_pdf` returns empty string**

The PDF exceeded the 50 MB cap, or contains only scanned images without
OCR text. Note the URL as inaccessible in the source note and continue.

**`alphaxiv` tools fail with a connection or auth error**

Two possible causes:

- **Not authenticated:** alphaxiv requires OAuth 2.0 before any tools work.
  See the [alphaxiv authentication](#alphaxiv-authentication) section for
  per-platform steps. Tokens expire — re-run the auth command if you see 401 errors.
- **Server unreachable:** `api.alphaxiv.org` is temporarily down.
  Skip all three alphaxiv tools for this session and proceed with
  `search_openalex`, `search_semantic_scholar`, and `search_crossref`.

**LaTeX compilation fails**

Ensure `pdflatex` and `bibtex` are installed. The compile script must
run three pdflatex passes plus one bibtex pass — a single pass leaves
references unresolved. Check that every `\cite{key}` has a matching
`.bib` entry.

**Smoke test fails (stdout not clean)**

Isolate the offending call:

```bash
python -c "
import sys, io
buf = io.StringIO()
sys.stdout = buf
sys.path.insert(0, '.')
import mcp_server
sys.stdout = sys.__stdout__
print('Captured:', repr(buf.getvalue()))
"
```

Redirect any stray `print()` to `utils.log.info(...)`.

---

## File structure

```
deep-research/
│
├── mcp_server.py               MCP server — exposes pipeline as stdio tools
├── config.py                   Config loader (env var → .env → yaml → defaults)
├── config.yaml                 Local config — gitignored, never commit with live keys
├── config.example.yaml         YAML template — copy to config.yaml to start
├── .env.example                Secrets template — copy to .env and fill in values
├── utils.py                    Stderr logger + retryable_get
├── requirements.txt            Python dependencies
├── setup.sh                    Unix/macOS setup script
├── setup.ps1                   Windows PowerShell setup script
├── README.md                   This file
│
├── SKILL-core.md               Shared platform-agnostic skill playbook
├── SKILL-claude-code.md        Overlay for Claude Code
├── SKILL-opencode.md           Overlay for OpenCode
├── SKILL-copilot.md            Overlay for Copilot CLI + Copilot VS Code
│
├── opencode.json               OpenCode MCP config (project-scoped)
├── .copilot/
│   └── mcp-config.json         Copilot CLI MCP config (project-scoped)
├── .vscode/
│   └── mcp.json                VS Code Copilot MCP config (workspace-scoped)
├── .codex/
│   └── config.toml             Codex CLI MCP config in TOML (project-scoped, trusted projects)
├── agents/
│   └── openai.yaml             Codex skill metadata and invocation policy
│
├── sources/
│   ├── academic/
│   │   ├── openalex.py         Two-pass OA search; PDF gate on both passes
│   │   ├── semantic_scholar.py Citation graph, TLDR, single-call ref expansion
│   │   └── crossref_unpaywall.py DOI metadata + concurrent Unpaywall enrichment
│   └── web/
│       ├── wikipedia.py        REST summary API; real lead extracts
│       └── reddit_hn.py        HN (Algolia) + Reddit; graceful 403 degradation
│
├── retrieval/
│   ├── content_extractor.py    Jina → trafilatura → BS4; debug logging on failure
│   ├── jina_reader.py          URL → clean Markdown via r.jina.ai
│   └── pdf_parser.py           Streamed download (50 MB cap) + dual backend
│
├── analysis/
│   └── ranker.py               Full-text gate, DOI+fuzzy dedup with field merge,
│                               relevance scoring, temporal bucket balance
│
└── tests/
    └── test_ranker.py          29 pure-logic ranker unit tests
```
