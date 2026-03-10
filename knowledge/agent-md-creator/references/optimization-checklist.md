# AGENTS.md Optimization Checklist

Use this checklist to keep `AGENTS.md` technical, precise, and cheap in tokens.

## Keep

- commands that the agent can actually run
- prerequisite commands with their trigger condition noted (e.g., "run after evasion/ changes")
- short active-decision bullets for persistent user tool/workflow choices
- file-scoped or package-scoped test commands when available
- short, explicit testing expectations when changed behavior should be covered by tests
- short folder-level path notes that reduce repeated exploration
- non-obvious conventions and architectural constraints
- short comment-style guidance when it materially changes how code should be documented
- hard constraint tables with safe alternatives when violations are silent but costly
- new-code checklists when the project has many non-obvious rules that apply together
- short numbered extension guides for modular architectures ("adding a new X")
- short debugging rules that tell the agent how to gather evidence and when to escalate
- short accepted-diagnostic notes when the user explicitly wants a warning or error left alone
- high-risk boundaries such as secrets, generated code, vendor dirs, migrations, or production deploys

## Remove

- generic persona text like "you are a helpful assistant"
- repeated README content
- long background explanations
- aspirational rules that are not enforced in the repo
- commands that are stale, slow, or unverifiable
- huge code samples unless one short example changes output quality
- project structure sections that expand into long file-by-file inventories
- **interface definitions, struct declarations, and type signatures** — these document what exists, not what to do; they belong in README
- **behavioral deep-dives** explaining how techniques, algorithms, or internal pipelines work — keep step-by-step only for the specific actions the agent must perform
- vague debugging advice like "investigate carefully" without any escalation rule or tooling hints
- decision sections that mirror the whole chat log instead of just current durable choices
- accepted diagnostics without scope, reason, or revisit condition

## Draft targets

- small repo: ~30–80 lines
- medium repo: ~60–120 lines
- monorepo root: keep broad, push details into nested files
- nested file: keep local and focused

## Section order

Prefer this order unless the repo strongly suggests another:

1. `## Commands`
2. `## Active user decisions` (only if needed)
3. `## Testing`
4. `## Debugging` (only if materially useful)
5. `## Project structure`
6. `## Code style` or `## Conventions`
7. `## Accepted diagnostics` (only if needed)
8. `## Boundaries`
9. `## PR instructions`

## Quality checks

Before saving, ask:

- would this line change how the agent behaves?
- is this fact specific to this repo?
- does this command exist right now?
- would this still be true if the team's current tools or workflow changed next month?
- can a shorter bullet say the same thing?
- should this live in a nested file instead of root?
- did an important repo change just happen that should update `AGENTS.md`?
- if debugging is included, does it tell the agent what evidence to gather and when to escalate?
- if user decisions are included, are they still active and actually useful?
- if accepted diagnostics are included, are they scoped clearly enough to stop repeated re-analysis?
- **does this section tell the agent what to do, or does it document how the code works?** If the latter, it belongs in README.
- if the project has hard constraints, is each one paired with a safe alternative?
- if comment guidance is included, does it improve comment quality without encouraging noisy line-by-line commentary?

## Rewrite patterns

### Too vague

- "Follow best practices"
- "Run tests before finishing"

### Better

- `pytest tests/unit -q`
- `npm run lint && npm test`
- `src/server/` owns API routes; do not place handlers in `src/ui/`
- `apps/web/` contains the frontend; `packages/ui/` contains shared components
- `Add or update tests for changed behavior; start with pytest tests/api/test_users.py -q`
- `Use logs, repro scripts, and the project debugger first; after 2–3 failed attempts, ask before using online research`
- `Use Tavily for online research when external lookup is approved`
- `Use objdump for ELF inspection before switching to heavier tooling`
- `Ignore the known warning in apps/web/src/App.tsx until the user reopens it`
- `go vet ./... # one pre-existing unsafe.Pointer warning in injection/ is accepted`
- `Regenerate the resource blob after changes in evasion/ or injection/: bash scripts/gen.sh`
- `Write code comments in English; keep them technical and brief; explain intent or edge cases, not obvious statements`

### Documentation masquerading as instruction (remove)

| Remove | Why |
|--------|-----|
| Full interface type definitions | Documents what exists; belongs in README |
| BuildConfig struct field list | Belongs in code comments or README |
| Internal pipeline step-by-step | Only the steps the agent must perform belong here |
| Technique behavioral deep-dives | Reference material, not agent instruction |
| Named pattern descriptions with ASCII diagrams | README material |

### Hard constraint table (add)

| Forbidden | Use instead |
|-----------|-------------|
| `crypto/rand` | `math/rand` seeded via `time.Now().UnixNano()` |
| XOR `^=` | MBA: `(a+b)-2*(a&b)` for obfuscation |
| `math/rand/v2` | `math/rand` v1 for TinyGo compatibility |

## When to split

Create nested `AGENTS.md` files when:

- frontend and backend have different commands
- infrastructure has different risk boundaries
- a package needs different style rules
- the root file starts reading like a manual instead of an index

## Sources

- GitHub blog, Nov 2025: command-first sections, concrete examples, six core areas, and explicit boundaries from analysis of 2,500+ repositories
- agents.md official FAQ and examples: open format, nested precedence, and practical root-file guidance
