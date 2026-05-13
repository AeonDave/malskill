# Tools

Load this file when designing callable capabilities for the model.

## Use a tool when

- the model needs to trigger an action
- the model needs a parameterized query or computation
- the operation may have side effects
- the operation is not naturally represented as stable URI-addressed context

## Design principles

### 1. Pick the right abstraction level

Prefer task-oriented tools over thin wrappers around every backend endpoint.

- Better: `schedule_meeting(participants, topic)`
- Worse: `list_users`, `list_events`, `create_event`, `send_invite` when the model always needs the whole chain

### 2. Optimize for token efficiency

- prefer search/filter over dump-all
- paginate large result sets
- offer concise summaries first
- avoid returning backend-only fields the model cannot use

### 3. Write precise descriptions

Tool descriptions are model-facing interface docs.

Include:

- what the tool does
- when to use it
- parameter expectations and formats
- constraints or caveats

### 4. Keep outputs meaningful

Return the fields needed to decide the next step, not every technical detail you happen to have.

### 5. Support long-running work responsibly

- log progress
- use explicit timeouts
- rate limit where needed
- fail clearly

## Verified Python pattern

```python
@mcp.tool()
async def search_notes(query: str, limit: int = 5) -> str:
    """Search notes by keyword and return the most relevant matches."""
    ...
```

## Tool errors

Use a protocol error when the request itself is malformed or the session is broken.

Use an execution result marked as an error when:

- the tool ran but the business operation failed
- the model can plausibly recover or try another path
- you want the host/model to see a structured failure rather than a crashed session

## Schema hygiene

- type every argument
- avoid vague `dict[str, Any]` inputs for public tools unless unavoidable
- keep parameter counts small
- use defaults only when they produce predictable behavior
- do not hide required context inside ambient global state

## Testing checklist

- happy path
- invalid params
- empty-result path
- timeout or upstream failure path
- large-result path
- host-visible error behavior

## Common mistakes

- one tool per raw API endpoint
- several overlapping tools that force the model to guess
- descriptions with no examples or no usage cues
- huge responses when a smaller result plus a follow-up tool would be better
- using tools for stable read-only content that should have been a resource
