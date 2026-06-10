# AGENTS.md — malskill

## Commands

- Scaffold a new skill: `python knowledge/skill-creator/scripts/init_skill.py <skill-name> --path <target-dir> --resources references`
- Validate one skill: `python knowledge/skill-creator/scripts/quick_validate.py <skill-dir>`
- Check changed-file hygiene: `python knowledge/skill-creator/scripts/check_changed_files.py`
- Package one skill: `python knowledge/skill-creator/scripts/package_skill.py <skill-dir>`
- Install skills interactively (PowerShell): `.\install.ps1` (supports `folder|skill|zip` with `flat|group` layouts)
- Install skills interactively (Bash): `./install.sh` (supports `folder|skill|zip` with `flat|group` layouts)
- For multi-skill validation, run `quick_validate.py <skill-dir>` once per skill; if a broader sweep is needed, use `python knowledge/skill-creator/scripts/validate_all.py`

## Active user decisions

- Keep `Project structure` sections folder-level only; do not turn them into file inventories.
- Treat `AGENTS.md` as a living operational file; update it after important repo changes or when workflows/tool availability materially change.
- `malskill` is an offsec-curated skill set; support categories such as `coding/`, `knowledge/`, `behaviours/`, `ai/`, `hardware/`, and `commands/` are valid only when they directly improve the active security task.
- Every loaded skill must help the active task. Do not load skills for design justification, benchmark/stats dumps, background reading, or generic narration.
- Put developer-facing detail in `README.md` first; use `references/` only when the detail is too deep or too specialized for the README.
- Code comments must be in English, technical, precise, and brief; explain intent or non-obvious behavior, not obvious syntax.
- When improving or curating tool skills, use external research (`fetch_webpage` plus Tavily/web search) for important, missing, disputed, or potentially outdated tools instead of relying only on local repo context.
- Tool skills clearly covered by stronger existing tools, duplicated elsewhere in the repo, or materially worse than modern alternatives may be removed unless the user explicitly asks to keep them.
- For every new skill, replacement skill, or major skill refactor, follow `knowledge/skill-creator/` guidance first and keep the resulting skill aligned with AgentSkills conventions.
- Keep `offensive-tools/` and `offensive-techniques/` strictly separated: `offensive-tools/` is for tool-specific usage guides, while `offensive-techniques/` is for general methodology/tradecraft that may reference tools without becoming tool manuals.
- When the same topic exists in both layers (for example fuzzing), keep the distinction explicit: tool flags/workflows belong in `offensive-tools/fuzzing/`; technique process and strategy belong in `offensive-techniques/fuzzing-technique/`.
- Keep `offensive-roles/` as supervisor/operator routing guidance: role skills compose `*-technique` methodology and optimized tool skills, but they must not become tool manuals or replace the technique layer.
- Keep `offensive-ctf/` separate from field offsec skills: it is for lab/challenge/flag-style workflows and may route into technique/tool skills only as support.
- `offensive-ctf/` captures challenge-derived patterns that may still help real-world tasks when the artifact, primitive, or workflow matches. Use it as a support layer, not as platform-specific writeup culture.

## Testing

- After changing a skill, validate the changed skill with `quick_validate.py` before finishing.
- After changing shared scaffolding or shared guidance in `knowledge/skill-creator/` or `knowledge/agent-md-creator/`, revalidate the affected skill folders.
- Prefer the smallest relevant validation command first; expand only when the change affects multiple skill directories.
- Prefer `check_changed_files.py` over dense PowerShell one-liners for newline and `git diff --check` validation.

## Debugging

- Use local evidence first: validator output, file structure, frontmatter, and the target skill's own `SKILL.md`.
- If a skill edit keeps failing validation, inspect the specific frontmatter/body issue before broad rewrites.
- Create small temporary helpers only when they materially speed up validation or structure checks; remove them when done.

## Project structure

- `offensive-tools/` — category folders such as `recon/`, `fuzzing/`, `cryptography/`, `web/`, or `windows/`; each category contains one folder per tool skill.
- `offensive-techniques/` — technique-first, tool-agnostic skills (for example `fuzzing-technique/`) describing how to execute an approach, choose tools, and run a methodology without turning into per-tool command guides.
- `offensive-roles/` — supervisor and vertical operator role skills for mission routing, delegation packets, evidence expectations, and handoffs across technique/tool skills.
- `offensive-coding/` — offensive development skills, including nested `bof-dev/` BOF skills plus workflow-focused skills like `edr-evasion-dev/`, `linux-internals-dev/`, and `windows-internals-dev/`.
- `offensive-ctf/` — offensive CTF/lab-solving skills, including dispatcher and dedicated `*-ctf` category skills for ICS/OT, hardware/embedded, game/GamePwn, blockchain/Web3, web, crypto, pwn, reverse, forensics, misc, OSINT, AI/ML, mobile, malware, and writeup workflows.
- `offensive-hardware/` — hardware-focused offensive skills for real-world assessments: physical device compromise, serial console attacks, firmware extraction, peripheral protocol exploitation (PJL), and embedded OS post-exploitation.
- `coding/` — language and pattern skills such as C/C++, Go, Python, Rust, assembly, plus cross-cutting TDD, testing reliability, and systematic debugging guidance.
- `knowledge/` — meta-skills and research helpers, including `skill-creator/`, `agent-md-creator/`, `opencode-agent-creator/` (OpenCode CLI agent/subagent team builder), design/planning workflows, deep-research skills, evidence/completion gates, feedback triage, and agentic orchestration workflows.
- `ai/` — AI framework skills (for example `langchain-py/`).
- `hardware/` — hardware-oriented non-offensive skills and subdomains (for example `arduino/`).
- `commands/` — agent behavior and command modes, controlling how the agent reasons and communicates.
- `AGENTS.md` — root operational guidance for the whole repository.

## Conventions

- Every skill root must contain `SKILL.md` with valid YAML frontmatter; `name` must match the folder name and use lowercase hyphens.
- Aim to keep the substantive body of `SKILL.md` around 500 lines as a soft target (not validator-enforced); move deep dives, long examples, and reference material to `references/`. Link/index sections like `## Reference Files` or `## Resources` do not count toward this target.
- `references/` files must extend the skill: deep dives, extra procedures, lookup tables, long examples, or domain detail the agent loads on demand to act. They are not a skill README and not a design/rationale justifier — never use a reference to explain or defend why the skill is built the way it is.
- Load `references/` only for a clear subtask. Pattern: broad parent skill first, then the narrowest reference that adds concrete task value.
- Remove or rewrite references that behave like catalogs, study guides, README material, or general background without a clear subtask trigger.
- Keep meta-justification (benchmarks, "why this exists", design defense) out of both `SKILL.md` and `references/`. If maintenance rationale is truly needed, reduce it to terse actionable rules; do not let it become prose.
- Use `scripts/` for deterministic helpers the agent can run and `assets/` for templates or static supporting files.
- Each skill folder is independent; read the local `SKILL.md` before editing resources under that skill.
- Prefer qualitative comments over verbose narration; document intent, constraints, and non-obvious tradeoffs.
- Do not commit workstation-specific absolute paths, usernames, home directories, or other local private data in `SKILL.md`, `references/`, `assets/`, examples, or scripts.
- Use portable placeholders in examples, such as `<workspace-root>`, `C:\path\to\file`, `/path/to/file`, or environment variables, instead of real local machine paths.

## Boundaries

- Ask first before large restructures across many skill folders, mass renames, or deleting categories.
- Never add fake commands, placeholder paths, or guessed repo structure to `AGENTS.md`.
- Do not move developer documentation into `AGENTS.md`; keep it in `README.md` or `references/`.
- Outside `offensive-ctf/`, never reference CTF competitions, challenge names, competition platforms, or CTF-platform branding; field skills must stay generic, real-world professional methodology for penetration testing, red team operations, and domain-specific analysis.
- Inside `offensive-ctf/`, keep challenge language generic and avoid platform/competition branding unless the user is explicitly working from provided archival material.

## PR instructions

- Use the title format `[skill-name] Short descriptive title` for skill-scoped changes.
- Ensure edited `SKILL.md` files validate and their `name` fields still match folder names.
- Include a brief summary of the capability, workflow, or guidance that changed.
- Prefer one new skill per PR; group related fixes together.
