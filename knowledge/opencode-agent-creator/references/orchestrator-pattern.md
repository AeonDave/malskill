# Supervisor + Hidden Subagents — Orchestrator Pattern

Field-tested pattern for an OpenCode team: one visible primary that thinks and delegates, plus a roster of hidden subagents that execute asynchronously.

## Why this shape

- **One visible entry point.** Only the supervisor is `mode: primary`; everything else is `hidden: true` subagent. The user talks to one agent; complexity hides behind it.
- **Isolated context per worker.** Each dispatch spins up a fresh session with its own context window and pinned model.
- **Async Unblocked Flow.** By using the `background-agents` plugin, the supervisor remains responsive. It can peek and steer subagents while they run in the background.

## Async Delegation Usage (CRITICAL)

OpenCode delegates tasks to subagents via the `delegate` tool instead of tracking execution sequentially.

1. **Size timeouts per task**: Use `timeout_minutes` intelligently. Provide a short window for lookups and `0` for deep endless exploitation where you intend to manually steer or stop.
2. **Never poll blindly**: `delegation_status` is instant but you shouldn't sit and loop it. Wait for `<task-notification>`.
3. **Peek before Steering**: Use `delegation_peek(id)` to read the live transcript of a subagent. Do not guess what it is doing—read its actual internal thoughts before you `delegation_steer(id, msg)` it.
4. **Prevent Hallucination**: Instruct subagents to return failures rather than blindly guessing syntax for missing tools.

## Supervisor prompt skeleton

```markdown
---
description: Supervisor for complex tasks.
mode: primary
permission:
  task:
    "*": deny
    "team-*": allow
  delegate: allow
  "delegation_*": allow
---
You are the primary supervisor. You plan, decompose, dispatch, and review.

## Roster
| ID | Domain |
|----|--------|
| team-x | <bounded domain> |

## Dispatch protocol
Invoke subagents with the `delegate` tool. Each packet MUST be self-contained. Include:
- target/context, constraints, and the exact deliverable + success signal.
- The precise skill the subagent needs to load.
- Set a proper `timeout_minutes` (e.g. 0 for endless, 10 for standard scan).
- If it drifts, use `delegation_peek(id)` then `delegation_steer(id, msg)`.
```
