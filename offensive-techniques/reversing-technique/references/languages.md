# Language-Specific Reversing Techniques

Load when triage shows Go, Rust, Python, or managed-runtime patterns and you need language-specific reversing pivots.

---

## Category 1: Go Binary Reversing

### 1.1 Recognition

```bash
strings binary | grep -E '^go\.(buildid|version)'  # Build ID + version
strings binary | grep 'runtime\.'                   # Go runtime symbols
nm binary 2>/dev/null | grep 'runtime.gopanic'      # Definitive indicator
file binary                                          # "statically linked" typical
```

**Characteristics:**
- Large static binary (includes runtime + stdlib)
- All function names present in `.symtab` unless stripped
- Goroutine scheduling visible as `runtime.newproc` calls
- No null-terminated strings — all `{ptr, len}` pairs (GoString)
- Defer chains appear as `runtime.deferreturn` calls at function end

---

### 1.2 Symbol Recovery

```bash
# GoReSym: recover function names, types, interfaces even from stripped binaries
./GoReSym -d ./binary > symbols.json
# Apply to Ghidra via GoReSym Ghidra script (IDAPython port also available)

# redress: print package structure, types, interfaces
./redress -src ./binary    # Source file layout
./redress -pkg ./binary    # Package list
./redress -type ./binary   # Type definitions
./redress -interface ./binary  # Interface definitions

# pclntab: Go compiler embeds function metadata; GoReSym reads it
# Even when symbol table is stripped, pclntab often survives
```

---

### 1.3 Go Memory Layout

Understanding data structures prevents misreading register values as scalars.

```
GoString:   { ptr *byte, len int64 }             // 16 bytes on 64-bit
GoSlice:    { ptr *T, len int64, cap int64 }     // 24 bytes
GoInterface:{ type *_type, data unsafe.Pointer } // 16 bytes
GoMap:      opaque pointer to runtime.hmap
```

**In disassembly:**
```asm
; String comparison: RAX = ptr, RBX = len
; NOT null-terminated; compare (ptr, len) pairs
mov  rax, [rsp+0x10]    ; ptr
mov  rbx, [rsp+0x18]    ; len
; runtime.memequal(ptr1, ptr2, len) is the comparison function
```

---

### 1.4 Goroutines and Concurrency

```bash
# GDB with go-runtime script (ships with Go distribution)
source /usr/local/go/src/runtime/runtime-gdb.py
(gdb) info goroutines          # List all goroutines
(gdb) goroutine 5 bt           # Backtrace of goroutine 5
```

**What to look for:**
- `go func()` compiles to `runtime.newproc` call — locate the goroutine entry function
- Channels appear as `runtime.chansend`/`runtime.chanrecv` calls
- Mutexes: `sync.Mutex.Lock` → `runtime.lock2`

---

### 1.5 Decompilation Patterns

| Pattern | Go source | Disassembly signature |
|---|---|---|
| `defer` | `defer f()` | `runtime.deferreturn` at function end |
| Error return | `return value, err` | Two values in `rax`+`rbx` (or stack) at `ret` |
| String concat | `s1 + s2` | `runtime.concatstring2` call |
| Type assertion | `x.(T)` | `runtime.assertI2T` call |
| Range over string | `for _, c := range s` | UTF-8 decode: `runtime.decoderune` |

---

## Category 2: Rust Binary Reversing

### 2.1 Recognition

```bash
strings binary | grep '__rust_panic'   # Rust panic handler
nm binary | grep '_ZN'                 # Mangled Rust symbols
nm binary | grep '3std'                # std:: prefix in mangled form
```

---

### 2.2 Symbol Demangling

```bash
# rustfilt: demangle Rust symbols
nm binary | rustfilt
# or
nm binary | sed 's/.*T //' | rustfilt

# c++filt also handles Rust: use --no-params for cleaner output
nm binary | c++filt
```

**Mangled example:**
```
_ZN4core3fmt5Write9write_fmt17h1b3d8d8a2f3e4c5fE
→ core::fmt::Write::write_fmt
```

---

### 2.3 Malware-Relevant Crate Fingerprinting

Rust malware carries its dependencies statically. Cargo registry paths in `.rodata` reveal capabilities before any code analysis.

**Cargo path pattern (regex):**
```
\.cargo[/\\]registry[/\\]src[/\\][^/]+[/\\]([\w-]+)-(\d+\.\d+\.\d+)
```

**Suspicious crate → capability table:**

| Crate | Capability signal |
|---|---|
| `reqwest` / `hyper` | HTTP client / C2 communication |
| `tokio` / `async-std` | Async runtime (concurrent exfil / C2 threads) |
| `aes` / `chacha20` / `salsa20` | Symmetric encryption |
| `rsa` / `ring` | Asymmetric encryption / key wrapping |
| `base64` | Encoding (common in C2 beacons, embedded payloads) |
| `winapi` / `windows` | Windows API access (process injection, persistence) |
| `winreg` | Registry manipulation (persistence) |
| `sysinfo` | System enumeration (host fingerprinting) |
| `screenshots` | Screen capture |
| `clipboard` | Clipboard theft |
| `keylogger` | Keystroke logging |
| `zip` / `flate2` | Compression (packing exfil data) |
| `walkdir` | Filesystem traversal (data staging / ransomware targeting) |

**Notable Rust malware families:**
- **BlackCat/ALPHV** — ransomware; AES-128/XChaCha20 + RSA key wrapping; cross-platform (Windows/Linux)
- **Hive** (variants) — ransomware; `ring` crate for crypto
- **Buer Loader** — loader/dropper; embedded shellcode execution

**Quick extraction (Python):**
```python
import re, sys

data = open(sys.argv[1], 'rb').read()
pattern = re.compile(
    rb'(?:crates\.io-[a-f0-9]+/|\.cargo/registry/src/[^/]+/)'
    rb'([\w-]+)-(\d+\.\d+\.\d+)'
)
crates = {m.group(1).decode(): m.group(2).decode() for m in pattern.finditer(data)}
for name, ver in sorted(crates.items()):
    print(f'  {name} v{ver}')
```

---

### 2.4 Rust-Specific Patterns

**Result<T, E> handling:**
Functions returning `Result` use a hidden discriminant; success is typically discriminant=0, error≠0. Check the first byte (or bit) after the return value to distinguish `Ok` from `Err`.

**Option<T> patterns:**
`None` represented as 0-filled fat pointer; `Some(x)` has the pointer set.

**SIMD constant extraction (IDAPython):**
```python
import idautils, idc

for head in idautils.Heads():
    if idc.get_operand_type(head, 1) == 5:   # Memory reference
        ref = idc.get_operand_value(head, 1)
        seg = idc.get_segm_name(ref)
        if seg and 'rodata' in seg:
            data = idc.get_bytes(ref, 16)
            if data:
                print(f'{head:#x}: xmmword constant = {data.hex()}')
```

---

## Category 3: Python Bytecode

### 3.1 Reading Compiled `.pyc` Files

```bash
# Identify version from magic bytes
python3 -c "import marshal, struct, sys
data = open('file.pyc','rb').read()
print(f'Magic: {data[:4].hex()}')
"

# Disassemble (Python 3.8+)
python3 -c "
import marshal, dis
with open('file.pyc','rb') as f:
    f.read(16)  # skip header (16 bytes for 3.8+)
    code = marshal.load(f)
dis.dis(code)
"
```

**Common validation pattern:**
```text
LOAD_CONST    'expected_string'
LOAD_GLOBAL   func
LOAD_FAST     user_input
CALL_FUNCTION 1
COMPARE_OP    ==
POP_JUMP_IF_FALSE fail
```

**Even/odd index XOR pattern:**
```python
# If disassembly shows:
# candidate[i] ^ candidate[i+1] == expected[i//2]   for even i
# Then recover:
candidate = ['?'] * n
for i in range(0, n-1, 2):
    candidate[i+1] = chr(ord(candidate[i]) ^ expected[i//2])
```

---

### 3.2 Opcode Remapping

**Pattern:** A modified Python interpreter remaps opcode values. `LOAD_CONST` may be 0x84 instead of the standard 0x64, making standard `dis` output nonsense.

**Recovery:**
```python
import dis

# Find the .pyc in a PyInstaller bundle
# The interpreter binary contains the modified opcode table
# Compare custom opmap to stock opmap:
stock = {v: k for k, v in dis.opmap.items()}

# Extract custom interpreter's opcode table from the binary
# (look for a 256-byte or 512-byte table in .rodata)
# Diff custom_table vs stock_table to build a remapping dict:
remap = {}  # custom_opcode -> standard_opcode
# Then patch the .pyc bytecode:
patched = bytearray(bytecode)
for i, b in enumerate(patched):
    if b in remap:
        patched[i] = remap[b]
# Now decompile the patched bytecode with uncompyle6/pycdc
```

**Tools by Python version:**
| Python version | Decompiler |
|---|---|
| 2.x – 3.8 | `uncompyle6` |
| 3.9+ | `pycdc` (maintained fork) |
| All (disassemble only) | `dis.dis` from matching Python |

---

### 3.3 Pyarmor 8/9 (Encrypted Python Bytecode)

Pyarmor 8/9 encrypts `.pyc` with a native extension (`pyarmor_runtime`). Static decompilation is not viable; use dynamic hooks or `Pyarmor-Static-Unpack-1shot`.

```bash
# Pyarmor-Static-Unpack-1shot (Lil-House, static, Pyarmor 8.0-9.2.x):
# https://github.com/Lil-House/Pyarmor-Static-Unpack-1shot
./pyarmor-1shot /path/to/protected/scripts/   # C++ binary; produces .1shot.disasm / .1shot.cdc.py

# Output: disassembly listings and (experimental) decompiled Python source
```

**If tool fails:** Hook `marshal.loads` at runtime:
```bash
python3 -c "
import marshal, builtins
_orig = marshal.loads
def hook(b):
    code = _orig(b)
    import dis; dis.dis(code)
    return code
marshal.loads = hook
import target_script  # Import triggers decryption + our hook
"
```

---

### 3.4 PyInstaller Extraction

PyInstaller bundles `.pyc` files and the Python interpreter into a single executable. The bundle uses a custom archive format (CArchive/ZlibArchive).

```bash
# pyinstxtractor-ng (actively maintained fork — use this, not the original pyinstxtractor)
# https://github.com/pyinstxtractor/pyinstxtractor-ng
python3 pyinstxtractor-ng.py target_binary
# Output: target_binary_extracted/ directory with all .pyc files

# Navigate to the extracted directory
cd target_binary_extracted/
ls -la *.pyc         # Entry-point script (matches original script name)
ls -la PYZ-00.pyz_extracted/   # All bundled modules
```

After extraction, decompile with `pycdc` (Python 3.9+) or `uncompyle6` (2.x–3.8):
```bash
pycdc entry_point.pyc          # C++ binary from https://github.com/zrax/pycdc
pycdas entry_point.pyc         # disassembler variant when decompilation fails
```

**PyArmor v8+ note:** If the extracted `.pyc` files are PyArmor 8/9-protected (identified by `pyarmor_runtime` module in the bundle), static decompilation is not viable. Use the `marshal.loads` hook from §3.3 after extraction.

**Troubleshooting:**
- `pyinstxtractor-ng` handles Python 3.11+ magic bytes correctly; the original `pyinstxtractor` often fails on newer versions
- If the entry `.pyc` is missing, check `PYZ-00.pyz_extracted/` — some bundles hide the main module there
- Encrypted bundles (PyInstaller `--key` option): pre-Python 3.8 only; search for `tinyaes` in extracted files → AES-encrypted `.pyc.enc` files; key is in the `struct` module `.pyc`

---

### 3.5 Nuitka-Compiled Python

Nuitka compiles Python to C then to a native binary. Recovery is limited; prioritize dynamic analysis. To stub out a Nuitka module and replace with Python:

```python
# Create a stub module that matches the exported function signatures
# observed from binary analysis, then rebuild with Nuitka injecting
# tracing into the stub.
```

---

## Category 4: Managed Runtimes Beyond Base .NET Workflow

Use `dotnet-rev.md` for the main `.NET` reversing workflow. This section keeps only the runtime-specific pivots that do not belong in the base managed-assembly playbook.

### 4.1 ConfuserEx Signal

**Recognition:** Module has a `.cctor` (module static constructor) that decrypts strings/resources at load time. dnSpy shows extremely short methods or empty-looking methods.

**Useful pivot:** Let the module constructor complete, save the decrypted in-memory assembly, then continue in `dotnet-rev.md` for config/resource extraction and stage loading.

---

### 4.2 Unity IL2CPP

**Recognition:** IL2CPP binaries have:
- `GameAssembly.dll` (native, compiled IL)
- `global-metadata.dat` (contains class/method/string metadata)
- No `.NET` metadata in `GameAssembly.dll` without extraction

**Extraction workflow:**
```bash
# Il2CppDumper: extract class structure + method signatures
./Il2CppDumper GameAssembly.dll global-metadata.dat output/
# Output: dump.cs (all types/methods), il2cpp.h, script.py (Ghidra/IDA import)

# Import into Ghidra:
# Run script.py → all functions labeled with C# names

# For decompilation, use Cpp2IL (converts IL2CPP back to .NET IL):
./Cpp2IL --game-path ./Game/ --use-all-cpp2il-processing-layers
```

**Encrypted metadata detection:**
```python
with open('global-metadata.dat', 'rb') as f:
    magic = f.read(4)
if magic != b'\xAF\x1B\xB1\xFA':
    print("Metadata is encrypted or non-standard version")
```

**Key derivation for some Unity DRM implementations:**
```python
import hashlib
company_name = "MyCompany"
product_name = "MyGame"
key = hashlib.sha256(f"{company_name}\n{product_name}".encode()).digest()
# AES-128 typically uses first 16 bytes
aes_key = key[:16]
```

---

### 4.3 HarmonyOS HAP / ArkTS ABC Files

**Recognition:** `.hap` file (ZIP) contains `*.abc` (ArkCompiler Bytecode).

```bash
# Extract HAP
unzip app.hap -d app_extracted/

# Decompile ABC (Ark Bytecode). Community tools:
# - abc-decompiler (jadx + abcde): https://github.com/ohos-decompiler/abc-decompiler
# - arkdecompiler (jd-opensource):   https://github.com/jd-opensource/arkdecompiler
# - dayu (parser + rudimentary):     https://github.com/hx1997/dayu
# - abcde (Kotlin toolkit):          https://github.com/Yricky/abcde

# Example: abc-decompiler (drop modules.abc from the extracted HAP into the tool)
java -jar abc-decompiler-<version>.jar app_extracted/modules.abc

# Output: TypeScript/JavaScript approximation of the ArkTS source
```

---

## Category 5: Language-Specific Attack Patterns

### 5.1 Byte-at-a-Time Block Cipher (Zero Diffusion)

**Pattern:** Encryption is applied independently per byte (no diffusion across output bytes). Changing one input byte changes exactly one output byte.

**Detection:**
```python
import subprocess

def encrypt(input_bytes):
    # Call binary with input, capture output
    p = subprocess.run(['./binary'], input=input_bytes,
                       capture_output=True)
    return p.stdout

base = b'\x00' * 32
base_enc = encrypt(base)

# Test if byte i affects only output byte i
test = bytearray(base); test[0] = 0x01
test_enc = encrypt(bytes(test))
diffs = [i for i in range(len(base_enc)) if base_enc[i] != test_enc[i]]
print(f"Changing input[0] changes output bytes: {diffs}")
# If diffs == [0], there is no diffusion
```

**Recovery:**
```python
recovered = bytearray(32)
for pos in range(32):
    for guess in range(256):
        candidate = bytearray(b'\x00' * 32)
        candidate[pos] = guess
        enc = encrypt(bytes(candidate))
        if enc[pos] == target_enc[pos]:
            recovered[pos] = guess
            break
```

---

### 5.2 Image XOR Mask Recovery via Smoothness Scoring

**Pattern:** A pixel image is XORed with an unknown single-byte or per-row mask. The correct mask produces a smooth (natural) image; wrong masks produce noise.

```python
from PIL import Image
import numpy as np

img = np.array(Image.open('encrypted.png'))

def smoothness_score(arr):
    """Lower = smoother. Sum of absolute differences between adjacent pixels."""
    return np.abs(np.diff(arr.astype(int), axis=0)).sum() + \
           np.abs(np.diff(arr.astype(int), axis=1)).sum()

best_score, best_key = float('inf'), None
for key in range(256):
    decrypted = img ^ key
    score = smoothness_score(decrypted)
    if score < best_score:
        best_score, best_key = score, key

print(f'Best XOR key: {best_key:#04x}')
decrypted = Image.fromarray((img ^ best_key).astype(np.uint8))
decrypted.save('decrypted.png')
```

**Extension to per-row key:**
```python
keys = []
for row in range(img.shape[0]):
    row_pixels = img[row]
    best = min(range(256), key=lambda k: abs(np.diff((row_pixels ^ k).astype(int))).sum())
    keys.append(best)
# Apply: img[row] ^ keys[row]
```

---

### 5.3 GF(2^8) Gaussian Elimination for Input Recovery

**Pattern:** Validation computes linear combinations of protected input bytes over GF(2^8) and checks the results.

```python
import numpy as np

# Each equation: sum(coeff[j] * input[j]) over GF(2^8) == result[i]
# coeff matrix and results extracted from disassembly

def gf_multiply(a, b, poly=0x11b):
    result = 0
    while b:
        if b & 1: result ^= a
        a <<= 1
        if a & 0x100: a ^= poly
        b >>= 1
    return result

# Build augmented matrix [A | b] over GF(2^8)
n = len(results)
matrix = [[coeff[i][j] for j in range(n)] + [results[i]] for i in range(n)]

# Gaussian elimination over GF(2^8)
for col in range(n):
    # Find pivot
    pivot = next((r for r in range(col, n) if matrix[r][col] != 0), None)
    if pivot is None: continue
    matrix[col], matrix[pivot] = matrix[pivot], matrix[col]
    # Eliminate
    inv_pivot = pow(matrix[col][col], 254, 0x100)  # GF inverse: a^(q-2)
    for row in range(n):
        if row != col and matrix[row][col] != 0:
            factor = gf_multiply(matrix[row][col], inv_pivot)
            for j in range(n + 1):
                matrix[row][j] ^= gf_multiply(factor, matrix[col][j])

recovered = ''.join(chr(matrix[i][n]) for i in range(n))
print(f'Recovered input: {recovered}')
```

---

### 5.4 Non-Bijective Substitution Recovery

**Pattern:** Multiple input values map to the same output (non-bijective S-box). You cannot simply invert the table; use constraint solving.

```python
from z3 import *

# sbox[i] = observed table (not 1-to-1)
# encoded[i] = sbox[input[i]] for each i
# Multiple input[i] candidates per encoded[i]

solver = Solver()
input_vars = [BitVec(f'in_{i}', 8) for i in range(len(encoded))]

for i, (var, enc) in enumerate(zip(input_vars, encoded)):
    # input[i] must be printable ASCII
    solver.add(var >= 0x20, var <= 0x7e)
    # Encode must match
    solver.add(Select(sbox_array, var) == enc)

# Add any additional constraints (known prefix, charset)
solver.add(input_vars[0] == ord('A'))   # if the protected input has a known prefix

if solver.check() == sat:
    model = solver.model()
    print(''.join(chr(model[v].as_long()) for v in input_vars))
```

---

### 5.5 Mathematical Convergence Bitmap

**Pattern:** Validation classifies each input character using a mathematical process (e.g., Newton's method converging to a root). The binary calls the algorithm on each character and compares to an expected classification.

```python
import numpy as np

def converges_to(c, target_root, max_iter=1000, tol=1e-6):
    """Newton's method for a polynomial; which root does c converge to?"""
    # f(x) = x^3 - 1, roots = [1, e^(2πi/3), e^(-2πi/3)]
    z = complex(c)
    for _ in range(max_iter):
        fz = z**3 - 1
        dfz = 3 * z**2
        if abs(dfz) < tol: break
        z -= fz / dfz
    # Classify by nearest root
    roots = [1, np.exp(2j*np.pi/3), np.exp(-2j*np.pi/3)]
    return min(range(3), key=lambda i: abs(z - roots[i]))

# Expected bitmap (grid of 0/1/2 classifications) extracted from binary
# Map protected-input character space: each ASCII character maps to a classification
charset = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_!@#$%^&*'
classification_map = {c: converges_to(ord(c)/10.0, 0) for c in charset}

# Reverse: for each expected classification, find matching character
recovered = ''
for expected_class in expected_bitmap:
    candidates = [c for c, cls in classification_map.items() if cls == expected_class]
    recovered += candidates[0]   # Multiple solutions may exist; additional constraints needed
print(f'Recovered input: {recovered}')
```

---

## Common Pitfalls

1. **GoString vs C string** — Go strings are not null-terminated. Reading Go string data as a C string in GDB or IDA stops at the first `\x00` and produces wrong output. Use `{ptr, len}` to extract the correct bytes.

2. **Rust panics obscure logic** — Rust inserts panic paths for every bounds check. `panic_bounds_check` calls are noise; collapse them in Ghidra with a headless script to declutter the CFG.

3. **IL2CPP method addresses shift with patches** — Il2CppDumper offsets are absolute addresses at dump time. After any game patch, re-run the dumper; do not reuse old offsets.

4. **Opcode remapping not always uniform** — Some Python obfuscators apply position-dependent opcode remapping. Test your remap table on multiple code objects before trusting it globally.

5. **Pyarmor runtime guard** — Pyarmor 8/9 includes a runtime integrity check that detects modified `.pyc` files. Use the `pyarmor-1shot` approach (or hook `marshal.loads`) instead of patching `.pyc` directly.

6. **Image smoothness scoring requires consistent scoring metric** — If the image has a complex scene vs. a simple geometric pattern, smoothness score is less reliable. Use entropy or frequency-domain metrics as alternatives.

---

## Category 6: Nim Binary Recognition

Quick triage only. For full Nim RE methodology, load `references/nim-rev.md`.

```bash
strings binary | grep -iE "NimMain|nimGC|@\[|nimRawNew"
nm binary 2>/dev/null | grep -iE "NimMain|HEX[0-9A-F]+"
```

**Strong indicators:** `NimMain`, mangled names with `HEXnn` encoding, `@[` constants in read-only data, `*.nim:line` source annotations in strings.

→ See `references/nim-rev.md` for symbol recovery, memory layout, and decompilation patterns.

---

## Category 7: VBScript / WSH Deobfuscation

VBScript (`.vbs`) and JScript (`.js`) run through Windows Script Host (`wscript.exe` / `cscript.exe`). Common in malware droppers, living-off-the-land payloads, and obfuscated macro loaders.

### 7.1 Recognition

```bash
strings binary_or_dropper | grep -iE "wscript|cscript|\.vbs|CreateObject|WScript\.Shell"
# VBScript in-memory: look for Execute/Eval calls
strings binary | grep -iE "Execute\(|Eval\(|ExecuteGlobal"
```

**Standalone `.vbs` / `.js` files:** directly readable in a text editor; obfuscation is the main obstacle.

### 7.2 Common obfuscation patterns

| Pattern | VBScript | JScript |
|---|---|---|
| String concatenation split | `"htt" & "ps://"` | `"htt" + "ps://"` |
| Chr() encoding | `Chr(104) & Chr(116) & Chr(116)` | `String.fromCharCode(104,116,116)` |
| Reversed + reconstructed | `StrReverse("...") ` | `[...s].reverse().join('')` |
| Base64 | `certutil -decode` / `ADODB.Stream` | `atob(...)` |
| eval/Execute packer | `Execute(decoded_string)` | `eval(decoded_string)` |

### 7.3 Deobfuscation workflow

**Option A — Replace Execute/Eval with a logger (safest)**

For VBScript: replace `Execute(...)` with `MsgBox(...)` or `WScript.Echo(...)`:
```vbs
' Original (dangerous):
Execute(Shell_Code_String)

' Replace with (safe, shows decoded payload):
WScript.Echo(Shell_Code_String)
```

Run under `cscript /nologo script.vbs` in a VM — output is the decoded next stage.

**Option B — WScript.Echo instrumentation**

Insert echo calls at each decode step:
```vbs
Dim s : s = decode_function(encoded_blob)
WScript.Echo "Decoded: " & s
' Do NOT execute s; just print it
```

**Option C — CScript tracing (JScript)**

```bash
# Run with Node.js for JScript-compatible payloads
node -e "eval = function(s) { console.log('[eval]', s); }; require('./payload.js')"
```

**Option D — Automated tools**

```bash
# js-beautify: format compressed JS
npm install -g js-beautify
js-beautify obfuscated.js -o clean.js

# synchrony: cleaner for javascript-obfuscator output (npm package: deobfuscator)
npm install -g deobfuscator
synchrony clean.js       # writes clean.cleaned.js beside the input

# For VBScript: manual rewriting is usually fastest
```

### 7.4 Extracting embedded payloads

VBScript/JScript droppers often decode a second-stage payload (shellcode, PE, PowerShell):
- `ADODB.Stream` + `Chr()` decoding → binary file written to disk
- `PowerShell.Run` / `shell.exec "powershell -enc ..."` → encoded PS command
- `GetObject("script:http://...")` → remote script fetch (look for URL in strings)

**Extract the PS command:**
```bash
# Decode base64 PS payload
echo "<base64>" | base64 -d | iconv -f utf-16le -t utf-8
```

### 7.5 Pitfalls

- **Never run directly on the host** — even to "just see the output"; use an isolated VM
- `Execute` / `Eval` / `ExecuteGlobal` are semantically identical in VBScript; search for all three
- Custom `Chr()` replacements: check if the script defines its own `Chr` function with a different table
