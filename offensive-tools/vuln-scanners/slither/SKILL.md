---
name: slither
description: "Auth/lab ref: smart contract static analyzer for Solidity and Vyper with detectors, printers, and custom analysis APIs."
license: AGPL-3.0
compatibility: "Linux, macOS, WSL; Python 3.10+; solc or framework compilation required."
metadata:
  author: AeonDave
  version: "1.0"
---

# Slither

Fast static analysis for Solidity and Vyper codebases.

## When to use Slither

Use Slither when you need to:

- run a fast first-pass audit on a smart contract repo
- catch common vulnerability classes with low friction
- generate structural views like call graphs and human summaries
- script custom contract analysis in Python

## Installation

```bash
# Recommended
uv tool install slither-analyzer

# Or pip
python3 -m pip install slither-analyzer
```

Upstream recommends `solc-select` or a supported build framework when multiple compiler versions are in play.

## Quick Start

```bash
# Preferred for real projects with imports
slither .

# Single self-contained file
slither contracts/Token.sol

# Markdown checklist report
slither . --checklist
```

## Core Workflow

### 1. Make compilation work first

If the project uses Hardhat, Foundry, Brownie, or another framework, ensure its normal compile command succeeds before blaming Slither.

Run Slither from the project root, not from an isolated contract file, when imports and dependencies exist.

### 2. Run default detectors

```bash
slither .
```

This gives broad coverage for issues like:

- reentrancy variants
- arbitrary-send patterns
- unchecked low-level calls
- weak PRNG
- `tx.origin` misuse
- dangerous upgradeability patterns
- uninitialized state or storage mistakes

### 3. Generate review-oriented outputs

```bash
slither . --checklist
slither . --print human-summary
slither . --print call-graph,cfg,function-summary
```

Use printers for comprehension, not just bug hunting.

## High-Value Uses

### CI or pre-commit gate

```bash
slither . --checklist
```

### Quick architecture review

```bash
slither . --print human-summary,inheritance-graph,entry-points
```

### Custom analysis

Use Slither's Python API when a one-off audit question is too specific for stock detectors.

## Practical Notes

- Slither is the fastest high-value first pass in many Solidity audits.
- It integrates best with the project's real build system.
- Use it early to reduce manual review surface before heavier symbolic or dynamic tooling.
- Pair with `mythril` for symbolic execution depth on suspicious paths.

## Caveats

- Static findings still require human triage.
- Compilation failures usually mean the project layout or dependencies are wrong, not necessarily a Slither bug.
- Single-file runs are convenient but weaker for real projects with imports.

## Resources

No bundled `scripts/`, `references/`, or `assets/`.
Use the upstream detector and printer documentation for the full detector list and tuning options.
