---
name: game-ctf
description: "Challenge-solving methodology for GamePwn and game-cracking CTF tasks involving Unity games (Mono and IL2CPP), native game binaries (ELF/PE, SDL, OpenGL), game asset bundles, and network-based game protocols. Use when artifacts are game executables (.exe, ELF), Unity builds (GameAssembly.dll, Assembly-CSharp.dll, *.assets, global-metadata.dat), game memory dumps (*.dmp), save files, or game network captures. Covers: Unity Mono decompilation and patching with dnSpy, Unity IL2CPP reversing with Il2CppDumper and Ghidra, game asset extraction (UABE, AssetRipper, strings), native game binary analysis for win-condition bypass, memory manipulation with Cheat Engine or Python, save file tampering, and game network protocol replay. Routes deep binary exploitation to pwn-ctf and static reversing depth to reverse-ctf and reversing-technique."
license: MIT
compatibility: "Linux/Windows; Unity (Mono/IL2CPP), native ELF/PE; tools: dnSpy, Il2CppDumper, Ghidra, UABE, Cheat Engine, Python."
metadata:
  author: AeonDave
  version: "1.0"
  category: ctf-solving
---

# Game CTF

Solve game challenges by identifying the engine and runtime first, then choosing the narrowest extraction or patching path before escalating to full binary reversing.

## When this skill applies

- Artifact is a game binary: `.exe`, ELF, `GameAssembly.dll`, `Assembly-CSharp.dll`, or a Unity build folder.
- Challenge requires reaching a win condition, unlocking a hidden flag, bypassing a score check, or extracting data from game assets.
- Artifact includes Unity asset files (`*.assets`, `*.dmp`, `sharedassets*`, `globalgamemanagers`).
- Challenge involves intercepting or replaying a game network protocol to obtain the flag.

## Operating model

```
1. Identify engine: Unity Mono | Unity IL2CPP | Native (SDL/OpenGL/custom) | Godot | other
2. Quick win: strings <binary> | grep flag{ — catches ~20% of challenges
3. Static analysis path per engine type
4. If flag not found: memory manipulation (Cheat Engine/Python) or network replay
5. Validate and submit
```

## Technique integration

- `reversing-technique` for obfuscated native binaries, custom crypto, or complex control flow.
- `pwn-ctf` if the game binary has an exploitable memory corruption vulnerability.
- `game-technique` for Cheat Engine workflow, pointer scanning, and real-world memory hacking patterns.

---

## Engine identification

```bash
# Quick type check
file target

# Unity Mono (old pipeline — .NET DLLs alongside exe)
ls <GameName>_Data/Managed/Assembly-CSharp.dll   # present → Mono

# Unity IL2CPP (new pipeline — native binary)
ls GameAssembly.dll                               # Windows
ls <GameName>_Data/Native/GameAssembly.so         # Linux
ls <GameName>_Data/il2cpp_data/Metadata/global-metadata.dat  # both

# Native (SDL / OpenGL / custom engine)
strings <binary> | grep -i "SDL_\|OpenGL\|GLFW\|raylib\|allegro"

# Godot
ls *.pck                                          # Godot PCK resource pack
strings <binary> | grep -i "godot\|GDScript"
```

---

## Type 1 — Unity Mono (.NET)

`Assembly-CSharp.dll` is a plain .NET assembly — decompile directly with dnSpy.

```bash
# Linux: use dnSpy on Windows or ilspycmd on Linux
dotnet tool install -g ilspycmd
ilspycmd Assembly-CSharp.dll -o decompiled/

# Search for flag/win condition
grep -r "flag{\|flag\|win\|score\|complete\|cheat\|unlock" decompiled/ -i | head -20

# Or: dnSpy on Windows
# Open Assembly-CSharp.dll → browse classes → find GameManager, FlagController, WinCondition
# Right-click method → Edit Method → patch return value or inject flag print
# File → Save All → run patched game
```

**Common CTF patterns in Mono games:**
- `WinCondition.CheckScore()` compares player score against hardcoded threshold → change threshold to 0 or patch `ret true`
- `FlagManager.GetFlag()` returns encrypted string → patch to return plaintext or log the decrypted value
- `GameManager.gameOver` boolean → force set via Cheat Engine or DLL patch

---

## Type 2 — Unity IL2CPP

C# compiled to native ARM/x86 binary. `GameAssembly.dll` contains game logic but method names are stripped without metadata.

### Step 1 — Dump class/method names with Il2CppDumper

```bash
# https://github.com/Perfare/Il2CppDumper
# Inputs:
#   Windows: GameAssembly.dll + <GameName>_Data\il2cpp_data\Metadata\global-metadata.dat
#   Linux:   GameAssembly.so  + <GameName>_Data/il2cpp_data/Metadata/global-metadata.dat

# Run Il2CppDumper (Windows GUI or CLI)
Il2CppDumper.exe GameAssembly.dll global-metadata.dat output/

# Outputs:
#   dump.cs          → all C# class/method/field stubs with field offsets
#   script.py        → Ghidra import script (auto-renames all functions)
#   stringliteral.json → all string constants with addresses

# Search dump.cs for flag/win condition
grep -i "flag{\|flag\|win\|score\|cheat\|unlock\|complete\|GetFlag\|CheckScore" output/dump.cs

# Search stringliteral.json for flag string
python3 -c "
import json
data = json.load(open('output/stringliteral.json'))
for entry in data:
    if 'flag{' in entry.get('value','') or 'flag' in entry.get('value','').lower():
        print(entry)
"
```

### Step 2 — Ghidra analysis with Il2CppDumper script

```bash
# In Ghidra:
# 1. Import GameAssembly.dll (or .so)
# 2. Run script.py via Script Manager → all functions renamed to C# method names
# 3. Search for the target method by name (e.g., GameManager$$CheckWinCondition)
# 4. Analyze the comparison logic and offset used for player score/state
```

### Step 3 — Memory patch via Cheat Engine

```bash
# While game runs:
# 1. Cheat Engine → attach to game process
# 2. Scan for score/flag value (4-byte int, exact value)
# 3. Change value → player score jumps to required threshold → flag displayed

# CLI alternative (Linux): use /proc/<pid>/mem with Python
python3 - <<'EOF'
import ctypes, struct

pid = <game_pid>
target_addr = <address_from_il2cppdumper_offset>

# Read current value
with open(f'/proc/{pid}/mem', 'rb') as m:
    m.seek(target_addr)
    val = struct.unpack('<i', m.read(4))[0]
    print(f'Current: {val}')

# Write new value
with open(f'/proc/{pid}/mem', 'r+b') as m:
    m.seek(target_addr)
    m.write(struct.pack('<i', 999999))
EOF
```

---

## Type 3 — Unity Asset files

Asset files (`*.assets`, `*.dmp`, `sharedassets*.assets`, `globalgamemanagers`) contain game data: textures, text, audio, MonoBehaviour configs.

```bash
# Quick strings (flag may be plaintext in text asset)
strings game_radar_challenge/assets.dmp | grep -i "flag{\|flag\|secret\|key" | head -20
strings sharedassets0.assets | grep -i "flag{"

# UABE (Unity Asset Bundle Extractor) — Windows GUI
# Open *.assets → browse assets list → export TextAsset / Texture2D / MonoBehaviour

# AssetRipper — cross-platform Unity asset extractor
git clone https://github.com/AssetRipper/AssetRipper
# Run and point at the game directory → extracts full project including text assets, scripts

# Python: manual asset file search
python3 -c "
import re
data = open('assets.dmp','rb').read()
print('HTB patterns:', re.findall(b'HTB\{[^}]{1,60}\}', data))
print('Strings (16+ printable chars):')
for s in re.findall(b'[\x20-\x7e]{16,}', data):
    print(s.decode())
" | head -40
```

---

## Type 4 — Native game binary (SDL / OpenGL / custom)

Pure C/C++ game. Standard binary reversing + memory manipulation.

```bash
# Static analysis
strings radar_challenge | grep -iE "HTB\{|flag|score|win|cheat|pass|unlock|level"
checksec --file=radar_challenge   # check mitigations

# Ghidra / radare2 analysis
# r2 -A radar_challenge → afl → look for: main_game_loop, check_win, validate_score, print_flag
r2 -A radar_challenge
[0x00401234]> afl | grep -i "win\|flag\|check\|score\|valid"
[0x00401234]> pdf @ sym.check_win   # decompile win condition function

# Patch win condition (hex edit or binary patch)
# Find comparison: CMP rax, <score_threshold>
# Patch to: XOR eax,eax; INC eax (always returns 1/true)
python3 -c "
data = bytearray(open('radar_challenge','rb').read())
# Find and patch offset from Ghidra analysis
data[0x1234:0x1238] = b'\\x31\\xc0\\xff\\xc0\\x90'  # xor eax,eax; inc eax; nop
open('radar_patched','wb').write(data)
"

# Memory manipulation while running (Linux)
# Use gdb or scanmem
scanmem --pid=$(pgrep radar_challenge)
# > list   → show found addresses after scanning for score value
# > set 99999   → set value at found address
```

---

## Type 5 — Godot games

```bash
# PCK file contains all game assets and GDScript
# Extract with Godot PCK Explorer or godotpcktool
godotpcktool extract game.pck -o extracted/

# GDScript files (.gd) readable directly
find extracted/ -name "*.gd" | xargs grep -i "flag\|password\|flag{\|win\|cheat"

# Godot 3: scripts decompile via godotdec or manually
# Godot 4: GDScript bytecode format changed — use gdsdecomp
```

---

## Type 6 — Game network protocol

When the game connects to a server and the server validates score/flag.

```bash
# Capture traffic while game runs
tcpdump -i lo -w game.pcap   # loopback if local server

# Inspect with Wireshark
# Look for: score submission packets, flag request/response, auth tokens

# Replay modified packet
python3 - <<'EOF'
import socket, struct

HOST, PORT = '127.0.0.1', 31337
# Reconstruct packet with modified score value
packet = struct.pack('>I', 999999)   # big-endian score field
with socket.socket() as s:
    s.connect((HOST, PORT))
    s.send(packet)
    print(s.recv(1024))
EOF
```

---

## Quick pivots by symptom

| Symptom | Action |
|---------|--------|
| `Assembly-CSharp.dll` present | Unity Mono → dnSpy → patch WinCondition |
| `GameAssembly.dll` + metadata | Unity IL2CPP → Il2CppDumper → dump.cs → Ghidra/Cheat Engine |
| `*.assets` / `*.dmp` files | strings + UABE/AssetRipper — flag may be text asset |
| `*.pck` file | Godot → godotpcktool extract → grep .gd scripts |
| Native ELF/PE, SDL strings | Binary reversing → checksec → r2/Ghidra → patch win condition |
| Game connects to server | Capture traffic → replay with tampered score/flag field |
| Score comparison in decompiled code | Patch comparison (JNZ→JMP) or set score via Cheat Engine/ptrace |
| Flag printed only on legit win | Hook flag-print function with Frida or breakpoint in debugger |

## Resources

- [references/unity-game-analysis.md](references/unity-game-analysis.md) — Il2CppDumper workflow, Mono vs IL2CPP identification, asset extraction, dnSpy patching patterns.
