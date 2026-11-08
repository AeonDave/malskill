---
name: netexec
description: "Use NetExec to assess SMB, WinRM, LDAP, MSSQL, SSH, or RDP services with known credentials in an authorized environment."
license: BSD-2-Clause
compatibility: "Linux; NetExec v1.5.1 (current upstream release checked 2026-11-08)."
metadata:
  author: AeonDave
  version: "1.0"
---

# NetExec

NetExec (`nxc`) is the maintained successor to CrackMapExec. Use it for scoped protocol checks and authenticated service inventory.

Install and check the version using the [official project instructions](https://github.com/Pennyw0rth/NetExec). The current upstream release is [v1.5.1](https://github.com/Pennyw0rth/NetExec/releases/tag/v1.5.1); distributions may package a different version. Upstream's Linux install uses `pipx install git+https://github.com/Pennyw0rth/NetExec`.

## Basic use

Select the protocol, then pass only in-scope hosts and credentials supplied for the assessment:

```bash
# Check SMB authentication and enumerate accessible shares
nxc smb <host> -u <user> -p <password> --shares

# Check an authorized WinRM endpoint
nxc winrm <host> -u <user> -p <password>
```

Available protocol modules and options vary by installed release. Check `nxc <protocol> --help` before relying on a flag or module. Do not infer that a successful authentication check proves access beyond the reported protocol and host.
