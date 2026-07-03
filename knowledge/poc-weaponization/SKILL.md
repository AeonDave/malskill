---
name: poc-weaponization
description: Safely evaluate, adapt, and rewrite raw public proof-of-concepts into reliable, offline-capable exploits free of backdoors.
---

# poc-weaponization

## When to use

- You have a public PoC (from `cve-search`, GitHub, Exploit-DB, Sploitus, etc.).
- The PoC lacks reliability, targets wrong offsets, or was written for Python 2.
- You must verify the PoC is not backdoored before running it against a target.

## The Weaponization Workflow

### 1. Safety Audit (Isolated Environment)
Before executing any public exploit script:
- **Run in an isolated environment first** (container or VM with no credentials mounted). A clean-looking PoC may still exfiltrate environment variables or SSH keys at runtime.
- Check `requirements.txt`, `setup.py`, `install.sh`, and any package manifest for typosquatted or malicious dependencies and build hooks that execute at install time.
- Look for obfuscation: Base64 blocks, `eval()`, `exec()`, reversed strings.
- Look for callbacks: network connections to third-party hosts outside the intended target (DNS exfiltration, analytics beacons, hardcoded C2).
- Check for destructive side-effects: hardcoded `rm -rf`, `DROP TABLE`, unnecessary persistence.
- Load `references/backdoor-patterns.md` for the full pattern list.

### 2. Modernization & Translation
- **Python 2 → 3**: Fix `print` statements, replace `urllib2` with `requests`, handle bytes/strings encode/decode.
- **LLM-assisted porting**: Using an LLM to translate or adapt PoC code is acceptable; review output for hallucinated API calls or function signatures that do not exist in the target library version.
- **Shellcode**: Strip hardcoded shellcode; replace with parameterized payload injection (e.g., `msfvenom`-generated blob via `--payload` flag).

### 3. Reliability & Generalization
- **Hardcoded constraints**: Eliminate hardcoded IPs, ports, and offsets. Implement `argparse` or click to allow parameterized inputs (`--target`, `--port`, `--lhost`, `--lport`).
- **Error handling**: Avoid raw stack traces on network timeouts. Handle `ConnectionRefusedError`, HTTP 404s, and unexpected payload formats cleanly.
- **Verification mode**: Add a `--check` flag that securely tests if the vulnerability is present without actually firing the payload or dropping the shell.

## References

- [references/backdoor-patterns.md](references/backdoor-patterns.md) — Common backdoor and beacon patterns in poisoned PoCs; load during step 1.
