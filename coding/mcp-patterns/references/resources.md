# Resources

Load this file when exposing read-only context through URIs.

## Use a resource when

- the content is read-only from the model’s perspective
- the content naturally maps to a stable URI
- you want the host/client to browse or fetch context without “calling a tool”

## Resource shapes

- **static resource**: one fixed URI
- **resource template**: URI pattern with parameters
- **text resource**: plain strings or structured text
- **binary resource**: bytes plus the correct MIME type

## Verified Python pattern

```python
@mcp.resource("greeting://{name}")
def get_greeting(name: str) -> str:
    """Get a personalized greeting."""
    return f"Hello, {name}!"
```

The official Python SDK examples also show optional metadata such as `mime_type`, `annotations`, and `icons`.

## URI design rules

- use stable, human-readable schemes
- make parameters obvious from the template
- keep one URI meaning per resource
- version explicitly if semantics change in a breaking way

## Metadata that matters

- MIME type
- annotations such as audience/priority when supported
- clear descriptions or titles where the SDK surface allows them

## Resource behavior patterns

- aggregate only the amount of context the host/model can actually use
- paginate or split large collections instead of creating one giant payload
- prefer deterministic reads
- send change notifications if the host depends on freshness and subscriptions are part of the flow

## Resource vs tool boundary

Choose a **resource** if the operation is a read.

Choose a **tool** if the model needs to:

- mutate something
- trigger computation with side effects
- request a workflow rather than fetch stable context

## Common mistakes

- using resources for writes or remote actions
- overloading one template with unrelated meanings
- omitting MIME types for non-plain-text content
- dumping an entire dataset when filtered or per-item resources would be better
- forgetting that host support for browsing/subscriptions can vary
