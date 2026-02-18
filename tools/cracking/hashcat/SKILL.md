---
name: hashcat
description: "GPU-accelerated offline password cracking tool supporting 300+ hash types. Use when asked to crack password hashes, recover passwords from NTLM/Net-NTLMv2/Kerberos/bcrypt/MD5/SHA hashes, perform wordlist or rule-based attacks, or conduct mask brute-force against any captured hash."
license: MIT
compatibility: "Linux, Windows, macOS. Install: apt install hashcat (Kali) or download from hashcat.net. Requires GPU (NVIDIA CUDA or AMD OpenCL) for performance; CPU mode available."
metadata:
  author: AeonDave
  version: "1.0"
---

# Hashcat

GPU-accelerated offline hash cracker — the standard tool for password recovery in offensive ops.

## Quick Start

```bash
# Wordlist attack on NTLM hashes
hashcat -a 0 -m 1000 hashes.txt rockyou.txt

# Rule-based wordlist attack
hashcat -a 0 -m 1000 hashes.txt rockyou.txt -r /usr/share/hashcat/rules/best64.rule

# Mask brute-force (8-char, uppercase + digits)
hashcat -a 3 -m 1000 hashes.txt ?u?u?u?u?d?d?d?d
```

## Attack Modes

| Mode | Flag | Description |
|------|------|-------------|
| Wordlist | `-a 0` | Dictionary attack |
| Combination | `-a 1` | Combine two wordlists |
| Brute-force | `-a 3` | Mask/charset brute-force |
| Rule-based | `-a 0 -r` | Wordlist + transformation rules |
| Hybrid | `-a 6/-a 7` | Wordlist + mask or mask + wordlist |

## Common Hash Types (`-m`)

| Hash | Mode | Source |
|------|------|--------|
| NTLM | `1000` | Windows SAM / NTDS dump |
| Net-NTLMv1 | `5500` | Responder capture |
| Net-NTLMv2 | `5600` | Responder capture |
| Kerberos 5 TGS (RC4) | `13100` | Kerberoasting |
| Kerberos 5 AS-REP | `18200` | AS-REP roasting |
| MD5 | `0` | Web app, misc |
| SHA1 | `100` | Web app, misc |
| SHA256 | `1400` | General |
| bcrypt | `3200` | Linux /etc/shadow |
| SHA512crypt | `1800` | Linux /etc/shadow |
| WPA-PMKID | `22000` | WiFi |

## Mask Characters

| Mask | Charset |
|------|---------|
| `?l` | lowercase a-z |
| `?u` | uppercase A-Z |
| `?d` | digits 0-9 |
| `?s` | special chars |
| `?a` | all printable (`?l?u?d?s`) |
| `?b` | all bytes 0x00-0xFF |

## Core Flags

| Flag | Description |
|------|-------------|
| `-a <n>` | Attack mode |
| `-m <n>` | Hash type |
| `-w <n>` | Workload: 1=low, 2=default, 3=high, 4=insane |
| `-O` | Optimized kernels (faster, limited pass length) |
| `--force` | Ignore GPU warnings |
| `-r <file>` | Rules file |
| `--increment` | Increment mask length |
| `--increment-min <n>` | Min mask length |
| `--increment-max <n>` | Max mask length |
| `-o <file>` | Output cracked hashes |
| `--outfmt <n>` | Output format: 2=hash:plain, 3=plain |
| `--show` | Show cracked hashes from potfile |
| `--status` | Real-time status |
| `--restore` | Resume previous session |
| `-S` | Slow candidates (for rules) |

## Common Workflows

```bash
# NTLM with rockyou + best64 rules
hashcat -a 0 -m 1000 ntlm.txt rockyou.txt -r best64.rule -O

# Net-NTLMv2 (Responder capture)
hashcat -a 0 -m 5600 netntlm.txt rockyou.txt -r best64.rule

# Kerberoasting TGS
hashcat -a 0 -m 13100 kerberoast.txt rockyou.txt -r one-rule-to-rule-them-all.rule

# AS-REP roasting
hashcat -a 0 -m 18200 asrep.txt rockyou.txt

# Mask brute-force: 8-char, any printable
hashcat -a 3 -m 1000 hashes.txt -1 ?a ?1?1?1?1?1?1?1?1 --increment --increment-min 6

# Combine wordlist + mask (hybrid)
hashcat -a 6 -m 1000 hashes.txt rockyou.txt ?d?d?d

# Show cracked passwords
hashcat -m 1000 hashes.txt --show
```

## Resources

| File | When to load |
|------|--------------|
| `references/rules-and-masks.md` | Rule file reference, mask cookbook, wordlist recommendations, hash extraction commands |

## Structuring This Skill
