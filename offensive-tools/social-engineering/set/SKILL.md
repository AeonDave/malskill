---
name: set
description: "Social-Engineer Toolkit (SET) for spear-phishing, credential harvesting, and payload delivery via social engineering vectors. Use when asked to create spear-phishing emails with payloads, clone websites for credential harvesting, generate social engineering pretexts, or automate phishing + exploit delivery."
license: Apache-2.0
compatibility: "Linux (Kali pre-installed). Install: git clone https://github.com/trustedsec/social-engineer-toolkit + pip install -r requirements.txt. Requires Python 3."
metadata:
  author: AeonDave
  version: "1.0"
---

# SET — Social-Engineer Toolkit

Comprehensive social engineering framework — spear-phishing, credential harvesting, and payload delivery.

## Quick Start

```bash
# Start interactive menu
sudo setoolkit

# Or launch specific attack from CLI
sudo python setoolkit
```

## Main Menu Structure

```
1) Social-Engineering Attacks
2) Penetration Testing (Fast-Track)
3) Third Party Modules
4) Update the Social-Engineer Toolkit
```

## Key Attack Vectors

### 1. Spear-Phishing Attack Vector
`1 > 1` — Send phishing emails with embedded payloads:
- File format exploits (PDF, Office macros)
- Custom payload attachments
- Mass email campaign

### 2. Website Attack Vector
`1 > 2` — Web-based attacks:

| Option | Description |
|--------|-------------|
| Java Applet | Signed Java applet dropping payload |
| Metasploit Browser | Browser exploit delivery |
| **Credential Harvester** | Clone site + capture creds |
| Tabnabbing | Replace inactive browser tab |
| Web Jacking | Redirect via iframe |
| Multi-Attack | Combine multiple web attacks |

### 3. Credential Harvester

```
1 > 2 > 3   # Credential Harvester Attack
> 2         # Site cloner
> Enter IP for POST back
> Enter URL to clone (e.g., https://mail.google.com)
```

SET clones the site and serves it locally. Credentials POSTed to the form are intercepted and logged.

### 4. Mass Mailer Attack
`1 > 5` — Send mass spear-phishing emails:
- Single targeted email
- Mass email from list
- Requires SMTP credentials

## Common Workflows

```bash
# Credential harvester with site clone
sudo setoolkit
# 1 > 2 > 3 > 2
# Enter attacker IP: 192.168.1.5
# URL to clone: https://outlook.office365.com

# Captured creds stored in: /var/www/ or SET reports dir
cat /root/.set/reports/2024*/

# Java-based payload delivery (legacy but useful for old JRE)
# 1 > 2 > 1

# Spear-phish with Office macro payload
# 1 > 1 > 1 (email to specific address)
```

## Logs & Reports

- Credentials: `/root/.set/reports/`
- Email logs: `/root/.set/`
- Config: `/etc/setoolkit/set.config`

## Resources

| File | When to load |
|------|--------------|
| `references/attack-vectors.md` | Full menu tree, payload options, SMTP configuration, evasion tips |
