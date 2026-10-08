# Add a tool or plugin to an agent

Use a deterministic tool for parsing, bounded API calls, or repeatable operations. Use a lifecycle plugin only when the behavior must run outside the model's chosen tool calls.

Load [opencode-plugin-creator](../../opencode-plugin-creator/SKILL.md) to implement either: it owns the released tool/plugin APIs, loading paths, hooks, and templates. Verify the target host/package version before copying code from V2 documentation or a third-party plugin.

For agent integration:

1. Discover the exact registered tool name and available arguments.
2. Grant only the intended agent access through `permission`; custom/MCP names and wildcard patterns use the same access policy as other tools.
3. Update the agent's prompt only when it needs a tool-selection rule or an output contract.
4. Test one successful call and one denied/invalid-input path in the target runtime.

Do not infer a read-only boundary from `edit: deny` when arbitrary tools or shell commands remain enabled. Do not infer that a declared plugin permission hook is an enforcement point without checking its released host consumer.

For native task background behavior, use [orchestrator-pattern.md](orchestrator-pattern.md#experimental-background-work). For launch-time credentials, use the [configuration secret rules](agent-config-reference.md#configuration-secrets); resolve required environment values before configuration loads.
