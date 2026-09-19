# Resource Routing Patterns

Use when splitting a skill into resources or repairing unnecessary loading.

## Choose the boundary

| Task shape | Structure |
|---|---|
| One compact workflow | Keep it in `SKILL.md`; extra files need a concrete use. |
| Shared baseline with an occasional specialized operation | Keep the baseline in the body; load the operation's reference when the task needs it. |
| Distinct workflows, formats, or platforms | Keep selection criteria and shared constraints in the body; route directly to the selected resource. |
| Repeated or fragile mechanics | Use a script with an explicit invocation condition and output contract. |

Split by what a task needs, not by a line threshold. If two references are always needed together, consider merging them. If a section adds no actionable information, delete it instead of relocating it.

## Write actionable routes

Each route needs a task condition, an exact resource, and the action to take. For example, a skill whose resources exist could use:

```markdown
## Export format

Use the requested format or the existing project configuration.
- CSV export: read [references/csv.md](references/csv.md) for quoting rules.
- XLSX export: read [references/xlsx.md](references/xlsx.md) for workbook layout.
Ask for the format only if it cannot be inferred and changes the output contract.
```

Keep independent branches independently readable. A task should not have to load every branch to discover which one applies. Keep essential shared constraints in the parent, without copying them into each branch.

## Repair common failures

| Observed problem | Targeted correction |
|---|---|
| The agent opens all resources before acting | Replace unconditional prerequisites with task-specific routes. |
| A reference is never discovered | Add a direct parent link at the decision that needs it. |
| The same fact differs across files | Select one canonical location and link to it. |
| The agent must traverse unrelated documents | Link directly to the resource needed for the task. |
| A long reference is hard to search | Add headings and a compact contents list for its actual subtasks. |
| A reference is mostly background | Retain only facts that change a decision or action. |
| A fixed recipe blocks a suitable existing tool | State the required contract; fix the implementation only when compatibility or correctness requires it. |

Verify referenced files and helpers exist. Review an actual task trace when claiming the new routing reduces irrelevant reads.
