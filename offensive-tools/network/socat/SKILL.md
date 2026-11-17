---
name: socat
description: "socat — universal relay/port-forward: TCP/UDP/SSL redirect, bind shells, file transfers, pivoting through multi-hop relays. Use when netcat isn't enough (encryption, bidirectional, fork, reuseaddr) or when chaining tunnels across pivots."
license: MIT
compatibility: "Linux/macOS (static binaries common); Windows via WSL or Cygwin build."
metadata:
  author: AeonDave
  version: "1.0"
---

# socat

Universal relay: pipes two bidirectional byte streams (TCP, UDP, SSL, files, exec) with fork/reuseaddr control. The netcat upgrade — use when you need encryption, multiple connections, or chained relays.

## Core workflow

```bash
# Port forward (fork = handle multiple connections; reuseaddr = rebind without TIME_WAIT wait)
socat TCP4-LISTEN:8080,fork,reuseaddr TCP4:10.0.0.1:80

# TLS relay: server.pem contains certificate/key; verify=0 disables client certificate checks
socat OPENSSL-LISTEN:4443,cert=server.pem,verify=0,fork TCP4:127.0.0.1:80

# Bind shell listener (replaces nc -e on OpenBSD nc)
socat TCP4-LISTEN:4444,reuseaddr,fork EXEC:/bin/sh,pty,stderr

# One-shot file transfer: receiver creates a new file and refuses to overwrite it
socat -u TCP4-LISTEN:9999,reuseaddr OPEN:outfile.bin,creat,excl
# Sender reads infile.bin and sends it to the receiver
socat -u FILE:infile.bin TCP4:10.0.0.1:9999

# Chained relay through a pivot (host A → host B → host C)
socat TCP4-LISTEN:2222,fork TCP4:<pivot-ip>:2222
# on pivot: socat TCP4-LISTEN:2222,fork TCP4:<final-target>:22
```

## Best practice

- Use `fork` for reusable service relays, not one-shot file receivers writing a shared destination. `reuseaddr` permits address reuse subject to OS socket rules.
- **Chained relays**: each relay's destination must match the next relay's listening host and port; different hosts may reuse the same port number.
- For interactive shells, add `pty,stderr` to EXEC: gives a TTY prompt and keeps stderr visible.
- Use `TCP4-LISTEN:0` (OS-assigned port) when a fixed listening port is unnecessary; read the assigned port from `ss -tlnp`.

## Gotchas

- Minimal/static socat builds can be compiled without `EXEC`, `SYSTEM`, or `OPENSSL` support — check `socat -V` for the compiled features before relying on `EXEC:` or `OPENSSL:`.
- The relay is bidirectional by default; use `-u` (unidirectional left→right) or `-U` (right→left) for one-way flows.
- Forked children inherit the environment: secrets in env vars leak to every child process.

## References

- [Upstream manual](http://www.dest-unreach.org/socat/doc/socat.html): address types, file-open flags, direction options, and TLS verification.
- Related: `netcat` (simpler, no fork/SSL), `chisel` (HTTP-tunneled relay for restrictive egress), `ligolo-ng` (agent-based pivot without port forwarding)
