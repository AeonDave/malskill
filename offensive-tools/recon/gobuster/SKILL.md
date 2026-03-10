---
name: gobuster
description: "Directory, DNS subdomain, and vhost brute-forcer written in Go. Use when asked to enumerate web directories, find hidden paths, brute-force subdomains via DNS, or discover virtual hosts on a web server."
license: Apache-2.0
compatibility: "Linux, Windows, macOS. Install: go install github.com/OJ/gobuster/v3@latest or download binary from GitHub releases. Pre-installed on Kali."
metadata:
  author: AeonDave
  version: "1.0"
---

# Gobuster

Go-based brute-forcer for directories, DNS, and vhosts.

## Quick Start

```bash
# Directory brute-force
gobuster dir -u http://example.com -w /usr/share/wordlists/dirb/common.txt

# DNS subdomain enumeration
gobuster dns -d example.com -w /usr/share/wordlists/subdomains.txt

# Virtual host discovery
gobuster vhost -u http://example.com -w /usr/share/wordlists/subdomains.txt
```

## Modes

| Mode | Description |
|------|-------------|
| `dir` | Directory/file enumeration |
| `dns` | DNS subdomain brute-force |
| `vhost` | Virtual host discovery |
| `fuzz` | Generic fuzzing (URL path/param) |
| `s3` | Enumerate open S3 buckets |
| `gcs` | Google Cloud Storage buckets |

## Dir Mode Flags

| Flag | Description |
|------|-------------|
| `-u <url>` | Target URL |
| `-w <wordlist>` | Wordlist path |
| `-t <n>` | Threads (default 10) |
| `-x <ext>` | File extensions (e.g., `php,html,txt`) |
| `-s <codes>` | Allowed status codes (default `200,204,301,302,307,401,403`) |
| `-b <codes>` | Blacklist status codes |
| `-r` | Follow redirects |
| `-k` | Skip TLS verification |
| `-H <header>` | Custom header (e.g., `"Authorization: Bearer TOKEN"`) |
| `-c <cookie>` | Add cookie |
| `--timeout <duration>` | HTTP timeout (e.g., `10s`) |
| `-o <file>` | Output file |
| `-q` | Quiet (no banner) |
| `--no-error` | Suppress errors |

## DNS Mode Flags

| Flag | Description |
|------|-------------|
| `-d <domain>` | Target domain |
| `-w <wordlist>` | Wordlist |
| `-r <resolver>` | Custom DNS resolver |
| `--wildcard` | Force continue on wildcard DNS |

## Common Workflows

```bash
# Dir enum with extensions, output to file
gobuster dir -u https://target.com -w common.txt -x php,html,bak -o dirs.txt -q

# Dir enum behind auth
gobuster dir -u https://target.com -w common.txt -H "Authorization: Bearer <token>"

# Recursive-style: pipe back interesting dirs
gobuster dir -u https://target.com/api/ -w api-endpoints.txt -x json

# DNS with custom resolver
gobuster dns -d target.com -w subdomains-top1m.txt -r 8.8.8.8 -t 50

# Vhost discovery (append domain for non-matching)
gobuster vhost -u http://target.com -w subdomains.txt --append-domain
```

## Useful Wordlists

- `/usr/share/wordlists/dirb/common.txt` — general dirs
- `/usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt` — comprehensive
- `SecLists/Discovery/Web-Content/raft-medium-directories.txt` — raft lists
- `SecLists/Discovery/DNS/subdomains-top1million-5000.txt` — DNS

## Resources

| File | When to load |
|------|--------------|
| `references/wordlists.md` | Recommended wordlists per mode and target type |
