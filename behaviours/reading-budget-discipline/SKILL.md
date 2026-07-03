---
name: reading-budget-discipline
description: "Keep the context window lean when reading large data. Use before opening big files, logs, dumps, PCAPs, decompiler output, research corpora, or a folder of worker artifacts. Enforces grep-first + windowed reads, extract-don't-hoard, and context quarantine (delegate a huge read to a sub-agent that returns a digest)."
license: MIT
compatibility: "AgentSkills-compatible reading/context guidance for coding, research, forensics, and security work."
metadata:
  author: AeonDave
  version: "1.0"
---

# Reading Budget Discipline

Your context is finite; the data isn't. Reading it all back is the failure mode. Pull only the
decisive lines.

## Activation triggers

- About to open a large file, log, dump, binary, PCAP, decompiler output, or research page.
- Consolidating a folder of artifacts (a worker's `raw/`, scan outputs, a `.research/` workspace).
- Tempted to `read` a whole file just to find one fact in it.

## The rules

1. **Grep-first, then window**: to find a fact in a big file, `grep`/search for the line numbers,
   then `read` a **tight window** (`offset`/`limit`) around the hit. Never whole-file to search.
2. **Head-first, windowed**: when you must open a document, read the smallest artifact first (an
   index/README, then the top of the main file). Continue with `offset` only if the head is
   insufficient.
3. **Extract, don't hoard**: keep only the ≤few decisive lines/quote you need; leave the bulk on
   disk. One fact needs one quote, not a page.
4. **Preview before full read**: for an artifact/upload/large tool output, check size + a small
   preview (metadata, head/tail, first few KB) before pulling the blob. Skip the full read when the
   preview answers the question; otherwise paginate with bounded windows.
5. **Tail growing logs by byte offset**: for streaming/appended logs (or long-running shell output),
   read from the last-known byte forward — never re-scan from byte 0. Prefer streaming large tool
   output to a side artifact/file over pulling it inline.
6. **Context quarantine**: if a large artifact must be fully analyzed, **delegate** it to a fresh
   sub-agent that reads it and returns a digest — keep the raw tokens out of your own window.

## Anti-patterns

| Smell | Instead |
|---|---|
| `read` a 5k-line file to find one symbol | `grep` the symbol → `read` a 20-line window |
| Loading a whole log/dump into context | tail/grep the relevant span only |
| Re-reading files a worker already summarized | consolidate from the returned report |
| Pasting a page to "keep it handy" | quote the decisive lines; leave the page on disk |
| Downloading a whole artifact just to look at it | preview metadata + head/tail first; fetch only if needed |
| Re-reading a growing log from byte 0 | tail from the last-known byte offset |
| Pulling a huge command's stdout inline | route it to a side artifact/file; read a window from disk |

## Writing for others' budget

When you produce output others read back (a report, a research file), lead with a one-line answer +
a short TL;DR (the part actually read); push detail below and raw dumps into side files. Keep the
returned report compact — the files are the archive.
