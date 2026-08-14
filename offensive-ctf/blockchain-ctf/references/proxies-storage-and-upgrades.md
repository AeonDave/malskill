# Proxies, Storage, and Upgrade Pitfalls

Load when the target uses a proxy, `delegatecall`, upgrade logic, or storage behavior that does not match the source you are reading.

## Recognition checklist

Look for these first:

- EIP-1967 slots in storage
- proxy admin / implementation slot reads
- `delegatecall` in fallback or dispatcher code
- `upgradeTo`, `upgradeToAndCall`, `initialize`, `reinitialize`
- source that does not match deployed behavior
- state living at a proxy address while code lives elsewhere

## EIP-1967 quick slots

Common slots to inspect:

- implementation: `0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc`
- admin: `0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103`

Read them before assuming which contract actually owns state.

## Core model

`delegatecall` executes implementation code against the proxy's storage.

Implications:

- the proxy keeps state
- constructors on the implementation do not initialize proxy state
- reading the implementation directly can hide the real bug if the proxy holds the values that matter
- storage layout mismatches become logic bugs, not just cosmetic drift

## High-value bug classes

### Uninitialized proxy or implementation

Check whether:

- the proxy was initialized exactly once
- the implementation disables initializers or is otherwise locked
- an `initialize()` path can still be called through the proxy

Proof pattern:

1. confirm current owner/guardian/admin state
2. attempt the initializer in local reproduction
3. show role or implementation change after the call

### Re-initialization

Look for:

- `initializeV2` or `reinitializer` patterns
- version flags reset during upgrade
- inherited initializer state that moved or was overwritten

### Storage collision / storage layout mismatch

Common causes:

- inserting or removing variables in the middle of the layout
- changing inheritance order
- putting proxy variables in ordinary low slots
- reusing old slots with new meanings

Proof pattern:

1. map old and new storage layout
2. identify the conflicting slot
3. show the security check or state variable that is now misread
4. prove impact on a local fork or deterministic test

### Unauthorized upgrades

Check:

- who can call the upgrade path
- whether admin lives in a single EOA
- whether `_authorizeUpgrade` or similar gates are reachable or bypassed
- whether the implementation can be swapped to arbitrary attacker code

### Dangerous `delegatecall` or `selfdestruct`

Treat as priority issues when they are user-controlled or reachable through upgrade logic.

### Metamorphic contracts (CREATE2 code swap at a fixed address)

A metamorphic address is `CREATE2(factory, salt, keccak(initcode))` where the initcode fetches its runtime from the factory at deploy time (classic stub: `5f5f5f5f335afa3d5f5f3e3d5ff3` — `STATICCALL` the caller, return whatever it hands back). The address therefore depends on `salt` only, **not** on the runtime — so the same address can host different code across deployments while every contract that stored it keeps trusting it.

Check three things:
- **Is `deploy(salt, runtime)` access-controlled?** These factories are frequently `external` with no owner check, so anyone can occupy any free metamorphic address.
- **Can the resident code be removed?** Redeploying requires an empty account: a `SELFDESTRUCT` in the runtime (still erases code pre-Cancun; on Cancun+ only within the same transaction as creation), or any harness that rolls chain state back past the deployment block.
- **Who still points at it?** A downgrade is only useful if a privileged consumer stored the address — e.g. a vault holding `antiFraud`/`oracle`/`validator`. Replacing a policy check with a permissive stub removes the control without touching the consumer.

Minimal always-true runtime for a `bool`-returning guard: `60015f5260205ff3` (8 bytes) — stores 1, returns 32 bytes. Enough to satisfy Solidity's `extcodesize` check and decode as `true`.

### Rollback harnesses as an attack surface

A challenge or test rig that exposes a reorg/snapshot/restore endpoint rewinds **more than balances**. Enumerate what it resets: consumed-nonce and used-leaf maps (replay), metamorphic code (downgrade above), and any *off-chain* signer counter. Rolling back a stateful signature scheme's counter re-uses a one-time key — see `../../crypto-ctf/references/exotic-crypto.md` for the WOTS+/XMSS forgery that follows, and `../../crypto-ctf/references/ecc-attacks.md` if the same endpoint leaks nonce structure.

## Minimal inspection workflow

1. Identify whether the address under test is proxy, implementation, or factory product.
2. Read implementation and admin slots.
3. Compare source, ABI, and deployed bytecode.
4. Inspect initialization and upgrade paths.
5. Confirm storage layout and slot ownership.
6. Build the smallest local proof that changes the success oracle.

## Pitfalls

- calling the implementation directly and assuming that proves anything about proxy state
- treating EIP-1967 as an auth model; it only standardizes slot locations
- forgetting that initializer mistakes can brick or seize the proxy without touching business logic
- using `vm.store` or raw slot writes before you understand the actual layout
