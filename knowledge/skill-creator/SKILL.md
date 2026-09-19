---
name: skill-creator
description: "Create, revise, evaluate, or package Agent Skills. Use for SKILL.md instructions, activation descriptions, and bundled resources."
license: MIT
metadata:
  author: AeonDave
  version: "1.6"
---

# Skill Creator

Produce a skill that changes how an agent handles a recurring task. Keep only instructions, resources, and constraints that contribute to that outcome.

## Establish the gap

Use the request, existing skill, and applicable repository instructions to identify the missing behavior and what completion requires. Inspect only resources relevant to the change. Ask for missing information only when it changes the scope, contract, or authorization.

- Reuse an existing skill when its scope already fits; fix its routing if discovery is the problem.
- Create a skill only for a distinct recurring capability. Keep one-off inputs in the task prompt and repository-wide conventions in repository instructions.
- Preserve supported behavior, metadata, user decisions, and authorization boundaries unless their change is part of the request.
- Separate the observed failure from a proposed remedy. Try deleting or narrowing conflicting instructions before adding another rule.

## Author the smallest useful instruction set

**Brief, clear, specific, useful.** Assume competence in ordinary domain knowledge and tool use. Retain non-obvious constraints, decision criteria, output contracts, and verification that prevent a concrete failure. Ground technical claims in the current implementation, a real run, or a primary source; qualify uncertain conditions.

Define the outcome and when work is complete. Prescribe a sequence only when order matters; otherwise let the agent choose the method. Record genuine approval boundaries without inserting review stops into already-authorized work. Do not turn a workaround for one model into a universal requirement.

### Frontmatter

```yaml
---
name: my-skill
description: "Capability and the specific task that should activate it."
---
```

- `name`: matches the folder, lowercase letters/digits/hyphens, at most 64 characters; no leading, trailing, or consecutive hyphens.
- `description`: the shortest clear routing signal, at most 1024 characters. Lead with the distinctive task. Include a near-miss boundary only when needed; omit workflow summaries, broad topic associations, synonym lists, and activation pressure.
- Add optional metadata only when useful. Declare non-obvious runtime requirements in `compatibility`; keep product-specific behavior scoped to that runtime.

Load [references/spec.md](references/spec.md) when choosing optional fields or checking specification details. The field limits are ceilings, not writing targets.

### Body and resources

Keep shared decisions and constraints in `SKILL.md`. For independently used workflows, make it a compact router with explicit conditions for loading each resource. A short, single-workflow skill can remain one file.

| Resource | Add when |
|---|---|
| `scripts/` | Repeated mechanics or fragile operations need deterministic execution. Specify inputs, outputs, dependencies, and failures. |
| `references/` | A subtask needs depth that other tasks can skip. Link the exact file with a "load when" condition. |
| `assets/` | The agent needs a reusable template or static file in the output. |

Keep each fact in one canonical location. Delete irrelevant material instead of moving it into a reference. Omit generic tutorials, design defenses, historical notes, and extra README/CHANGELOG/install guides. Add examples only to resolve ambiguity; add navigation when a long reference cannot be scanned easily.

Load [references/patterns.md](references/patterns.md) when deciding how to split workflows or repair resource routing.

## Create or revise

For an existing skill, edit in place; do not re-scaffold. For a new skill, resolve this script relative to the skill-creator directory:

```bash
python <skill-creator-dir>/scripts/init_skill.py <skill-name> --path <output-dir>
# Request resource directories only when needed:
python <skill-creator-dir>/scripts/init_skill.py <skill-name> --path <output-dir> --resources references
```

Use `--examples` only when sample files help; replace or remove them before finishing. Execute new or changed helpers on representative inputs, including relevant failure cases.

## Evaluate the change

Use the smallest check that can detect the claimed improvement:

- Editorial change: review the diff and validate structure.
- Instruction or workflow change: try a realistic task in a clean context and inspect the result and actions taken.
- Substantial behavior change: compare the candidate with the pre-edit or no-skill baseline using the same inputs and environment. Set expected outputs and prohibited outcomes before grading.
- Routing change: exercise natural requests and plausible near misses with the available skill catalog.

Load [references/pressure-testing-skills.md](references/pressure-testing-skills.md) when designing behavior comparisons or diagnosing failures. Load [references/skill-triggering-tests.md](references/skill-triggering-tests.md) when tuning activation.

Test the models and hosts used by the intended audience when making compatibility claims; name untested targets. Check for unnecessary reads, tool calls, tests, and approval stops as well as incorrect outputs. A shorter file is not evidence of better behavior.

## Validate and finish

From the target repository, run these scripts for each changed skill directory:

```bash
python <skill-creator-dir>/scripts/quick_validate.py <skill-dir>
python <skill-creator-dir>/scripts/sweep_skills.py <skill-dir>
python <skill-creator-dir>/scripts/check_changed_files.py
```

Resolve frontmatter errors, broken links, scaffold markers, and workstation-path leakage. The sweep enforces broken links through its exit status; inspect its report-only findings too. These checks establish structure and hygiene, not behavioral quality.

Finish the requested edits, affected checks, and corrections before handing back the result. Report what was tested and what remains unverified. Package with `python <skill-creator-dir>/scripts/package_skill.py <skill-dir>` only when an archive is requested; use `python <skill-creator-dir>/scripts/validate_all.py <repo-root>` only for repository-wide validation.

After a real failure or model/runtime change, reassess the affected instructions and rerun relevant scenarios. Keep a rule only if it still improves the outcome.
