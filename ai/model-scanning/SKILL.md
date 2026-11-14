---
name: model-scanning
description: "Scan untrusted ML model artifacts for code-execution payloads before loading them: picklescan, fickling, modelscan, modelaudit across pickle/PyTorch/Keras/TF/ONNX/GGUF/safetensors. Use to triage downloaded or third-party model files and to reason about scanner-bypass limits — a clean scan is not proof the file is safe to load."
license: MIT
compatibility: "Python 3.10+; pip-installed scanners. modelaudit scans offline without ML frameworks; others may import format libs. Load untrusted artifacts only in a disposable sandbox."
metadata:
  author: AeonDave
  version: "1.0"
---

# model-scanning

Most model formats execute code at load time, so loading an untrusted model is running untrusted code. Scan first, in isolation, and treat the result as a triage signal — **not** a safety guarantee. The manual opcode-level method (`pickletools`, magic-byte identification, format-specific sinks) lives in [model-file-forensics](../../offensive-ctf/ai-ml-ctf/references/model-file-forensics-and-deserialization.md); this skill covers the scanner tooling and how far to trust it.

## Pick the scanner

| Tool | Scope | Strength |
|---|---|---|
| `picklescan` | Pickle / PyTorch ZIP | HF's inline pipeline; fast; blocklist-based (weakest, most-bypassed) |
| `fickling` | Pickle / dill | Trail of Bits; decompiles the pickle to readable Python + allowlist safety check |
| `modelscan` | Pickle, PyTorch, Keras H5/V3, TF SavedModel, NumPy, Joblib, ONNX | Protect AI; CI-friendly multi-format |
| `modelaudit` | 40+ formats incl. GGUF, safetensors, config files | Promptfoo; CVE rules, SARIF/SBOM, secret scan, offline, remote pulls |

Default to `modelaudit` for breadth, cross-check pickle verdicts with `fickling --check-safety`, and read the pickle imports `picklescan` reports. Multiple scanners are defense-in-depth, not redundancy.

## Run

```bash
# modelaudit (pip install modelaudit) — offline, never loads the model
modelaudit scan suspicious_model.pkl
modelaudit scan hf://org/model                      # scan from the Hub without downloading
modelaudit scan model.pt --format sarif --output r.sarif
modelaudit scan --list-scanners                     # see scanner IDs
modelaudit scan models/ --scanners pickle --strict  # fail on warnings
# equivalent via the promptfoo wrapper: promptfoo scan-model model.pt

# fickling (Trail of Bits) — static verdict + decompile
fickling --check-safety model.pkl
fickling --trace model.pkl                           # what unpickling would do

# modelscan (Protect AI)
modelscan -p model.h5

# picklescan — reports the imported globals it finds
picklescan -p model.pkl
```

For a PyTorch ZIP, the dangerous member is the inner `*/data.pkl`; scanners that key only off the outer extension miss it.

## "Clean scan" is not "safe to load"

Blocklist scanners enumerate known-dangerous callables and allow everything else, so one off-list function bypasses them. This is a documented, active gap:

- **picklescan bypass classes** (repeatedly disclosed as CVEs across 2025): file-extension mismatch (scanner keys off the outer extension), corrupted-archive handling that skips embedded members, blocklist evasion via **submodule indirection** (`import` of a safe parent module whose child is dangerous), and opcode-edge mishandling (`STACK_GLOBAL` argument order). The pattern: each scanner release fixes the *known* bypass; a new variant passes again. Patch to current and still do not treat a pass as safe.
- **Research reality:** published evasion research (ShadowPickle) shows crafted pickles passing the full mainstream scanner set while still executing on `torch.load` — multi-scanner agreement is a weaker signal than it feels.

Therefore: a failed scan is a strong stop signal; a passing scan only means no known-bad signature fired in that version.

## Safer handling

- **Prefer safetensors.** It removes the code-execution primitive at the format level (header JSON + raw tensors); pickle-weight models are still a large share of popular Hub downloads, so selection is a provenance decision, not an assumption. Convert trusted pickle to safetensors via [`transformers`](../transformers/SKILL.md) `save_pretrained(safe_serialization=True)`.
- Verify source and checksums; `weights_only=True` (default in PyTorch ≥2.6) is a strong guard but not a guarantee — a parser-level bypass existed on torch ≤2.5.1 (fixed in 2.6.0): the guard is version-sensitive, keep torch current.
- Load anything still untrusted only in a throwaway, resource-limited sandbox with no secrets and no network.

## References

- Tools: [modelaudit](https://github.com/promptfoo/modelaudit) · [modelscan](https://github.com/protectai/modelscan) · [fickling](https://github.com/trailofbits/fickling) · [picklescan](https://github.com/mmaitre314/picklescan)
- Manual opcode/forensics method: [model-file-forensics](../../offensive-ctf/ai-ml-ctf/references/model-file-forensics-and-deserialization.md); supply-chain context: [`litellm`](../litellm/SKILL.md), [`llm-technique`](../../offensive-techniques/llm-technique/SKILL.md)
