---
name: ghidra
description: "NSA's open-source reverse engineering suite with disassembler, decompiler, and scripting. Use when statically analyzing malware, firmware, or binaries to understand logic, find vulnerabilities, or recover algorithms."
license: MIT
compatibility: "Java 11+; Linux/macOS/Windows; GUI; github.com/NationalSecurityAgency/ghidra"
metadata:
  author: AeonDave
  version: "1.0"
---

# Ghidra

NSA open-source RE suite — disassembler + decompiler + scripting for static analysis.

## Quick Start

1. Download from ghidra-sre.org
2. `./ghidraRun` (Linux/macOS) or `ghidraRun.bat` (Windows)
3. New Project → Import File → target binary
4. Double-click to open CodeBrowser → Analyze (auto-analysis)

## Key Windows

| Window | Purpose |
|--------|---------|
| Symbol Tree | Functions, labels, imports |
| Decompiler | C pseudocode of selected function |
| Listing | Assembly view |
| Data Type Manager | Struct/enum definitions |
| Program Trees | Segments/sections |
| References | Cross-references to/from |

## Common Analysis Tasks

**Find interesting functions:**
```
Search > For Strings → look for "password", "exec", "http"
Window > Symbol Tree > Functions → filter by name
```

**Rename and annotate:**
```
Right-click function → Edit Function → rename
Right-click variable → Rename Variable
```

**Scripting (Python/Java):**
```python
# Script Manager > New Script (Python)
from ghidra.program.flatapi import FlatProgramAPI
api = FlatProgramAPI(currentProgram)
funcs = list(api.getFunctions(True))
print([f.getName() for f in funcs[:10]])
```

## Common Workflows

**Malware static analysis:**
1. Import sample → auto-analyze
2. Symbol Tree → Imports: check suspicious APIs (VirtualAlloc, CreateRemoteThread)
3. Decompile each suspicious function

**Find hardcoded credentials:**
```
Search > For Strings → password/key/secret
Double-click result → decompile surrounding function
```

## Resources

| File | When to load |
|------|--------------|
| `references/` | Script examples and struct recovery tips |
