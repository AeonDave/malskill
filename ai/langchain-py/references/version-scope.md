# Version scope: LangChain 1.3.x / LangGraph 1.2.x

This skill targets **LangChain 1.3.x** (langchain-core 1.4.x line) and **LangGraph 1.2.x** semantics and APIs.

## Baseline assumptions

- Python 3.10+ (Python 3.9 support was dropped at 1.0 alongside its Oct 2025 EOL)
- `langchain>=1.3,<2`
- `langgraph>=1.2,<2`
- Use `langchain.agents.create_agent` as the default agent factory

## Why version scope matters

LangChain changed substantially from pre-1.0 to 1.x. The same snippets can fail if copied from old blogs or v0 docs. `LangChain 1.0` shipped in October 2025 with a semver commitment: no breaking changes until 2.0.

## 1.x migration-critical rules

- Use `from langchain.agents import create_agent` (not `langgraph.prebuilt.create_react_agent` — the whole `langgraph.prebuilt` module is deprecated; functionality moved to `langchain.agents`).
- Use `system_prompt` (renamed from old `prompt`).
- For tool-aware state updates, use tools returning `Command(update=...)`.
- Prefer middleware for dynamic behavior (`dynamic_prompt`, `wrap_model_call`, `wrap_tool_call`).
- Custom `state_schema` is TypedDict-based (`AgentState` extension); avoid old Pydantic/dataclass state patterns.
- Legacy chain abstractions (`LLMChain`, `initialize_agent`, `AgentExecutor`, old `ConversationBufferMemory` and friends) live in **`langchain-classic`**. `AgentExecutor` reaches **end of maintenance December 2026** — plan migration to `create_agent` (standard tool-calling loops) or a raw LangGraph `StateGraph` (custom control flow).
- `.run(prompt)` is replaced by `.invoke(prompt)`; Pydantic v2 semantics apply throughout.

## 1.3 / LangGraph 1.2 highlights relevant to this skill

- `create_agent`: continued improvements to provider-specific tool definitions via `extras` on tools and stricter schema adherence with `response_format` (`ProviderStrategy`).
- **LangGraph 1.2 per-node execution controls**: configurable timeouts, error-recovery policies, graceful shutdown hooks — use these instead of hand-rolled retry loops around node bodies.
- **Streaming API v3**: typed per-channel projections — downstream consumers subscribe to specific state keys instead of receiving the full graph state on every update.
- **DeltaChannel (beta)**: stores incremental state deltas rather than full snapshots on each checkpoint write — reach for it on large-state graphs where checkpoint I/O dominates.

## Guardrails for generated code

- If a snippet uses `LLMChain` or old chain abstractions, treat it as `langchain-classic` (still importable, but a migration target).
- Prefer explicit model IDs and avoid stale provider examples.
- If code references deprecated stream node names (`"agent"`), adapt to 1.x model-node semantics.
- If a checkpointer is missing from a graph you plan to run in production, add one before shipping — in-memory state is fine for demos only.

## Source links

- Migration guide: https://docs.langchain.com/oss/python/migrate/langchain-v1
- Changelog: https://docs.langchain.com/oss/python/releases/changelog
- `create_agent` reference: https://reference.langchain.com/python/langchain/agents/factory/create_agent
