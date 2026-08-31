---
name: hashcat
description: "Auth/lab ref: GPU-accelerated offline password recovery for hashes, network captures, and encrypted-volume headers. Use for dictionary, rule, mask, hybrid, and TrueCrypt/VeraCrypt header campaigns."
license: MIT
compatibility: "Linux, Windows, macOS."
metadata:
  author: AeonDave
  version: "1.1"
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

## TrueCrypt Header Campaigns

For a standard non-system file container, preserve all four 512-byte header candidates before cracking:

```bash
vol=volume.tc
size=$(stat -c %s "$vol")
dd if="$vol" of=header-primary-normal.bin iflag=skip_bytes,count_bytes skip=0 count=512 status=none
dd if="$vol" of=header-primary-hidden.bin iflag=skip_bytes,count_bytes skip=65536 count=512 status=none
dd if="$vol" of=header-backup-normal.bin iflag=skip_bytes,count_bytes skip=$((size-131072)) count=512 status=none
dd if="$vol" of=header-backup-hidden.bin iflag=skip_bytes,count_bytes skip=$((size-65536)) count=512 status=none
sha256sum header-*.bin
```

TrueCrypt legacy mode matrix:

| Header PRF | XTS 512 | XTS 1024 | XTS 1536 |
|---|---:|---:|---:|
| RIPEMD-160 | `6211` | `6212` | `6213` |
| SHA-512 | `6221` | `6222` | `6223` |
| Whirlpool | `6231` | `6232` | `6233` |

- Do not stop at modes ending in `1`; XTS 1024/1536 cascade configurations require the `...2`/`...3` modes.
- Test primary and backup headers independently. A stale or damaged primary header does not invalidate its backup.
- Record source offset, mode, candidate set, and potfile per run; a random-looking header or extractor output is not proof of format.
- VeraCrypt mode families and input formats differ by PRF, legacy/boot mode, and PIM. Confirm them with `hashcat -hh | grep -i veracrypt` and use the extractor's `$veracrypt$...` record instead of assuming a raw TrueCrypt header contract.
- Start with exact evidence-derived candidates across the complete applicable mode/header matrix before widening rules or masks.
- Validate any recovered candidate through a read-only mount and filesystem listing; potfile output alone is not a decryption oracle.

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

## Session Management

```bash
# Named session (survives interruption)
hashcat -a 0 -m 1000 hashes.txt rockyou.txt --session mysession

# Resume session
hashcat --session mysession --restore
```

## PRINCE Attack (`-a 9`)

```bash
# Requires princeprocessor (pp64.bin)
pp64.bin wordlist.txt | hashcat -a 0 -m 1000 hashes.txt
# Or native (hashcat 6.2+)
hashcat -a 9 -m 1000 hashes.txt wordlist.txt
```

## Combinator Attack (`-a 1`)

```bash
# Concatenate every word from list1 with every word from list2
hashcat -a 1 -m 1000 hashes.txt words1.txt words2.txt

# Add rules to left/right side
hashcat -a 1 -m 1000 hashes.txt words1.txt words2.txt -j '$-' -k 'l'
```

## Resources

| File | When to load |
|------|--------------|
| `references/rules-and-masks.md` | Rule file reference, mask cookbook, wordlist recommendations, hash extraction commands |
