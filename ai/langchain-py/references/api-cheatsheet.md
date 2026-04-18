# API cheatsheet (LangChain 1.2)

Fast reference for symbols commonly used in this skill.

## create_agent essentials

- `model`: string id or chat model instance
- `tools`: callables / BaseTool / provider tool dicts
- `system_prompt`: `str | SystemMessage`
- `middleware`: sequence of middleware instances
- `response_format`: schema, `ToolStrategy`, or `ProviderStrategy`
- `state_schema`: TypedDict extension of `AgentState`
- `context_schema`: runtime context type
- `checkpointer`: per-thread persistence
- `store`: cross-thread persistence
- `name`: useful for subgraph integration

## ToolRuntime essentials

In tools, `runtime` gives:

- `runtime.state`: mutable short-term state
- `runtime.context`: immutable invocation context
- `runtime.store`: long-term memory store
- `runtime.tool_call_id`: required for proper `ToolMessage` pairing
- `runtime.stream_writer`: progress streaming

## Command essentials

`Command` can control:

- `update`: state update payload
- `goto`: next node/agent routing
- `graph=Command.PARENT`: route to parent graph
- `resume`: interrupt resume payload

## Quality checklist before shipping code

- No legacy imports from `langgraph.prebuilt.create_react_agent`
- No outdated state schema types (use TypedDict/AgentState extension)
- Handoffs preserve tool-call message pairing
- Checkpointer configured for multi-turn stateful workflows
- Middleware order reviewed (prompt/tools/model changes intentional)

## Source links

- Agents docs: https://docs.langchain.com/oss/python/langchain/agents
- Tools docs: https://docs.langchain.com/oss/python/langchain/tools
- Middleware docs: https://docs.langchain.com/oss/python/langchain/middleware
- create_agent reference: https://reference.langchain.com/python/langchain/agents/factory/create_agent
