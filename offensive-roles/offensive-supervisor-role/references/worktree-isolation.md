# Worktree Isolation

Use git worktrees when experimentation may contaminate the main workspace.

## Use a worktree for

- exploit PoC branches with generated artifacts
- payload or loader experiments
- broad skill refactors across many folders
- risky dependency updates or build-system changes
- parallel implementation tasks on the same repository

## Avoid a worktree when

- the change is a one-line fix
- the repo is not clean and uncommitted work ownership is unclear
- the task requires shared local state that is hard to duplicate

## Isolation workflow

1. Check current git status and note pre-existing user changes.
2. Choose a location by project convention: existing `.worktrees/`, existing `worktrees/`, documented repo preference, then ask.
3. For project-local worktree directories, verify they are ignored before creating the worktree.
4. Create a branch/worktree with a descriptive task name.
5. Run project setup and baseline validation before edits.
6. Keep generated binaries, dumps, corpora, and captures out of tracked source unless explicitly required.
7. Merge, preserve, or discard only after validation and user-facing summary.

## Ignore and baseline gates

- If using `.worktrees/` or `worktrees/`, check whether Git ignores the directory. Add an ignore rule first if needed.
- If baseline tests fail in the new worktree, report the failures and ask whether to proceed or investigate. Do not hide baseline instability.
- Record the worktree path and branch name in the task notes so cleanup is possible later.

## Completion choices

When the work is complete and verified, present a small set of explicit choices:

1. merge back to the base branch locally,
2. push and open a review request,
3. keep the branch/worktree as-is,
4. discard the work after typed confirmation.

Do not delete a worktree for “keep as-is”. Do not discard work without explicit confirmation and a summary of what will be removed.

## Offensive-specific cautions

- Do not commit target identifiers, credentials, captures, payload binaries, or local absolute paths.
- Keep destructive tests behind explicit operator approval.
- Record cleanup steps for any local services, listeners, or generated artifacts.
