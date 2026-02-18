---
name: mimipenguin
description: "Dump credentials from memory on Linux systems (GNOME Keyring, VSFTPd, Apache, SSH). Use when you have root on a Linux target to extract plaintext passwords from running processes and memory."
license: MIT
compatibility: "Python 3 / Bash; Linux; requires root; github.com/huntergregal/mimipenguin"
metadata:
  author: AeonDave
  version: "1.0"
---

# MimiPenguin

Linux credential dumper — extract plaintext passwords from memory (Mimikatz-equivalent for Linux).

## Quick Start

```bash
# Requires root
git clone https://github.com/huntergregal/mimipenguin
cd mimipenguin

# Python version
sudo python3 mimipenguin.py

# Shell version
sudo bash mimipenguin.sh
```

## Sources Dumped

| Source | Notes |
|--------|-------|
| GNOME Keyring | `/proc/<PID>/mem` of gnome-keyring-daemon |
| VSFTPd | Active FTP session credentials |
| Apache Basic Auth | HTTP Basic Auth from apache2 process |
| SSH | SSH passphrase from ssh-agent |
| gdm3 | GNOME Display Manager login |
| su | Credentials from `su` process |

## Common Workflows

**Quick dump all sources:**
```bash
sudo python3 mimipenguin.py 2>/dev/null
```

**Shell version (no python dependency):**
```bash
sudo bash mimipenguin.sh
```

**Redirect output:**
```bash
sudo python3 mimipenguin.py | tee /tmp/.creds
```

> **Note**: Effectiveness depends on what services are running and memory layout.

## Resources

| File | When to load |
|------|--------------|
| `references/` | Process memory dump techniques on Linux |
