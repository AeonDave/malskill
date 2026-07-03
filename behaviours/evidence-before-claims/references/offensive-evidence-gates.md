# Offensive Evidence Gates

Use this reference when converting tool output or research notes into claims.

## Vulnerability discovery

Confirmed requires at least one of:

- manual reproduction against the scoped service
- source/sink path with reachable input and vulnerable configuration
- scanner finding plus manual replay or second independent tool

Downgrade when:

- only banner/version matching exists
- exploit preconditions are unknown
- WAF/proxy behavior may be synthetic
- the result depends on a lab-only configuration

## Exploit development

Confirmed requires:

- controlled crash, primitive, leak, auth bypass, or code execution reproduced from a clean run
- exact input, offsets, environment, and target build captured
- negative control when false positives are plausible

Downgrade when:

- exploit only works under debugger without explanation
- ASLR/PIE/canary state is assumed, not measured
- network timing or race behavior is not stable

## Credential and secret validation

Confirmed requires:

- authorized, read-only authentication check where possible
- target/service identifier and timestamp/context
- clear distinction between valid, invalid, expired, and unknown

Downgrade when:

- only regex pattern match exists
- API returned rate-limit or network error
- account scope/privileges were not checked

## Malware and reverse engineering

Confirmed requires:

- static evidence tied to function/address/string/resource and behavior hypothesis
- dynamic trace or emulation when claiming runtime behavior
- sample hash and tooling/version notes for repeatability

Downgrade when:

- strings imply capability but no code path is found
- sandbox output is incomplete or anti-analysis may have altered behavior

## Forensics and OSINT

Confirmed requires:

- source URL, acquisition time, hash/screenshot/archive when relevant
- chain of custody for local artifacts
- correlation across independent sources for identity or attribution claims

Downgrade when:

- evidence is user-generated and mutable
- identity linkage is based on a single weak signal
- timestamps/time zones are ambiguous

## LLM and agent output

Confirmed requires:

- primary artifact re-checked in the current context (file read, command rerun, request replayed) — the model/subagent report alone is not evidence
- exact quote/path/offset the model cited, verified to exist and match
- for delegated work: inspection of diff/artifacts, not the worker's summary

Downgrade when:

- claim rests on paraphrased tool output or a subagent's conclusion
- cited file/line/CVE/function was not opened and matched byte-for-byte
- screenshot is the only artifact for a text/log claim (replay the source)
- model output contradicts a fresh command run

## Cleanup and remediation

Confirmed requires:

- post-action verification from the target state, not just a successful command exit
- logs/artifacts showing removal, patch application, or control effectiveness
- rollback notes if the action changed state

Downgrade when:

- verification only checked the local tool state
- failure paths were not tested
