---
name: ftk-imager
description: "FTK Imager: widely used forensic acquisition tool for disk, files, and volatile memory capture. Use when you need rapid, defensible evidence acquisition and verification before deeper analysis in Autopsy/TSK/FTK/Volatility."
license: Proprietary (free and commercial editions)
compatibility: "Windows-focused; Exterro FTK ecosystem. exterro.com"
metadata:
  author: AeonDave
  version: "1.0"
---

# FTK Imager

Evidence acquisition-first tool for triage and forensic collection.

## What to use it for

- Full disk imaging with verification hashes.
- Targeted logical/file collection when full image is not immediately possible.
- Volatile memory capture in live-response scenarios.
- Preview/triage before escalation.

## Practical acquisition flow

1. Prepare destination media and case naming convention.
2. Acquire image (physical/logical) with metadata notes.
3. Enable/record hash verification results.
4. Export manifest + acquisition logs.
5. Store immutable original + working copy for analysis.

## Analyst notes

- Prefer full physical image for high-integrity investigations.
- Use targeted acquisition only when scope/time constraints are justified.
- Document every operator action for defensibility.

## Resources

| File | When to load |
|------|--------------|
| `references/acquisition-tricks-and-flow.md` | Repeatable imaging workflow, flash-drive usage patterns, and chain-of-custody tips |
