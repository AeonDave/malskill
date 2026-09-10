# Python bytecode (.pyc) and packed Python

Load when the sample is `.pyc`, `__pycache__`, or a PyInstaller/py2exe bundle. Nuitka and similar compile to native — use ELF/PE workflow, not this file. Pyarmor / custom opcode tables: [languages.md](../../../offensive-techniques/reversing-technique/references/languages.md) (reversing-technique).

## Header (CPython 3.7+)

[PEP 552](https://peps.python.org/pep-0552/): **16 bytes**, then a `marshal` code object.

| Offset | Size | Meaning |
|---|---|---|
| 0 | 4 | Magic (`importlib.util.MAGIC_NUMBER`) |
| 4 | 4 | Flags. Bit 0 set → hash-based pyc; else timestamp+size |
| 8 | 8 | SipHash of source, or `mtime` + source size |

3.3–3.6: 12-byte header (no flags word). Pre-3.3: 8 bytes.

`marshal` code objects are **not** compatible across CPython versions. Wrong version → `ValueError`/`EOFError` or garbage. Do not `exec` recovered objects on the analysis host.

## Same-version disassembly (stdlib)

```python
import dis, importlib.util, marshal, struct, sys
from pathlib import Path

HEADER = 16  # 3.7+

def load_pyc(path: str):
    data = Path(path).read_bytes()
    magic, flags = data[:4], struct.unpack_from("<I", data, 4)[0]
    if magic != importlib.util.MAGIC_NUMBER:
        raise ValueError(
            f"pyc magic {magic.hex()} != this interpreter "
            f"{importlib.util.MAGIC_NUMBER.hex()} ({sys.version.split()[0]})"
        )
    code = marshal.loads(data[HEADER:])  # skip header; never loads() the raw file
    return code, flags

def walk(code):
    print(code.co_filename, code.co_name, code.co_consts, code.co_names)
    dis.dis(code)
    for const in code.co_consts:
        if hasattr(const, "co_code"):
            walk(const)

code, flags = load_pyc("module.cpython-314.pyc")
walk(code)
```

`co_consts` / `co_names` often yield C2 strings and API names without a decompiler.

## Cross-version

- **Disassemble another version’s `.pyc`**: `pydisasm` from [xdis](https://github.com/rocky/python-xdis) (magic table includes 3.14). Do not `marshal.loads` it under 3.14.7 if the magic differs.
- **Decompile to source** (opportunistic, lags CPython):
  - `uncompyle6`: through **3.8** only
  - `pycdc`/`pycdas` ([zrax/pycdc](https://github.com/zrax/pycdc)): try it; **3.13–3.14 often `Bad MAGIC` or incomplete** — fall back to `dis`/`pydisasm`
- Matching `pythonX.Y -c "import dis,marshal,..."` is the ground-truth disassembler for that bytecode.

## PyInstaller

Prefer [pyinstxtractor-ng](https://github.com/pyinstxtractor/pyinstxtractor-ng) (fixes pyc headers; current PyInstaller PE **and** ELF). Run it with a Python **close to the bundle’s** version so PYZ `marshal` succeeds.

```text
python pyinstxtractor-ng.py target.exe
# target.exe_extracted/<entry>.pyc
# target.exe_extracted/PYZ-00.pyz_extracted/*.pyc
```

Then treat files as `.pyc` above. Encrypted archives (`--key` / tinyaes): extractor must decrypt; if PYZ fails, look for `.pyc.enc` and the key in the extracted `struct` module — same recovery as in `reversing-technique` languages.md.

py2exe / cx_Freeze: overlay or `PYTHONSCRIPT` resource → extract raw marshal/pyc, then this header skip.

## Anti-patterns

- `marshal.load(open("foo.pyc","rb"))` without skipping the 16-byte header.
- Trusting a decompiler on 3.12–3.14 while `dis` already shows the algorithm.
- Using this interpreter’s `dis.opmap` on another version’s `co_code`.

## References

- https://peps.python.org/pep-0552/
- https://docs.python.org/3/library/marshal.html
- https://docs.python.org/3/library/dis.html
- https://github.com/rocky/python-xdis
- https://github.com/pyinstxtractor/pyinstxtractor-ng
