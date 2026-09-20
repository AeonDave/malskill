---
name: cve-search
description: "Research and document CVEs for defensive vulnerability management using authoritative CNA, vendor, NVD, CVE.org, OSV, and CISA KEV records. Use when building a current CVE inventory, affected-version and remediation matrix, or evidence-backed vulnerability digest."
license: MIT
metadata:
  author: malskill
  version: "1.1"
compatibility: "Requires web access for source discovery; shell access is optional for local artifact checks."
---

# CVE Search

Build a traceable, defensive CVE inventory. Record what authoritative sources say; do not turn this workflow into exploit development or exploit validation.

## Inputs

- `vuln_type` — vulnerability class or search theme
- `time_range` — optional year, date range, or freshness limit
- `dest_file` — optional workspace path for the Markdown output
- `product` or `vendor` — optional product and supplier constraints

## Workflow

1. Bound the request: normalize the vulnerability class, product, vendor, platform, and date constraints. If no destination is supplied, derive a clear filename.
2. Enumerate candidates from CVE.org/CNA records and vendor advisories. Cross-check NVD, OSV/GHSA, and the CISA KEV catalog where applicable. Prefer the current record and vendor source when enrichment differs.
3. For each candidate, verify the CVE state and aliases, affected product/version ranges, fixed versions, configuration conditions, vendor remediation, publication/update dates, and authoritative references. Record whether the CVE is reserved, published, rejected, or disputed when the source exposes that state.
4. Capture severity separately from risk. Preserve the CVSS version, vector, score, and source; do not equate a severity score with local risk. Treat KEV membership as evidence of CISA-listed exploitation priority, not proof of ongoing exploitation or complete coverage.
5. Write one evidence-backed entry per CVE:

```md
- **CVE-YYYY-NNNN:** short title
  - **State:** published | reserved | rejected | disputed | unknown
  - **Aliases:** CVE aliases or `none found`
  - **Affected:** product, version/configuration range, and source
  - **Fixed:** vendor-fixed version or remediation, when published
  - **Severity:** CVSS version/vector/score, or `not published`
  - **KEV:** catalog date and required action, or `not listed`
  - **References:** CNA/vendor/NVD/CVE.org/OSV URLs
  - **Notes:** remaining uncertainty and verification date
```

6. Review every entry against the requested class and time range. Keep unknowns explicit, cite the source for every version or remediation claim, and record the retrieval date for changing records.

## Precision rules

- Use current CNA or vendor records for product, version, configuration, and remediation claims; do not invent affected ranges.
- Distinguish CVE state and alias identity from vulnerability severity and from operational risk.
- KEV is a useful prioritization signal, not evidence that exploitation is currently active everywhere or that the catalog is complete.
- HTTP success, a reachable reference, or a search-result hit does not prove correctness, applicability, exploitability, or remediation.
- Do not search for, improve, run, or validate exploit payloads or weaponized proof-of-concept automation. If a public reference is relevant to defensive triage, record its authoritative URL and describe it only as a reference.
