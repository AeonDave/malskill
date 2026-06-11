# Document and Script Analysis Procedure

Detailed workflow for analyzing Office documents, PDFs, and script-based malware. Load this reference when the sample is a document or script file.

## Office Documents (OLE2 / OOXML)

### Identification

- `.doc`, `.xls`, `.ppt` → OLE2 (Compound Binary Format), magic: `\xD0\xCF\x11\xE0`
- `.docx`, `.xlsx`, `.pptx` → OOXML (ZIP-based), magic: `PK\x03\x04`
- `.docm`, `.xlsm` → OOXML with macros

### OLE2 analysis

```bash
# Identify suspicious indicators
oleid sample.doc

# Extract and analyze VBA macros
olevba sample.doc
olevba --deobf sample.doc    # Attempt deobfuscation

# Stream explorer
oledump.py sample.doc
oledump.py -s <stream_num> -v sample.doc   # Dump specific stream
```

Python fallback (when oletools not installed):
```python
import zipfile, re
# For OOXML — just a ZIP
with zipfile.ZipFile("sample.docm") as z:
    for name in z.namelist():
        if "vbaProject" in name or "macro" in name.lower():
            print(f"Macro container: {name}")
```

### OOXML analysis

1. Unzip and inspect structure: `unzip -l sample.docx`
2. Check `word/_rels/document.xml.rels` for external template references (template injection)
3. Check `[Content_Types].xml` for embedded objects (OLE, ActiveX)
4. Search XML for: external URLs, `oleObject`, `Target=`, `mso-application`
5. Extract `word/vbaProject.bin` and analyze with `olevba`

### What to look for in macros

**Auto-execute triggers:**
- `AutoOpen`, `Auto_Open`, `Document_Open`, `Workbook_Open`
- `AutoClose`, `Document_Close`
- `AutoExec`, `Auto_Exec`

**Suspicious patterns:**
- `Shell()`, `WScript.Shell`, `CreateObject`
- `Environ()` — environment variable access
- PowerShell invocation: `powershell`, `-enc`, `-encodedcommand`
- LOLBins: `certutil`, `bitsadmin`, `mshta`, `rundll32`, `regsvr32`
- String obfuscation: `Chr()`, `ChrW()`, `Asc()`, numeric arrays, `Split()`/`Join()`
- `MSXML2.XMLHTTP`, `WinHttpRequest` — HTTP downloads
- `ADODB.Stream` — binary file writing

### Deobfuscation strategy

1. Collect all `Chr()`/`ChrW()` calls → rebuild string
2. Base64 decode any `-enc` PowerShell commands
3. Reconstruct concatenated strings
4. If heavily obfuscated, write a minimal Python decoder on the extracted code (do not execute the macro)

## PDF Analysis

### Identification
Magic: `%PDF`

### Key objects to examine

```bash
# If pdfid/pdf-parser are available (from Didier Stevens tools):
pdfid sample.pdf
pdf-parser --stats sample.pdf
pdf-parser --object <num> sample.pdf

# Python with pikepdf:
python3 -c "import pikepdf; pdf = pikepdf.open('sample.pdf'); print(pdf.pages)"
```

**Suspicious elements:**
- `/JavaScript` or `/JS` — embedded JavaScript
- `/OpenAction` or `/AA` — auto-execute actions
- `/Launch` — launch external application
- `/EmbeddedFile` — embedded file stream
- `/URI` — URL reference
- `/AcroForm` — forms with submit actions

### PDF exploitation patterns
- JavaScript heap spray → exploit viewer vulnerability
- Embedded EXE in `/EmbeddedFile` with auto-launch
- XFA forms with malicious scripting
- `/URI` pointing to malicious download

## Script-based Malware

### JavaScript (.js, .jse)

1. Beautify/deobfuscate minified code
2. Look for: `WScript.Shell`, `ActiveXObject`, `eval()`, `new Function()`, `document.write` in HTA context
3. Track variable assignments — reconstruct obfuscated strings
4. Identify download-execute: `XMLHTTP`, `ADODB.Stream`, `Shell.Run`

### VBScript (.vbs, .vbe)

1. VBE files: decode VBScript encoding (well-known algorithm, Python can decode)
2. Look for: `CreateObject`, `WScript.Shell`, `Shell.Run`, `Environ`
3. Similar deobfuscation to VBA macros

### PowerShell (.ps1, encoded commands)

1. Decode `-EncodedCommand`: `echo <base64> | base64 -d` or Python `base64.b64decode()`
2. Look for: `IEX`, `Invoke-Expression`, `DownloadString`, `DownloadFile`, `WebClient`, `Start-Process`
3. AMSI bypass patterns: `[Ref].Assembly`, `amsiInitFailed`, patching `AmsiScanBuffer`
4. Multi-layer: decoded PS often contains another encoded layer → decode iteratively

### HTA (.hta)

Combination of HTML + VBScript/JScript:
1. Parse as HTML, extract `<script>` blocks
2. Follow VBS/JS analysis patterns above
3. Often used as first-stage dropper via `mshta.exe`

### Batch / CMD (.bat, .cmd)

1. Look for: `certutil -decode`, `bitsadmin /transfer`, `powershell -enc`, `start /b`
2. Variable obfuscation: `%var:~start,len%` substring extraction
3. `set` commands building strings character by character

## HTML Smuggling

1. Identify: `Blob`, `URL.createObjectURL`, `download`, `atob()`, `Uint8Array`
2. Embedded payload usually base64-encoded in JS
3. Reconstruct: decode base64 → result is typically a ZIP/ISO/IMG containing the actual payload
4. Check for anti-sandbox: `navigator.userAgent` checks, timing delays

## Webshells

1. Identify language: PHP (`eval`, `system`, `exec`, `passthru`), ASP/ASPX (`Process.Start`, `cmd.exe`), JSP (`Runtime.exec`)
2. Look for: authentication gates (password check), file upload/download, command execution
3. Check for obfuscation: `base64_decode`, `str_rot13`, `gzinflate`, variable functions (`$_GET['cmd']($arg)`)
4. Extract C2 indicators: callback URLs, exfiltration endpoints
