---
name: enum4linux-ng
description: "Use enum4linux-ng for scoped SMB and Samba enumeration of shares, users, groups, password policy, and host details."
license: GPL-2.0
compatibility: "Linux; Python 3 and Samba client tools."
metadata:
  author: AeonDave
  version: "1.0"
---

# enum4linux-ng

enum4linux-ng rewrites the classic Perl tool in Python and exports findings as JSON or YAML. Use [ParrotSec/enum4linux-ng](https://github.com/ParrotSec/enum4linux-ng) and record the installed package version or source revision; numbered source tags and distribution packages may differ.

## Common use

```bash
# Default enumeration against an authorized host
enum4linux-ng -A <host>

# Save findings for review or processing
enum4linux-ng -A <host> -oA <output>

# Select specific enumeration categories
enum4linux-ng -U -G -S -P <host>
```

The tool uses `nmblookup`, `net`, `rpcclient`, and `smbclient`; install the Samba client utilities and Python dependencies listed by upstream. `-A` performs the default simple enumeration. Use `-U`, `-G`, `-S`, or `-P` to select users, groups, shares, or password-policy checks. `-oJ`, `-oY`, and `-oA` write JSON, YAML, or both formats.
