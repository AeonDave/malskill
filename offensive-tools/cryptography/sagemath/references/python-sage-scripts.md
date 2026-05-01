# SageMath Reference — Using Sage in Python Scripts

This reference covers practical script patterns for agentic cryptanalysis workflows.

## A) Script modes

## 1) Native `.sage` script

```python
#!/usr/bin/env sage

x = 2^10        # preparser: ^ becomes exponentiation
print(factor(2006))
```

Run:
```bash
sage solver.sage
```

## 2) Python script with Sage runtime

```python
from sage.all import GF, PolynomialRing, matrix

F = GF(2**128)
R.<x> = PolynomialRing(F)
print(R)
```

Run:
```bash
sage -python solver.py
```

## 3) Standard Python + explicit Sage namespace

In compiled/`.spyx` or stricter Python contexts, use explicit namespace:

```python
import sage.all

F = sage.all.GF(2**64)
print(sage.all.factorial(20))
```

## B) Loading code during iterative solving

- `load("file.sage")`: execute once.
- `attach("file.sage")`: auto-reload on file changes (great for debugging).

## C) Jupyter and VS Code workflows

- Start notebook server: `sage -n jupyter`
- Verify kernel availability: `jupyter kernelspec list`
- If needed, install Sage kernel into existing Jupyter env via kernelspec install/symlink.

## D) Type and conversion pitfalls

- Sage integers/rationals are not always plain Python `int`/`float`.
- Convert explicitly when interacting with non-Sage libs:
  - `int(sage_integer)`
  - `bytes.fromhex(...)` after deterministic string formatting
- Beware operator differences in pure Python contexts:
  - In Python, `^` is XOR
  - In Sage-preparsed `.sage`, `^` is exponentiation

## E) Performance and debugging

- Use `%prun` in interactive mode to locate bottlenecks.
- Keep algebraic objects minimal (avoid huge ring/object recreation in loops).
- Cache repeated computed invariants (field/ring definitions, basis vectors).

## F) Agentic template (service + math split)

```python
# phase 1: collect input data (pwntools or file)
# phase 2: solve math in Sage objects
# phase 3: convert to primitive outputs (int/bytes)
# phase 4: submit answer back to service
```

This separation keeps troubleshooting straightforward and reproducible.
