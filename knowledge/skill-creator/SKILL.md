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

### 4. Explain Intent, Not Just Rules

Prefer explaining *why* a behavior matters over stacking rigid rules. Agents have strong theory of mind — when they understand the reasoning, they generalize better than when they follow mechanical constraints. If you find yourself writing `ALWAYS` or `NEVER` in caps, reframe as a rationale instead.

---

## Skill Creation Process

1. Understand the skill or audit the existing one (examples + success criteria)
2. Plan reusable resources (scripts/references/assets)
3. Prepare the working area (scaffold new or update existing)
4. Author SKILL.md + resources
5. Validate and package
6. Install and test
7. Iterate from real usage

---

### Step 1: Understand the Skill or Audit the Existing One

Gather concrete usage examples before writing anything. If the conversation already contains a workflow the user wants to capture, extract intent from it first — tools used, step sequence, corrections made, input/output formats observed. Only ask for what the conversation does not already answer; bias toward action.

When updating an existing skill, read the current `SKILL.md` first, then inspect only the scripts, references, or assets touched by the requested change. Identify three things before editing: what already works, what is stale, and what must remain stable (usually the skill's name, folder, and core activation scope).

Key questions (ask at most two at a time):
- "What specific tasks should this skill handle?"
- "What would a user type that should trigger this skill?"
- "What does success look like?"
- "What are the edge cases or failure modes?"

For a new skill, conclude with 3–5 representative usage examples. For an update, conclude with a clear statement of what changes, what stays, and what success looks like after the edit.

### Step 2: Plan Resources

For each example, ask: *what would an agent need to execute this repeatedly?*

| Resource type | Use when |
|---|---|
| `scripts/` | Same code is rewritten each time; deterministic output required |
| `references/` | Agent needs detailed docs, schemas, or policies at runtime |
| `assets/` | Output includes templates, images, or boilerplate the agent copies |

Produce a short resource plan before writing any code.

### Step 3: Prepare the Working Area

For a new skill, run the init script to scaffold the directory:

```bash
python scripts/init_skill.py <skill-name> --path <output-dir>
# With optional resource dirs and example placeholders:
python scripts/init_skill.py <skill-name> --path <output-dir> --resources scripts,references,assets --examples
```

The script creates the skill folder, a `SKILL.md` template with TODO placeholders, and optionally example files in each resource directory.

For an existing skill, do not re-scaffold it. Edit in place, or copy it to a writable location first if needed. Preserve the folder name and `name` field unless the user explicitly wants a rename or repositioning.

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
- This is the primary routing signal — make it assertive. Agents tend to under-trigger; explicitly list contexts and synonyms that should activate the skill, even when the user does not name the skill directly
- Cover near-miss cases: describe what the skill does *not* handle to reduce false triggers on adjacent domains

**Example:**
- Weak: `"Helps with PDFs."`
- Strong: `"Extract text and tables from PDF files, fill PDF forms, merge and split PDFs. Use when the user asks about PDFs, document extraction, form filling, or page manipulation — even if they don't say 'PDF' explicitly."`

#### SKILL.md — Body

Write step-by-step instructions the agent follows. Common structural patterns:

| Pattern | Best for |
|---|---|
| Workflow-based | Sequential processes with clear steps |
| Task-based | Tool collections with distinct operations |
| Reference/guidelines | Standards, policies, brand guides |
| Capabilities-based | Integrated systems with interrelated features |

Mix patterns as needed. Always end with a **Resources** section listing what is in `scripts/`, `references/`, and `assets/` and when to use each file.

**Writing guidance:**
- Keep skills lean — after each draft, re-read and remove anything the agent can infer on its own or that doesn't improve output quality.
- Explain the *why* behind each instruction; agents generalize better from reasoning than from rigid constraints.
- Use short examples over verbose explanations; one concrete input → output pair often replaces a paragraph.
- Write for the general case; avoid narrow fixes that only help one test prompt.
- When updating, prefer surgical edits: extend, trim, or reorganize existing sections before adding brand-new ones.

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

For updates, full reinstall is usually unnecessary — validate with `quick_validate.py`, then test the changed behavior with one representative prompt.

### Step 7: Iterate

After real usage, revisit:

1. Did the agent trigger the skill when it should have? → Improve `description`
2. Did the agent struggle with any step? → Add clarity or a script
3. Did `SKILL.md` exceed 500 lines? → Move content to `references/`
4. Are there new usage patterns? → Add examples or a new reference file
5. Did every test run recreate the same helper script? → Bundle it in `scripts/`
6. Did a section not improve any output? → Remove it
7. Did the update preserve the skill's identity? → Keep the original name, core purpose, and activation scope unless the user asked to change them

**Iteration mindset:** Generalize from specific feedback — a fix for one test prompt should improve all similar prompts, not just that one. Resist adding narrow patches; instead find the underlying instruction gap and address it. Challenge every line: if removing it doesn't hurt outputs, delete it.

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
