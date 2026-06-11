---
name: skill-creator
description: "Design, create, update, and package Agent Skills following the open AgentSkills specification (agentskills.io). Use when asked to create a new skill, improve an existing skill, scaffold a skill directory, validate a SKILL.md, or package a skill into a distributable .skill file."
license: MIT
metadata:
  author: AeonDave
  version: "1.4"
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

The context window is shared. Every token in a skill competes with the user's request. **Challenge every sentence:** does the agent actually need this to act? Write imperative instructions, not essays. Every skill must directly help the agent act on the task.

### 2. Progressive Disclosure

Design for staged loading to keep the context clean:
- **Discovery**: `name` + `description` only
- **Activation**: full `SKILL.md` body (baseline workflow, routing, and task guidance)
- **On demand**: explicit triggers load files in `scripts/`, `references/`, `assets/`

If a workflow gets deeply specific, move it to `references/` so the agent only loads it when that specific subtask triggers.

### 3. Agent-Neutral Language

Skills are executed by different AI agents (Claude, Gemini, Codex, etc.). Never hardcode a product name inside the skill body; say "the agent" instead.

### 4. No Meta-Justification

Keep `SKILL.md` and `references/` files stripped of benchmarks, "why we built this" defenses, and generic README material. Only include actionable rules and necessary constraints. Tell the agent *what* to do and the operational *why* (e.g., "because command X hangs the service"), not the philosophical why.

---

## Skill Creation Process

Follow these steps to build or refactor a skill:

### Step 1: Understand or Audit

Gather concrete usage examples first.
- **New skill:** Ask what triggers it, what tasks it handles, and what success looks like.
- **Update:** Read `SKILL.md` first. Identify what works, what is stale, and what must remain stable.

### Step 2: Plan Resources

Ask: *what does an agent need to execute this repeatedly?*
- `scripts/`: Use when the same code is rewritten each time or deterministic output is required.
- `references/`: Use for specific subtasks, schemas, or guides needed dynamically. They must not fill context with non-actionable material.
- `assets/`: Use for boilerplate or templates the agent copies.

### Step 3: Scaffold

For a new skill, run the init script:
```bash
python scripts/init_skill.py <skill-name> --path <output-dir> --resources scripts,references,assets --examples
```
For an existing skill, edit in place. Do not re-scaffold.

### Step 4: Author

#### SKILL.md — Frontmatter
Required fields only:
```yaml
---
name: my-skill                  # lowercase, hyphens, max 64 chars, matches folder name
description: "Single coherent paragraph covering what it does + when to use it; max 1024 chars."
---
```
**Description rules:** The description is the primary routing signal. Explicitly array the trigger words, file types, and scenarios. (Weak: "Helps with PDFs." Strong: "Extract text from PDF files, fill PDF forms. Use when the user asks about PDFs or document extraction.")

#### SKILL.md — Body
Write step-by-step instructions. Explain intent so agents can generalize, but keep it lean. Always end with a **Resources** section listing what is in `scripts/`, `references/`, and `assets/` **and exactly when to load them**.

#### References (`references/`)
- Reference files must extend the skill for a specific subtask.
- **Do not** use them as a README, training manual, or catalog.
- Add a table of contents at the top of any file over 100 lines.
- Never duplicate content between `SKILL.md` and a reference file.

#### What NOT to Include
Do not create: `README.md`, `CHANGELOG.md`, `INSTALLATION_GUIDE.md`. Evict any file that doesn't direct agent behavior.

### Step 5: Pressure-Test Behavior

Simulate realistic constraint scenarios (time pressure, authority pressure, sunk cost). Ensure the skill workflow forces the agent to behave correctly (e.g., verifying a scanner finding before claiming it). See `references/pressure-testing-skills.md`.

### Step 6: Validate and Package

```bash
# Validate frontmatter
python scripts/quick_validate.py <path/to/skill-folder>

# Package into a .skill archive (validates first)
python scripts/package_skill.py <path/to/skill-folder>
```
Fix all errors. Resolve all `TODO` markers.

### Step 7: Iterate

After real usage:
- If it under-triggers, improve the `description`.
- If a section doesn't improve output, remove it.
- If it grows too large, push depth into `references/`.
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
- See [references/pressure-testing-skills.md](references/pressure-testing-skills.md) for realistic RED/GREEN behavior tests for skills.
- See [references/skill-triggering-tests.md](references/skill-triggering-tests.md) for natural-prompt activation checks.

## Scripts

| Script | Purpose |
|---|---|
| `scripts/init_skill.py` | Scaffold a new skill directory with template |
| `scripts/package_skill.py` | Validate + zip a skill into a `.skill` file |
| `scripts/quick_validate.py` | Standalone SKILL.md frontmatter validator |
| `scripts/check_changed_files.py` | Safe changed-file newline and `git diff --check` hygiene checks |
