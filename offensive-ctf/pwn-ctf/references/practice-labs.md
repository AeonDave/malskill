# Practice labs for pwn workflows

Use this reference when a pwn task is also a training or study-path question. Keep it high level: this file routes practice work to the right local references and records lab ethics, but it must not contain challenge-specific solutions.

## Scope

- Use pwn.college as a hands-on practice environment for terminal fluency, program security, system security, and software exploitation.
- Use local references for technique details: `overflow.md`, `rop.md`, `format-string.md`, `heap.md`, `heap-fsop.md`, `relro-aslr-relocations.md`, `sandbox.md`, `kernel.md`, `exotic-arch.md`, and `windows-pwn.md`.
- For heap-specific allocator/version work, cross-load `offensive-coding/heap-exploitation-dev` and treat how2heap as the executable compatibility corpus.

## Lab ethics

pwn.college states that its challenges are educational material used for grading, and asks participants not to publish writeups, walkthrough videos, livestreams, or challenge solutions. Follow that constraint when using this skill:

- Do not include challenge-specific flags, solution transcripts, or step-by-step answers in generated notes.
- Keep reports generic unless the user explicitly asks for private study notes and the scope is authorized.
- Prefer explaining the underlying primitive and how to reproduce it on a local toy binary.
- If a public answer would solve an active lab directly, downgrade to hints, validation strategy, or reference routing.

## Practice routing

| Practice signal | Load first | Then load when needed |
|---|---|---|
| terminal, files, process basics | `field-notes.md` | `sandbox.md` for restricted shell/process pivots |
| stack memory errors | `overflow.md` | `rop.md`, `relro-aslr-relocations.md` |
| format string primitives | `format-string.md` | `relro-aslr-relocations.md`, `advanced-primitives.md` |
| ROP, SROP, shellcode, syscall constraints | `rop.md` | `sandbox.md`, `exotic-arch.md` |
| heap bugs and allocator behavior | `heap.md` | `heap-fsop.md`, `offensive-coding/heap-exploitation-dev` |
| modern glibc post-hook exploitation | `heap-fsop.md` | `offensive-coding/fsop-dev`, `relro-aslr-relocations.md` |
| seccomp or filesystem constraints | `sandbox.md` | `rop.md`, `kernel.md` |
| architecture-specific labs | `exotic-arch.md` | `coding/asm-patterns`, `coding/asm-testing` |
| Windows exploitation practice | `windows-pwn.md` | `rop.md`, Windows-specific debugging/tool skills |

## Study loop

1. Reproduce the bug locally and name the primitive in one sentence.
2. Load the closest reference and extract only the constraints that match the binary.
3. Build a tiny local proof for the primitive before solving the full lab.
4. Keep a pivot ledger: hypothesis, check, result, next shortest path.
5. Record final learning as a generic primitive pattern, not as a challenge walkthrough.

## Research trail

- pwn.college home page and rules: hands-on cybersecurity education platform, maintained by the ASU team, with an explicit request not to publish challenge solutions.
- pwn.college dojos page: material is grouped into ordered practice areas, including getting-started material and core program/system/software exploitation tracks.
