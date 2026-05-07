# Web3 and Blockchain Web Attacks

Use this reference for web challenges that depend on wallet auth, on-chain state, proxy contracts, calldata quirks, governance logic, or Web3 challenge infrastructure.

## Table of Contents
- [Fast triage](#fast-triage)
- [Challenge infrastructure](#challenge-infrastructure)
- [Proxy and upgrade patterns](#proxy-and-upgrade-patterns)
- [Calldata and ABI tricks](#calldata-and-abi-tricks)
- [Governance and proof systems](#governance-and-proof-systems)
- [Common operator notes](#common-operator-notes)

## Fast triage

Map four layers separately:
1. web auth layer: nonce, signature, cookie/token, account normalization
2. app layer: instance creation, challenge API, solve checker, frontend bundle leaks
3. chain layer: factory, proxy, implementation, storage layout, privileged roles
4. exploit primitive: reentrancy, upgrade abuse, delegatecall, proof replay, calldata confusion

## Challenge infrastructure

Common flow:
- fetch nonce
- sign with wallet
- exchange signature for web token
- create instance on chain
- solve contract condition
- hit check endpoint for proof/flag

Always inspect frontend bundles for:
- chain ID
- factory addresses
- API endpoints
- address formatting assumptions

## Proxy and upgrade patterns

High-yield checks:
- EIP-1967 storage slots
- unprotected upgrade or governance setters
- codehash checks that strip metadata
- delegatecall into attacker-controlled implementation with proxy storage context

## Calldata and ABI tricks

Useful patterns:
- ABI coder v1 vs v2 address validation differences
- overlapping calldata layouts
- non-standard offsets and dirty-address tricks
- `bytes32` string encoding assumptions
- crafted calldata for proxy or validator confusion

## Governance and proof systems

Look for:
- proof replay because nullifiers are never tracked
- broken trusted setup assumptions
- vote or market logic that trusts unbounded IDs or stale state
- force-funding or selfdestruct-based balance manipulation

## Common operator notes

Use web tooling and chain tooling together:
- inspect app JS for auth and infra details
- use `cast` / Foundry to read storage and send crafted calls
- separate web-session proof from on-chain solve proof

## See also

- `auth-access-control.md` — nonce, token, and wallet-login handling on the web side
