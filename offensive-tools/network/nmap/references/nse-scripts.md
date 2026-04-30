# Nmap NSE Scripts Reference

## Script Categories

| Category | Trigger with | Content |
|----------|-------------|---------|
| `default` (`-sC`) | Automatic | Safe, common enumeration |
| `safe` | `--script safe` | No harmful side effects |
| `discovery` | `--script discovery` | Host/service enumeration |
| `vuln` | `--script vuln` | Vulnerability checks |
| `auth` | `--script auth` | Default/blank credential checks |
| `brute` | `--script brute` | Password brute-force |
| `exploit` | `--script exploit` | Active exploitation |
| `intrusive` | `--script intrusive` | May crash/alter services |
| `malware` | `--script malware` | Backdoor detection |

## Key Vuln Scripts

```bash
# MS17-010 (EternalBlue)
nmap --script smb-vuln-ms17-010 -p 445 <target>

# SMB vuln suite
nmap --script "smb-vuln-*" -p 445 <target>

# MS08-067 (Conficker era)
nmap --script smb-vuln-ms08-067 -p 445 <target>

# Heartbleed (OpenSSL)
nmap --script ssl-heartbleed -p 443 <target>

# ShellShock
nmap --script http-shellshock --script-args uri=/cgi-bin/test.sh -p 80 <target>

# SNMP enum
nmap --script snmp-info -sU -p 161 <target>

# SSL/TLS weaknesses
nmap --script ssl-enum-ciphers -p 443 <target>
```

## SMB Enumeration

```bash
# OS, domain, SMB version
nmap --script smb-os-discovery -p 445 <target>

# Enumerate shares
nmap --script smb-enum-shares -p 445 <target>

# Enumerate users
nmap --script smb-enum-users -p 445 <target>

# Session info
nmap --script smb-security-mode -p 445 <target>
```

## HTTP Enumeration

```bash
# Title + headers + methods
nmap --script http-title,http-headers,http-methods -p 80,8080 <target>

# Directory brute-force
nmap --script http-enum -p 80 <target>

# Web server version (detailed)
nmap --script http-server-header -p 80 <target>

# Find admin pages
nmap --script http-auth-finder -p 80 <target>

# Robots.txt
nmap --script http-robots.txt -p 80 <target>
```

## FTP

```bash
# Anonymous login check
nmap --script ftp-anon -p 21 <target>

# FTP banner + bounce
nmap --script ftp-bounce,ftp-syst -p 21 <target>
```

## DNS

```bash
# Zone transfer
nmap --script dns-zone-transfer --script-args dns-zone-transfer.domain=<domain> -p 53 <target>

# Brute subdomains
nmap --script dns-brute --script-args dns-brute.domain=<domain> <target>
```

## LDAP / Active Directory

```bash
# LDAP enum (root DSE)
nmap --script ldap-rootdse -p 389 <target>

# LDAP search
nmap --script ldap-search -p 389 <target>
```

## Database Services

```bash
# MySQL enum
nmap --script mysql-info,mysql-databases,mysql-empty-password -p 3306 <target>

# MSSQL info
nmap --script ms-sql-info,ms-sql-empty-password -p 1433 <target>

# PostgreSQL
nmap --script pgsql-brute -p 5432 <target>
```

## Brute-Force Scripts

```bash
# SSH
nmap --script ssh-brute -p 22 <target>

# HTTP basic auth
nmap --script http-brute -p 80 <target>

# FTP
nmap --script ftp-brute -p 21 <target>

# Custom wordlists
nmap --script ssh-brute --script-args userdb=users.txt,passdb=passwords.txt -p 22 <target>
```

## Script Args Pattern

```bash
--script-args <key>=<value>,<key2>=<value2>

# Common args
--script-args uri=/path/to/test          # HTTP path
--script-args username=admin             # Credential
--script-args password=admin
--script-args newtargets                 # Add discovered hosts to scan
```

## Find Scripts

```bash
# List all vuln scripts
ls /usr/share/nmap/scripts/ | grep vuln

# Search by keyword
ls /usr/share/nmap/scripts/ | grep smb

# Script help
nmap --script-help smb-vuln-ms17-010
```
