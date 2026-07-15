---
name: 1337-brain
description: "Mode: /1337-brain - maintain an Obsidian vault as an AI second brain for project knowledge. Use to ingest sources, create atomic linked wiki notes, build maps of content (MOCs), answer grounded questions through a hot-cache, index, then page retrieval ladder, dedupe, audit for contradictions and dead links, keep a recent-context cache, and log changes. Prefers the Obsidian MCP (list/read/search/create/update notes); falls back to the filesystem. Assumes Obsidian and the Obsidian MCP are installed. Trigger on /1337-brain or subcommands init|ingest|ask|link|moc|dedupe|audit|project|profile|log|hot, or when the user wants to capture, organize, distill, or retrieve durable project knowledge. Markdown is the source of truth; never invent facts; preserve source paths; keep links selective."
license: MIT
compatibility: "Requires an Obsidian vault. Prefers the Obsidian MCP; degrades to filesystem tools."
metadata:
   author: AeonDave
   version: "1.0"
---

# 1337-brain

The persistent second brain. Pairs with `/1337`: 1337 executes, 1337-brain remembers.

Turn raw project information - recon, findings, research, sources, decisions - into a living, linked wiki of reusable knowledge.

- The vault is the memory.
- Obsidian is the interface.
- Markdown is the source of truth.
- The agent is only the maintainer.

## Activation

Dispatch on `/1337-brain <command>` or when the user wants to capture, organize, distill, or retrieve durable project knowledge in Obsidian.

Classify the request into one workflow, then execute it:
`init` · `ingest <path>` · `ask <question>` · `link <note-or-topic>` · `moc <topic>` · `dedupe` · `audit` · `project <name>` · `profile` · `log` · other maintenance.

No persistent mode. Each invocation is one workflow run.

## Core principles

- Persist useful knowledge into the vault; never treat the chat as the memory.
- Retrieve before answering: read `index/hot.md`, then indexes/MOCs and note summary lines, then drill into the few relevant pages. Answer from vault evidence, never from model memory.
- Never delete raw sources unless explicitly instructed. Sources are immutable; reconcile the wiki during `audit`, not by deleting notes when a source is removed.
- Never invent facts unsupported by source material. Mark uncertainty explicitly.
- Atomic notes over long summaries. One idea per note, opened by a one-line summary the agent can scan.
- Wikilinks `[[note-name]]`, selective only - link when one note genuinely improves understanding of the other, never on shared keyword alone.
- Use native Obsidian formatting (callouts, embeds, properties) when it adds clarity; keep the underlying content plain, portable Markdown.
- Preserve the source path in every generated note.
- Separate source facts from your own synthesis/inference.
- Keep structure consistent across sessions; refresh `index/hot.md` and update indexes/logs after meaningful changes.
- Never write secrets, API keys, or live credentials into notes.

## MCP usage (MCP-first)

Obsidian MCP is assumed installed. Prefer it for: list vault files, read note, search notes, create note, update/append/patch note, resolve links.

Tool names vary by server - discover them at runtime and match by capability (list / read / search / create / patch). If a capability is missing, slower, or errors, fall back to filesystem tools. The filesystem remains the source of truth; the vault root is whatever the Obsidian MCP serves.

Transports vary: a Local REST API-style server (vault plugin over local HTTP) or a filesystem-style server pointed at the vault path. Detect which is present; never hardcode API keys, hosts, or ports into notes.

If Obsidian-native format skills are available (e.g. `obsidian-skills` for Markdown, Bases, JSON Canvas, and the CLI), defer to them for advanced formatting - `.base` dashboards, `.canvas` maps, rich callouts - instead of hand-rolling syntax.

## Vault structure

Use or create this; if the user already has a structure, respect it and adapt without migration.

```text
raw/{articles,books,transcripts,pdf,snippets}/   # unprocessed material
sources/                                          # original clipped sources
wiki/                                             # cleaned atomic knowledge
  concepts/ mental-models/ frameworks/ tools/
  people/ projects/ sources/ questions/ profile/
index/
  MOC.md  Sources.md  Open Questions.md  Log.md  hot.md
```

`wiki/sources/` holds one source summary per ingested source. `index/` holds maps, the source registry, open questions, the change log, and `hot.md` - a small recent-context cache rewritten after each run so the next session opens with context and needs no recap.

## Commands

| Command | Action |
|---------|--------|
| `init` | Create missing folders + `index/{MOC,Sources,Open Questions,Log}.md`. No ingest. Report what was created. |
| `ingest <path>` | Read source(s), extract durable knowledge, write source summary + atomic notes, link, update indexes + log. |
| `ask <question>` | Retrieval ladder: read `hot.md`, scan the index/MOCs and note summary lines, drill into the few relevant pages, then answer using only that vault evidence; cite note paths; separate facts / synthesis / gaps. |
| `link <topic>` | Add useful `[[links]]` + backlinks, remove weak ones, update relevant MOCs. |
| `moc <topic>` | Create/update `index/MOC - <topic>.md` grouping notes by theme with one-line "why it matters". |
| `dedupe` | Find overlapping notes; propose merges/splits. Never merge automatically. |
| `audit` | Health check: unindexed sources, unsourced notes, orphans, dead links, oversized notes, stale questions, weak MOCs, contradictions between notes, stale claims, and concepts referenced with no page. Reconcile against current sources; propose merges/deletions, never auto-delete. |
| `project <name>` | Create `wiki/projects/<name>/{Inputs,Process,Outputs,Feedback}/` + scoped `CLAUDE.md`/`AGENTS.md` that point at this vault with the read order (hot.md -> index -> sub-index -> pages) and the rule "do not read the wiki for general coding questions"; link to wiki + project index. |
| `profile` | Create/update `wiki/profile/user-profile.md` (durable info only; ask one question at a time if missing). |
| `log` | Append a dated entry to `index/Log.md`. |
| `hot` | Rewrite `index/hot.md`: recent activity, active threads, open questions, and pointers into the index. Runs automatically after meaningful changes; can be invoked directly. |

### ingest depth

- **light**: source summary + 1-3 concept notes.
- **medium** (default): source summary + 3-10 concept/framework notes + 2-3 links each + open questions when useful.
- **deep**: all major concepts + cross-links.
- If the user names a focus, prioritize it.

For folders: ingest only files not already in `index/Sources.md`, one at a time; merge into existing concept notes instead of creating duplicates.

After any ingest, report: created notes, updated notes, skipped duplicates, unresolved questions.

### Session cache (hot.md)

Keep `index/hot.md` small and current: what was just added, active threads, open questions, and pointers into the index. Read it first on `ask` and at session start; rewrite it after any meaningful change. It is fast-load context that removes re-explaining between sessions - not a second log (durable history lives in `index/Log.md`).

## Note templates

Keep notes atomic, sourced, scannable. Frontmatter fields used as needed: `type, status, tags, domain, source, author, date_ingested, created, updated, related`.

**Concept / mental-model / framework / tool note**
```md
---
type: concept
status: draft
tags: []
source:
created:
updated:
related:
---
# Title
## Definition
One line.
## Core idea
Clear explanation.
## Key points
- ...
## Connections
- [[related-note]] - why this link matters
## Source references
- `path/to/source.md`
## Open questions
- ...
```

**Source summary** (`wiki/sources/`)
```md
---
type: source-summary
source:
author:
date_ingested:
tags: []
---
# Source title
## What this is
## Key ideas
- ...
## Extracted notes
- [[note-name]]
## Useful quotes
Short excerpts only.
## Open questions
- [[question-note]]
## Source path
`path/to/source.md`
```

**Question** (`wiki/questions/`)
```md
---
type: question
status: open
created:
related:
---
# Question
## Why it matters
## Current evidence
- ...
## Possible directions
- ...
## Related
- [[related-note]]
```

## Output formats

**ask**
```text
Answer

Evidence used:
- path/to/note.md
- path/to/source-summary.md

Missing or uncertain:
- ...
```

**moc** → `index/MOC - <topic>.md`
```md
# MOC - Topic
## Overview
## Core notes
- [[note]] - why it matters
## Sources
- [[source-summary]]
## Open questions
- [[question-note]]
## Next actions
- ...
```

**dedupe**
```text
Potential duplicates:
1. wiki/concepts/a.md + wiki/concepts/b.md
   Suggested: merge into a.md - reason ...
```

**audit**
```text
Vault audit
Unindexed sources: ...
Notes without sources: ...
Orphan notes: ...
Dead links: ...
Oversized notes: ...
Contradictions: note-a.md vs note-b.md - ...
Stale claims: ...
Missing pages: concept referenced but unwritten
Suggested next actions: ...
```

**log** → append to `index/Log.md`
```md
## YYYY-MM-DD
### Created
- ...
### Updated
- ...
### Open questions
- ...
```

## Tag + link rules

- Tags: lowercase, kebab-case, organic, durable (`mental-model`, `framework`, `recon`, `web`, `crypto`, `tooling`). No premature taxonomies.
- 2-3 strong links per note. Good links explain, contrast, apply, or show a dependency. Bad links: same keyword, vague theme, graph decoration.

## Obsidian formatting

- Use callouts for signals the reader must not miss: `> [!note]`, `> [!question]`, `> [!warning]`, and `> [!contradiction]` (place both conflicting sources inside it).
- Embed with `![[note#section]]` to reuse content instead of duplicating it.
- Use a `.base` for dashboards or filtered note views and a `.canvas` for visual maps; defer to Obsidian format skills when available.

## Quality bar

Good note: atomic, sourced, reusable, selectively linked, short enough to scan. Bad note: blob summary, unsourced, weak links, too broad, invented synthesis, disconnected.

## Output style

After a workflow, report terse:
```text
Read: ...
Created: ...
Updated: ...
Skipped: ...
Uncertain: ...
Cached: hot.md ...
Next: ...
```
No narration of internal steps. No motivational commentary.

## Safety

- Prefer read-only access for external tools.
- No external actions (email, calendar, deletes) unless explicitly instructed.
- No secrets/API keys in notes; keep the vault portable and model-agnostic.

## Operating heuristic

Capture (raw sources) → Organize (summaries, notes, indexes) → Distill (atomic notes, MOCs) → Express (grounded answers, strategies, decisions). The goal is not to store everything; it is to make useful knowledge easy to retrieve, combine, and apply.
