# Feroxbuster — Filters, Config & Advanced Patterns

## Filter / Match Reference

### Status Codes

```bash
# Include only these (default: 200,204,301,302,307,308,401,403,405)
feroxbuster -u https://target.com -w wordlist.txt -s 200,301

# Exclude these
feroxbuster -u https://target.com -w wordlist.txt -C 404,302,301
```

### Response Size

```bash
# Filter exact size (hide identical "not found" pages)
feroxbuster -u https://target.com -w wordlist.txt -S 1234

# Multiple sizes
feroxbuster -u https://target.com -w wordlist.txt -S 1234,5678
```

### Word Count

```bash
# Filter pages with exactly 42 words
feroxbuster -u https://target.com -w wordlist.txt -W 42
```

### Line Count

```bash
# Filter pages with exactly 10 lines
feroxbuster -u https://target.com -w wordlist.txt -L 10
```

### Regex Filter

```bash
# Filter responses matching regex
feroxbuster -u https://target.com -w wordlist.txt --filter-regex "Not Found|Error 404"

# Match only responses with regex
feroxbuster -u https://target.com -w wordlist.txt --include-status 200 \
  --filter-regex "admin|login|dashboard"
```

## Noise Reduction Workflow

```bash
# Step 1: probe with tiny wordlist to identify noise pattern
feroxbuster -u https://target.com \
  -w /usr/share/seclists/Discovery/Web-Content/raft-small-directories.txt \
  --no-recursion -t 20

# Step 2: note the false positive response size, e.g., all 404s = 1543 bytes

# Step 3: re-run filtering that size
feroxbuster -u https://target.com \
  -w /usr/share/seclists/Discovery/Web-Content/raft-medium-directories.txt \
  -S 1543 -C 404
```

## Recursion Control

```bash
# Default: recursive, depth 4
feroxbuster -u https://target.com -w wordlist.txt

# Disable recursion (flat scan only)
feroxbuster -u https://target.com -w wordlist.txt --no-recursion

# Limit depth
feroxbuster -u https://target.com -w wordlist.txt -d 2

# Limit concurrent scans during recursion
feroxbuster -u https://target.com -w wordlist.txt --scan-limit 4
```

## Collection Mode

```bash
# Collect words from responses + expand wordlist dynamically
feroxbuster -u https://target.com -w common.txt --collect-words

# Collect extensions seen in responses
feroxbuster -u https://target.com -w common.txt --collect-extensions

# Collect backup file variants of found files
feroxbuster -u https://target.com -w common.txt --collect-backups
# Appends: .bak, .old, .orig, .bkp, .copy, ~

# Full collect mode (all three)
feroxbuster -u https://target.com -w common.txt \
  --collect-words --collect-extensions --collect-backups
```

## Link Extraction (Spider Mode)

```bash
# Extract links from found HTML pages and add to scan queue
feroxbuster -u https://target.com -w wordlist.txt --extract-links

# Combined: brute + spider
feroxbuster -u https://target.com \
  -w /usr/share/seclists/Discovery/Web-Content/raft-medium-directories.txt \
  --extract-links --collect-words -t 40
```

## State Save / Resume

```bash
# Scan auto-saves state to ferox-<target>-state.json

# Resume interrupted scan
feroxbuster --resume-from ferox-https_target_com-state.json

# Manually save on exit (Ctrl+C → prompted to save)
# Press 's' to stop a URL mid-scan
```

## Configuration File

```toml
# ~/.config/feroxbuster/ferox-config.toml

wordlist = "/usr/share/seclists/Discovery/Web-Content/raft-medium-directories.txt"
threads = 50
depth = 3
timeout = 10
status_codes = [200, 204, 301, 302, 307, 308, 401, 403]
filter_status = [404]
filter_size = []
extensions = ["php", "html", "txt", "bak"]
auto_tune = true
collect_words = true
collect_extensions = true
extract_links = true
quiet = false
json = false
user_agent = "feroxbuster/2.x"
```

## Multi-Target Scanning

```bash
# Scan all live hosts from httpx output
cat live_hosts.txt | feroxbuster --stdin \
  -w /usr/share/seclists/Discovery/Web-Content/raft-small-directories.txt \
  --no-recursion -t 20 --scan-limit 5
```

## Output Parsing

```bash
# JSON output
feroxbuster -u https://target.com -w wordlist.txt --json -o results.json

# Parse JSON
cat results.json | jq -r 'select(.status==200) | "\(.status) \(.content_length) \(.url)"'

# Extract just found URLs
cat results.json | jq -r 'select(.status==200) | .url'

# Text output grep
feroxbuster -u https://target.com -w wordlist.txt -q | \
  grep "200" | awk '{print $NF}'
```

## Comparison: feroxbuster vs ffuf vs gobuster

| Feature | feroxbuster | ffuf | gobuster |
|---------|------------|------|----------|
| Recursion | Native, auto | Manual (`-recursion`) | No |
| Link extraction | Yes | No | No |
| Word collection | Yes | No | No |
| Multi-FUZZ | No | Yes | No |
| DNS/vhost mode | No | Yes | Yes |
| State resume | Yes | No | No |
| Config file | Yes | Yes (`.ffufrc`) | No |
| Speed | Fast (Rust) | Fast (Go) | Fast (Go) |

**Use feroxbuster** when: recursive web scan, unknown depth, need spider + brute combo
**Use ffuf** when: parameter fuzzing, multi-position fuzzing, custom POST/header fuzzing
**Use gobuster** when: DNS subdomain, vhost discovery, S3 bucket enumeration
