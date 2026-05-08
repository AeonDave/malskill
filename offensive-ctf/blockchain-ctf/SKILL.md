---
name: blockchain-ctf
description: "Challenge-solving methodology for blockchain, Web3 smart-contract, and on-chain transaction-forensics lab tasks. Use when artifacts involve Solidity, Vyper, EVM bytecode, ABI files, deployed addresses, RPC endpoints, transaction traces, Bitcoin or UTXO transaction IDs, wallet signatures, factory instances, proxies, delegatecall, storage slots, calldata, reentrancy, oracle or governance logic, ZK verifier contracts, token standards, Foundry, Hardhat, cast, forge, Slither, Mythril, Echidna, ethers.js, or web3.py."
license: MIT
compatibility: "AgentSkills-compatible agents; local artifacts; authorized isolated lab and testnet environments."
metadata:
  author: AeonDave
  version: "1.0"
  category: ctf-solving
---

# Blockchain CTF

Solve blockchain and Web3 lab tasks by treating source, bytecode, storage, transactions, and contract state as one evidence graph, then proving the shortest exploit sequence on a local fork or authorized testnet.

## When this skill applies

- Solidity, Vyper, EVM bytecode, ABI, deployed address lists, RPC URLs, transaction hashes, UTXO transaction IDs, event logs, contract frontends, or wallet-signature flows.
- Blockchain-forensics tasks involving peel chains, mixer-like fan-out/fan-in, transaction graph reconstruction, explorer APIs, account/UTXO flow tracing, internal transactions, or address clustering clues.
- Smart-contract patterns: proxy, factory, upgradeable implementation, delegatecall, low-level call, reentrancy, selfdestruct, storage collision, signature replay, oracle manipulation, governance, betting/market state, token accounting, calldata tricks, or ZK verifier logic.
- Tool cues: Foundry, Hardhat, cast, forge, anvil, solc, Slither, Mythril, Echidna, ethers.js, web3.py, blockchain explorer, or local fork.

## Operating model

1. Collect chain context: network, chain ID when applicable, explorer/API path, accounts, transaction IDs, target addresses, ABI/source/bytecode if present, frontend bundle, factory/instance mapping, and success oracle.
2. Reconstruct contract graph: factory, proxy, implementation, libraries, token contracts, oracle contracts, verifier contracts, and privileged roles.
3. Inspect storage and calldata: EIP-1967 slots, packed variables, mappings, array slots, ABI coder assumptions, function selectors, and custom encodings.
4. For transaction-forensics tasks, reconstruct value flow before exploit logic: inputs, outputs, internal transfers, timing, amount correlation, change outputs, and likely peel-chain hops.
5. Run static and symbolic checks only after compiler version and source/bytecode match are known.
6. Build a local proof first when possible: anvil fork, Foundry test, Hardhat script, deterministic web3.py/ethers.js sequence, or read-only explorer trace.
7. Execute the minimal authorized transaction sequence and validate by event logs, storage diff, balance changes, returned flag, transaction graph endpoint, or `isSolved`-style oracle.

## Technique integration

Load these when the adjacent domain appears:

- `web-exploit-technique` for Web3 frontends, auth nonces, wallet login flows, APIs, SSRF, or browser-admin interactions.
- `vuln-exploit-technique` for exploit-chain discipline and primitive-to-impact reasoning.
- `fuzzing-technique` for Echidna, Foundry fuzz, invariant testing, and state-machine exploration.
- `crypto-technique` for signatures, ECDSA nonce issues, ZK proof mistakes, commitments, and randomness.
- `reversing-technique` for bytecode-only targets, decompilation, metadata stripping, and function selector recovery.
- `coding/python-patterns` for web3.py scripts and reproducible transaction orchestration.

## Tool routing

- Foundry: `cast call`, `cast send`, `cast storage`, `cast calldata`, `cast sig`, `forge test`, `forge create`, `anvil` forks.
- Solidity toolchain: `solc`, `solc-select`, compiler metadata, Yul IR output, storage layout, and ABI generation.
- Static and symbolic analysis: Slither for detectors and summaries, Mythril for path-sensitive issues, solc SMTChecker when source is available.
- Fuzzing: Foundry fuzz/invariants and Echidna for stateful bugs, accounting violations, and unexpected reachability.
- Automation: ethers.js, web3.py, Brownie-style scripts, RPC JSON calls, explorer APIs, and transaction receipt parsing.
- Bytecode and storage: decompilers, selector databases, raw `eth_getStorageAt`, traces, debug RPC, and event topic decoding.
- Transaction forensics: mempool.space-compatible APIs, Blockchair-style multi-chain explorers, Etherscan-compatible account/internal transaction APIs, CSV/JSON graphing, and Python networkx/pandas when a graph must be reconstructed.

## Vulnerability checklist

- Access control: owner/admin/initializer/setter exposure, unprotected upgrade, tx.origin, role confusion.
- Reentrancy and callbacks: external calls before effects, token hooks, receive/fallback recursion, cross-function reentry.
- Proxy/delegatecall: EIP-1967 slots, storage layout mismatch, controlled implementation, controlled delegatecall target.
- Accounting: rounding, precision, rebasing, share/asset mismatch, unchecked return values, forced ETH, selfdestruct transfers.
- Oracle and market logic: stale price, spot-price manipulation, phantom IDs, unresolved state, missing existence checks.
- Signature and auth: replay, missing chain ID/domain separator, malleability, dirty address, unchecked signer, nonce reuse.
- Calldata and ABI: overlapping dynamic offsets, short calldata, custom fallback dispatch, ABI coder v1/v2 differences.
- Compiler/bytecode: metadata stripping, optimizer/via-IR bugs, transient storage issues, version-specific behavior.
- ZK/governance: trusted setup equality mistakes, public input mismatch, replayed proofs, missing nullifier tracking.

## Safety and scope gates

- Treat mainnet-like or third-party contracts as read-only unless the user explicitly provides authorized lab/testnet scope.
- Never send value-bearing transactions without confirming target, chain ID, sender, value, and expected state diff.
- Prefer local fork reproduction before any broadcast.
- Stop after the success oracle is proven; do not drain extra funds or continue state manipulation.
- Record exact transaction sequence, calldata, storage observations, and validation output.

## Resources

- `references/web3-workflow.md` — detailed smart-contract triage, storage, tooling, exploit, and validation workflow.
- `references/transaction-forensics.md` — read-only Bitcoin/UTXO and account-chain transaction tracing workflow.
