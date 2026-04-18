---
name: dnspy
description: ".NET assembly decompiler, debugger, and editor for reverse engineering managed binaries. Use when analyzing .NET malware (C#/VB.NET), decompiling managed executables, debugging without source code, patching .NET assemblies, or extracting configs from obfuscated .NET samples."
license: MIT
compatibility: "Windows; .NET Framework/.NET Core; github.com/dnSpyEx/dnSpy"
metadata:
  author: AeonDave
  version: "1.0"
---

# dnSpy

.NET decompiler + debugger + editor — the primary tool for reversing managed (.NET) binaries.

## Installation

```
# dnSpyEx (actively maintained fork)
# Download from https://github.com/dnSpyEx/dnSpy/releases
# Extract and run dnSpy.exe (no installation needed)

# Alternative CLI decompiler (cross-platform)
dotnet tool install --global ilspycmd
```

> **Note:** The original dnSpy by 0xd4d is archived. Use **dnSpyEx** — the active community fork.

## Quick Start

1. **File → Open** → select `.exe` or `.dll` (.NET assembly)
2. Assembly Explorer (left panel) → expand namespaces → click class/method
3. Decompiled C# appears in the main panel
4. **Right-click assembly → Go to Entry Point** to start at `Main()`
5. To debug: **Debug → Start Debugging** (F5) or **Attach to Process**

## Key Panels

| Panel | Purpose |
|-------|---------|
| Assembly Explorer | Tree view of loaded assemblies, namespaces, types |
| Decompiler | C#/VB.NET/IL decompiled source |
| Output | Debug output and log messages |
| Locals / Watch | Variable inspection during debugging |
| Call Stack | Stack trace during debugging |
| Breakpoints | Manage all breakpoints |
| Modules | Loaded assemblies/modules in debugged process |

## Navigation Shortcuts

| Key | Action |
|-----|--------|
| `Ctrl+Shift+K` | Search assemblies (types, methods, strings) |
| `Ctrl+G` | Go to token/offset |
| `F12` | Go to definition |
| `Ctrl+Shift+F` | Find all references |
| `Ctrl+D` | Go to metadata token |
| `F5` | Start/continue debugging |
| `F9` | Toggle breakpoint |
| `F10` | Step over |
| `F11` | Step into |
| `Shift+F11` | Step out |

## Malware Analysis Workflow

### Step 1: Verify .NET and detect obfuscation

Before opening in dnSpy, verify the sample is .NET:
```bash
# Check for CLI header in PE
python -c "
import struct, sys
data = open(sys.argv[1], 'rb').read()
lfanew = struct.unpack_from('<I', data, 0x3c)[0]
opt = lfanew + 4 + 20
magic = struct.unpack_from('<H', data, opt)[0]
dd_off = opt + (112 if magic == 0x10b else 128)  # data dir 14 = COM descriptor
rva = struct.unpack_from('<I', data, dd_off)[0]
print('.NET' if rva else 'Native')
" sample.exe

# Detect obfuscator
de4dot --detect sample.exe
```

Common obfuscators: ConfuserEx, .NET Reactor, SmartAssembly, Dotfuscator, Babel, Eazfuscator

### Step 2: Deobfuscate with de4dot

```bash
# de4dot: .NET deobfuscator (supports most common protections)
de4dot sample.exe -o sample_clean.exe
# For specific obfuscator:
de4dot --un-name "!^[a-zA-Z]{1,2}$" sample.exe -o sample_clean.exe
```

### Step 3: Static analysis in dnSpy

1. Open cleaned assembly → **Go to Entry Point** (`Main`)
2. Follow execution flow from `Main` through initialization
3. Search for suspicious patterns:

**Search targets (Ctrl+Shift+K):**
- `WebClient`, `HttpClient`, `WebRequest` — network communication
- `Process.Start`, `ProcessStartInfo` — command execution
- `Assembly.Load`, `Assembly.LoadFrom` — dynamic code loading
- `GetManifestResourceStream` — embedded resource extraction
- `CryptoStream`, `AesManaged`, `RijndaelManaged` — encryption
- `Convert.FromBase64String` — base64 decoding
- `Registry`, `RegistryKey` — persistence via registry
- `DllImport`, `Marshal.GetDelegateForFunctionPointer` — P/Invoke to native
- `Thread`, `Timer`, `Task.Run` — async/background execution

### Step 4: Debug to extract runtime data

1. Set breakpoint on decryption method or config loading
2. **Debug → Start Debugging** (F5)
3. When breakpoint hits:
   - **Locals** window shows decrypted values
   - Right-click variable → **Add to Watch** for complex objects
   - Use **Immediate** window to evaluate expressions
4. For encrypted C2: break after decryption, inspect the string variable

### Step 5: Edit and patch

```
# Patch a method:
1. Right-click method → Edit Method (C#)
2. Modify code (e.g., add Console.WriteLine for tracing)
3. Compile (Ctrl+Shift+P)
4. File → Save Module → save patched assembly

# Patch IL directly:
1. Right-click method → Edit IL Instructions
2. Modify opcodes
3. OK → Save Module
```

## Key .NET Analysis Patterns

### Config extraction

```
# Common patterns for embedded configs:
1. Hardcoded strings in static fields → visible in decompiler
2. Base64 in static constructor (.cctor) → decode with Convert.FromBase64String
3. Encrypted resource → GetManifestResourceStream + AES/XOR decrypt
4. Settings class → Properties.Settings or custom config class
5. Embedded JSON/XML in resources → check Resources node in Assembly Explorer
```

### Stealers (RedLine, Raccoon, etc.)

Focus areas:
- `Credentials` or `Passwords` class — browser credential theft
- `Crypto` or `Wallet` class — cryptocurrency wallet targeting
- `FileGrabber` — file exfiltration rules
- `SystemInfo` — fingerprinting methods
- `Gate` or `Panel` or `Config` — C2 URL and build config

### RATs (AsyncRAT, QuasarRAT, etc.)

Focus areas:
- `Settings` class — C2 IP/port, mutex, install path, encryption key
- `Connection` or `Client` class — C2 protocol implementation
- `Plugin` or `Commands` namespace — available capabilities
- `Install` method — persistence mechanism
- `AntiVM` or `AntiDebug` — evasion checks

### Loaders and droppers

Focus areas:
- `Main` → resource extraction → `Assembly.Load` (in-memory stage 2)
- `WebClient.DownloadData` → `Assembly.Load` (download + execute)
- `RunPE` or `Inject` method — process hollowing/injection
- Delay/sleep before payload execution (sandbox evasion)

## Resources

| File | When to load |
|------|--------------|
| [references/deobfuscation.md](references/deobfuscation.md) | Deobfuscation strategies per obfuscator family |
| [references/dotnet-malware-patterns.md](references/dotnet-malware-patterns.md) | Common .NET malware family patterns and IOC locations |
