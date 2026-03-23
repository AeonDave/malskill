---
name: self-improvement
description: "Inject a short self-improvement reminder during OpenClaw bootstrap."
metadata:
  openclaw:
    emoji: "🧠"
    events:
      - agent:bootstrap
---

# Self Improvement Hook

Optional OpenClaw hook that injects a short reminder during bootstrap.

## Purpose

Use this hook when you want each main OpenClaw session to start with a reminder to:
- review existing `.learnings/` entries when relevant
- log non-obvious errors, corrections, and discoveries
- promote durable patterns instead of rediscovering them later

## Notes

- intended as an optional complement to the main skill
- keeps output short to avoid bloating bootstrap context
- skips sub-agent sessions in the handler logic
