#!/usr/bin/env python3
"""YARA scanner with built-in generic malware detection rules.
Requires: yara-python (pip install yara-python)

Usage:
    python yara_scanner.py sample.bin [--rules-dir /path/to/rules] [--built-in-only]
"""

import argparse
import sys
import tempfile
from pathlib import Path

BUILTIN_RULES = r"""
rule suspicious_pe_imports {
    meta:
        description = "PE with suspicious injection/evasion API imports"
        severity = "medium"
    strings:
        $inj1 = "VirtualAllocEx" ascii
        $inj2 = "WriteProcessMemory" ascii
        $inj3 = "CreateRemoteThread" ascii
        $inj4 = "NtCreateThreadEx" ascii
        $inj5 = "QueueUserAPC" ascii
        $eva1 = "IsDebuggerPresent" ascii
        $eva2 = "NtQueryInformationProcess" ascii
        $eva3 = "CheckRemoteDebuggerPresent" ascii
    condition:
        uint16(0) == 0x5A4D and (2 of ($inj*) or 2 of ($eva*))
}

rule shellcode_patterns {
    meta:
        description = "Common shellcode byte sequences"
        severity = "high"
    strings:
        $sc1 = { FC 48 83 E4 F0 }        // x64 cld; and rsp, -0x10
        $sc2 = { 64 A1 30 00 00 00 }      // x86 PEB access via fs:[0x30]
        $sc3 = { 65 48 8B 04 25 60 00 }   // x64 PEB access via gs:[0x60]
        $sc4 = { E8 00 00 00 00 }         // call $+5 (PIC getpc)
    condition:
        any of them
}

rule base64_encoded_pe {
    meta:
        description = "Base64-encoded PE header"
        severity = "high"
    strings:
        $b64_mz1 = "TVqQAAMAA" ascii  // MZ header base64
        $b64_mz2 = "TVpQAAIAAA" ascii
        $b64_mz3 = "TVoAAAAAAAA" ascii
    condition:
        any of them
}

rule xor_encoded_pe {
    meta:
        description = "XOR-encoded MZ header (common single-byte keys)"
        severity = "high"
    strings:
        // MZ XORed with common keys
        $xor_41 = { 0C 1B }  // MZ ^ 0x41
        $xor_55 = { 18 2F }  // MZ ^ 0x55
        $xor_AA = { E7 D0 }  // MZ ^ 0xAA
        $xor_FF = { B5 A5 }  // MZ ^ 0xFF
    condition:
        any of them at 0
}

rule suspicious_powershell {
    meta:
        description = "Suspicious PowerShell strings"
        severity = "medium"
    strings:
        $ps1 = "-enc " ascii nocase
        $ps2 = "-encodedcommand" ascii nocase
        $ps3 = "FromBase64String" ascii nocase
        $ps4 = "Invoke-Expression" ascii nocase
        $ps5 = "IEX(" ascii nocase
        $ps6 = "DownloadString" ascii nocase
        $ps7 = "WebClient" ascii nocase
        $ps8 = "-nop " ascii nocase
        $ps9 = "bypass" ascii nocase
    condition:
        3 of them
}

rule c2_indicators {
    meta:
        description = "Potential C2 communication indicators"
        severity = "medium"
    strings:
        $ua1 = "Mozilla/5.0" ascii
        $ua2 = "User-Agent:" ascii
        $http1 = "POST /" ascii
        $http2 = "GET /" ascii
        $beacon = /sleep\s*\(\s*\d{3,}/ ascii nocase
        $tg1 = "api.telegram.org" ascii
        $tg2 = "chat_id=" ascii
        $discord = "discord.com/api/webhooks" ascii
    condition:
        3 of them
}

rule packed_or_encrypted {
    meta:
        description = "Binary is likely packed or encrypted (high entropy section)"
        severity = "low"
    strings:
        $upx0 = "UPX0" ascii
        $upx1 = "UPX1" ascii
        $aspack = ".aspack" ascii
        $themida = ".themida" ascii
        $vmp = ".vmp" ascii
        $mpress = ".MPRESS" ascii
    condition:
        uint16(0) == 0x5A4D and any of them
}

rule embedded_archive {
    meta:
        description = "PE with embedded archive (overlay or resource)"
        severity = "low"
    strings:
        $zip = { 50 4B 03 04 }
        $rar = "Rar!" ascii
        $7z = { 37 7A BC AF 27 1C }
        $cab = "MSCF" ascii
    condition:
        uint16(0) == 0x5A4D and any of them
}
"""


def main():
    parser = argparse.ArgumentParser(description="YARA scanner with built-in malware rules")
    parser.add_argument("file", help="Path to sample")
    parser.add_argument("--rules-dir", help="Additional YARA rules directory")
    parser.add_argument("--built-in-only", action="store_true", help="Only use built-in rules")
    args = parser.parse_args()

    try:
        import yara
    except ImportError:
        print("[ERROR] yara-python is required: pip install yara-python", file=sys.stderr)
        sys.exit(1)

    path = Path(args.file)
    if not path.is_file():
        print(f"[ERROR] File not found: {path}", file=sys.stderr)
        sys.exit(1)

    rules_list = {}

    # Compile built-in rules
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yar", delete=False) as f:
        f.write(BUILTIN_RULES)
        f.flush()
        rules_list["builtin"] = f.name

    # Add external rules
    if args.rules_dir and not args.built_in_only:
        rules_dir = Path(args.rules_dir)
        if rules_dir.is_dir():
            for yar_file in sorted(rules_dir.glob("**/*.yar")) + sorted(rules_dir.glob("**/*.yara")):
                rules_list[yar_file.stem] = str(yar_file)

    print("=" * 64)
    print(f"  YARA Scanner — {path.name}")
    print(f"  Rule sources: {len(rules_list)}")
    print("=" * 64)

    total_matches = 0
    for source_name, rule_path in rules_list.items():
        try:
            rules = yara.compile(filepath=rule_path)
            matches = rules.match(str(path))
            if matches:
                for m in matches:
                    total_matches += 1
                    severity = m.meta.get("severity", "unknown")
                    desc = m.meta.get("description", "")
                    print(f"\n  [MATCH] {m.rule}")
                    print(f"    Source:   {source_name}")
                    print(f"    Severity: {severity}")
                    print(f"    Desc:     {desc}")
                    if m.strings:
                        print(f"    Hits:     {len(m.strings)}")
                        for s in m.strings[:5]:
                            offset, identifier, matched_data = s[0], s[1], s[2]
                            preview = matched_data[:32]
                            print(f"      0x{offset:08X}  {identifier}  {preview}")
        except yara.Error as e:
            print(f"  [WARN] Failed to compile {source_name}: {e}")

    print(f"\n{'─' * 56}")
    if total_matches == 0:
        print("  No YARA rule matches.")
    else:
        print(f"  Total matches: {total_matches}")
    print(f"{'=' * 64}")

    # Clean up temp file
    try:
        Path(rules_list["builtin"]).unlink()
    except OSError:
        pass

    sys.exit(1 if total_matches > 0 else 0)


if __name__ == "__main__":
    main()
