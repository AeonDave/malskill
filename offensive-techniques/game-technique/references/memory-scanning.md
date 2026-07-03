# Game Memory Scanning Reference

Systematic workflow for locating and manipulating game state variables in process memory.

---

## Core concept

Every game state value (score, health, currency, position, ammo) lives at a memory address during runtime. The address usually changes between sessions (ASLR), but a pointer chain from a static base address leads to it. The workflow: scan → narrow → locate stable pointer → manipulate.

---

## Cheat Engine workflow (Windows)

### First scan

```
Process: Cheat Engine → File → Open Process → select game
Scan Type: "Exact Value"  for known values
           "Unknown Initial Value"  when value not known
Value Type: 4 Bytes (int32) for most score/health values
            Float for HP bars or decimal values
            8 Bytes (int64) for large currency
            Double for high-precision values

First scan: enter current in-game value (e.g., score = 0)
→ Change value in game (score becomes 100)
→ Next Scan: "Exact Value" = 100
→ Repeat until <10 results
→ Found address → change to 999999 in Cheat Engine
```

### Value type identification

```
If exact scan finds nothing:
  Try: All / Float / Double / 2 Bytes
  
If value appears encrypted/obfuscated:
  Try: "Changed Value" / "Unchanged Value" scans based on observations
  Or: find value decryption routine in binary → patch to disable encryption
```

### Pointer scanning (for stable addresses)

```
After finding dynamic address:
1. Right-click address → "Pointer scan for this address"
2. Max pointer depth: 4 (most games)
3. After pointers found: restart game, repeat value scan
4. Filter pointer list: keep entries that still resolve to the correct value
5. Stable pointer = <module_base>+<static_offset> → [+offset1] → [+offset2] → value
```

### Cheat table (.CT file)

```lua
-- Cheat Engine table entry:
[ENABLE]
<module_base>+0x1234:    -- score pointer base
mov [eax+18], #999999    -- patch at field offset

[DISABLE]
<module_base>+0x1234:
mov [eax+18], 0
```

---

## Linux: scanmem

```bash
sudo apt install scanmem

# Attach to running game
sudo scanmem --pid=$(pgrep game_binary)
# or: sudo scanmem <pid>

# Interactive session:
# > 0             ← scan for value 0 (current score)
# [change score in game to 100]
# > 100           ← narrow: scan for 100
# > list          ← show remaining addresses (first column = match-id)
# > set 1=999999  ← set match-id 1 to 999999 (or: write i32 0x7f1234 999999)
# > reset         ← clear results and start fresh
```

---

## Python: /proc/pid/mem direct read/write

```python
import struct, os

def read_int(pid, addr):
    with open(f'/proc/{pid}/mem', 'rb') as f:
        f.seek(addr)
        return struct.unpack('<i', f.read(4))[0]

def write_int(pid, addr, value):
    with open(f'/proc/{pid}/mem', 'r+b') as f:
        f.seek(addr)
        f.write(struct.pack('<i', value))

def find_in_mem(pid, value, val_type='<i', size=4):
    """Scan all readable memory regions for a value."""
    maps_file = f'/proc/{pid}/maps'
    mem_file = f'/proc/{pid}/mem'
    results = []

    target = struct.pack(val_type, value)
    with open(maps_file) as maps, open(mem_file, 'rb') as mem:
        for line in maps:
            parts = line.split()
            if 'r' not in parts[1]: continue  # skip non-readable
            start, end = (int(x, 16) for x in parts[0].split('-'))
            if end - start > 512 * 1024 * 1024: continue  # skip huge regions
            try:
                mem.seek(start)
                data = mem.read(end - start)
                offset = 0
                while True:
                    idx = data.find(target, offset)
                    if idx == -1: break
                    results.append(start + idx)
                    offset = idx + 1
            except OSError:
                pass
    return results

# Usage:
pid = int(input("PID: "))
addresses = find_in_mem(pid, 100)   # find all occurrences of value 100
print(f"Found at: {[hex(a) for a in addresses]}")
# Change score in game → call find_in_mem again with new value → intersect results
write_int(pid, addresses[0], 999999)
```

---

## Speed hack methodology

Speed hacks manipulate the game's time scale by hooking or patching the time functions it calls.

```
Windows: QueryPerformanceCounter, timeGetTime, GetTickCount
Linux: clock_gettime, gettimeofday

Cheat Engine speed hack:
  Enable → drag slider (< 1.0 = slow, > 1.0 = fast)

Manual patch (x64):
  Find: call QueryPerformanceCounter
  Patch: multiply returned value by constant (e.g., 2× for 2× speed)
  
Python LD_PRELOAD approach (Linux):
  Compile shared lib that intercepts clock_gettime and scales result
```

---

## Struct layout from Il2CppDumper (Unity)

```python
# dump.cs shows field offsets:
# public class PlayerData {
#     public int score;    // 0x18
#     public float health; // 0x1C
#     public bool hasFlag; // 0x20
# }

# Find PlayerData object pointer in memory
# Then score is at: object_ptr + 0x18
# health is at: object_ptr + 0x1C

# With Cheat Engine:
# 1. Find score value by scanning
# 2. Right-click → "Browse this memory region"
# 3. Look 0x18 bytes before found address → that's the object base
# 4. Object base + 0x20 → hasFlag boolean → set to 1
```

---

## Value types and scan settings

| In-game value | Scan type | Size | Notes |
|---------------|-----------|------|-------|
| Score, coins, kills | Exact / 4-byte int | 4 bytes | Most common |
| HP bar 0.0–1.0 | Float | 4 bytes | E.g., 0.75 for 75% HP |
| Large currency (millions) | 8-byte / int64 | 8 bytes | |
| Timer (milliseconds) | 4 or 8 byte | varies | Scan for "changed" |
| Boolean flag | 1-byte / byte | 1 byte | 0=false, 1=true |
| Encrypted value | — | — | Find decryption in binary |

---

## Encrypted values

Some anti-cheat systems XOR or rotate memory values so direct scanning fails.

```
Symptoms: exact scan finds nothing; value in memory doesn't match displayed value

Resolution:
1. Binary analysis: find decryption function called before value display
2. Identify the encryption key (often stored adjacent to encrypted value)
3. Decrypt manually: scan for the encrypted equivalent of known value
   python3 -c "print(100 ^ 0xDEAD)"  → scan for XOR result
4. Or: hook the display function and read the plaintext value before it's encrypted
```
