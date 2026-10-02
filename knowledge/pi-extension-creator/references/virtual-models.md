# Virtual Models

Load this when building an extension that routes each request to a different physical model — a task/cost/phase router, classifier-driven dispatch, or `provider/auto`-style selection. For base extension APIs, use [api-surface.md](api-surface.md).

A virtual model is a selectable model that picks a physical model (and thinking level) per request. The user selects one model; the router dispatches to a physical pair for each request. Virtual models appear in `/model`, `--model`, scoped models, and settings like any other model.

## Register

```typescript
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

export default function (pi: ExtensionAPI) {
  pi.registerVirtualModel({
    provider: "router",
    id: "auto",
    name: "Auto",
    thinkingLevels: ["low", "high"],
    route(request, ctx) {
      // Keep tool follow-ups and retries on the model that handled the turn.
      const sticky = request.failed ?? request.previous;
      if (request.reason !== "user" && sticky) {
        return { model: sticky.model, thinkingLevel: sticky.thinkingLevel ?? "medium" };
      }
      const id = request.thinkingLevel === "high" ? "claude-sonnet-4-5" : "claude-haiku-4-5";
      return { model: ctx.modelRegistry.find("anthropic", id)!, thinkingLevel: "medium" };
    },
  });
}
```

- `provider` can be any provider ID. On a physical provider the virtual model is available when that provider has credentials; under an unused ID it is always available.
- `id` must not match a physical model ID of that provider (if a catalog refresh later adds one, the virtual model hides it).
- `thinkingLevels` lists the levels offered for selection (default `["off"]`). `contextWindow` and `maxTokens` are shown before the first response. `input` defaults to text and images.
- Re-registering the same `provider`+`id` replaces it. `pi.unregisterVirtualModel(provider, id)` removes it (`pi.unregisterProvider()` does not). SDK code registers one with `modelRuntime.registerVirtualModel(definition)`.

## `route(request, ctx)`

Runs before every request made with the virtual model and returns `{ model, thinkingLevel, state? }`. `model` must be a physical model whose provider has credentials (look it up with `ctx.modelRegistry`); a virtual model cannot route to another virtual model. Pi clamps the thinking level to the returned model. If `route()` throws, or returns a virtual model or a model without credentials, the request ends with an error response.

| `request` field | Meaning |
|---|---|
| `model`, `thinkingLevel` | The selected virtual model and level (the router's input) |
| `reason` | `user`, `continuation`, `retry`, or `direct` (see below) |
| `previous` | Physical model and level of the latest successful response in `messages` |
| `failed` | For `retry`: physical model, level, and assistant `message` (with `stopReason`, `errorMessage`) of the failed request |
| `state` | Router state last returned on this session branch |
| `messages` | The conversation for this request, including system messages |
| `signal` | Abort signal of the request |

| `reason` | Request |
|---|---|
| `user` | First request after a user-written message (including steer/follow-up) |
| `continuation` | Any other request in the agent loop (after tool results or extension messages) |
| `retry` | Automatic retry after a failed request, including after compaction for overflow |
| `direct` | Request outside the agent loop (compaction summary, `ctx.modelRegistry.streamSimple()`) |

Returning `previous` for `continuation` and `failed` for `retry` keeps prompt caches and thinking signatures valid. Switching models between turns is allowed but loses the prompt cache; a retry can switch models when `failed.message.errorMessage` reports an overloaded provider or context overflow.

## Routing state

`route()` can return `state` next to the model; Pi stores it on the session branch and passes it back as `request.state`. Use it for decisions the transcript does not record, such as a classifier result or routing phase.

- State must be JSON-serializable. Returning `undefined` or `request.state` keeps the current state; returning any other object stores it (return a new object only when the state changes).
- State follows the session tree, so forks and `/tree` navigation see their branch's state, and it survives compaction. `direct` requests have no state.

Routers can call other models through `ctx.modelRegistry`, for example `classify()` with a classifier from `findOfType("classifier", provider, id)`; this adds latency before the first token. See `examples/extensions/jev-router.ts` in the Pi repo for a complete planner/builder router that keeps its phase as routing state.
