---
name: cobalt-strike
description: "Cobalt Strike: commercial adversary simulation platform with Beacon implant supporting HTTP/S, DNS, SMB, TCP, and Malleable C2 profiles. Use when operating professional red team engagements, simulating advanced threat groups, managing multi-operator teamserver infrastructure, or executing BOFs."
license: Commercial
compatibility: "Teamserver: Linux/macOS. Client: Windows/Linux/macOS (Java). Commercial license required."
metadata:
  author: AeonDave
  version: "1.0"
---

# Cobalt Strike

Commercial adversary simulation with Beacon implant.

## Quick Start

```bash
./teamserver <ip> <password> [malleable-profile]
./cobaltstrike
```

## Beacon Commands

| Command | Purpose |
|---------|---------|
| `shell <cmd>` | Run via cmd.exe |
| `run <cmd>` | Execute directly |
| `powerpick <ps>` | Unmanaged PowerShell |
| `execute-assembly <dll> <args>` | In-memory .NET execution |
| `inline-execute <bof>` | Execute BOF in Beacon |
| `jump psexec <target> <listener>` | Lateral movement via SMB |
| `jump winrm64 <target> <listener>` | Lateral via WinRM |
| `steal_token <pid>` | Token impersonation |
| `mimikatz sekurlsa::logonpasswords` | Kiwi credential dump |
| `socks 1080` | SOCKS proxy |
| `rportfwd <lp> <host> <rp>` | Reverse port forward |

## Malleable C2

Profiles modify Beacon network fingerprint. Key sections: `http-get`, `http-post`, `stage`, `process-inject`.

```bash
./c2lint malleable-profile.profile
```

## Resources

| File | When to load |
|------|--------------|
| `references/` | Aggressor Script, BOF development, Malleable profile examples |
