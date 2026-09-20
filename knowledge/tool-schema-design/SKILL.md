---
name: tool-schema-design
description: "Design or revise model-callable tools. Use for tool selection ambiguity, argument and result schemas, validation, error contracts, and execution semantics."
license: MIT
compatibility: "Agent-neutral. Applies to OpenAI function calling, Anthropic tool_use, Google Gemini function calling, Bedrock Converse, and MCP tools/resources."
metadata:
  author: AeonDave
  version: "1.0"
---

# Tool Schema Design

Tool-calling reliability lives in three places: the **description** the model reads to pick the tool, the **JSON Schema** it fills to call it, and the **error response** it uses to recover. Get those three right and a well-tuned model picks the right function, supplies valid arguments, and recovers gracefully.

## The description writes the router

Descriptions — of tools and of parameters — are the primary lever for selection accuracy. The model disambiguates between similar tools by reading descriptions, not names.

- **Tool description**: cover *what it does*, *when to use it*, and *when NOT to use it* (name the sibling tool the model should pick instead).
- **Parameter description**: include expected format, valid range, and a concrete example. `"The ISO 8601 start date, e.g. '2026-03-15'"` beats `"The start date"`.
- Write in a neutral, third-person voice. No marketing.

Example:

```json
{
  "name": "search_knowledge_base",
  "description": "Search the internal knowledge base for factual answers. Use for product documentation, policies, and FAQs. Do NOT use for real-time data like prices, stock levels, or order status — use get_product or get_order_status instead.",
  "parameters": {
    "type": "object",
    "properties": {
      "query": {
        "type": "string",
        "description": "A natural-language search query, 3–15 words. Example: 'return policy for opened electronics'."
      }
    },
    "required": ["query"]
  }
}
```

## Schema design rules

Every JSON Schema constraint is information the model uses to generate a valid call. Add signal, not noise.

- **Types carry semantics**: `integer` on `quantity` tells the model fractional quantities are invalid; `number` allows them. Use the narrower type.
- **`enum` narrows the accepted space**: prefer `"enum": ["day", "week", "month"]` over `"description": "one of day, week, or month"`. Still validate arguments because model output can violate a schema when strict enforcement is unavailable.
- **`minimum` / `maximum` / `pattern` / `format`** narrow generation. `page_number` with `minimum: 1` implicitly signals one-indexed pages. `format: "date"`, `format: "uri"`, `format: "email"` are standardized.
- **Consistent naming across the toolkit**: pick one of `user_id` / `userId` / `uid` and use it everywhere. Mixing shapes lowers extraction accuracy.
- **Choose required fields for the target runtime.** Generic JSON Schema permits optional properties, but OpenAI strict function calling requires every property in `required` and `additionalProperties: false`; represent an optional value with a nullable type where that API requires it. Do not assume a JSON Schema `default` is injected by the model or runtime; apply defaults in application code.
- **One responsibility per tool**. `create_or_update_user` is two contracts colliding; split them.
- **Nested objects sparingly**. Deep nesting increases call errors; flatten when the operational meaning survives.

## Structured outputs, not free text

When the response has to be machine-consumable, do not parse free text. Use provider strict-schema modes:

- **OpenAI**: use the current Structured Outputs contract for the selected API, with strict JSON Schema where supported. Strict mode constrains schema-compatible output; handle refusals, truncation, and API errors.
- **Anthropic**: use the current tool schema and `tool_choice` controls when you need a specific tool; verify provider-specific strict structured-output support separately.
- **Google Gemini**: use the current `response_mime_type` / `response_schema` contract where supported.

Rules of thumb:

- Prefer a strict schema over "please respond in JSON" in the prompt.
- Include the schema in the system prompt only if the model does not support strict mode; do not duplicate it if it does.
- Version the schema alongside the prompt.

## `tool_choice` — the selection dial

Providers expose it under slightly different names. The four states are the same:

| State | When |
|---|---|
| `auto` (default) | Model decides whether to call any tool. |
| `required` / `any` | Some providers require a tool call this turn. Verify the provider's exact setting and semantics. |
| `<specific tool>` | Some providers can require **that** tool. This is provider-specific, not equivalent to schema strictness. |
| `none` | Model may not call tools. Use for summarization / final response steps. |

Pin `tool_choice` at the agent step where behavior matters; leave `auto` where the model should route.

## Error responses that steer recovery

A model-visible tool error can become another observation. Return content the model can act on when the host supports that contract.

- **Return a clear structured error when the host supports model-visible tool errors.** Do not assume every framework treats thrown exceptions as terminal or returned strings as recoverable observations; follow the host contract.
- Name the failure class: `not_found`, `invalid_argument`, `rate_limited`, `permission_denied`, `upstream_error`.
- Include the offending argument value and the correction hint: `"invalid_argument: 'category'='electronic' is not in enum. Valid: ['electronics','clothing','food']."`
- For retryable failures (rate limit, transient upstream), say so and give a hint: `"rate_limited: retry after 5s"`. Combine with framework-level retry policies (see `loop-control-and-pivots`) — do not loop internally.
- Never leak stack traces, secrets, or PII into the error string; the model puts it in the response.

## Parallel and streaming considerations

- **Parallel tool calls** and their defaults vary by provider, model, and request setting. Design tools to be idempotent where possible; add an idempotency key parameter when a repeat call would double-charge or double-write.
- **Long-running tools** should use the host's supported asynchronous result, callback, task, or status contract. A small handle such as `operation_id` can help, but do not invent a polling companion when the host provides another completion mechanism. For MCP, use Tasks when negotiated (see `mcp-creator`).
- **Streaming outputs** from a tool are rarely useful to a model that reasons on complete observations; buffer and return the final result unless the tool is streaming user-visible content the agent forwards verbatim.

## Anti-patterns

- **`description: "A tool for users"`** — useless; the model routes on descriptions, not names.
- **Bare `"type": "string"`** on an id, date, or enum — you gave the model no scaffolding, expect hallucinated values.
- **Overlapping tools with the same trigger words** — model routes randomly. Fix by explicit *when-NOT-to-use* on each description, or merge the tools.
- **`get_data(filters: object)` with no schema for `filters`** — the model invents keys. Enumerate the fields.
- **Everything `required` without checking the target contract** — generic optionality and provider strict mode differ. Make fields nullable or handle defaults in application code where the provider requires them.
- **Silent success on empty result** — `"[]"` reads as "worked, nothing found." If the argument was probably wrong, say so.
- **Boolean flags that mean two different things** — `force=true` conflates "override safety" and "skip cache". Split.

## Verification

Before shipping a tool schema:

- Read the description as if you were the model: does it say *when to use* and *when NOT to use*? Does each parameter description carry format, range, and an example?
- Sample a representative set of realistic prompts and confirm the model picks the right tool and fills valid arguments (record the traces).
- Force a malformed call and confirm the returned error is diagnostic — the model should self-correct on the next turn.
- If two tools have overlapping triggers, add a differentiating clause and re-test.

Pair with `evidence-before-claims` before declaring "the tool works" — a single successful sample is not evidence; a small held-out set is.

## Companion skills

- `mcp-creator` — for MCP-specific tool/resource contracts (execution classes, result types, transport).
- `agents-claude-creator` / `opencode-agent-creator` / `pi-extension-creator` — when the tools live inside an agent's `tools:` array.
- `opencode-plugin-creator` — for the `tool()` API with zod schemas and `ToolContext`.
- `evidence-before-claims` — before reporting a tool schema as "correct".
- `loop-control-and-pivots` — for the retry / non-retryable classification the error string signals to.
