# Linux Security Modules internals

Load when interacting with Linux Security Modules architecture, hook placement, and policy enforcement.

LSM is a kernel hook framework enabling pluggable security decisions and security metadata attachment. It is infrastructure, not a single policy engine.

Typical consumers include major MAC systems and smaller behavior-focused modules.

## Hook and blob architecture

LSM adds hook call sites at sensitive kernel operations and security blob storage attached to kernel objects.

Common object scopes include:

- task and credential objects
- inodes, files, and superblocks
- sockets and networking structures
- IPC-related kernel objects

Hooks broadly split into:

- metadata lifecycle and propagation
- access-control decision points

## Stacking and ordering

LSM hooks are maintained per-hook in ordered lists.

Critical behavior:

- active module list and order define check evaluation order
- capability module appears first in active stack
- module order can influence composite allow and deny behavior

Operational visibility:

- `/sys/kernel/security/lsm` exposes active modules in evaluation order

## Userland-facing process attributes

Security attributes are visible through procfs attr paths and newer userspace APIs.

Examples include current and historical process security contexts and module-specific attr paths. Support varies by active module.

Do not assume a single universal attr path covers every module feature uniformly.

## Development and policy implications

A new LSM should have clearly documented protection goals and threat assumptions so code can be validated against intent.

Hook behavior is expansive; effective design requires careful choice of minimal sufficient hook surface plus explicit ordering expectations in stacked deployments.

## Common operational pitfalls

- attributing policy outcome to one module without checking full active stack order
- treating legacy proc attr paths as complete module truth in all configurations
- assuming hook availability and semantics are static across kernel versions
- forgetting that module-specific behavior can differ even when using same hook families

## Hardening and telemetry notes

- reading active LSM order is a first diagnostic step for security decision surprises
- combine LSM context inspection with capability and namespace ownership analysis for accurate permission reasoning
- policy tests should include stacked-module scenarios, not only single-module baselines

## Fast troubleshooting checklist

- read `/sys/kernel/security/lsm` and record exact order
- identify whether decision path depends on capability-first or major-module checks
- inspect relevant `/proc/self/attr` and module-specific attr paths
- verify kernel version and module feature support before assuming hook behavior
