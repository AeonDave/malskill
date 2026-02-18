---
name: kiterunner
description: "Context-aware API route discovery and brute-forcing using real-world API schema wordlists. Use when enumerating API endpoints, discovering hidden routes on REST/gRPC services, or replacing dirbusting for API surfaces."
license: MIT
compatibility: "Go binary; Linux/macOS/Windows; github.com/assetnote/kiterunner"
metadata:
  author: AeonDave
  version: "1.0"
---

# Kiterunner

Context-aware API route brute-forcer using real-world API schema wordlists (Assetnote).

## Quick Start

```bash
# Download binary from https://github.com/assetnote/kiterunner/releases

# Scan with default wordlist
kr scan https://target.com -w routes-small.kite

# Scan from file of hosts
kr scan hosts.txt -w routes-large.kite -x 20

# Replay a finding with full request detail
kr replay -w routes-small.kite "GET   403 [   191,    9,   1] https://target.com/api/v1/user"
```

## Core Flags

| Flag | Purpose |
|------|---------|
| `-w FILE` | Kite wordlist (.kite or .txt) |
| `-x N` | Concurrent requests |
| `--ignore-length N` | Filter by response length |
| `-H "K:V"` | Custom header |
| `-A "bearer:TOKEN"` | Auth header shorthand |
| `--fail-status-codes` | Codes treated as failures |
| `--success-status-codes` | Codes treated as hits |
| `-o json` | JSON output |
| `--delay N` | Per-request delay (ms) |

## Common Workflows

**Authenticated API scan:**
```bash
kr scan https://api.target.com -w routes-large.kite -A "bearer:$TOKEN" -x 30
```

**Filter noise — ignore typical 404/400 lengths:**
```bash
kr scan https://api.target.com -w routes-small.kite --ignore-length 19
```

**Replay to inspect full response:**
```bash
kr replay -w routes-large.kite "POST  200 [  512,  10,   2] https://api.target.com/api/v2/admin"
```

## Resources

| File | When to load |
|------|--------------|
| `references/` | Wordlist sources and API fingerprinting notes |
