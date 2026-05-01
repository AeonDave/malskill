#!/usr/bin/env python3
"""Lightweight forensic evidence triage helper.

Purpose:
- classify evidence path by type (disk image, ISO, memory dump, pcap)
- print objective-driven next actions and suggested tool-family skills
- produce deterministic, LLM-friendly output for incident handoff
"""

from __future__ import annotations

import argparse
from pathlib import Path

DISK_EXT = {".e01", ".dd", ".raw", ".img", ".vmdk", ".vhd", ".vhdx"}
PCAP_EXT = {".pcap", ".pcapng", ".cap"}
MEM_EXT = {".mem", ".dmp", ".vmem", ".raw"}
ISO_EXT = {".iso"}


def classify(path: Path) -> str:
    ext = path.suffix.lower()
    if ext in ISO_EXT:
        return "iso"
    if ext in DISK_EXT:
        # .raw can also be memory; use filename hints for ambiguity
        name = path.name.lower()
        if ext == ".raw" and any(k in name for k in ("mem", "ram", "dump")):
            return "memory"
        return "disk"
    if ext in PCAP_EXT:
        return "pcap"
    if ext in MEM_EXT:
        return "memory"
    return "unknown"


def guidance(kind: str) -> tuple[list[str], list[str]]:
    if kind == "disk":
        return (
            [
                "Validate evidence hash and preserve read-only workflow.",
                "Map partitions/filesystems and build early activity timeline.",
                "Prioritize user, execution, persistence, and log artifacts before deep carving.",
                "Corroborate key findings with a secondary source.",
            ],
            [
                "offensive-tools/forensic/sleuth-kit",
                "offensive-tools/forensic/autopsy",
                "offensive-tools/forensic/ftk-imager",
                "offensive-tools/forensic/yara",
            ],
        )

    if kind == "iso":
        return (
            [
                "Verify hash and mount ISO read-only.",
                "Inventory executable/script payloads and autorun/install metadata.",
                "Scan extracted artifacts and correlate with endpoint execution evidence.",
            ],
            [
                "offensive-tools/forensic/sleuth-kit",
                "offensive-tools/rev/binwalk",
                "offensive-tools/forensic/yara",
            ],
        )

    if kind == "pcap":
        return (
            [
                "Start with protocol and endpoint triage (top talkers, uncommon ports/protocols).",
                "Pivot through DNS/TLS/HTTP and reconstruct ordered session sequence.",
                "Map suspicious sessions to endpoint process/user context when possible.",
            ],
            [
                "offensive-tools/forensic/zeek",
                "offensive-tools/forensic/tcpdump",
                "offensive-tools/network/wireshark",
            ],
        )

    if kind == "memory":
        return (
            [
                "Enumerate process tree, command lines, sockets, and loaded modules.",
                "Hunt for injected/hidden regions and suspicious memory protections.",
                "Extract suspect process artifacts and correlate with disk/network evidence.",
            ],
            [
                "offensive-tools/forensic/volatility3",
                "offensive-tools/forensic/yara",
            ],
        )

    return (
        [
            "Type could not be auto-classified from extension.",
            "Run manual triage: hash, file metadata, and header signature checks.",
            "Assign one of disk/iso/pcap/memory workflows explicitly before deep analysis.",
        ],
        [
            "offensive-tools/forensic/sleuth-kit",
            "offensive-tools/network/wireshark",
            "offensive-tools/forensic/volatility3",
        ],
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Forensic evidence triage helper")
    parser.add_argument("evidence", help="Path to evidence file")
    args = parser.parse_args()

    p = Path(args.evidence)
    kind = classify(p)
    steps, tools = guidance(kind)

    print(f"EVIDENCE: {p}")
    print(f"TYPE: {kind}")
    print("NEXT_ACTIONS:")
    for i, step in enumerate(steps, start=1):
        print(f"  {i}. {step}")

    print("TOOL_SKILLS:")
    for t in tools:
        print(f"  - {t}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
