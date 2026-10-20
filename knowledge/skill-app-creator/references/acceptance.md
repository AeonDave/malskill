# Acceptance and failure cases

Select cases for actual components. Set expected outcomes before running. Use small representative fixtures, temporary output directories, and mocked outages for controlled failures; mocks do not prove live-provider success.

## Exercise delivery

Run the documented command from a fresh working directory with declared dependencies. Inspect the canonical result, deliverables, checks, exit status, and links. Repeat input to check stable structure and detect duplicate/stale output. Normalize declared volatile fields only.

| Case | Required observation |
|---|---|
| Ordinary input | Output opens and passes domain checks; final status agrees. |
| Missing, wrong, or corrupt input | Useful error before costly work; original preserved; no success artifact published. |
| Insufficient evidence/empty result | Partial/unresolved outcome with unknowns and next action; no fabricated defaults. |
| Missing required dependency | Doctor/entrypoint names the blocked capability and remedy; nonzero failure. |
| Missing optional dependency | Fallback or explicitly reduced result; unrelated capabilities still work. |
| Spaces/Unicode; different caller directory | Correct resource resolution; output inside declared location. |
| Timeout, quota, malformed response | Bounded execution; failed retrieval distinguished from an empty result. |
| Interruption/resume | Valid work reused; incomplete output not promoted; no second live writer. |
| Changed input/configuration | Stale dependent results invalidated; new provenance recorded. |
| Retry/repeated finalization | No duplicate records/sections or repeated external writes. |
| User stop/skipped verification | Limit honored; reason and actual coverage retained; no verified-success upgrade. |
| Failed write/render/rename | Prior valid artifacts preserved; recoverable status; no false delivery success. |
| UI/export, when included | Displays stored terminal result; links survive final placement/shutdown. |

Execute representative paths on claimed platforms or name untested ones. Separate synthetic tests, transport reachability, authenticated known-answer probes, and real service task success.

## Exercise agent use

Try a realistic natural request in a clean context. Check that the agent finds the entrypoint, loads relevant references only, honors limits, uses emitted paths, and verifies delivery. Implementation tests do not test activation or orchestration.

Test app creation, evolution of an existing app, and a near miss needing only an ordinary prose skill. For substantial workflow changes, compare with previous/no-skill behavior using the same inputs and preset expectations. Use skill-creator's behavior-evaluation guidance; do not claim it ran when only reviewing instructions.

## Keep checks focused

Place operational-helper regression tests according to the target repository. In malskill, maintenance-tool tests belong in root `tests/`; task-specific app tests can stay with the skill. Test user-visible failures and promised contracts, not constants or wording.

Acceptance requires applicable delivery/failure cases to behave as declared, evidence for claimed support, valid skill structure, and explicit limitations. Record command, fixture, observation, and what each check proves in the working project or handoff; keep evaluation narratives out of shipped skill instructions.
