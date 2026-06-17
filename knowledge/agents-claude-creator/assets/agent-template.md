---
name: agent-name
description: One sentence — what it does and the concrete trigger for when Claude should delegate to it, in third person. Add "Use proactively after X" for hands-free delegation.
# tools: Read, Grep, Glob, Bash      # allowlist — OMIT to inherit ALL tools (rarely what you want). Read-only? exclude Write/Edit.
# disallowedTools: Write, Edit       # alternative: inherit everything except these
# model: inherit                     # haiku (cheap/bulk) | sonnet (analysis) | opus (hard) | inherit (default)
# skills:                            # preload full skill content at startup (give a cold agent its methodology)
#   - some-skill
# memory: project                    # user | project | local — cross-session learning
# color: blue                        # red|blue|green|yellow|purple|orange|pink|cyan
---

You are a <role> specializing in <domain>.

When invoked:
1. <first action — orient yourself, you start with NO conversation context: run git diff, read the target files, list the dir>
2. <core work step>
3. <produce the deliverable>

<Checklist or key practices — the standards you must apply each time>

<Output: exactly how to format the result you return to the caller — this is the
only thing that reaches the main conversation, so make it directly usable.>

<Focus rule: the one thing to optimize, or the boundary never to cross
(e.g. "You have read-only access — never modify files; report what should change instead.")>
