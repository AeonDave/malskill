---
name: game-technique
description: "Auth assessment: game security methodology; client integrity, anti-cheat, protocol replay, save formats, DRM/license checks, memory analysis."
license: MIT
compatibility: "Linux/Windows; Cheat Engine (Windows), scanmem (Linux), Python 3, Ghidra/radare2, Wireshark; authorized isolated game environments required."
metadata:
  author: AeonDave
  version: "1.0"
  category: offensive-techniques
---

# Game Technique

Goal: systematically assess game client security in an authorized context — identifying exploitable weaknesses in memory protection, network validation, license enforcement, or save file integrity — and produce findings that map to concrete client-side or server-side remediations.

## When this technique applies

- Authorized game client security assessment or bug bounty engagement targeting a specific game title.
- Red team scenario requiring demonstration that game anti-cheat can be bypassed.
- Assessment of game server economic integrity (can scores, currency, or items be spoofed?).
- License or DRM security review (authorized by the publisher for internal audit).
- Game mod/plugin security assessment (does the game safely load third-party content?).

## Boundary with other skills

- **CTF game challenges**: flag extraction from game binaries → `game-ctf` (faster, CTF-specific patterns).
- **Deep binary exploitation**: buffer overflow, heap spray in game binary → `reversing-technique` + `vuln-exploit-technique`.
- **Game backend/API**: REST API score submission, OAuth, economy endpoints → `web-exploit-technique`.
- **Mobile game apps**: Android APK, iOS IPA game apps → `mobile-technique`.

## Safety and authorization

Game security testing without explicit written authorization violates terms of service and may violate computer fraud laws in many jurisdictions:
- Only test on accounts you own or on isolated test environments provided by the publisher.
- Never deploy cheats against live competitive multiplayer unless authorized to do so in a controlled research environment.
- Network-side testing (packet manipulation, score spoofing) against production game servers requires explicit written authorization from the publisher/operator.
- Anti-cheat bypass research has dual-use implications — findings should be disclosed to the publisher, not weaponized or distributed.

## Initial triage

Before choosing a technique, classify the attack surface:

- **Is score/state validated client-side only?** → memory manipulation or packet replay is the primary path.
- **Is there server-side validation?** → network protocol analysis + server-side testing.
- **Is the game .NET/Unity?** → `game-ctf` techniques apply; static analysis is fast.
- **Is there DRM/license enforcement?** → license bypass is the focus.
- **Is there an anti-cheat driver?** → kernel-level analysis required; escalate scope early.

---

## Phase 1 — Game binary reconnaissance

```bash
# Basic triage
file game_binary
strings game_binary | grep -iE "steam|denuvo|easyanticheat|battleye|license|serial|register|crack"
checksec --file=game_binary   # ASLR, DEP, CFG, Authenticode

# Identify engine
strings game_binary | grep -iE "unity|unreal|godot|cryengine|SDL_|OpenGL|GLFW|DirectX"

# Import analysis (reveals linked protection libraries)
# Windows PE
dumpbin /imports game.exe 2>/dev/null | grep -iE "steam|eac|anticheat|battleye"
# Linux ELF
readelf -d game_elf | grep NEEDED
ldd game_elf
```

---

## Phase 2 — Memory scanning and value manipulation

The foundation of game client hacking. Every game state variable (health, score, currency, ammo, coordinates) exists at a memory address while the game runs.

### Cheat Engine methodology (Windows)

```
1. Open Cheat Engine → Attach to game process (as admin if needed)
2. First scan:
   - Know the current value (e.g., score = 100) → "Exact Value" scan, 4-byte integer
   - Or unknown value → "Unknown Initial Value" then filter by change type
3. Trigger value change in game (score goes from 100 → 150)
4. Next scan: "Changed Value" or "Exact Value" = 150
5. Repeat until address list is small (usually 1–5 addresses)
6. Double-click found address → edit value in Cheat Engine → value changes in game
7. For dynamic addresses: right-click → "Pointer scan for this address"
   → follow pointer chain back to a static base + offset (survives game restart)
```

**Speed hack (time scale):**
```
Cheat Engine → Enable Speedhack → set game speed to 0.5 (slowmo) or 2.0 (fast)
Works by hooking QueryPerformanceCounter / timeGetTime
```

**Floating point values:**
```
Score/currency may be stored as float or double
Scan type: Float → 4-byte or Double → 8-byte
Or: scan for "All" types when data type unknown
```

### Linux: scanmem + Python ptrace

```bash
# scanmem — interactive CLI memory scanner
sudo apt install scanmem
sudo scanmem --pid=$(pgrep game_binary)
# > 100          → scan for value 100 (current score)
# > [change score to 150 in game]
# > 150          → narrow results
# > list         → show remaining addresses (first column = match-id)
# > set 1=999999 → set match-id 1 to 999999 (or: write i32 0x7fff1234 999999)

# Python: direct /proc/<pid>/mem manipulation
python3 - <<'EOF'
import struct, sys

pid = int(sys.argv[1])
addr = int(sys.argv[2], 16)

mem = open(f'/proc/{pid}/mem', 'r+b', 0)
mem.seek(addr)
old = struct.unpack('<i', mem.read(4))[0]
print(f'At 0x{addr:x}: {old}')
mem.seek(addr)
mem.write(struct.pack('<i', 999999))
print('Patched.')
mem.close()
EOF
```

---

## Phase 3 — Game binary reversing and license bypass

Focus: find the license validation routine and patch it to always succeed.

```bash
# Ghidra / radare2 analysis
r2 -A game_binary
[0x00401000]> afl | grep -iE "license|serial|register|check|valid|crack|trial|expire"
[0x00401000]> pdf @ sym.check_license   # decompile the validation function

# Common license check patterns:
# 1. Compare serial hash against hardcoded hash → patch JNE to JMP (bypass)
# 2. Online activation via HTTP → intercept and spoof 200 OK response
# 3. Time-based trial → patch timestamp comparison or modify system time check
# 4. Dongle/HWID check → patch HWID comparison to always match
```

**Patch JNE to JMP (x86/x64) — universal bypass:**
```python
# After finding the failing comparison+jump at offset 0x1234
data = bytearray(open('game.exe','rb').read())
# JNE (75 XX) → JMP (EB XX) — unconditional jump, same relative offset
# JE  (74 XX) → NOP NOP (90 90) — skip conditional jump
data[0x1234] = 0xEB   # JNE → JMP
open('game_patched.exe','wb').write(data)
```

**HTTP-based license bypass with mitmproxy:**
```python
# mitmproxy script: intercept license response
from mitmproxy import http

def response(flow: http.HTTPFlow):
    if "license.example.com" in flow.request.pretty_host:
        # Spoof valid license response
        flow.response.set_text('{"status":"valid","expiry":"2099-01-01"}')
```

---

## Phase 4 — Game network protocol analysis

For games that submit scores, currency, or progress to a server.

```bash
# Capture game traffic
tcpdump -i eth0 -w game_session.pcap port <game_port>

# Wireshark analysis
# Look for: score submission, item purchase, match result, auth tokens
# Filter: tcp.port == <game_port> && tcp.len > 0

# Identify protocol: binary vs JSON vs Protobuf vs custom
python3 -c "
data = open('game_session.pcap','rb').read()
import re
# Detect JSON in traffic
print(re.findall(b'\{[^}]{10,200}\}', data))
"
```

**Score replay attack:**
```python
import socket, struct

# After dissecting a legitimate high-score submission packet from pcap
HOST = 'game-server.example.com'
PORT = 7777

# Craft modified score packet (identified field at offset 12, 4 bytes, big-endian)
ORIGINAL_PACKET = bytes.fromhex('...')   # from Wireshark
packet = bytearray(ORIGINAL_PACKET)
struct.pack_into('>I', packet, 12, 999999)   # overwrite score field

with socket.create_connection((HOST, PORT)) as s:
    s.send(bytes(packet))
    print(s.recv(1024))
```

**Protobuf reverse engineering:**
```bash
# If game uses gRPC or Protobuf
pip3 install blackboxprotobuf
python3 -c "
import blackboxprotobuf
data = bytes.fromhex('...')   # raw protobuf payload from pcap
msg, typedef = blackboxprotobuf.decode_message(data)
print(msg)
"
```

---

## Phase 5 — Save file analysis and tampering

```bash
# Identify save file format
find ~ -name "*.sav" -o -name "*.dat" -o -name "save*" 2>/dev/null | head -10
file save.dat

# Common formats:
# JSON → edit directly
# Binary struct → find fields with Cheat Engine memory scan matching saved values
# SQLite → sqlite3 save.db
# Encrypted → find decryption key in game binary (usually XOR or AES)

# XOR decrypt
python3 -c "
key = b'<key_from_game_binary>'
data = open('save.dat','rb').read()
out = bytes(c ^ key[i % len(key)] for i,c in enumerate(data))
open('save_decrypted.dat','wb').write(out)
"

# JSON save tampering
python3 -c "
import json
save = json.load(open('save.json'))
save['coins'] = 999999
save['level'] = 99
save['flag_unlocked'] = True
json.dump(save, open('save_modified.json','w'))
"

# Integrity checksum bypass
# Many games compute CRC32 or MD5 over save data
# After modifying, recompute checksum and update checksum field
python3 -c "
import zlib, struct
data = bytearray(open('save.dat','rb').read())
crc = zlib.crc32(bytes(data[4:]))   # checksum over data after header
struct.pack_into('<I', data, 0, crc & 0xffffffff)
open('save_fixed.dat','wb').write(data)
"
```

---

## Phase 6 — Anti-cheat analysis (authorized research)

Understanding anti-cheat mechanisms for authorized bypass research or security audits.

```bash
# Process-level anti-cheat (userspace)
# - Scans loaded modules for known cheat DLLs (signature scanning)
# - Monitors memory regions for known cheat code patterns
# - Hooks API calls (OpenProcess, ReadProcessMemory, WriteProcessMemory)
# Detection: identify which APIs are hooked via IAT/EAT inspection

# Kernel-level anti-cheat (EasyAntiCheat, BattlEye, Vanguard)
# - Loads a kernel driver → full system visibility
# - Cannot be bypassed from userspace without kernel access
# Authorized research approach:
#   - Analyze driver in isolated VM with kernel debugger attached
#   - Map IoControl codes and communication protocol with userspace agent

# Common evasion primitives (for authorized research context):
# DLL injection → hijack loaded DLL via DLL sideloading or search-order hijack
# Manual mapping → load DLL without going through LoadLibrary (bypasses DLL list scanning)
# Hypervisor-level → run game in hypervisor, hide cheat in lower ring

# For authorized assessment, focus on:
# - Which game state is validated server-side vs client-side?
# - Can the anti-cheat be detected without triggering it?
# - Does the anti-cheat protect integrity of game binaries (code signing check)?
```

---

## Quality gates

- Game binary analysis performed on isolated copy, original preserved.
- Network testing performed against authorized test server or owned account only.
- Patch applied to copy, original binary unchanged.
- All session captures and extracted data handled per engagement confidentiality rules.
- Anti-cheat research confined to isolated VM — no interaction with live competitive servers.

## Anti-patterns

- Testing memory manipulation against a live game with anti-cheat detection — triggers bans, alerts publisher security team, may be illegal without authorization.
- Distributing working cheats, bypass scripts, or cracked binaries outside the engagement scope.
- Sharing session captures or anti-cheat analysis with third parties.
- Assuming a client-side score is also accepted server-side without testing the actual server validation.

## Resources

- [references/memory-scanning.md](references/memory-scanning.md) — Cheat Engine methodology, pointer scanning, scanmem Linux workflow, Python ptrace patterns, float/double/struct value location.
