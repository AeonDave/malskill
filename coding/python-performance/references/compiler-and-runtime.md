# Compiler and runtime knobs

Load after a profiled code-level fix, when you need build/runtime flags. These are not a substitute for algorithm or allocation work.

## Contents

- [Order](#order)
- [Experimental JIT (PEP 744)](#experimental-jit-pep-744)
- [Tail-call interpreter (3.14)](#tail-call-interpreter-314)
- [PGO / official binaries](#pgo--official-binaries)
- [Free-threaded vs JIT](#free-threaded-vs-jit)

## Order

1. Measure (`profiling.md`).
2. Fix code (algorithm, I/O, allocations, parallelism in `gil-and-parallelism.md`).
3. Then consider a different **build** (free-threaded) or **experimental** interpreter features.

## Experimental JIT (PEP 744)

Still **experimental** in 3.14. Not recommended for production.

- Official **macOS and Windows 3.14** binaries include the JIT **disabled**. Enable with `PYTHON_JIT=1`.
- Source builds: `--enable-experimental-jit=yes-off` (build it, default off; `PYTHON_JIT=1` to enable) or `yes` (on unless `PYTHON_JIT=0`).
- Impact: about **10% slower to 20% faster** depending on workload. Measure; do not assume a win.
- Introspection (documented private): `sys._jit.is_available()`, `sys._jit.is_enabled()`.
- `gdb` / `perf` cannot unwind JIT frames. `pdb` / `profile` still work.
- **Free-threaded builds do not support JIT.**

3.13: JIT exists only if compiled with `--enable-experimental-jit`; disabled by default; modest gains.

## Tail-call interpreter (3.14)

Opt-in CPython implementation: `--with-tail-call-interp`. Clang 19+ on x86-64 and AArch64. Reported ~3–5% on `pyperformance` vs 3.14+Clang19 without it. **Not** tail-call optimization of Python functions. Enable PGO if you use it. Skip unless you control the build.

## PGO / official binaries

Use the official binary or a PGO build before chasing interpreter flags. `--enable-optimizations` is the usual source-build PGO path. Don't compare a debug build to a release binary.

## Free-threaded vs JIT

| Knob | Default 3.14 | Production? |
|---|---|---|
| GIL-enabled interpreter | yes | yes |
| Free-threaded (`python3.14t`) | optional install | supported, optional; measure |
| `PYTHON_JIT=1` | off | experimental |
| Tail-call interp | off | opt-in build |

## References

- https://docs.python.org/3/whatsnew/3.14.html
- https://docs.python.org/3/whatsnew/3.13.html
- https://docs.python.org/3/using/configure.html
- https://peps.python.org/pep-0744/
