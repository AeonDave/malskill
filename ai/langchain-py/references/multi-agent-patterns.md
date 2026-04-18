# Multi-agent patterns (LangChain Python)

Use this file when selecting architecture for multi-agent systems.

## Why multi-agent

Use multi-agent when one agent with many tools becomes unreliable, or when you need domain isolation, parallelization, and stronger context boundaries.

## Pattern map

### 1) Subagents (supervisor pattern)

- Main agent calls specialized subagents as tools.
- Strong centralized control.
- Good for domain decomposition (calendar/email/research).
- Tradeoff: extra model calls due to supervisory coordination.

### 2) Handoffs (state-driven)

- Behavior or active agent changes based on state variables (for example `current_step` / `active_agent`).
- Best for conversational flows with sequential constraints.
- Direct user interaction persists through state transitions.

### 3) Skills

- Single controlling agent loads specialized context on demand.
- Great when tool graph is stable but context payloads are large.

### 4) Router

- Routing stage classifies input and dispatches to specialist paths.
- Good for parallel domain fan-out and synthesis.

### 5) Custom workflows (LangGraph)

- Deterministic + agentic orchestration as graph nodes.
- Use when prebuilt patterns cannot enforce required constraints.

## Pattern selection quick rules

- Need user-facing sequential stages (support flow, onboarding)? -> **Handoffs**.
- Need domain specialists with a coordinator? -> **Subagents**.
- Need dynamic retrieval of domain instructions without full multi-agent graph? -> **Skills**.
- Need cheap, parallel expert dispatch for classification-heavy tasks? -> **Router**.
- Need custom control flow and deterministic gates? -> **LangGraph workflow**.

## Performance considerations

- Subagents: often more calls, strong context isolation.
- Handoffs/Skills: often lower repeat-turn cost in stateful conversations.
- Router/Subagents: often better for multi-domain parallel work.

## Design rule: context engineering first

Multi-agent quality depends mostly on **what context each agent sees**:

- Keep each agent’s prompt narrow.
- Pass only required messages/data.
- Avoid forwarding full internal subagent traces unless needed.

## Source links

- Multi-agent overview: https://docs.langchain.com/oss/python/langchain/multi-agent
- Context engineering: https://docs.langchain.com/oss/python/langchain/context-engineering
