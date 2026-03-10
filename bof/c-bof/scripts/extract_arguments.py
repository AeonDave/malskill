#!/usr/bin/env python3
"""
extract_arguments.py — Parse and pretty-print arguments from a BOF binary pack.

Usage:
    python3 extract_arguments.py <packet.bin>

The Cobalt Strike BOF argument packer uses a simple TLV-like format.
This script decodes it for debugging purposes.
"""

from __future__ import annotations

import struct
import sys
from pathlib import Path


def parse_bof_packet(data: bytes) -> list[tuple[str, object]]:
    """Parse a packed BOF argument buffer into (type, value) tuples."""
    offset = 0
    args: list[tuple[str, object]] = []

    while offset < len(data):
        if offset + 4 > len(data):
            break

        # Read the 4-byte type/length prefix
        length = struct.unpack_from("<I", data, offset)[0]
        offset += 4

        if length == 0:
            # int (4 bytes, little-endian)
            if offset + 4 > len(data):
                break
            val = struct.unpack_from("<i", data, offset)[0]
            args.append(("int", val))
            offset += 4

        elif length == 1:
            # short (2 bytes, little-endian)
            if offset + 2 > len(data):
                break
            val = struct.unpack_from("<H", data, offset)[0]
            args.append(("short", val))
            offset += 2

        else:
            # binary/string blob of `length` bytes
            if offset + length > len(data):
                break
            raw = data[offset : offset + length]
            try:
                text = raw.rstrip(b"\x00").decode("utf-8")
                args.append(("string", text))
            except UnicodeDecodeError:
                args.append(("binary", raw.hex()))
            offset += length

    return args


def main() -> None:
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <packet.bin>", file=sys.stderr)
        sys.exit(1)

    path = Path(sys.argv[1])
    if not path.is_file():
        print(f"[!] File not found: {path}", file=sys.stderr)
        sys.exit(1)

    data = path.read_bytes()
    print(f"[*] Parsing {len(data)} bytes from {path}\n")

    for i, (typ, val) in enumerate(parse_bof_packet(data)):
        print(f"  [{i}] {typ:>6s} : {val}")


if __name__ == "__main__":
    main()
