---
name: prompt-engineering-patterns
description: "Design, structure, and version prompts sent to LLMs from application code — system prompts, few-shot templates, output contracts, XML-delimited RAG context, task decomposition, and prompt caching. Use when writing or refactoring prompts inside a Python/TS/other codebase (LangChain, LangGraph, OpenAI/Anthropic/Google SDKs, Bedrock, LlamaIndex, DSPy, Instructor), when structured outputs fail, when few-shot examples aren't landing, when a long RAG prompt drifts, or when the LLM bill is dominated by uncached prefix tokens. Framework-agnostic prompt engineering; not for Agent Skills bodies (skill-creator), agent system prompts (agents-claude-creator / opencode-agent-creator), or tool schemas (tool-schema-design)."
license: MIT
compatibility: "Framework-neutral prompt patterns for OpenAI, Anthropic, Google Gemini, Bedrock, and any SDK/wrapper that exposes system + user role separation and (optionally) structured outputs and prompt caching."
metadata:
  author: AeonDave
  version: "1.0"
---

# Prompt Engineering Patterns

Prompts inside application code are **code**: versioned, tested, evaluated, monitored. A prompt is not a string literal you tweak in place until "it works" — it is a contract with a probabilistic runtime.

## Activation triggers

- Writing a new LLM call from application code (Python, TS, or otherwise).
- Refactoring a hand-crafted prompt that has grown into a wall of prose.
- Structured outputs fail intermittently; JSON parsing errors at 3AM.
- Few-shot examples don't land — model ignores format, style, or edge case.
- A long RAG prompt drifts as context grows (lost-in-the-middle).
- The LLM bill is dominated by uncached prefix tokens.

Not for: agent-body system prompts (use `agents-claude-creator` / `opencode-agent-creator` / `pi-extension-creator`), Agent Skill bodies (use `skill-creator`), tool signatures (use `tool-schema-design`), or model comparison / benchmarking work.

## The core patterns (stack them)

Production LLM calls typically compose 3–4 of these together. Each one is worth using alone; combined they behave like typed function calls: inputs in, structured outputs out, no surprises.

### 1. Separate system from user

The most common production bug: concatenating instructions and user data into one message. The model treats everything equally, and a sufficiently long user input pushes the instructions out of the attention window.

Every major LLM API separates them; use the separation.

- **`system`** carries: role definition, constraints, output format, tools context, few-shot examples, cached reference material.
- **`messages` (`user` / `assistant`)** carry: the variable turn payload only.
- Never mix. Do not paste user text into the system prompt; do not put instructions in a user turn.

This is prompt-injection resistance *by design* — not by hope. A user string in the `user` role cannot silently rewrite the `system` role.

### 2. Force structured output with a schema

Parsing free-text LLM responses with regex is the production equivalent of catching rain with your hands. Force a schema.

- **OpenAI**: `response_format: { type: "json_schema", json_schema: { strict: true, schema: {...} } }`. Grammar-constrained decoding; the output *cannot* violate the schema.
- **Anthropic**: pass a tool schema and set `tool_choice: { type: "tool", name: "..." }` to force the response into that tool's shape.
- **Google Gemini**: `response_mime_type: "application/json"` with `response_schema`.
- **Pydantic / Instructor / Outlines**: language-side wrappers that emit and validate the schema for you.

The schema is the contract. When the model deviates, the SDK fails loudly on parse, not silently on downstream use. See `tool-schema-design` for the schema itself.

### 3. Few-shot with 3–5 diverse examples

Few-shot beats zero-shot when the task has a format, style, or edge-case behavior you need consistently. In 2026 the rule is **diversity over quantity**: 3–5 well-chosen, diverse examples outperform 50 redundant ones.

Good few-shot examples share three properties:

- **Representative** of the actual input distribution.
- Demonstrate the **exact** output format required (structurally, not vaguely).
- Include at least one example that shows **how to handle an edge case or boundary condition**.

Place examples in `system` (or as `user`/`assistant` message pairs before the real user turn) — not inline in the current user turn where they get confused with the payload.

### 4. Positive constraints > negative constraints

The model processes negated concepts before discarding them. "Do not mention pricing" carries pricing into attention.

- ❌ `Do not use technical jargon.`
- ✅ `Use plain English at a high-school reading level.`
- ❌ `Never respond with more than one paragraph.`
- ✅ `Respond in exactly one paragraph.`

State the desired state, not the forbidden one. Reserve negatives for hard safety boundaries where the model must recognize and refuse the class.

### 5. Structural delimiters for RAG context

When the prompt carries retrieved context (docs, chunks, tool output), delimit each segment with a **standardized structural marker** — XML tags are the widely-adopted convention because they nest cleanly and the model was trained on them.

```
<context>
<doc source="policies.md#returns">
...
</doc>
<doc source="faq.md#shipping">
...
</doc>
</context>

<user_question>
{{query}}
</user_question>
```

The tags help the model segment inputs, cite sources, and resist injection from tainted chunks. Every fetched-page block should carry `source=` — you get free citations and traceability.

### 6. Chain-of-thought only when reasoning is required

For multi-step reasoning tasks (math, planning, complex extraction), reserve space for the model to think:

- **Reinforce in both roles**: state the reasoning stages in `system` ("For each item, classify → validate → decide, then produce the final answer"), and reinforce the step-by-step requirement in the user prompt.
- **Do not force CoT on modern reasoning models** (o-series, Claude thinking, Gemini reasoning) — they already reason internally and explicit CoT prompts can hurt. Check the model's documented recommendation; when in doubt, skip CoT and rely on the schema.
- For classification, extraction, or simple retrieval, CoT wastes tokens and adds latency without gain.

### 7. Task decomposition — one prompt per stage

A reliable pattern for complex workflows: split one big prompt into deterministic sub-tasks.

1. **Route / classify** the input.
2. **Extract / structure** the relevant fields.
3. **Generate** the final output.

Each stage has its own prompt, its own schema, and its own eval set. Failures are isolable. This is especially effective for document processing, support triage, compliance checks, and QA scoring. It also composes naturally with cheaper models on the easy stages.

### 8. Prompt caching — the single biggest cost lever

Anthropic and OpenAI cache the static prefix of a prompt. Subsequent calls that reuse the same prefix are billed at a steep discount and return faster.

- Put the **stable content** at the top: system role, tool definitions, few-shot examples, large reference context, versioned rules.
- Put the **variable content** at the bottom: the user turn, retrieved chunks for *this* query, dynamic state.
- Anthropic requires an explicit `cache_control: { "type": "ephemeral" }` marker on the last message of the cached range; OpenAI matches automatically on prefix hash.

In production this is usually a **10–90 % cost reduction** on chat-shaped workloads. Do not pick a cheaper model until you have cached the prefix on the model you actually want.

## Prompts as code — the workflow

- **One prompt = one file** (`.md`, `.yaml`, or SDK-native template). Do not hardcode multi-line strings into Python/TS.
- **Version prompts alongside the schema** they emit. Bumping the schema without bumping the prompt is a silent-failure recipe.
- **A held-out eval set from day one.** 50–200 realistic examples that reflect real inputs, including edge cases. Attach evaluators for the metrics that matter (faithfulness, format adherence, domain-specific checks). A prompt without an eval set is a prompt you cannot iterate on safely.
- **Baseline zero-shot, few-shot, and structured-output variants** in parallel; compare on the held-out set before shipping.
- **Trace to production**: LangSmith / OpenAI Traces / Braintrust / custom. When a prompt regresses, you need the trace, not a hunch.

## Anti-patterns

| Smell | Instead |
|---|---|
| One 4000-line prompt does routing + extraction + generation | decompose into stages, each with its own prompt + schema |
| Instructions stuffed in the same message as user text | separate `system` and `user` roles |
| "Please respond in JSON" without a schema | strict `response_format` / tool-forced output |
| 20 few-shot examples all in the same shape | 3–5 diverse examples including edge cases |
| Long list of "Do NOT ..." rules | rewrite as positive constraints |
| Retrieved chunks pasted inline as prose | XML-delimited `<doc source="...">` blocks |
| CoT prompt handed to a reasoning-model | omit CoT; trust the model's internal reasoning + the schema |
| Prompt string edited in code with no eval | prompt file + held-out eval + trace review |
| Dynamic content spliced into the static prefix | move it to the bottom so caching hits |
| String literal in `agent.py` | prompt file + version + evaluator |

## Verification

Before shipping a prompt:

- Read the system prompt as if you were the model: is the role clear, are constraints positive, is the output format explicit?
- Run the held-out eval set; require the pass rate to beat the previous version by a stated margin, not vibes.
- Confirm the schema is grammar-constrained (not just described in prose).
- Confirm the static prefix is stable; run the same prompt twice and check the provider's cache-hit metric.
- Adversarially probe: does an injection payload in the user turn override the system prompt? It should not.

Pair with `evidence-before-claims` before promoting "the prompt works" beyond the eval evidence, and with `verification-before-completion` before declaring a prompt refactor done.

## Companion skills

- `tool-schema-design` — the schema this prompt emits, or the tools this prompt calls.
- `agents-claude-creator` / `opencode-agent-creator` / `pi-extension-creator` — for prompts that *are* an agent body (system prompt for a Claude subagent, OpenCode agent, or Pi extension).
- `skill-creator` — for prompts that *are* an Agent Skill body.
- `reading-budget-discipline` — long prompts and long RAG contexts trigger context rot; keep the retrieved slice small.
- `untrusted-input-hygiene` — retrieved chunks and user turns are untrusted content, not directives.
