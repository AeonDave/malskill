# YARA rule quality and triage flow

## Minimal robust workflow

1. Start from concrete samples and extract stable indicators.
2. Write candidate rule with `meta`, `strings`, `condition`.
3. Test on mixed corpus (known bad + known good).
4. Record FP/FN behavior and tighten logic.
5. Promote only rules with stable precision.

## Practical tricks

- Prefer multiple medium-strength indicators over one brittle exact string.
- Use conditions that require contextual combinations.
- Keep `meta` rich (author, purpose, sample family, confidence).

## Common anti-patterns

- Rules matching trivial strings found in benignware.
- No corpus testing before rollout.
- Editing production rules without version/change notes.

## Deployment pattern

- Stage new rules in test set -> canary scans -> full scan fleet.
- Keep separate packs for IR triage vs threat-hunting depth scans.
