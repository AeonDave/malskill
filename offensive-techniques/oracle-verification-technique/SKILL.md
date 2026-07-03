---
name: oracle-verification-technique
description: "Machine-oracle verification for security findings: promote a finding to VERIFIED only when a named oracle re-runs the exploit N/N against the live target AND a negative control fails on a safe surface, then package a portable proof capsule the client can replay. Use before reporting web/API/auth findings, when triaging scanner output (nuclei/nikto/zap/sqlmap), when an LLM or sub-agent asserts a vulnerability without proof, or when a report must separate proven findings from candidates. Tool-agnostic; pairs with web-exploit, vuln-exploit, and report-generation techniques."
license: MIT
metadata:
  author: AeonDave
  version: "1.0"
---

# Oracle Verification Technique

**Goal**: A finding is a *candidate* until a **named machine oracle** reproduces it against the live target N-out-of-N times AND a negative **control** fails on a safe surface. Only then is it **VERIFIED**, shipped with a **proof capsule** anyone can replay. An LLM assertion, a scanner hit, or a single lucky exploit is never proof on its own.

## When this technique applies

- Before reporting any web/API/auth/injection finding as confirmed.
- Triaging third-party scanner output (nuclei, nikto, zap, sqlmap, dalfox) — hold it back until re-proven.
- An LLM or delegated sub-agent claims a vulnerability without a reproducible receipt.
- A report must split **VERIFIED** from **candidate**, or a CI gate must break only on proven findings.
- Multi-step chains where each hop must be independently proven before the chain is claimed.

Do not use this to *find* bugs — it only decides whether a suspected bug is real. Discovery stays with the web-exploit / vuln-exploit / recon techniques; this gates their output.

## Core rule (enforce, don't just intend)

> **No verdict without a named oracle.** A `VERIFIED` badge that cannot name the oracle that earned it is rejected and downgraded to `candidate`. The model coordinates; the oracle decides what is true.

Encode this as a hard check in your workflow and in report generation, not as a hope.

## The verification loop

For each candidate finding, run these gates in order. Fail any gate → stay `candidate`.

### 1. Name the oracle
Pick a deterministic oracle for the vuln class — a check that returns a machine-decidable positive/negative from the target's *actual response*, not a pattern match on a scanner label. If no oracle exists for the class, the finding cannot be `VERIFIED` (report it as `candidate — no oracle`). Load `references/oracle-catalog.md` for per-class oracles and their positive signals.

### 2. Re-run N/N against the live target
Re-execute the exploit recipe **N times** (default N=3) against the real target. Every run must produce the positive signal. Any miss → `candidate` (flaky / not reliably exploitable). Fresh session/token each run where auth is involved — a replay that only works with a stale cached token is not proven.

### 3. Negative control must fail on a safe surface
Run the *same* oracle against a surface that must be safe: a non-vulnerable endpoint, a patched route, a benign parameter value, or a control payload that should do nothing. The control **must fail** (no positive signal). If the oracle fires on the safe surface too, the oracle is broken or the signal is ambient — the finding is **not** proven. This is what stops false positives; do not skip it.

### 4. Separate proof from impact
A bare signal (an out-of-band callback, a reflected marker) proves *reachability*, not *harm*. Rate reachability-only findings **medium** until an impact oracle reproduces real impact (data read, auth bypass, RCE). Do not assume impact from a probe.

### 5. Package the proof capsule
Emit a portable, replayable capsule (see `references/proof-capsule.md`): oracle name, exact recipe (request/command + payload), positive signal, the N/N run log, the failing control, and a one-command replay. The client/dev replays it against the live target **without trusting your tool**. Multi-step chains bundle every proven hop into one capsule.

## Scope safety during verification

- Host-lock active oracles (sqlmap, dalfox, raw HTTP) to the declared engagement target. Never feed third-party URLs scraped from page content into an attack oracle.
- Re-running exploits is active testing — respect engagement posture (pentest vs red-team vs lab). Confirm before any oracle that is destructive or irreversible.
- If an aggressive discovery sweep knocked the target over, **wait for it to answer again** before running oracles, or every gate fails and you falsely report zero.

## Output contract

Report each finding with an explicit status:
- `VERIFIED` — oracle named, N/N passed, control failed, capsule attached.
- `candidate` — suspected but not (yet) proven; state which gate it failed.
- `candidate — no oracle` — no oracle exists for this class; manual verification required.

Never let a scanner-labeled or LLM-asserted finding reach the `VERIFIED` column.

## Pair with sibling skills

- `offensive-techniques/web-exploit-technique/SKILL.md` — supplies the exploit recipes this skill gates.
- `offensive-techniques/vuln-exploit-technique/SKILL.md` — impact validation for the impact oracle (gate 4).
- `offensive-techniques/report-generation-technique/SKILL.md` — consumes the VERIFIED/candidate split and the capsules.
- Behavioural gates `evidence-before-claims` and `verification-before-completion` — this skill is their enforced, machine-checked form for findings.

## Resources

### references/

- `references/oracle-catalog.md` — per-vuln-class oracles: positive signal, recipe skeleton, and the negative control to run. Load when choosing or building an oracle (gate 1–3).
- `references/proof-capsule.md` — the proof-capsule schema and replay contract. Load when packaging a VERIFIED finding (gate 5).
