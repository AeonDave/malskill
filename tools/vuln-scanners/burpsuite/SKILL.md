---
name: burpsuite
description: "Burp Suite: integrated web application security testing platform with proxy, scanner, intruder, and repeater. Use when testing web apps by intercepting/modifying HTTP traffic, fuzzing endpoints, exploiting SQLi/XSS/IDOR manually, or running automated active scans. Community free; Pro required for scanner."
license: Commercial (Pro) / Free (Community)
compatibility: "Windows / macOS / Linux. Java 11+. Download from portswigger.net/burp."
metadata:
  author: AeonDave
  version: "1.0"
---

# Burp Suite

Web application security testing platform.

## Quick Start

```bash
burpsuite
# Set browser proxy: 127.0.0.1:8080
# Install CA cert: browse to http://burp while proxied
```

## Core Tools

| Tool | Use |
|------|-----|
| **Proxy** | Intercept / modify HTTP/S traffic |
| **Repeater** | Replay and modify single requests |
| **Intruder** | Automated fuzzing / brute-force |
| **Scanner** | Active/passive vuln detection (Pro) |
| **Decoder** | Encode/decode URL, Base64, hex |
| **Comparer** | Diff two HTTP responses |
| **Extender** | Load BApp plugins |

## Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+R` | Send to Repeater |
| `Ctrl+I` | Send to Intruder |
| `Ctrl+F` | Forward intercepted request |
| `Ctrl+Z` | Drop request |

## Common Workflows

### SQLi manual detection
1. Capture request → Repeater (`Ctrl+R`)
2. Modify parameter value, observe response differences

### Intruder brute-force
1. Capture request → Intruder → mark positions with `§`
2. Load wordlist → Start Attack

## Resources

| File | When to load |
|------|--------------|
| `references/` | BApp recommendations, match-and-replace rules, scan config |
