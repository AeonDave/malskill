---
name: 1337-brain
description: "Maintain and query an Obsidian knowledge vault. Use /1337-brain for source ingestion, linked notes, project indexes, grounded answers, deduplication, or vault audits."
license: MIT
compatibility: "Requires access to an Obsidian vault through an available connector or filesystem tools."
metadata:
  author: AeonDave
  version: "1.1"
---

# 1337-brain

Run the requested vault workflow; an invocation does not enable a persistent mode or authorize unrelated memory updates.

## Establish the vault contract

Locate the requested vault and inspect its existing conventions. Discover available connector capabilities instead of assuming a particular Obsidian MCP is installed. Use filesystem access only when the root and permission are established; a connector does not necessarily expose a local path.

Preserve existing structure and raw sources. Follow `memory-hygiene` for write authority, scope, secrets, corrections, and provenance. A read-only question does not authorize changes to logs, profile, or caches.

## Choose the workflow

| Command | Work |
|---|---|
| `init` | Create the requested missing structure without replacing existing notes. |
| `ingest <path>` | Check source identity and changes; update its summary and only the reusable notes it supports. Reuse existing concepts. |
| `ask <question>` | Search the smallest relevant index or notes; answer with source paths and distinguish evidence, inference, and gaps. |
| `link <topic>` | Add or repair links that establish a useful relationship. Obsidian derives backlinks from incoming links. |
| `moc <topic>` | Create or update a map of content when it helps navigation across existing notes. |
| `dedupe` | Identify overlap; merge only when requested or already authorized, preserving provenance and updating affected links. |
| `audit` | Report unsourced or contradictory claims, stale pointers, broken links, duplicates, and missing coverage. Correct only within the requested edit scope. |
| `project <name>` | Create the requested project notes and navigation; add agent instruction files only when requested. |
| `profile` | Record only user-provided or confirmed details within the requested scope. |
| `log` | Add a concise dated entry for the requested change. |
| `hot` | Refresh an existing recent-context cache with current pointers; avoid duplicating durable notes. |

Treat these as intent labels, not a requirement that a command parser exists. Ask only for missing information that changes the requested operation.

## Ingestion and retrieval

- Preserve source URL/path, revision or acquisition date where relevant, and unresolved uncertainty. Separate extracted facts from synthesis.
- Choose depth from the source and task; do not manufacture a fixed number of notes or links.
- For previously ingested sources, compare identity or revision before skipping or updating. A matching filename alone does not establish unchanged content.
- Use existing indexes and a recent-context cache when relevant and current; do not read the entire vault or require a cache to exist.
- Correct dependent summaries when an authorized source update changes their meaning. Do not delete originals as routine cleanup.

For a new vault, `sources/`, `wiki/`, and `index/` are optional starting points. Create only directories needed by the requested workflow.

## Note contract

Keep a note focused on a reusable topic, with a short summary, supporting facts, source pointers, and meaningful links. Add YAML properties only when the vault uses them; retain their established types.

Obsidian supports Wikilinks and Markdown links. Use unambiguous paths when names collide. Quote internal links in YAML properties; use a YAML list for aliases. Consult [Obsidian properties](https://help.obsidian.md/properties) and [internal links](https://help.obsidian.md/links) when editing those formats.

A filesystem rename may leave references stale. Use supported link-aware operations where available and check affected references; Obsidian's automatic link-update behavior depends on its settings.

## Verify and report

Inspect created or changed notes, source pointers, affected links, and indexes. Ensure duplicate ingestion does not create duplicate notes. Do not claim the vault is globally consistent after checking only one topic.

Report the answer or changed notes, relevant evidence paths, and unresolved gaps. Keep raw extracts out of the response unless needed to support the conclusion.
