# Harness and Oracle Patterns

Reusable templates for driving remote/stateful challenges. Load when building the solve script.

## Contents

- Remote loop (pwntools / socket)
- Oracle-error walking
- Minimal-matrix brute (reconnect per attempt)
- Flag regex helpers
- Subagent parallelization

## Remote loop

Prefer one script that runs connect → flag. `socket` gives exact byte control for binary protocols; `pwntools` is faster for line/text protocols.

```python
import socket, re

def io(host, port, payload, greet=False, timeout=8, recv=8192):
    s = socket.socket(); s.settimeout(timeout); s.connect((host, port))
    banner = b""
    if greet:                       # only if the service is known to speak first
        try: banner = s.recv(1024)
        except socket.timeout: pass
    s.send(payload)                 # send-then-recv: works whether or not it greeted
    try: resp = s.recv(recv)
    except socket.timeout: resp = b""
    s.close()
    return banner, resp
```

pwntools equivalent for text protocols:

```python
from pwn import remote, context
context.log_level = "warn"
r = remote(host, port)
# r.recvline(timeout=2)            # only if it greets
r.send(payload)
print(r.recvall(timeout=3))
```

Rule: if `recv` times out on connect, the target is waiting for input — do not block on a banner; send first.

## Oracle-error walking

Layered validators reject one field at a time and name it. Loop: send → read the error → fix exactly what it named → resend. Keep a ledger of `{field: value}` and only change the field the error points at.

```python
state = {"seq": 0, "count": 0, "type": 1}   # current best guess of every field
while True:
    resp = attempt(state)
    if flag := re.search(rb"HTB\{[^}]+\}", resp):
        print("FLAG:", flag.group().decode()); break
    print("oracle:", resp)          # e.g. b"Expected ... 1 but got 0"
    # parse the message, set state[<named field>] to the value it expects, resend
    if not progressed(resp):        # error stopped changing -> re-triage, don't spin
        break
```

When the message reveals an expected number (`expected VCFC 1`, `sequence count 1`, `length 42`), set that field directly rather than searching for it.

## Minimal-matrix brute (reconnect per attempt)

Only after the oracle is exhausted and exactly one small field remains ambiguous. Reset state per attempt so a prior failure does not poison the next.

```python
import itertools, re
found = None
for a, b in itertools.product(range(3), range(2)):     # tiny space only
    resp = fresh_session_then(a, b)                    # reconnect + re-sync inside
    if m := re.search(rb"(HTB|flag)\{[^}]+\}", resp):
        found = (a, b, m.group().decode()); break
    print(f"a={a} b={b} -> {resp[:80]!r}")
print("hit:", found)
```

`fresh_session_then` should open a new connection and replay any handshake before the tested inputs — stateful services keep counters that must start clean.

## Flag regex helpers

```python
import re
PATTERNS = [rb"HTB\{[^}]+\}", rb"flag\{[^}]+\}", rb"[A-Za-z0-9_]{2,}\{[^}]{4,}\}"]
def find_flag(blob):
    for p in PATTERNS:
        if m := re.search(p, blob):
            return m.group().decode(errors="replace")
    return None
```

Confirm the match against the platform's stated format before submitting; a random brace-string is not a flag.

## Subagent parallelization

For N independent challenges, or N independent spec-guesses of one stubborn challenge, dispatch one subagent each and collect only the results. Give every subagent:

- the concrete target (`host:port`, challenge id) and stated flag format;
- the exact spec/params from the brief (not placeholder values);
- any already-working helper code (frame builder, CRC, handshake) so it does not re-derive the basics;
- an instruction to return the flag and the minimal method, and to submit via the platform tool if one exists.

Split a *single* challenge across subagents only along a real seam (recon vs. exploitation, or independent sub-flags) where there is no shared mutable state. Otherwise keep one challenge in one agent to preserve its session/oracle state.
