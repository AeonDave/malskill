---
name: wfuzz
description: "Classic web application fuzzer using FUZZ placeholders across URL, headers, forms, auth, and request components. Use for endpoint discovery, payload injection workflows, and advanced response-filter triage."
license: GPL-2.0
compatibility: "Python on Linux/Windows/macOS; also Docker image."
metadata:
  author: GitHub Copilot
  version: "1.1"
---

# wfuzz

HTTP fuzzing tool built around payload injection via `FUZZ` tokens.

## Quick Start

```bash
pip install wfuzz

# Directory fuzzing
wfuzz -c -w wordlist.txt --hc 404 https://target/FUZZ

# Parameter fuzzing
wfuzz -c -w payloads.txt "https://target/search?q=FUZZ"
```

## Operator Flow

1. Establish baseline response shape (status/lines/words/chars).
2. Run discovery pass with hide filters (`--hc/--hl/--hw/--hh`).
3. Switch to targeted payloads (params, headers, auth, verbs).
4. Use filter language and plugin outputs for second-pass triage.
5. Save/reuse sessions for reproducible follow-up tests.

## Common Uses

- Path/file discovery.
- Query/form/header fuzzing.
- Auth and session edge-case probing.
- Semi-automatic testing around captured requests.

## High-Value Features

- Baseline token (`FUZZ{baseline}` + `BBB`) for differential filtering.
- Multi-payload iterators (`product`, `zip`, `chain`) for combination testing.
- Advanced filter grammar (`--filter`, `--prefilter`, `--slice`).
- Scan plugins (`--script`) for parse/discovery-assisted workflows.
- Reuse prior sessions (`wfuzzp`, Burp state/log payloads) for contextual fuzzing.

## Practical Tricks

- Use `-Z` scan mode when enumerating unstable hostnames/services; then filter `XXX` errors explicitly.
- When brute forcing behind proxies, tune `--conn-delay` and `--req-delay` to avoid false noise.
- Use `--field` / `--efield` to emit pipeline-friendly output into other tools.

## Common Pitfalls

- Running large dictionaries without baseline filters (noise flood).
- Ignoring soft-404 patterns and relying only on status code.
- Fuzzing all components at once instead of phased request decomposition.

## Notes

- In this repository, `ffuf` is often the faster default for bulk enumeration.
- Use `wfuzz` when you need its plugin/modular style and FUZZ-placement flexibility.

## Resources

- https://github.com/xmendez/wfuzz
- http://wfuzz.readthedocs.io/
- https://wfuzz.readthedocs.io/en/latest/user/getting.html
- https://wfuzz.readthedocs.io/en/latest/user/basicusage.html
- https://wfuzz.readthedocs.io/en/latest/user/advanced.html
