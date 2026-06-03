---
name: boofuzz
description: "Auth/lab ref: Python network protocol fuzzing framework (Sulley successor). For stateful TCP/UDP protocol fuzzing, request-graph modeling, monitor-driven crash detection, and reproducible protocol campaign workflows."
license: GPL-2.0
compatibility: "Python 3 on Linux/Windows/macOS."
metadata:
  author: GitHub Copilot
  version: "1.1"
---

# boofuzz

Protocol fuzzer framework with request modeling, session graphs, monitors, and structured logging.

## Quick Start

```bash
pip install boofuzz
```

```python
from boofuzz import Session, Target, TCPSocketConnection, s_initialize, s_string, s_get

s_initialize("req")
s_string("HELLO", fuzzable=True)

session = Session(target=Target(connection=TCPSocketConnection("127.0.0.1", 9999)))
session.connect(s_get("req"))
session.fuzz()
```

## Operator Flow (Recommended)

1. Define protocol requests as `Request` + `Block` + primitives.
2. Build realistic session graph via `session.connect(...)`.
3. Add monitors (process/network/callback) before scaling testcases.
4. Enable logs and reproduce individual failing testcases from run DB.
5. Iterate on protocol model quality (field sizes, delimiters, checksums, dependencies).

## Best Use Cases

- Custom/legacy network protocols.
- Stateful handshake + multi-step message flows.
- Harnesses requiring explicit restart/monitor logic.

## Practical Tricks

- Use `post_test_case_callbacks` for protocol-aware checks instead of only crash/no-crash signals.
- Use `ProtocolSessionReference` when later messages need dynamic data extracted from prior responses.
- Keep a strict separation between:
  - transport connection behavior,
  - protocol message modeling,
  - health/monitoring logic.
- Prefer deterministic target reset routines in monitor hooks.

## Common Pitfalls

- Blind mutation of raw bytes without block/field modeling wastes boofuzz strengths.
- No monitor/restart chain -> flaky crash attribution.
- Overly broad callback side effects -> non-deterministic failures.

## Logging & Triage

- Use text/CSV/curses loggers via `FuzzLogger` multiplexer for both operator visibility and artifacts.
- Persist each run DB (`boofuzz-results/run-*.db`) and reopen for post-campaign review.
- Keep concise crash synopsis in monitor implementations (`get_crash_synopsis`).

## Resources

- https://github.com/jtpereyda/boofuzz
- https://boofuzz.readthedocs.io/
- https://boofuzz.readthedocs.io/en/stable/user/quickstart.html
- https://boofuzz.readthedocs.io/en/stable/user/monitors.html
- https://boofuzz.readthedocs.io/en/stable/user/protocol-definition.html
