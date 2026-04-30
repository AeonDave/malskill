# dnSpy — .NET Deobfuscation Guide

## Obfuscator Detection

```bash
# de4dot: detect obfuscator before trying to decompile
de4dot --detect sample.exe

# Common outputs:
# Detected: ConfuserEx
# Detected: .NET Reactor
# Detected: SmartAssembly
# Detected: Dotfuscator
# Detected: Babel
# Detected: Eazfuscator
# Detected: Agile.NET
```

## de4dot — Primary Deobfuscation Tool

```bash
# Install
# Download from https://github.com/de4dot/de4dot/releases
# or: dotnet tool install -g de4dot (community forks)

# Auto-detect and deobfuscate
de4dot sample.exe -o clean.exe

# Force specific obfuscator (when auto-detect fails)
de4dot --un-type confuserex sample.exe -o clean.exe
de4dot --un-type netreactor sample.exe -o clean.exe
de4dot --un-type smartassembly sample.exe -o clean.exe

# Rename meaningless method/type names
de4dot --un-name "!^[a-zA-Z_][a-zA-Z0-9_]{1,20}$" sample.exe -o clean.exe

# Decrypt strings and remove protection (some obfuscators only)
de4dot --strtyp delegate --strtok 06000123 sample.exe
```

## Obfuscator-Specific Strategies

### ConfuserEx

Most common for malware. Common protections: Anti-Tamper, Anti-Debug, Junk Code, Control Flow, String Encryption, Resource Encryption.

```bash
# Basic deobfuscation
de4dot sample.exe -o clean.exe

# If de4dot fails, try dnlib-based tools:
# NoFuserEx, ConfuserExStringDecryptor

# Manual: find the string decrypt method
# Search: "GetString" or "StringDecryptor" class
# Break on it in debugger → extract decrypted strings from Locals window
```

**Control flow obfuscation**: Junk jumps, opaque predicates.
- Strategy: Use dnSpy debugger → step through → understand actual flow
- In decompiler: look for `if (true) {...}` patterns = junk

### .NET Reactor

Commercial packer. Wraps assembly in native stub.

```bash
de4dot --un-type netreactor sample.exe -o clean.exe

# If native unpacking stub detected:
# 1. Run sample under dnSpy debugger
# 2. Break at Assembly.Load or Assembly.LoadFrom
# 3. Dump the loaded assembly from memory (Scylla for .NET or manual)
```

### SmartAssembly

```bash
de4dot --un-type smartassembly sample.exe -o clean.exe
# Usually works well with de4dot
```

### Eazfuscator / Obfuscar / Babel

```bash
de4dot sample.exe -o clean.exe  # Try auto first

# Eazfuscator string encryption: method call that returns string
# Find the decrypt method → trace to get key → write custom decryptor
```

### Custom / Unknown Obfuscation

**String decryption — manual approach:**

1. In dnSpy: search `Ctrl+Shift+K` → "strings" or look for class `StringTable`, `RC4`, `AES`
2. Find the decrypt method (often takes an index/ID and returns string)
3. Set breakpoint on it → run → Locals shows decrypted value
4. Alternatively: copy decrypt logic to a test project and run it

```csharp
// Example: decode all strings by calling the obfuscated decrypt method via reflection
using System.Reflection;
Assembly asm = Assembly.LoadFile("sample.exe");
Type decryptType = asm.GetType("Namespace.StringDecryptor");
MethodInfo decryptMethod = decryptType.GetMethod("Decrypt",
    BindingFlags.Static | BindingFlags.Public | BindingFlags.NonPublic);
// Enumerate expected string IDs (0..N) and call decrypt
for (int i = 0; i < 1000; i++) {
    try {
        string result = (string)decryptMethod.Invoke(null, new object[] { i });
        Console.WriteLine($"{i}: {result}");
    } catch { }
}
```

## Manual Deobfuscation in dnSpy

### Control flow flattening

Pattern: large switch statement, fake state machine.

```
1. Identify the dispatcher (central switch)
2. Trace each case — note the real execution order
3. Manually re-order in your notes
4. Or: use debugger, trace → Export to C# from dynamic view
```

### String encryption patterns

| Pattern | Location in Code |
|---------|-----------------|
| Index-based | `strings[42]` — find strings array |
| Method call | `Decrypt(42)` — break on Decrypt method |
| XOR in static ctor | `.cctor` — decode from bytes |
| Resource stream | `GetManifestResourceStream` + AES decrypt |
| Base64 | `Convert.FromBase64String` |

### Proxy method removal

Pattern: `private static void m000(int a, string b) => realMethod(a, b)`

- In dnSpy: these show as wrappers around real calls
- Find the real method via Go to Definition

## Dynamic String Extraction via dnSpy

```
1. Open sample in dnSpy
2. Find string decrypt method
3. Right-click method → Analyze → Used By (where it's called)
4. Set breakpoint at the method's return statement
5. Debug → Start Debugging
6. In Locals: inspect return value for each hit
7. Use Immediate Window: evaluate expressions to batch-call decrypt
```

**Immediate Window trick:**
```csharp
// In dnSpy Immediate window (C# expression evaluator):
// Call the decrypt method for all IDs:
for (int i = 0; i < 500; i++) StringTable.Decrypt(i)
```

## Rebuild Import Table After Deobfuscation

After deobfuscation, imports may be renamed. Rebuild:

```bash
# Recompile with ILDASM + ILASM
ildasm clean.exe /out:clean.il
ilasm clean.il /output:rebuilt.exe

# Or use dnSpy's Save Module (File → Save Module → clean.exe)
```

## Useful de4dot Options

```bash
# Preserve all token values (important for some samples)
de4dot --preserve-tokens sample.exe -o clean.exe

# Decode encrypted resources
de4dot --decrypt-methods --preserve-tokens sample.exe -o clean.exe

# Don't rename types/methods (keep obfuscated names)
de4dot --dont-rename sample.exe -o clean.exe

# Keep all obfuscated names but decrypt strings only
de4dot --keep-types --str-typ delegate --str-tok 0x06001234 sample.exe -o clean.exe
```
