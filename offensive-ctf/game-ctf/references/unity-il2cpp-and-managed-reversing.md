# Unity Mono and IL2CPP Reversing

Load when the game artifact is a Unity build or a .NET assembly and you need to decompile, patch, or trace flag validation logic.

---

## Engine detection

```bash
# Mono (managed .NET DLLs alongside the executable)
ls <GameName>_Data/Managed/Assembly-CSharp.dll

# IL2CPP (native binary with metadata file)
ls GameAssembly.dll                                       # Windows
ls <GameName>_Data/Native/GameAssembly.so                # Linux
ls <GameName>_Data/il2cpp_data/Metadata/global-metadata.dat   # both

# Godot PCK
ls *.pck
strings binary | grep -i "godot\|GDScript"
```

---

## Mono workflow

`Assembly-CSharp.dll` is a plain .NET assembly — decompile directly.

**Tool priority:**
1. `dnSpyEx` — decompile + debug + patch; supports breakpoints and Edit Method
2. `ILSpy` / `ilspycmd` — read-only decompile on Linux or when dnSpy is unavailable
3. `dotPeek` — export full decompiled project as `.cs` files for text search

```bash
# Quick keyword scan after decompilation
ilspycmd Assembly-CSharp.dll -o decompiled/
grep -r "flag{\|flag\|win\|score\|complete\|cheat\|unlock\|GetFlag\|CheckScore" decompiled/ -i | head -30
```

**Patching in dnSpyEx:**
- Right-click any class or method → Edit Method (or Edit Class)
- Rewrite the logic (e.g., force `return true` on a check, skip an `if` block)
- Compile → File → Save Module → run the patched `.dll`

**Key Unity lifecycle methods:**
- `Start()` — runs once at spawn; inject one-shot actions here (e.g., `SceneManager.LoadScene(N)`)
- `Update()` — runs every frame; patch movement checks, score validation, or key detection here

**Runtime plugin loader (for live object inspection):**
1. Install MelonLoader (v0.5.7) pointing at the game `.exe`
2. Install CinematicUnityExplorer (Mono or IL2CPP variant) → extract to game root
3. Launch → inspect objects, force field values, call methods at runtime via UnityExplorer

---

## IL2CPP workflow

C# compiled to native ARM/x86; `GameAssembly.dll` has no readable symbols without the metadata file.

### Step 1 — Dump symbols

```bash
# Il2CppDumper: https://github.com/Perfare/Il2CppDumper
Il2CppDumper.exe GameAssembly.dll global-metadata.dat output/
# Outputs:
#   dump.cs           → all class/method/field stubs with field offsets
#   script.py         → Ghidra import script (renames all functions)
#   stringliteral.json → all string constants with addresses
```

```bash
# Search dump.cs for flag logic
grep -i "flag{\|flag\|win\|score\|GetFlag\|CheckScore\|complete\|cheat\|unlock" output/dump.cs

# Check string literals for embedded flags
python3 -c "
import json
data = json.load(open('output/stringliteral.json'))
for e in data:
    v = e.get('value', '')
    if 'flag{' in v.lower() or ('flag' in v.lower() and len(v) < 80):
        print(e)
"
```

### Step 2 — Load into Ghidra

1. Analyze `GameAssembly.dll` in Ghidra normally.
2. Run `script.py` from Il2CppDumper output → all methods are auto-renamed.
3. Search for the renamed win-condition or flag-display function and decompile.

### Step 3 — Runtime patching (IL2CPP)

```bash
# BepInEx + IL2CppInterop: inject your own C# code that calls game methods by name
# Il2CppInspector: generates a complete C++ scaffold with method pointers for DLL injection
# Use il2cpp_runtime_invoke(method_info, object, params, exception) to call any method
```

**Cpp2IL** — decompiles `GameAssembly.dll` back to pseudo-C# without metadata hunting; useful as a second pass.

---

## Godot workflow

```bash
# Extract PCK contents
gdtoolkit / Godot PCK Explorer / extract-godot-export

# Decompile GDScript bytecode back to source
gdscript-decompiler / gdsdecomp (https://github.com/GDRETools/gdsdecomp)

# Save-file locations (user://)
# Linux: ~/.local/share/<game>/
# Windows: %APPDATA%/<game>/

# Save format: binary .res/.tres → ResourceLoader.load() or binary Variant format
# Simple cheat: locate saved score/level int in the binary and flip it
```

---

## Asset extraction

| Tool | Use |
|---|---|
| AssetRipper | Export full Unity project from a build folder |
| UABE (Unity Assets Bundle Extractor) | Inspect/modify `.assets` and AssetBundles |
| UnityPy (Python) | Parse and dump `.assets` files programmatically |
| textmeshpro inspector | Extract text assets and TextAsset strings |

```python
# UnityPy: dump all TextAsset strings (flags often live here)
import UnityPy
env = UnityPy.load("path/to/sharedassets0.assets")
for obj in env.objects:
    if obj.type.name == "TextAsset":
        data = obj.read()
        print(data.name, data.text)
```

---

## Pitfalls

- Treating IL2CPP like Mono: you need `global-metadata.dat` — without it all symbols are noise.
- Patching the `.exe` instead of `Assembly-CSharp.dll` in a Mono build.
- Overlooking string literals in `stringliteral.json` for IL2CPP — flag may not be in code at all.
- Forgetting that BepInEx/MelonLoader require matching versions to the game's Unity engine build.
- Running `Save Module` in dnSpy without backing up the original DLL first.
