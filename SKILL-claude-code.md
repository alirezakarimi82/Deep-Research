---
name: deep-research
description: Run a thorough, source-heavy investigation on any topic. Use when the user asks for deep research, a comprehensive analysis, an in-depth report, or a multi-source investigation. Produces a cited research brief with provenance tracking.
---

# Deep Research — Claude Code Overlay

> **First action for this skill:** use `Read` on the file `SKILL-core.md`
> (same directory as this overlay). It contains the integrity rules,
> tool reference, workflow, and output conventions for the entire
> skill. This overlay only translates the core's abstract verbs into
> Claude Code tools and pins down the Claude-Code-specific flow bits
> (mandatory plan mode, `AskUserQuestion` schema, `Agent` subagents).
>
> Once you have read the core, apply the mapping below and follow the
> workflow there verbatim.

---

## Verb → tool mapping (Claude Code)

| Core verb | Claude Code tool |
|---|---|
| `askUser` | `AskUserQuestion` |
| `readFile` | `Read` |
| `writeFile` | `Write` |
| `editFile` | `Edit` |
| `runShell` | `Bash` |
| `webFetch` | `WebFetch` |
| `webSearch` | `WebSearch` |
| `taskTracker` | `TaskCreate` / `TaskUpdate` / `TaskList` |
| `spawnSubagent` | `Agent` |
| `planMode` | `EnterPlanMode` / `ExitPlanMode` |

All MCP tool names (`search_openalex`, `rank_and_filter`, `extract_content`,
etc.) are identical across hosts — use them exactly as written in the core.

---

## Claude-Code-specific flow bits

### Step 1 — Plan mode is mandatory

**The very first action of Step 1 is to call `EnterPlanMode()`.** Do not
perform any analysis, derive the slug, or write anything until this call
has been made. Do not call `ExitPlanMode()` if `EnterPlanMode()` was not
called first in the same step.

```
EnterPlanMode()
```

While in plan mode, you may use `AskUserQuestion` to resolve any
remaining ambiguities before finalizing the plan. Do **not** use
`AskUserQuestion` to ask for plan approval — that is what `ExitPlanMode`
is for.

After writing the plan file, exit plan mode to present it for approval:

```
ExitPlanMode()
```

Wait for the user's approval before proceeding to Step 2.

### `AskUserQuestion` schema

Single call with an array of question objects. Each object has
`question` (string) and `options` (array of strings), plus optional
`multiSelect: true`. Put "(Recommended)" at the end of default options.

```
AskUserQuestion([
  {
    question: "Output format?",
    options: ["Markdown (Recommended)", "LaTeX (+ PDF compilation)"]
  },
  {
    question: "Report length?",
    options: [
      "Standard — 12-18 pages (Recommended)",
      "Brief — 5-8 pages",
      "Detailed — 25-35 pages",
      "Extensive — 40+ pages"
    ]
  },
  {
    question: "Depth mode?",
    options: [
      "Fast — snippets only (Recommended)",
      "Full — targeted full-text fetch"
    ]
  },
  {
    question: "How many top sources to synthesise?",
    options: ["30 (Recommended)", "15", "50"]
  },
  {
    question: "Which source types to include?",
    multiSelect: true,
    options: [
      "Academic papers (Recommended)",
      "Web / industry (Recommended)",
      "News",
      "Books"
    ]
  }
])
```

### `taskTracker` on Claude Code

Use `TaskCreate` to create each stage, `TaskUpdate` to advance status
(`todo` → `in-progress` → `done` / `blocked`), and `TaskList` to
inspect. Stage titles per the core's Step 2.

### Subagents

`Agent(prompt=...)` spawns a general-purpose subagent. For the subagent
split in the core's §Subagent split strategy, dispatch two agents in a
single turn with their own prompts pointing at the respective staging
file paths. Wait for both to return before merging.

### Extraction hierarchy Tier 3

`webFetch` resolves to Claude Code's `WebFetch` tool. Use it only when
the MCP `extract_content` and `parse_pdf` tools have both failed for a
given URL.
