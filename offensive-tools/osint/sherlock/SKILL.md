---
name: sherlock
description: "Hunt username presence across 400+ social networks. Use when pivoting on a discovered username during OSINT to map a target's digital footprint across platforms."
license: MIT
compatibility: "Python 3; pip install sherlock-project; Linux/macOS/Windows; github.com/sherlock-project/sherlock"
metadata:
  author: AeonDave
  version: "1.0"
---

# Sherlock

Username hunter across 400+ social platforms.

## Quick Start

```bash
pip install sherlock-project

# Search single username
sherlock username

# Search multiple usernames
sherlock user1 user2 user3

# Output to file
sherlock username --output results.txt

# JSON output
sherlock username --json
```

## Core Flags

| Flag | Purpose |
|------|---------|
| `--timeout N` | Per-site timeout (default: 60s) |
| `--print-found` | Only show found accounts |
| `--print-all` | Show all (including not found) |
| `--output FILE` | Save results |
| `--json` | JSON format |
| `--site NAME` | Search specific site only |
| `--csv` | CSV output |
| `-x XLSX` | Excel output |

## Common Workflows

**Hunt username from breach data:**
```bash
sherlock johndoe_83 --print-found --output johndoe_found.txt
```

**Multiple username variants:**
```bash
sherlock "john.doe" johndoe john_doe jdoe --print-found
```

**Targeted site lookup:**
```bash
sherlock johndoe --site twitter --site github --site linkedin
```

## Resources

| File | When to load |
|------|--------------|
| `references/` | Username variation techniques |
