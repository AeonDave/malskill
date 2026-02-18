---
name: eyewitness
description: "Web screenshotting and reporting tool that captures screenshots of web services and generates an HTML report. Use when asked to visually enumerate web services, screenshot a list of URLs/hosts, generate visual web inventory, or create a report of discovered web interfaces."
license: Apache-2.0
compatibility: "Linux, macOS (limited). Install: git clone + pip install -r requirements.txt. Docker image available. Pre-installed on Kali."
metadata:
  author: AeonDave
  version: "1.0"
---

# EyeWitness

Screenshots web services and produces an HTML report with categorized results.

## Quick Start

```bash
# Screenshot from URL list
eyewitness -f urls.txt --web

# Screenshot from nmap XML
eyewitness -x nmap_scan.xml --web

# Specify output directory
eyewitness -f urls.txt --web -d output/eyewitness
```

## Core Flags

| Flag | Description |
|------|-------------|
| `-f <file>` | Input file with URLs/hosts |
| `-x <xml>` | Nmap XML output file |
| `--web` | HTTP screenshotting (default) |
| `--rdp` | RDP screenshots |
| `--vnc` | VNC screenshots |
| `-d <dir>` | Output directory |
| `--no-prompt` | Skip interactive prompts |
| `--timeout <n>` | Per-target timeout (default 7s) |
| `--threads <n>` | Threads (default 10) |
| `--delay <n>` | Delay between requests |
| `--proxy-ip <ip>` | Proxy IP |
| `--proxy-port <port>` | Proxy port |
| `--resolve` | Resolve IP addresses |
| `--add-http-headers <h>` | Add custom headers |
| `--user-agent <ua>` | Custom user agent |
| `--prepend-https` | Prepend https:// to input |
| `--prepend-http` | Prepend http:// to input |
| `--active-scan` | Active fingerprinting |
| `--jitter <n>` | Jitter between screenshots |

## Common Workflows

```bash
# Screenshot a subdomain list
cat subs.txt | sed 's/^/http:\/\//' > urls.txt
eyewitness -f urls.txt --web -d report/ --no-prompt

# From nmap scan + report
nmap -sV -p 80,443,8080,8443 -oX scan.xml 192.168.1.0/24
eyewitness -x scan.xml --web -d web_report/ --no-prompt

# With both HTTP and HTTPS
eyewitness -f hosts.txt --prepend-http --prepend-https --web -d out/

# RDP screenshot of internal network
eyewitness -f hosts.txt --rdp -d rdp_report/
```

## Output

EyeWitness produces:
- `report.html` — categorized screenshots with HTTP headers
- `Matches/` — interesting categories (login pages, Cisco, Citrix, etc.)
- `Screenshots/` — raw screenshot images

## Resources

| File | When to load |
|------|--------------|
| `references/report-structure.md` | HTML report layout, category descriptions, integration with other tools |
