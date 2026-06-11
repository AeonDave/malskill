# YARA Rule Templates

Generic YARA rule templates for common malware patterns. Use as starting points for case-specific rules.

## Rule writing guidelines

- Keep conditions specific enough to avoid false positives
- Use `meta:` for description, author, severity, date
- Prefer byte patterns over string-only rules for reliability
- Use `filesize` constraints to limit scope
- Test rules against known-good files before deploying

## PE structure rules

```yara
rule suspicious_section_entropy {
    meta:
        description = "PE with high-entropy executable section (likely packed)"
        severity = "medium"
    condition:
        uint16(0) == 0x5A4D and
        for any i in (0..pe.number_of_sections - 1):
            (pe.sections[i].characteristics & 0x20000000 != 0 and  // IMAGE_SCN_MEM_EXECUTE
             math.entropy(pe.sections[i].raw_data_offset, pe.sections[i].raw_data_size) > 7.2)
}

rule tiny_import_table {
    meta:
        description = "PE with very few imports (likely packed or manually resolves)"
        severity = "low"
    condition:
        uint16(0) == 0x5A4D and
        pe.number_of_imports < 5 and
        filesize > 50KB
}
```

## Injection patterns

```yara
rule process_injection_apis {
    meta:
        description = "Imports consistent with process injection"
        severity = "high"
    strings:
        $alloc = "VirtualAllocEx" ascii
        $write = "WriteProcessMemory" ascii
        $thread1 = "CreateRemoteThread" ascii
        $thread2 = "NtCreateThreadEx" ascii
        $thread3 = "RtlCreateUserThread" ascii
    condition:
        uint16(0) == 0x5A4D and $alloc and $write and 1 of ($thread*)
}

rule process_hollowing {
    meta:
        description = "APIs consistent with process hollowing"
        severity = "high"
    strings:
        $create = "CreateProcessA" ascii
        $create_w = "CreateProcessW" ascii
        $unmap = "NtUnmapViewOfSection" ascii
        $write = "WriteProcessMemory" ascii
        $resume = "ResumeThread" ascii
    condition:
        uint16(0) == 0x5A4D and (1 of ($create*)) and $unmap and $write and $resume
}
```

## Network indicators

```yara
rule embedded_url_patterns {
    meta:
        description = "Contains URL patterns suggesting network activity"
        severity = "low"
    strings:
        $http = /https?:\/\/[\w.-]+\.[\w]{2,6}/ ascii
        $ua = "Mozilla/5.0" ascii
        $tg = "api.telegram.org" ascii
        $discord = "discord.com/api/webhooks" ascii
    condition:
        2 of them
}
```

## Persistence mechanisms

```yara
rule windows_persistence {
    meta:
        description = "Strings suggesting Windows persistence mechanism"
        severity = "medium"
    strings:
        $run1 = "CurrentVersion\\Run" ascii nocase
        $run2 = "CurrentVersion\\RunOnce" ascii nocase
        $schtask = "schtasks" ascii nocase
        $service = "CreateServiceA" ascii
        $service_w = "CreateServiceW" ascii
        $startup = "\\Startup\\" ascii nocase
        $wmi = "Win32_Process" ascii
    condition:
        2 of them
}

rule linux_persistence {
    meta:
        description = "Strings suggesting Linux persistence mechanism"
        severity = "medium"
    strings:
        $cron = "/etc/cron" ascii
        $bashrc = ".bashrc" ascii
        $profile = ".profile" ascii
        $systemd = "/etc/systemd" ascii
        $initd = "/etc/init.d" ascii
        $rclocal = "/etc/rc.local" ascii
    condition:
        2 of them
}
```

## Obfuscation and evasion

```yara
rule anti_debug_strings {
    meta:
        description = "Contains anti-debugging API references"
        severity = "low"
    strings:
        $ad1 = "IsDebuggerPresent" ascii
        $ad2 = "CheckRemoteDebuggerPresent" ascii
        $ad3 = "NtQueryInformationProcess" ascii
        $ad4 = "OutputDebugString" ascii
        $vm1 = "VMwareVMware" ascii
        $vm2 = "VBoxVBoxVBox" ascii
        $vm3 = "QEMU" ascii
        $sb1 = "SbieDll" ascii
        $sb2 = "dbghelp" ascii
    condition:
        3 of them
}

rule amsi_bypass {
    meta:
        description = "Strings suggesting AMSI bypass attempt"
        severity = "high"
    strings:
        $a1 = "AmsiScanBuffer" ascii
        $a2 = "amsiInitFailed" ascii
        $a3 = "AmsiUtils" ascii
        $a4 = "amsi.dll" ascii nocase
    condition:
        2 of them
}
```

## Crypto indicators

```yara
rule crypto_constants {
    meta:
        description = "Contains well-known cryptographic constants"
        severity = "low"
    strings:
        // AES S-box first bytes
        $aes = { 63 7C 77 7B F2 6B 6F C5 30 01 67 2B FE D7 AB 76 }
        // SHA-256 initial hash values
        $sha256 = { 6A 09 E6 67 BB 67 AE 85 3C 6E F3 72 A5 4F F5 3A }
        // RC4 key scheduling pattern (256 consecutive bytes)
        $rc4_init = { 00 01 02 03 04 05 06 07 08 09 0A 0B 0C 0D 0E 0F }
    condition:
        any of them
}
```

## Script/document rules

```yara
rule malicious_macro_indicators {
    meta:
        description = "Office document with suspicious macro indicators"
        severity = "medium"
    strings:
        $ole = { D0 CF 11 E0 A1 B1 1A E1 }
        $auto1 = "AutoOpen" ascii nocase
        $auto2 = "Document_Open" ascii nocase
        $auto3 = "Workbook_Open" ascii nocase
        $susp1 = "Shell" ascii
        $susp2 = "CreateObject" ascii
        $susp3 = "PowerShell" ascii nocase
        $susp4 = "WScript" ascii
    condition:
        $ole at 0 and 1 of ($auto*) and 2 of ($susp*)
}

rule html_smuggling {
    meta:
        description = "HTML file with smuggling indicators"
        severity = "high"
    strings:
        $blob = "new Blob" ascii
        $create_url = "createObjectURL" ascii
        $download = ".download" ascii
        $atob = "atob(" ascii
        $uint8 = "Uint8Array" ascii
        $from_char = "fromCharCode" ascii
    condition:
        3 of them
}
```

## Usage

```bash
# Scan a single file
yara rules.yar sample.bin

# Scan recursively with all .yar files in a directory
yara -r rules/ sample.bin

# Scan with tags
yara -t injection rules.yar sample.bin

# Output with matched strings
yara -s rules.yar sample.bin
```
