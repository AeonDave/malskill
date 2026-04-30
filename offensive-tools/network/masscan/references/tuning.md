# Masscan — Tuning & Config Reference

## Full Config File Options

```ini
# masscan.conf — all options in INI format
rate = 50000
ports = 0-65535
output-format = json          # json | grepable | xml | list | binary
output-filename = results.json
excludefile = /etc/masscan/exclude.conf
adapter = eth0                # source interface
adapter-ip = 192.168.1.100    # source IP
router-mac = 11:22:33:44:55:66  # gateway MAC (if autodetect fails)
banners = true
no-capture = false
wait = 10                     # seconds to wait after scan completes
randomize-hosts = true
```

```bash
masscan 10.0.0.0/16 -c masscan.conf
```

## Output Formats

| Format | Flag | Best for |
|--------|------|----------|
| List | `--output-format list` | Quick review |
| Grepable | `-oG file` | Grep/awk pipelines |
| XML | `-oX file` | Parsing, Metasploit import |
| JSON | `-oJ file` | Scripting, jq queries |
| Binary | `-oB file` | Resume-friendly |

### JSON query with jq

```bash
# All open ports per host
jq '.[] | {ip:.ip, port:.ports[0].port, proto:.ports[0].proto}' results.json

# Count unique hosts
jq -r '.[].ip' results.json | sort -u | wc -l

# Filter by port
jq '.[] | select(.ports[0].port == 445) | .ip' results.json
```

## Exclude File Format

```
# /etc/masscan/exclude.conf
# One CIDR/IP per line — never scan these
10.0.0.1            # default gateway
192.168.1.1
224.0.0.0/4         # multicast
```

## Adapter Issues

```bash
# If masscan can't find default gateway:
arp -n | head -5                          # find gateway MAC
masscan ... --router-mac AA:BB:CC:DD:EE:FF

# Multiple interfaces — force specific one:
masscan ... --adapter eth1 --adapter-ip 192.168.2.10
```

## Binary Output for Resume

```bash
# Start scan to binary
masscan 10.0.0.0/8 -p1-65535 --rate=100000 -oB scan.bin

# If interrupted, resume from paused.conf (auto-created)
masscan --resume paused.conf

# Convert binary to JSON later
masscan --readscan scan.bin -oJ results.json
```

## Combining Masscan + Nmap (Pipeline Script)

```bash
#!/bin/bash
TARGET="$1"
RATE="${2:-5000}"

echo "[*] Masscan port discovery..."
masscan "$TARGET" -p1-65535 --rate="$RATE" -oG masscan_raw.txt 2>/dev/null

PORTS=$(grep "open" masscan_raw.txt | awk '{print $4}' | cut -d/ -f1 | sort -u | paste -sd,)
HOSTS=$(grep "open" masscan_raw.txt | awk '{print $6}' | sort -u)

if [ -z "$PORTS" ]; then
  echo "[-] No open ports found"
  exit 1
fi

echo "[*] Open ports: $PORTS"
echo "[*] Nmap service scan..."
echo "$HOSTS" > hosts.txt
nmap -sV -sC -O -p"$PORTS" -iL hosts.txt -oA nmap_services --open
```
