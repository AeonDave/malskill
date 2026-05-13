# Python Local Servers

Load this file when implementing the server itself.

## Official baseline

Use the **official** Python SDK first.

- Python 3.10+
- `uv add "mcp[cli]" httpx`
- explicit imports from `mcp`, not a similarly named third-party package by accident

The official `FastMCP` import path is:

```python
from mcp.server.fastmcp import FastMCP
```

## Suggested project shape

```text
my-mcp-server/
├── pyproject.toml
├── server.py
├── core.py          # domain logic
└── adapters.py      # API/db/filesystem helpers
```

Keep `server.py` small. It should define the MCP surface and call helpers.

## Minimal stdio server

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("notes")


@mcp.tool()
def ping() -> str:
    """Return a health-check string."""
    return "pong"


if __name__ == "__main__":
    mcp.run(transport="stdio")
```

## Verified resource and prompt syntax

The official Python SDK examples also confirm these registration patterns:

```python
@mcp.resource("greeting://{name}")
def get_greeting(name: str) -> str:
    """Get a personalized greeting."""
    return f"Hello, {name}!"


@mcp.prompt()
def greet_user(name: str, style: str = "friendly") -> str:
    """Generate a greeting prompt."""
    return f"Write a {style} greeting for {name}."
```

Resource decorators also support options such as `mime_type`, `annotations`, `icons`, and static or templated URIs. Prompt decorators support optional metadata such as `title` and `description`.

## Implementation rules

- Use type hints everywhere on public tool/resource/prompt functions.
- Treat docstrings as model-facing guidance, not as developer-only comments.
- Push network/database/filesystem work into helper functions or service objects.
- Use async handlers when calling network services or other async APIs.
- Return concise, agent-friendly data shapes first; expand only when needed.

## Local stdio client harness

Use a small harness before involving a desktop host:

```python
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


server_params = StdioServerParameters(
    command="uv",
    args=["run", "server.py"],
)


async with stdio_client(server_params) as (read, write):
    async with ClientSession(read, write) as session:
        await session.initialize()
        tools = await session.list_tools()
        print([tool.name for tool in tools.tools])
```

Useful variations:

- use `env={...}` when the server needs explicit environment variables
- use `sys.executable` when you want an exact Python interpreter path
- add callbacks only for capabilities you are explicitly testing

## Naming and packaging trap

Broader web search may surface other Python projects that also use the name “FastMCP”. Keep the skill centered on the official `mcp` package unless the user explicitly chooses another ecosystem.

## First-pass checklist

- One server instance
- One trivial tool that proves connectivity
- No stdout logging
- Absolute paths in any host config or harness args
- Inspector or local client harness passing before desktop-host setup
