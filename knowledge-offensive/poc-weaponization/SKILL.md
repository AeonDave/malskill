---
name: poc-weaponization
description: "Review an existing public proof-of-concept artifact for provenance, suspicious behavior, dependency risk, and safe assessment use. Use when triaging a PoC referenced by a CVE or received during an authorized security assessment."
license: MIT
metadata:
  author: malskill
  version: "1.1"
compatibility: "Static review needs local file access; artifact and source verification may need web access."
---

# PoC Artifact Review

Review a PoC as untrusted code and produce a concrete assessment-preparation decision. For CVE identity, affected ranges, and asset applicability, use [CVE inventory and triage](../cve-search/SKILL.md).

## Review workflow

1. Identify the exact artifact: canonical source URL, repository and immutable revision or release, file path, retrieval date, claimed CVE/product/version, and SHA-256 digest. If a trusted publisher provides a signature, verify it against a separately trusted key. A matching digest identifies bytes; a signature or provenance statement supports origin/integrity claims. Neither establishes that the code is safe. See [SLSA artifact verification](https://slsa.dev/spec/v1.2/verifying-artifacts) and [NIST SSDF](https://csrc.nist.gov/pubs/sp/800/218/final).
2. Read source, build files, manifests, lockfiles, helper scripts, and workflow configuration before running anything. Check dependency names, versions, sources, lifecycle/build hooks, subprocesses, filesystem access, and network destinations. Do not install dependencies or invoke setup/build hooks from the public artifact. Stop before execution if the code path needed for the check is opaque, downloads unreviewed code, requires credentials, or has unbounded or unexplained side effects. Record missing lockfiles, mutable references, hidden downloads, or dependencies that cannot be independently identified.
3. Trace behavior from entry point through subprocess, filesystem, network, and privilege-sensitive operations. Load [PoC review indicators](references/backdoor-patterns.md) for the focused checklist. Distinguish observed code paths from suspicious names or patterns; static review cannot prove benign behavior, especially for opaque binaries, dynamic loading, and behavior dependent on runtime inputs.
4. Compare the artifact's claimed target and conditions with the authoritative vendor/CNA record and local asset evidence. A public PoC's existence or apparent success message does not establish that the assessed product is vulnerable.
5. Decide whether a check is useful and bounded. A reviewed, non-destructive diagnostic path may be adapted for portability, bytes handling, library contracts, timeouts, or bounded input validation. Keep the original artifact unchanged; record the adapted file's separate digest and exact changes. Do not construct exploit payloads or add command execution, callbacks, data collection, persistence, or unrelated network access. When adapting would cross these limits, use a separate harmless fixture or vendor-supported check instead.
6. Execute only the reviewed non-destructive check or separate fixture in a disposable isolated environment with synthetic data, no credentials, no production connectivity, and no route to unrelated hosts. Before running it, record expected observations, a negative/control case, input and time bounds, side effects to monitor, stop conditions, and cleanup. Do not run unreviewed installers, hooks, opaque or unsafe code paths. Stop immediately if observed behavior differs from the declared check, exceeds bounds, or touches undeclared resources.
7. Report one disposition: `reviewed-static`, `check-confirmed`, `suspicious`, or `insufficient-evidence`. Include expected versus observed results and interpretation limits. A negative result, timeout, unreachable service, or blocked request does not prove that the software is unaffected or the artifact is safe; it may reflect a control, environment mismatch, or a test that did not reach the relevant condition.

## Review record

```md
- **Artifact:** source/revision/path, retrieval date, SHA-256
- **Claim:** CVE, product/version, and claimed preconditions
- **Origin/integrity:** signature or provenance verification and trust basis; or unavailable
- **Inspected:** source files, manifests, lockfiles, build/runtime paths
- **Observed:** file, process, network, privilege, and data handling behavior
- **Adaptation:** separate path and digest; exact portability/diagnostic changes, if used
- **Check:** expected observation and control; observed result; stop/cleanup outcome
- **Disposition:** reviewed-static | check-confirmed | suspicious | insufficient-evidence
- **Interpretation:** what the result supports and what it does not establish
- **Limitations:** binaries, dynamic behavior, missing dependencies, or untested paths
```

## Limits

- A hash proves byte identity only when compared with a trusted expected digest. A valid signature binds an artifact to a signing key; trust in the key and the signer remains a separate question.
- Dependency metadata, SBOMs, signatures, sandbox runs, and static scans each cover different evidence. None alone proves all code paths benign or predicts behavior in every runtime environment.
- Preserve suspicious artifacts and notes for analysis; do not publish or redistribute them as executable assessment tooling.
