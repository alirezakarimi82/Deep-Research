# DeepResearch Framework

A multi-source, agentic research pipeline that turns any question into a
fully-cited Markdown or LaTeX report. Runs inside **Claude Code**,
**OpenCode**, **GitHub Copilot CLI**, and **GitHub Copilot in VS Code**.

```
User request → Plan → Gather (MCP tools) → Rank → Retrieve → Synthesise → Report
```

---

## Platform compatibility

| Feature | Claude Code | OpenCode | Copilot CLI | Copilot VS Code |
|---|:---:|:---:|:---:|:---:|
| Local stdio MCP servers | ✅ | ✅ | ✅ | ✅ |
| Remote SSE MCP servers | ✅ | ✅ | ✅ | ✅ |
| Skill files (SKILL.md) | ✅ | ✅ | ✅ | ✅ |
| Structured `askUser` tool | ✅ | ✅ | prose only | prose only |
| Native plan mode | ✅ | — | ✅ (Shift+Tab) | — |
| Parallel subagents | ✅ (`Agent`) | ✅ (`Task`) | ✅ (`/fleet`) | limited |
| Native task tracker | ✅ | ✅ | — | — |
| `.tasks.md` fallback tracker | — | — | ✅ | ✅ |

> **Copilot prerequisite:** MCP is disabled by default in GitHub
> organizations. An org admin must enable it under
> Organization → Settings → Copilot → MCP before any MCP config file
> takes effect.

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
opencode               # OpenCode      — reads opencode.json
claude                 # Claude Code   — reads .mcp.json / .claude/mcp.json
copilot        # Copilot CLI   — reads .copilot/mcp-config.json
# VS Code: open workspace, switch Copilot Chat to agent mode (the ⚡ icon)

# 4. Verify MCP servers are live
/mcp                   # Claude Code
/mcp                   # OpenCode
/mcp show              # Copilot CLI
# VS Code: type / in Copilot Chat — deep-research tools appear in completions
```

---

## MCP pipeline tools

These tools are exposed by `mcp_server.py` and are identical on all
four platforms.

| Tool | Signature | Notes |
|---|---|---|
| `search_openalex` | `(query, max_results=20)` | 250 M+ works; two-pass (recent + seminal). Full-text PDF gate on **both** passes when API key is set. |
| `search_semantic_scholar` | `(query, max_results=20)` | AI TLDRs, citation graph, OA PDFs. Two-pass. |
| `search_crossref` | `(query, max_results=20, from_year=None)` | DOI metadata + **parallel** Unpaywall enrichment (8 concurrent workers). |
| `search_wikipedia` | `(query, max_results=5)` | Real article leads via REST API (not just snippets). |
| `search_hackernews` | `(query, max_results=10)` | Practitioner discussions via Algolia. |
| `search_reddit` | `(query, subreddit="all", max_results=10)` | Community knowledge; subreddit routing available. |
| `rank_and_filter` | `(sources_json, query, key_concepts_json, top_n=None)` | DOI-exact dedup with field-level merge → fuzzy title dedup → full-text gate → relevance score → temporal balance. `top_n` defaults to `analysis.max_sources_for_synthesis` in `config.yaml`. |
| `extract_content` | `(url)` | Jina Reader → trafilatura → BeautifulSoup fallback. |
| `parse_pdf` | `(url)` | **Streamed download, 50 MB hard cap**; pdfplumber → PyMuPDF fallback. |

**Server-side guarantees you can rely on:**

- Abstract-only and closed-access papers are dropped by the full-text
  gate before `rank_and_filter` returns them — no pre-filtering needed.
- DOI duplicates across sources are merged at the field level: the
  ranked result carries the PDF URL from OpenAlex, the TLDR from
  Semantic Scholar, and the venue from Crossref as a single entry.
- Web sources must carry either a URL or a ≥200-char snippet to pass
  the gate.
- `parse_pdf` returning empty string = 50 MB cap exceeded or no
  extractable text — treat as inaccessible and move on.

### External MCP servers

| Server | Type | Key tools |
|---|---|---|
| `alphaxiv` | remote SSE | `alphaxiv_embedding_similarity_search`, `alphaxiv_full_text_papers_search`, `alphaxiv_agentic_paper_retrieval`, `alphaxiv_get_paper_content`, `alphaxiv_answer_pdf_queries` |
| `ddgs` | local stdio | `ddgs_search_text`, `ddgs_search_news`, `ddgs_search_books`, `ddgs_extract_content` |
| `playwright` | local stdio | `browser_navigate`, `browser_snapshot` — last-resort JS-heavy page fallback only |

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
`config.example.yaml` → `config.yaml` if missing, runs an MCP server
import smoke test (verifies stdout is clean), and optionally runs the
29-test unit suite.

### Step 2 — API keys

All keys are optional but improve rate limits and unlock features.
**Preferred path: environment variables** — they override `config.yaml`
and keep secrets out of version control.

| Variable | Where to get | Effect |
|---|---|---|
| `UNPAYWALL_EMAIL` | Your own email, no registration needed | Polite-pool access, 100k OA PDF lookups/day |
| `SEMANTIC_SCHOLAR_KEY` | semanticscholar.org/product/api | 10k req/min (vs 100/5 min unauthenticated) |
| `OPENALEX_API_KEY` | openalex.org/api-key | Semantic embedding search + full-text PDFs |

**macOS / Linux:**
```bash
export UNPAYWALL_EMAIL="you@example.com"
export SEMANTIC_SCHOLAR_KEY="..."
export OPENALEX_API_KEY="..."
# Add to ~/.zshrc or ~/.bashrc to persist across sessions
```

**Windows (PowerShell):**
```powershell
$env:UNPAYWALL_EMAIL      = "you@example.com"
$env:SEMANTIC_SCHOLAR_KEY = "..."
$env:OPENALEX_API_KEY     = "..."
# For persistence across sessions:
[Environment]::SetEnvironmentVariable("UNPAYWALL_EMAIL","you@example.com","User")
```

**Fallback — `config.yaml`:** copy `config.example.yaml` to
`config.yaml` and fill in the top-level fields. `config.py` overlays
env vars over file values at runtime (env vars always win).
**Never commit `config.yaml` with live keys.**

### Step 3 — Ranker tuning (optional)

Edit the `analysis:` block in `config.yaml`. Changes take effect on
the next server restart.

```yaml
analysis:
  max_sources_for_synthesis: 30   # default top_n for rank_and_filter
  dedup_threshold: 0.85           # fuzzy title similarity cutoff (0–1)
  recent_years: 3                 # "recent" bucket: papers within N years
  seminal_threshold: 100          # "seminal" bucket: cited_by_count >= N
  recent_share: 0.40              # fraction of top_n drawn from recent bucket
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

# Global (available in all projects)
mkdir -p ~/.claude/skills/deep-research
cp SKILL-claude-code.md ~/.claude/skills/deep-research/SKILL.md
cp SKILL-core.md        ~/.claude/skills/deep-research/
```

### Usage

```
/deep-research  write a report on BESS degradation and bidding in CAISO
```

Plan mode activates automatically at Step 1 (`EnterPlanMode`). Confirm
the plan to begin gathering. Verify MCP servers with `/mcp`.

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
    "alphaxiv":      { "type": "remote", "url": "https://api.alphaxiv.org/mcp/v1" },
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

The skill directory name must match the `name:` frontmatter field
(`deep-research`).

### Usage

```
/deep-research  research solid electrolyte interphase formation mechanisms
```

Use the **Plan** agent tab (Tab) to review the plan before confirming.
Switch back to **Build** to begin gathering. Verify MCP with `:mcp`.
Toggle `/dcp` to reduce context on long Extensive-length runs.

---

## Platform setup — Copilot CLI

### Prerequisites

```bash
gh extension install github/gh-copilot
gh extension upgrade gh-copilot    # ensure 1.x or later
gh copilot --version
```

**Organization accounts:** an org admin must enable MCP under
Organization → Settings → Copilot → MCP.

### MCP configuration

The shipped `.copilot/mcp-config.json` is ready for project-scoped
use. For global:

```bash
cp .copilot/mcp-config.json ~/.copilot/mcp-config.json
# Edit the deep-research "cwd" to the absolute path of this directory
```

Config precedence (highest → lowest):
1. `--additional-mcp-config <path>` CLI flag
2. Project `.copilot/mcp-config.json`
3. User `~/.copilot/mcp-config.json`

Verify:
```
gh copilot chat
/mcp show
```

### Skill installation

Copilot CLI picks up skills from several directories, including
`.claude/skills/` — so Claude Code users are often already set up.

```bash
# Personal (all projects)
mkdir -p ~/.copilot/skills/deep-research
cp SKILL-copilot.md ~/.copilot/skills/deep-research/SKILL.md
cp SKILL-core.md    ~/.copilot/skills/deep-research/

# Project-scoped
mkdir -p .github/skills/deep-research
cp SKILL-copilot.md .github/skills/deep-research/SKILL.md
cp SKILL-core.md    .github/skills/deep-research/
```

Verify inside a session:
```
/skills list
/skills info deep-research
```

### Usage

```bash
gh copilot chat
/deep-research  research lithium dendrite suppression in solid-state batteries
```

Plan mode: **Shift+Tab** to enter, **Shift+Tab** again to switch to
autopilot and confirm. Use `/fleet` for broad topics requiring parallel
subagent branches (the skill triggers this automatically).

---

## Platform setup — Copilot in VS Code

### Prerequisites

- VS Code 1.99 or later (April 2025)
- GitHub Copilot + Copilot Chat extensions, signed in
- Agent mode: Copilot Chat panel → click the ⚡ icon

**Organization accounts:** same org admin MCP prerequisite as CLI.

### MCP configuration

The shipped `.vscode/mcp.json` is ready for workspace use:

```json
{
  "servers": {
    "deep-research": {
      "type": "stdio",
      "command": "python",
      "args": ["${workspaceFolder}/mcp_server.py"]
    },
    "alphaxiv": { "type": "sse",   "url": "https://api.alphaxiv.org/mcp/v1" },
    "ddgs":     { "type": "stdio", "command": "ddgs", "args": ["mcp"] },
    "playwright": {
      "type":    "stdio",
      "command": "npx",
      "args":    ["@playwright/mcp@latest", "--headless"]
    }
  }
}
```

For user-level config (all workspaces), open VS Code settings (JSON)
and add:

```json
{
  "mcp": {
    "servers": { ...same block... }
  }
}
```

Verify: Copilot Chat (agent mode) → type `/` → MCP tool names appear.

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

In Copilot Chat (agent mode ⚡):

```
/deep-research  comprehensive review of hydrogen storage materials
```

The skill presents the plan in chat and waits for "yes" before
gathering. Subagent branches on broad topics run sequentially (VS Code
agent mode has limited parallel support compared to Copilot CLI's
`/fleet`).

---

## Skill architecture

The skill is split into a shared core and thin platform overlays so
nothing is duplicated.

| File | Purpose |
|---|---|
| `SKILL-core.md` | Platform-agnostic playbook — integrity commandments, full MCP tool reference, source quality tiers, workflow Steps 0–7, source note format, LaTeX conventions. Uses abstract verbs only. |
| `SKILL-claude-code.md` | Claude Code overlay — verb → tool mapping, mandatory plan-mode flow, `AskUserQuestion` schema, `Agent` subagents. |
| `SKILL-opencode.md` | OpenCode overlay — verb → tool mapping, write-plan-then-confirm flow, `question` schema, `Task` subagents. |
| `SKILL-copilot.md` | Copilot overlay covering both CLI and VS Code — verb → tool mapping, prose-question flow, `/fleet` and `.agent.md` subagents, `.tasks.md` tracker. |

Each overlay's first instruction is to read `SKILL-core.md` from the
same directory. Both files **must** be installed together.

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
cases, `top_n` boundary conditions (including `top_n=0` and `top_n=1`),
and end-to-end ranking on a mixed multi-source corpus. Run automatically
by the setup scripts when pytest is available.

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
| OpenCode | `:mcp` |
| Copilot CLI | `/mcp show` |
| VS Code Copilot | Type `/` in chat panel → MCP tools appear in completions |

---

## Troubleshooting

**MCP tools not appearing**

- Confirm `python mcp_server.py` starts cleanly (stderr only, nothing
  on stdout).
- Claude Code / OpenCode: verify the `cwd` or server path in your MCP
  config is correct.
- Copilot (CLI or VS Code): confirm org MCP policy is enabled.
- Restart the agent after any MCP config change — servers register at
  startup.

**`rank_and_filter` returns fewer sources than expected**

The full-text gate dropped abstract-only entries. Check stderr for
`Dropped N abstract-only / inaccessible sources`. To widen the pool:
add `from_year` to `search_crossref`, or lower `dedup_threshold` in
`config.yaml` if near-duplicates are being over-collapsed.

**Unpaywall enrichment is slow**

The 8-worker concurrent enrichment is already active. If still slow,
reduce `max_results` in `search_crossref` or add `from_year` to shrink
the enrichment batch.

**`parse_pdf` returns empty string**

The PDF exceeded the 50 MB cap, or contains only scanned images without
OCR text. Note the URL as inaccessible in the source note and continue.

**`alphaxiv` tools fail with connection error**

The remote server at `api.alphaxiv.org` is temporarily unreachable.
Skip all three alphaxiv tools for this session and rely on
`search_openalex`, `search_semantic_scholar`, and `search_crossref`.

**LaTeX compilation fails**

Ensure `pdflatex` and `bibtex` are installed. The compile script in the
core must run three pdflatex passes plus one bibtex pass — running a
single pass will leave references unresolved. Check for missing `.bib`
entries (every `\cite{key}` must have a match).

**Smoke test fails (stdout not clean)**

Something in the import chain is calling `print()` to stdout. Isolate
it:

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

The output identifies the exact string. The most common fix is
redirecting a stray `print()` call in a source or analysis module to
`utils.log.info(...)`.

---

## File structure

```
deep-research/
│
├── mcp_server.py               MCP server — exposes pipeline as stdio tools
├── config.py                   Config loader (env var overlay over YAML)
├── config.yaml                 Local config — gitignored, never commit with live keys
├── config.example.yaml         Template — copy to config.yaml to start
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
