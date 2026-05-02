---
name: deep-research
description: Run a thorough, source-heavy investigation on any topic. Use when the user asks for deep research, a comprehensive analysis, an in-depth report, or a multi-source investigation. Produces a cited research brief with provenance tracking.
---

# Deep Research — Copilot Overlay

> **First action for this skill:** read the file `SKILL-core.md` in the
> same directory. It contains the full playbook — integrity commandments,
> source tiers, workflow Steps 0–7, source note format, and LaTeX
> conventions. This overlay only (a) maps the core's abstract verbs to
> Copilot-native tools, and (b) pins down the Copilot-specific flow bits
> for plan mode, subagents, task tracking, and user confirmation. Once
> you have read the core, apply the mapping below and follow its workflow
> verbatim.
>
> This overlay covers **both** surfaces:
> - **Copilot CLI** (`copilot` in the terminal)
> - **Copilot in VS Code** (agent mode in the Copilot Chat panel)
> Where behavior differs between the two, it is called out explicitly.

---

## Verb → tool mapping

| Core verb | Copilot CLI | Copilot VS Code |
|---|---|---|
| `askUser` | Ask in natural language; wait for reply | Ask in natural language; wait for reply |
| `readFile` | `read_file` / shell `cat` | `read_file` |
| `writeFile` | `create_file` / shell `tee` | `create_file` |
| `editFile` | `replace_string_in_file` / shell patch | `replace_string_in_file` |
| `runShell` | `run_command` | `run_in_terminal` |
| `webFetch` | `fetch_webpage` (if available) or `ddgs_extract_content` | `fetch_webpage` or `ddgs_extract_content` |
| `webSearch` | `ddgs_search_text` (primary), or `websearch` if enabled | `ddgs_search_text` or VS Code built-in search |
| `taskTracker` | Write/update `.tasks.md` in the project root | Write/update `.tasks.md` in the project root |
| `spawnSubagent` | `/fleet` command (see below) | Custom `.agent.md` subagent (see below) |
| `planMode` | Shift+Tab → plan; Shift+Tab → autopilot | Present plan in chat; ask for confirmation |

All MCP tool names (`search_openalex`, `rank_and_filter`, `extract_content`,
etc.) are identical across hosts — use them exactly as written in the core.

> **`websearch` availability:** in VS Code, Copilot's built-in web search
> is available in agent mode. In Copilot CLI it depends on your provider;
> if unavailable, use `ddgs_search_text` and `ddgs_search_news` from the
> ddgs MCP server as the primary web-search path.

---

## Copilot-specific flow bits

### Step 0 — Gathering preferences (no structured-choice tool)

Neither Copilot CLI nor Copilot VS Code has a dedicated structured-choice
widget like `AskUserQuestion` or `question`. Instead, ask the five
preference questions as a single prose message and wait for the user's
reply before proceeding.

Example message:

```
Before I start, a few quick questions:

1. Output format — Markdown, or LaTeX with PDF compilation?
   Default: Markdown.

2. Report length — Brief (5–8 pages), Standard (12–18 pages),
   Detailed (25–35 pages), or Extensive (40+ pages)?
   Default: Standard.

3. Depth — Fast (snippets only) or Full (targeted full-text fetch)?
   Default: Fast.

4. How many top sources to synthesise — 15, 30, or 50?
   Default: 30.

5. Source types to include (pick any combination) — Academic papers,
   Web/industry, News, Books?
   Default: Academic + Web/industry.

Reply with your choices or just say "go" to accept all defaults.
```

Record all answers before proceeding to Step 1.

### Step 1 — Plan mode

**Copilot CLI:** press Shift+Tab to enter plan mode before beginning
any analysis. Outline the sub-questions, per-question queries, strategy,
and slug. Write the plan file with `create_file`. Then press Shift+Tab
again to switch to autopilot mode and ask the user to confirm the plan
before proceeding to Step 2. Do not proceed without explicit confirmation.

**Copilot VS Code:** there is no keyboard plan-mode shortcut in the chat
panel. Instead, write the plan file, present its contents in chat, and
ask the user explicitly: "Does this plan look right? Reply 'yes' to
proceed, or tell me what to adjust." Wait for confirmation before
Step 2.

### Task tracking — use a `.tasks.md` file

Neither Copilot surface has a dedicated task-tracker tool. Track
progress in a plain Markdown file at the project root instead:

```
create_file(".tasks.md", content="")   -- or write via shell
```

Structure:

```markdown
# Research Tasks

- [ ] Stage 2: Parallel search
- [ ] Stage 3: Rank and filter
- [ ] Stage 4: Two-pass read
- [ ] Write draft (incremental)
- [ ] Unified review pass
- [ ] Deliver
```

Update by replacing `[ ]` with `[x]` using `replace_string_in_file` as
each stage completes. Reading `.tasks.md` at any point gives the current
state without consuming extra context.

### Subagents — Copilot CLI: `/fleet`

For the core's §Subagent split strategy, use `/fleet` to run two
branches in parallel:

```
/fleet
  Branch A (academic): run search_openalex, search_semantic_scholar,
    search_crossref, all 3 alphaxiv tools for each sub-question.
    Write results to reports/.staging/<slug>/academic-results.json.

  Branch B (web/news): run search_wikipedia, search_hackernews,
    search_reddit, ddgs_search_text, ddgs_search_news.
    Write results to reports/.staging/<slug>/web-results.json.
```

After `/fleet` completes, read both staging files, merge the result
lists, and pass the merged list to `rank_and_filter`.

### Subagents — Copilot VS Code: `.agent.md` custom agents

In VS Code agent mode, use a custom agent profile for each branch.
Create `.github/agents/deep-research-academic.agent.md` and
`.github/agents/deep-research-web.agent.md` (you can delete them after
the session). Invoke them from the agents dropdown in the Copilot Chat
panel or by typing `@deep-research-academic` in the prompt.

Alternatively, if your VS Code version supports it, run both branches
sequentially in the same session — VS Code agent mode is not yet as
parallel-friendly as Copilot CLI's `/fleet`.

### Step 7 — Next steps

Ask in natural language:

```
The report is ready at reports/<slug>.md.

Would you like to:
  1. Leave this as-is (recommended)
  2. Expand to a longer length target
  3. Deepen one or more sections
  4. Run a targeted follow-up on an Open Questions gap
  5. Convert to a different output format

Reply with a number or describe what you'd like.
```

---

## Skill installation

### Copilot CLI

Skills are discovered from:
- `~/.copilot/skills/<skill-name>/SKILL.md` (personal, all projects)
- `.github/skills/<skill-name>/SKILL.md` (project-scoped)
- `.claude/skills/<skill-name>/SKILL.md` (also picked up automatically)
- `.agents/skills/<skill-name>/SKILL.md`

**Important:** Copilot automatically picks up skills in `.claude/skills/`
— if you already have this skill installed for Claude Code there, Copilot
will find it without any extra steps.

To install manually:
```bash
mkdir -p ~/.copilot/skills/deep-research
cp SKILL-copilot.md ~/.copilot/skills/deep-research/SKILL.md
cp SKILL-core.md    ~/.copilot/skills/deep-research/SKILL-core.md
```

Verify from inside a Copilot CLI session:
```
/skills list          -- should show deep-research
/skills info deep-research
```

Invoke explicitly with:
```
/deep-research research battery degradation in grid storage
```

### Copilot VS Code

Skills are read from `.github/skills/` in the open workspace or from
`~/.config/copilot/skills/` (global). Same SKILL.md format.

```bash
mkdir -p .github/skills/deep-research
cp SKILL-copilot.md .github/skills/deep-research/SKILL.md
cp SKILL-core.md    .github/skills/deep-research/SKILL-core.md
```

Invoke in the Copilot Chat panel (agent mode):
```
/deep-research  research lithium iron phosphate degradation mechanisms
```

Or reference the skill in your prompt:
```
Use the deep-research skill to write a report on BESS arbitrage in CAISO.
```

---

## Setup checklist

1. **Install Python dependencies** (if not already done):
   ```bash
   bash setup.sh        # Unix/macOS
   .\setup.ps1          # Windows PowerShell
   ```

2. **Set API keys as environment variables:**
   ```bash
   export UNPAYWALL_EMAIL="you@example.com"
   export SEMANTIC_SCHOLAR_KEY="..."       # optional
   export OPENALEX_API_KEY="..."           # optional
   ```
   Set before launching `copilot` so child processes inherit them.

3. **Register MCP servers** — edit or create
   `~/.copilot/mcp-config.json` (global) or `.copilot/mcp-config.json`
   (project-scoped; takes precedence). The shipped `.copilot/mcp-config.json`
   in this repo is ready to use for project-scoped setup. For global,
   copy it to `~/.copilot/mcp-config.json`.

4. **For VS Code:** configure `.vscode/mcp.json` (workspace-scoped).
   The shipped `.vscode/mcp.json` in this repo is ready to use.

5. **Install the skill files** as described above.

6. **Verify** from inside a Copilot CLI session:
   ```
   /mcp show             -- all configured MCP servers and their tools
   /skills list          -- should show deep-research
   ```
   From VS Code: open Copilot Chat, switch to agent mode (the ⚡ icon),
   type `/` — `deep-research` should appear in the skill completions.

---

## Reminders specific to Copilot

- MCP is **disabled by default in GitHub organizations**. An org admin
  must enable it under Organization → Settings → Copilot → MCP before
  `/mcp add` or the config file takes effect.
- Copilot CLI MCP config precedence (highest → lowest):
  `--additional-mcp-config` flag → project `.copilot/mcp-config.json` →
  user `~/.copilot/mcp-config.json`.
- When compiling LaTeX with `run_command` / `run_in_terminal`, pdflatex
  must run **three times** plus one `bibtex` pass — the core's compile
  script handles this.
- If `parse_pdf` returns an empty string for a large PDF, the file
  exceeded the 50 MB streamed download cap. Note the URL as inaccessible
  in the source note and continue.
- The alphaxiv MCP server is remote. If it is unreachable, skip all
  three alphaxiv search tools and proceed with `search_openalex`,
  `search_semantic_scholar`, and `search_crossref` only.
