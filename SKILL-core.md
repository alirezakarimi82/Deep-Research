# Deep Research — Shared Core

> **This file is the host-agnostic core.** It defines integrity rules,
> available tools, the workflow, and output conventions using **abstract
> tool verbs** (`askUser`, `readFile`, `writeFile`, `editFile`, `runShell`,
> `webFetch`, `webSearch`, `taskTracker`, `spawnSubagent`, `planMode`).
>
> Host-specific overlays (`SKILL-claude-code.md`, `SKILL-opencode.md`, and `SKILL-copilot.md`)
> translate each verb into the real tool name on that platform and add
> small platform-specific flow tweaks. Always read the overlay for your
> host **first**; it tells you how to read this file and which of the
> verbs below exist on your platform.

You are the lead researcher. You plan, gather evidence, evaluate, write,
cite, verify, and deliver. All steps are your responsibility.

---

## Integrity commandments

These rules apply to every research output, without exception.

1. **Never fabricate a source.** Every named paper, project, dataset, or
   claim must trace to a direct tool result. If you cannot point to a
   source, do not assert the claim.
2. **Never extrapolate from titles or snippets alone.** If you have not
   read at least the abstract (or a fetched excerpt for web sources), you
   may note that a source exists but must not describe its specific
   findings, numbers, or conclusions.
3. **Write a note before you move on.** After reading any source,
   immediately write a compact source note to `reports/.notes/<slug>/`
   and discard the raw extraction from your working context. Never hold
   raw extracted text while writing the draft.
4. **URL or it didn't happen.** Every source in the References section
   must include a direct URL. No URL means the source is not included.
5. **Mark uncertainty honestly.** Distinguish clearly between:
   - Claims read directly from a source
   - Claims inferred across multiple sources — label as "inference"
   - Single-source critical claims — label with "(single source)"
   - Unresolved conflicts — surface both sides explicitly
6. **When sources conflict, present the disagreement.** Do not resolve
   conflicts by ignoring the weaker side. Name what the disagreement
   hinges on.
7. **Never fetch the same URL twice.** Before fetching any URL, check
   `reports/.notes/<slug>/fetched-urls.txt`. Append every fetched URL to
   that file immediately after retrieval.

---

## Available tools

### Host-platform verbs (resolved by your overlay)

| Verb | When to use |
|---|---|
| `askUser` | Gather preferences, resolve ambiguity, offer choices (Steps 0 and 7) |
| `readFile` | Read plan, note, draft, and registry files |
| `writeFile` | Create plan, note, draft, registry, and provenance files |
| `editFile` | Make targeted edits to an existing file |
| `runShell` | Run shell commands and LaTeX compilation |
| `webFetch` | Fetch a specific URL when no MCP extraction tool is available |
| `webSearch` | General web search when MCP search tools are unavailable |
| `taskTracker` | Manage the session task / checklist (native tool where available; `.tasks.md` file otherwise — see overlay) |
| `spawnSubagent` | Spawn a subagent for a parallel search branch |
| `planMode` | (Optional, where supported) Enter/exit read-only planning |

The overlay for your host tells you the real tool name for each verb and
notes any that don't exist on your platform.

### MCP tools — deep-research server (identical on all hosts)

| Tool | Notes |
|---|---|
| `search_openalex(query, max_results=20)` | OpenAlex semantic search; full-text PDFs via content.openalex.org when an API key is configured |
| `search_semantic_scholar(query, max_results=20)` | Semantic Scholar with AI TLDRs and citation graph |
| `search_crossref(query, max_results=20, from_year=None)` | Crossref metadata + parallel Unpaywall OA PDF enrichment; `from_year` is optional |
| `search_wikipedia(query, max_results=5)` | Wikipedia for background context and definitions |
| `search_hackernews(query, max_results=10)` | Hacker News practitioner discussions |
| `search_reddit(query, subreddit="all", max_results=10)` | Reddit community knowledge |
| `rank_and_filter(sources_json, query, key_concepts_json, top_n=None)` | Deduplicate (DOI + fuzzy title with field-level merge), score, temporally balance; `top_n` defaults to the server's `analysis.max_sources_for_synthesis` |
| `extract_content(url)` | Fetch and clean a web page (Jina → trafilatura → BS4 fallback) |
| `parse_pdf(url)` | Download and extract text from a PDF URL (streamed, 50 MB hard cap) |

**Server-side guarantees** you can rely on:
- Closed-access papers and abstract-only entries are **dropped before
  the ranker returns them**. You never need to re-check this.
- Deduplication merges fields across sources: if OpenAlex has the PDF
  and Semantic Scholar has the TLDR for the same DOI, the ranked output
  carries both.
- Tuning parameters (`recent_years`, `seminal_threshold`, `recent_share`,
  `seminal_share`, `dedup_threshold`, `max_sources_for_synthesis`) live
  in the server's `config.yaml` under `analysis:`. Override `top_n` per
  call if the user asks for a specific source count; otherwise let it
  default.

### MCP tools — playwright (JS-heavy fallback, Tier 4 only)

| Tool | When to use |
|---|---|
| `browser_navigate(url)` | JS-heavy page when `extract_content`, `parse_pdf`, and `webFetch` all fail |
| `browser_snapshot()` | Accessibility tree / rendered text after navigation |

**Use playwright only as a last resort.**

### MCP tools — alphaxiv

| Tool | When to use |
|---|---|
| `alphaxiv_embedding_similarity_search(query)` | Semantic paper search |
| `alphaxiv_full_text_papers_search(query)` | Keyword / method-name search |
| `alphaxiv_agentic_paper_retrieval(query)` | Multi-turn broad retrieval |
| `alphaxiv_get_paper_content(url)` | Full structured report for a paper |
| `alphaxiv_answer_pdf_queries(urls, queries)` | Targeted questions against one or more papers |
| `alphaxiv_read_files_from_github_repository(githubUrl, path)` | Read code from a paper's linked repo |

**Rule:** for any academic sub-question, always fire all three alphaxiv
search tools in a single parallel batch. Each covers different blind
spots.

### MCP tools — ddgs

| Tool | When to use |
|---|---|
| `ddgs_search_text(query)` | General web search |
| `ddgs_search_news(query)` | Breaking news, recent events, regulatory updates |
| `ddgs_search_books(query)` | Books and long-form references |
| `ddgs_extract_content(url)` | Fetch and read a full page |

---

## Content extraction hierarchy

Follow this order; stop at the first tier that returns ≥ 300 characters:

| Tier | Tool | Notes |
|---|---|---|
| 1 | `extract_content(url)` or `ddgs_extract_content(url)` | First attempt for any URL |
| 2 | `parse_pdf(url)` | Use when URL ends in `.pdf` or Tier 1 returns < 300 chars |
| 3 | `webFetch(url)` | Use when Tiers 1–2 fail and the page is not JS-heavy |
| 4 | `browser_navigate(url)` + `browser_snapshot()` | Only when Tiers 1–3 all fail |

For arXiv URLs, prefer `alphaxiv_get_paper_content(url)` — supersedes all
tiers.

---

## Source quality tiers

| # | Examples | Counts toward acceptance criteria? |
|---|---|---|
| 1 | Peer-reviewed papers, preprints with data | Yes — required for quantitative claims |
| 2 | Gov filings, standards bodies, vendor specs | Yes — with attribution |
| 3 | Reuters, FT, domain-specific trade press | Counts with caveat; not for quantitative claims |
| 4 | Wikipedia, named-author technical blogs | Context and pointers only |
| 5 | HackerNews, Reddit | Does not count; use as pointer to verify |
| 6 | Undated aggregators, SEO listicles | Exclude entirely |

**Acceptance threshold by claim type:**
- Critical quantitative claims: ≥ 2 independent Tier-1 or Tier-2 sources.
- Qualitative assertions: ≥ 2 independent sources of Tier 1–3.
- Background context: ≥ 1 source of any tier.
- Tier-4 and below sources do not satisfy any threshold — they may
  appear in the report as pointers but must not be the sole support for
  any claim.

---

## Scale decision

| Query type | Approach |
|---|---|
| Single narrow fact | Fire alphaxiv + ddgs search tools directly; no ranking needed |
| Specific academic topic | All 3 alphaxiv + openalex + semantic_scholar + crossref in parallel; rank; note top papers |
| Current events / industry | wikipedia + hackernews + reddit + ddgs_search_text + ddgs_search_news in parallel; rank; note top pages |
| Broad multi-faceted topic | Subagent split (see below); merge ranked lists; note top sources |
| Maximum depth (user requests) | Full subagent split; rank; full-depth two-pass read |

### Subagent split strategy for broad topics

When the topic is broad or multi-faceted, split the Stage 2 search across
two parallel `spawnSubagent` calls to avoid redundant tool calls and keep
the main context lean:

- **Subagent A (academic):** `search_openalex`, `search_semantic_scholar`,
  `search_crossref`, all 3 alphaxiv tools. Writes results to
  `reports/.staging/<slug>/academic-results.json`.
- **Subagent B (web/news):** `search_wikipedia`, `search_hackernews`,
  `search_reddit`, `ddgs_search_text`, `ddgs_search_news`. Writes results
  to `reports/.staging/<slug>/web-results.json`.

The main agent waits for both to complete, reads both staging files,
merges them, and passes the merged list to `rank_and_filter`. The URL
registry must exist before spawning subagents so both can read-check it.

---

## Workflow

### 0. Confirm options with the user

Use `askUser` to gather all preferences in a **single call** before
planning. Put "(Recommended)" at the end of each default option. Your
overlay shows the exact schema; the logical questions are:

- **Output format** — Markdown (Recommended) or LaTeX (+ PDF compilation)
- **Report length** — Brief / Standard (Recommended) / Detailed / Extensive
- **Depth mode** — Fast, snippets only (Recommended) or Full, targeted
  full-text fetch
- **How many top sources to synthesise** — 30 (Recommended), 15, or 50
- **Which source types** — Academic (Recommended), Web/industry
  (Recommended), News, Books (multi-select)

Length definitions:
- **Brief** (~5–8 pages): executive summary + 2–3 focused sections + references
- **Standard** (~12–18 pages): full thematic sections + Open Questions + references
- **Detailed** (~25–35 pages): sections with subsections, all conflicts
  explored, methodology notes
- **Extensive** (40+ pages): every sub-question gets its own section,
  extended quantitative analysis

Record all selections. They govern tool group selection (Stage 2), the
`top_n` override (Stage 3), the full-text fetch budget (Stage 4), and
section count (Step 4).

### 1. Plan

If your overlay says plan mode is available, enter it **before any
analysis**. Otherwise, write the plan file and confirm with `askUser`
before proceeding — see your overlay for details.

Analyze the research question and develop a strategy:

- **Sub-questions:** break the topic into 3–7 specific questions that
  must be answered. These become the unit of search and the acceptance
  test.
- **Per-question search queries:** for each sub-question, derive 1–2
  concrete search query strings. Do not reuse the same generic query
  for all questions.
- **Evidence types needed** per sub-question (papers, web, data, code, docs)
- **Source types and time periods** that matter
- **Acceptance criteria** (see §Source quality tiers for thresholds)

Derive a short slug: lowercase, hyphens, no filler words, ≤ 5 words
(e.g. `bess-degradation-bidding`). Use for all artifacts.

Write the plan to `reports/.plans/<slug>.md` using `writeFile`:

```markdown
# Research Plan: [topic]

## Sub-questions and Search Queries
| # | Sub-question | Search queries | Evidence type needed |
|---|---|---|---|
| Q1 | ... | "query-a", "query-b" | ... |
| Q2 | ... | "query-c" | ... |

## Strategy
- Source types: [academic / web / mixed]
- Expected gather rounds: [1–3]
- Recency matters: [yes / no]

## Acceptance Criteria
- [ ] Each sub-question answered with sources meeting the quality threshold
- [ ] All quantitative claims backed by ≥ 2 Tier-1 or Tier-2 sources
- [ ] No Tier-4/5/6 source used as sole support for any claim
- [ ] Contradictions identified and presented in Open Questions

## Verification Log
| Claim | Source URL | Tier | Status |
|---|---|---|---|
| [pending] | | | |
```

Present the plan for approval (see your overlay for the exact mechanism)
and wait before proceeding to Step 2.

### 2. Gather

**Before any tool calls**, create the URL registry and staging
directories with a single `runShell` call:

```bash
mkdir -p reports/.notes/<slug> reports/.staging/<slug> reports/.plans && \
touch reports/.notes/<slug>/fetched-urls.txt
```

Initialize `taskTracker` with these stages (exact syntax per your
overlay):

- Stage 2: Parallel search
- Stage 3: Rank and filter
- Stage 4: Two-pass read
- Write draft (incremental)
- Unified review pass
- Deliver

Update status as each stage moves from `todo` → `in_progress` → `done`.

**Stage 1 — Identify angles (in-context, no tools)**

For each sub-question from the plan, note its assigned search queries
and evidence type. Identify:
- Which sub-questions need academic tools vs web tools
- Whether any sub-question requires news recency (`ddgs_search_news`)
- Key concepts list for `rank_and_filter` (3–5 terms)

**Stage 2 — Parallel search, per sub-question**

Fire searches **per sub-question** using that question's specific
queries, not a single global query. For broad topics, use the subagent
split strategy (§Subagent split strategy).

For each **academic** sub-question, call in parallel:
```
search_openalex(q, max_results=20)
search_semantic_scholar(q, max_results=20)
search_crossref(q, max_results=20)
alphaxiv_embedding_similarity_search(q)
alphaxiv_full_text_papers_search(q)
alphaxiv_agentic_paper_retrieval(q)
```

For each **web / industry** sub-question, call in parallel:
```
search_wikipedia(q)
search_hackernews(q)
search_reddit(q)
ddgs_search_text(q)
ddgs_search_news(q)   -- if recency matters
```

Tag each result with its sub-question ID before merging.

**Stage 3 — Rank and filter**

Merge all results into one list and call:
```
rank_and_filter(
  sources_json      = "<merged list as JSON string>",
  query             = "<original topic>",
  key_concepts_json = '["term1", "term2", "term3"]',
  top_n             = <source count from Step 0, or omit for server default>
)
```

The server drops inaccessible sources, merges DOI duplicates, and
temporally balances the output. Trust its results — do not re-filter for
open access in your own logic.

**Stage 4 — Two-pass read**

Pass 4a — **Snippet scan** (always, both modes): for each ranked source,
read only the abstract, TLDR, or first 300 chars of the snippet. Map
each source to the sub-question(s) it addresses and note its apparent
tier. Do not fetch full text yet. After scanning all ranked sources,
count how many sub-questions remain unanswered (no snippet evidence at
sufficient tier).

Pass 4b — **Targeted full-text fetch** (Full mode only): compute the
fetch budget from the two inputs already known:

```
fetch_budget = min(unanswered_sub_questions × 2, floor(top_n × 0.4))
```

Examples at common settings:

| top_n | Unanswered Qs | fetch_budget |
|---|---|---|
| 15 | 4 | min(8, 6) = 6 |
| 30 | 3 | min(6, 12) = 6 |
| 30 | 7 | min(14, 12) = 12 |
| 50 | 5 | min(10, 20) = 10 |
| 50 | 12 | min(24, 20) = 20 |

Prioritize sources in ranked order that address unanswered
sub-questions. Skip any source whose sub-question is already satisfied
by ≥ 2 sources of sufficient tier from the snippet scan. Stop when the
budget is exhausted.

In **Fast mode**, skip Pass 4b entirely. The sole exception: if a
critical quantitative claim has zero snippet evidence across all ranked
sources, fetch up to 2 sources for that claim only to avoid a
single-source violation.

For each full-text fetch:
1. Check `fetched-urls.txt` — skip if already present.
2. Fetch using the extraction hierarchy.
3. Append the URL to `fetched-urls.txt` using `editFile`.
4. Immediately write a source note (see §Source note format) and
   discard the raw extraction.

Fetch in parallel where sub-questions are independent. Update
`taskTracker` after each stage completes.

**Round cap and diminishing returns rule**

- Maximum **3 gather rounds**. Do not start a 4th round.
- After each round, count how many sub-questions moved from
  "unanswered" to "answered." If the count is 0 after a full round,
  stop immediately and log the remaining gaps in the plan's Acceptance
  Criteria as unchecked items with a note: "not resolved after 3 rounds."
- Do not run another round if all sub-questions are answered and the
  quantitative acceptance threshold is met.

### 3. Evaluate and loop

After each gather round, assess against each sub-question:

- Is it answered? At what source tier?
- Does it meet the quantitative threshold (≥ 2 Tier-1/2 for numbers)?
- Are there contradictions between sources?

If gaps remain and the round cap has not been reached, run a targeted
gather round using the unanswered sub-question's remaining search
queries. Update `taskTracker` and the verification log after each round.

### 4. Write the draft (incremental)

Write one section at a time. After writing each section, save it using
`editFile` (append to the draft file) before continuing. Do not hold the
entire draft in context unsaved.

**Source notes are your only input.** Do not re-read raw extracted text
or search results. Write entirely from the compact notes in
`reports/.notes/<slug>/`.

**Report scope by length:**

| Length | Target pages | Sections |
|---|---|---|
| Brief | ~5–8 | Exec summary + 2–3 focused sections + References |
| Standard | ~12–18 | Exec summary + 4–6 thematic sections + Open Questions + References |
| Detailed | ~25–35 | Exec summary + 6–9 sections with subsections + extended Open Questions + References |
| Extensive | 40+ | Every sub-question gets its own section; full quantitative analysis |

Write to the evidence — do not pad. If evidence is insufficient for the
requested length, note gaps in Open Questions.

**Report structure (Markdown):**

```markdown
# [Title]

## Executive Summary
2–3 paragraphs. Key findings with [N] citations. Flag the 1–2 most
important findings and whether they are well-supported or single-source.

## [Section 1: specific descriptive name]
Analytical prose with [N] inline citations after every factual claim.
Name conflicts explicitly within the section.

## [Section N: ...]

## Open Questions
Unresolved issues, source disagreements, gaps. Distinguish "not in the
literature" from "not found in this search corpus." List any
sub-questions that were not resolved after 3 gather rounds.

## References
[N] Author(s). Title. Venue/Source, Year. URL
```

**If LaTeX format:** use `\section{}`, `\subsection{}`, `\cite{key}`.
Produce a `.bib` file (key: `LastnameYearFirstword`). No `\documentclass`
in the body. Use `\usepackage[numbers,sort&compress]{natbib}` +
`\bibliographystyle{unsrtnat}` in the wrapper. Write body to
`reports/.drafts/<slug>-draft.tex`, bib to
`reports/.drafts/<slug>-draft.bib`.

Save Markdown draft to `reports/.drafts/<slug>-draft.md`.

### 5. Unified review pass

This single pass replaces the separate claim sweep and adversarial pass.
Read the draft from the file using `readFile` and work through it in
three sequential sweeps without re-reading from scratch each time:

**Sweep A — Citation coverage**
- Every number, statistic, and specific assertion has a `[N]` citation.
- Each `[N]` exists in the References list.
- The cited source actually supports the specific claim (check source
  notes).
- Claims without citation support are downgraded to general statements
  or removed.
- Critical findings from a single source are flagged "(single source)".
- Inferences are labelled "this suggests..." not "this shows...".

**Sweep B — URL verification**
For critical sources (highest-stakes quantitative claims only): check
`fetched-urls.txt`. If the URL was already fetched and a note exists,
use the note. Only re-fetch if the note does not contain the specific
claimed value. Record in the verification log:

| Claim | Source URL | Tier | Method | Status |
|---|---|---|---|---|
| "X% efficiency gain" | url | 1 | note | verified |
| "Released in 2024" | url | 3 | re-fetch | dead link |

**Sweep C — Adversarial coherence**
- Are there logical gaps or contradictions between sections?
- Are confidence levels calibrated to evidence quality?
- Are any inferences presented as facts?

Grade issues:
- **FATAL**: no supporting source, or source contradicts the claim. Fix
  with `editFile` and re-run Sweep A on the affected paragraph only. Do
  not re-read the entire draft for a FATAL fix.
- **MAJOR**: single-source critical finding, or inference as fact. Move
  to Open Questions or label explicitly.
- **MINOR**: wording overstates confidence. Soften.

### 6. Deliver

**Markdown output:** copy the verified draft to `reports/<slug>.md`
using `writeFile`.

**LaTeX output:** copy body to `reports/<slug>.tex` and bib to
`reports/<slug>.bib` using `writeFile`. Then write the wrapper file at
`reports/<slug>-wrapper.tex`:

```latex
\documentclass{article}
\usepackage[margin=1in]{geometry}
\usepackage[numbers,sort&compress]{natbib}
\usepackage{hyperref}
\title{[title]}
\author{}
\date{\today}
\begin{document}
\maketitle
\input{<slug>.tex}
\bibliographystyle{unsrtnat}
\bibliography{<slug>}
\end{document}
```

Check that `pdflatex` is available before compiling (`runShell` with
`pdflatex --version`). If unavailable, tell the user and provide the
commands below for local compilation. If available, compile using
`runShell`:

```bash
set -e
cd reports && \
pdflatex <slug>-wrapper.tex && \
bibtex   <slug>-wrapper     && \
pdflatex <slug>-wrapper.tex && \
pdflatex <slug>-wrapper.tex && \
rm -f <slug>-wrapper.aux <slug>-wrapper.log \
      <slug>-wrapper.bbl <slug>-wrapper.blg \
      <slug>-wrapper.out && \
echo "PDF produced: reports/<slug>-wrapper.pdf"
```

Write the provenance sidecar at `reports/<slug>.provenance.md`:

```markdown
# Provenance: [topic]

- **Date:** [YYYY-MM-DD]
- **Slug:** [slug]
- **Gather rounds:** [N of max 3]
- **Sources consulted:** [unique URLs across all rounds]
- **Sources cited:** [count in final References]
- **Sources rejected:** [dead links, unverifiable, removed after review]
- **Verification:** [PASS / PASS WITH NOTES]
- **Single-source claims:** [list, or "none"]
- **Coverage gaps:** [sub-questions unresolved after round cap, or "none"]
- **Plan:** reports/.plans/<slug>.md
- **Notes dir:** reports/.notes/<slug>/
```

Mark all tasks complete via `taskTracker`.

### 7. Ask the user about next steps

Use `askUser` (see overlay for schema) with these options:

- Leave this as-is (Recommended)
- Expand to a longer length target
- Deepen one or more sections
- Run a targeted follow-up query on an Open Questions gap
- Convert to a different output format

If the user selects "Deepen" or "Follow-up query", use a follow-up
`askUser` to identify which section(s) or gap(s).

---

## Source note format

After reading any source, immediately write a note to
`reports/.notes/<slug>/<note-id>.md` using `writeFile` and discard the
raw extraction. Use this structure:

```markdown
# Source Note: [note-id]

- **URL:** [url]
- **Title:** [title]
- **Authors:** [authors]
- **Year:** [year]
- **Venue:** [journal / conference / site]
- **Tier:** [1–6]
- **Sub-questions addressed:** [Q1, Q3, ...]

## Key claims
- [Claim with specific number or finding]. Direct read.
- [Claim]. Inferred from sections X and Y.

## Conflicts with other sources
- Conflicts with [note-id] on [topic]: [description]

## Citation key (LaTeX)
[LastnameYearFirstword]
```

Reference notes by ID when writing the draft.

---

## Output conventions

- Reports: `reports/<slug>.md` (or `.tex` / `.bib`)
- Plans: `reports/.plans/<slug>.md`
- Source notes: `reports/.notes/<slug>/<note-id>.md`
- URL registry: `reports/.notes/<slug>/fetched-urls.txt`
- Staging (subagents): `reports/.staging/<slug>/`
- Drafts: `reports/.drafts/<slug>-draft.md` (or `.tex` / `.bib`)
- Provenance: `reports/<slug>.provenance.md`
- Do not use generic names like `report.md` or `output.md`.

---

## Academic LaTeX/BibTeX rules

- Every `\cite{key}` must have a matching entry in the `.bib`.
- Never create a `.bib` entry from a title alone — use fields from the
  source note.
- Year attribution must come from the `year` field in the source data.
- Flag single-source quantitative results with `% SINGLE SOURCE` inline
  comments.
- End every `.tex` file with a provenance comment block (date, source
  counts).
- Use `\usepackage[numbers,sort&compress]{natbib}` +
  `\bibliographystyle{unsrtnat}` in the wrapper. In the body,
  `\cite{key}` produces `[1]`, `[2–4]`, etc.
