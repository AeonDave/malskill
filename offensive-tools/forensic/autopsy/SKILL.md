---
name: autopsy
description: "Autopsy: GUI digital-forensics platform built on Sleuth Kit. Use for disk image examination, timeline analysis, keyword/hash workflows, artifact extraction, and report generation in incident response or legal/eDiscovery-style investigations."
license: Apache-2.0
compatibility: "Windows/Linux/macOS (Java-based). autopsy.com"
metadata:
  author: AeonDave
  version: "1.0"
---

# Autopsy

Case-oriented forensic GUI for image-based investigations.

## Quick Start

1. Create Case -> Add Data Source (disk image/device/logical files).
2. Enable ingest modules (hash lookup, keyword search, recent activity, etc.).
3. Review results by artifact type and timeline.
4. Tag notable items and export final report.

## High-Value Workflows

- Deleted file recovery and metadata review.
- Timeline analysis for user/system activity reconstruction.
- Keyword and hash set triage to prioritize evidence.
- Browser, email, and OS artifact pivoting.

## Practical Flow

1. Verify source and maintain chain-of-custody notes.
2. Run broad ingest first (timeline + file type + hashes).
3. Narrow with targeted keywords and date ranges.
4. Tag + correlate artifacts into event narrative.
5. Generate structured report with only defensible findings.

## Resources

| File | When to load |
|------|--------------|
| `references/forensic-case-flow.md` | Ingest strategy, artifact triage, and reporting best practices |
