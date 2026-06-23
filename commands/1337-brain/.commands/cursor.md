---
description: Maintain an Obsidian vault as a project second brain - ingest sources, link atomic notes, answer grounded questions, build MOCs, dedupe, audit. Obsidian MCP first, filesystem fallback.
globs: ""
alwaysApply: false
---

# 1337-brain

The persistent second brain. Pairs with `1337`: 1337 executes, 1337-brain remembers. Turn raw project information into a living, linked Obsidian wiki of reusable knowledge.

Vault = memory. Obsidian = interface. Markdown = source of truth. Agent = maintainer.

## Dispatch

On a request to capture, organize, distill, or retrieve durable project knowledge in Obsidian, classify into one workflow: `init` · `ingest <path>` · `ask <question>` · `link <topic>` · `moc <topic>` · `dedupe` · `audit` · `project <name>` · `profile` · `log`.

## Principles

Persist to the vault, not the chat. Never delete raw sources unless told. Never invent facts; mark uncertainty. Atomic notes over summaries. `[[wikilinks]]` selective only (genuine understanding gain, not shared keyword). Preserve source path on every note; separate source facts from synthesis. No secrets in notes. Update indexes/log after meaningful changes.

## MCP-first

Obsidian MCP assumed installed - prefer it for list / read / search / create / patch / link-resolve; discover tool names at runtime, match by capability. Missing or failing -> filesystem fallback (source of truth). Vault root = whatever the MCP serves.

## Vault structure (create if missing, else respect existing)

```text
raw/{articles,books,transcripts,pdf,snippets}/  sources/
wiki/{concepts,mental-models,frameworks,tools,people,projects,sources,questions,profile}/
index/{MOC,Sources,Open Questions,Log}.md
```

## Commands

- **init**: create missing folders + `index/{MOC,Sources,Open Questions,Log}.md`; report what was created.
- **ingest `<path>`**: source(s) -> source summary in `wiki/sources/` + atomic notes -> selective links -> source path on each -> update `index/Sources.md`, `Open Questions.md`, `Log.md`. Folders: skip already-indexed, one at a time, merge (no duplicates). Depth: light (summary+1-3), medium default (summary+3-10+2-3 links), deep (all+cross-links). Report created/updated/skipped/unresolved.
- **ask `<question>`**: vault evidence only; cite paths; separate facts/synthesis/gaps; outside knowledge only if asked.
- **link `<topic>`**: add useful links + backlinks, drop weak, update MOCs, report changes.
- **moc `<topic>`**: create/update `index/MOC - <topic>.md`, notes by theme + one-line why.
- **dedupe**: propose merge/split with reason; never auto-merge; keep source refs.
- **audit**: unindexed sources, unsourced notes, orphans, oversized notes, stale questions, weak MOCs.
- **project `<name>`**: `wiki/projects/<name>/{Inputs,Process,Outputs,Feedback}/` + scoped rules file; link to wiki + project index.
- **profile**: `wiki/profile/user-profile.md`; durable info only; one question at a time.
- **log**: append dated entry to `index/Log.md`.

## Templates

Concept note: frontmatter (`type,status,tags,source,created,updated,related`) + Title / Definition (one line) / Core idea / Key points / Connections (`[[note]] - why`) / Source references (`path`) / Open questions. Source summary (`wiki/sources/`): `type: source-summary` + What this is / Key ideas / Extracted notes / Open questions / Source path. Question (`wiki/questions/`): `type: question, status: open` + Why it matters / Current evidence / Possible directions / Related.

## Formats

ask -> Answer / Evidence used (paths) / Missing or uncertain. audit -> unindexed / unsourced / orphans / oversized / next. dedupe -> pairs + action + reason. moc -> Overview / Core notes / Sources / Open questions / Next actions. log -> `## YYYY-MM-DD` / Created / Updated / Open questions.

## Rules + style

Tags lowercase kebab-case, durable, organic. 2-3 strong links/note (explain/contrast/apply/depend). Good note: atomic, sourced, reusable, scannable. Report terse: `Read / Created / Updated / Skipped / Uncertain / Next`. No internal-step narration, no motivational commentary.

## Safety

Read-only for external tools; no external actions unless instructed; no secrets in notes; vault portable and model-agnostic. Heuristic: Capture -> Organize -> Distill -> Express.
