---
name: snaffler
description: "Auth/lab ref: Snaffler AD share audit; accessible shares, sensitive file patterns, secret-risk indicators, evidence reporting."
license: MIT
compatibility: "Windows .NET; domain SMB access required."
metadata:
  author: AeonDave
  version: "1.0"
---

# Snaffler

.NET tool for credential and secret hunting across Active Directory network shares.

## Quick Start

```powershell
# Basic scan — enumerate all shares and find interesting files
.\Snaffler.exe -s -d domain.local -o snaffler.log -v data

# Output to console + file with verbosity
.\Snaffler.exe -s -d domain.local -o results.log -v data
```

## Core Usage

### Basic enumeration
```powershell
# Enumerate shares in current domain
.\Snaffler.exe -s -d <domain>

# Specify output file and verbosity
# -v options: info, data (show matched content), trace, debug
.\Snaffler.exe -s -d domain.local -o snaffler.log -v data

# Target specific hosts
.\Snaffler.exe -s -n host1,host2,host3 -o results.log -v data
```

### Filtering and targeting
```powershell
# Only scan specific shares
.\Snaffler.exe -s -d domain.local -a sharename

# Exclude specific shares
.\Snaffler.exe -s -d domain.local -x "NETLOGON,SYSVOL"

# Only scan writable shares
.\Snaffler.exe -s -d domain.local -y

# Limit file size scanned (default 500KB)
.\Snaffler.exe -s -d domain.local -l 1048576
```

### Output interpretation
Snaffler classifies findings by severity:
- **Black** — highest value: credentials, private keys, password managers
- **Red** — high value: config files with connection strings, scripts with creds
- **Yellow** — medium value: interesting files that may contain secrets
- **Green** — low value: potentially interesting but needs review

### What Snaffler finds
- Passwords in scripts (`.ps1`, `.bat`, `.vbs`, `.py`)
- Configuration files with connection strings (`web.config`, `appsettings.json`)
- Private keys (`.pfx`, `.pem`, `.key`, `id_rsa`)
- KeePass databases (`.kdbx`)
- Password manager exports
- GPP passwords (`Groups.xml`, `Registry.xml`)
- Autologon credentials in registry policy files
- SSH keys and configs
- Cloud credential files (AWS, Azure, GCP)
- Database backups (`.bak`, `.mdf`)

### Integration with AD attack workflow
```powershell
# After initial foothold, run Snaffler to find stored credentials
.\Snaffler.exe -s -d domain.local -o snaffler_$(Get-Date -Format 'yyyyMMdd').log -v data

# Parse results for immediate wins
Select-String -Path snaffler.log -Pattern "(password|credential|secret)" -CaseSensitive:$false
```

## OPSEC considerations
- Generates significant SMB traffic (share enumeration + file reads)
- Noise level: MODERATE to LOUD depending on domain size
- Consider targeting specific hosts rather than full domain scan
- Run during business hours to blend with normal file access patterns
- Event IDs: 5140 (share access), 5145 (file access check)

## Alternatives
- Manual: `Find-DomainShare -CheckShareAccess` + manual inspection (slower)
- CrackMapExec spider_plus module: `cme smb <target> -M spider_plus`
- SharpShares: lightweight share enumeration (no content analysis)
