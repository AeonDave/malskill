# Supervisor + Subagents — Orchestrator Pattern

Field-tested pattern for an OpenCode team: one visible primary that thinks and delegates, plus a roster of subagents that execute in isolated child sessions. Built on the **native `task` tool** — the supported, documented way OpenCode does multi-agent work.

## Contents
- [Why this shape](#why-this-shape)
- [The native dispatch model](#the-native-dispatch-model)
- [Supervisor prompt skeleton (lean)](#supervisor-prompt-skeleton-lean)
- [Supervisor prompt skeleton (XML-structured)](#supervisor-prompt-skeleton-xml-structured)
- [Subagent prompt skeleton](#subagent-prompt-skeleton)
- [The dispatch packet (cold-context contract)](#the-dispatch-packet-cold-context-contract)
- [Wave parallelism](#wave-parallelism)
- [Anti-loop and delegation discipline](#anti-loop-and-delegation-discipline)
- [Async / background delegation](#async--background-delegation)

## Why this shape

- **One visible entry point.** Only the supervisor is `mode: primary`; everything else is `hidden: true` subagent. The user talks to one agent; complexity hides behind it.
- **Isolated context per worker.** Each `task` dispatch spins up a fresh child session with its own context window and pinned model. Verbose work never pollutes the supervisor's context.
- **Cost control by routing.** The supervisor "selects a model" only by choosing which pinned agent to dispatch (the native `task` tool has no `model` parameter — see [model-tiering.md](model-tiering.md)).

## The native dispatch model

The supervisor invokes a subagent with the built-in **`task`** tool, which takes exactly three arguments:

```
task(
  subagent_type="reviewer",         # which agent (must be permitted by permission.task)
  description="Review auth diff",   # short label
  prompt="<the full self-contained packet — see below>"
)
```

There is **no `model`, no depth control, no streaming-steer** in native `task`. Dispatches are **synchronous** by default: the supervisor waits for the subagent's final result. To issue several at once (a swarm/wave), the supervisor emits **multiple `task` calls in one turn** — OpenCode runs them concurrently and returns all results. (For true fire-and-forget, see [async / background delegation](#async--background-delegation).)

## Supervisor prompt skeleton (lean)

```markdown
---
description: Supervisor that plans, decomposes, dispatches specialists, and synthesizes. The only visible agent.
mode: primary
permission:
  task:
    "*": deny
    "team-*": allow
    "util-*": allow
  edit: deny          # dispatch-and-review only; specialists do the writing
  bash: deny
---
You are the primary supervisor. You plan, decompose, dispatch, and synthesize.
You do NOT execute noisy or destructive work yourself — you route it.

## Roster
| subagent_type | Domain | Model tier |
|---|---|---|
| team-x | <bounded domain> | specialist |
| team-y | <bounded domain> | specialist |
| util-summarize | bulk summarizing/parsing | utility (cheap) |

## Dispatch protocol
1. Restate the goal and gate scope before any dispatch.
2. Decompose into bounded subtasks, each with ONE deliverable and a success signal.
3. For each subtask, write a SELF-CONTAINED packet (see "dispatch packet") and call
   task(subagent_type=…, description=…, prompt=…). Independent subtasks → emit their
   task() calls together so they run in parallel.
4. Review each result against its success signal; re-dispatch with a tighter packet if weak.
5. Synthesize a single answer. Never paste raw subagent transcripts back to the user.

## Discipline
- Subagents start COLD: anything they must know goes in the packet.
- Push trivial/bulk work to util-* (cheap models); keep reasoning with team-* and synthesis with yourself.
- One well-scoped worker beats three vague ones.
```

## Supervisor prompt skeleton (XML-structured)

Some teams prefer the explicit `<role>/<task>/<workflow>` structure (the OpenAgentsControl house style). It costs more tokens but enforces staged behavior — use it for high-stakes, multi-stage pipelines:

```markdown
---
description: Multi-stage feature orchestrator with validation gates.
mode: primary
temperature: 0.2
permission:
  task: { "*": deny, "team-*": allow }
---
<role>Feature orchestrator coordinating specialists across plan→build→validate stages.</role>
<task>Decompose the request, dispatch specialists per stage, gate each transition on validation.</task>

<workflow>
  <stage id="1" name="Discover">Dispatch a read-only explore/scout to map the target. Gate: context gathered.</stage>
  <stage id="2" name="Plan">Produce the subtask list with dependencies. Gate: every subtask has a deliverable + success signal.</stage>
  <stage id="3" name="Execute">Dispatch specialists per dependency batch (parallel where independent). Gate: all deliverables verified.</stage>
  <stage id="4" name="Synthesize">Integrate, report. Gate: result answers the original goal.</stage>
</workflow>

<discipline>Subagents are cold — inject context into each packet. Never skip a gate. Route bulk work to util-*.</discipline>
```

Both styles are valid; keep one style per team for consistency.

## Subagent prompt skeleton

```markdown
---
description: <assertive, specific — this is what the supervisor reads to route here>
mode: subagent
hidden: true
model: provider/specialist-model     # omit to inherit the supervisor
permission:
  task: deny                          # never re-dispatch
  edit: deny                          # add only if this agent legitimately writes
---
You are a <role> specializing in <domain>.

When invoked you receive a self-contained packet. You start with NO prior context.

1. Load the skills named in the packet via the `skill` tool (bare names, no paths).
2. <core work step — read the target, run the analysis, produce the artifact>
3. Return ONLY the contracted deliverable.

Operating principles:
- <evidence requirement — cite file:line / command output, don't assert>
- <the one boundary never to cross>

Output contract: <exact shape of what you return — keep it tight; this is all that
reaches the supervisor, so make it directly usable, not a context dump.>
```

## The dispatch packet (cold-context contract)

The `prompt` you pass to `task()` is the subagent's **entire world**. It must carry everything:

- **Target & context** — the files, paths, scope, and any facts from the conversation the subagent never saw.
- **Skills to load** — bare skill names ("load `web-exploit-technique` and `evidence-before-claims`").
- **Constraints** — read-only? don't touch `vendor/`? redact secrets before returning?
- **Deliverable + success signal** — exactly what to return and how you'll judge it.

If a subagent keeps missing something, the fix is almost always a fuller packet — not a change to its body.

## Wave parallelism

Adapted from the OpenAgentsControl batch model — parallelize only what is genuinely independent, gate on dependencies:

1. **Build the dependency graph.** Group subtasks into waves where everything in a wave is independent of its peers.
2. **Emit a wave together.** Issue all `task()` calls for a wave in one turn → they run concurrently.
3. **Barrier.** Wait for the whole wave to return before starting the next (a later wave depends on earlier deliverables).
4. **Verify, then proceed.** Check each result against its success signal; re-dispatch failures before advancing.

```
Wave 1 (parallel): task(team-a …)  task(team-b …)  task(team-c …)    # no inter-deps
   ↓ barrier — all three returned and verified
Wave 2 (parallel): task(team-d …)  task(team-e …)                    # depend on wave 1
   ↓ barrier
Wave 3 (single):   task(team-integrate …)                            # depends on all
```

This buys the time savings of parallelism without the chaos of unbounded fan-out.

## Anti-loop and delegation discipline

OpenCode has **no recursion-depth guard** (issue #18100): a subagent that can call `task` can spawn more subagents endlessly. Enforce these:

- **`permission: { task: deny }` on every subagent.** Only the supervisor dispatches. This is the structural guard.
- **Anti-recursion line in subagent prompts** (belt-and-suspenders): "You are a subagent. NEVER use the Task tool to re-delegate your own work. Use Read/Grep/Glob/Bash directly."
- **`steps:` cost cap** on each agent so a confused agent can't burn unbounded iterations.
- **Return failures, don't guess.** Instruct subagents to report "missing input / tool unavailable" rather than hallucinate syntax — a guessing subagent wastes a whole wave.

## Async / background delegation

Native `task` is synchronous. Two ways to get fire-and-forget so the supervisor stays responsive:

- **Native (experimental):** set `OPENCODE_EXPERIMENTAL_BACKGROUND_SUBAGENTS=true`; a running subagent can be sent to the background. Behavior is still moving — treat as preview.
- **Plugin (`opencode-background-agents`):** adds `delegate(prompt, agent)` → returns an id immediately, `delegation_read(id)`, `delegation_list()`. Results persist to disk and **survive context compaction**. Constraints: **read-only subagents only** (write-capable work must use native `task`); 1-hour default timeout; background sessions sit outside the undo/branch tree. Each delegation reuses the named subagent's configured model. Full setup + limits: [plugins-and-tools.md](plugins-and-tools.md).

Rule of thumb: **native `task` for anything that writes or that you need synchronously; background `delegate` for long read-only research you want to run while you keep working.**
