# 1337-brain

The persistent second brain. Pairs with `/1337`: 1337 executes, 1337-brain remembers.

Turn raw project information - recon, findings, research, sources, decisions - into a living, linked Obsidian wiki of reusable knowledge.

- Vault = memory. Obsidian = interface. Markdown = source of truth. Agent = maintainer.

## Dispatch

Trigger on `/1337-brain <command>` or a request to capture, organize, distill, or retrieve durable project knowledge in Obsidian. Classify into one workflow:
`init` · `ingest <path>` · `ask <question>` · `link <topic>` · `moc <topic>` · `dedupe` · `audit` · `project <name>` · `profile` · `log`.

## Core principles

- Persist useful knowledge into the vault; never treat the chat as memory.
- Never delete raw sources unless told. Never invent facts; mark uncertainty.
- Atomic notes over summaries. One idea per note.
- `[[wikilinks]]` selective only - link when it genuinely improves understanding, not on shared keyword.
- Preserve the source path in every note. Separate source facts from synthesis.
- No secrets/API keys in notes. Update indexes/log after meaningful changes.

## MCP-first

Obsidian MCP is assumed installed. Prefer it for list / read / search / create / patch / link-resolve. Tool names vary - discover at runtime, match by capability. Missing or failing capability -> filesystem fallback. Filesystem is source of truth; vault root = whatever the MCP serves.

## Vault structure (create if missing, else respect existing)

```text
raw/{articles,books,transcripts,pdf,snippets}/
sources/
wiki/{concepts,mental-models,frameworks,tools,people,projects,sources,questions,profile}/
index/{MOC,Sources,Open Questions,Log}.md
```

`wiki/sources/` = one summary per source. `index/` = maps, source registry, open questions, log.

## Commands

- **init**: create missing folders + `index/{MOC,Sources,Open Questions,Log}.md`; no ingest; report what was created.
- **ingest `<path>`**: read source(s) -> extract durable concepts/people/tools/frameworks/questions -> write source summary in `wiki/sources/` + atomic notes -> selective links -> source path on every note -> update `index/Sources.md`, `Open Questions.md`, `Log.md`. Folders: skip files already in `index/Sources.md`, one at a time, merge into existing notes (no duplicates). Depth: light = summary + 1-3 notes; medium (default) = summary + 3-10 notes + 2-3 links each; deep = all concepts + cross-links. Report created/updated/skipped/unresolved.
- **ask `<question>`**: search vault only; cite note paths; separate facts / synthesis / gaps. If insufficient evidence, say so. Outside knowledge only if explicitly asked.
- **link `<topic>`**: add useful links + backlinks, drop weak ones, update relevant MOCs, report changed files.
- **moc `<topic>`**: create/update `index/MOC - <topic>.md` grouping notes by theme with one-line "why".
- **dedupe**: find overlapping notes; propose merge/split with reason; never merge automatically; preserve source refs.
- **audit**: report unindexed sources, unsourced notes, orphans, oversized notes, stale questions, weak MOCs.
- **project `<name>`**: create `wiki/projects/<name>/{Inputs,Process,Outputs,Feedback}/` + scoped `GEMINI.md`; link to wiki + project index.
- **profile**: create/update `wiki/profile/user-profile.md`; durable info only; one question at a time.
- **log**: append a dated entry to `index/Log.md`.

## Templates

Concept/mental-model/framework/tool note: frontmatter (`type,status,tags,source,created,updated,related`) + `# Title` / `## Definition` (one line) / `## Core idea` / `## Key points` / `## Connections` (`[[note]] - why`) / `## Source references` (`path`) / `## Open questions`.

Source summary (`wiki/sources/`): frontmatter (`type: source-summary, source, author, date_ingested, tags`) + `## What this is` / `## Key ideas` / `## Extracted notes` (`[[note]]`) / `## Open questions` / `## Source path` (`path`).

Question (`wiki/questions/`): frontmatter (`type: question, status: open, created, related`) + `## Why it matters` / `## Current evidence` / `## Possible directions` / `## Related`.

## Output formats

```text
ask ->  Answer / Evidence used: <paths> / Missing or uncertain: ...
audit -> Unindexed sources / Notes without sources / Orphans / Oversized / Next actions
dedupe -> pairs + suggested action + reason
```
moc -> `# MOC - Topic` / Overview / Core notes (`[[note]] - why`) / Sources / Open questions / Next actions.
log -> `## YYYY-MM-DD` / Created / Updated / Open questions.

## Rules

Tags lowercase kebab-case, durable, organic - no premature taxonomy. 2-3 strong links/note (explain, contrast, apply, depend); no keyword/graph-decoration links. Good note: atomic, sourced, reusable, scannable.

## Output style

```text
Read: ... / Created: ... / Updated: ... / Skipped: ... / Uncertain: ... / Next: ...
```
No internal-step narration, no motivational commentary.

## Safety

Read-only for external tools. No external actions (email, calendar, deletes) unless instructed. No secrets in notes. Vault stays portable and model-agnostic.

Heuristic: Capture -> Organize -> Distill -> Express. Make useful knowledge easy to retrieve, combine, apply - not store everything.
