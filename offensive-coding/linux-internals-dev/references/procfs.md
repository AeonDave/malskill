# procfs internals and interpretation

## What procfs is

`/proc` is a pseudo-filesystem exposing kernel and process state through virtual files. It includes per-process trees (`/proc/pid`) and system-wide interfaces (`/proc/sys`, `/proc/meminfo`, and more).

Most files are read-only snapshots with caveats. Some files are writable and mutate kernel behavior.

## Access control model

Many process files are permission-gated for non-self inspection.

Key points:

- self-inspection generally allowed
- reading other processes often requires ptrace-mode permissions
- `CAP_SYS_PTRACE` or `CAP_PERFMON` can be required depending on file and operation
- `/proc/pid/mem` has stronger requirements than read-only metadata files

Mount options materially change visibility:

- `hidepid=0` classic behavior
- `hidepid=1` hide sensitive entries inside other users' process dirs
- `hidepid=2` hide other users' `/proc/pid` dirs entirely
- `hidepid=4` show only ptraceable process directories
- `gid=` allows a group to bypass hidepid restrictions

## Process directory semantics

`/proc/pid` includes high-value runtime files:

- `status` structured process and capability state
- `maps`, `smaps`, `smaps_rollup` memory mappings and usage
- `fd`, `fdinfo` open descriptors and metadata
- `mountinfo` mount tree from process perspective
- `ns/*` namespace handles and identifiers

Important lifetime rule:

Open descriptors to `/proc/pid/*` do not retarget to a reused pid. Operations on dead-process proc fds generally fail with `ESRCH`.

## maps and smaps correctness caveats

`maps` and `smaps` are introspection gold, but reads are inherently racy.

Guarantees include monotonic address progression and non-overlap in output ordering. Full consistency usually requires a single read call and controlled target state.

Partial reads while mappings mutate can produce mixed-era views.

Recent kernels also introduce query-oriented interfaces for more efficient VMA retrieval in some paths.

## mountinfo as namespace truth surface

`/proc/pid/mountinfo` is often a better truth source than simplistic mount listings.

Fields encode:

- mount ID and parent relationships
- per-mount and superblock options
- propagation state such as shared and slave markers
- filesystem type and mount source details

For namespace and container analysis, mount propagation flags are frequently decisive.

## proc and namespace interaction

A procfs instance reflects the PID namespace context associated with its mount semantics.

Practical implications:

- process visibility depends on the namespace context, not just global pid existence
- multiple proc instances can present different filtered views
- mounts can pin namespace-relevant views beyond process lifetime under specific conditions

## Common analyst mistakes

- assuming `/proc` lists all host processes inside containers
- trusting `maps` and `smaps` as atomic timelines during active mutation
- ignoring hidepid and ptrace gating when process discovery appears incomplete
- parsing null-delimited proc strings without handling embedded separators correctly

## Hardening and telemetry notes

- stricter `hidepid` significantly reduces low-effort process reconnaissance
- proc metadata can still leak through alternate channels if broader permissions remain
- defensive parsers should fail safe on malformed, partial, or race-affected reads

## Fast troubleshooting checklist

- check proc mount options first
- confirm capability and ptrace context of observer
- for mapping analysis, prefer single-read snapshots and control target activity where possible
- compare `status`, `maps`, and `fdinfo` together before drawing conclusions
