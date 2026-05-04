# Source Coverage

This dedicated skill fills the blockchain/Web3 gap in the private challenge-solving collection.

## Local and imported coverage used

- Preserved Web3 source material: wallet nonce authentication, instance factories, EIP-1967 proxy slots, ABI coder v1/v2 dirty address behavior, Solidity metadata stripping, overlapping calldata, bytes32 encoding, delegatecall storage abuse, Groth16 proof/replay issues, market state bugs, transient storage compiler bug class, reentrancy, and Foundry `cast`/`forge` usage.
- Imported smart-contract analysis guidance: Slither, Mythril, solc compiler matching, SWC-style vulnerability classes, static analysis, symbolic execution, and audit report structure.
- Repository methodology skills: `web-exploit-technique`, `vuln-exploit-technique`, `fuzzing-technique`, `crypto-technique`, `reversing-technique`, and `coding/python-patterns`.
- External research synthesis: generic Web3 challenge workflows, tool families, validation signals, and pitfalls.

## Coverage checklist

- [x] Solidity, Vyper, ABI, bytecode, deployed addresses, RPC endpoints
- [x] Frontend wallet auth and nonce signing flows
- [x] Factory and per-instance patterns
- [x] Proxy, delegatecall, and raw storage analysis
- [x] Calldata, ABI, selector, and dirty-address quirks
- [x] Reentrancy and callback bugs
- [x] Access control and upgradeability bugs
- [x] Accounting, forced ETH, and market/governance state machines
- [x] Signature replay, domain separator, and nonce issues
- [x] ZK verifier and nullifier mistakes
- [x] Compiler/metadata/via-IR edge cases
- [x] Slither, Mythril, solc, Foundry, Echidna, ethers.js, and web3.py routing
- [x] Bitcoin/UTXO transaction tracing and peel-chain heuristics
- [x] Account-chain transaction graph tracing, internal transfers, amount/timing correlation, and explorer API workflow

## Explicit non-goals

- No live third-party exploitation guidance outside authorized lab or testnet scope.
- No challenge names, competition/platform branding, real private keys, or workstation-specific paths.
- No duplicate full tool manuals; detailed syntax belongs in tool-specific skills and official docs.
