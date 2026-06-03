---
name: sstimap
description: "Auth/lab ref: actively maintained SSTI detection and exploitation tool with interactive and predetermined modes across Jinja2, Twig, Smarty, Freemarker, Velocity, ERB, Pug, Nunjucks, and more."
license: GPL-3.0
compatibility: "Linux / macOS / Windows; Python 3."
metadata:
  author: AeonDave
  version: "1.0"
---

# SSTImap

Modern SSTI detection and exploitation — maintained successor to tplmap.

## Quick Start

```bash
git clone https://github.com/vladko312/SSTImap
cd SSTImap && pip3 install -r requirements.txt

# Basic detection
python3 sstimap.py -u "http://target.com/render?name=*"

# POST injection point
python3 sstimap.py -u "http://target.com/render" -d "name=*"

# Interactive exploitation
python3 sstimap.py -u "http://target.com/render?name=*" --interactive
```

Use `*` to mark the injection point in URL params, POST body, or headers.

## Core Flags

| Flag | Purpose |
|------|---------|
| `-u <url>` | Target URL with `*` marker |
| `-d <data>` | POST body with `*` marker |
| `-H "K: V"` | Custom header |
| `--cookie <str>` | Cookie string |
| `--os-shell` | Try interactive OS shell |
| `--os-cmd <cmd>` | Execute one OS command |
| `--interactive` | Interactive exploitation mode |
| `--engine <name>` | Force engine if known |
| `--proxy <url>` | Route through Burp/ZAP |
| `--extra <dir>` | Load extra plugins |

## Supported Engines

Common engines covered:
- Jinja2 / Python eval
- Twig / Smarty
- Freemarker / Velocity
- ERB / Slim / Ruby eval
- Pug / Nunjucks / doT / Dust / EJS
- Tornado / Mako / Marko

## Detection Workflow

```bash
# 1. Confirm reflection manually
name={{7*7}}
name=${7*7}
name=<%= 7*7 %>
name=#{7*7}

# 2. Hand off to SSTImap
python3 sstimap.py -u "http://target.com/?name=*"

# 3. If engine known, force it for cleaner exploitation
python3 sstimap.py -u "http://target.com/?name=*" --engine jinja2 --interactive
```

## Typical Escalation Path

| Stage | Objective |
|-------|-----------|
| Expression eval | `{{7*7}}` / `${7*7}` returns `49` |
| Object traversal | reach builtins / classes / globals |
| File read | load templates, config, env |
| Command exec | `os.popen`, `subprocess`, engine-native gadget |
| Shell | reverse shell or interactive command loop |

## Why Prefer SSTImap over tplmap

- Actively maintained with releases in 2025
- Native Python 3 workflow
- Interactive mode is cleaner for real exploitation
- Extra plugins support newer engines and CVE-specific chains

## References

- SSTI payloads: `references/ssti-payloads.md`
- [SSTImap repository](https://github.com/vladko312/SSTImap)
