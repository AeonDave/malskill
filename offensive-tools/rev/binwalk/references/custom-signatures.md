# Binwalk — Custom Signatures & Magic Files

## Magic File Format

Binwalk uses libmagic-compatible signature files. Location: `~/.config/binwalk/magic/`

```
# Format: offset   type    value   [mask]   description
# offset: byte offset (or &offset for relative)
# type: byte, short, long, quad, string, search, regex
# value: the pattern to match
# description: shown in output

# Example: match ELF 64-bit executable at offset 0
0      string    \x7FELF                 ELF binary
>4     byte      2                       64-bit
>5     byte      1                       little-endian
>16    short     2                       executable
```

## Built-in Signatures Reference

Binwalk's default signatures are in: `/usr/lib/python3/dist-packages/binwalk/magic/`

Common files:
- `general` — generic file signatures (gzip, zip, elf, pe, etc.)
- `firmware` — firmware-specific (LZMA, u-boot, kernel)
- `crypto` — SSH keys, certificates, entropy markers
- `binwalk` — custom tool signatures

## Writing Custom Signatures

### File header detection

```
# Custom signature file: ~/.config/binwalk/magic/custom
# Detect a proprietary firmware container (MYFW header)
0       string    MYFW        MYFW firmware container
>4      long      x           version: %d
>8      long      x           length: %d bytes

# Match only if magic is MYFW and version >= 2
0       string    MYFW        MYFW v2+ firmware
>4      long      >1          \b, version %d
```

### Search pattern (not at fixed offset)

```
# Find SSL/TLS private keys anywhere in binary
0       search/4096   -----BEGIN RSA PRIVATE KEY-----   PEM RSA private key
0       search/4096   -----BEGIN EC PRIVATE KEY-----    PEM EC private key
0       search/4096   -----BEGIN PRIVATE KEY-----       PEM PKCS8 private key

# Find hardcoded C2 IPs (simple regex won't work in magic, use binwalk -R)
```

### Nested magic (after matching)

```
# LZMA inside custom container
0       string    CONTAINER   Custom container
>4      long      x           data offset: %d
# Next line is relative offset from container start
&4      string    \xFD7zXZ\x00  \b, XZ-compressed payload
```

## Using Custom Signatures

```bash
# Use specific custom magic file
binwalk -m ~/.config/binwalk/magic/custom firmware.bin

# Combine with default
binwalk firmware.bin -m my_sigs.magic

# Disable default, use only custom
binwalk --disable-extractor -m my_sigs.magic firmware.bin
```

## Extraction Rules

Custom extraction: `-D 'TYPE:EXT:COMMAND'`

```bash
# Extract all gzip files
binwalk -D 'gzip compressed data:gz:gunzip -c {filename} > {filename}.extracted' firmware.bin

# Custom extract with offset and length
binwalk -D '.*:bin:dd if={filename} bs=1 skip=%e count=%l of={filename}.raw' firmware.bin

# Extract LZO compressed
binwalk -D 'LZO.*:lzo:lzop -d {filename}' firmware.bin
```

## Binwalk -R / -B for Pattern Search

```bash
# Find all occurrences of a hex pattern
binwalk -R "\x04\x03\x02\x01" firmware.bin    # Little-endian magic

# Find hardcoded IPs
binwalk -R "\xC0\xA8" firmware.bin    # 192.168.x.x prefix

# Find null-terminated strings starting with "http"
binwalk -R "http://" firmware.bin
binwalk -R "https://" firmware.bin

# Find function prologue (x86: push rbp; mov rbp,rsp)
binwalk -R "\x55\x48\x89\xE5" firmware.bin

# Find PE files embedded in firmware
binwalk -R "\x4D\x5A\x90\x00" firmware.bin  # MZ header

# Find PKCS#8 structure (ASN.1 DER-encoded private key)
binwalk -R "\x30\x82" firmware.bin
```

## Advanced: Python API for Custom Scanning

```python
import binwalk

# Custom scan with filter
for module in binwalk.scan('firmware.bin',
                            signature=True,
                            quiet=True,
                            magic_files=['custom.magic']):
    for result in module.results:
        if result.description and 'MYFW' in result.description:
            print(f"Found at 0x{result.offset:x}: {result.description}")
            # Custom extraction logic
            with open('firmware.bin', 'rb') as f:
                f.seek(result.offset + 8)  # skip header
                data = f.read(result.length)
                with open(f'extract_{result.offset:#x}.bin', 'wb') as out:
                    out.write(data)
```

## Entropy + Custom Search Combined

```bash
# Find high-entropy regions then search for patterns at boundaries
binwalk -E firmware.bin 2>&1 | grep "Rising\|1\.000" | awk '{print $1}' | while read offset; do
    echo "High entropy at $offset:"
    binwalk -R "\x4D\x5A" -l 256 firmware.bin  # Look for PE header at boundary
done
```

## Common Firmware Patterns Cheatsheet

| Pattern | Hex | Meaning |
|---------|-----|---------|
| gzip | `1F 8B` | gzip compressed |
| LZMA | `5D 00 00` | LZMA stream |
| XZ | `FD 37 7A 58 5A 00` | XZ compressed |
| LZO | `89 4C 5A 4F 00 0D` | LZO compressed |
| SquashFS | `73 71 73 68` / `68 73 71 73` | SquashFS (LE/BE) |
| JFFS2 | `85 19 03 20` | JFFS2 filesystem |
| U-Boot | `27 05 19 56` | U-Boot image |
| DTB | `D0 0D FE ED` | Device tree blob |
| uImage | `27 05 19 56` | Linux uImage |
| ELF | `7F 45 4C 46` | ELF binary |
| PE | `4D 5A` | PE/MZ Windows binary |
