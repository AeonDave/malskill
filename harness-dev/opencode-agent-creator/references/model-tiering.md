# Model routing

The [v1.18.35 Task implementation](https://github.com/anomalyco/opencode/blob/v1.18.35/packages/opencode/src/tool/task.ts) has no `model` argument. It uses the target agent's configured model, or the invoking assistant's provider/model when that agent has no pin. An unpinned worker also inherits the caller's variant; a pinned worker uses its own configured variant.

## Choose a policy

| Need | Configuration |
|---|---|
| Follow the user's selected model | Omit the worker's `model`. |
| Stable provider/model choice per role | Set a verified `provider/model-id` on that worker. |
| Cheap routine work and stronger difficult work | Create distinct agent roles/pins only when the distinction changes real routing. |
| Provider-specific reasoning level | Use a supported `variant` or provider option; confirm availability and behavior for that model. |

Run `opencode models` against the target installation before writing a pin. Do not copy example identifiers, free-tier availability, pricing, or reasoning controls from an old catalog. The bundled agents omit pins so they remain adaptable; assign deliberate pins when deploying a roster.

Inheritance is not automatic fallback on quota errors. A failed pinned model remains a failed dispatch; report the error and change the model policy explicitly. New calls to an unpinned worker use the caller's current model, including when resuming a task. A model change does not erase the resumed child's existing history.

Before sending engagement data to a different provider, check that provider's current retention/training terms and the user's constraints. Redact before dispatch when required; output redaction cannot remove data already sent in the prompt. Keep unredactable material with an approved provider or local workflow.

Load [orchestrator-pattern.md](orchestrator-pattern.md) for task identity/resumption and [agent-config-reference.md](agent-config-reference.md) for model/variant fields.
