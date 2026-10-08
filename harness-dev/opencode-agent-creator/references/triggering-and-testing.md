# Test discovery, routing, and boundaries

Use an isolated project/config directory for checks; do not change the user's global agent roster. Record `opencode --version` and use a fresh process after editing definitions.

## Structural checks

- Parse every Markdown frontmatter block as YAML; check mode, permission value shapes, positive `steps`, exact agent identity, and any model pin.
- Run `opencode agent list` from the intended project and inspect the resolved permission rules, not just presence of a name.
- Test nested names and duplicate/overridden definitions when used. Hidden workers can still appear in the list; `hidden` affects autocomplete.
- Verify `default_agent` names an existing visible primary/all agent.
- Check `opencode models` before asserting a pin is available. Parsing a model ID does not prove access, quota, or generation quality.

## Behavioral checks

| Promise | Meaningful check |
|---|---|
| Correct routing | Give a realistic request without naming the worker, plus a near miss; inspect the actual dispatched role. |
| Read-only work | Ask for a finding and a fix; verify no mutations. Check Bash and custom/MCP tools as well as `edit`. |
| Self-contained dispatch | Start a fresh child using only the packet; confirm it has enough target/context information. |
| Continued context | Resume the returned `task_id` with a correction; verify the same child session was used. |
| Leaf/nested delegation | Inspect Task permissions and test the configured depth boundary. |
| Parallel work | Use independent tasks with disjoint writes; inspect child execution and integration results. |
| Experimental background | Verify early return, completion/error notification, and cancellation on the target version. |

Test permissions using harmless temporary artifacts. A prompt saying "read-only" is not evidence that the tool policy enforces it. Conversely, provider unavailability does not prove a routing/permission defect.

Fix the mechanism implicated by the failure: missing agent -> discovery/identity; wrong role -> description/roster; wrong context -> packet/resumption; unexpected tool use -> permissions; unusable result -> output contract. Recheck the affected behavior after the edit.

Report schema/list checks separately from live model tests. Name any routing, tools, provider, or background behavior not exercised.
