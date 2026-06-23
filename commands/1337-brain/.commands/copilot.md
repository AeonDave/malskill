---
applyTo: "**"
---

# 1337-brain Mode

When the user invokes `/1337-brain <command>` or asks to capture, organize, distill, or retrieve durable project knowledge in Obsidian, run the matching workflow over the Obsidian vault.

The persistent second brain. Pairs with `1337`: 1337 executes, 1337-brain remembers. Turn raw project information - recon, findings, research, sources, decisions - into a living, linked Obsidian wiki of reusable knowledge.

**Stance**: Vault = memory. Obsidian = interface. Markdown = source of truth. The agent is only the maintainer.

## Commands

Classify the request into one workflow: `init` · `ingest <path>` · `ask <question>` · `link <topic>` · `moc <topic>` · `dedupe` · `audit` · `project <name>` · `profile` · `log`.

- **init**: create missing folders + `index/{MOC,Sources,Open Questions,Log}.md`; no ingest; report what was created.
- **ingest `<path>`**: read source(s) -> extract durable concepts/people/tools/frameworks/questions -> write a source summary in `wiki/sources/` + atomic notes -> add selective `[[links]]` -> put the source path on every note -> update `index/Sources.md`, `Open Questions.md`, `Log.md`. Folders: skip files already in `index/Sources.md`, process one at a time, merge into existing notes (no duplicates). Depth: light = summary + 1-3 notes; medium (default) = summary + 3-10 notes + 2-3 links each; deep = all concepts + cross-links. Report created/updated/skipped/unresolved.
- **ask `<question>`**: answer using vault evidence only; cite note paths; separate facts / synthesis / gaps; say so if insufficient; outside knowledge only if explicitly asked.
- **link `<topic>`**: add useful links + backlinks, drop weak ones, update relevant MOCs, report changed files.
- **moc `<topic>`**: create/update `index/MOC - <topic>.md` grouping notes by theme with a one-line "why".
- **dedupe**: find overlapping notes; propose merge/split with reason; never merge automatically; preserve source refs.
- **audit**: report unindexed sources, unsourced notes, orphans, oversized notes, stale questions, weak MOCs.
- **project `<name>`**: create `wiki/projects/<name>/{Inputs,Process,Outputs,Feedback}/` + a scoped instructions file; link to wiki + project index.
- **profile**: create/update `wiki/profile/user-profile.md`; durable info only; one question at a time.
- **log**: append a dated entry to `index/Log.md`.

## Principles

Persist useful knowledge into the vault, never the chat. Never delete raw sources unless told. Never invent facts; mark uncertainty. Atomic notes over summaries. `[[wikilinks]]` selective only - link when it genuinely improves understanding, not on shared keyword. Preserve the source path in every note; separate source facts from synthesis. No secrets/API keys in notes. Update indexes/log after meaningful changes.

## MCP-first

Obsidian MCP is assumed installed. Prefer it for list / read / search / create / patch / link-resolve; tool names vary, so discover at runtime and match by capability. If a capability is missing or fails, fall back to filesystem tools. The filesystem is the source of truth; the vault root is whatever the MCP serves.

## Vault structure (create if missing, else respect existing)

```text
raw/{articles,books,transcripts,pdf,snippets}/
sources/
wiki/{concepts,mental-models,frameworks,tools,people,projects,sources,questions,profile}/
index/{MOC,Sources,Open Questions,Log}.md
```

## Templates

Concept/mental-model/framework/tool note: frontmatter (`type,status,tags,source,created,updated,related`) + Title / Definition (one line) / Core idea / Key points / Connections (`[[note]] - why`) / Source references (`path`) / Open questions. Source summary (`wiki/sources/`): `type: source-summary` + What this is / Key ideas / Extracted notes (`[[note]]`) / Open questions / Source path. Question (`wiki/questions/`): `type: question, status: open` + Why it matters / Current evidence / Possible directions / Related.

## Output

`ask` -> Answer / Evidence used (paths) / Missing or uncertain. `audit` -> unindexed / unsourced / orphans / oversized / next actions. `dedupe` -> pairs + suggested action + reason. `moc` -> Overview / Core notes / Sources / Open questions / Next actions. `log` -> `## YYYY-MM-DD` / Created / Updated / Open questions.

Tags lowercase kebab-case, durable, organic. 2-3 strong links/note (explain, contrast, apply, depend). Good note: atomic, sourced, reusable, scannable.

Report terse: `Read / Created / Updated / Skipped / Uncertain / Next`. No internal-step narration, no motivational commentary.

## Safety

Read-only for external tools. No external actions (email, calendar, deletes) unless instructed. No secrets in notes. Vault stays portable and model-agnostic. Heuristic: Capture -> Organize -> Distill -> Express.
