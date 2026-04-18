#!/usr/bin/env python3
"""Per-section and sliding-window entropy analysis with region classification.
Zero external dependencies.

Usage:
    python entropy_scan.py sample.bin [--block-size 1024] [--threshold 7.0]

Classifies regions as:
  ENCRYPTED  — high entropy (>7.0), uniform byte distribution (low chi²)
  COMPRESSED — high entropy (>7.0), skewed byte distribution (high chi²)
  CODE       — medium entropy (4.5–7.0)
  STRUCTURED — low-medium entropy (2.0–4.5), likely data/config
  PADDING    — very low entropy (<2.0) or near-zero unique bytes
"""

import argparse
import math
import struct
import sys
from pathlib import Path

# ── Entropy and statistics ───────────────────────────────────────────────────

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

def chi_squared(data: bytes) -> float:
    """Chi-squared test vs uniform distribution. Low value = uniform (encrypted)."""
    if not data:
        return 0.0
    freq = [0] * 256
    for b in data:
        freq[b] += 1
    expected = len(data) / 256.0
    return sum((f - expected) ** 2 / expected for f in freq)

def classify_region(entropy: float, chi2: float, size: int) -> str:
    if size < 16:
        return "PADDING"
    if entropy < 2.0:
        return "PADDING"
    if entropy < 4.5:
        return "STRUCTURED"
    if entropy < 7.0:
        return "CODE"
    # High entropy — distinguish encrypted vs compressed
    if chi2 < 500:
        return "ENCRYPTED"
    return "COMPRESSED"

# ── PE section parsing ───────────────────────────────────────────────────────

def parse_pe_sections(data: bytes) -> list[dict] | None:
    if data[:2] != b"MZ":
        return None
    try:
        e_lfanew = struct.unpack_from("<I", data, 0x3C)[0]
        if data[e_lfanew:e_lfanew + 4] != b"PE\x00\x00":
            return None
        coff_off = e_lfanew + 4
        _, num_sections, _, _, _, opt_size, _ = struct.unpack_from("<HHIIIHH", data, coff_off)
        sect_off = coff_off + 20 + opt_size
        sections = []
        for i in range(num_sections):
            s = sect_off + i * 40
            name = data[s:s + 8].rstrip(b"\x00").decode("ascii", errors="replace")
            _, _, raw_size, raw_ptr = struct.unpack_from("<IIII", data, s + 8)
            sections.append({"name": name, "offset": raw_ptr, "size": raw_size})
        return sections
    except (struct.error, IndexError):
        return None

# ── ELF section parsing ─────────────────────────────────────────────────────

def parse_elf_sections(data: bytes) -> list[dict] | None:
    if data[:4] != b"\x7fELF":
        return None
    try:
        is_64 = data[4] == 2
        endian = "<" if data[5] == 1 else ">"
        if is_64:
            e_shoff = struct.unpack_from(f"{endian}Q", data, 40)[0]
            e_shentsize = struct.unpack_from(f"{endian}H", data, 58)[0]
            e_shnum = struct.unpack_from(f"{endian}H", data, 60)[0]
            e_shstrndx = struct.unpack_from(f"{endian}H", data, 62)[0]
        else:
            e_shoff = struct.unpack_from(f"{endian}I", data, 32)[0]
            e_shentsize = struct.unpack_from(f"{endian}H", data, 46)[0]
            e_shnum = struct.unpack_from(f"{endian}H", data, 48)[0]
            e_shstrndx = struct.unpack_from(f"{endian}H", data, 50)[0]

        # Read string table section header
        strtab_hdr = e_shoff + e_shstrndx * e_shentsize
        if is_64:
            strtab_off = struct.unpack_from(f"{endian}Q", data, strtab_hdr + 24)[0]
        else:
            strtab_off = struct.unpack_from(f"{endian}I", data, strtab_hdr + 16)[0]

        sections = []
        for i in range(e_shnum):
            hdr = e_shoff + i * e_shentsize
            name_idx = struct.unpack_from(f"{endian}I", data, hdr)[0]
            if is_64:
                sh_offset = struct.unpack_from(f"{endian}Q", data, hdr + 24)[0]
                sh_size = struct.unpack_from(f"{endian}Q", data, hdr + 32)[0]
            else:
                sh_offset = struct.unpack_from(f"{endian}I", data, hdr + 16)[0]
                sh_size = struct.unpack_from(f"{endian}I", data, hdr + 20)[0]
            # Read name from string table
            name_end = data.index(b"\x00", strtab_off + name_idx)
            name = data[strtab_off + name_idx:name_end].decode("ascii", errors="replace")
            if name and sh_size > 0:
                sections.append({"name": name, "offset": sh_offset, "size": sh_size})
        return sections
    except (struct.error, IndexError, ValueError):
        return None

# ── Sliding window analysis ──────────────────────────────────────────────────

def sliding_window_entropy(data: bytes, block_size: int) -> list[dict]:
    blocks = []
    for offset in range(0, len(data), block_size):
        chunk = data[offset:offset + block_size]
        if len(chunk) < 64:
            continue
        ent = shannon_entropy(chunk)
        chi2 = chi_squared(chunk)
        cls = classify_region(ent, chi2, len(chunk))
        blocks.append({
            "offset": offset,
            "size": len(chunk),
            "entropy": ent,
            "chi2": round(chi2, 1),
            "class": cls,
        })
    return blocks

def merge_regions(blocks: list[dict]) -> list[dict]:
    """Merge contiguous blocks of the same class into regions."""
    if not blocks:
        return []
    regions = [dict(blocks[0])]
    for b in blocks[1:]:
        last = regions[-1]
        if b["class"] == last["class"]:
            last["size"] = (b["offset"] + b["size"]) - last["offset"]
            last["entropy"] = (last["entropy"] + b["entropy"]) / 2
        else:
            regions.append(dict(b))
    return regions

# ── Output ───────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Entropy analysis with region classification")
    parser.add_argument("file", help="Path to the sample binary")
    parser.add_argument("--block-size", type=int, default=1024, help="Sliding window block size (default: 1024)")
    parser.add_argument("--threshold", type=float, default=7.0, help="Entropy threshold for high-entropy alert (default: 7.0)")
    args = parser.parse_args()

    path = Path(args.file)
    if not path.is_file():
        print(f"[ERROR] File not found: {path}", file=sys.stderr)
        sys.exit(1)

    data = path.read_bytes()
    print("=" * 64)
    print(f"  Entropy Analysis — {path.name} ({len(data):,} bytes)")
    print("=" * 64)

    # Global entropy
    global_ent = shannon_entropy(data)
    global_chi2 = chi_squared(data)
    global_cls = classify_region(global_ent, global_chi2, len(data))
    print(f"\n  Overall entropy:  {global_ent} / 8.0  [{global_cls}]")
    print(f"  Chi-squared:      {global_chi2:.1f}")

    # Per-section analysis
    sections = parse_pe_sections(data) or parse_elf_sections(data)
    if sections:
        print(f"\n{'─' * 56}")
        print("  Per-Section Entropy")
        print(f"{'─' * 56}")
        print(f"  {'Section':<12s}  {'Offset':>10s}  {'Size':>10s}  {'Entropy':>7s}  {'Chi²':>10s}  Class")
        for sec in sections:
            chunk = data[sec["offset"]:sec["offset"] + sec["size"]]
            ent = shannon_entropy(chunk)
            chi2 = chi_squared(chunk)
            cls = classify_region(ent, chi2, sec["size"])
            flag = " <<<" if ent >= args.threshold else ""
            print(f"  {sec['name']:<12s}  {sec['offset']:>10,}  {sec['size']:>10,}  {ent:>7.4f}  {chi2:>10.1f}  {cls}{flag}")

    # Sliding window
    print(f"\n{'─' * 56}")
    print(f"  Sliding Window (block={args.block_size})")
    print(f"{'─' * 56}")
    blocks = sliding_window_entropy(data, args.block_size)
    regions = merge_regions(blocks)

    high_ent_total = sum(r["size"] for r in regions if r["class"] in ("ENCRYPTED", "COMPRESSED"))
    code_total = sum(r["size"] for r in regions if r["class"] == "CODE")
    ratio = high_ent_total / code_total if code_total > 0 else float("inf")

    print(f"\n  Regions: {len(regions)}")
    print(f"  High-entropy bytes: {high_ent_total:,} ({high_ent_total * 100 / len(data):.1f}%)")
    print(f"  Code bytes:         {code_total:,} ({code_total * 100 / len(data):.1f}%)")
    print(f"  Encrypted/Code:     {ratio:.2f}")

    # Show notable regions (>= threshold or large encrypted/compressed)
    print(f"\n  {'Offset':>10s}  {'Size':>10s}  {'Entropy':>7s}  Class")
    for r in regions:
        if r["entropy"] >= args.threshold or (r["class"] in ("ENCRYPTED", "COMPRESSED") and r["size"] >= 4096):
            print(f"  0x{r['offset']:08X}  {r['size']:>10,}  {r['entropy']:>7.4f}  {r['class']}")

    print(f"\n{'=' * 64}")

if __name__ == "__main__":
    main()
