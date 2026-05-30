# DeepResearch Framework

A multi-source, agentic research pipeline that turns a question into a fully cited Markdown or LaTeX report. The repository is designed to run inside Claude Code, OpenCode, GitHub Copilot CLI, GitHub Copilot in VS Code, and Codex CLI.

> User request → Plan → Gather (MCP tools) → Rank → Retrieve → Synthesise → Report

## What this repo provides

- A shared MCP server (`mcp_server.py`) that exposes the research pipeline as tools.
- A shared core skill (`SKILL-core.md`) plus platform-specific overlays.
- Platform configs and setup scripts for the supported agent environments.
- Local config templates for Python, MCP, and research output under `reports/`.

## Platform compatibility

| Feature | Claude Code | OpenCode | Copilot CLI | Copilot VS Code | Codex CLI |
|---|:---:|:---:|:---:|:---:|:---:|
| Local stdio MCP servers | ✅ | ✅ | ✅ | ✅ | ✅ |
| Remote SSE MCP servers | ✅ | ✅ | ✅ | ✅ | ✅ |
| Skill files (`SKILL.md`) | ✅ | ✅ | ✅ | ✅ | ✅ |
| Codex skill metadata (`openai.yaml`) | — | — | — | — | ✅ |
| Project context (`AGENTS.md`) | ✅ | ✅ | — | — | ✅ |
| MCP config format | JSON | JSON | JSON | JSON | TOML |
| Structured `askUser` tool | ✅ | ✅ | prose only | prose only | prose only |
| Native plan mode | ✅ | — | ✅ (Shift+Tab) | — | — |
| Parallel subagents | ✅ (`Agent`) | ✅ (`Task`) | ✅ (`/fleet`) | limited | Agents SDK |
| Native task tracker | ✅ | ✅ | — | — | — |
| `.tasks.md` fallback tracker | — | — | ✅ | ✅ | ✅ |

> Copilot org prerequisite: MCP is disabled by default for Copilot Business and Enterprise plans. An org admin must enable it under Organization → Settings → Copilot → MCP. Individual Free and Pro plans have MCP available without any additional toggle.

## Quick start

```bash
# 1. Install Python dependencies and local templates
bash setup.sh          # macOS / Linux
.\setup.ps1           # Windows PowerShell

# 2. Set API keys (optional, but improves rate limits and coverage)
export UNPAYWALL_EMAIL="you@example.com"
export SEMANTIC_SCHOLAR_KEY="..."    # optional
export OPENALEX_API_KEY="..."         # optional

# 3. Start your agent
claude                 # Claude Code
codex                  # Codex CLI
opencode               # OpenCode
copilot                # Copilot CLI
# VS Code: open the workspace, then Copilot Chat → mode dropdown → Agent

# 4. Verify MCP servers are live
/mcp                   # Claude Code
/mcp                   # Codex CLI
/mcp                   # OpenCode
/mcp show              # Copilot CLI
# VS Code: Agent mode → tools icon → server list
```

## Installation — all platforms

The repo includes the source files needed for all supported environments. The setup scripts install Python dependencies, create a `.venv`, prepare `reports/`, copy `.env.example` to `.env` when needed, and provide platform-specific skill/config guidance.

### Python environment

Use Python 3.10 or later.

```bash
python -m venv .venv
source .venv/bin/activate   # macOS / Linux
# or:
.\.venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

### Local research config

Secrets can be provided either through `.env` or through shell environment variables:

- `UNPAYWALL_EMAIL`
- `SEMANTIC_SCHOLAR_KEY`
- `OPENALEX_API_KEY`

The pipeline works without API keys, but external sources and rate limits are better with them.

## Platform setup — Codex CLI

### MCP configuration

Codex uses TOML for MCP config. Project-scoped config lives in `.codex/config.toml` in a trusted project. Global config lives in `~/.codex/config.toml`.

Register the servers interactively:

```bash
codex mcp add deep-research -- python /absolute/path/to/mcp_server.py
codex mcp add ddgs -- ddgs mcp
codex mcp add alphaxiv --url https://api.alphaxiv.org/mcp/v1
```

If you prefer project-scoped config, trust the repository first:

```bash
codex trust
```

Then verify the servers:

```bash
/mcp
```

### Skill installation

Codex skills go in `~/.codex/skills/` for personal use or `.codex/skills/` for a trusted project. This repository ships the Codex overlay at `SKILL-codex.md`, the shared playbook at `SKILL-core.md`, and Codex skill metadata at `openai.yaml`.

```bash
# Personal install
mkdir -p ~/.codex/skills/deep-research/
cp SKILL-codex.md ~/.codex/skills/deep-research/SKILL.md
cp SKILL-core.md ~/.codex/skills/deep-research/SKILL-core.md
cp openai.yaml ~/.codex/skills/deep-research/openai.yaml

# Project-scoped install
mkdir -p .codex/skills/deep-research/
cp SKILL-codex.md .codex/skills/deep-research/SKILL.md
cp SKILL-core.md .codex/skills/deep-research/SKILL-core.md
cp openai.yaml .codex/skills/deep-research/openai.yaml
```

Restart Codex after installing, then verify with `/skills`.

### Usage

```bash
codex
$deep-research research BESS degradation and bidding strategies in CAISO
```

The skill presents the plan in chat and waits for confirmation before gathering begins.

### Approval mode

For research tasks, `auto-edit` is usually the best fit because the workflow writes many intermediate files. Set it in `~/.codex/config.toml` or `.codex/config.toml` if your local setup does not already do so.

## Platform setup — Claude Code

Claude Code uses JSON MCP config and the shared skill pair:

```bash
cp SKILL-claude-code.md ~/.claude/skills/deep-research/SKILL.md
cp SKILL-core.md ~/.claude/skills/deep-research/SKILL-core.md
```

Use `/mcp` to verify server registration and `/deep-research` to invoke the skill.

## Platform setup — OpenCode

OpenCode reads `opencode.json` from the project root automatically. Install the overlay and shared core skill, then verify with `/mcp` and `/skills`.

## Platform setup — Copilot CLI

Copilot CLI uses `.copilot/mcp-config.json` plus the Copilot overlay. Install the skill in `~/.copilot/skills/` or `.github/skills/`, then use `/mcp show` and `/skills`.

## Platform setup — Copilot in VS Code

Open the workspace in VS Code, switch Copilot Chat to **Agent** mode, and use the MCP tools icon to confirm the registered servers. The workspace-scoped config lives in `.vscode/mcp.json`.

## MCP pipeline tools

The MCP server exposes the same tools on every platform:

| Tool | Signature | Notes |
|---|---|---|
| `search_openalex` | `(query, max_results=20)` | Two-pass search with PDF gating when API keys are available. |
| `search_semantic_scholar` | `(query, max_results=20)` | Citation graph, TLDRs, and OA PDFs. |
| `search_crossref` | `(query, max_results=20, from_year=None)` | DOI metadata plus Unpaywall enrichment. |
| `search_wikipedia` | `(query, max_results=5)` | Real article leads via the REST API. |
| `search_hackernews` | `(query, max_results=10)` | Practitioner discussions via Algolia. |
| `search_reddit` | `(query, subreddit="all", max_results=10)` | Community knowledge with subreddit routing. |
| `rank_and_filter` | `(sources_json, query, key_concepts_json, top_n=None)` | DOI dedup, fuzzy title dedup, relevance scoring, and temporal balancing. |
| `extract_content` | `(url)` | Jina Reader → trafilatura → BeautifulSoup fallback. |
| `parse_pdf` | `(url)` | Streamed PDF parsing with a 50 MB cap. |

## External MCP servers

The repo also supports external MCP servers such as `alphaxiv`, `ddgs`, and `playwright`. `alphaxiv` uses OAuth and may require a first-use authorization flow depending on the platform.

## Skill architecture

| File | Purpose |
|---|---|
| `SKILL-core.md` | Shared platform-agnostic playbook for the full research workflow. |
| `SKILL-claude-code.md` | Claude Code overlay. |
| `SKILL-opencode.md` | OpenCode overlay. |
| `SKILL-copilot.md` | Copilot CLI and Copilot VS Code overlay. |
| `SKILL-codex.md` | Codex CLI overlay. |
| `openai.yaml` | Codex skill metadata and invocation policy. |

Each overlay’s first instruction is to read `SKILL-core.md` from the same directory.

## Workflow summary

1. Confirm the user’s preferences: format, length, depth, source count, and source types.
2. Plan the sub-questions and acceptance criteria.
3. Gather sources in parallel through the MCP tools.
4. Rank and deduplicate the corpus.
5. Read snippets first, then fetch targeted full text where needed.
6. Write the draft incrementally.
7. Review citations, coverage, and coherence.
8. Deliver the final report with provenance and offer follow-up options.

## Tests

```bash
pytest tests/
```

The test suite focuses on the ranker and the source-merging logic.

## Verifying the install

```bash
python -c "import sys; sys.path.insert(0,'.'); import mcp_server"
python mcp_server.py
```

The import check should produce no stdout. The server should start cleanly and wait on stdin.

## Troubleshooting

- If MCP tools do not appear, confirm the config file path is correct for the platform.
- If Codex does not load the skill, verify the skill directory contains `SKILL.md`, `SKILL-core.md`, and `openai.yaml`.
- If a server command is not found, use an absolute path or make sure it is on the PATH inherited by the agent.
- Restart the agent after any MCP or skill change.

## File structure

```text
deep-research/
├── mcp_server.py
├── config.py
├── config.yaml
├── config.example.yaml
├── .env.example
├── utils.py
├── requirements.txt
├── setup.sh
├── setup.ps1
├── README.md
├── SKILL-core.md
├── SKILL-claude-code.md
├── SKILL-opencode.md
├── SKILL-copilot.md
├── SKILL-codex.md
├── openai.yaml
├── opencode.json
├── .copilot/
│   └── mcp-config.json
├── .vscode/
│   └── mcp.json
├── .codex/
│   └── config.toml
└── tests/
    └── test_ranker.py
```
