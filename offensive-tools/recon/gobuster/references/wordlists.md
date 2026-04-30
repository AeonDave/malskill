# Gobuster — Wordlists, Modes & Strategy

## Wordlists by Use Case

### Directory / File Enumeration

| Wordlist | Size | Notes |
|----------|------|-------|
| `dirb/common.txt` | 4k | Quick, low noise |
| `dirbuster/directory-list-2.3-small.txt` | 87k | Small comprehensive |
| `dirbuster/directory-list-2.3-medium.txt` | 220k | Standard choice |
| `dirbuster/directory-list-lowercase-2.3-medium.txt` | 207k | Lowercase only (Linux servers) |
| `SecLists/Discovery/Web-Content/raft-small-directories.txt` | 17k | Curated, low noise |
| `SecLists/Discovery/Web-Content/raft-medium-directories.txt` | 30k | Best balance |
| `SecLists/Discovery/Web-Content/raft-large-directories.txt` | 62k | Thorough |
| `SecLists/Discovery/Web-Content/raft-large-files.txt` | 37k | Files only |
| `SecLists/Discovery/Web-Content/big.txt` | 20k | General |
| `SecLists/Discovery/Web-Content/common.txt` | 4k | General |

### File Extensions by Target Type

| Target | Extensions |
|--------|-----------|
| PHP app | `php,php7,php5,phtml,inc,php.bak` |
| ASP.NET | `asp,aspx,ashx,asmx,svc,config` |
| Java | `jsp,jsf,do,action,jspx` |
| Ruby | `rb,erb` |
| Config/backup | `bak,old,orig,tmp,conf,cfg,log,ini,env` |
| Generic | `html,htm,js,json,txt,xml,yaml,yml` |

```bash
# Combined extension sweep
gobuster dir -u https://target.com -w raft-medium.txt \
  -x php,bak,conf,txt,html -t 50 -q
```

### DNS Subdomains

| Wordlist | Size | Notes |
|----------|------|-------|
| `SecLists/Discovery/DNS/subdomains-top1million-5000.txt` | 5k | Quick |
| `SecLists/Discovery/DNS/subdomains-top1million-20000.txt` | 20k | Standard |
| `SecLists/Discovery/DNS/subdomains-top1million-110000.txt` | 110k | Deep |
| `SecLists/Discovery/DNS/bitquark-subdomains-top100000.txt` | 100k | Alt source |
| `SecLists/Discovery/DNS/n0kovo_subdomains.txt` | 3M | Comprehensive |

### API Endpoints

| Wordlist | Notes |
|----------|-------|
| `SecLists/Discovery/Web-Content/api/api-endpoints.txt` | REST API paths |
| `SecLists/Discovery/Web-Content/api/objects.txt` | API objects/resources |
| `SecLists/Discovery/Web-Content/api/actions.txt` | API actions |
| `SecLists/Discovery/Web-Content/api/api_seen_in_wild.txt` | Real-world API paths |

## Mode Strategy Guide

### dir — Directory/File Brute-Force

```bash
# Step 1: Quick scan (fast signal)
gobuster dir -u https://target.com \
  -w /usr/share/seclists/Discovery/Web-Content/raft-small-directories.txt \
  -t 50 -q

# Step 2: Extensions pass (find backup/config files)
gobuster dir -u https://target.com \
  -w /usr/share/seclists/Discovery/Web-Content/raft-medium-directories.txt \
  -x php,bak,conf,txt -t 50 --exclude-length 0

# Step 3: Deep dive on interesting paths
gobuster dir -u https://target.com/admin/ \
  -w /usr/share/seclists/Discovery/Web-Content/raft-large-files.txt \
  -x php,html -t 30
```

### dns — Subdomain Brute-Force

```bash
# Standard
gobuster dns -d target.com \
  -w /usr/share/seclists/Discovery/DNS/subdomains-top1million-5000.txt \
  -r 8.8.8.8 -t 50 --show-ips

# Show CNAMEs (useful for takeover detection)
gobuster dns -d target.com \
  -w /usr/share/seclists/Discovery/DNS/subdomains-top1million-20000.txt \
  --show-cname --show-ips
```

### vhost — Virtual Host Discovery

```bash
# Find vhosts: important to filter default response size
# Step 1: Get default response size
curl -s -o /dev/null -w "%{size_download}" http://target.com/

# Step 2: Exclude that size
gobuster vhost -u http://target.com \
  -w /usr/share/seclists/Discovery/DNS/subdomains-top1million-5000.txt \
  --append-domain --exclude-length <DEFAULT_SIZE>
```

### s3 — Bucket Enumeration

```bash
gobuster s3 -w /usr/share/seclists/Discovery/DNS/subdomains-top1million-5000.txt
# Try company name variations:
# targetcorp, target-corp, target-backup, target-dev, target-staging
```

## Performance Tuning

| Scenario | Threads | Rate limit | Notes |
|----------|---------|------------|-------|
| Fast internal | 100 | none | LAN, no WAF |
| Standard external | 50 | none | Default |
| Rate-limited target | 10-20 | `--delay 100ms` | Avoid 429 |
| CDN/WAF | 5-10 | `--delay 500ms` | Stealth |

## Output Parsing

```bash
# Parse found paths from output file
grep "Status: 200" gobuster_output.txt | awk '{print $1}'

# Quiet + extended mode (print full URLs, useful for piping)
gobuster dir -u https://target.com -w common.txt -q -e 2>/dev/null | \
  grep "(Status: 200)" | awk '{print $1}'

# Feed found dirs back into gobuster
gobuster dir -u https://target.com -w common.txt -q 2>/dev/null | \
  grep "Status: 301" | awk '{print $1}' | \
  while read path; do
    gobuster dir -u "https://target.com$path" -w common.txt -q -t 30
  done
```
