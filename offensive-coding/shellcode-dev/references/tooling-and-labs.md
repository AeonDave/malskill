# Tooling and Labs

## pwntools (Python)

Use pwntools for rapid generation/harnessing, especially when iterating stagers and architecture variants.

Typical usage areas:
- shellcraft templates for baseline payloads
- byte assembly/disassembly loops
- controlled transport tests for staged loaders

Practical rule: keep generated payload bytes versioned per test case so crashes can be reproduced exactly.

---

## Capstone + Keystone + Unicorn loop

Use the trio as a deterministic lab loop:

1. Keystone: assemble candidate snippets quickly
2. Capstone: disassemble and verify final byte stream
3. Unicorn: emulate execution and inspect register/memory transitions

This reduces expensive runtime-debug cycles by catching ABI and control-flow mistakes early.

### What to assert in emulation

- entry register assumptions are met
- stack remains aligned at call/syscall boundaries
- decoder/stager loop terminates correctly
- memory writes stay in expected region
- transfer-of-control lands at intended decoded payload start

---

## Debugger loop

### Windows

- prefer WinDbg/x64dbg for runtime truth
- verify stack frame shape around transition call
- inspect return address lineage when call-stack-sensitive techniques are enabled

### Linux/macOS

- pair debugger with syscall visibility (`strace`-style or platform equivalent)
- verify `mmap/mprotect` arguments and return values
- validate boundary cases (small/large staged payloads)

---

## Harness design

A robust harness keeps these phases separable:

- `generate`: produce byte payload
- `inspect`: static decode/disasm checks
- `emulate`: deterministic behavioral checks
- `execute`: runtime integration test

Never combine all logic into one opaque script. Separation keeps regressions local and debuggable.

---

## Recommended source set

- pwntools documentation: https://docs.pwntools.com/
- Capstone project/docs: https://github.com/capstone-engine/capstone and https://www.capstone-engine.org/documentation.html
- Keystone project/docs: https://github.com/keystone-engine/keystone and docs/COMPILE.md
- Unicorn project/docs: https://github.com/unicorn-engine/unicorn and docs/COMPILE.md
