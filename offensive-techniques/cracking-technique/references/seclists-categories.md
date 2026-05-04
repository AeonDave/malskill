# SecLists category strategy

## Purpose

Use curated wordlist categories intentionally instead of throwing generic lists at every cracking or authentication problem.

## Category map

| Objective | Useful category | Why |
|---|---|---|
| Generic password baseline | `Passwords/Common-Credentials`, `Passwords/Leaked-Databases` | Fast signal and common reuse |
| Organization-focused candidates | custom list + `Passwords/Default-Credentials` | Products, brands, seasons, locations |
| User enumeration | `Usernames`, names from OSINT | Build valid principal sets before spraying |
| Service defaults | `Passwords/Default-Credentials` | Routers, cameras, appliances, apps |
| Web discovery handoff | `Discovery/Web-Content` | Not cracking; feed recon/content discovery |
| Pattern matching | `Pattern-Matching` | Detect secrets, tokens, and structured leaks |
| Payload testing | `Fuzzing`, `Payloads` | Not candidate passwords; keep separate from cracking |

## Campaign selection

### Password audit

1. Start with policy-aware custom candidates.
2. Add organization-specific terms from OSINT.
3. Apply small, explainable rules.
4. Use generic leaked lists only after targeted passes plateau.

### Breach/hash dump

1. Run a quick common-password signal pass.
2. Cluster recovered passwords by language, season, suffix, keyboard pattern, and policy shape.
3. Generate masks/rules from observed clusters.
4. Expand into larger leaked corpora only when marginal yield remains useful.

### Credential recovery with known user context

1. Build candidates from username, email, department, hostnames, project names, local language, and dates.
2. Add common substitutions and suffixes.
3. Use masks for policy-shaped guesses.
4. Stop when yield is flat and report coverage limits.

## Online spraying caution

SecLists password categories are often too aggressive for online authentication. Before any live test:

- Confirm lockout threshold and reset window.
- Use one or very few candidates per window.
- Prefer known-compromised credential validation over broad guessing.
- Keep username source quality high to reduce noise.

## Candidate hygiene

- Normalize encoding and line endings.
- Remove duplicates before long campaigns.
- Track which source generated each candidate class.
- Separate password candidates from payload/fuzzing lists.
- Do not store recovered credentials in plaintext reports unless policy permits.

## Common pitfalls

- Using `rockyou` as the first and only strategy.
- Mixing web payload lists into password candidates.
- Ignoring local language and organization-specific naming.
- Launching online attempts from offline cracking assumptions.
- Reporting recovered count without explaining which policy weakness caused recovery.
