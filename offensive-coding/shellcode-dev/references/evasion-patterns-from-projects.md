# Evasion Patterns Extracted from Real Projects (Shellcode-Dev Scope)

This note captures implementation patterns that are directly relevant to shellcode development and loader reliability.

## 1) Indirect syscall gate with runtime SSN mapping

Observed pattern:
- enumerate `Zw*` exports from `ntdll`
- sort stubs by virtual address
- derive SSN from sorted index
- resolve `Nt*` requests via address/hash reconciliation (not static syscall IDs)

Why it matters for shellcode-dev:
- reduces OS-build fragility versus hardcoded SSNs
- keeps syscall dispatch reusable across loaders/stagers

Shellcode-dev guidance:
- keep one deterministic SSN resolver module
- treat static SSN tables as research-only artifacts
- regression-test resolver against target build set before release

---

## 2) Recycled gadget selection (`syscall; ret`) with per-build variance

Observed pattern:
- collect many candidate `Nt*` stubs
- shuffle candidates with seed-dependent order
- pick first valid `syscall;ret` sequence

Why it matters for shellcode-dev:
- avoids pinning a single gadget offset
- improves portability and resilience when one candidate is unavailable

Shellcode-dev guidance:
- maintain candidate scan + validation logic as a separate gate phase
- ensure clean fallback path when no valid gadget is found
- store only the selected address at runtime, never as a compile-time constant

---

## 3) DESYNC-style stack spoof prerequisites are strict ABI constraints

Observed pattern:
- stack-spoof mode depends on unwind-aware frame selection
- gadget quality checks include call-preceded constraints and frame-size thresholds
- donor module cascade is used when first-choice module lacks required gadgets

Why it matters for shellcode-dev:
- this is primarily a calling-contract problem, not just “find gadget then call”
- incorrect frame assumptions break reliability before any evasion benefit appears

Shellcode-dev guidance:
- gate stack-spoof mode behind explicit readiness checks
- keep no-spoof and indirect-only modes as first-class fallbacks
- validate unwinder behavior in debugger before promoting build profiles

---

## 4) Multi-arity syscall wrappers (4/6/11 args) must preserve calling contract

Observed pattern:
- dedicated wrappers for different argument counts
- explicit handling of stack-passed arguments beyond register budget
- fallback to original `ntdll` stubs for wider signatures when needed

Why it matters for shellcode-dev:
- many loader failures are argument marshalling errors, not syscall logic errors
- wrapper correctness directly affects stability of mapping/protection/thread APIs

Shellcode-dev guidance:
- implement wrappers per arity, not one fragile variadic path
- test representative Nt APIs for each arity class
- include alignment and shadow-space checks in debugger scripts

---

## 5) Sleep masking as a staged pipeline (not a single function)

Observed pattern:
- suspend selected sibling threads
- encrypt/decrypt tracked regions around sleep
- perform delay via native path
- resume threads and rotate key
- avoid heap-walk deadlocks by encrypting tracked allocations only

Why it matters for shellcode-dev:
- sleep masking interacts with memory ownership and thread state
- naive heap/global masking can deadlock or crash stable payloads

Shellcode-dev guidance:
- prefer explicit region tracking over blind heap traversal
- separate trampoline/worker memory from regions being transformed
- keep a build-time kill-switch for fast incident isolation in test builds

---

## 6) CFG-aware registration for mid-function call targets

Observed pattern:
- when indirecting into mid-function gadgets, valid call targets are registered on relevant pages

Why it matters for shellcode-dev:
- modern mitigations can break otherwise-correct gadget chains
- mitigation-awareness is now part of loader engineering quality

Shellcode-dev guidance:
- treat mitigation registration as best-effort setup with graceful degradation
- group all dynamic gadget targets in one registration routine
- test with mitigation settings representative of target fleet

---

## 7) Module-overloading reflective loader design principles

Observed pattern:
- stage layout is explicit (`bootstrap + reflective-loader + payload`)
- reflective loader performs section overlay, relocations, import resolution, TLS callback handling
- sacrificial module candidate list with retry/fallback behavior

Why it matters for shellcode-dev:
- robust in-memory loading depends more on deterministic PE lifecycle handling than on obfuscation

Shellcode-dev guidance:
- codify stage contracts (offsets, sizes, entry transfer assumptions)
- treat candidate module lists as reliability inputs, not static constants
- keep relocation/import/TLS handling independently testable

---

## 8) Practical release profile model (recommended)

Define explicit profiles and do not mix assumptions:
- Profile A: direct/native API, no spoof
- Profile B: indirect syscall gate, no stack spoof
- Profile C: indirect syscall + stack spoof + sleep masking

Promotion rule:
- only move from A -> B -> C after each profile independently passes static, emulation, and runtime gates.

---

## 9) Dual-map section pipelines reduce noisy write/protect chains (ADE MapSection)

Observed pattern:
- create one shared section, map local RW + remote RX views
- write payload bytes locally (`memcpy`) so remote bytes update without cross-process write API usage
- unmap local view and flush remote instruction cache before trigger

Why it matters for shellcode-dev:
- decouples payload transfer from classic remote write primitives
- improves determinism of memory-permission state (no repeated RWX flips required)

Shellcode-dev guidance:
- isolate section-map logic as a reusable transport primitive
- treat instruction-cache flush as mandatory, not optional
- validate both view-lifecycle and cleanup path under debugger (map/unmap/close order)

---

## 10) Execution primitive should be configurable and independent from transfer path

Observed pattern:
- transfer path stays constant while execution trigger is selected separately (`thread`, `threadpool`, `callback`, etc.)
- same payload placement code can be reused across trigger variants

Why it matters for shellcode-dev:
- enables testing reliability by swapping only the execution primitive
- avoids coupling payload layout bugs with trigger-specific bugs

Shellcode-dev guidance:
- design loader core as: `place payload -> set permissions -> trigger`
- expose trigger strategy as explicit build/runtime config
- maintain regression tests per trigger strategy using identical payload bytes

---

## 11) Handle rights minimization + candidate fallback loops improve field reliability

Observed pattern:
- open process handles with minimal rights for each stage
- optional handle-recycling path before direct open
- candidate retry loops with bounded attempts and fast-fail for hard denial conditions

Why it matters for shellcode-dev:
- reliability issues often come from over-broad handle assumptions, not from payload logic
- bounded retry/fallback behavior prevents dead-end failures on heterogeneous hosts

Shellcode-dev guidance:
- declare required access masks per operation (open/read/write/execute)
- implement fallback chain explicitly (preferred path -> alternate path -> controlled fail)
- record reason-coded failures so triage distinguishes access failures from loader bugs

---

## 12) Stomp/overload cleanup semantics must be first-class (restore, unmap, thread state)

Observed pattern:
- optional restore mode: preserve overwritten bytes, wait for payload thread, write original bytes back, restore protection
- optional cleanup mode for phantom mappings: unmap section after completion
- thread freeze/resume windows used to avoid races during temporary overwrite phases

Why it matters for shellcode-dev:
- temporary code overlays are race-prone without explicit lifecycle control
- cleanup behavior changes forensic and runtime outcomes and must be deliberate

Shellcode-dev guidance:
- define two explicit modes: fire-and-forget vs cleanup/restore
- treat restore artifacts (saved bytes, old protections, frozen thread list) as structured state
- validate race windows with synthetic stress tests before promoting release profiles
