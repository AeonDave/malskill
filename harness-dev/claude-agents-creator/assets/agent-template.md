---
name: agent-name
description: Performs one bounded task. Use when its concrete trigger occurs.
tools: Read, Grep, Glob              # add an execution tool only when required
# disallowedTools: Write, Edit       # alternative for a deliberately inherited tool set
model: inherit                      # explicit parent model; omission permits other defaults
# skills:                            # preload full skill content at startup (give a cold agent its methodology)
#   - some-skill
# memory: project                    # enables Read/Write/Edit when auto memory is on
# omitClaudeMd: true                 # only when the delegation brief supplies required rules
# isolation: worktree                # verify the base and supplied change set
# color: blue                        # red|blue|green|yellow|purple|orange|pink|cyan
---

You are a <role> specializing in <domain>.

When invoked:
1. <inspect the supplied task inputs with the granted tools>
2. <core work step>
3. <produce the deliverable>

<Checklist or key practices — the standards you must apply each time>

<Output: a usable result with evidence and any incomplete or blocked work.>

<Focus rule: the one thing to optimize, or the boundary never to cross
(e.g. "You have read-only access — never modify files; report what should change instead.")>
