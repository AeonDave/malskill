# Foundry Forks, Traces, and Minimal Proofs

Load when you need a local proof on a fork or test deployment and want the shortest reproducible transaction sequence.

## Fork-first workflow

1. Pin the RPC endpoint and block number.
2. Reproduce the state locally before writing exploit logic.
3. Build one test that proves the primitive.
4. Expand only after the primitive is stable.

Why pin the block:

- balances, prices, and roles stay stable
- traces remain comparable across reruns
- failures are easier to attribute to the exploit logic instead of state drift

## Trace workflow

Use trace verbosity intentionally:

- `-vvv` — execution traces for failing tests
- `-vvvv` — execution traces for all tests, setup traces for failing tests
- `-vvvvv` — execution and setup traces for all tests

Storage diffs are not surfaced by verbosity; use `vm.record` + `vm.accesses(addr)` in the test or `forge inspect <contract> storage-layout` to enumerate slots.

Read traces for:

- exact call hierarchy
- which branch reverted
- staticcall vs call vs delegatecall context
- storage side effects on the vulnerable path

## Cheatcodes that matter most in CTF proofs

- `vm.prank` / `vm.startPrank` — impersonate the caller that matters
- `vm.deal` — fund an address deterministically
- `vm.warp` / `vm.roll` — control time and block-based gates
- `vm.store` / raw storage reads — only after slot mapping is understood
- `vm.expectRevert` / `vm.expectEmit` — prove exact branch or event behavior
- fork cheatcodes — create/select forks when the challenge depends on live state
- snapshots — roll state back while preserving the same setup cost

## Minimal proof pattern

1. Read the initial oracle state.
2. Apply the smallest transaction sequence that should change it.
3. Assert on the state diff, event, balance, role, or `isSolved` value.
4. Remove exploratory calls that do not affect the final proof.

Good proof targets:

- a single storage slot changes to attacker/player state
- a role or admin value flips
- the vulnerable branch becomes reachable
- a balance or accounting invariant breaks in one deterministic sequence

## Fuzz and symbolic support

Use fuzzing only after the deterministic proof works.

Good uses:

- exploring edge-case calldata or accounting boundaries
- checking invariant drift after the core exploit is understood
- shrinking a multi-transaction state machine into a smaller proof

Do not start with fuzzing when:

- the bug is clearly a proxy/storage/initializer issue
- you still do not know the correct caller or fork block
- traces already show the exact failing guard

## Common pitfalls

- unpinned forks that make tests non-reproducible
- broadcasting before the fork proof is complete
- reading traces without checking call type or storage side effects
- using `vm.store` to force a state you do not understand
- keeping giant test harnesses when one short exploit test would prove the issue
