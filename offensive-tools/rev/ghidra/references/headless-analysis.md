# Ghidra — Headless Analysis & Batch Processing

## analyzeHeadless Syntax

```bash
analyzeHeadless <project-location> <project-name> [options]

# Located at: $GHIDRA_HOME/support/analyzeHeadless
# Windows: analyzeHeadless.bat
```

## Basic Usage

```bash
# Import + analyze single binary
analyzeHeadless /tmp/ghidra_projects MyProject \
    -import /path/to/malware.exe

# Import + analyze + run a post-script
analyzeHeadless /tmp/ghidra_projects MyProject \
    -import /path/to/malware.exe \
    -postScript MyAnalysisScript.py

# Import batch (whole directory)
analyzeHeadless /tmp/ghidra_projects MyProject \
    -import /path/to/samples/ \
    -recursive

# Analyze existing project (no import)
analyzeHeadless /tmp/ghidra_projects ExistingProject \
    -process \
    -postScript ExtractReport.py

# Delete project after (clean temp projects)
analyzeHeadless /tmp/ghidra_projects TempProject \
    -import /path/to/binary \
    -postScript MyScript.py \
    -deleteProject
```

## Key Options

| Option | Purpose |
|--------|---------|
| `-import <file/dir>` | Import binary/directory |
| `-recursive` | Recurse into subdirectories |
| `-process [<file>]` | Process existing project files |
| `-postScript <script> [args]` | Run script after analysis |
| `-preScript <script>` | Run script before analysis |
| `-scriptPath <dir>` | Additional script search paths |
| `-scriptlog <file>` | Log script output to file |
| `-log <file>` | Log analyzeHeadless output |
| `-deleteProject` | Delete project after completion |
| `-overwrite` | Overwrite existing files in project |
| `-max-cpu <n>` | Max CPU threads |
| `-processor <id>` | Override processor (e.g., `x86:LE:64:default`) |
| `-cspec <id>` | Override compiler spec (e.g., `gcc`) |
| `-loader <id>` | Force specific loader |
| `-analysisTimeoutPerFile <sec>` | Timeout per file |
| `-noanalysis` | Skip analysis (import only) |

## Script Path

Ghidra looks for scripts in:
- `$HOME/ghidra_scripts/`
- `$GHIDRA_HOME/Ghidra/Features/Base/ghidra_scripts/`

Place custom scripts in `~/ghidra_scripts/` for easy access.

## Batch Malware Analysis Script

```python
# ~/ghidra_scripts/MalwareTriage.py
# @author AeonDave
# @category Analysis
# @menupath Analysis.MalwareTriage
# @toolbar

import json, os

SUSPICIOUS_APIS = [
    'VirtualAlloc', 'VirtualAllocEx', 'VirtualProtect',
    'WriteProcessMemory', 'CreateRemoteThread', 'NtCreateThreadEx',
    'LoadLibraryA', 'LoadLibraryW', 'GetProcAddress',
    'ShellExecuteA', 'ShellExecuteW', 'WinExec',
    'connect', 'send', 'recv', 'WSASend', 'WSARecv',
    'RegSetValueExA', 'RegSetValueExW', 'RegCreateKeyExA',
    'CryptEncrypt', 'CryptDecrypt',
    'NtUnmapViewOfSection', 'NtMapViewOfSection'
]

def run():
    fm = currentProgram.getFunctionManager()
    sm = currentProgram.getSymbolTable()
    rm = currentProgram.getReferenceManager()

    filename = currentProgram.getExecutablePath()
    report = {"file": os.path.basename(filename), "suspicious": {}}

    # Find suspicious API calls
    for api_name in SUSPICIOUS_APIS:
        syms = list(sm.getSymbols(api_name))
        for sym in syms:
            refs = list(rm.getReferencesTo(sym.getAddress()))
            if refs:
                callers = []
                for ref in refs:
                    func = fm.getFunctionContaining(ref.getFromAddress())
                    if func:
                        callers.append(f"{func.getName()}@{ref.getFromAddress()}")
                if callers:
                    report["suspicious"][api_name] = callers

    # Output
    output_path = f"/tmp/ghidra_reports/{report['file']}.json"
    os.makedirs("/tmp/ghidra_reports", exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(report, f, indent=2)
    println(f"Report: {output_path}")

run()
```

```bash
# Run on batch
analyzeHeadless /tmp/proj BatchScan \
    -import /samples/ \
    -recursive \
    -postScript MalwareTriage.py \
    -log /tmp/headless.log \
    -scriptlog /tmp/scripts.log \
    -deleteProject
```

## String Extraction Script

```python
# ~/ghidra_scripts/ExtractStrings.py

import json, os

def run():
    KEYWORDS = ['http', 'cmd', 'exec', 'password', 'key', 'token',
                'inject', 'shellcode', '\\\\', 'SOFTWARE\\']
    results = []
    for data in currentProgram.getListing().getDefinedData(True):
        if data.hasStringValue():
            val = str(data.getValue())
            if any(kw.lower() in val.lower() for kw in KEYWORDS):
                results.append({"addr": str(data.getAddress()), "string": val})

    fname = os.path.basename(currentProgram.getExecutablePath())
    out = f"/tmp/strings_{fname}.json"
    with open(out, 'w') as f:
        json.dump(results, f, indent=2)
    println(f"Strings written to {out}")

run()
```

## Config File for Headless Analysis

```properties
# $GHIDRA_HOME/support/analyzeHeadless.properties (create if missing)
# These set default analysis options

ANALYSIS_ENABLED=true
FUNCTION_START_SEARCH=true
STACK_ANALYSIS=true
DECOMPILER_PARAMETER_ID=true
```

## Tips for Headless Speed

```bash
# Skip decompiler analysis (faster, but no decompiled output)
analyzeHeadless /tmp/proj MyProj -import sample.exe \
    -analyzeHeadless.properties \
    -postScript FastTriage.py

# Disable specific analyzers (via pre-script)
# In pre-script:
# options = state.getTool().getOptions("Analyzers")
# options.setBoolean("Decompiler Switch Analysis.Enable", False)

# Parallel batch (process N files at once)
for f in /samples/*.exe; do
    analyzeHeadless /tmp/proj/$(basename $f) $(basename $f .exe) \
        -import "$f" -postScript MalwareTriage.py -deleteProject &
done
wait
```

## CAPA Integration (capability detection)

```bash
# After Ghidra analysis, run capa for capability fingerprinting
capa malware.exe -o json > capa_results.json
cat capa_results.json | jq '.rules | keys[]'
# Outputs: "inject shellcode", "enumerate system processes", etc.

# Combined workflow:
analyzeHeadless /tmp/proj Scan -import malware.exe \
    -postScript ExtractFunctions.py -deleteProject
capa malware.exe -o json | jq '.rules | to_entries[] | {cap: .key, score: .value.meta.scam}'
```

## Useful Headless Tools

| Tool | Purpose |
|------|---------|
| **Sekiryu** | Full headless pipeline toolkit (ghidra + scripts + reporting) — `github.com/20urc3/Sekiryu` |
| **ghidriff** | Headless binary diff engine; generates markdown diff reports — `github.com/clearbluejar/ghidriff` |
| **CERT Kaiju** | CMU malware analysis extensions for Ghidra (fn2hash, fn2yara, etc.) |
| **Ghidrathon** | Python 3 scripting support (replaces Jython 2.7) — needed for modern libs |
| **AskJOE** | Runs CAPA + imports results as Ghidra symbols/comments automatically |

```bash
# Sekiryu: run full headless analysis pipeline
sekiryu -t /path/to/samples -o /path/to/output

# ghidriff: diff two binaries headlessly
ghidriff old.exe new.exe --output report.md

# CERT Kaiju: install via Ghidra extension manager
# File → Install Extensions → select kaiju.zip
```

## Export to C Header

```bash
# From GUI: File → Export Program → C/C++ (limited)
# Better: use script

# ~/ghidra_scripts/ExportStructs.py
dtm = currentProgram.getDataTypeManager()
for dt in dtm.getAllDataTypes():
    if str(dt.getCategoryPath()).startswith("/UserDefined"):
        println(f"// {dt.getName()}")
        println(str(dt))  # C representation
```

## Automation Shell Script

```bash
#!/bin/bash
# Batch analyze samples and collect reports

GHIDRA="/opt/ghidra/support/analyzeHeadless"
SCRIPTS="$HOME/ghidra_scripts"
SAMPLES="$1"
OUT="/tmp/malware_reports"
mkdir -p "$OUT"

for sample in "$SAMPLES"/*.{exe,dll,bin}; do
    [ -f "$sample" ] || continue
    name=$(basename "$sample")
    proj_name="${name//[^a-zA-Z0-9]/_}"
    echo "[*] Analyzing $name..."

    "$GHIDRA" "$OUT/projects" "$proj_name" \
        -import "$sample" \
        -postScript MalwareTriage.py \
        -scriptPath "$SCRIPTS" \
        -log "$OUT/${proj_name}_headless.log" \
        -scriptlog "$OUT/${proj_name}_script.log" \
        -deleteProject \
        2>/dev/null

    echo "[+] Done: $name"
done

echo "[*] Reports in $OUT/"
```
