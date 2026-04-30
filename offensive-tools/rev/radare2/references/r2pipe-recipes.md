# Radare2 — r2pipe Python Scripting Recipes

## Setup

```bash
pip install r2pipe

# Verify
python3 -c "import r2pipe; r2 = r2pipe.open('/bin/ls'); print(r2.cmd('i'))"
```

## Core Pattern

```python
import r2pipe, json

# Open binary
r2 = r2pipe.open('./malware.exe')
# r2 = r2pipe.open('./malware.exe', flags=['-2'])  # suppress stderr

# Analyze
r2.cmd('aaa')           # Full analysis
r2.cmd('e io.cache=true')  # Enable write cache (for patching without modifying)

# Commands:
# r2.cmd('...')   → returns string
# r2.cmdj('...')  → parses JSON, returns Python obj
# r2.cmdf('...') → formatted output

r2.quit()
```

## Static Analysis Recipes

### Function enumeration

```python
import r2pipe

r2 = r2pipe.open('malware.exe')
r2.cmd('aaa')

# Get all functions as JSON
funcs = r2.cmdj('aflj')
print(f"Total functions: {len(funcs)}")

# Sort by size (largest first = most complex)
funcs.sort(key=lambda f: f.get('size', 0), reverse=True)
for f in funcs[:20]:
    print(f"{f['offset']:#010x}  {f['name']:40s}  {f['size']} bytes  {f.get('nbbs', 0)} blocks")
```

### Import/export triage

```python
# Imports
imports = r2.cmdj('iij')
suspicious = ['VirtualAlloc', 'VirtualProtect', 'CreateRemoteThread',
              'WriteProcessMemory', 'NtUnmapViewOfSection', 'GetProcAddress',
              'LoadLibrary', 'connect', 'send', 'recv', 'ShellExecute',
              'WinExec', 'RegSetValue', 'NtCreateThreadEx']

print("=== SUSPICIOUS IMPORTS ===")
for imp in imports:
    name = imp.get('name', '')
    if any(s.lower() in name.lower() for s in suspicious):
        print(f"  {imp['plt']:#x}  {imp['libname']}!{name}")

# Exports
exports = r2.cmdj('iEj')
for exp in exports:
    print(f"  {exp['vaddr']:#x}  {exp['name']}")
```

### String analysis

```python
# All strings
strings = r2.cmdj('izj')

KEYWORDS = ['http', 'https', 'cmd', 'exec', 'powershell', 'password',
            'key', 'token', 'inject', 'shellcode', '\\\\', 'registry',
            'SOFTWARE\\', 'Run', 'Startup']

print("=== INTERESTING STRINGS ===")
for s in strings:
    val = s.get('string', '')
    if any(kw.lower() in val.lower() for kw in KEYWORDS):
        # Get cross-references to this string
        refs = r2.cmdj(f"axtj {s['vaddr']:#x}") or []
        ref_names = []
        for ref in refs:
            func = r2.cmdj(f"afij @ {ref['from']:#x}")
            if func:
                ref_names.append(func[0].get('name', f"{ref['from']:#x}"))
        print(f"  {s['vaddr']:#x}  '{val}'  refs: {ref_names}")
```

### Cross-reference analysis

```python
# Find all calls to a specific function
def get_callers(r2, func_name):
    """Get all functions that call func_name."""
    sym = r2.cmdj(f"isj~{func_name}")
    if not sym:
        return []
    addr = sym[0].get('vaddr', 0)
    if not addr:
        return []
    refs = r2.cmdj(f"axtj {addr:#x}") or []
    callers = []
    for ref in refs:
        if ref.get('type') == 'CALL':
            func = r2.cmdj(f"afij @ {ref['from']:#x}")
            if func:
                callers.append({
                    'from': ref['from'],
                    'caller': func[0].get('name', f"{ref['from']:#x}")
                })
    return callers

for api in ['VirtualAlloc', 'connect', 'send']:
    callers = get_callers(r2, api)
    if callers:
        print(f"\n{api} called from:")
        for c in callers:
            print(f"  {c['from']:#x}  {c['caller']}")
```

### Disassemble and decompile

```python
# Disassemble a function
def disassemble_func(r2, addr):
    ops = r2.cmdj(f"pdfj @ {addr:#x}")
    if not ops:
        return
    print(f"=== {ops.get('name', 'unknown')} ===")
    for op in ops.get('ops', []):
        print(f"  {op['offset']:#x}  {op.get('disasm', '')}")

# Decompile (requires r2ghidra)
def decompile_func(r2, addr):
    r2.cmd(f"s {addr:#x}")
    code = r2.cmd('pdg')  # r2ghidra decompile
    return code

# Get all calls within a function
def get_calls_in_func(r2, addr):
    ops = r2.cmdj(f"pdfj @ {addr:#x}") or {}
    calls = []
    for op in ops.get('ops', []):
        if 'call' in op.get('type', ''):
            calls.append({
                'addr': op['offset'],
                'target': op.get('jump', 0),
                'disasm': op.get('disasm', '')
            })
    return calls
```

## Automated Malware Triage Script

```python
#!/usr/bin/env python3
"""Automated malware triage with r2pipe."""
import r2pipe, json, sys

def triage(binary_path):
    r2 = r2pipe.open(binary_path, flags=['-2'])
    r2.cmd('aaa')

    report = {"file": binary_path}

    # File info
    info = r2.cmdj('ij')
    report['arch'] = info.get('bin', {}).get('arch', '?')
    report['bits'] = info.get('bin', {}).get('bits', 0)
    report['os'] = info.get('bin', {}).get('os', '?')
    report['canary'] = info.get('bin', {}).get('canary', False)
    report['nx'] = info.get('bin', {}).get('nx', False)
    report['pic'] = info.get('bin', {}).get('pic', False)

    # Functions
    funcs = r2.cmdj('aflj') or []
    report['function_count'] = len(funcs)

    # Suspicious imports
    imports = r2.cmdj('iij') or []
    SUSPICIOUS = ['VirtualAlloc', 'CreateRemoteThread', 'WriteProcessMemory',
                  'connect', 'send', 'recv', 'GetProcAddress', 'LoadLibrary',
                  'ShellExecute', 'WinExec', 'RegSetValue']
    report['suspicious_imports'] = [
        f"{i['libname']}!{i['name']}" for i in imports
        if any(s.lower() in i.get('name', '').lower() for s in SUSPICIOUS)
    ]

    # Interesting strings
    strings = r2.cmdj('izj') or []
    KEYWORDS = ['http', 'cmd', 'exec', 'password', 'key', '\\Software\\', 'Run']
    report['interesting_strings'] = [
        s['string'] for s in strings
        if any(kw.lower() in s.get('string', '').lower() for kw in KEYWORDS)
    ][:20]

    r2.quit()
    return report

if __name__ == '__main__':
    result = triage(sys.argv[1])
    print(json.dumps(result, indent=2))
```

## Patching Recipes

```python
# Patch a JZ to JMP (bypass anti-debug jump)
r2 = r2pipe.open('target.exe', flags=['-w'])
r2.cmd('aaa')
r2.cmd('s 0x401234')
r2.cmd('wa jmp 0x401300')  # Patch JZ to JMP

# NOP out a check
r2.cmd('s 0x401200')
r2.cmd('wx 9090909090')  # 5 NOPs

# Write to file
r2.cmd('wtf patched.exe $s @ 0')  # Write full binary to file

r2.quit()
```

## r2pipe Async / Batch Processing

```python
import r2pipe, os
from pathlib import Path

def analyze_batch(directory):
    for path in Path(directory).iterdir():
        if not path.is_file():
            continue
        try:
            r2 = r2pipe.open(str(path), flags=['-2'])
            r2.cmd('aaa')
            info = r2.cmdj('ij')
            arch = info.get('bin', {}).get('arch', 'unknown')
            funcs = len(r2.cmdj('aflj') or [])
            strings = len(r2.cmdj('izj') or [])
            print(f"{path.name:40s} arch={arch:8s} funcs={funcs:4d} strings={strings:4d}")
            r2.quit()
        except Exception as e:
            print(f"{path.name}: ERROR {e}")

analyze_batch('/path/to/samples/')
```
