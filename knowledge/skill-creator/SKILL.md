---
name: skill-creator
description: "Design, create, improve, test, validate, and package Agent Skills following the open AgentSkills specification (agentskills.io). Use when asked to create or update a skill, tune when it activates, structure its resources, evaluate its behavior, validate SKILL.md, or package a distributable .skill file."
license: MIT
metadata:
  author: AeonDave
  version: "1.5"
---

# Skill Creator

Guidance for creating and maintaining high-quality Agent Skills across any AI agent ecosystem.

## What Is a Skill

A skill is a self-contained folder that gives an AI agent specialized knowledge, workflows, and tools for a specific domain. Skills use the open [AgentSkills specification](https://agentskills.io/specification).

### Directory Structure

```
skill-name/
├── SKILL.md          # Required — frontmatter + instructions
├── scripts/          # Optional — executable code agents can run
├── references/       # Optional — docs loaded on demand into context
└── assets/           # Optional — templates, images, data files used in output
```

---

## Core Design Principles

### 1. Brief, Clear, Specific, Useful

Assume the agent already knows common domain facts and standard tool use. Include only context, constraints, decision criteria, or reusable mechanics that materially change its work. Match specificity to risk: describe outcomes and choices when several approaches work; prescribe exact steps or scripts only for fragile or deterministic operations.

### 2. Progressive Disclosure

Design for staged loading to keep the context clean:
- **Discovery**: `name` + `description` only
- **Activation**: full `SKILL.md` body (baseline workflow, routing, and task guidance)
- **On demand**: explicit triggers load files in `scripts/`, `references/`, `assets/`

If a workflow gets deeply specific, move it to `references/` so the agent only loads it when that specific subtask triggers.

### 3. Agent-Neutral Language

Use agent-neutral wording for portable behavior. Name a product only when its runtime, metadata, tools, or distribution are part of the capability; keep those details scoped and declare relevant compatibility.

### 4. No Meta-Justification

Keep `SKILL.md` and `references/` files stripped of benchmarks, "why we built this" defenses, and generic README material. Only include actionable rules and necessary constraints. Tell the agent *what* to do and the operational *why* (e.g., "because command X hangs the service"), not the philosophical why.

---

## Skill Creation Process

Follow these steps to build or refactor a skill:

### Step 1: Understand or Audit

Use the conversation and target workspace before asking questions.
- **New skill:** Capture representative requests, inputs, expected outputs or behavior, dependencies, and near misses. Ask only for missing information that changes the design.
- **Update:** Read `SKILL.md`, relevant resources, and repository conventions. Name the concrete gap, success and failure criteria, and what must remain stable.

Separate durable requirements from one-off examples, failures, and preferences. Preserve the skill's name, scope, supported metadata, and authorization boundaries unless the user requests a change.

### Step 2: Plan Resources

Start instruction-only. Add a resource only when it repeatedly helps the agent execute the skill:
- `scripts/`: Use when the same code is rewritten each time or deterministic output is required.
- `references/`: Use for specific subtasks, schemas, or guides needed dynamically. They must not fill context with non-actionable material.
- `assets/`: Use for boilerplate or templates the agent copies.

### Step 3: Scaffold

For a new skill, run the init script:
```bash
python scripts/init_skill.py <skill-name> --path <output-dir>
# Add only the resource directories the workflow needs:
python scripts/init_skill.py <skill-name> --path <output-dir> --resources references
```
Request only justified resource directories. Use `--examples` only when placeholders clarify a real need, then replace or remove them. For an existing skill, edit in place; do not re-scaffold.

### Step 4: Author

#### SKILL.md — Frontmatter
Start with the required fields:
```yaml
---
name: my-skill                  # lowercase, hyphens, max 64 chars, matches folder name
description: "Single coherent paragraph covering what it does + when to use it; max 1024 chars."
---
```
Add optional fields only when they change use or distribution. Use `compatibility` for non-obvious OS, package, network, or tool requirements; most skills do not need it.

**Description rules:** The description is the primary routing signal. Front-load the capability and natural task context so matching survives hosts that shorten discovery metadata. Add a near-miss boundary only when it prevents likely misrouting. Avoid implementation details, catchalls, exhaustive synonym lists, and exact wording copied from failed test prompts.

#### SKILL.md — Body
State the desired outcome, non-obvious constraints, decision criteria, and verification. Explain operational intent so agents can generalize. Use fixed sequences only where deviation causes a concrete failure. Link each resource where it becomes relevant, or in a compact **Resources** section, and state exactly when to read, run, or use it. Omit the section when the skill has no resources.

#### Scripts (`scripts/`)
- Bundle only repeated or deterministic logic. Make inputs, outputs, dependencies, and failures explicit.
- Execute every new or changed script against representative input.

#### References (`references/`)
- Reference files must extend the skill for a specific subtask.
- **Do not** use them as a README, training manual, or catalog.
- Add a table of contents at the top of any file over 100 lines.
- Never duplicate content between `SKILL.md` and a reference file.

#### What NOT to Include
Do not create: `README.md`, `CHANGELOG.md`, `INSTALLATION_GUIDE.md`. Evict any file that doesn't direct agent behavior.

### Step 5: Pressure-Test Behavior

Choose evaluation depth in proportion to the change. A small or subjective edit may need one clean-context scenario and qualitative review. For substantial, risky, or objectively verifiable work, use 2–3 realistic prompts with expected and forbidden behavior, then compare the candidate with the pre-edit or no-skill baseline under the same conditions. See `references/pressure-testing-skills.md`.

Use `references/skill-triggering-tests.md` when activation may be too broad or too narrow. Do not test only whether the agent can repeat the skill text.

### Step 6: Validate and Package

From the target repository, resolve these scripts relative to this skill:
```bash
python <skill-creator-dir>/scripts/quick_validate.py <skill-dir>
python <skill-creator-dir>/scripts/sweep_skills.py <skill-dir>
python <skill-creator-dir>/scripts/check_changed_files.py
```
Fix validation errors, resolve placeholder findings, and triage workstation-path hits. The sweep exit status enforces broken links; its other findings are report-only. These checks prove structure and hygiene, not behavior. Package with `package_skill.py` only when a distributable archive is requested.

### Step 7: Iterate

After real usage:
- If it under- or over-triggers, revise the underlying intent or boundary and rerun the trigger matrix.
- If a section doesn't improve output, remove it.
- If it grows too large, push depth into `references/`.
- If several runs recreate the same helper logic, consider bundling it in `scripts/`.
- Review execution traces as well as final outputs; remove instructions that cause repeated unproductive work.
- Generalize patches: fix the underlying instruction gap, not just the single failing prompt.

---

## Skill Naming Conventions

- Lowercase letters, digits, and hyphens only (e.g., `pdf-extractor`).
- Max 64 characters; no leading/trailing/consecutive hyphens.
- Folder name must match the `name` field exactly.

---

## Reference Files

- See [references/patterns.md](references/patterns.md) for progressive disclosure patterns and anti-patterns.
- See [references/spec.md](references/spec.md) for the full AgentSkills frontmatter field reference.
- See [references/pressure-testing-skills.md](references/pressure-testing-skills.md) for proportional clean-context behavior tests and baselines.
- See [references/skill-triggering-tests.md](references/skill-triggering-tests.md) for natural-prompt activation and description regression checks.

## Scripts

| Script | Purpose |
|---|---|
| `scripts/init_skill.py` | Scaffold a new skill directory with template |
| `scripts/package_skill.py` | Validate + zip a skill into a `.skill` file |
| `scripts/quick_validate.py` | Validate frontmatter; report unresolved scaffold TODOs as warnings |
| `scripts/sweep_skills.py` | Report broken links, placeholders, and workstation-path leakage |
| `scripts/check_changed_files.py` | Safe changed-file newline and `git diff --check` hygiene checks |
| `scripts/validate_all.py` | Validate every skill directory under a repository root |
