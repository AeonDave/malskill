# Source Selection by Claim

Load when deciding which sources can establish a claim. Prefer the record closest to the claim's origin; use aggregators and social posts to find leads, not as sole support for consequential conclusions.

| Claim | Preferred evidence | Check |
|---|---|---|
| Affected product/version and conditions | Vendor security advisory, release notes, fixed-version record, or patch | Product edition, build range, configuration, authentication and exposure prerequisites |
| CVE identity and public record | CVE Program record and NVD CVE API/record | CNA attribution, record state, dates, affected configurations, and missing/changed enrichment |
| Known exploitation | CISA KEV entry for catalog inclusion; primary incident report for campaign details | Catalog inclusion supports that specific status; it does not prove exploitation of the assessed asset |
| Exploitability or impact | Vendor analysis, technical paper, source diff, or reviewed research | Preconditions and demonstrated behavior; a repository label or repost is not verification |
| Mitigation | Vendor fix/configuration guidance and release notes | Exact fixed version, workaround limits, operational prerequisites |
| Detection or behavior mapping | Primary incident/research evidence plus current MITRE ATT&CK technique content | Map only observed behavior; record the ATT&CK version or retrieval date |

Use the source's own dates and terminology. Distinguish publication date, last update, and the date you retrieved it. When a page lacks stable line numbers, cite its heading, table row, page, or API field path. Preserve contradictions rather than silently selecting the more convenient account.

## Primary references

- [CVE Program](https://www.cve.org/) — CVE records and program information.
- [NVD API documentation](https://nvd.nist.gov/developers) — current API endpoints and response contract; do not copy field assumptions from older API versions.
- [CISA Known Exploited Vulnerabilities Catalog](https://www.cisa.gov/known-exploited-vulnerabilities-catalog) — catalog entries and machine-readable formats.
- [MITRE ATT&CK](https://attack.mitre.org/) — current behavior taxonomy; use the technique page or current dataset rather than a remembered ID/name pairing.

For product-specific claims, locate the manufacturer's current security bulletin or fixed-version documentation directly. Confirm that third-party summaries link to the same underlying record before treating them as independent corroboration.
