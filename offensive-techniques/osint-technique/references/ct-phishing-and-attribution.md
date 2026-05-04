# Certificate transparency phishing and attribution

## Purpose

Use public certificate transparency (CT), passive DNS, URL intelligence, and artifact pivots to identify lookalike infrastructure and support cautious attribution analysis.

## CT monitoring use cases

- Detect newly issued lookalike domains targeting an organization or brand.
- Identify unauthorized certificates for legitimate domains.
- Cluster phishing infrastructure through SAN overlap, issuer timing, and naming patterns.
- Seed further passive DNS and URLScan research.

## Lookalike patterns

| Pattern | Example signal |
|---|---|
| Typosquatting | missing, doubled, swapped, adjacent-key characters |
| Homograph | Unicode or punycode lookalikes |
| Prefix/suffix abuse | `login-`, `secure-`, `-support`, `-verify` |
| Brand plus service | brand + `vpn`, `sso`, `mfa`, `payroll`, `hr` |
| Environment mimicry | `okta`, `adfs`, `portal`, `idp`, `mail` |

## CT workflow

1. Build a seed list of brand names, product names, subsidiaries, and common abbreviations.
2. Query CT sources for exact and fuzzy matches.
3. Normalize domains and extract registered domain, SANs, issuer, validity, and first-seen time.
4. Enrich with passive DNS, WHOIS/RDAP, URLScan, Shodan/Censys, and web screenshots.
5. Prioritize domains with login-themed content, recent issuance, privacy registration, or hosting overlap with known abuse.
6. Archive evidence before takedown or content rotation.

## Attribution discipline

Use confidence labels, not certainty. Evaluate evidence classes:

| Evidence | Strength |
|---|---|
| Same domain registration account or nameserver reuse | Medium to high |
| Same TLS certificate or key reuse | High when unique |
| Same hosting ASN/CDN only | Low by itself |
| Same phishing kit path or HTML comments | Medium |
| Same wallet, email, or panel endpoint | Medium to high |
| Similar timing or naming pattern only | Low |

Require independent evidence before linking infrastructure to an actor or campaign.

## ACH-lite process

1. List competing hypotheses: same actor, copycat, shared kit, coincidental hosting, sinkhole/defensive registration.
2. For each evidence item, mark whether it supports, contradicts, or is neutral for each hypothesis.
3. Prefer the hypothesis with the fewest contradictions.
4. State confidence and what evidence would change the assessment.

## Output

- Candidate domain list with first-seen time and reason.
- Enrichment table: DNS, hosting, certificate, URLScan, screenshots.
- Risk priority and recommended action.
- Attribution assessment with confidence and caveats.

## Common pitfalls

- Treating a lookalike certificate as malicious without content or DNS evidence.
- Over-attributing based on shared commodity hosting.
- Ignoring defensive registrations by the protected organization.
- Failing to archive pages before content changes.
