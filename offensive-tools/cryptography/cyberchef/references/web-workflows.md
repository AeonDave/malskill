# CyberChef Reference — Web Workflows

## 1) Input triage flow

1. Paste or drop input.
2. Toggle raw/text mode correctly.
3. Run `Magic` with moderate depth first.
4. Inspect whether output gains structure (headers, readable text, known magic bytes).

## 2) Building robust recipes

Recommended pattern:
- Normalization first (trim, line breaks, from hexdump/base64).
- Decoding/decryption middle stages.
- Structural parse/validation at end (JSON parse, UTF-8, regex extraction).

Avoid giant opaque recipes; keep stages interpretable.

## 3) Breakpoints and step-through

Use breakpoints on suspicious operations to compare intermediate states.
If an operation introduces high-entropy noise unexpectedly, branch and test alternatives.

## 4) Magic operation guidance

Magic uses pattern matching + speculative execution + ranking heuristics.
Useful for discovery, but final recipe should be explicit and auditable.

Key knobs:
- Depth: controls recursive decode exploration.
- Intensive mode: enables expensive brute-force style branches (encodings, arithmetic logic).

## 5) Common decode chains

- `From Base64` -> `From Hex` -> `Gunzip`
- `XOR` (single-byte or key) -> `To/From Hex` -> textual parse
- `AES Decrypt` with IV extracted from prefix via register/slice operations

## 6) Sharing and reproducibility

Use one of:
- URL hash (contains recipe + optional input)
- Save Recipe JSON (best for programmatic handoff)

Always preserve:
- operation order
- exact option labels
- key/IV encodings

## 7) Validation checklist

- Output matches expected format (`FLAG{...}`, file signature, protocol grammar).
- Re-running recipe on same input is deterministic.
- Small perturbation tests fail appropriately (guard against accidental false positives).
