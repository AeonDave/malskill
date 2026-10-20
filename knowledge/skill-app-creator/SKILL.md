---
name: skill-app-creator
description: "Create or evolve skill-apps: Agent Skills with executable workflows and consistent deliverables. Use when turning a recurring task into a skill with deterministic helpers, output contracts, runtime diagnostics, or resumable sessions."
license: MIT
metadata:
  author: AeonDave
  version: "1.0"
---

# Skill App Creator

Build a skill that operates like a small application: the agent handles judgment, helpers handle repeatable mechanics, and users receive predictable deliverables. Keep output structure stable; let conclusions, uncertainty, and supported precision vary with the evidence. “Skill-app” is a design convention within the Agent Skills format, not a separate host capability.

Use [skill-creator](../skill-creator/SKILL.md) for skill structure, routing, scaffolding, and repository validation. This skill adds application contracts and runtime design. In malskill, build support apps only when they improve an active security workflow.

## Establish the application contract

Inspect existing skills and actual helpers before designing new components. For an existing app, trace one input through stored state to delivery; preserve working commands and data unless the requested change requires migration.

Complete [assets/app-contract.md](assets/app-contract.md) when designing an app or changing its input, output, or lifecycle contract. Keep the filled contract in the working project; publish only the rules, schemas, and templates the resulting skill needs.

Decide before implementation:

- The recurring user action, accepted inputs, and smallest useful deliverable.
- Exact output filenames, fields or sections, units, ordering, and unknown values. A user-requested format overrides defaults without erasing verification status.
- What the agent decides, what scripts calculate or validate, and which evidence supports success.
- Required dependencies and optional capabilities; offline behavior, external uploads, configuration precedence, and cost limits.
- How invalid inputs, partial results, interruptions, and unresolved tasks appear. Never require an invented value just to satisfy a success schema.

Proceed with reasonable defaults from the request. Ask only for missing facts that change the contract or authorization; do not add approval stops to authorized work.

## Choose the smallest runtime

| Need | Include |
|---|---|
| One bounded transformation | A task helper and output template or schema; no persistent session machinery. |
| Multiple steps, evidence, or interruption recovery | A run directory, authoritative state, and lifecycle commands. |
| Dependencies that can fail independently | A doctor with capability-specific checks and actionable fixes. |
| User must inspect progress or compare results visually | An optional viewer, preview, or dashboard derived from stored state. |
| A host integration provides essential interaction | Its adapter and a fallback or explicit requirement. |

Load [references/runtime.md](references/runtime.md) when implementing helpers, doctor checks, sessions, integrations, or a UI. Use only sections for selected components. A CLI, document, spreadsheet, or directory of artifacts can be the complete interface.

## Build one complete path first

1. Implement one representative input through delivery, including its failure outcome. Reuse established libraries and helpers; avoid a generic framework before a second concrete need.
2. Put repeatable parsing, calculations, validation, and rendering in code. Let the agent select routes and interpret ambiguous evidence. A template constrains presentation; it does not prove content.
3. Give ordinary use one obvious entrypoint. Keep specialist operations available without requiring agents to orchestrate every internal helper. Read actual `--help` before documenting commands.
4. Validate the canonical result, then render human-facing deliverables from it. For document-only apps, validate declared sections and artifact requirements rather than forcing JSON.
5. Check artifacts from their final location. Deliver usable file links and state what is partial, unknown, or blocked. Mark success only after required checks and delivery succeed.

Default to inexpensive, selective work. Escalate when another feasible operation can change the requested result; show progress at meaningful transitions. Honor explicit time, cost, stop, and format instructions. Record skipped checks without upgrading the result to verified.

## Keep the resulting skill operable

The generated `SKILL.md` tells an agent how to start ordinary work, locate output, recover failure, and know when it is done. Link specialized depth with explicit “load when” conditions. Keep schema and command semantics canonical; derive templates, reports, and UI from the same contract.

Resolve the skill directory through the actual host or an explicit argument. Separate installed resources from run outputs and caches. Do not assume a vendor variable, current directory, installed sibling skill, browser, GPU, or network service unless declared as a requirement.

Use a doctor when meaningful runtime checks exist; a prose-only creator needs no ceremonial doctor. Add scripts and UI only for selected capabilities. Keep repository maintenance outside generated operational helpers.

## Verify and deliver

Load [references/acceptance.md](references/acceptance.md) when defining acceptance cases, testing an app, or changing its runtime contract. Test delivery and applicable failures, not just imports or schema syntax.

Run skill-creator's structural and hygiene checks for each changed skill. They do not establish runtime correctness. Report separately: structural validation, actual end-to-end runs, failure coverage, and untested hosts/services. Do not claim repeatable agent behavior from template review alone.

Finish with the skill location, ordinary-use command, components delivered, verification performed, and material limitations. Package or install only when requested.

## Design sources

- [Agent Skills specification](https://agentskills.io/specification): use the standard layout and load resources on demand.
- [Building effective agents](https://www.anthropic.com/engineering/building-effective-agents): start with simple composable workflows; give tools clear inputs and feedback.
