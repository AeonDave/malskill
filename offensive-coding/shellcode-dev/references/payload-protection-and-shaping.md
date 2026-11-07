# Payload Protection and Binary Shaping

Load when building a loader: payload encryption/key splitting, encrypted container layout, and static-analysis shaping (entropy, ML-classifier features). Does not cover transport encoders — see `encoders-and-stagers.md`.

## 1) Key splitting over ambient state

Split the payload key into shares derived from environment state, XOR them at runtime. One share per property you want enforced:

```
K = S_container ^ S_reg ^ S_peb ^ S_cf
```

- `S_container` — static share from the binary (config constant).
- `S_reg` — normal key material.
- `S_peb` — derived from PEB debug state (`BeingDebugged`, `NtGlobalFlag` under a debugger: both flip). A debugged process reconstructs the wrong key with **no branch to patch**.
- `S_cf` — FNV-1a64 lanes over the ciphertext itself: any tamper with the container yields the wrong key.

Why it matters: sandbox/anti-tamper verdicts become **arithmetic, not logical**. There is no `if (is_sandbox) exit();` for a sandbox to NOP — the wrong key just decrypts garbage. Implementation evidence: `AshuraLoader key_splitting.go` (4-share split, branchless verdict). Keep shares cheap to compute and fail on any share mismatch by design (garbage-in → garbage-out).

Design rules:
- Every anti-analysis check folded into key material must be **stable on the real target** (false positives corrupt execution on legitimate hosts).
- Prefer state that is hard to fake consistently in a sandbox: PEB debug fields, ciphertext-derived shares, build-bound digests.
- Do not fold volatile host state (usernames, hostnames) into shares unless the campaign is host-locked.

## 2) MBA-obfuscated key material

The XOR identity `a ^ b == (a + b) - 2*(a & b)` is exact for all integers. Rewrite key/nonce computation over it so byte-pattern rules matching `xor` disappear. Used identically in three independent implementations (`AshuraLoader mba.go`, evasion `goahead_runtime.go`, nativeloader `mba_crypto.h`).

Harden further:
- Add junk terms that are algebraically zero but **structurally non-cancellable** by the optimizer (e.g., `volatile`-loaded values that are provably 0 at runtime, not at compile time).
- Split constants: `constant = a - b` with both halves derived from the build seed (kills immediate-value signatures).
- Caveat: MBA-XOR is still XOR — two plaintext/ciphertext pairs recover the keystream. It defeats byte-pattern rules, not cryptographic attack. It is obfuscation of the key schedule, not of the cipher.

## 3) Encrypted container layout

Ciphertext does not need to look like a data blob:

- **Chunked ASCII containers**: split ciphertext into variable-length lowercase-hex chunks, interleave benign "hexspeak" filler, NUL-separate, compile into a PE section whose **name is drawn from a seed-derived pool** (evidence: `AshuraLoader loaderascii.c`, `compile_c.go`). Nothing looks like a key or a payload at a glance; entropy is spread thin.
- **Seed-named payload sections**: every build draws section names/identifiers from a per-build seed — YARA rules pinned to names or offsets break.
- **Read-back barriers**: when zeroing or wiping memory in place, read back after write so dead-store elimination cannot remove the wipe (evidence: `ade memevasion_active.go`).

## 4) Binary shaping against ML/static classifiers

Detection is increasingly classifier-based, not signature-based. Shape the feature vector, not just strings:

| Feature (EMBER-style) | Control |
|---|---|
| Rich header presence/consistency | Emit a synthetic Rich header with real MSVC product IDs and plausible build counts (absence of Rich header on an MSVC-style binary is itself a signal) |
| Byte histogram / entropy | Interleave benign text (English words) into high-entropy data regions; keep ciphertext chunks short and interleaved with ASCII filler |
| Import table | Retain a handful of benign kernel32/user32 imports as anchors (`-Wl,--undefined=__imp_<api>`); keep the import count out of minimal-territory (field-reported threshold) — tiny import tables score "unusual" |
| Authenticode | A large fake certificate table (project-measured: ~200 KB fake cert moved an EMBER score 0.9999 → 0.3044 — evidence: `ade peharden.go`, project validation, no integrity claim possible or intended) |
| Timestamp | TimeDateStamp 0 or absurd future values are anomalies; pick a plausible per-build timestamp inside recent release windows |
| Version info / .rsrc | Ship a complete seed-derived VERSIONINFO; "no resources" is a signal |
| Debug directory | Fake non-empty CodeView RSDS entry with a plausible PDB path, or strip cleanly — a half-formed debug dir is a signal |
| Go binaries | `.gopclntab` is a Go giveaway: rename and neutralize runtime strings with **same-length** swaps so layout checks still pass (`ade peharden_metadata.go`) |

Rules:
- Shaping is per-build and seed-driven: no two builds share the same fake names/timestamps/section layout.
- Every fabricated structure must be **internally consistent** (checksums recomputed, directory sizes match, Rich header XOR-key sane). Inconsistency is a stronger signal than absence.
- Never fabricate a validity claim: fake certificates never verify — treat them as histogram shaping only.

## 5) Entropy: observe, don't chase

- Measure entropy per section as a **sanity gate**, not an optimization target. A payload that must encrypt is high-entropy; the fix is layout (chunking, interleaving, section spreading), not mutating the cipher.
- Encrypt-at-rest + decrypt-at-use bounds the exposure window: keep plaintext in memory only during the write/exec transition (see `edr-evasion-dev` for the sleep/in-memory side of this).
- High entropy localized in one section is more reportable than the same bytes spread as interleaved chunks across a container.

## Validation

- Decode-equivalence check (decrypt → hash == expected) in CI for every build seed.
- Static diff across seeds: confirm no constant byte offset or section name survives.
- Run at least one classifier check on release builds; record the score next to the YARA scan result. The living reference dataset is [EMBER2024](https://github.com/FutureComputing4AI/EMBER2024) (feature set v3: DOS/Rich header, data directories, Authenticode) — the original EMBER 2018 repo is a read-only archive.
- Runtime check: sandbox behavior identical with key-splitting enabled (the share corruption must not produce a distinctive error path).
