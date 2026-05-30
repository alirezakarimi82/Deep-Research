---
name: deep-research
description: >
  Run a thorough, source-heavy investigation on any topic and produce a
  fully cited Markdown or LaTeX report. Use when the user asks for deep
  research, a comprehensive analysis, an in-depth report, or a
  multi-source investigation. Do NOT trigger for general coding tasks,
  debugging, or questions answerable from the codebase alone.
---

# Deep Research — Codex CLI Overlay

> **First action for this skill:** read `SKILL-core.md` in the same directory.
> It contains the full playbook — integrity rules, source tiers, workflow
> Steps 0–7, note format, LaTeX conventions, and MCP tool signatures.

This overlay only:
1. maps the core verbs to Codex tools,
2. documents Codex-specific flow differences, and
3. lists setup and verification commands.

## Tool verb mapping (Codex CLI)

| Core verb | Codex CLI tool |
|---|---|
| `askUser` | Ask in natural language and wait for the reply |
| `readFile` | `read_file` or `shell` → `cat` |
| `writeFile` | `write_file` or `shell` → `tee` / `cat >` |
| `editFile` | `edit_file` or `shell` → patch / `sed` |
| `runShell` | `shell` |
| `webFetch` | `shell` → `curl -sL` or `ddgs_extract_content` |
| `webSearch` | `ddgs_search_text` / `ddgs_search_news` |
| `taskTracker` | `.tasks.md` file in the project root |
| `spawnSubagent` | OpenAI Agents SDK handoff |
| `planMode` | Not available — write a plan file, show it in chat, and ask for confirmation |

All MCP tool names (`search_openalex`, `rank_and_filter`, `extract_content`, and so on) are platform-agnostic and identical across Codex, Claude Code, OpenCode, and Copilot.

## Approval mode

Codex CLI runs in three sandbox modes: `suggest`, `auto-edit`, and `full-auto`.
For research work that creates many intermediate files, `auto-edit` is usually the best fit.

## Step 0 — Gather preferences

Codex CLI has no structured-choice widget. Ask the five preference questions as one prose message and wait for a reply:

```text
Before I start, quick questions:
1. Output format — Markdown (default) or LaTeX + PDF?
2. Length — Brief 5–8 pages, Standard 12–18 (default), Detailed 25–35, or Extensive 40+?
3. Depth — Fast: snippets only (default) or Full: targeted full-text fetch?
4. Top sources — 15, 30 (default), or 50?
5. Source types — Academic papers, Web/industry (both default), News, Books?

Reply with choices or just say "go" for all defaults.
```

## Step 1 — Plan

Codex CLI has no plan-mode shortcut. Write the plan file under `reports/.plans/` using the research slug, then present its contents in chat and ask for confirmation.

Use a filename such as:

- `reports/.plans/{slug}.md`

Then say:

```text
Here is my research plan. Reply "yes" to proceed or tell me what to adjust.
```

Wait for confirmation before moving to Step 2.

## Task tracking — `.tasks.md`

Codex CLI has no native task-tracker tool. Keep a Markdown checklist in the project root:

```bash
cat > .tasks.md << 'EOF'
# Research Tasks

- [ ] Stage 2: Parallel search
- [ ] Stage 3: Rank and filter
- [ ] Stage 4: Two-pass read
- [ ] Write draft (incremental)
- [ ] Unified review pass
- [ ] Deliver
EOF
```

Update the file as each stage completes.

## Subagents — Agents SDK

For broad topics, use the core playbook’s subagent split strategy through the OpenAI Agents SDK. A practical pattern is to run the academic and web branches in parallel, collect their staging files, merge them, and pass the merged set to `rank_and_filter`.

Keep the branch outputs in staging files and avoid overwriting the shared draft until ranking is complete.

## Step 7 — Next steps

At delivery, ask in natural language:

```text
Report delivered to reports/{slug}.md. Options:
1. Done (keep as-is)
2. Expand to a longer length
3. Deepen a specific section
4. Follow up on an open question
5. Convert format

Reply with a number or describe what you'd like.
```

## MCP server verification

After starting a Codex session:

```bash
/mcp     # list configured servers and tools
/skills  # browse available skills; select this one with $deep-research
```

Check alphaxiv OAuth status:

```bash
codex mcp show alphaxiv
```

## Setup checklist

1. **Install Python dependencies** if needed:

   ```bash
   bash setup.sh
   # or on Windows:
   .\setup.ps1
   ```

2. **Set API keys** — add them to `.env` in the project root, or export them as shell variables before launching `codex`:

   ```bash
   export UNPAYWALL_EMAIL="you@example.com"
   export SEMANTIC_SCHOLAR_KEY="your_key_here"
   export OPENALEX_API_KEY="your_key_here"
   ```

3. **Register MCP servers** — use `codex mcp add` for a fresh setup, or keep a `.codex/config.toml` in a trusted project and `~/.codex/config.toml` for global use.

   ```bash
   codex mcp add deep-research -- python /absolute/path/to/mcp_server.py
   codex mcp add ddgs -- ddgs mcp
   codex mcp add alphaxiv --url https://api.alphaxiv.org/mcp/v1
   ```

4. **Authenticate alphaxiv** when prompted:

   ```bash
   codex mcp login alphaxiv
   ```

5. **Optional project context** — add an `AGENTS.md` to the repo root with repo-specific facts such as test commands, virtualenv location, and where reports are written.

## Reminders specific to Codex CLI

- Codex MCP config is TOML, not JSON.
- Use absolute paths in MCP config when a server command is not picked up correctly.
- `codex trust` is required before a trusted-project `.codex/config.toml` will be read.
- `openai.yaml` belongs next to the skill files and controls invocation policy.
- If `parse_pdf` returns an empty string, treat the source as inaccessible and move on.
- Restart the agent after any MCP or skill change.
