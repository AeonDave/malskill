# Version scope: LangChain 1.2.x

This skill targets **LangChain 1.2.x** semantics and APIs.

## Baseline assumptions

- Python 3.10+
- `langchain>=1.2,<1.3`
- `langgraph>=1.1`
- Use `langchain.agents.create_agent` as the default agent factory

## Why version scope matters

LangChain changed substantially from pre-1.0 to 1.x. The same snippets can fail if copied from old blogs or v0 docs.

## 1.x migration-critical rules

- Use `from langchain.agents import create_agent` (not `langgraph.prebuilt.create_react_agent`).
- Use `system_prompt` (renamed from old `prompt`).
- For tool-aware state updates, use tools returning `Command(update=...)`.
- Prefer middleware for dynamic behavior (`dynamic_prompt`, `wrap_model_call`, `wrap_tool_call`).
- Custom `state_schema` is TypedDict-based (`AgentState` extension); avoid old Pydantic/dataclass state patterns.

## 1.2 highlights relevant to this skill

From official changelog for `langchain v1.2.0`:

- `create_agent`: improved support for provider-specific tool definitions via `extras` on tools.
- Better strict schema adherence with `response_format` (notably `ProviderStrategy`).

## Guardrails for generated code

- If a snippet uses `LLMChain` or old chain abstractions, treat it as legacy (`langchain-classic`).
- Prefer explicit model IDs and avoid stale provider examples.
- If code references deprecated stream node names (`"agent"`), adapt to 1.x model-node semantics.

## Source links

- Migration guide: https://docs.langchain.com/oss/python/migrate/langchain-v1
- Changelog: https://docs.langchain.com/oss/python/releases/changelog
- `create_agent` reference: https://reference.langchain.com/python/langchain/agents/factory/create_agent
