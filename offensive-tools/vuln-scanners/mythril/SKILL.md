---
name: mythril
description: "Auth/lab ref: symbolic-execution-based security analyzer for Solidity and EVM bytecode."
license: MIT
compatibility: "Linux, macOS, WSL."
metadata:
  author: AeonDave
  version: "1.0"
---

# Mythril

Symbolic execution for smart contract vulnerability discovery.

## When to use Mythril

Use Mythril when you want to:

- explore vulnerable transaction sequences, not just static patterns
- analyze a Solidity file or deployed address for reachable issues
- get SWC-tagged findings with traces and state setup
- confirm whether a suspicious path is symbolically reachable

Use `slither` for fast repo-wide triage. Use Mythril for deeper path exploration.

## Installation

```bash
# Docker (upstream-recommended simple path)
docker pull mythril/myth

# Classic pip path
pip3 install mythril
```

## Quick Start

```bash
# Analyze Solidity source
myth analyze Contract.sol

# Analyze deployed contract by address
myth analyze -a 0xDEADBEEF...

# Limit transaction depth
myth analyze Contract.sol -t 3
```

## Core Workflow

### 1. Run a bounded analysis

```bash
myth analyze Contract.sol -t 3 --execution-timeout 60
```

Use bounded depth and timeout early to avoid wasting cycles on state explosion.

### 2. Read findings as execution stories

Upstream output includes:

- issue title and severity
- SWC identifier
- function name and program counter
- vulnerable source location
- transaction sequence and caller chain

That trace is the real value: it shows *how* a condition can be reached.

### 3. Re-run with tighter scope when needed

If output is noisy or slow, reduce transaction depth or compare only the contract under active review.

## Good Use Cases

- validating suspicious payable/destruct logic
- sanity-checking selfdestruct, auth, and call-chain issues
- triaging high-risk paths after a `slither` pass
- reviewing deployed contracts when source is limited but address is known

## Practical Notes

- Mythril is slower and deeper than Slither; do not start there for every repo.
- Docker is often the least painful install path.
- Combine symbolic findings with manual contract review and test reproduction.
- Use SWC IDs as starting taxonomy, not as the whole remediation story.

## Caveats

- Symbolic execution can hit path explosion or timeouts quickly.
- Not every reported issue is exploitable in production context.
- Tooling around compiler/runtime versions still matters; mismatches can distort results.

## Resources

No bundled `scripts/`, `references/`, or `assets/`.
Use upstream docs for installation edge cases, command variants, and remediation links via the SWC registry.
