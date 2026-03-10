---
name: skill-creator
description: "Design, create, update, and package Agent Skills following the open AgentSkills specification (agentskills.io). Use when asked to create a new skill, improve an existing skill, scaffold a skill directory, validate a SKILL.md, or package a skill into a distributable .skill file."
license: MIT
metadata:
  author: AeonDave
  version: "1.0"
---

# Skill Creator

Guidance for creating and maintaining high-quality Agent Skills that work across all AI agents.

## What Is a Skill

A skill is a self-contained folder that gives any AI agent specialized knowledge, workflows, and tools for a specific domain. Skills use the open [AgentSkills specification](https://agentskills.io/specification).

### Directory Structure

```
skill-name/
├── SKILL.md          # Required — frontmatter + instructions
├── scripts/          # Optional — executable code agents can run
├── references/       # Optional — docs loaded on demand into context
└── assets/           # Optional — templates, images, data files used in output
```

### What Skills Provide

- Specialized multi-step workflows for specific domains
- Reusable scripts for deterministic, repeatable operations
- Domain knowledge, schemas, and policies the agent cannot infer
- Templates and boilerplate assets for consistent output

---

## Core Design Principles

### 1. Concise is Key

The context window is shared. Every token in a skill competes with the user's request, conversation history, and other skills. Challenge every sentence: *does the agent actually need this?* Prefer short examples over verbose explanations.

### 2. Progressive Disclosure

Design for staged loading:

- **Discovery**: `name` + `description` only
- **Activation**: full `SKILL.md` body (keep under **500 lines**)
- **On demand**: files in `scripts/`, `references/`, `assets/`

Move detail to `references/` so the agent loads only what it needs.

### 3. Agent-Neutral Language

Skills are executed by different AI agents (Claude, Gemini, Codex, etc.). Write instructions in imperative form. Never hardcode a product name inside the skill body; say "the agent" instead.

---

## Skill Creation Process

1. Understand the skill (examples + success criteria)
2. Plan reusable resources (scripts/references/assets)
3. Initialize the directory (scaffold)
4. Author SKILL.md + resources
5. Validate and package
6. Install and test
7. Iterate from real usage

---

### Step 1: Understand the Skill

Gather concrete usage examples before writing anything. Ask at most two clarifying questions at a time; bias toward action.

Useful questions:
- "What specific tasks should this skill handle?"
- "What would a user type that should trigger this skill?"
- "What does success look like?"

Conclude this step with a clear list of 3–5 representative usage examples.

### Step 2: Plan Resources

For each example, ask: *what would an agent need to execute this repeatedly?*

| Resource type | Use when |
|---|---|
| `scripts/` | Same code is rewritten each time; deterministic output required |
| `references/` | Agent needs detailed docs, schemas, or policies at runtime |
| `assets/` | Output includes templates, images, or boilerplate the agent copies |

Produce a short resource plan before writing any code.

### Step 3: Initialize

Run the init script to scaffold the directory:

```bash
python scripts/init_skill.py <skill-name> --path <output-dir>
# With optional resource dirs and example placeholders:
python scripts/init_skill.py <skill-name> --path <output-dir> --resources scripts,references,assets --examples
```

The script creates the skill folder, a `SKILL.md` template with TODO placeholders, and optionally example files in each resource directory.

> **Note:** Use the absolute path to this skill-creator's `scripts/` directory.

### Step 4: Author

#### SKILL.md — Frontmatter

Required fields only; no extras:

```yaml
---
name: my-skill                  # lowercase, hyphens, max 64 chars, matches folder name
description: >                  # what it does + when to use it; max 1024 chars
  Single coherent paragraph covering capabilities and activation triggers.
---
```

Optional fields (add only when meaningful):

```yaml
license: MIT
compatibility: Requires Python 3.11+, git
metadata:
  author: your-org
  version: "1.0"
allowed-tools: Bash(python:*) Read   # experimental
```

**Description rules:**
- Include both *what* the skill does and *when* to activate it
- Mention file types, task keywords, and activation phrases
- Max 1 024 characters; no angle brackets
- This is the primary routing signal — make it precise

#### SKILL.md — Body

Write step-by-step instructions the agent follows. Common structural patterns:

| Pattern | Best for |
|---|---|
| Workflow-based | Sequential processes with clear steps |
| Task-based | Tool collections with distinct operations |
| Reference/guidelines | Standards, policies, brand guides |
| Capabilities-based | Integrated systems with interrelated features |

Mix patterns as needed. Always end with a **Resources** section listing what is in `scripts/`, `references/`, and `assets/` and when to use each file.

#### Scripts (`scripts/`)

- Write in Python 3 (preferred) or Bash
- Output must be LLM-friendly: clean success/failure strings, no raw tracebacks, truncate long output
- Test every script before committing
- Document dependencies with a `# requires: package` comment or a `requirements.txt`

#### References (`references/`)

- One file per domain/topic — agents load these individually
- Add a table of contents at the top of any file over 100 lines
- Link all reference files explicitly from `SKILL.md` with a note on when to load them
- Never duplicate content between `SKILL.md` and a reference file

#### Assets (`assets/`)

- Static files copied or used in agent output
- Not loaded into context — size is not a concern
- Use subdirectories for complex templates (e.g., `assets/project-template/`)

#### What NOT to Include

Do not create: `README.md`, `CHANGELOG.md`, `INSTALLATION_GUIDE.md`, or any file that documents the skill creation process rather than the skill's domain. Every file must justify its presence to an agent executing the skill.

### Step 5: Validate and Package

**Validate:**

```bash
python scripts/quick_validate.py <path/to/skill-folder>
# Or the official CLI (if installed):
skills-ref validate <path/to/skill-folder>
```

Fix all errors. Resolve all `TODO` markers before packaging.

**Package:**

```bash
python scripts/package_skill.py <path/to/skill-folder>
# Optional output dir:
python scripts/package_skill.py <path/to/skill-folder> ./dist
```

The packager validates first, then creates `<skill-name>.skill` (a zip file). Output path is printed on success.

### Step 6: Install and Test

Install the packaged skill using your agent platform's install mechanism (CLI/UI). If your platform supports scopes, prefer **workspace/repo scope** while iterating.

After installation, reload skills (if required by the platform), then run one representative example from Step 1 and verify:

- the skill triggers when it should
- the steps are followed correctly
- scripts/resources are discovered and used as intended

### Step 7: Iterate

After real usage, revisit:

1. Did the agent trigger the skill when it should have? → Improve `description`
2. Did the agent struggle with any step? → Add clarity or a script
3. Did `SKILL.md` exceed 500 lines? → Move content to `references/`
4. Are there new usage patterns? → Add examples or a new reference file

---

## Skill Naming Conventions

- Lowercase letters, digits, and hyphens only — e.g., `pdf-extractor`, `gh-address-comments`
- Max 64 characters; no leading/trailing/consecutive hyphens
- Folder name must match the `name` field exactly
- Prefer verb-led or noun-led phrases: `code-review`, `rotate-pdf`, `deploy-aws`
- Namespace by tool when it aids discovery: `gh-`, `linear-`, `jira-`

---

## Reference Files

- See [references/patterns.md](references/patterns.md) for progressive disclosure patterns and structural examples
- See [references/spec.md](references/spec.md) for the full AgentSkills frontmatter field reference

## Scripts

| Script | Purpose |
|---|---|
| `scripts/init_skill.py` | Scaffold a new skill directory with template |
| `scripts/package_skill.py` | Validate + zip a skill into a `.skill` file |
| `scripts/quick_validate.py` | Standalone SKILL.md frontmatter validator |
