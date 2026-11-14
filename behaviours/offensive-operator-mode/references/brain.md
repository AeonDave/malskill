# Operational Brain

Load when an investigation or development task needs organized state across steps, artifacts, branches, or sessions. Keep enough context to resume the right work without reconstructing the conversation or repeating invalid experiments.

## Start from the task

Find the task's existing notes, index, and artifact locations. Read the current checkpoint and follow only the pointers relevant to the next action. Reuse established names, links, and structure.

If no record exists and the work needs one, start `brain.md` in the task workspace. Use a specified Obsidian vault when available; plain Markdown with filesystem tools is sufficient. If the workspace is not writable, retain the checkpoint in the conversation and identify the missing destination only when persistent storage is needed. Do not install a plugin or create an unrelated vault to begin work.

These are task records. For a user profile, cross-project memory, or a managed memory store, load `memory-hygiene` and follow that store's write contract. A read-only question about notes calls for retrieval, not maintenance.

## Organize only as the work grows

Start with one note. Split a topic when it needs independent retrieval or its detail obscures the current state. Keep one entry note linking the active entities, evidence, decisions, and open work; an index should navigate, not copy every finding.

Use stable identities: host identity with address history, sample identity with hash, repository with revision, or test with relevant build and configuration. An IP address, filename, function offset, or display name alone may refer to different objects over time. Avoid merging records on that basis alone.

Record a fact or decision in one canonical place. Link relationships with their meaning, such as a service running on a host, a sample producing an artifact, a test supporting a finding, or a decision governing a component. Mark an inferred relationship as inferred. Add links that help retrieval or the next decision; no fixed folder tree, tag taxonomy, or link quota is required.

## Keep a usable checkpoint

At the entry point, retain:

- **Objective and completion signal.** Include the active operating mode when needed for resumption.
- **Current state.** Relevant entities, versions, access or analysis position, and pointers to established findings.
- **Open work.** Unresolved questions, active hypothesis, blockers, and the next useful action with its expected observation.

Update this checkpoint after consequential changes and before interruption or handoff. Keep completed detail in its canonical record. Do not rewrite it for every command or reproduce it in every response.

## Record what changes the work

Update existing records in place. Preserve relevant source pointers, experiment identifiers, and decision rationale; mark obsolete conclusions as superseded with the reason. Before replacing or condensing a passage, check what evidence or context the replacement would lose.

Attach a resolvable evidence pointer to each consequential finding or experiment when recording it, including newly supplied results. A short pattern is `Claim/status — [source](relative/path), locator and conditions`. Naming a tool or writing "the trace shows" is not a source pointer.

Use only the other fields needed for the item; these are recording contracts, not mandatory templates.

| Item | Preserve |
|---|---|
| Finding | Precise claim; observed, derived, hypothesized, or unknown; source locator; relevant identity/version/conditions; unresolved conflicting evidence |
| Experiment or useful failed attempt | Question or hypothesis; reproducible input/command and setup; expected versus actual result; evidence pointer; interpretation; what would justify a retry |
| Technical decision | Chosen option; relevant alternatives and reason; affected component; verification or unresolved tradeoff; condition that would reopen it |
| Artifact | Original location; identity/revision/hash when needed to distinguish it; acquisition or event time and timezone when relevant; relation to the finding or experiment |

Keep raw captures, logs, samples, and dumps in their artifact locations. Notes point to the decisive file, offset, line, event, query, or test result instead of embedding entire outputs. Preserve originals; a summary is a derived record. Retain decisive errors exactly, including enough context to distinguish a tool failure from a negative finding. Refer to credential or sensitive-evidence storage without copying secret values into navigation or summaries.

## Adapt the record to the work

| Work | Context that prevents lost progress |
|---|---|
| CTF / fullpwn / network assessment | Hosts and address history, services, access and privilege actually observed, credential references with tested applicability, routes and dependencies between hosts, objectives and proof artifacts. Distinguish historical access from a currently verified session. |
| Reverse engineering / malware analysis | Sample and build identity, architecture, address basis, function names or offsets, inferred semantics, relevant tool/database state, inputs and observations. Preserve what was already checked and which interpretation remains tentative. |
| Patchdiff / vulnerability research | Exact old/new revisions, mapping of changed functions, behavioral delta, security hypothesis, unresolved preconditions or reachability, old/new test results and controls. A changed check alone does not establish exploitability. |
| Security development, including malware / EDR tooling | Component and revision, design choices and rationale, interfaces or invariants affected, build/test context, regressions, and unresolved tradeoffs. Reuse existing ADRs and issues instead of creating parallel decisions. |
| Defense / purple-team validation | Assets, trust relationships, controls, telemetry sources, collection windows, and visibility gaps; expected versus observed test effects. Track configured controls, received telemetry, and demonstrated detection separately. |
| Forensics / incident analysis | Evidence identity and acquisition context, timeline with timezone or clock uncertainty, observations versus attribution, transformations and output pointers, and gaps that affect the reconstruction. |

For another task, retain the identities, relationships, evidence, and decisions that determine its next action. Do not manufacture unused domain sections.

## Resume, correct, and consolidate

1. Read the entry checkpoint, then the specific record needed. Avoid reloading the whole archive.
2. Check whether its target, build, environment, or time window still matches. Revalidate volatile facts when the next action relies on them; do not rerun every settled test.
3. Consult prior attempts before choosing a test. Repeat only with a meaningful changed condition or justified transient retry; record the difference. An invalid harness result does not rule out the target hypothesis.
4. Keep contradictory evidence visible until resolved. Mark a superseded conclusion and link the correcting evidence; distinguish an earlier error from a later state change. Update affected current summaries without rewriting historical results as though they never happened.
5. Merge duplicate summaries only when they describe the same entity and conditions. Preserve unique evidence and repair incoming links. Ingesting the same source again should update its record only when content, identity, or interpretation changed.
6. Compare the saved note with its prior contents and the new evidence: retain useful rationale and history, resolve its source pointers, and check that current claims match their evidence. Ensure a fresh reader can identify the current state, what was already attempted, and the next action. Report the updated entry point when useful; do not claim to have audited notes you did not inspect.

## Markdown and Obsidian

Use ordinary relative Markdown links for a new portable record. In an existing Obsidian vault, follow its link conventions; use paths that distinguish duplicate note names. Do not depend on graph views, Dataview, or another plugin to recover essential state. See [Obsidian internal links](https://obsidian.md/help/links) when choosing vault-specific link syntax.

Keep properties optional and consistent with the existing vault. Preserve established property types; quote internal links in YAML. Consult [Obsidian properties](https://obsidian.md/help/properties) only when editing those fields.

After a filesystem rename or move, check affected links explicitly. Obsidian's link updates depend on its settings and operations; moving files outside it is not proof that references were repaired.
