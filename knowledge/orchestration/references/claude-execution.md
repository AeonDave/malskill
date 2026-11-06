# Claude Code execution

Load when coordinating work in Claude Code. Inspect the installed version, exposed tools, selected agent definition, and effective model settings. Use the current tool schema; a feature described online may be unavailable or disabled in this session.

## Select the mechanism

| Mechanism | Use when | Operating rule |
|---|---|---|
| Subagent | A focused worker can return to the lead | Foreground when its answer gates the next step; background when independent work can continue |
| Agent Team | Workers need sustained discussion, challenges, or shared task ownership | Check that teams are enabled; give teammates distinct ownership, coordinate through messages/tasks, and shut them down when finished |
| Dynamic Workflow | Scripted fan-out, branching, or repeatable orchestration would remove substantial lead bookkeeping | Check workflow availability, pilot a narrow slice, and retain explicit budgets, result identities, and failure handling |

Use the [subagent guide](https://code.claude.com/docs/en/sub-agents), [team guide](https://code.claude.com/docs/en/agent-teams), or [workflow guide](https://code.claude.com/docs/en/workflows) for the selected mechanism. Do not create a team for a simple batch or install a workflow framework to handle one small job.

## Subagents: make the dispatch effective

- Select an agent by its actual description, prompt, tools, and output contract. A built-in reader fits discovery; a general or custom worker fits tasks requiring edits or execution. Avoid loading unrelated role instructions into a bounded job.
- Request the chosen model and effort through supported invocation fields. Naming a model in prose is not proof that the host selected it. Do not assume Explore uses a cheaper model; check effective inheritance and overrides.
- Map the parent's capability choices to the models available in this account. Keep simple extraction inexpensive, ordinary implementation on a capable general model, and difficult diagnosis or integration on a stronger reasoning model. Start from the model's default effort when unsure; raise it for unresolved reasoning complexity, not routine tool latency.
- Normal named subagents do not receive the parent conversation; explicit conversation forks have different inheritance. Built-in readers can omit project instructions. Carry essential task facts and constraints in the brief; use a fork only when its inherited context is useful. Forking does not create independent judgment.
- Background work must have enough context and permissions to proceed. Inspect its result or blocker on completion; do not assume it can obtain interactive input while the lead is occupied. Use the exposed result/wait mechanism or completion notifications; if none is available, choose foreground execution before dispatch. Resume a supported worker for targeted follow-up rather than replaying its completed research.

For model and effort resolution, environment overrides, and supported fields, consult [model configuration](https://code.claude.com/docs/en/model-config). When creating or changing agent definitions, load [claude-agents-creator](../../../harness-dev/claude-agents-creator/SKILL.md); keep configuration syntax there.

## Workflows: keep orchestration in the script

- Before authoring or changing a saved workflow script, load the host's bundled `workflow-authoring` skill and current API guidance. Do not invent a `Workflow` tool or transfer its API to another harness. Reload saved definitions as documented before testing the edit in the current session.
- Express actual dependencies. A `parallel()` join waits for every branch; put downstream work inside its own chain when it needs only that branch's result. Keep discovery, per-item processing, and cross-item aggregation separate where their inputs differ.
- Keep bulky intermediate results in script variables or artifacts. Give stages compact inputs and return only decision-relevant results to the lead. Reuse stable prompts/configurations when practical for caching; do not strip necessary context to manufacture cache hits.
- Handle empty input, failed or stopped agents, missing results, and partial completion explicitly. Validate a stage's result before passing it downstream. A null result is missing work, not proof that an item has no findings.
- Bound dynamic loops and total dispatch/retries explicitly. Concurrency limits, token targets, and cost warnings are different controls; inspect which are enforced by the current runtime. Measure total lead and worker usage before claiming savings.
- Monitor through the host's run controls. Automatic restarts may lose transcript context while filesystem changes persist; inspect state before repeating side effects. Resume only outputs still valid for the current inputs. Pause/stop requests do not prove that spawned processes have exited.

## Teams: coordinate without duplicate work

Use the shared task list for ownership and prerequisites, and direct messages for actionable updates. Check stalled task state against actual worker status before reassigning it. Teammates may have different effective model or effort settings; verify selection instead of assuming every override propagated.

Confirm shutdown before cleanup. Check current resume support: a resumed lead conversation does not necessarily restore its teammates. Preserve completed artifacts and reconstruct only outstanding work.
