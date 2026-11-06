# Offensive Evidence Gates

Use this reference when converting tool output or research notes into claims.

## Vulnerability discovery

Match the conclusion to what was established:

- A reproduction against the scoped service supports the observed mechanism and impact under the recorded conditions.
- A verified source/sink path with reachable input and relevant configuration can establish a code defect; deployed exploitability also depends on the target's actual build, configuration, and controls.
- Scanner agreement alone does not confirm a vulnerability. Inspect the underlying evidence and verify the mechanism and preconditions for the claim through applicable source review or authorized testing.

Downgrade when:

- only banner/version matching exists
- exploit preconditions are unknown
- WAF/proxy behavior may be synthetic
- the result depends on a lab-only configuration

For automated static findings, apply [OWASP's SAST limitations](https://devguide.owasp.org/en/05-implementation/05-static-analysis/#limitations): review context and account for false positives and coverage gaps.

## Exploit development

For a demonstrated exploit effect, preserve:

- evidence of the claimed crash, primitive, leak, auth bypass, or code execution
- triggering input, initial state, environment, target build, and offsets where needed to reproduce that effect
- negative control when false positives are plausible

Name the demonstrated effect: a crash is not code execution, and one successful run does not establish exploit reliability.

Narrow exploitability, portability, or reliability claims when:

- exploit only works under debugger without explanation
- ASLR/PIE/canary state is assumed, not measured
- network timing or race behavior is not stable

## Credential and secret validation

Separate presence, validity, and privileges:

- An inspected artifact can establish that it contains secret material; a regex match alone establishes only a candidate.
- Current credential validity requires an authorized service-specific check, preferably read-only, with the service and timestamp recorded. Distinguish accepted, rejected, expired, and inconclusive according to the response semantics.
- Successful authentication does not establish unchecked permissions or access to other services.

Rate limits, transport errors, or ambiguous denials do not establish invalid credentials. Report validity as unknown when testing is unavailable; do not expand scope to resolve it.

## Malware and reverse engineering

Match the claim to the analysis:

- Tie static conclusions to inspected code/data locations and explicit execution conditions; strings alone do not establish a capability or reachable path.
- Claims of observed execution require a trace or experiment from the relevant sample and environment. Code can establish conditional behavior without proving that it ran on a target.
- Preserve sample hash and relevant tooling/version notes for repeatability.

Downgrade when:

- sandbox output is incomplete or anti-analysis may have altered behavior
- emulated or sandbox behavior is generalized to an unexamined target

## Forensics and OSINT

Confirmed requires:

- source URL, acquisition time, hash/screenshot/archive when relevant
- chain of custody for local artifacts
- evidence linking the specific identity or actor to the artifact/activity; independent corroboration when the linkage is ambiguous

Downgrade when:

- provenance is unclear or mutable content was not captured
- identity linkage is based on a single weak signal
- timestamps/time zones are ambiguous

## LLM and agent output

Confirmed requires:

- cited material inspected in context and supporting the claimed conclusion; verify exact text/bytes for literal quotes, hashes, or byte-level claims, and meaning for paraphrases
- for delegated findings: inspect the relevant diff/artifacts and check results; use `verification-before-completion` for completion claims

Downgrade when:

- claim rests only on a summary without checking the underlying material
- cited file/line/CVE/function cannot be located or does not support the claim
- a screenshot omits the context needed for a text/log claim (inspect the original when available)
- model output conflicts with applicable primary evidence

## Cleanup and remediation

Confirmed requires:

- post-action verification from the target state, not just a successful command exit
- logs/artifacts showing removal, patch application, or control effectiveness
- observed restoration when claiming a rollback succeeded; rollback notes alone do not establish it

Downgrade when:

- verification only checked the local tool state
- unchecked persistence locations, failure paths, or target instances are included in a broad cleanup claim

## Engagement summary

Before a report spanning workers or targets, reconcile material claims about findings, coverage, current access, and required cleanup. For each, identify the evidence, relevant job or observer, target/build, observation time, and what was actually checked. Distinguish inspected support from an unchecked worker report or missing evidence; do not promote every worker's DONE status into a verified engagement outcome.

Claims that all actions stayed within the agreed boundaries require adequate action records. Incomplete logs leave a gap; absence of a recorded exception is not proof that none occurred. Carry unresolved failures with their original evidence and supported cause, including unknown causes. State outstanding jobs and cleanup obligations rather than presenting partial closure as complete. Inspect existing artifacts when sufficient; a fresh intrusive test is not required merely to prepare the report.
