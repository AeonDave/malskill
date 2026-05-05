---
name: keras
description: "Keras model loading and structure-inspection workflow for `.keras`, SavedModel, and HDF5 artifacts. Use when you need to inspect layers, summaries, configs, weights, or quick inference behavior from TensorFlow/Keras model files."
compatibility: "Linux, Windows, macOS; Python 3; TensorFlow/Keras installed"
metadata:
  author: AeonDave
  version: "1.0"
---

# Keras

High-level model inspection when the artifact speaks layers, configs, and summaries.

## When to use Keras

Use Keras when you need to:

- load a saved Keras or TensorFlow model artifact
- print a structural summary and inspect layers quickly
- review configuration, weights, or input/output expectations
- run a small inference sanity check without rebuilding the whole training stack

## Quick Start

```python
from keras.saving import load_model

model = load_model("model.keras", compile=False, safe_mode=True)
model.summary()
```

## High-Value Workflows

### Layer and config inspection

```python
for layer in model.layers:
    print(layer.name, layer.__class__.__name__)

config = model.get_config()
print(config.keys())
```

### Weight inspection

```python
for layer in model.layers:
    weights = layer.get_weights()
    if weights:
        print(layer.name, [w.shape for w in weights])
```

## Practical Notes

- Use `compile=False` when you only need inspection; it avoids unnecessary optimizer/loss restoration.
- Keep `safe_mode=True` unless you are intentionally loading trusted custom objects that require otherwise.
- `model.summary()` is the quickest overview; `get_config()` is better for structured downstream tooling.

## Caveats

- Custom layers, losses, or metrics may require explicit `custom_objects` support.
- SavedModel, `.keras`, and old `.h5` artifacts do not behave identically across all environments.
- Deserialization of untrusted custom objects is a real risk; stay conservative.

## Resources

No bundled `scripts/`, `references/`, or `assets/`.
Use the official Keras saving and serialization documentation for format differences and `safe_mode` behavior.
