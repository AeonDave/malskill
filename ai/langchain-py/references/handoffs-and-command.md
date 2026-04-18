# Handoffs, state machines, and Command

Use this file for robust handoff implementations in LangChain 1.2 + LangGraph 1.1.

## Core mechanism

Handoffs are driven by tools that return `Command(update=...)` and mutate state.

```python
from langchain.tools import tool, ToolRuntime
from langchain.messages import ToolMessage
from langgraph.types import Command

@tool
def transfer_to_sales(runtime: ToolRuntime) -> Command:
    return Command(
        update={
            "active_agent": "sales",
            "messages": [
                ToolMessage(
                    content="Transferred to sales",
                    tool_call_id=runtime.tool_call_id,
                )
            ],
        }
    )
```

## Mandatory message pairing rule

When handing off after a tool call, preserve valid conversation structure:

- Include the triggering `AIMessage` tool call.
- Include the corresponding `ToolMessage` with matching `tool_call_id`.

If you skip this pairing, downstream agents can receive malformed history.

## Single-agent middleware vs multi-subgraph handoffs

### Single-agent middleware (default)

- One agent changes prompt/tools by reading state in middleware.
- Simpler and safer for most workflows.

### Multi-agent subgraphs

- Distinct agent nodes and explicit routing (`goto=...`, `graph=Command.PARENT`).
- More powerful but easier to break with bad context transfer.

## State-machine implementation pattern

1. Define `AgentState` extension with `current_step`.
2. Define step tools returning `Command(update={..., "current_step": ...})`.
3. Use `@wrap_model_call` middleware to load step-specific prompt/tools.
4. Persist with checkpointer for multi-turn continuity.

## Common failure modes

- Updating step state without a checkpointer -> transitions reset between turns.
- Passing full subagent message history in handoffs -> bloat/confusion.
- Returning tool result without `ToolMessage` where model expects one.

## Source links

- Handoffs conceptual: https://docs.langchain.com/oss/python/langchain/multi-agent/handoffs
- Customer-support handoff tutorial: https://docs.langchain.com/oss/python/langchain/multi-agent/handoffs-customer-support
- `Command` reference: https://reference.langchain.com/python/langgraph/types/Command
