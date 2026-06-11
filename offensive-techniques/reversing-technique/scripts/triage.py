#!/usr/bin/env python3
"""All-in-one malware triage: hashing, file identification, header parsing,
section info, and string extraction. Zero external dependencies — uses only
the Python standard library.

Usage:
    python triage.py sample.bin [--strings] [--full]

Options:
    --strings   Extract ASCII/UTF-16 strings and scan for IOC patterns
    --full      Run everything: hashes, headers, sections, strings, IOC scan
"""

import argparse
import hashlib
import math
import os
import re
import struct
import sys
from pathlib import Path

# ── Hashing ──────────────────────────────────────────────────────────────────

def compute_hashes(data: bytes) -> dict:
    return {
        "MD5": hashlib.md5(data).hexdigest(),
        "SHA1": hashlib.sha1(data).hexdigest(),
        "SHA256": hashlib.sha256(data).hexdigest(),
    }

# ── File identification ──────────────────────────────────────────────────────

MAGIC_SIGS = [
    (b"MZ", "PE executable (Windows)"),
    (b"\x7fELF", "ELF executable (Linux/Unix)"),
    (b"\xfe\xed\xfa", "Mach-O (macOS, big-endian)"),
    (b"\xcf\xfa\xed\xfe", "Mach-O 64 (macOS, little-endian)"),
    (b"\xce\xfa\xed\xfe", "Mach-O 32 (macOS, little-endian)"),
    (b"\xca\xfe\xba\xbe", "Mach-O Universal (macOS, fat)"),
    (b"PK\x03\x04", "ZIP archive (may be APK, OOXML, JAR)"),
    (b"\xd0\xcf\x11\xe0", "OLE2 Compound (Office doc/xls/ppt)"),
    (b"%PDF", "PDF document"),
    (b"\x1f\x8b", "Gzip compressed"),
    (b"BZ", "Bzip2 compressed"),
    (b"\xfd7zXZ", "XZ compressed"),
    (b"7z\xbc\xaf", "7-Zip archive"),
    (b"Rar!", "RAR archive"),
]

def identify_file(data: bytes) -> str:
    for sig, desc in MAGIC_SIGS:
        if data[:len(sig)] == sig:
            return desc
    # Check for script shebangs and text
    try:
        head = data[:512].decode("utf-8", errors="ignore")
        if head.startswith("#!"):
            return f"Script ({head.splitlines()[0]})"
        if head.startswith("<?xml") or head.startswith("<html") or head.startswith("<!DOCTYPE"):
            return "XML/HTML document"
    except Exception:
        pass
    return "Unknown binary"

# ── PE parsing ───────────────────────────────────────────────────────────────

def parse_pe(data: bytes) -> dict | None:
    if data[:2] != b"MZ":
        return None
    try:
        e_lfanew = struct.unpack_from("<I", data, 0x3C)[0]
        if data[e_lfanew:e_lfanew + 4] != b"PE\x00\x00":
            return None
        coff_off = e_lfanew + 4
        machine, num_sections, timestamp, _, _, opt_size, characteristics = struct.unpack_from(
            "<HHIIIHH", data, coff_off
        )
        machines = {0x14C: "x86", 0x8664: "x64", 0xAA64: "ARM64"}
        opt_off = coff_off + 20
        opt_magic = struct.unpack_from("<H", data, opt_off)[0]
        is_64 = opt_magic == 0x20B
        if is_64:
            entry_rva = struct.unpack_from("<I", data, opt_off + 16)[0]
            image_base = struct.unpack_from("<Q", data, opt_off + 24)[0]
        else:
            entry_rva = struct.unpack_from("<I", data, opt_off + 16)[0]
            image_base = struct.unpack_from("<I", data, opt_off + 28)[0]

        # Parse sections
        sect_off = opt_off + opt_size
        sections = []
        for i in range(num_sections):
            s = sect_off + i * 40
            name_raw = data[s:s + 8].rstrip(b"\x00").decode("ascii", errors="replace")
            vsize, rva, raw_size, raw_ptr, _, _, _, _, chars = struct.unpack_from(
                "<IIIIIIHHI", data, s + 8
            )
            ent = shannon_entropy(data[raw_ptr:raw_ptr + raw_size]) if raw_size > 0 else 0.0
            sections.append({
                "name": name_raw, "vsize": vsize, "rva": rva,
                "raw_size": raw_size, "raw_ptr": raw_ptr,
                "characteristics": f"0x{chars:08X}", "entropy": ent,
            })

        return {
            "machine": machines.get(machine, f"0x{machine:04X}"),
            "sections_count": num_sections,
            "timestamp": timestamp,
            "entry_rva": f"0x{entry_rva:08X}",
            "image_base": f"0x{image_base:016X}" if is_64 else f"0x{image_base:08X}",
            "pe_type": "PE32+" if is_64 else "PE32",
            "is_dll": bool(characteristics & 0x2000),
            "sections": sections,
        }
    except (struct.error, IndexError):
        return None

# ── ELF parsing ──────────────────────────────────────────────────────────────

def _elf_read_cstr(data: bytes, base: int, idx: int) -> str:
    """Read a null-terminated string from a string table at base+idx."""
    pos = base + idx
    if pos >= len(data):
        return ""
    end = data.find(b"\x00", pos)
    if end < 0:
        end = min(pos + 256, len(data))
    return data[pos:end].decode("ascii", errors="replace")

def parse_elf(data: bytes) -> dict | None:
    """Parse ELF header, sections (with entropy), program headers, libraries."""
    if data[:4] != b"\x7fELF":
        return None
    try:
        ei_class = data[4]  # 1 = 32-bit, 2 = 64-bit
        ei_data = data[5]   # 1 = LE, 2 = BE
        endian = "<" if ei_data == 1 else ">"
        is_64 = ei_class == 2

        # ── ELF header ───────────────────────────────────────────────────
        if is_64:
            e_type, e_machine = struct.unpack_from(f"{endian}HH", data, 16)
            e_entry = struct.unpack_from(f"{endian}Q", data, 24)[0]
            e_phoff = struct.unpack_from(f"{endian}Q", data, 32)[0]
            e_shoff = struct.unpack_from(f"{endian}Q", data, 40)[0]
            e_phentsize, e_phnum = struct.unpack_from(f"{endian}HH", data, 54)
            e_shentsize, e_shnum, e_shstrndx = struct.unpack_from(f"{endian}HHH", data, 58)
        else:
            e_type, e_machine = struct.unpack_from(f"{endian}HH", data, 16)
            e_entry = struct.unpack_from(f"{endian}I", data, 24)[0]
            e_phoff = struct.unpack_from(f"{endian}I", data, 28)[0]
            e_shoff = struct.unpack_from(f"{endian}I", data, 32)[0]
            e_phentsize, e_phnum = struct.unpack_from(f"{endian}HH", data, 42)
            e_shentsize, e_shnum, e_shstrndx = struct.unpack_from(f"{endian}HHH", data, 46)

        types = {1: "REL", 2: "EXEC", 3: "DYN (shared/PIE)", 4: "CORE"}
        machines_elf = {3: "x86", 62: "x86_64", 183: "AArch64", 40: "ARM", 8: "MIPS"}

        result = {
            "class": "ELF64" if is_64 else "ELF32",
            "type": types.get(e_type, f"0x{e_type:X}"),
            "machine": machines_elf.get(e_machine, f"0x{e_machine:X}"),
            "entry": f"0x{e_entry:X}",
            "is_stripped": True,
            "is_dynamic": False,
            "interpreter": "",
            "libraries": [],
            "sections": [],
        }

        # ── Program headers (PT_INTERP) ──────────────────────────────────
        for i in range(e_phnum):
            ph = e_phoff + i * e_phentsize
            p_type = struct.unpack_from(f"{endian}I", data, ph)[0]
            if is_64:
                p_offset = struct.unpack_from(f"{endian}Q", data, ph + 8)[0]
                p_filesz = struct.unpack_from(f"{endian}Q", data, ph + 32)[0]
            else:
                p_offset = struct.unpack_from(f"{endian}I", data, ph + 4)[0]
                p_filesz = struct.unpack_from(f"{endian}I", data, ph + 16)[0]
            if p_type == 3:  # PT_INTERP
                result["is_dynamic"] = True
                interp = data[p_offset:p_offset + p_filesz].rstrip(b"\x00")
                result["interpreter"] = interp.decode("ascii", errors="replace")

        # ── Section headers ──────────────────────────────────────────────
        if e_shnum == 0 or e_shoff == 0 or e_shstrndx >= e_shnum:
            return result

        def read_shdr(idx):
            off = e_shoff + idx * e_shentsize
            sh_name_idx = struct.unpack_from(f"{endian}I", data, off)[0]
            sh_type = struct.unpack_from(f"{endian}I", data, off + 4)[0]
            if is_64:
                sh_flags = struct.unpack_from(f"{endian}Q", data, off + 8)[0]
                sh_offset = struct.unpack_from(f"{endian}Q", data, off + 24)[0]
                sh_size = struct.unpack_from(f"{endian}Q", data, off + 32)[0]
                sh_entsize = struct.unpack_from(f"{endian}Q", data, off + 56)[0]
            else:
                sh_flags = struct.unpack_from(f"{endian}I", data, off + 8)[0]
                sh_offset = struct.unpack_from(f"{endian}I", data, off + 16)[0]
                sh_size = struct.unpack_from(f"{endian}I", data, off + 20)[0]
                sh_entsize = struct.unpack_from(f"{endian}I", data, off + 36)[0]
            return sh_name_idx, sh_type, sh_flags, sh_offset, sh_size, sh_entsize

        # String table for section names
        strtab_hdr = read_shdr(e_shstrndx)
        strtab_off = strtab_hdr[3]  # sh_offset

        SH_TYPE_NAMES = {
            0: "NULL", 1: "PROGBITS", 2: "SYMTAB", 3: "STRTAB",
            4: "RELA", 5: "HASH", 6: "DYNAMIC", 7: "NOTE",
            8: "NOBITS", 9: "REL", 11: "DYNSYM", 14: "INIT_ARRAY",
            15: "FINI_ARRAY", 0x6ffffff6: "GNU_HASH", 0x6ffffffd: "VERDEF",
            0x6ffffffe: "VERNEED", 0x6fffffff: "VERSYM",
        }

        dynstr_off = 0
        dynamic_off = dynamic_size = dynamic_entsize = 0

        for i in range(e_shnum):
            ni, sh_type, sh_flags, sh_offset, sh_size, sh_entsize = read_shdr(i)
            name = _elf_read_cstr(data, strtab_off, ni)

            if name == ".symtab":
                result["is_stripped"] = False
            if sh_type == 3 and name == ".dynstr":  # SHT_STRTAB
                dynstr_off = sh_offset
            if sh_type == 6:  # SHT_DYNAMIC
                dynamic_off = sh_offset
                dynamic_size = sh_size
                dynamic_entsize = sh_entsize if sh_entsize else (16 if is_64 else 8)

            # Flags string
            flags_parts = []
            if sh_flags & 0x2: flags_parts.append("A")
            if sh_flags & 0x1: flags_parts.append("W")
            if sh_flags & 0x4: flags_parts.append("X")
            flags_str = "".join(flags_parts) or "-"

            type_name = SH_TYPE_NAMES.get(sh_type, f"0x{sh_type:X}")

            # Entropy (skip NOBITS which has no file data)
            if sh_size > 0 and sh_type != 8:
                chunk = data[sh_offset:sh_offset + sh_size]
                ent = shannon_entropy(chunk)
            else:
                ent = 0.0

            if name:
                result["sections"].append({
                    "name": name, "type": type_name,
                    "offset": sh_offset, "size": sh_size,
                    "flags": flags_str, "entropy": ent,
                })

        # ── DT_NEEDED libraries from .dynamic ────────────────────────────
        if dynamic_off and dynstr_off:
            pos = dynamic_off
            end = dynamic_off + dynamic_size
            while pos + dynamic_entsize <= end:
                if is_64:
                    d_tag = struct.unpack_from(f"{endian}q", data, pos)[0]
                    d_val = struct.unpack_from(f"{endian}Q", data, pos + 8)[0]
                else:
                    d_tag = struct.unpack_from(f"{endian}i", data, pos)[0]
                    d_val = struct.unpack_from(f"{endian}I", data, pos + 4)[0]
                pos += dynamic_entsize
                if d_tag == 0:  # DT_NULL
                    break
                if d_tag == 1:  # DT_NEEDED
                    lib = _elf_read_cstr(data, dynstr_off, d_val)
                    if lib:
                        result["libraries"].append(lib)

        return result
    except (struct.error, IndexError):
        return None

# ── Entropy ──────────────────────────────────────────────────────────────────

def shannon_entropy(data: bytes) -> float:
    if not data:
        return 0.0
    freq = [0] * 256
    for b in data:
        freq[b] += 1
    length = len(data)
    ent = 0.0
    for count in freq:
        if count > 0:
            p = count / length
            ent -= p * math.log2(p)
    return round(ent, 4)

# ── String extraction ────────────────────────────────────────────────────────

def extract_strings(data: bytes, min_len: int = 6) -> tuple[list[str], list[str]]:
    ascii_pat = re.compile(rb"[\x20-\x7e]{" + str(min_len).encode() + rb",}")
    utf16_pat = re.compile(rb"(?:[\x20-\x7e]\x00){" + str(min_len).encode() + rb",}")
    ascii_strs = [m.group().decode("ascii") for m in ascii_pat.finditer(data)]
    utf16_strs = [m.group().decode("utf-16-le", errors="ignore") for m in utf16_pat.finditer(data)]
    return ascii_strs, utf16_strs

IOC_PATTERNS = {
    "URL": re.compile(r"https?://[^\s\"'<>]+", re.IGNORECASE),
    "IP": re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
    "Domain": re.compile(r"\b[a-z0-9][-a-z0-9]*\.[a-z]{2,}(?:\.[a-z]{2,})?\b", re.IGNORECASE),
    "Email": re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]+\b"),
    "Registry": re.compile(r"\\?(HKLM|HKCU|HKCR|HKU|HKEY_)\\[^\s\"]+", re.IGNORECASE),
    "FilePath_Win": re.compile(r"[A-Z]:\\[\w\\. -]+", re.IGNORECASE),
    "FilePath_Unix": re.compile(r"/(?:usr|etc|tmp|var|home|opt|bin|dev)/[\w/.-]+"),
    "Telegram": re.compile(r"api\.telegram\.org|bot\d{8,}:", re.IGNORECASE),
}

def scan_iocs(strings: list[str]) -> dict:
    results = {}
    combined = "\n".join(strings)
    for name, pat in IOC_PATTERNS.items():
        matches = list(set(pat.findall(combined)))
        if matches:
            results[name] = sorted(matches)
    return results

# ── Output formatting ────────────────────────────────────────────────────────

def print_banner(filepath: str, size: int):
    print("=" * 64)
    print(f"  Malware Triage — {os.path.basename(filepath)}")
    print(f"  Size: {size:,} bytes ({size / 1024:.1f} KB)")
    print("=" * 64)

def print_section(title: str):
    print(f"\n{'─' * 56}")
    print(f"  {title}")
    print(f"{'─' * 56}")

# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Malware triage — zero-dependency sample analysis")
    parser.add_argument("file", help="Path to the sample binary")
    parser.add_argument("--strings", action="store_true", help="Extract and display strings")
    parser.add_argument("--full", action="store_true", help="Run full analysis including strings + IOC scan")
    args = parser.parse_args()

    path = Path(args.file)
    if not path.is_file():
        print(f"[ERROR] File not found: {path}", file=sys.stderr)
        sys.exit(1)

    data = path.read_bytes()
    do_strings = args.strings or args.full

    print_banner(str(path), len(data))

    # Hashes
    print_section("Hashes")
    for algo, digest in compute_hashes(data).items():
        print(f"  {algo:<8s}  {digest}")

    # File type
    print_section("File Identification")
    ftype = identify_file(data)
    print(f"  Type:     {ftype}")
    ent = shannon_entropy(data)
    print(f"  Entropy:  {ent} / 8.0")
    if ent > 7.5:
        print("  [HIGH] Likely packed or encrypted")
    elif ent > 6.5:
        print("  [MODERATE] May contain compressed/encrypted sections")

    # PE parsing
    pe = parse_pe(data)
    if pe:
        print_section("PE Header")
        print(f"  Format:       {pe['pe_type']}")
        print(f"  Machine:      {pe['machine']}")
        print(f"  Entry RVA:    {pe['entry_rva']}")
        print(f"  Image Base:   {pe['image_base']}")
        print(f"  DLL:          {pe['is_dll']}")
        print(f"  Timestamp:    {pe['timestamp']}")
        print_section("Sections")
        print(f"  {'Name':<10s}  {'VSize':>8s}  {'RawSize':>8s}  {'Entropy':>7s}  Characteristics")
        for s in pe["sections"]:
            flag = " [HIGH-ENT]" if s["entropy"] > 7.0 else ""
            print(f"  {s['name']:<10s}  {s['vsize']:>8,}  {s['raw_size']:>8,}  {s['entropy']:>7.4f}  {s['characteristics']}{flag}")

    # ELF parsing
    elf = parse_elf(data)
    if elf:
        print_section("ELF Header")
        print(f"  Format:       {elf['class']}")
        print(f"  Type:         {elf['type']}")
        print(f"  Machine:      {elf['machine']}")
        print(f"  Entry:        {elf['entry']}")
        print(f"  Stripped:     {elf['is_stripped']}")
        print(f"  Dynamic:      {elf['is_dynamic']}")
        if elf["interpreter"]:
            print(f"  Interpreter:  {elf['interpreter']}")
        if elf["libraries"]:
            print(f"  Libraries:    {', '.join(elf['libraries'])}")
        if elf["sections"]:
            print_section("Sections")
            print(f"  {'Name':<16s}  {'Type':<10s}  {'Size':>10s}  {'Entropy':>7s}  Flags")
            for s in elf["sections"]:
                flag = " [HIGH-ENT]" if s["entropy"] > 7.0 else ""
                print(f"  {s['name']:<16s}  {s['type']:<10s}  {s['size']:>10,}  {s['entropy']:>7.4f}  {s['flags']}{flag}")

    # Strings
    if do_strings:
        ascii_strs, utf16_strs = extract_strings(data)
        all_strs = ascii_strs + utf16_strs
        print_section(f"Strings ({len(ascii_strs)} ASCII, {len(utf16_strs)} UTF-16)")
        if len(all_strs) > 200:
            print(f"  (showing first 200 of {len(all_strs)})")
            for s in all_strs[:200]:
                print(f"    {s}")
        else:
            for s in all_strs:
                print(f"    {s}")

        # IOC scan
        print_section("IOC Scan")
        iocs = scan_iocs(all_strs)
        if iocs:
            for ioc_type, values in iocs.items():
                print(f"\n  [{ioc_type}] ({len(values)} found)")
                for v in values[:20]:
                    print(f"    {v}")
                if len(values) > 20:
                    print(f"    ... and {len(values) - 20} more")
        else:
            print("  No IOC patterns detected in strings.")

    print(f"\n{'=' * 64}")
    print("  Triage complete.")
    print(f"{'=' * 64}")

if __name__ == "__main__":
    main()
