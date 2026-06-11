---
name: poc-weaponization
description: Safely evaluate, adapt, and rewrite raw public proof-of-concepts into reliable, offline-capable exploits free of backdoors.
---

# poc-weaponization

**Goal**: Convert raw, untested Proofs-of-Concept (from GitHub, Exploit-DB, etc.) into robust, weaponized tactical scripts.

## When this skill applies

- You have acquired a public PoC script (e.g. from `cve-search`).
- The PoC needs to be run against a target but lacks reliability, relies on outdated Python 2, or targets extremely specific offsets that differ from the live environment.
- You must verify the PoC for safety (no backdoors or outbound callback mechanisms capturing your own host).

## The Weaponization Workflow

### 1. Safety Audit (Offline Sandbox)
Before executing any public exploit script:
- Look for obfuscation: Base64 blocks, `eval()`, `exec()`, reversed strings.
- Look for callbacks: Does it ping a third-party server (e.g., DNS exfiltration, analytics beacon, malicious C2) outside of the intended target?
- Check for destructive actions: hardcoded `rm -rf`, aggressive `DROP TABLE`, unnecessary persistence mechanisms.

### 2. Modernization & Translation
- If written in Python 2: Translate to Python 3. Fix `print` statements, `urllib2` to `requests`, and handle bytes/strings encode/decode mismatches.
- If it throws arbitrary shellcode: Strip the shellcode and convert it to allow custom payload injections (e.g., passing your own generated reverse shell from `msfvenom`).

### 3. Reliability & Generalization
- **Hardcoded constraints**: Eliminate hardcoded IPs, ports, and offsets. Implement `argparse` or click to allow parameterized inputs (`--target`, `--port`, `--lhost`, `--lport`).
- **Error handling**: Avoid raw stack traces on network timeouts. Handle `ConnectionRefusedError`, HTTP 404s, and unexpected payload formats cleanly.
- **Verification mode**: Add a `--check` flag that securely tests if the vulnerability is present without actually firing the payload or dropping the shell.

## References

- [references/backdoor-patterns.md](references/backdoor-patterns.md) — Identify common backdoors and malicious beacons embedded inside fake or poisoned PoCs.
