---
name: deep-research
description: Run a thorough, source-heavy investigation on any topic. Use when the user asks for deep research, a comprehensive analysis, an in-depth report, or a multi-source investigation. Produces a cited research brief with provenance tracking.
compatibility: opencode
---

# Deep Research — OpenCode Overlay

> **First action for this skill:** use `read` on the file `SKILL-core.md`
> (same directory as this overlay). It contains the integrity rules,
> tool reference, workflow, and output conventions for the entire
> skill. This overlay only translates the core's abstract verbs into
> OpenCode tools and pins down the OpenCode-specific flow bits (no
> formal plan mode, `question` schema with `header`, `Task`-based
> subagents, `websearch` opt-in).
>
> Once you have read the core, apply the mapping below and follow the
> workflow there verbatim.

---

## Verb → tool mapping (OpenCode)

| Core verb | OpenCode tool |
|---|---|
| `askUser` | `question` |
| `readFile` | `read` |
| `writeFile` | `write` |
| `editFile` | `edit` |
| `runShell` | `bash` |
| `webFetch` | `webfetch` |
| `webSearch` | `websearch` *(see opt-in note below)* |
| `taskTracker` | `todowrite` |
| `spawnSubagent` | `Task` (with `@general` subagent) |
| `planMode` | **not available** — see flow note below |

> **`websearch` opt-in:** only available with the OpenCode Zen provider
> or when `OPENCODE_ENABLE_EXA=1` is set in the environment
> (`OPENCODE_ENABLE_EXA=1 opencode`). If unavailable, fall back to
> `ddgs_search_text` / `ddgs_search_news` from the ddgs MCP server.

All MCP tool names (`search_openalex`, `rank_and_filter`, `extract_content`,
etc.) are identical across hosts — use them exactly as written in the core.

---

## OpenCode-specific flow bits

### Step 1 — No plan mode; write-then-confirm instead

OpenCode has no formal plan mode. Instead:

1. Write the plan file to `reports/.plans/<slug>.md` with `write`.
2. Present the plan contents to the user.
3. Use `question` to confirm readiness to proceed:

```
question([
  {
    header: "Research plan",
    question: "Ready to begin gathering, or would you like to adjust the plan?",
    options: [
      "Looks good — start gathering (Recommended)",
      "I'd like to adjust the plan first"
    ]
  }
])
```

If the user wants to adjust, incorporate their feedback and re-confirm.

> **Tip:** switch to the **Plan agent** (press `Tab` in the TUI) to
> review the plan in a read-only context before committing. Switch back
> to **Build** when ready.

### `question` schema on OpenCode

OpenCode's `question` tool takes an array of question objects. Each
object has `header` (short label), `question` (full text), and `options`
(array of strings). Put "(Recommended)" at the end of default options.

```
question([
  {
    header: "Output format",
    question: "Markdown or LaTeX (+ PDF compilation)?",
    options: ["Markdown (Recommended)", "LaTeX"]
  },
  {
    header: "Report length",
    question: "How long should the report be?",
    options: [
      "Standard — 12-18 pages (Recommended)",
      "Brief — 5-8 pages",
      "Detailed — 25-35 pages",
      "Extensive — 40+ pages"
    ]
  },
  {
    header: "Depth mode",
    question: "Snippets only, or targeted full-text fetch for unanswered questions?",
    options: [
      "Fast — snippets only (Recommended)",
      "Full — targeted full-text fetch"
    ]
  },
  {
    header: "Source count",
    question: "How many top sources to synthesise?",
    options: ["30 (Recommended)", "15", "50"]
  },
  {
    header: "Source types",
    question: "Which source types to include?",
    options: [
      "Academic papers (Recommended)",
      "Web / industry (Recommended)",
      "News",
      "Books"
    ]
  }
])
```

OpenCode's `question` is single-select per question. For the "source
types" question, ask multiple `question` calls or treat the first two as
default-on and offer News/Books as additive follow-ups.

### `taskTracker` on OpenCode

Use `todowrite` with the full updated list each call. Status values are
`todo`, `in_progress`, `completed`, `cancelled`.

```
todowrite([
  { id: "T1", content: "Stage 2: Parallel search", status: "todo" },
  { id: "T2", content: "Stage 3: Rank and filter", status: "todo" },
  { id: "T3", content: "Stage 4: Two-pass read", status: "todo" },
  { id: "T4", content: "Write draft (incremental)", status: "todo" },
  { id: "T5", content: "Unified review pass", status: "todo" },
  { id: "T6", content: "Deliver", status: "todo" }
])
```

Advance status as stages progress; call `todowrite` with the full
updated list after each stage.

### Subagents

Use the `Task` tool with the `@general` subagent for the core's
§Subagent split strategy. Dispatch two `Task` calls in a single turn
with prompts directing each subagent at its staging file. Wait for both
to return before merging.

### Extraction hierarchy Tier 3

`webFetch` resolves to OpenCode's `webfetch` tool. Use it only when the
MCP `extract_content` and `parse_pdf` tools have both failed for a given
URL.

---

## Installation note

The skill files live at either:

- `.opencode/skills/deep-research/SKILL.md` (project-local), or
- `~/.config/opencode/skills/deep-research/SKILL.md` (global)

The directory name must match the `name` field in the frontmatter
(`deep-research`). Place `SKILL-core.md` in the **same directory** as
this overlay (rename the overlay to `SKILL.md` when installing); the
overlay's first instruction loads the core by relative path.
