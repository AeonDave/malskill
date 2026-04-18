# Tavily integration with LangChain

Use this file when the agent needs web search grounded in current sources.

## Package and credentials

```bash
pip install -U langchain-tavily
```

Set `TAVILY_API_KEY` in environment.

## Minimal setup

```python
from langchain_tavily import TavilySearch
from langchain.agents import create_agent

tavily_search = TavilySearch(max_results=5, topic="general", search_depth="basic")
agent = create_agent(model="openai:gpt-4.1", tools=[tavily_search])
```

## Practical invocation strategy

- Start with `search_depth="basic"`.
- Increase to `advanced` only if recall is insufficient.
- Bound result size (`max_results`) to control token costs.
- Use `include_domains` / `exclude_domains` for high-precision routing.

## Multi-agent usage pattern

- Add Tavily only to research-oriented subagents, not to every agent.
- Keep supervisor free of low-level web-search details.
- Return summarized, cited findings back to supervisor.

## Footguns

- Enabling broad raw-content fields for every query can blow context budget.
- Giving Tavily to all agents causes redundant searches and unstable routing.
- Missing tool description clarity leads to misuse by model.

## Source links

- Tavily integration docs: https://docs.langchain.com/oss/python/integrations/tools/tavily_search
- Tavily API parameters: https://docs.tavily.com/documentation/api-reference/endpoint/search
