# AGENTS.md — malskill

## Commands

- Scaffold a new skill: `python knowledge/skill-creator/scripts/init_skill.py <skill-name> --path <target-dir> --resources references`
- Validate one skill: `python knowledge/skill-creator/scripts/quick_validate.py <skill-dir>`
- Package one skill: `python knowledge/skill-creator/scripts/package_skill.py <skill-dir>`
- Install skills interactively (PowerShell): `.\install.ps1` (supports `folder|skill|zip` with `flat|group` layouts)
- Install skills interactively (Bash): `./install.sh` (supports `folder|skill|zip` with `flat|group` layouts)
- Validate a whole section (Bash): `find <section> -type f -name SKILL.md -exec dirname {} \; | sort -u | while IFS= read -r dir; do python knowledge/skill-creator/scripts/quick_validate.py "$dir"; done`
- Validate a whole section: `Get-ChildItem <section> -Recurse -Directory | ForEach-Object { python knowledge/skill-creator/scripts/quick_validate.py $_.FullName }`

## Active user decisions

- Keep `Project structure` sections folder-level only; do not turn them into file inventories.
- Treat `AGENTS.md` as a living operational file; update it after important repo changes or when workflows/tool availability materially change.
- Put developer-facing detail in `README.md` first; use `references/` only when the detail is too deep or too specialized for the README.
- Code comments must be in English, technical, precise, and brief; explain intent or non-obvious behavior, not obvious syntax.
- When improving or curating tool skills, use external research (`fetch_webpage` plus Tavily/web search) for important, missing, disputed, or potentially outdated tools instead of relying only on local repo context.
- Tool skills clearly covered by stronger existing tools, duplicated elsewhere in the repo, or materially worse than modern alternatives may be removed unless the user explicitly asks to keep them.
- For every new skill, replacement skill, or major skill refactor, follow `knowledge/skill-creator/` guidance first and keep the resulting skill aligned with AgentSkills conventions.

## Testing

- After changing a skill, validate the changed skill with `quick_validate.py` before finishing.
- After changing shared scaffolding or shared guidance in `knowledge/skill-creator/` or `knowledge/agent-md-creator/`, revalidate the affected skill folders.
- Prefer the smallest relevant validation command first; expand only when the change affects multiple skill directories.

## Debugging

- Use local evidence first: validator output, file structure, frontmatter, and the target skill's own `SKILL.md`.
- If a skill edit keeps failing validation, inspect the specific frontmatter/body issue before broad rewrites.
- Create small temporary helpers only when they materially speed up validation or structure checks; remove them when done.

## Project structure

- `offensive-tools/` — category folders such as `recon/`, `web-app/`, or `windows/`; each category contains one folder per tool skill.
- `offensive-coding/` — offensive development skills, including `bof/` plus workflow-focused skills like `edr-evasion/` and `windows-internals/`.
- `coding/` — language and pattern skills such as C/C++, Go, Python, Rust, and assembly patterns/testing/performance guidance.
- `knowledge/` — meta-skills and research helpers, including `skill-creator/`, `agent-md-creator/`, and deep-research skills.
- `ai/` — AI framework skills (for example `langchain-py/`).
- `hardware/` — hardware-oriented skills and subdomains (for example `arduino/`).
- `offensive-hardware/` — reserved for offensive hardware-focused skills.
- `AGENTS.md` — root operational guidance for the whole repository.

## Conventions

- Every skill root must contain `SKILL.md` with valid YAML frontmatter; `name` must match the folder name and use lowercase hyphens.
- Keep `SKILL.md` under 500 lines; move deep dives, long examples, and reference material to `references/`.
- Use `scripts/` for deterministic helpers the agent can run and `assets/` for templates or static supporting files.
- Each skill folder is independent; read the local `SKILL.md` before editing resources under that skill.
- Prefer qualitative comments over verbose narration; document intent, constraints, and non-obvious tradeoffs.
- Do not commit workstation-specific absolute paths, usernames, home directories, or other local private data in `SKILL.md`, `references/`, `assets/`, examples, or scripts.
- Use portable placeholders in examples, such as `<workspace-root>`, `C:\path\to\file`, `/path/to/file`, or environment variables, instead of real local machine paths.

## Boundaries

- Ask first before large restructures across many skill folders, mass renames, or deleting categories.
- Never add fake commands, placeholder paths, or guessed repo structure to `AGENTS.md`.
- Do not move developer documentation into `AGENTS.md`; keep it in `README.md` or `references/`.

## PR instructions

- Use the title format `[skill-name] Short descriptive title` for skill-scoped changes.
- Ensure edited `SKILL.md` files validate and their `name` fields still match folder names.
- Include a brief summary of the capability, workflow, or guidance that changed.
- Prefer one new skill per PR; group related fixes together.