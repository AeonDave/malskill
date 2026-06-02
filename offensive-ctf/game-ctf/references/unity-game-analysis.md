# Unity Game Analysis Reference

Full workflow for analyzing Unity games in CTF challenges — both Mono and IL2CPP pipelines.

---

## Identification checklist

```
Unity Mono (old pipeline):
  ✓ <GameName>_Data/Managed/Assembly-CSharp.dll     ← main game code
  ✓ <GameName>_Data/Managed/UnityEngine.dll
  ✓ <GameName>_Data/Managed/*.dll                   ← all as .NET assemblies

Unity IL2CPP (new pipeline):
  ✓ GameAssembly.dll  (Windows)  or  libGameAssembly.so  (Linux/Android)
  ✓ <GameName>_Data/il2cpp_data/Metadata/global-metadata.dat
  ✗ No Assembly-CSharp.dll in Managed/
  
SokobanGame / native stub with Unity runtime:
  ✓ <game>.exe but NO GameAssembly.dll next to it
  ✓ Inspect EXE — if IL2CPP strings inside, unity runtime is embedded
```

---

## Unity Mono — dnSpy patching

### Locate and open

```
dnSpy → File → Open → Assembly-CSharp.dll
# Expand namespaces on left panel
# Look for: GameManager, LevelManager, WinCondition, FlagController, ScoreManager
```

### Find win condition

Common patterns to search (Edit → Find):
- `flag{` — flag may be hardcoded as a string
- `GetFlag` / `ShowFlag` / `PrintFlag`
- `WinCondition` / `CheckWin` / `GameOver`
- `score >= ` / `>= threshold` / comparison with magic number

### Patch with dnSpy

```csharp
// Example: original method compares score
public bool CheckWin() {
    return this.score >= 1000;  // → patch to: return true;
}

// dnSpy: right-click method → Edit Method (C#)
// Change body to: return true;
// Compile → File → Save Module
// Run patched game
```

**Alternative — patch the IL bytes directly:**
```
dnSpy → View method → right-click → Edit IL Instructions
Find: ldc.i4 1000 (load constant 1000)
      blt → conditional branch if less than
Change blt to br (unconditional branch) → always takes the "win" path
```

---

## Unity IL2CPP — Full workflow

### Il2CppDumper

```
Input:
  GameAssembly.dll (or .so) + global-metadata.dat

Run:
  Windows: Il2CppDumper.exe GameAssembly.dll global-metadata.dat output/
  Linux:   dotnet Il2CppDumper.dll GameAssembly.dll global-metadata.dat output/

Output files:
  output/dump.cs              ← all C# class/method/field stubs + field offsets
  output/script.py            ← Ghidra auto-rename script
  output/stringliteral.json   ← all string constants with RVA addresses
  output/il2cpp.h             ← C++ header with struct layouts
```

### Read dump.cs

```csharp
// Example dump.cs entry:
// Namespace: GameNamespace
public class GameManager : MonoBehaviour {
    // Fields: (fields are at struct offsets)
    public int score; // 0x18
    public bool hasWon; // 0x20
    
    // Methods: (virtual addresses = base + RVA)
    public void CheckWin(); // RVA: 0x123456
    public string GetFlag(); // RVA: 0x789ABC
}
```

### Ghidra analysis

```
1. Import GameAssembly.dll / GameAssembly.so into Ghidra
2. Run script.py via: Ghidra → Script Manager → Run script → output/script.py
   → All game functions renamed to C# method names
3. Search for: GameManager$$CheckWin, FlagController$$GetFlag, etc.
4. Analyze: find score comparison → patch jump or set score via memory
```

### Memory patching via Cheat Engine (Windows)

```
1. Il2CppDumper output → struct layout: score field at offset +0x18 from GameManager*
2. In game: open Cheat Engine → attach to game process
3. Scan for current score value (int32, exact)
4. Change score → win condition triggered
5. Or: use "Pointer Scan" with Il2CppDumper's object offset to find stable pointer chain
```

### stringliteral.json — flag extraction

```python
# Flag may be stored as a string literal in the binary
import json

data = json.load(open('output/stringliteral.json'))
for entry in data:
    val = entry.get('value', '')
    if 'flag{' in val or 'flag' in val.lower():
        print(f"RVA {entry['address']:#x}: {val}")

# If found, flag is at GameAssembly.dll + RVA offset in read-only data section
```

### Flag is not a literal — obfuscated string table

When `stringliteral.json` and asset/metadata strings hold no flag, the flag is decoded at runtime. A common IL2CPP obfuscator (Eazfuscator-style) keeps an internal class (often single-letter names like `a`) with:
- a static `byte[]` initialized from a `private struct` blob (the field-default-value data lives in `global-metadata.dat`, referenced by `RuntimeHelpers.InitializeArray`);
- a `.cctor` that decodes it in place with a per-index transform such as `b[i] ^= (i & 0xFF) ^ K`;
- lazy getters `a()`,`b()`,… returning slices of the decoded buffer.

Recover it offline: read the blob bytes at the metadata offset, apply the same loop, then scan the decoded buffer for printable strings. The "flag" is often not text but a **base64 image** (`iVBOR…` PNG / `/9j/…` JPEG) that `Start()` passes through `Convert.FromBase64String` → `Texture2D.LoadImage` → a `SpriteRenderer`. Decode the base64 to a PNG and read the rendered flag.

```python
meta = open("global-metadata.dat","rb").read()
off, n = 0x1609CB, 0x4E18          # struct offset + byte[] length from the .cctor / dump.cs
dec = bytes((meta[off+i] ^ (i & 0xFF) ^ 0xAA) for i in range(n))
i = dec.find(b"iVBOR")             # base64 PNG start
import re, base64
b64 = re.match(rb"[A-Za-z0-9+/]+={0,2}", dec[i:]).group(0)
open("flag.png","wb").write(base64.b64decode(b64))   # open image → flag
```

Map the helper VAs (`Convert.FromBase64String`, `ImageConversion.LoadImage`, `Texture2D..ctor`) via Il2CppDumper's `dump.cs`/`script.json` to confirm the pipeline before reversing the decoder by hand.

---

## Unity Asset extraction

### File types

| File | Content |
|------|---------|
| `sharedassets0.assets` | Textures, audio clips, text assets |
| `globalgamemanagers.assets` | Engine config, level references |
| `level0`, `level1` | Scene objects and component data |
| `resources.assets` | Bundled resources |
| `*.dmp` | Unity memory/asset dump |

### Quick strings search

```bash
# Flag may be a plaintext TextAsset embedded in the bundle
strings sharedassets0.assets | grep -i "flag{\|flag\|secret\|key" | head -10
strings globalgamemanagers.assets | grep -i "flag{"

# All printable strings ≥ 10 chars
strings -n 10 *.assets | grep -vE "^[0-9]+$" | sort -u | head -50
```

### UABE (Unity Asset Bundle Extractor)

```
UABE (Windows):
1. File → Open → sharedassets0.assets
2. Browse asset list → find TextAsset or MonoBehaviour entries
3. Select → Export Dump → view as JSON or raw bytes
4. Or: Info → for image assets → Export to .png
```

### AssetRipper (cross-platform)

```bash
# https://github.com/AssetRipper/AssetRipper
AssetRipper <game_data_folder> -o extracted_project/
# Produces: full Unity project structure
# Scripts in: extracted_project/Assets/Scripts/
# Resources in: extracted_project/Assets/Resources/
```

### Python: raw asset search

```python
import re

data = open('assets.dmp', 'rb').read()

# HTB flag pattern
flags = re.findall(b'HTB\{[^}]{1,60}\}', data)
print('Flags found:', flags)

# All printable ASCII sequences ≥ 12 chars
strings = re.findall(b'[\x20-\x7e]{12,}', data)
for s in strings:
    print(s.decode())
```

---

## Tools summary

| Tool | Use | Platform |
|------|-----|---------|
| Il2CppDumper | Dump C# class/method names from IL2CPP binary | Windows/Linux/macOS |
| dnSpy | Decompile + patch Unity Mono .NET assemblies | Windows |
| ilspycmd | Decompile Mono DLLs (CLI) | Linux/macOS |
| Ghidra | Reverse engineer GameAssembly.dll with Il2CppDumper script | Cross-platform |
| UABE | Extract/edit Unity asset bundles | Windows |
| AssetRipper | Full Unity project extraction from built game | Cross-platform |
| Cheat Engine | Memory scan and patch running Unity processes | Windows |
| scanmem | Memory scan Linux game processes | Linux |

---

## References

- Il2CppDumper: https://github.com/Perfare/Il2CppDumper
- Unity game hacking guide: https://github.com/imadr/Unity-game-hacking
- IL2CPP reversing with Ghidra: https://noob3xploiter.medium.com/hacking-and-reverse-engineering-il2cpp-games-with-ghidra-5cee894024f2
- AssetRipper: https://github.com/AssetRipper/AssetRipper
