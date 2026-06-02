# Native Game Binary Reversing

Patterns for reversing native (non-Unity-Mono) game binaries: SDL, OpenGL, custom engines, C/C++ games.

---

## Quick triage

```bash
file game_binary
strings game_binary | grep -iE "flag\{|FLAG\{|CTF\{|win|complete|congratul|cheat|level|unlock"
checksec --file=game_binary

# Symbol check — unstripped binaries expose function names
nm game_binary 2>/dev/null | grep -iE "win|flag|check|level|complete|score"
# or via r2
r2 -A game_binary
[0x0]> afl | grep -iE "win|flag|check|level|score|complete"
```

---

## Win-condition patterns

### Pattern 1 — Score/state comparison

Most common: game checks a value against a threshold at level complete.

```
Ghidra / r2:
  Find the "win" function via: symbol names, strings xrefs ("You Win", "Level Complete"), or
  the function that triggers flag display.

  Look for: CMP reg, 0xNNNN (score threshold)
            JL / JNZ → "not yet" path

  Patch: JL → JMP (unconditional), OR set score via memory at runtime.
```

### Pattern 2 — Game state as crypto key (puzzle-derived key pattern)

The flag is encrypted. The decryption key is derived from the solved game state (e.g., final positions of puzzle pieces). This forces the player to actually solve the puzzle — or reverse-engineer both the crypto AND the expected solved state.

**Detection:**
```bash
# Crypto function near win-condition code
r2 -A game.exe
[0x0]> afl | grep -i "crypt\|encrypt\|decrypt\|encode\|xor\|xtea\|aes\|rc4"
# If none found: look for tight loops with XOR, ADD, SUB, ROL near win-check
[0x0]> pdf @ sym.check_win  # decompile win condition
```

**Analysis workflow:**
1. Find win-condition function (via string xref to flag display or "congratulations").
2. Trace backwards: what inputs does it take? Often: array of final positions.
3. Identify crypto function called with those inputs as key material.
4. Reverse the crypto: find algorithm, key schedule, number of rounds.
5. Option A: solve puzzle legitimately → extract key from memory → decrypt.
6. Option B: fully reverse key derivation + crypto → compute flag offline without running game.

**Common crypto in GamePwn:**
- XTEA / modified XTEA (32–64 rounds, 4-word key, delta-based)
- XOR with position-derived key
- Simple arithmetic encoding (add/subtract/XOR with tile coords)

**XTEA reverse template:**
```python
import struct

def xtea_decrypt(v, key, n_rounds=32):
    v0, v1 = v
    delta = 0x9E3779B9
    mask = 0xFFFFFFFF
    total = (delta * n_rounds) & mask
    for _ in range(n_rounds):
        # Check if key indexing is standard (sum-dependent) or fixed
        # Standard: key[(sum>>11)&3] and key[sum&3]
        # Modified variant: fixed indices regardless of sum
        v1 = (v1 - (((v0 << 4 ^ v0 >> 5) + v0) ^ (total + key[1]))) & mask
        v0 = (v0 - (((v1 << 4 ^ v1 >> 5) + v1) ^ (total + key[0]))) & mask  # note: uses updated v1
        total = (total - delta) & mask
    return v0, v1

# Key extraction: read from game memory or derive from solved state
# Game stores: box0.y, box0.x, box1.x, box2.x → key[0..3]
```

**Key insight**: Always verify the crypto implementation against standard algorithms. Modified variants (wrong key index schedule, cross-dependencies between v0/v1 updates) are common in GamePwn and will produce wrong output if you assume standard implementation.

### Pattern 3 — Level data in binary

Level/map data often stored as static arrays in `.rdata` or `.data`:
```bash
# Find level data: look for repeated small integers (tile IDs: 0-5 range)
r2 -A game.exe
[0x0]> izz | grep -i "level\|map\|tile\|grid"
# Or: trace xmm/vector loads at start of game_init → level array address

# Tile encoding examples:
# 0=empty, 1=wall, 2=target, 3=box, 4=player, 5=box-on-target
# Grid: width × height dwords at a static address
```

### Pattern 4 — Flag rendered from a static data table

Some games never store the flag as text: a static array in `.rodata`/`.data` drives the render/update loop to **draw** the flag, so it only appears on screen. Reconstruct it offline instead of playing:
- Find the entity/update function that walks an array (a `rep movsq` copy of N qwords, or an indexed loop over a fixed table); the array address resolves into a read-only section.
- Interpret the table by its consumer: pairs of doubles/floats are usually `(x, y)` points; a sentinel value (for example `(0,0)`) separates strokes/letters; an offset register advanced per group spaces them out.
- Dump the bytes at that address (`r2`: `pxq N @ addr`, or read the file offset) and **plot** the points as a polyline. The trajectory spells the flag.

```python
import struct
data = open("game","rb").read()
off, nq = 0x5060, 0x176                       # .rodata offset + qword count from the update fn
vals = struct.unpack_from("<%dd" % nq, data, off)
pts  = list(zip(vals[0::2], vals[1::2]))       # (x,y) pairs; split letters on (0,0) sentinels
# render pts as a polyline (PIL / minimal PNG) and read the drawn flag
```

### Custom asset containers

Engines ship a bespoke pack (`*.dmp`, `*.pak`, `assets.bin`). Recover the format from the loader, not by guessing:
- Read the load function: it usually loops reading a 4-byte chunk **type**, then per-type fields (`fread` calls reveal the layout). Map each type to player state, a tile/map grid (`w`,`h`, then `w*h*C` bytes), or a texture (fixed-size name, `w`, `h`, then `w*h*4` RGBA).
- Re-implement the parser in Python and dump textures as PNG; the flag is often one texture, a wall/sprite atlas, or the rendered map.

---

## Memory manipulation at runtime

When static analysis is complex, run and patch:

```bash
# Linux
scanmem --pid=$(pgrep game)
# Scan for current level/score → change to win value

# Python ptrace
python3 - <<'EOF'
import struct, sys
pid = int(sys.argv[1])
addr = int(sys.argv[2], 16)
with open(f'/proc/{pid}/mem', 'r+b') as f:
    f.seek(addr)
    f.write(struct.pack('<i', 999999))
EOF
```

---

## Binary patch for win condition

```python
# After finding comparison offset in Ghidra (e.g., JNZ at offset 0x1234)
data = bytearray(open('game_binary', 'rb').read())
data[0x1234] = 0xEB  # JNZ → JMP (unconditional)
open('game_patched', 'wb').write(data)
```

---

## SDL / SFML game specifics

SDL and SFML games follow a standard event loop:
```
poll_events() → update_state() → render() → check_win()
```

Look for the `check_win` equivalent by tracing from the render loop. In SFML, function names often survive in the binary as vtable entries or debug strings.

---

## Windows PE specifics

```bash
# r2 on Windows PE (GamePwn often targets Windows)
r2 -A game.exe   # works on Linux via r2's PE parser

# Imports reveal engine:
# SDL2.dll → SDL game
# sfml-graphics-2.dll → SFML game
# opengl32.dll → raw OpenGL

# Debug symbols: if binary is not stripped, nm/r2 afl shows real names
# If stripped: look for vtable patterns, constructor chains, string xrefs
```
