---
name: deep-research
description: >
  Run a thorough, source-heavy investigation on any topic and produce a
  fully-cited Markdown or LaTeX report. Use when the user asks for deep
  research, a comprehensive analysis, an in-depth report, or a
  multi-source investigation. Do NOT trigger for general coding tasks,
  debugging, or questions answerable from the codebase alone.
---

# Deep Research — Codex CLI Overlay

> **First action for this skill:** read the file `SKILL-core.md` in the
> same directory as this file. It contains the full playbook — integrity
> commandments, source tiers, workflow Steps 0–7, source note format,
> LaTeX conventions, and all MCP tool signatures. This overlay only:
> (a) maps the core's abstract verbs to Codex tools, (b) documents
> Codex-specific flow differences (no plan mode shortcut, prose
> questions, `.tasks.md` tracker), and (c) lists setup commands.

---

## Tool verb mapping (Codex CLI)

| Core verb | Codex CLI tool |
|---|---|
| `askUser` | Ask in natural language; wait for reply in chat |
| `readFile` | `read_file` or `shell` → `cat` |
| `writeFile` | `write_file` or `shell` → `tee` / `cat >` |
| `editFile` | `edit_file` or `shell` → patch / `sed` |
| `runShell` | `shell` (sandbox-aware; see Approval mode note below) |
| `webFetch` | `shell` → `curl -sL <url>` or `ddgs_extract_content` |
| `webSearch` | `ddgs_search_text` / `ddgs_search_news` (primary) |
| `taskTracker` | `.tasks.md` file in project root — see below |
| `spawnSubagent` | OpenAI Agents SDK multi-agent handoff — see below |
| `planMode` | **not available** — write plan file, present in chat, ask for confirmation |

All MCP tool names (`search_openalex`, `rank_and_filter`, `extract_content`,
etc.) are platform-agnostic and identical across Codex, Claude Code,
OpenCode, and Copilot.

> **Approval mode:** Codex CLI runs in one of three sandbox modes:
> `suggest` (shows diffs for approval), `auto-edit` (edits files
> without confirmation), or `full-auto` (edits + runs shell commands).
> For research tasks that write many intermediate files, `auto-edit` is
> recommended. Run `codex --approval-mode auto-edit` or set
> `approval_mode = "auto-edit"` in `~/.codex/config.toml`.

---

## Codex-specific flow bits

### Step 0 — Gathering preferences

Codex CLI has no structured-choice widget. Ask the five preference
questions as a single prose message and wait for a reply:

```
Before I start, quick questions:

1. Output format — Markdown (default) or LaTeX + PDF?
2. Length — Brief 5–8 pages, Standard 12–18 (default), Detailed 25–35,
   or Extensive 40+?
3. Depth — Fast: snippets only (default) or Full: targeted full-text fetch?
4. Top sources — 15, 30 (default), or 50?
5. Source types — Academic papers, Web/industry (both default), News, Books?

Reply with choices or just say "go" for all defaults.
```

### Step 1 — Plan (no keyboard shortcut)

Codex CLI has no plan-mode shortcut. Write the plan file to
`reports/.plans/<slug>.md` using `write_file` or `shell`, then
present its contents in chat and ask:

```
Here is my research plan. Reply "yes" to proceed or tell me what to adjust.
```

Wait for confirmation before Step 2.

### Task tracking — `.tasks.md`

Codex CLI has no native task-tracker tool. Use a Markdown file at the
project root:

```
shell("cat > .tasks.md << 'EOF'\n# Research Tasks\n\n- [ ] Stage 2: Parallel search\n- [ ] Stage 3: Rank and filter\n- [ ] Stage 4: Two-pass read\n- [ ] Write draft (incremental)\n- [ ] Unified review pass\n- [ ] Deliver\nEOF")
```

Update by replacing `[ ]` with `[x]` via `edit_file` or `shell` →
`sed -i` as each stage completes.

### Subagents — Agents SDK

For the core playbook's §Subagent split strategy, Codex integrates
with the OpenAI Agents SDK for multi-agent handoffs. In practice the
lightest approach for research is to run the two branches sequentially
within the same session, since Codex's context window (200K) is large
enough to hold both result sets before ranking.

If you are running Codex programmatically via the Agents SDK, spawn
two Codex agent instances with the academic and web tool subsets
respectively, collect their staging files, merge, and pass to
`rank_and_filter` in the main agent.

### Step 7 — Next steps

Ask in natural language:

```
Report delivered to reports/<slug>.md.

Options:
  1. Done (keep as-is)
  2. Expand to a longer length
  3. Deepen a specific section
  4. Follow-up query on an Open Questions gap
  5. Convert format

Reply with a number or describe what you'd like.
```

---

## MCP server verification

After starting a Codex session:

```
/mcp          lists all configured servers and tools
/skills       browse available skills; select this one with $deep-research
```

Check alphaxiv OAuth status:

```
codex mcp show alphaxiv
```

---

## Setup checklist

1. **Install Python dependencies** (if not already done):
   ```bash
   bash setup.sh        # Unix/macOS
   .\setup.ps1          # Windows
   ```

2. **Set API keys** — add to `.env` in the project root (preferred)
   or export as shell env vars before launching `codex`:
   ```bash
   export UNPAYWALL_EMAIL="you@example.com"
   export SEMANTIC_SCHOLAR_KEY="your_key_here"
   export OPENALEX_API_KEY="your_key_here"
   ```

3. **Register MCP servers** — the shipped `.codex/config.toml` in
   this repo is ready for project-scoped use (trusted projects only).
   For global setup, copy to `~/.codex/config.toml`.
   Or register interactively:
   ```bash
   codex mcp add deep-research -- python /absolute/path/to/mcp_server.py
   codex mcp add ddgs -- ddgs mcp
   codex mcp add alphaxiv --url https://api.alphaxiv.org/mcp/v1
   ```

4. **Authenticate alphaxiv** (OAuth, one-time per machine):
   ```bash
   codex mcp login alphaxiv
   ```

5. **Install the skill files**:
   ```bash
   # Personal (all projects)
   mkdir -p ~/.codex/skills/deep-research
   cp SKILL-codex.md     ~/.codex/skills/deep-research/SKILL.md
   cp SKILL-core.md      ~/.codex/skills/deep-research/SKILL-core.md
   cp agents/openai.yaml ~/.codex/skills/deep-research/agents/openai.yaml

   # Project-scoped (this repo, trusted project required)
   mkdir -p .codex/skills/deep-research/agents
   cp SKILL-codex.md     .codex/skills/deep-research/SKILL.md
   cp SKILL-core.md      .codex/skills/deep-research/SKILL-core.md
   cp agents/openai.yaml .codex/skills/deep-research/agents/openai.yaml
   ```
   Restart Codex after installing. Verify with `/skills`.

6. **Optionally add an `AGENTS.md`** to the project root to give Codex
   always-on context about this repo (how to run tests, venv path,
   Python version). The skill handles the research workflow; `AGENTS.md`
   handles project-level facts.

---

## Reminders specific to Codex CLI

- MCP config is TOML, not JSON. Syntax errors (missing quotes, wrong
  bracket style) silently break server registration. Validate with
  `codex mcp list` after editing.
- The `.codex/config.toml` project scope only works in **trusted**
  projects. Trust a project with `codex trust` or via the Codex app.
- If a stdio MCP server isn't starting, check that the command is on
  the `PATH` Codex inherits. Use an absolute path in `config.toml` if
  in doubt. Increase `startup_timeout_sec` for slow-starting servers.
- `parse_pdf` returning empty string means the 50 MB cap was hit or
  the PDF is scanned-only. Note as inaccessible and continue.
- alphaxiv uses SSE transport; the `url =` form in `config.toml`
  handles this correctly.
- If alphaxiv is unreachable, skip its three tools and proceed with
  `search_openalex`, `search_semantic_scholar`, and `search_crossref`.
