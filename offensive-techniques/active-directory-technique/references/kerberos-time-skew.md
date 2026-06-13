# Kerberos Time Skew Bypass & Synchronization

**Load when**: An authentication attempt, Impacket script, bloodyAD run, or Kerberos ticket request fails with the error `KRB_AP_ERR_SKEW (Clock skew too great)`.

## The Problem
The Kerberos protocol relies on time-stamped authenticators to prevent replay attacks. If the clock on the attacking machine (e.g., Kali Linux) differs from the Domain Controller's clock by more than 5 minutes (300 seconds), the KDC will refuse the connection.

## Solution 1: Active NTP Synchronization (Requires Root)

If you have `sudo` privileges and the network allows NTP traffic to the DC:

```bash
# Sync local time directly to the Domain Controller
sudo ntpdate -u <DC_IP_or_HOSTNAME>

# In case ntpdate is not installed, use systemd-timesyncd or simply date
# Format: MMDDhhmmYYYY.ss (e.g. Nov 14 15:30 2024 -> 111415302024.00)
sudo date -s "2024-11-14 15:30:00"
```

## Solution 2: libfaketime (No Root Required / Stealthy)

If you do not have root, or NTP packets are blocked by a firewall, you can use `libfaketime` (or the `faketime` wrapper). It intercepts the `time()` system call for a specific program, tricking the tool into thinking the current time matches the DC's time.

### 1. Find the Exact Time of the Domain Controller
Query the remote DC using SMB, LDAP, or RPC without authentication just to read the server's timestamp:
```bash
# Using netexec (CME fallback)
netexec smb <DC_IP>

# Using ldapsearch
ldapsearch -x -H ldap://<DC_IP> -s base | grep currentTime
```

### 2. Run the Tool via Faketime
Once you know the exact time of the target DC, wrap your command with `faketime`:

```bash
# Specific absolute time (format: 'YYYY-MM-DD HH:MM:SS')
faketime '2024-11-14 15:36:00' impacket-wmiexec -k -no-pass dc01.contoso.local

# Relative offsets (e.g., if the DC is exactly 2 hours and 15 mins ahead)
faketime '+2h +15m' impacket-psexec -k -no-pass contoso.local/administrator@dc01.contoso.local

# BloodyAD via faketime
faketime '-1d' proxychains bloodyAD -H dc01 -d contoso.local -k get object administrator
```

### macOS Equivalent
On macOS, `faketime` is usually unavailable due to SIP (System Integrity Protection). The easiest macOS fallback is to use an isolated Docker container with the correct time or temporarily override the system time in System Settings.
