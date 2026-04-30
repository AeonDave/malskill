# EyeWitness — Report Structure, Categories & Integration

## Report Structure

```
eyewitness_output/
├── report.html          # Main HTML report (open this)
├── Eyewitness.db        # SQLite database with all results
├── Matches/             # Signature-matched screenshots
│   ├── Cisco/
│   ├── Citrix/
│   ├── Login_Pages/
│   ├── VMware/
│   ├── Fortinet/
│   └── ...
├── Screenshots/         # All raw PNGs
│   ├── http_target_com.png
│   └── ...
└── open_ports.csv       # If --active-scan used
```

## Signature Categories (Matches/)

EyeWitness auto-categorizes screenshots by signature matching:

| Category | Description |
|----------|-------------|
| `Login_Pages` | Generic login forms |
| `Cisco` | Cisco ASA, IOS, ASDM |
| `Citrix` | Citrix NetScaler, StoreFront |
| `VMware` | vSphere, ESXi, Horizon |
| `Fortinet` | FortiGate, FortiManager |
| `F5` | F5 BIG-IP |
| `Juniper` | Junos, SRX |
| `Palo_Alto` | PAN-OS |
| `Jenkins` | Jenkins CI/CD |
| `Tomcat` | Apache Tomcat Manager |
| `Default_Pages` | Apache/nginx default install pages |
| `Error_Pages` | 500/403 error pages |
| `Printers` | Network printers |

## Report HTML Navigation

```
Report opens with:
- Total hosts screenshotted
- Categorized results (Matches first)
- Thumbnail grid view
- Click thumbnail → full screenshot + HTTP headers + response code
- Navigation: Next / Previous / Back to top
```

## SQLite Database Queries

```bash
# Open database
sqlite3 Eyewitness.db

# List all tables
.tables

# All captured hosts
SELECT host, port, service, http_status FROM hosts;

# Only 200 OK responses
SELECT host, port, http_status, page_title FROM hosts WHERE http_status=200;

# Find login-related titles
SELECT host, page_title FROM hosts WHERE page_title LIKE '%login%' OR page_title LIKE '%admin%';

# Export to CSV
.mode csv
.output interesting.csv
SELECT host, port, http_status, page_title FROM hosts WHERE http_status=200;
.quit
```

## Integration Workflows

### Full Recon → Screenshot Pipeline

```bash
#!/bin/bash
TARGET=$1
OUTDIR="recon_${TARGET}"
mkdir -p "$OUTDIR"

# Step 1: subdomain enum + live check
subfinder -d "$TARGET" -silent -all | \
  dnsx -silent | \
  httpx -silent -ports 80,443,8080,8443,3000,5000,8888 | \
  tee "${OUTDIR}/live_hosts.txt"

# Step 2: screenshot
eyewitness -f "${OUTDIR}/live_hosts.txt" --web \
  -d "${OUTDIR}/screenshots" \
  --no-prompt --threads 10

echo "Report: ${OUTDIR}/screenshots/report.html"
```

### From Nmap/Masscan

```bash
# nmap → EyeWitness
nmap -sV -p 80,443,8080,8443 -oX nmap.xml 192.168.1.0/24
eyewitness -x nmap.xml --web -d ew_report/ --no-prompt

# masscan → httpx → EyeWitness
masscan -p 80,443,8080,8443 10.0.0.0/24 --rate 10000 -oX masscan.xml
cat masscan.xml | grep "addr=" | grep -oP 'addr="\K[^"]+' | \
  while read ip; do echo "http://$ip"; done | \
  httpx -silent | \
  eyewitness --web -f /dev/stdin -d ew_out/ --no-prompt
```

### RDP Internal Network

```bash
# Screenshot all RDP hosts on internal network
nmap -p 3389 10.0.0.0/24 -oG - | grep "3389/open" | awk '{print $2}' > rdp_hosts.txt
eyewitness -f rdp_hosts.txt --rdp -d rdp_report/ --no-prompt
```

## Tips

- **Always use `--no-prompt`** in pipelines to avoid interactive Y/N prompts
- **Use `--threads 10-20`** — higher = more Chromium instances = more RAM
- **`--timeout 7`** (default) works for most; increase to 15s for slow targets
- Report is offline HTML — open in browser, no server needed
- Large scans: filter interesting screenshots first via Matches/ subdirectory
