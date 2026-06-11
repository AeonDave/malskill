# Linux namespaces: mechanics that matter

Load when navigating or interacting with Linux namespace isolation and transition constraints.

Namespaces isolate global resources into scoped views. A process belongs to one namespace instance of each namespace type.

Core types and examples:

- mount namespace for mount points
- PID namespace for process ID space
- user namespace for uid and gid mapping and capability scope
- network namespace for interfaces and routing stack
- IPC, UTS, cgroup, and time namespaces for their respective domains

## Primary APIs

- `clone` and `clone3` create child with selected new namespaces
- `unshare` creates new namespace context for caller or caller's future children depending on type
- `setns` re-associates with existing namespace handles
- namespace handles are exposed via `/proc/pid/ns/*`

## User namespace is special

User namespaces redefine capability context.

Important properties:

- unprivileged creation became possible on modern kernels
- process can be uid 0 inside user namespace while unprivileged outside it
- ownership of non-user namespaces is tied to a user namespace and controls permission checks

Mapping files (`uid_map`, `gid_map`, optional project maps) are central and tightly constrained.

`gid_map` updates often require handling of `/proc/pid/setgroups` state, including deny-before-map patterns.

## PID namespace semantics

- first child in new PID namespace becomes PID 1 and init-like reaper
- if namespace init exits, remaining processes are killed and namespace becomes nonviable for new forks
- processes can descend into child PID namespaces but cannot enter ancestor PID namespaces
- `setns` with PID namespace affects where **future children** appear, not caller's own PID identity

## setns constraints and capability context

`setns` requires careful capability checks in both current and target owning user namespaces.

Common constraints:

- multithreaded callers cannot switch certain namespace types such as user namespace
- shared fs attributes (`CLONE_FS`) can block user or mount namespace changes
- PID reassociation is descendant-only

With pidfd-based `setns`, multiple namespace moves can be requested atomically through a flag mask.

## Namespace lifetime and pinning

A namespace can outlive member processes when pinned by:

- open namespace file descriptors
- bind mounts of namespace links
- hierarchical child namespace relationships
- ownership relationships from user namespace to child non-user namespaces

This is crucial for both persistence and forensic interpretation.

## Limits and failure modes

Per-user and per-namespace limits can force `clone` or `unshare` failures, typically with `ENOSPC` on modern kernels.

Distro and kernel settings under `/proc/sys/user` influence practical namespace creation ceilings.

## Container boundary implications

- creating user plus other namespaces in one flow changes privilege assumptions dramatically
- capability checks must be reasoned in owning user namespace context
- mount and pid namespace visibility via proc depends on mount origin and namespace association

## Common mistakes

- treating uid 0 inside user namespace as host-global root
- expecting caller PID to change after PID `setns` or `unshare`
- assuming namespace death when last visible process exits without checking pinning factors
- forgetting that ownership user namespace drives many non-user namespace permission decisions

## Fast troubleshooting checklist

- inspect `/proc/pid/ns/*` inode identity and target ownership relations
- confirm capability context in both current and target owning user namespaces
- verify thread model and `CLONE_FS` sharing constraints before `setns`
- for PID flows, track caller identity and child placement separately
