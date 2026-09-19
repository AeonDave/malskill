# Reviewing an AGENTS.md Rewrite

Load when a substantial rewrite needs evidence that shorter instructions preserve useful behavior. Use [OpenAI's guidance on revisiting agent instructions](https://developers.openai.com/blog/rethinking-skills-and-prompts-for-gpt-6-astra) to reassess assumptions when the supported models change; retain constraints justified by the repository and its actual users.

## Audit the diff

For each removed or changed instruction, identify its effect:

| Finding | Revision |
|---|---|
| Required document stack for every edit | Give each relevant document a task condition. |
| Repeated generic advice | Remove it unless a demonstrated failure needs a precise rule. |
| Fixed investigation itinerary or retry count | State the required evidence and concrete escalation condition. |
| Blanket approval request | Name the action and real authorization boundary; preserve authorized local work. |
| Checks detached from the changed behavior | Tie them to their trigger while retaining mandatory project gates. |
| Stop after a first draft | State the required deliverable, verification, and actual stopping boundary. |
| Copied example presented as policy | Replace it with a verified repository rule or remove it. |

Check that shortening did not delete a build prerequisite, non-obvious invariant, active decision, accepted diagnostic, or required approval. Keep one canonical home for each retained fact. Do not optimize toward a line count or compensate by hiding the same redundant text in references.

## Compare representative behavior

Use the same task, workspace state, tools, and supported model/host for the existing and candidate instructions. Choose cases that exercise the edited rules, for example:

- A small documentation fix: does it avoid unrelated discovery and tests while satisfying applicable checks?
- A code change with generated output: does it preserve the regeneration step and finish the relevant validation?
- A task crossing a subtree or release boundary: are the correct instructions loaded and does it stop only where authorization actually ends?

State expected and forbidden behavior before the run. Inspect tool traces as well as the final artifact: unnecessary reads, repeated checks, avoidable approval questions, missed constraints, and incomplete authorized work. Compare result quality first; fewer lines or tool calls alone do not prove improvement.

Use clean sessions when available. If testing covers only one host/model, or review is static, report that limit. Retest the affected case after a substantive correction; do not create a broad evaluation campaign for a wording fix.
