---
name: cracking-technique
description: "Technique-first password/hash cracking methodology for AI agents. Covers triage, target modeling, strategy selection (dictionary/rules/hybrid), corpus and candidate engineering, campaign orchestration, and reproducible result analysis for audits, breach analysis, and credential recovery. Use when you need the right cracking flow without turning the skill into a per-tool command manual."
license: MIT
compatibility: "Linux/Windows/macOS; local CPU/GPU cracking environments"
metadata:
  author: AeonDave
  version: "2.0"
  category: crypto
  language: multi
---

# Cracking technique

Goal: maximize useful recoveries while keeping campaigns reproducible, explainable, and aligned to objective.

## When this technique applies

- Password-strength audits and policy validation.
- Breach/hash-dump analysis and prioritization.
- Credential recovery with legitimate authorization.
- Local cracking campaigns that need staged wordlist, rule, and hybrid policy.

## Boundary with offensive-tools

This skill defines **methodology, decision flow, and quality gates**.
Tool-specific flags and commands belong to `offensive-tools/cracking/*` skills.

## Tool families

| Family | When to use | Skill |
|--------|-------------|-------|
| `hashcat` | GPU-accelerated hash cracking — dictionary, rule, mask, hybrid | `offensive-tools/cracking/hashcat/` |
| `john` | CPU-first cracking, wide format coverage, quick format detection | `offensive-tools/cracking/john/` |
| `hydra` | Online auth brute-force (SSH, HTTP, SMB, RDP, etc.) — not hash cracking | `offensive-tools/cracking/hydra/` |

## Initial triage

Before launching a campaign, classify the material and choose the smallest strategy that can produce signal fast.

- **Starting state**: are you working with offline hashes, encrypted archives, a password-audit corpus, or a live authentication surface?
- **First questions**: what is the exact hash or auth format, what objective matters most (audit insight, recovery yield, or single-account recovery), and what contextual candidate sources exist?
- **Immediate actions**: verify format integrity, split targets by type/salt/context, and rank candidate strategies before spending runtime.
- **Tool-family direction**: use `john` or format-identification workflows to validate parsing, `hashcat` for scaled offline campaigns, and `hydra` only when the target is a live service and online guessing is explicitly justified.
- **Escalation rule**: prefer high-signal contextual candidates and rules before broad brute-force or large generic masks.

Pick `hashcat` for large GPU campaigns or competitive keyspace. Pick `john` for quick format identification and formats hashcat does not support. Pick `hydra` only when the attack surface is a live service, not a hash dump.

## Agent operating model

The agent should run this loop:

1. Triage hash material and constraints.
2. Model target password behavior.
3. Select and order cracking strategies.
4. Prepare candidate assets (wordlists/rules/masks).
5. Execute and monitor campaigns with clear stop criteria.
6. Analyze cracked set and remaining set.
7. Feed patterns back into next iteration.

Do not scale runtime before confirming hash format correctness, replayability, and campaign telemetry.

## Objective-driven strategy selection

### Case A: Password audit

Use precision-first strategy.

- Prioritize target-specific candidates over huge generic lists.
- Emphasize explainability of recovered patterns for policy remediation.

### Case B: Breach/hash leak analysis

Use yield-first strategy.

- Start broad enough to get signal quickly.
- Then narrow to leak-specific patterns to improve marginal recovery.

### Case C: Credential recovery with known user context

Use context-first strategy.

- Build candidates from user/domain context before brute expansion.
- Use progressive masks only after contextual attempts plateau.

## Campaign lifecycle

1. **Triage**
   - Validate hash type(s), salts/format, and ingestion integrity.
   - Confirm legal scope and success criteria.

2. **Target modeling**
   - Infer likely password construction patterns (language, policy, reuse behaviors, suffix habits).
   - Define candidate classes to test in order.
   - Prefer target-specific and small high-signal corpora plus rules before generic masks.

3. **Asset engineering**
   - Prepare candidate corpus from contextual and generic sources.
   - Choose wordlist categories intentionally: leaked-password baselines, default credentials, usernames, pattern-matching, and custom OSINT-derived candidates have different purposes.
   - Deduplicate and normalize candidates before execution.
   - Prepare rules as the default expansion layer: append years/digits/specials, toggle case, leetspeak, and mutate target terms intelligently.
   - Use masks only for strong known structures or cleanup; do not replace targeted wordlists + rules with broad brute masks.

4. **Execution orchestration**
   - Run phased campaigns (quick signal pass → focused pass → expansion pass).
   - Track recovery-rate delta, not only elapsed time.
   - Stop low-yield phases early and reallocate effort.

5. **Analysis and iteration**
   - Cluster recovered passwords by pattern families.
   - Identify what classes remain uncracked and why.
   - Generate next-pass candidates from observed pattern gaps.

6. **Reporting**
   - Separate recovered credentials, inferred policy weaknesses, and recommendations.
   - Report confidence and coverage limits explicitly.

## Quality gates

- Hash parsing and mode mapping verified before long run.
- Candidate assets are deduplicated and traceable to a strategy hypothesis.
- Campaign telemetry is retained (phase, duration, yield, residual set).
- Recovered patterns are analyzed before launching the next phase.
- Final report distinguishes facts from assumptions.

## Anti-patterns

- Running massive generic dictionaries first without target model.
- Treating tool throughput as success when yield is flat.
- Mixing multiple strategy changes at once (no attribution of gains).
- Reporting cracked count without pattern insight or remediation value.
- Embedding tool-command manuals directly in technique skill body.

## Resources

- [references/wordlist-strategy.md](references/wordlist-strategy.md)
- [references/seclists-categories.md](references/seclists-categories.md)
- [references/mask-generation.md](references/mask-generation.md)
- [references/rule-chaining.md](references/rule-chaining.md)
- [references/progressive-cracking.md](references/progressive-cracking.md)
