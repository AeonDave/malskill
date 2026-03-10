# AGENTS.md

## Commands
- Install dependencies: `<real command>`
- Run the dev workflow: `<real command>`
- Run the fast validation for changed code: `<real command>`
- Run the full test suite: `<real command>`

## Active user decisions
- Use `<tool / workflow choice>` when relevant.
- Ask before changing these decisions; they are active preferences, not permanent rules.

## Testing
- Add or update tests for changed behavior.
- Prefer the smallest relevant test command first.
- Do not finish with failing tests, lint, or type checks unless the user explicitly accepts it.

## Debugging
- Use available local tools first: tests, logs, debuggers, repro scripts, type checks, profilers, or existing diagnostics.
- If local evidence is still insufficient after 2–3 failed iterations, ask before using online research.
- Create small temporary debug helpers only when they materially improve signal, then remove or formalize them as appropriate.

## Project structure
- Keep this section at folder level only; list only directories and very high-signal paths.
- `<path>/` — `<what lives here>`
- `<path>/` — `<what lives here>`
- `<path>/` — `<what lives here>`

## Accepted diagnostics
- `<path or scope>` — `<warning / lint / UI issue>` — `<ignored / deferred / out of scope until user reopens>`

## Conventions
- `<non-obvious style or architecture rule>`
- Code comments should be in English, technical, and brief; explain intent, invariants, or non-obvious behavior.
- `<library / framework preference>`
- `<naming / file placement rule>`
- Update `AGENTS.md` after important changes to commands, structure, conventions, or boundaries.

## Boundaries
- Ask first before: `<schema / dependency / deploy / destructive change>`
- Never: `<secrets / vendor dirs / generated output / production config>`

## PR instructions
- `<title format or required checks, only if real>`
