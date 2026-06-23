---
name: implement-and-review
description: Implement an approved plan, review it, then apply required fixes
---

## implementation-worker
output: implementation.md
progress: true

Implement the approved plan with minimal edits.

## security-reviewer
reads: implementation.md
output: security-review.md

Review the implementation for concrete security risks.

## reviewer
reads: implementation.md
output: review.md

Review the implementation for correctness, regression risk, and missing validation.

## implementation-worker
reads: security-review.md, review.md

Apply only the review fixes that are clearly required.
