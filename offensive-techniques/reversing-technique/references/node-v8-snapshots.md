# Node.js / V8 Startup Snapshot Reversing

Load after `triage.md` when a `pkg`, `nexe`, or SEA executable embeds JavaScript or a V8 snapshot.

---

## Category 1: Recognition

### 1.1 Quick identification

```bash
strings binary | grep -iE "snapshot_blob|v8\.getHeap|SEA_FUSE|pkg/prelude|nexe"
strings binary | grep -E "NODE_SEA_FUSE_fce680ab2cc467b6e072b8b5df1996b2"
```

**Strong indicators by bundler:**

| Bundler | Indicator string / pattern |
|---|---|
| `pkg` (vercel) | `pkg/prelude`, `PKG_ENTRYPOINT`, `"/snapshot/"` paths in strings |
| Node.js SEA (v20+) | `NODE_SEA_FUSE_fce680ab2cc467b6e072b8b5df1996b2:<0/1>` sentinel |
| `nexe` | `NEXE_PAYLOAD_SENTINEL`, `__nexe` |
| `pkg` + snapshot | `snapshot_blob.bin` string; V8 has no fixed ASCII magic — look for the snapshot header structure and Node runtime references |

**V8 startup snapshot layout note:**
V8's `SnapshotData` header is `uint32_t`-based (`[magic|external_refs] [num_reservations] [payload_len] ...`), not a fixed ASCII string. Detect V8 snapshots by adjacency to Node runtime strings and by feeding candidate blobs to a matching Node binary (§2.2).

### 1.2 Binary structure (pkg)

A `pkg`-produced binary is:
```
[Node.js runtime binary] + [PAYLOAD SECTION] + [MANIFEST]
```

The payload section contains:
- A virtual filesystem (VFS) of JS source files or snapshot
- The entry point path

```bash
# Locate payload offset
strings -o binary | grep -i "PKG_ENTRYPOINT\|snapshot\|/snapshot/"
# Or: search for the pkg payload sentinel
python3 -c "
data = open('binary','rb').read()
pos = data.rfind(b'\\xBF\\x55\\x74\\xA2\\x4C')   # pkg payload marker (varies by version)
print(hex(pos))
"
```

### 1.3 Binary structure (Node.js SEA, v20+)

SEA does NOT append the blob after the fuse. `postject` writes the blob to a
format-specific container and flips the fuse's trailing `:0` to `:1` so the
loader knows a resource is present:

- **PE**: resource named `NODE_SEA_BLOB` (parse with `pefile` / `Resource Hacker`).
- **Mach-O**: section `NODE_SEA_BLOB` inside segment `NODE_SEA` (`otool -s NODE_SEA NODE_SEA_BLOB`).
- **ELF**: note named `NODE_SEA_BLOB` (`readelf -n` / `objcopy --dump-section`).

```bash
strings binary | grep "NODE_SEA_FUSE"          # sentinel; ends in :1 when a blob was injected

# ELF example
objcopy --dump-section .note.NODE_SEA_BLOB=sea.blob ./binary

# PE example (Python)
python3 - << 'EOF'
import pefile
pe = pefile.PE('binary.exe')
for rt in pe.DIRECTORY_ENTRY_RESOURCE.entries:
    for name in rt.directory.entries:
        if str(name.name) == 'NODE_SEA_BLOB':
            for lang in name.directory.entries:
                d = lang.data.struct
                blob = pe.get_data(d.OffsetToData, d.Size)
                open('sea.blob','wb').write(blob)
EOF

# Mach-O example
otool -s NODE_SEA NODE_SEA_BLOB ./binary       # or use lief.MachO to dump section bytes
```

---

## Category 2: Extraction Workflow

### 2.1 pkg — extract VFS (JS files)

```bash
# pkg-fetch to download the matching Node.js runtime base
npx pkg-fetch --node-range node18 --platform linux --arch x64

# pkg-js-hooks (community): extract embedded VFS
npx pkg-js-hooks extract ./target_binary ./output_dir

# Manual: search for JS source markers
strings binary | grep -E "^\s*(const|let|var|function|require|module\.exports)"

# If JS is in a V8 snapshot (not plain text), proceed to §2.2
```

### 2.2 V8 snapshot → JS recovery

When JS is compiled into a V8 startup snapshot, source is not directly present. Options:

**Option A — Run with modified Node.js (best when binary executes)**
```bash
# Run the binary while capturing snapshot deserialization output
node --snapshot-blob /dev/null target_binary 2>&1
# Or patch the binary to call v8.getHeapSnapshot() at startup
```

**Option B — `v8-snapshot-deserializer` (community tool)**
```bash
# https://github.com/nicolo-ribaudo/v8-snapshot-deserializer
node v8-snapshot-deserializer.js extracted_snapshot.bin
```

**Option C — Ghidra / radare2 static approach (partial)**
```bash
# Locate the snapshot blob in the binary
# Load as raw bytes, look for V8 context markers, string constants in the serialized heap
strings extracted_snapshot.bin | grep -E "function|require|exports"
```

**Option D — Frida dynamic extraction**
```javascript
// Hook v8::StartupData or the snapshot deserialization
// Intercept Node.js module loading
Interceptor.attach(Module.getExportByName(null, 'node::LoadEnvironment'), {
  onEnter(args) {
    // args[0] = env, args[1] = main script string
    const script = args[1].readUtf8String();
    if (script) send({ type: 'script', data: script });
  }
});
```

### 2.3 nexe extraction

```bash
pip install nexe-extract   # community tool
nexe-extract ./target_binary ./output/
# Or manually: payload is appended after Node.js binary, preceded by sentinel
strings -o binary | grep NEXE
```

---

## Category 3: JavaScript Analysis

Once JS source is recovered (plain text or partially), proceed:

### 3.1 Identify entry point

```bash
# pkg writes the entrypoint in the manifest
strings binary | grep -iE "require\(|\.\/index|\/app\.|main\.js"
# Look for the startup module path
```

### 3.2 Deobfuscation

Most `pkg`-bundled production code applies a JS obfuscator:

| Obfuscator | Indicator | Deobfuscation |
|---|---|---|
| `javascript-obfuscator` | `_0x` variable names, hex string arrays | `de4js.com`, `deobfuscate.io`, or `synchrony` |
| `UglifyJS` | Single-char variable names, no whitespace | prettier + rename pass |
| Custom eval packer | `eval(function(p,a,c,k,e,d){...})` | Run in isolated Node.js REPL + intercept eval |

**Synchrony (automated JS deobfuscation for `javascript-obfuscator` output):**
```bash
npm install -g deobfuscator     # npm package name; CLI binary is `synchrony`
synchrony obfuscated.js         # writes obfuscated.cleaned.js beside input
```

**eval interception:**
```javascript
// Run in Node.js with --inspect or via node-red
const origEval = eval;
eval = function(code) { require('fs').appendFileSync('/tmp/eval_log.js', code + '\n---\n'); return origEval(code); };
require('./obfuscated');
```

### 3.3 Locate key logic

```bash
# After deobfuscation, search for crypto, network, file ops
grep -E "crypto\.|https?\.|fs\.|child_process\.|require\(" clean.js | head -50
grep -iE "password|secret|key|token|credential|encrypt|decrypt" clean.js
```

### 3.4 Dynamic analysis

```bash
# Run with Node.js inspector
node --inspect-brk extracted.js
# Connect Chrome DevTools → chrome://inspect
# Set breakpoints on module.exports functions, crypto operations

# Or run directly and intercept at the process level
strace -e trace=network,file node extracted.js 2>&1 | head -100
```

---

## Category 4: Anti-Analysis in Bundled Executables

Some bundled executables detect analysis:
- Check `process.env.NODE_ENV` — some bundles activate debug/safe mode under known env vars
- Check `process.argv[0]` — expect the original binary name; launching as `node script.js` may bypass checks
- Integrity check on the VFS snapshot — modifying extracted JS and re-bundling may fail CRC validation

**Bypass:**
```bash
# Rename your analysis binary to match expected name
cp node custom_binary_name
./custom_binary_name extracted.js

# Or: use Frida to intercept the integrity check function
```

---

## Tool citations

- `ghidra` / `radare2` — locate snapshot blob, static string analysis
- `frida` — intercept module loading, script extraction at runtime
- `strings` — initial detection and string mining
- `pkg-js-hooks` / `pkg-fetch` — VFS extraction (external npm tools)
- `synchrony` / `deobfuscate` — JS deobfuscation (external npm tools)
- `node --inspect-brk` — browser DevTools debugging of extracted JS
