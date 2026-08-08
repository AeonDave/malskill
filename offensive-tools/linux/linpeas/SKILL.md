---
name: linpeas
description: "Auth/lab ref: LinPEAS Linux privilege review; weak permissions, services, env/config exposure, kernel hints, report triage."
license: GPL-3.0
compatibility: "Linux (any distro); Bash script; no dependencies."
metadata:
  author: AeonDave
  version: "1.0"
---

# LinPEAS

Linux Privilege Escalation Awesome Suite — comprehensive system audit for privilege escalation assessment.

## Quick Start

```bash
# Download and run in one line
curl -L https://github.com/carlospolop/PEASS-ng/releases/latest/download/linpeas.sh | bash

# Or local file
bash linpeas.sh

# Quiet mode (critical findings only)
bash linpeas.sh -q

# Export to file
bash linpeas.sh > enum_full.txt 2>&1

# Aggressive all-checks mode
bash linpeas.sh -a 2>&1 | tee linpeas_full.out

# Run as root (more thorough)
sudo bash linpeas.sh
```

## Key Enumeration Areas

| Category | What's Checked | Critical Findings |
|---|---|---|
| **System Info** | Kernel version, distro, architecture, hostname | Unpatched kernel (CVE), old distro |
| **Users & Groups** | All users, sudoers, groups, sudo access | Overprivileged users, sudo without password |
| **Network** | Network interfaces, open ports, connections | Listening privileged ports, root services |
| **Services & Daemons** | Running services, startup scripts, service perms | World-writable service binaries, root scripts |
| **Cron Jobs** | Crontab entries, cron.d scripts, anacron | Root crons with weak perms, writable scripts |
| **SUID/SGID Binaries** | SUID/SGID files, permissions, known vulns | Exploitable binaries (nmap, cp, sudo) |
| **Capabilities** | Linux capabilities on binaries | cap_setuid, cap_net_raw on user tools |
| **File Permissions** | Writable directories, SGID abuse, world-writable | Writable /etc/, /root, /home paths |
| **Credentials** | /etc/shadow readable, .bashrc creds, SSH keys | Readable shadow, hardcoded passwords |
| **SSH** | SSH keys in home dirs, SSH configs, authorized_keys | Private keys, known_hosts data |
| **Containers** | Docker group membership, container escape paths | Docker socket, privileged containers |
| **PAM & NSS** | PAM config, LDAP/NIS bindings | Weak auth mechanisms, credential stores |
| **Kernel Exploits** | CVEs matching kernel version | Exploitable kernel bugs (DirtyCOW, OverlayFS) |
| **Sudo Config** | NOPASSWD entries, sudoers misconfigs | sudo without password, wildcards in sudoers |
| **Application Configs** | Database configs, web app secrets, API keys | Plaintext DB creds, API keys in configs |

## Core Flags

| Flag | Description |
|---|---|
| `-q` | Quiet mode (only critical findings) |
| `-P <pass>` | Try supplied password against sudo prompts where relevant |
| `-s` | Search for passwords in common files |
| `-g` | Search common paths for hidden files |
| `-p` | Password list for bruteforcing (optional) |
| `-t <N>` | Time limit (seconds) |
| `-a` | All checks (aggressive mode) |

## Common Workflows

### Initial user-space enumeration
```bash
bash linpeas.sh -q 2>/dev/null | grep -i "root\|sudo\|exploit"
# Quick summary of exploitable paths
```

### Full audit (from low-priv user)
```bash
bash linpeas.sh | tee /tmp/lp.txt
# Review output for:
# 1. SUID/SGID binaries with known exploits
# 2. Sudo entries without password
# 3. Writable system files / cron scripts
# 4. Kernel vulnerabilities
# 5. Unpatched services running as root
```

### After gaining root, check for persistence vectors
```bash
sudo bash linpeas.sh
# Identify ways to maintain access:
# - Backdoor cron jobs
# - SSH key insertion
# - Rootkit opportunities
# - Hidden user accounts
```

### Credential harvesting preparation
```bash
bash linpeas.sh -s
# Scans for plaintext passwords in common locations:
# - /home/*/.*profile / .bashrc / .zshrc
# - /etc/mysql/my.cnf
# - /etc/postgresql/postgresql.conf
# - Application configs
```

## Key Findings Priority

🔴 **CRITICAL** — Immediate escalation:
- SUID binary with known public exploit matching kernel
- Sudo entry with NOPASSWD + command
- Unpatched kernel with PoC available
- World-writable cron script running as root
- Plaintext root password in config file

🟠 **HIGH** — Likely exploitable:
- SUID binary (even without known exploit, reverse engineer)
- Writable system binary / script
- Capability-based (cap_setuid on user tool)
- Sudo with wildcard or glob expansion
- /etc/shadow readable by current user

🟡 **MEDIUM** — Context-dependent:
- Weak cron script perms (depends on what it does)
- SSH keys with weak perms
- Database credentials in config

## Output Interpretation

LinPEAS color codes findings:

- 🟢 **Green** — Not exploitable or low risk
- 🟡 **Yellow** — Worth investigating, potentially exploitable
- 🔴 **Red** — High priority, likely exploitable
- 💛 **Red with [!]** — Critical, exploitable now

Also prioritize lines flagged like `99% PE` or equivalent high-confidence markers before spending time on weaker leads.

**Findings are grep excerpts, not proof — read the full file before acting.** LinPEAS often prints only the matching line (e.g. just the `auth ... pam_permit.so` line of `/etc/pam.d/common-auth`, or a single sudoers/cron line), which can read like a misconfiguration or auth bypass the complete file does not actually support. Confirm the whole file first. Its version-based CVE hits (Kernel Exploit Registry, and service LPEs like PackageKit/`pkexec`/sudo) are stronger, verifiable leads — a held-back package version is often the intended path.

## Post-LinPEAS Workflow

1. **Triage findings** — focus on red/critical items first
2. **Verify exploitability** — manually test (can you write to that file? does sudo work?)
3. **Build exploit** — craft shell script, compile, or use existing tool (e.g., `sudo -l`, `find` SUID abuse)
4. **Execute escalation** — run exploit, verify root shell
5. **Check for further privesc** — re-run LinPEAS at root level, identify lateral movement or persistence

## Combining with Other Tools

| Tool | Use Case |
|---|---|
| **linux-exploit-suggester** | Map kernel version to CVEs; compare with LinPEAS findings |
| **mimipenguin** | Dump memory for credentials; use LinPEAS to find process PIDs |
| **pwncat** | Catch shell + automatic privilege escalation attempt |
| **BeRoot** | Lighter alternative; quick SUID/capabilities scan |

## Resources

| File | When to load |
|---|---|
| `references/` | Kernel exploit compilation, SUID abuse techniques, sudo exploitation |
