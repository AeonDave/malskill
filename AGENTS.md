# AGENTS.md — malskill

## Commands

- Scaffold a new skill: `python knowledge/skill-creator/scripts/init_skill.py <skill-name> --path <target-dir> --resources references`
- Validate one skill: `python knowledge/skill-creator/scripts/quick_validate.py <skill-dir>`
- Package one skill: `python knowledge/skill-creator/scripts/package_skill.py <skill-dir>`
- Validate a whole section: `Get-ChildItem <section> -Recurse -Directory | ForEach-Object { python knowledge/skill-creator/scripts/quick_validate.py $_.FullName }`

## Active user decisions

- Keep `Project structure` sections folder-level only; do not turn them into file inventories.
- Treat `AGENTS.md` as a living operational file; update it after important repo changes or when workflows/tool availability materially change.
- Put developer-facing detail in `README.md` first; use `references/` only when the detail is too deep or too specialized for the README.
- Code comments must be in English, technical, precise, and brief; explain intent or non-obvious behavior, not obvious syntax.

## Testing

- After changing a skill, validate the changed skill with `quick_validate.py` before finishing.
- After changing shared scaffolding or shared guidance in `knowledge/skill-creator/` or `knowledge/agent-md-creator/`, revalidate the affected skill folders.
- Prefer the smallest relevant validation command first; expand only when the change affects multiple skill directories.

## Debugging

- Use local evidence first: validator output, file structure, frontmatter, and the target skill's own `SKILL.md`.
- If a skill edit keeps failing validation, inspect the specific frontmatter/body issue before broad rewrites.
- Create small temporary helpers only when they materially speed up validation or structure checks; remove them when done.

## Project structure

- `bof/` — BOF-focused skills; each skill root typically contains `SKILL.md` plus optional `assets/`, `references/`, and `scripts/`.
- `offensive-tools/` — category folders such as `recon/`, `web-app/`, or `windows/`; each category contains one folder per tool skill.
- `programming/` — language and pattern skills such as C/C++, Go, Python, and assembly patterns/testing/performance guidance.
- `knowledge/` — meta-skills and research helpers, including `skill-creator/`, `agent-md-creator/`, and deep-research skills.
- `AGENTS.md` — root operational guidance for the whole repository.

## Conventions

- Every skill root must contain `SKILL.md` with valid YAML frontmatter; `name` must match the folder name and use lowercase hyphens.
- Keep `SKILL.md` under 500 lines; move deep dives, long examples, and reference material to `references/`.
- Use `scripts/` for deterministic helpers the agent can run and `assets/` for templates or static supporting files.
- Each skill folder is independent; read the local `SKILL.md` before editing resources under that skill.
- Prefer qualitative comments over verbose narration; document intent, constraints, and non-obvious tradeoffs.

## Boundaries

- Ask first before large restructures across many skill folders, mass renames, or deleting categories.
- Never add fake commands, placeholder paths, or guessed repo structure to `AGENTS.md`.
- Do not move developer documentation into `AGENTS.md`; keep it in `README.md` or `references/`.

## PR instructions

- Use the title format `[skill-name] Short descriptive title` for skill-scoped changes.
- Ensure edited `SKILL.md` files validate and their `name` fields still match folder names.
- Include a brief summary of the capability, workflow, or guidance that changed.
- Prefer one new skill per PR; group related fixes together.