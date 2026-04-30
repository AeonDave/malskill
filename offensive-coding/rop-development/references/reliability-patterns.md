# Reliability patterns for ROP engineering

These are reusable engineering patterns for making ROP chains stable across rebuilds, targets, and environments.

## 1) Deterministic gadget selection beats gadget lottery

Gather candidates, score them, sort them, then pick deterministically.

Apply to ROP:
- Use stable ranking criteria (side effects, length, clobbers, alignment impact).
- Keep randomization out of production chain selection.
- Log candidate counts and rejection reasons.

## 2) Unwind-aware validation as a gadget quality filter

When stack-walk plausibility matters, prefer candidates in well-formed functions with coherent unwind metadata.

Apply to ROP:
- Reject candidates tied to unstable unwind/call-stack behavior.
- Prefer gadget locations that remain valid across minor binary updates.

## 3) Fallback cascades prevent hard-fail fragility

Do not rely on a single ideal gadget source.

Apply to ROP:
- Define fallback search domains up front (main module -> runtime library -> secondary modules).
- Keep explicit “last resort” branches instead of aborting when one source lacks ideal gadgets.

## 4) Safety floors for stack math

Use explicit minimum bounds for pivots and stack argument regions.

Apply to ROP:
- Define minimum safe pivot displacement and argument area boundaries.
- Fail closed when chain geometry violates these bounds.

## 5) Separate transfer logic from execution logic

Keep leak/resolve, pivoting, and call/syscall invocation modular.

Apply to ROP:
- Easier debugging and portability between targets.
- You can replace one primitive without rewriting the full chain.

## 6) Instrumentation-first debugging

Reliability work needs counters and one-shot diagnostics.

Apply to ROP:
- Log selected gadgets, rejected candidates, and mitigation-relevant decisions.
- Keep first-run diagnostics to quickly classify failures.