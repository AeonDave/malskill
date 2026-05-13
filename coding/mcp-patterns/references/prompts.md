# Prompts

Load this file when you need reusable, user-invoked workflow templates.

## Use a prompt when

- the user should be able to choose a named workflow
- the main value is task framing or message construction
- you want reusable templates with arguments rather than direct side effects

Prompts are not a substitute for tools. They frame work; they do not execute it.

## Verified Python pattern

```python
@mcp.prompt(title="Code Review")
def review_code(code: str) -> str:
    """Generate a code review prompt."""
    return f"Review this code:\n{code}"
```

Official SDK examples also show prompts returning structured message lists, not only strings.

## Prompt design rules

- keep the template focused on one workflow
- make arguments explicit and small in number
- include only the context required for the next step
- name prompts by outcome, not by internal implementation detail

## Good prompt use cases

- review this snippet in language X
- draft a migration plan from input Y
- turn resource/tool output into a structured next-step instruction set

## Versioning and composition

- version prompt names or titles when semantics change materially
- compose with resources when shared context belongs outside the prompt body
- avoid giant “do everything” prompt templates

## Prompt vs server instructions

- **Prompt**: user-invoked template for a concrete task
- **Server instructions**: global operational guidance about how to use the server

Use both only when they solve different problems.

## Common mistakes

- encoding tool ordering or global operational caveats inside one prompt only
- creating prompts that duplicate a normal user message with no added value
- turning prompts into long manuals
- expecting prompts to replace precise tool/resource design
