# Server Instructions

Load this file when the server needs short global guidance that tool descriptions alone do not express.

## What server instructions are for

Server instructions explain **cross-feature behavior**:

- preferred tool ordering
- caching or rate-limit constraints
- required multi-step safety workflow
- capability-dependent fallbacks

They are not a place to restate every tool description.

## Good uses

- “Use `validate_schema` before `migrate_schema`.”
- “For bulk export, write results with the filesystem server after generating them here.”
- “If elicitation is unsupported, fall back to defaults instead of asking the user through the server.”

## Writing rules

- keep them short
- keep them factual
- keep them model-agnostic
- emphasize relationships and constraints, not marketing

## Anti-patterns

- repeating tool descriptions verbatim
- writing a giant manual in instructions
- trying to change the model’s personality
- using instructions to hide weak tool design

## Design reminder

If the model only succeeds after a long instruction block explains basic tool meaning, the tool abstraction or description is probably the real problem.

## Practical recommendation

Add server instructions only when the server has real workflow semantics that span multiple tools/resources/prompts. Keep them as the final thin layer on top of good design, not as the thing holding the server together with duct tape and hope.
