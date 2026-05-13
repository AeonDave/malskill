# Local Host Integration

Load this file when registering the server with a desktop host.

## Baseline idea

Server code and host registration are different concerns.

- the server implements capabilities
- the host config decides how to launch it
- runtime approvals still happen separately inside the host UI

## Claude Desktop-class config shape

Use a `mcpServers` object with a friendly server name, command, args, and optional env.

```json
{
  "mcpServers": {
    "notes": {
      "command": "uv",
      "args": [
        "--directory",
        "D:/path/to/notes-mcp",
        "run",
        "server.py"
      ],
      "env": {
        "NOTES_API_KEY": "replace-me"
      }
    }
  }
}
```

## Path rules

- use absolute paths
- on Windows, prefer forward slashes or escaped backslashes in JSON
- if `uv` is not found, use the full executable path
- do not rely on the host’s current working directory

## Useful config locations

- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

## Integration workflow

1. confirm the server works in Inspector or a local client harness
2. add host config
3. fully restart the host
4. verify the server appears in the host’s connector/tool UI
5. run one trivial tool first

## Environment variables

- assume only a limited environment is inherited automatically
- pass required variables explicitly through the host config
- keep secrets out of source files and docs examples

## Approval model

Even after the server is configured, the host may still ask the user to approve actions. Do not design the server as if configuration alone grants universal permission.

## Common mistakes

- relative paths in args or `.env` references
- forgetting to fully restart the host
- debugging host config before proving the server works standalone
- storing too much trust in one broad filesystem or network grant
