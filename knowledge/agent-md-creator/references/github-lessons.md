# GitHub Blog Lessons (Nov 2025)

Condensed notes from GitHub's article **"How to write a great agents.md: Lessons from over 2,500 repositories"**.

Source:
- `https://github.blog/ai-and-ml/github-copilot/how-to-write-a-great-agents-md-lessons-from-over-2500-repositories/`

## What the article says works

### 1. Put commands early

The article explicitly recommends putting executable commands near the top of the file so the agent can use them repeatedly without searching through prose.

High-value commands:

- install / bootstrap
- dev server
- lint / typecheck
- fast test command
- full test command
- build only if it is part of the normal agent workflow

### 2. Use code examples instead of abstract explanations

One short, real example of the preferred style is usually better than a paragraph of generic rules.

Use examples only when they materially improve output quality.

### 3. Set boundaries clearly

The strongest files define what the agent:

- should always do
- should ask first about
- should never do

Good boundaries prevent expensive or destructive mistakes:

- secrets
- production deploys
- schema changes
- generated/vendor directories
- deleting tests to make CI pass

### 4. Be specific about the stack

The article recommends naming real frameworks, versions, and directories instead of vague labels.

Prefer:

- `FastAPI + Pydantic v2`
- `React 18 + TypeScript + Vite`
- `tests/integration/` contains API integration tests

Avoid:

- "Python backend"
- "frontend app"

### 5. Cover the six core areas when relevant

GitHub identifies six areas that repeatedly show up in effective files:

1. commands
2. testing
3. project structure
4. code style
5. git workflow
6. boundaries

Do **not** force all six into every repo. Include only the ones supported by real repo facts.

### 6. Start minimal and iterate

The article argues against writing a giant file up front.

Recommended approach:

- start with a narrow, practical file
- observe where the agent makes mistakes
- add only the missing constraints or commands
- keep pruning generic text

## How to apply this in practice

When writing `AGENTS.md`:

- lead with exact commands
- keep bullets short
- include only repo-specific facts
- add one example only if it clarifies style
- add boundaries only for real risks
- prefer nested files over one giant root file in complex repos

## What to avoid

- generic assistant persona filler
- repeating the README
- long motivation or background sections
- undocumented assumptions about commands or stack
- huge style sections with no actionable examples
- one root file trying to describe every subproject in detail

## Minimal interpretation for this skill

Translate the article into these defaults:

- short root `AGENTS.md`
- commands first
- test expectations second
- project paths and conventions next
- boundaries last
- split into nested files when exceptions start piling up
