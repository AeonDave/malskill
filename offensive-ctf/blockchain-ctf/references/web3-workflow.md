# Web3 Workflow

Use this reference when `blockchain-ctf` is active and the task needs deeper smart-contract analysis or transaction orchestration.

## Intake checklist

Collect these before deciding exploit path:

- chain ID and RPC endpoint
- funded account and signer format
- target addresses and deployment transaction hashes
- source, ABI, bytecode, compiler version, optimizer settings, and via-IR status
- factory, player instance, proxy, implementation, and library addresses
- frontend bundle, auth nonce/signature flow, and checker endpoint if present
- success oracle: public function, event, balance target, storage value, or external checker

## Contract graph workflow

1. Identify every contract role: factory, challenge instance, token, vault, oracle, governance, verifier, proxy, implementation, library, helper.
2. Check whether calls reach the target directly or through fallback/proxy dispatch.
3. Resolve implementation and admin slots for EIP-1967-style proxies:
   - implementation slot: `0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc`
   - admin slot: `0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103`
4. Build storage map: packed fields, mappings, dynamic arrays, inherited layouts, and delegatecall storage context.
5. Compare source and deployed bytecode. Strip compiler metadata when codehash checks ignore metadata.

## Static and dynamic analysis ladder

- Source available: compile with matching `solc`, inspect storage layout, run Slither, then write Foundry tests for suspicious paths.
- Bytecode only: recover selectors, decompile, inspect metadata, trace transactions, and query raw storage.
- State-machine target: fuzz with Foundry/Echidna invariants before hand-writing long exploit chains.
- Path-sensitive bug: use Mythril or symbolic checks for reachability, then verify manually with a focused test.
- Frontend-gated task: inspect bundle for addresses, chain ID, nonce/signature format, and lowercase/checksum expectations.

## High-value patterns

### Proxy and delegatecall

- Unprotected `upgradeTo`, `setImplementation`, `setGovernance`, or library setters can redirect execution.
- Delegatecall writes into caller storage; attacker contract storage layout must match the target slots that matter.
- `address(this)` inside implementation code is the proxy during delegatecall.

### Calldata and ABI

- Empty revert data can indicate ABI decoder validation rather than target logic.
- ABI coder v1 can accept dirty high bytes for address-like values; ABI coder v2 validates them.
- Dynamic offsets can overlap when contracts enforce unusual calldata lengths or parse manually.
- Function selectors and fallback dispatch can hide privileged paths.

### Accounting and forced value

- Native currency can be forced into a contract through selfdestruct-style transfers or pre-funded deployment mechanics.
- Check whether accounting uses `address(this).balance` or internal balances.
- Rounding and share calculations often fail near zero, one wei, or very large values.
- Unchecked low-level calls can silently fail and leave state inconsistent.
- ERC-4626 vaults: attacker mints 1 share, `asset.transfer`s a large donation to inflate `pricePerShare`, next depositor rounds down to 0 shares. Check for OpenZeppelin `_decimalsOffset()` or virtual-shares defense; without it the first-depositor pattern is exploitable.

### Smart accounts and delegation

- ERC-4337: entrypoint calls `validateUserOp` on the account and `validatePaymasterUserOp` on the paymaster before execution. Trust boundary is that pair — replay, missing sig-hash chaining, wildcard callers, or accepting unbounded gas from a paymaster are all account bugs, not bundler bugs.
- ERC-4337 simulation gap: bundlers enforce storage/opcode rules only during simulation; a permissive or self-hosted bundler can include ops that read state banned by ERC-7562 rules, so accounts must not trust the simulated environment.
- EIP-7702 (Pectra, May 2025): a signed authorization tuple sets EOA code to the designator `0xef0100 || <delegate>`. Delegation persists until the EOA signs a new tuple or delegates to the zero address.
- 7702 init-frontrun: if the delegate contract has a public `init()` that grants ownership on first call, an observer of the mempool can front-run the intended init and take over the delegated EOA. Delegates must atomically bind init to the authorization signer.
- 7702 storage carryover: switching delegates does not clear the EOA's storage; a new delegate can read/misinterpret slots written by the previous one.

### Governance, markets, and ZK

- Confirm entity existence checks before betting, voting, resolving, or executing proposals.
- State reset functions may leave old totals, nullifiers, or votes intact.
- Groth16 verifier mistakes include reused setup parameters, unconstrained public inputs, replayable proofs, and missing nullifier tracking.

### Compiler and bytecode edge cases

- Check compiler version and optimizer/via-IR flags before trusting source-level assumptions.
- EIP-1153 transient storage (`tstore`/`tload`) is cleared at transaction boundaries; safe as a same-tx reentrancy lock, unsafe if used to persist state across calls that end the tx or across a fork/snapshot boundary in tests.
- Metadata length is stored at the end of Solidity bytecode; strip it only when the target logic does the same.

## Exploit construction workflow

1. Write the exploit as a transaction sequence, not prose.
2. Reproduce on a local fork or local deployment.
3. Log before/after state: relevant storage slots, balances, roles, and events.
4. Minimize transactions: remove probes that are not required for final proof.
5. Broadcast only after target address, chain ID, value, sender, gas, and expected state diff are checked.
6. Verify with the success oracle and save receipts/calldata.

## Validation signals

- success oracle returns true or emits a target event
- expected storage slot changes to the attacker/player value
- balance or token accounting reaches the required state
- privileged role changes as predicted
- transaction trace reaches the vulnerable branch
- frontend checker returns recovered secret after on-chain state changes

## Common pitfalls

- Calling implementation directly when the state lives in the proxy.
- Forgetting chain ID or domain separator in signatures.
- Assuming token standards are compliant.
- Ignoring gas and value constraints that differ between local tests and the target chain.
- Running Slither/Mythril without matching compiler setup and then trusting false positives or false negatives.
- Broadcasting exploratory transactions instead of proving locally first.
