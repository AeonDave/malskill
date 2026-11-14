---
name: secure-tooling-implementation
description: "Implementation discipline for offensive/security tooling so the tool does not become the vulnerability: trust-boundary validation, subprocess/interpreter injection, safe temp and output handling, credential hygiene, fail-closed defaults, and TLS verification. Use when writing or reviewing scanners, loaders, parsers, agents, or any tool that handles untrusted input."
license: MIT
compatibility: "Agent workflow guidance; language-agnostic with cross-references to the language pattern skills."
metadata:
  author: AeonDave
  version: "1.0"
---

# Secure Tooling Implementation

Offensive tools process hostile input: responses from malicious servers, parsed target files, model outputs, captured packets — all attacker-controlled until proven otherwise. Validate/normalize at that boundary when *writing* the tool; audit-side skills (`vibe-audit-technique`, `source-review-technique`) review existing code, and the language skills cover per-idiom detail. Match the hardening to exposure: a shared or shipped tool earns the full checklist; a one-shot local probe gets only the boundary rules for the inputs it touches.

## Trust boundaries in offensive tools

Every response, parsed file, model output, and target-supplied string is **attacker-controlled until the target is proven trusted** — and on an engagement, it never is. The boundary is not "the network"; it is every byte whose content depends on a target's behavior:

- HTTP responses and headers (a server can return a filename, a redirect target, a content-type)
- Parsed artifacts: PE/ELF headers, APK manifests, PCAP records, model files (see `model-scanning` for the load-time RCE class)
- DNS answers, banner strings, SSL certificate fields — all attacker-settable strings that end up in logs, filenames, or shell commands
- LLM/model output (route through `untrusted-input-hygiene` when it can reach instructions)

Rule: validate/normalize **at the boundary**, then pass typed, structured data inward. A tool that f-strings raw target strings into a command is an RCE the target can fire back.

## Recurring implementation mistakes (by class)

| Class | Rule |
|---|---|
| **Subprocess** | Never interpolate target data into shell strings. Use exec-arrays (`subprocess.run([...], shell=False)`, `exec.Command` with separate args); if a shell is unavoidable, escape with the language's shlex-style helper and reject metacharacters at the boundary |
| **Path handling** | Target-derived names never compose output paths raw — sanitize, join against a fixed base, resolve and check containment. Temp files: `tempfile` with random names, restrictive permissions, clean up |
| **TLS** | `verify=False` / `-k` is a debugging aid that must not ship: make verification the default and opt-out per-flag with an explicit OPSEC note (and never for credentials in flight) |
| **Secrets** | Credentials, keys, and captured secrets are CLI args/env vars — never source-code literals, never in logs or reports without redaction. Repos leak via the tool's own debug output |
| **Defaults** | Fail closed: parse errors reject, unknown flags error, empty responses are treated as failures — silent fallbacks hide real states during engagements |
| **Resource safety** | Timeout every network call; bound downloads/allocations on attacker-influenced sizes (a Content-Length of 10 GB is an attacker choice); a hung tool mid-engagement is an availability incident |
| **Destructive ops** | Tools that modify target state ship with dry-run/confirm defaults — mirror `irreversible-action-gate` in the tool's own UX |

## Concurrency and error paths

- Worker pools that fan out to targets: per-task timeouts + overall deadline; a target that never answers must not hold the pool (loop-control applies to the tool's own runtime too).
- Error paths are attacker-observable: error messages that echo target input back into shells/HTML/SQL are injection sinks. Log structured, display sanitized.
- Cleanup on failure: if the tool stages payloads/temp state, the failure path cleans them — a crashed run must not leave artifacts that out the tool's presence later.

## Review checklist (for your own tool before shipping)

- [ ] Every target-derived string traced to its sink (shell/path/log/SQL/regex) — validated at the boundary
- [ ] No secrets in source, logs, or default report paths
- [ ] TLS verification on by default; exceptions explicit and logged
- [ ] All network I/O timeout-bound; attacker-controlled sizes bounded
- [ ] Temp/state files randomized, permissioned, cleaned on all exit paths
- [ ] Dry-run/safe default for state-changing operations
- [ ] The tool's own dependency surface follows `dependency-discipline`

## Related

- `untrusted-input-hygiene` (behaviours/) — the prompt-injection side of the same boundary problem
- `software-guidelines` — the scoped-change workflow this plugs into
- `irreversible-action-gate` (behaviours/) — the ops-side gate for what the tool *does*
- `model-scanning` (ai/) — the model-artifact branch of load-time RCE
- Language specifics: the relevant `*-patterns` skill (c/cpp/rust/golang/python)
