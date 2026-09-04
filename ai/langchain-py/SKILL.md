---
name: langchain-py
description: "Build and maintain production-grade LangChain Python systems (LangChain 1.3.x / LangGraph 1.2.x baseline) with create_agent, middleware, tools, structured output, and multi-agent architectures (subagents, handoffs, router, skills). Activate for Python agent design, debugging, migrations from older APIs, context engineering, and Tavily-backed web search integration."
license: MIT
compatibility: "Python 3.10+. LangChain 1.3.x baseline, LangGraph 1.2.x+."
metadata:
  author: AeonDave
  version: "1.2"
---

# LangChain Python (v1.3-focused)

Practical workflow for building reliable LangChain systems with **correct 1.x APIs** and strong multi-agent design.

## When to activate

- Building or refactoring Python agents with `create_agent`
- Designing multi-agent systems (subagents, handoffs, router, skills)
- Implementing middleware/context engineering/stateful tools
- Integrating Tavily or provider-specific tools
- Migrating snippets from stale pre-1.0 docs to current semantics

---

## Version baseline (important)

Assume **LangChain 1.3.x** semantics (langchain-core on the 1.4.x line) with **LangGraph 1.2.x** unless the user explicitly requests another version.

- Prefer `from langchain.agents import create_agent`
- Prefer middleware-based dynamics (`dynamic_prompt`, `wrap_model_call`, `wrap_tool_call`)
- Use `Command(update=...)` for state updates in tools/handoffs
- Treat old `langgraph.prebuilt.create_react_agent` snippets as migration candidates — the `langgraph.prebuilt` module is deprecated; canonical home is `langchain.agents`
- Legacy chain abstractions (`LLMChain`, `initialize_agent`, `AgentExecutor`, old memory classes) live in **`langchain-classic`**; `AgentExecutor` reaches **end of maintenance December 2026** — migrate to `create_agent` or a raw LangGraph `StateGraph`
- LangGraph 1.2 adds per-node execution controls (timeouts, error-recovery policies, graceful shutdown hooks), the streaming API v3 (typed per-channel projections), and beta `DeltaChannel` for incremental checkpoint writes on large state

If uncertain, load `references/version-scope.md` first.

---

## Recommended workflow

1. **Scope**: identify version, providers, and required capabilities (single agent vs multi-agent).
2. **Choose architecture**:
   - Single agent for simple tasks and small toolsets
   - Subagents for domain separation and centralized coordination
   - Handoffs for sequential/user-facing state transitions
   - LangGraph custom workflow for deterministic control gates
3. **Define tools** with strong names, typed signatures, and clear docstrings.
4. **Engineer context** via middleware (prompt/tool/model/response format selection).
5. **Add memory/persistence** with checkpointer/store only where needed.
6. **Harden** with error middleware, interrupts (HITL), and traceability.
7. **Verify version correctness** (no legacy imports/patterns).

---

## Multi-agent design rules

- **Subagents**: supervisor calls specialists as tools; great for domain boundaries.
- **Handoffs**: tool-driven state transitions; best for staged conversational workflows.
- **Router**: classification + dispatch for fast parallel domain fan-out.
- **Skills**: on-demand context loading while one main agent remains in control.

When implementing handoffs:

- Keep message history valid (tool-call and ToolMessage pairing).
- Use `Command.PARENT` only when explicit parent-graph routing is required.
- Pass minimal context between agents; summarize rather than dumping internal traces.

---

## Tavily integration guidance

Use Tavily as a focused retrieval/search tool, not as a blanket dependency for every agent.

- Add Tavily mainly to research subagents.
- Keep `max_results` and depth bounded to control token/latency costs.
- Use domain filters (`include_domains`, `exclude_domains`) for precision.

Load `references/tavily-integration.md` for concrete patterns.

---

## Anti-patterns

- Mixing pre-1.0 and 1.x APIs in same implementation
- Giving every agent every tool (routing degrades quickly)
- Handoffs without valid message/tool pairing
- Stateful workflows without checkpointer persistence
- Copy-pasting old blog snippets without migration audit

---

## Outcome expectations

- Architecture choice is explicit and justified.
- Generated code is valid for LangChain 1.3.x / LangGraph 1.2.x.
- Multi-agent context boundaries are intentional and testable.
- Tooling and middleware are minimal but sufficient for reliability.

---

## Resources

Load on demand:

- `references/version-scope.md` — 1.3.x / LangGraph 1.2.x scope, migration-critical rules, changelog highlights
- `references/multi-agent-patterns.md` — pattern selection and tradeoffs
- `references/handoffs-and-command.md` — state-machine handoffs, `Command`, message validity
- `references/subagents-supervisor.md` — supervisor/subagent layering and information flow
- `references/tavily-integration.md` — LangChain + Tavily setup and practical constraints
- `references/api-cheatsheet.md` — fast API checklist for `create_agent`, `ToolRuntime`, `Command`
