---
name: dependency-discipline
description: "Evaluate, pin, and audit dependencies at adoption and upgrade time — provenance, maintenance signal, install-script surface, CVE history, hash pinning. Use when adding or upgrading any dependency, wiring CI installs, or after a supply-chain incident in the ecosystem."
license: MIT
compatibility: "Agent workflow guidance; language-agnostic (pip/npm/cargo/go/actions)."
metadata:
  author: AeonDave
  version: "1.0"
---

# Dependency Discipline

Every dependency is untrusted code that runs in your build and your users' hosts.

Release pipelines and maintainer accounts get compromised; a correctly-signed new version can still ship malicious code — signature checks and CVE databases do not catch it. Assume the next occurrence: bus-factor limits, hash-pinned installs, a cool-down on fresh releases, and re-verification of anything installed in a suspect window are the controls below.

## Adopting a dependency — the evaluation gate

Match the depth to the risk: a widely-used, pinned, already-in-tree library does not need this; a new, unknown, unpinned, or install-scripted dependency earns the full gate. Before adding (not after), check — in order of cost:

1. **Necessity**: can the standard library or an existing dependency do it? (One line in `software-guidelines` is a rule; this is the expanded gate.) A 3-function helper is not worth a supply-chain surface.
2. **Provenance and bus factor**: who maintains it, how many, recent commit activity, does the repo match the published package (source vs built artifact)? A single-maintainer package that changes hands (xz: new co-maintainer) is the classic pre-backdoor signal.
3. **Install-time surface**: does the package run code at install (setup.py hooks, postinstall scripts, Makefile downloads)? `pip install --no-deps` inspection or `npm install --ignore-scripts` first; review what executes.
4. **Scorecard checks** ([OpenSSF Scorecard](https://securityscorecards.dev/)): minimum bar = `Pinned-Dependencies`, `Token-Permissions`, `Dangerous-Workflow`, `Maintained`, `Code-Review`. Check via [deps.dev](https://deps.dev/) or the Scorecard API without cloning.
5. **CVE history and response**: past vulns happen; the signal is *how they were handled* (advisories, fast patches, honest disclosures). Silent major bumps after a disclosure are worse.
6. **License**: compatibility with your distribution (most offensive tooling ships unlicensed-privately, but a leaked tool with GPL deps is an exposure).

## Pinning and upgrades

- **Pin exact versions** in CI and Dockerfiles; pin GitHub Actions to **full commit SHAs** (tags are mutable — a moved tag is a silent code swap).
- Combine pinning with update tooling (Renovate/Dependabot) so pinned does not mean stale — the update PR becomes the review point for every upgrade.
- **Hash-verify** what you install for anything security-relevant: `pip install --require-hashes`, `cargo` uses `Cargo.lock` + `--locked`, npm has `--ignore-scripts` + integrity fields. After any ecosystem compromise, re-verify versions already on disk: poisoned releases are typically pulled in by unpinned consumers, not by the pinning users.
- Distrust new releases in the hours after publication: install the previous pin until the release is diffed or attested (SLSA provenance where available).

## Auditing what you already have

- `trivy fs`/`osv-scanner` (this repo) for known-CVE sweep on every dependency bump, not just at release.
- Know your install scripts: `npm pkg get scripts` (postinstall/preinstall), `setup.py`/`pyproject` build hooks — the entry points that execute before your code does.
- Review transitive dependencies on adoption (one level deep minimum): the small package you chose pulls a large unmaintained graph.

## Incident response

When an ecosystem incident lands (poisoned release, hijacked maintainer):
1. Check installed versions against the affected range; assume compromised if in range.
2. Rotate every secret the environment could reach — treat the host as exposed, not just the package.
3. Re-pin to the last verified-good version *by hash*, then upgrade to the attested fix when published.
4. Record the incident rule in the repo's docs if it changes the pinning policy.

## Related

- `software-guidelines` — the adoption one-liner this expands; scoped-change workflow.
- `litellm` (ai/) — worked example of the poisoned-release pattern in this repo's own stack.
- `model-scanning` (ai/) — the model-artifact flavor of the same problem (pickle payloads).
- `trivy`, `osv-scanner`, `gitleaks` (offensive-tools/) — the scanning half of the lifecycle.
- `secure-tooling-implementation` — the tool-code side of not shipping the vulnerability.
