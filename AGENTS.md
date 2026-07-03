# AGENTS.md — malskill

## Skill change workflow

Follow this for any request to add or update a skill or reference.

1. Hold the mantra: **brief, clear, specific, useful**. Every skill must help an agent act on its task. Every addition or edit must add concrete value — otherwise drop it. No justification, storytelling, statistics, or filler.
2. Clarify the exact gap first, then pick the smallest change:
   - **new skill** — capability has no existing home
   - **enrich an existing skill** — parent `SKILL.md` is the right place
   - **new reference** — a distinct subtask needs its own on-demand deep-dive
   - **enrich an existing reference** — deep-dive exists but has a real gap
3. Read `knowledge/skill-creator/SKILL.md` first, apply the change, validate with `quick_validate.py`, and run `check_changed_files.py` before finishing.

## Tooling & Commands

- Scaffold a new skill: `python knowledge/skill-creator/scripts/init_skill.py <skill-name> --path <target-dir> --resources references`
- Validate one skill: `python knowledge/skill-creator/scripts/quick_validate.py <skill-dir>`
- Validate changed-file hygiene: `python knowledge/skill-creator/scripts/check_changed_files.py`
- Package one skill: `python knowledge/skill-creator/scripts/package_skill.py <skill-dir>`
- Install interactively: `.\install.ps1` (PowerShell) or `./install.sh` (Bash)

## Repository Structure & Boundaries

`malskill` is an offsec-curated skill set. Support skills (`coding/`, `knowledge/`, `ai/`, etc.) exist only to improve the active security task.

- `offensive-tools/`: Tool-specific usage guides, syntax, and flags.
- `offensive-techniques/`: Tool-agnostic methodology, tradecraft, and attack paths. Do not turn these into tool manuals.
- `offensive-roles/`: Supervisor/operator routing. Composes techniques and tools.
- `offensive-coding/`: Offensive development (BOFs, loaders, EDR evasion, OS internals).
- `offensive-hardware/`: Hardware-focused assessments (device compromise, firmware extraction).
- `offensive-ctf/`: Challenge-derived patterns. Use as a support layer for real-world tasks when artifacts or workflows match; avoid platform-specific writeup culture.
- `knowledge/`: Meta-skills (skill-creator, research helpers, orchestration).
- `coding/`, `ai/`, `hardware/`, `commands/`: Support categories.

## Skill Structure & Conventions

- **YAML Frontmatter**: Required in `SKILL.md`. `name` must match the folder name exactly (lowercase hyphens).
- **SKILL.md body**: Keep it focused and concise. Focus on baseline workflow, routing, and task guidance.
- **references/** files: Load-on-demand deep dives extending the skill for specific subtasks.
  - Pattern: Broad parent skill first, then narrowest reference that adds concrete task value.
  - DO NOT use references as catalogs, study guides, READMEs, or general background.
- **scripts/** & **assets/**: Deterministic executable helpers and templates.
- **No Meta-justifications**: Keep benchmarks, "why this exists", and design defense out of `SKILL.md` and `references/`. Rationale must be reduced to terse, actionable rules.
- **No Workspace Spillage**: Do not commit workstation-specific absolute paths or usernames. Use portable placeholders (`<workspace-root>`, `/path/to/thing`).
- **Code Comments**: English, technical, precise, brief. Explain intent/edge cases, not obvious syntax.

## Testing & PRs

- **Validation**: Prefer the smallest relevant validation command first (`quick_validate.py <skill-dir>`). Expand only when the change affects multiple skill directories.
- **Hygiene**: Run `check_changed_files.py` (prefer this over dense PowerShell one-liners).
- **Debugging**: If validation fails, inspect the specific frontmatter/body issue before broad rewrites.
- **PR Titles**: `[skill-name] Short descriptive title`. Make one new skill per PR, or group related fixes together.
