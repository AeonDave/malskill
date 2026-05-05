---
name: scikit-learn
description: "scikit-learn model inspection workflow for loading persisted estimators, pipelines, and tree models. Use when you need to inspect `joblib` or pickle-based model artifacts, view parameters, feature names, importances, or pipeline structure, or run lightweight predictions for analysis."
compatibility: "Linux, Windows, macOS; Python 3; scikit-learn and joblib installed"
metadata:
  author: AeonDave
  version: "1.0"
---

# scikit-learn

Use this when the artifact is an estimator, pipeline, or tree model rather than a deep-learning checkpoint.

## When to use scikit-learn

Use scikit-learn when you need to:

- load persisted estimators or pipelines from `joblib` or pickle files
- inspect parameters, pipeline stages, and feature handling
- read feature importances or linear coefficients
- export or reason about decision-tree structure

## Quick Start

```python
import joblib

model = joblib.load("model.joblib")
print(type(model))
print(model.get_params().keys())
```

## High-Value Workflows

### Pipeline inspection

```python
if hasattr(model, "named_steps"):
    print(model.named_steps)

if hasattr(model, "get_feature_names_out"):
    print(model.get_feature_names_out())
```

### Feature importance or coefficients

```python
if hasattr(model, "feature_importances_"):
    print(model.feature_importances_)

if hasattr(model, "coef_"):
    print(model.coef_)
```

### Tree export helpers

```python
from sklearn.tree import export_text

if hasattr(model, "tree_"):
    print(export_text(model))
```

## Practical Notes

- `joblib` is the common persistence format for sklearn models with large NumPy arrays.
- Pipelines often carry more insight than the final estimator alone, so inspect `named_steps` early.
- `feature_names_in_` and `get_feature_names_out()` are high-value clues when reconstructing model inputs.

## Caveats

- `joblib.load` and pickle are unsafe for untrusted files.
- Cross-version loading is not guaranteed to be stable.
- Some estimators expose rich introspection, while others offer almost none beyond `get_params()`.

## Resources

No bundled `scripts/`, `references/`, or `assets/`.
Use the official scikit-learn persistence and pipeline docs for version and API specifics.
