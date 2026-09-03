# AGENTS.md — malskill

## Skill change workflow

Before starting, read `knowledge/skill-creator/SKILL.md` — it defines skill structure, frontmatter rules, and validation flow that every change below depends on.

1. Hold the mantra: **brief, clear, specific, useful**. Every skill must help an agent act on its task. Every addition or edit must add concrete value — otherwise drop it. No justification, storytelling, statistics, or filler.
2. **Correctness over completeness.** Ground technical claims (SID-filter rules, CVE behavior, flag/tool semantics) in a real run or primary source. A subtly-wrong rule is worse than an omission because agents act on it — when unsure, state the precise condition, not lore.
3. Clarify the exact gap first, then pick the smallest change. **Default to enriching:**
   - **new skill** — only when no existing skill's `description` would ever route a user here
   - **enrich an existing skill** — parent `SKILL.md` is the right place
   - **new reference** — only when the subtask loads independently of the parent's other references
   - **enrich an existing reference** — deep-dive exists but has a real gap
   - **one canonical home per fact** — a technique that spans layers (tool/technique/ctf/role) is documented once where it is most actionable and cross-referenced from the others, never copied
   - **wire new depth into routing** — a new reference or major section is dead weight unless the parent `SKILL.md` points to it with an explicit "load when…" trigger
4. After the edit, validate the changed skill dir — `quick_validate.py` (frontmatter only), `sweep_skills.py <dir>` (broken links, placeholder markers, leaked workstation paths), and `check_changed_files.py` — before finishing.

## Tooling & Commands

- Scaffold a new skill: `python knowledge/skill-creator/scripts/init_skill.py <skill-name> --path <target-dir> --resources references`
- Validate one skill: `python knowledge/skill-creator/scripts/quick_validate.py <skill-dir>`
- Validate changed-file hygiene: `python knowledge/skill-creator/scripts/check_changed_files.py`
- Sweep a category or skill dir for broken links, placeholder markers, and workstation paths: `python knowledge/skill-creator/scripts/sweep_skills.py <path> [--ctf-check] [--top N]`
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
- `knowledge/`: Meta-skills (skill-creator, research helpers, orchestration, doc automation).
- `behaviours/`: Cross-cutting discipline skills (evidence gates, hypothesis-driven work, loop control, reading budget, verification, untrusted-input hygiene, operator modes).
- `coding/`, `ai/`, `hardware/`: Support categories.

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

- **Validation**: `quick_validate.py <skill-dir>` checks frontmatter only — pair it with `sweep_skills.py <skill-dir>` to catch broken links, placeholders, and leaked workstation paths in the body. Expand to the whole category only when the change spans multiple skill directories.
- **Hygiene**: Run `check_changed_files.py` (prefer this over dense PowerShell one-liners).
- **Debugging**: If validation fails, inspect the specific frontmatter/body issue before broad rewrites.
- **PR Titles**: `[skill-name] Short descriptive title`. Make one new skill per PR, or group related fixes together.
