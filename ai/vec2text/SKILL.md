---
name: vec2text
description: "vec2text: embedding-inversion library for reconstructing approximate text from sentence embeddings. Use when working with saved embedding tensors, privacy/inversion research, or AI/ML challenge workflows where you need to load a corrector model and invert strings or embeddings directly."
compatibility: "Linux, macOS, Windows; Python 3; PyTorch and Hugging Face stack; GPU strongly recommended for larger runs"
metadata:
  author: AeonDave
  version: "1.0"
---

# vec2text

Use vec2text when embeddings are the artifact and text recovery is the question.

## When to use vec2text

Use vec2text when you need to:

- invert sentence embeddings back into approximate text
- load a pretrained corrector for supported embedding families
- work from saved embedding tensors rather than original source text
- tune inversion quality with multiple refinement steps or beam search

## Quick Start

```python
import vec2text

corrector = vec2text.load_pretrained_corrector("gtr-base")
```

## High-Value Workflows

### Invert known strings through the matching embedder workflow

```python
vec2text.invert_strings(
    ["example text"],
    corrector=corrector,
    num_steps=20,
    sequence_beam_width=4,
)
```

### Invert embeddings directly

```python
import torch

embeddings = torch.load("embeddings.pt", map_location="cpu")
texts = vec2text.invert_embeddings(
    embeddings=embeddings,
    corrector=corrector,
    num_steps=20,
)
print(texts)
```

## Practical Notes

- Corrector choice must match the embedding family; mismatched models produce garbage.
- `num_steps` improves refinement quality, while `sequence_beam_width` improves search at higher memory cost.
- The project supports both direct string inversion workflows and embedding-only inversion workflows.

## Caveats

- Reconstruction is approximate, not guaranteed exact text recovery.
- Beam search raises memory usage quickly.
- Model support and pretrained aliases evolve; prefer current upstream docs over old examples.

## Resources

No bundled `scripts/`, `references/`, or `assets/`.
Use the upstream vec2text README for current pretrained corrector aliases, API entry points, and embedding-family matching guidance.
