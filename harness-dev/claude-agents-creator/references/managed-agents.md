# Claude Managed Agents

Load for an application-driven hosted agent, not a worker inside Claude Code. Use the [current API overview](https://platform.claude.com/docs/en/managed-agents/overview) and [agent setup contract](https://platform.claude.com/docs/en/managed-agents/agent-setup); Claude Code frontmatter is a separate format.

## Define and run

1. Define a versioned agent with a `name`, available model ID, `system`, and required tools. API fields such as `mcp_servers` use snake_case; Code aliases and tool-name strings are not interchangeable with API model/tool objects.
2. Configure a cloud or self-hosted environment and its networking. Enumerate required hosts rather than assuming package-manager access grants web search/fetch access.
3. Create a session referencing the agent and `environment_id`. An agent ID string selects its latest version; pin an explicit version for reproducible execution.
4. Start work through a `user.message` event, or use `initial_events` at creation. Creating a session alone does not start the agent loop.
5. Stream events and inspect the result. `session.status_idle` means the agent has stopped working; verify the intended artifact and stop reason before treating the task as complete.

All Managed Agents endpoints currently require `managed-agents-2026-04-01`; supported SDK beta methods set the header. Pin and check the SDK's exported types before generating a client. The [quickstart](https://platform.claude.com/docs/en/managed-agents/quickstart) supplies current CLI/SDK setup; `ant apply` records resource IDs in `claude-lock.json`, which prevents accidental duplicate resources on later applies.

## Versioned sessions and overrides

For a supplied client plus existing agent/environment resources:

```python
session = client.beta.sessions.create(
    agent={"type": "agent", "id": agent.id, "version": agent.version},
    environment_id=environment.id,
)
```

Session overrides use `type: agent_with_overrides`. Omitted fields inherit; supplied `model`, `system`, `tools`, `mcp_servers`, or `skills` replace the base field rather than merging. A model override must restate any required effort or inference geography. See [session creation](https://platform.claude.com/docs/en/managed-agents/sessions) when implementing overrides or `initial_events`.

## Tools, events, and limits

- `agent_toolset_20260401` enables the built-in toolset. Choose only required tools and permission policies; its default policy is not a restrictive allowlist. Use the [tools contract](https://platform.claude.com/docs/en/managed-agents/tools) for per-tool objects and custom-tool handling.
- Open the event stream before sending the initial message when observing the whole turn. Handle tool confirmations/results where configured. Preview deltas are not the committed event history; load the [event-delta contract](https://platform.claude.com/docs/en/managed-agents/event-deltas) for a streaming UI.
- For a bounded session, configure its budget at creation. `max_list_cost.amount` is a string of whole US cents. Enforcement happens between model requests, so the crossing request can finish above the cap. Use [session budgets](https://platform.claude.com/docs/en/managed-agents/budgets) for updates and multiagent accounting.
- Sessions persist conversation and sandbox state. Verify the required data-handling and deletion behavior before uploading task data; deleting a session and deleting uploaded files are separate operations.
- For a coordinator with hosted workers, load the [Managed Agents multiagent contract](https://platform.claude.com/docs/en/managed-agents/multiagent-orchestration) rather than using Code's `Agent(...)` configuration.

Verify agent version, environment networking, effective tools/policies, event delivery, interruption/resume, and final artifacts in the intended runtime. Record unexecuted API checks explicitly.
