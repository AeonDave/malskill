# Claude Managed Agents (cloud harness)

For when the user wants a **programmatic / long-running / cloud** agent rather than a Claude Code subagent. Managed Agents is Anthropic's hosted agent harness on the Claude API: you define the agent, Anthropic runs the agent loop, tool execution, and a secure sandbox.

> Source: platform.claude.com → *Managed Agents*. Beta. Cross-check the live docs before shipping — the API surface evolves.

## Subagent vs. Managed Agent — which to build

| | Claude Code subagent | Claude Managed Agent |
|---|---|---|
| Lives as | `.md` file under `.claude/agents/` | an agent object created via the API |
| Runs in | your Claude Code session | Anthropic-managed (or self-hosted) sandbox |
| Best for | isolating work inside an interactive session; tool boundaries; team-shared roles | long-running / async tasks, minutes-to-hours, multiple tool calls, no agent loop to build |
| Invoked by | Claude delegating, `@`-mention, `--agent` | your application sending events over the API |
| State | fresh per invocation (or fork) | stateful sessions: persistent filesystem + history server-side |
| You build | a Markdown file | a small client that creates the agent, an environment, and sessions |

If the user is working *inside Claude Code* and wants a focused helper, build a **subagent** (the rest of this skill). Reach for Managed Agents when they want an autonomous agent their own software drives.

## The shared mental model

Both incarnations are the same five things: **model + system prompt + tools + MCP servers + skills.** A Managed Agent just adds managed infrastructure around them. Everything you know about writing a sharp system prompt, scoping tools to least privilege, and routing to the right model carries over — see [system-prompt-patterns.md](system-prompt-patterns.md).

## Four core concepts

| Concept | What it is |
|---|---|
| **Agent** | The model, system prompt, tools, MCP servers, and skills. Create once, reference by ID across sessions. |
| **Environment** | Where sessions run: an Anthropic-managed cloud sandbox, or a self-hosted sandbox on your infrastructure. |
| **Session** | A running agent instance in an environment, performing a task and producing outputs. Stateful and resumable. |
| **Events** | Messages exchanged with the agent: user turns, tool results, status updates. Streamed back over SSE. |

## How it works

1. **Create an agent** — define model, system prompt, tools, MCP servers, skills. Reusable by ID.
2. **Create an environment** — cloud sandbox, or self-hosted for compliance/data-residency.
3. **Start a session** — references your agent + environment.
4. **Send events, stream responses** — send user messages as events; Claude autonomously executes tools and streams results over server-sent events. History is persisted server-side.
5. **Steer or interrupt** — send more user events to redirect mid-run, or interrupt to change direction.

## Built-in tools available to the agent

- **Bash** — run shell commands in the sandbox.
- **File operations** — read, write, edit, glob, grep.
- **Web search and fetch** — search the web, retrieve URLs.
- **MCP servers** — connect external tool providers.

(Full list and config: the *Tools* page in the Managed Agents docs.)

## When to use Managed Agents

- **Long-running execution** — minutes to hours, many tool calls.
- **Cloud infrastructure** — secure sandboxes with pre-installed packages and network access.
- **Self-hosted execution** — sandboxes on infrastructure you control for compliance.
- **Minimal infrastructure** — no agent loop, sandbox, or tool-execution layer to build.
- **Stateful sessions** — persistent filesystem and conversation history across interactions.

## Beta access and constraints

- All Managed Agents endpoints require the beta header **`managed-agents-2026-04-01`** (the SDKs set it automatically).
- Needs a Claude API key; enabled by default for API accounts. MCP tunnels and "dreaming" are a more limited preview.
- **Stateful by design** → sessions store history, sandbox state, and outputs server-side. Therefore **not** currently eligible for Zero Data Retention or HIPAA BAA coverage. You can delete sessions and uploaded files via the API at any time.
- Also available on Claude Platform on AWS with some feature/session differences.

## Authoring checklist (parity with subagents)

- System prompt: role + workflow + output contract, same craft as a subagent body.
- Tools: grant least privilege; only what the task needs.
- Model: route by difficulty/cost.
- MCP/skills: attach the external tools and methodology the task requires.
- Test the loop with a bare-bones prompt first, then tighten where it goes wrong — let Claude be an agent before over-specifying.
