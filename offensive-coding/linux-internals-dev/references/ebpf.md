# eBPF internals for reliable operation

## eBPF execution model

eBPF programs are verified bytecode loaded into kernel hooks. They operate with strict safety constraints and helper-mediated kernel interaction.

Three pillars:

- verifier acceptance before load
- map-based shared state between kernel and userland
- attach-point semantics tied to program type

## bpf syscall command families

The `bpf()` syscall drives object lifecycle and operations.

Core command groups:

- map lifecycle and element operations
- program load and attach operations
- object pin and get in bpffs
- object and link introspection by ID and fd
- batch map operations for scale

Object lifetime depends on references:

- open file descriptors
- subsystem attachments
- bpffs pins

No reference, object dies.

## Verifier mental model

Verifier safety checks include:

- control-flow validity and guaranteed termination
- register and stack initialization tracking
- pointer type and provenance tracking
- bounds, alignment, and packet-access proofs
- reference lifetime rules for helper-returned objects

Frequent rejection classes:

- uninitialized register or stack reads
- invalid pointer arithmetic or out-of-bounds access
- missing NULL-check transition from nullable pointer types
- misaligned memory access
- unreleased references from lookup helpers

Always collect verifier logs for root-cause diagnosis.

## Register and pointer state implications

Verifier tracks scalar ranges, signed and unsigned bounds, and bit-level uncertainty. Pointer states carry base type, fixed and variable offsets, and shared identity tags used for proof propagation.

Practical consequence:

A helper that may mutate packet layout can invalidate previous pointer proofs. Recompute and re-check bounds after such helpers.

## Maps: design and tradeoffs

Common map families:

- hash variants for dynamic key sets
- arrays for constant-time indexed state
- per-cpu maps for reduced contention
- program arrays for tail-call dispatch
- queue and stack maps for ordered flows
- sock and storage maps for socket and object-local state

Design concerns:

- map type dictates update and delete semantics
- max entries are hard limits and can trigger operational failures
- per-cpu maps shift synchronization cost and interpretation model

## Program attach and execution context

Program type controls:

- available helper subset
- expected context structure
- legal attach targets

Attachment methods differ by subsystem and can include socket options, perf ioctl paths, cgroup attachment, tracepoint links, and dedicated link object APIs.

## Pinning and delegation

Pinning objects in bpffs allows reuse across process lifetimes.

Operationally important:

- pinned objects can outlive the creating process
- unlinking pin paths drops filesystem references
- final deallocation requires no remaining descriptors, pins, or subsystem refs

## Privilege and policy surface

Modern kernels support finer privilege models than legacy all-powerful admin gating, but effective behavior depends on kernel version and policy settings.

Also account for:

- unprivileged BPF restrictions
- per-system toggles that can disable unprivileged use
- LSM and capability context interactions in hardened environments

## Common mistakes

- loading without verifier log buffer and guessing at failures
- forgetting reference release after socket lookup helpers
- using helper incompatible with program type or map type
- assuming map updates are atomic where semantics do not guarantee it
- relying on legacy privilege assumptions across mixed kernel fleets

## Fast troubleshooting checklist

- classify verifier failure class first, then inspect affected instruction path
- validate helper and map compatibility for selected program type
- verify attach target expectations and link lifecycle
- audit object references to explain unexpected persistence or disappearance
- confirm effective privilege and unprivileged policy settings
