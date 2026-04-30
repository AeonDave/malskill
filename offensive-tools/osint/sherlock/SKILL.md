---
name: sherlock
description: "Hunt username presence across 400+ social networks and output found profile URLs. Use when pivoting on a discovered username during OSINT to map a target's digital footprint, build a list of active platforms, and feed results into further profiling. Complement with maigret for dossier building."
license: MIT
compatibility: "Python 3; pip install sherlock-project; Linux/macOS/Windows; github.com/sherlock-project/sherlock"
metadata:
  author: AeonDave
  version: "1.1"
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

**From breach data — test common variations at once:**
```bash
sherlock john.doe johndoe john_doe j.doe jdoe83 --print-found --timeout 10
```

## Username Variation Strategy

Given a real name "John Doe" or email `johndoe83@gmail.com`:

```
johndoe, john.doe, john_doe, jdoe, j.doe, johndoe83, jdoe83
firstname+lastname, firstnamelastname, last.first
Add: year of birth, numbers 1/2/_, common suffixes (_real, _official)
```

## vs maigret

| | sherlock | maigret |
|--|---------|---------|
| Sites | ~400 | 2800+ |
| Output | URL list | Full dossier (scraped data) |
| Speed | Fast | Slower |
| Best for | Quick platform sweep | Deep profile building |

Use sherlock for fast sweep, maigret for deep investigation.

## Resources

| File | When to load |
|------|--------------|
| `references/username-techniques.md` | Username generation, variation tools, pivot strategies, platform-specific tips |
