---
name: crypto-ctf
description: >
  Challenge-solving methodology for cryptography challenge solving. Integrates crypto-technique, cracking-technique with preserved imported CTF techniques, generic writeup-derived patterns, and tool-routing for agentic AI. Use when working on cryptography challenge solving tasks involving ciphertexts, keys, signatures, oracles, transcripts, proofs, PRNG outputs, or mathematical protocol code.
license: MIT
compatibility: "AgentSkills-compatible agents; local challenge artifacts; authorized training and lab environments."
metadata:
  author: AeonDave
  version: "1.0"
  category: ctf-solving
---

# Crypto CTF

Goal: solve cryptography challenge solving tasks with professional offensive methodology, preserved imported technique coverage, and reproducible evidence.

## When this skill applies

- ciphertexts, keys, signatures, oracles, transcripts, proofs, PRNG outputs, or mathematical protocol code
- RSA, ECC, DH, DSA/ECDSA, lattice/LWE, PRNG, symmetric-mode, stream-cipher, ZKP, secret-sharing, or exotic algebraic weaknesses

## Operating model

1. Classify the dominant artifact, primitive, or objective.
2. Load the closest `offensive-techniques` methodology before selecting tools.
3. Use `references/source-coverage.md` to see preserved imported topics.
4. Load debrandized imported references only for deep technique details.
5. Choose the smallest tool chain that can produce a validation signal.
6. Record the exact proof path and stop once the objective is reproducible.

## Technique integration

Primary methodology to load:

- `crypto-technique`
- `cracking-technique`

Use these as decision engines. This skill adds challenge-oriented triage, time-boxing, and preserved specialized patterns from the imported corpus.

## Tool routing

Prefer these tool families when the corresponding signal appears:

- `offensive-tools/cryptography/rsactftool`
- `offensive-tools/cryptography/sagemath`
- `offensive-tools/cryptography/cyberchef`
- `offensive-tools/cracking/hashcat`
- `offensive-tools/cracking/john`
- `coding/python-patterns`

Tool syntax belongs in the tool skills. This skill decides when a tool family fits and what output should validate progress.

## Writeup-derived patterns

- Public writeup patterns favor artifact-first triage, shortest reproducible path, and explicit validation signal before pivoting.
- Record failed hypotheses with evidence so an agent does not repeat expensive dead paths.
- Prefer category-specific tools after surface classification instead of running every scanner or brute-forcer by habit.
- End with a replayable proof: recovered secret, local verification, exploit output, decoded artifact, or correlated evidence chain.

## Category-specific quick pivots

- Extract parameters before choosing attacks: modulus, exponent, curve order, nonce, IV, oracle response, random source, and serialization.
- Rank attacks by structural evidence: factorability, smoothness, nonce reuse, small roots, linear recurrence, or mode misuse.
- Validate recovered material by re-encryption, signature verification, oracle replay, or known plaintext.

## Quality gates

- No claim without a validation signal: recovered secret, replayed exploit, decoded artifact, reproduced model behavior, or corroborated evidence.
- Do not brute force before representation, constraints, and success oracle are known.
- Keep a pivot ledger: hypothesis, evidence, result, next shortest path.
- Preserve source coverage: every imported file is mapped in `references/source-coverage.md` and available in `references/imported/`.
- Keep challenge/platform/competition names out of notes and generated reports.

## Resources

- [references/agentic-workflow.md](references/agentic-workflow.md) — category workflow, tool routing, and technique handoff.
- [references/source-coverage.md](references/source-coverage.md) — no-loss map of preserved imported source files and topics.
- [references/imported/source-skill.md](references/imported/source-skill.md) — preserved, debrandized imported technique material.
- [references/imported/advanced-math.md](references/imported/advanced-math.md) — preserved, debrandized imported technique material.
- [references/imported/classic-ciphers.md](references/imported/classic-ciphers.md) — preserved, debrandized imported technique material.
- [references/imported/ecc-attacks.md](references/imported/ecc-attacks.md) — preserved, debrandized imported technique material.
- [references/imported/exotic-crypto-2.md](references/imported/exotic-crypto-2.md) — preserved, debrandized imported technique material.
- [references/imported/exotic-crypto.md](references/imported/exotic-crypto.md) — preserved, debrandized imported technique material.
- [references/imported/historical.md](references/imported/historical.md) — preserved, debrandized imported technique material.
- [references/imported/lattice-and-lwe.md](references/imported/lattice-and-lwe.md) — preserved, debrandized imported technique material.
- [references/imported/modern-ciphers-2.md](references/imported/modern-ciphers-2.md) — preserved, debrandized imported technique material.
- [references/imported/modern-ciphers-3.md](references/imported/modern-ciphers-3.md) — preserved, debrandized imported technique material.
- [references/imported/modern-ciphers.md](references/imported/modern-ciphers.md) — preserved, debrandized imported technique material.
- [references/imported/prng-attacks.md](references/imported/prng-attacks.md) — preserved, debrandized imported technique material.
- [references/imported/prng.md](references/imported/prng.md) — preserved, debrandized imported technique material.
- [references/imported/rsa-attacks-2.md](references/imported/rsa-attacks-2.md) — preserved, debrandized imported technique material.
- [references/imported/rsa-attacks.md](references/imported/rsa-attacks.md) — preserved, debrandized imported technique material.
- [references/imported/stream-ciphers.md](references/imported/stream-ciphers.md) — preserved, debrandized imported technique material.
- [references/imported/zkp-and-advanced.md](references/imported/zkp-and-advanced.md) — preserved, debrandized imported technique material.
