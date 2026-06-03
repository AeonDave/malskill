---
name: foundry-cast
description: "Auth/lab ref: command-line utility for interacting with Ethereum-compatible chains."
compatibility: "Linux, macOS, Windows; Foundry installed; RPC access required."
metadata:
  author: AeonDave
  version: "1.0"
---

# Foundry cast

CLI Swiss Army knife for Ethereum and EVM chains.

## When to use cast

Use cast when you need to:

- perform read-only calls against contracts
- inspect balances, storage slots, code, receipts, or block data
- encode or decode ABI data quickly from the shell
- send a controlled transaction in an authorized lab

## Quick Start

```bash
# Balance lookup
cast balance 0x0000000000000000000000000000000000000000 --rpc-url https://rpc.example

# Read-only contract call
cast call 0xContract "owner()(address)" --rpc-url https://rpc.example

# Inspect storage slot 0
cast storage 0xContract 0 --rpc-url https://rpc.example
```

## High-Value Workflows

### ABI helpers

```bash
cast calldata "transfer(address,uint256)" 0x1111111111111111111111111111111111111111 1000000000000000000
cast abi-decode "(uint256,address)" 0x0000000000000000000000000000000000000000000000000000000000000042
```

### Chain and code inspection

```bash
cast block-number --rpc-url https://rpc.example
cast code 0xContract --rpc-url https://rpc.example
cast receipt 0xTxHash --rpc-url https://rpc.example
cast rpc eth_chainId --rpc-url https://rpc.example
```

### Controlled state-changing transaction

```bash
cast send 0xContract "setValue(uint256)" 1 --rpc-url https://rpc.example --private-key 0xYOURKEY
```

## Practical Notes

- Prefer `call` first; it answers a surprising amount before you risk a transaction.
- `storage` is excellent for proxy, slot, and state-layout triage.
- Pair with `solc` for compilation context and `slither` or `mythril` for deeper security review.

## Caveats

- RPC and chain selection matter; wrong endpoint means wrong truth.
- `send` signs and broadcasts a transaction, so treat it as a deliberate action.
- ABI decoding is only as good as the signature or tuple you provide.

## Resources

No bundled `scripts/`, `references/`, or `assets/`.
Use the current Foundry cast reference for subcommand-specific flags and aliases.
