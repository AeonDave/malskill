---
name: sagemath
description: "Computer algebra and number-theory environment for cryptanalysis scripting. Use when crypto tasks require finite fields, polynomial rings, elliptic curves, lattice reduction (LLL), small-roots methods, symbolic algebra, or direct Sage-powered Python scripts (.sage / sage.all)."
license: GPL-3.0
compatibility: "Linux/macOS/WSL recommended; works via native install, conda, Docker, Jupyter kernel, or cloud runtimes (SageCell/CoCalc)."
metadata:
  author: AeonDave
  version: "1.0"
---

# SageMath

Sage is the go-to environment for **mathematical cryptanalysis** and attack modeling.
Use it when standard scripting is not enough for algebraic structures and lattice workflows.

## Typical use cases

- Finite field computations (`GF`, extension fields).
- Polynomial rings and elimination/resultants.
- Elliptic curve arithmetic and discrete-log style tasks.
- Lattice modeling (`matrix`, `LLL`) for partial leakage recovery.
- Fast prototyping of attack math before operationalizing in Python.

## Invocation modes

```bash
# REPL
sage

# Run .sage script
sage solver.sage

# Run Python file with Sage runtime
sage -python solver.py

# Jupyter with Sage kernel
sage -n jupyter
```

## Practical workflow

1. Parse input values (files, network output, pubkeys).
2. Model algebra in Sage-native structures (`GF`, rings, curves, matrices).
3. Validate with small synthetic tests.
4. Execute full solve, export recovered secrets to plain Python bytes/ints.
5. Integrate with `pwntools` or service scripts for secret recovery.

## Common cryptanalysis patterns

From real-world cryptanalysis work, common patterns include:

- `from sage.all import *` alongside `pwntools` remote interaction.
- Factoring and formatting factorization answers for oracle protocols.
- Elliptic curve order / point lifting / discrete-log solves.
- Lattice assembly via identity/augment/stack + `LLL()`.
- Finite-field polynomial construction and resultant-based elimination.
- `.sage` solvers combining bitwise transforms, polynomial operations over `GF(2^N)`, and iterative remote interaction rounds.

## Output hygiene

- Convert Sage integers to Python ints before serialization.
- Convert numeric secrets to bytes with explicit endianness/length handling.
- Keep deterministic seeds/options when random components appear.

## Resources

- `references/python-sage-scripts.md` — authoritative patterns for `.sage` and `sage -python` workflows, imports, interoperability, and pitfalls.
- `references/cryptanalysis-patterns.md` — practical cryptanalysis templates (GF, EC, lattice, polynomial elimination) grounded in real solver style.
