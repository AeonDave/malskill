# Getting Started

Set up a lightweight learning store so useful discoveries survive beyond the current session.

## 1. Create the directory and register it in project instructions

Create a local `.learnings/` folder in the project or workspace root:

```text
.learnings/
├── LEARNINGS.md
├── ERRORS.md
├── FEATURE_REQUESTS.md
└── STATUS.md
```

If you want starter content, copy from these assets:
- `assets/LEARNINGS.md`
- `assets/ERRORS.md`
- `assets/FEATURE_REQUESTS.md`
- `assets/STATUS.md`

Or let the helper scripts do it:
- `scripts/ensure_store.py --store-dir .learnings`
- `scripts/ensure_store.sh .learnings`

Then add a short section to the project's instruction file (`AGENTS.md`, `CLAUDE.md`, or `.github/copilot-instructions.md`) so future agent sessions know the store exists and which skill to use.

Minimum example:

```md
## Self-improvement

This project uses a `.learnings/` folder to track errors, corrections, discoveries, and session status.

- Before starting deep work, review `.learnings/STATUS.md` and scan relevant entries in `LEARNINGS.md` and `ERRORS.md`.
- After corrections, non-obvious failures, or session-end, log entries using the `self-improvement` skill.
```

If the project already contains equivalent guidance, verify it is still accurate instead of duplicating it.

## 2. Decide how learnings are stored

Choose one model and stick to it.

### Local-only

Use when the notes are personal working memory.

```gitignore
.learnings/
```

### Shared in repo

Use when the learnings are useful team knowledge and safe to version.

Do not ignore `.learnings/`.

### Hybrid

Use when you want the structure tracked but not the working entries.

```gitignore
.learnings/*.md
!.learnings/.gitkeep
```

## 3. Review before long tasks

Before starting a substantial task:
1. read `.learnings/STATUS.md` first to see where the last session stopped
2. identify the area, tools, or file types involved
3. search `.learnings/` for matching keywords, tags, or related files
4. read only the entries that are still relevant
5. carry the resulting rules into the task plan

This is especially valuable for:
- multi-session refactors
- repeated validator or packaging work
- BOF development and tool-specific gotchas
- documentation or skill-authoring workflows

## 4. Log at the right moments

Good logging triggers:
- the user says the current approach is wrong or incomplete
- a validator fails for a non-obvious reason
- you discover a repo-specific convention that was not documented elsewhere
- a better repeatable workflow emerges while debugging
- a missing helper or automation step becomes obvious

You can write these entries with:
- `scripts/log_learning.py --kind learning --summary "..." --details "..." --suggested-action "..."`
- `scripts/log_learning.sh --kind learning --store-dir .learnings --summary "..."`

Also supports `--kind error` (requires `--name`, `--error-text`) and `--kind feature` (requires `--name`, `--requested-capability`).

Bad logging triggers:
- trivial spelling mistakes
- obvious command misuse with no reusable lesson
- speculative ideas that were never tested

## 5. Optional automatic reminders

If your agent platform supports hook commands, wire the reminder helpers:
- `scripts/activator.py` for prompt-submit style reminders
- `scripts/error_detector.py` for command-result inspection

These scripts only emit short reminder text. They do not modify files.

### Windows with WSL

If you are on Windows and want to use the shell fallbacks reliably, run them through:

- `scripts/run_in_wsl.ps1`

Examples:

```text
powershell -File knowledge/self-improvement/scripts/run_in_wsl.ps1 ensure_store.sh .learnings
powershell -File knowledge/self-improvement/scripts/run_in_wsl.ps1 log_learning.sh --kind learning --store-dir .learnings --summary "..."
```

This avoids the Windows-to-Bash path mangling that can happen when calling `bash script.sh` directly from PowerShell.

## 6. Promote only what deserves it

Do not flood project instructions with raw incident logs. Distill first.

Promote only when the rule is:
- short
- verified
- broadly relevant
- more useful as prevention than as history

Once that threshold is met, use:

Promote into a project file:

```text
scripts/promote_learning.py --source-file .learnings/LEARNINGS.md --entry-id LRN-YYYYMMDD-001 --target file --target-file AGENTS.md
```

Promote into a new skill:

```text
scripts/promote_learning.py --source-file .learnings/LEARNINGS.md --entry-id LRN-YYYYMMDD-001 --target skill --skills-root knowledge
```

Shell equivalents (`promote_learning.sh`, `extract_skill.sh`) accept the same arguments.

For promotion strategy, load `references/promotion-guidelines.md`.

## 7. Optional OpenClaw path

If you use OpenClaw, load `references/openclaw-integration.md`. Keep that path optional; the core workflow works without it.

## 8. Write a new skill only when justified

If a learning is genuinely reusable beyond the current repository, scaffold a new skill with:
- `scripts/extract_skill.py`
- `scripts/extract_skill.sh`

Prefer promotion to project instructions for narrow repository rules. Reserve new skills for reusable workflows.

## 9. What gets automated and what still needs judgment

Automated well:
- creating the store
- generating entry IDs
- appending structured entries
- updating source entry status during promotion
- scaffolding a new skill from a validated learning

Still requires judgment:
- deciding whether a learning is truly reusable
- distilling the shortest useful rule for project instructions
- deciding whether a new skill is warranted or overkill
- refining a generated skill when the learning is complex

Use automation for mechanics. Use judgment for promotion scope.
