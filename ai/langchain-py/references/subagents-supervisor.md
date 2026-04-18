# Supervisor + subagents pattern

Use this file for centralized orchestration with specialized subagents.

## Architecture

Three practical layers:

1. **API tools layer**: strict tools (calendar/email/search/DB APIs)
2. **Subagent layer**: domain specialists wrapping API tools
3. **Supervisor layer**: top-level router/synthesizer using subagent wrappers as tools

## Implementation skeleton

```python
from langchain.agents import create_agent
from langchain.tools import tool

calendar_agent = create_agent(model, tools=[create_calendar_event, get_slots], system_prompt=CALENDAR_PROMPT)
email_agent = create_agent(model, tools=[send_email], system_prompt=EMAIL_PROMPT)

@tool
def schedule_event(request: str) -> str:
    result = calendar_agent.invoke({"messages": [{"role": "user", "content": request}]})
    return result["messages"][-1].text

@tool
def manage_email(request: str) -> str:
    result = email_agent.invoke({"messages": [{"role": "user", "content": request}]})
    return result["messages"][-1].text

supervisor = create_agent(
    model,
    tools=[schedule_event, manage_email],
    system_prompt="Coordinate specialist tools and synthesize results clearly.",
)
```

## Context flow controls

- Upstream to subagent: optionally pass user’s original request context if needed.
- Downstream to supervisor: return concise final summary or structured payload; avoid raw traces.

## Human-in-the-loop

For sensitive actions (`send_email`, transactional ops):

- Use `HumanInTheLoopMiddleware` on subagents.
- Keep checkpointer on supervisor to support pause/resume.

## When to pick supervisor over handoffs

Choose supervisor when:

- Agents should not directly converse with user independently.
- Central orchestration and synthesis quality matter.
- You want clean domain boundaries with tool-like specialist calls.

## Source links

- Subagents tutorial: https://docs.langchain.com/oss/python/langchain/multi-agent/subagents-personal-assistant
- Multi-agent overview: https://docs.langchain.com/oss/python/langchain/multi-agent
