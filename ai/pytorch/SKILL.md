---
name: pytorch
description: "PyTorch model inspection and checkpoint workflow for loading tensors, `state_dict` data, modules, and parameters. Use when working with `.pt` or `.pth` artifacts, auditing model structure, extracting weights, or scripting inference-oriented inspection of deep-learning checkpoints."
compatibility: "Linux, Windows, macOS; Python 3; PyTorch installed; GPU optional but often useful"
metadata:
  author: AeonDave
  version: "1.0"
---

# PyTorch

Use PyTorch when model artifacts are tensors first and everything else second.

## When to use PyTorch

Use PyTorch when you need to:

- load `.pt` or `.pth` checkpoints safely onto CPU or GPU
- inspect `state_dict` keys, module hierarchy, and parameter shapes
- switch a model into stable inference mode for probing
- script quick tensor statistics or output checks against a checkpoint

## Quick Start

```python
import torch

checkpoint = torch.load("model.pt", map_location="cpu")
print(type(checkpoint))
print(checkpoint.keys() if isinstance(checkpoint, dict) else "non-dict checkpoint")
```

## High-Value Workflows

### Inspect a state dict

```python
state = torch.load("weights.pth", map_location="cpu")
for name, tensor in state.items():
    print(name, tuple(tensor.shape), tensor.dtype)
```

### Inspect a loaded model

```python
model.eval()
for name, module in model.named_modules():
    print(name, module.__class__.__name__)

for name, param in model.named_parameters():
    print(name, tuple(param.shape))
```

### Safe inference baseline

```python
model.eval()
with torch.no_grad():
    output = model(sample_input)
```

## Practical Notes

- Use `map_location="cpu"` first unless you explicitly need GPU execution.
- Prefer `state_dict`-style loading and inspection over whole-model pickle blobs when possible.
- If your version supports it, prefer `weights_only=True` for safer tensor-only loads from trusted workflows.
- `eval()` and `torch.no_grad()` belong together for stable inspection and reduced memory noise.

## Caveats

- `torch.load` uses pickle under the hood; do not trust untrusted checkpoint files.
- Whole-model checkpoints require the original class code to be importable.
- Version drift can break deserialization or subtly alter behavior.

## Resources

No bundled `scripts/`, `references/`, or `assets/`.
Use the official PyTorch docs for `torch.load`, module introspection, and checkpoint best practices.
