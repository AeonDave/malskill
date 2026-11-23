# Recon Operations Playbook

Operational add-on for `osint-technique`: confidence upgrades, detectability-aware probing, time budgeting, and asset-graph discipline.

---

## 1) Confidence Levels (Operational)

Use three levels on every claim:

- **TENTATIVE**: plausible from indirect evidence, not directly verified.
- **FIRM**: directly observed once, not yet corroborated.
- **CONFIRMED**: independently corroborated or directly validated.

Attribution floor:

- Use **rule-of-three** for weak signals: at least 3 independent weak signals, or 1 strong + 1 weak.
- Never claim ownership/control from single-source coincidence.

Upgrade workflow examples:

- `subdomain`: TENTATIVE (single passive source) -> FIRM (DNS resolves) -> CONFIRMED (serves + cert/banner ties to org).
- `email`: TENTATIVE (pattern inference) -> FIRM (listed in independent source) -> CONFIRMED (passive validator corroboration).
- `secret`: TENTATIVE (regex hit) -> CONFIRMED only after read-only validator succeeds.

---

## 2) Detectability Tags and Back-Off Ladder

Tag each operation before running it:

- **LOW**: passive datasets/APIs, CT logs, historical archives, metadata fetches.
- **MEDIUM**: targeted read-only probes to live endpoints (auth realm checks, limited enum).
- **HIGH**: scanning/fuzzing/high-request volume or protocol enum likely to generate alerts.

Back-off ladder when detection signs appear (`429`, captcha, sudden `403`, WAF page, banner drift):

1. Reduce concurrency, add jitter.
2. Stop noisy path, pivot to passive sources.
3. Record the response and observation time. A block is not evidence that the underlying resource is absent.
4. For `429`, honor `Retry-After` when supplied. A change of IP, identity, or time window does not grant access; if access remains denied, report the coverage gap.

---

## 3) Time Budget Profiles

Use engagement profile to avoid over-collection:

- **1h rapid**: passive seed + high-signal leaks + top-risk summary.
- **4h focused**: rapid + identity fabric + top external exposures.
- **1d standard**: full staged recon with scoring and remediation notes.
- **1w deep**: standard + deep archival/JS/package/tenant correlation.

Abort/pivot conditions:

- scope mismatch found;
- low signal after seed/expansion;
- repeated detection triggers from medium/high operations.

---

## 4) Asset-Graph Discipline (Minimum Set)

Store discoveries as typed nodes + typed edges, not free text.

Recommended node types:

- `domain`, `subdomain`, `ip`, `asn`
- `webapp`, `api_endpoint`, `certificate`
- `email`, `person`, `org`
- `repo`, `secret`, `bucket`

Recommended edge types:

- `resolves_to` (`subdomain -> ip`)
- `announced_by` (`ip -> asn`)
- `hosts` (`domain -> webapp`)
- `uses_cert` (`webapp -> certificate`)
- `mentions` (`repo -> secret`)
- `belongs_to` (`email/person -> org`)

Why this matters:

- prevents duplicate findings,
- makes confidence upgrades auditable,
- speeds pivoting (`secret -> repo -> org -> exposed endpoint`).

---

## 5) Reporting Guardrails

- Include confidence + detectability tag on each finding.
- Distinguish clearly: **correlation** vs **control**.
- For sensitive claims, include exact corroboration path (source A + source B + verification step).
