# John the Ripper — Formats, *2john Tools, Rule Syntax

## Common Format Names (`--format=`)

| Format | Hash source |
|--------|------------|
| `NT` | Windows NTLM (SAM/NTDS) |
| `netntlmv2` | NTLMv2 challenge-response (Responder) |
| `krb5tgs` | Kerberos TGS (Kerberoasting) |
| `krb5asrep` | Kerberos AS-REP (AS-REP roasting) |
| `sha512crypt` | Linux /etc/shadow $6$ |
| `md5crypt` | Linux /etc/shadow $1$ |
| `bcrypt` | $2a$ / $2b$ |
| `sha256crypt` | Linux $5$ |
| `descrypt` | Classic Unix DES |
| `md5` | Raw MD5 |
| `sha1` | Raw SHA1 |
| `Raw-SHA256` | Raw SHA256 |
| `wpapsk` | WPA/WPA2 PSK |
| `rar5` | RAR5 archives |
| `zip` | PKZIP |
| `7z` | 7-Zip |
| `pdf` | PDF user password |
| `office` | Office 2007-2016 |
| `keepass` | KeePass 1.x/2.x |
| `ssh` | SSH private key passphrase |
| `pgp` | PGP/GPG key passphrase |

```bash
# List all supported formats
john --list=formats | tr ',' '\n'
```

## *2john Tools

| Tool | Input | Usage |
|------|-------|-------|
| `ssh2john` | SSH private key | `ssh2john id_rsa > hash` |
| `zip2john` | ZIP archive | `zip2john file.zip > hash` |
| `rar2john` | RAR archive | `rar2john file.rar > hash` |
| `7z2john` | 7-Zip archive | `7z2john file.7z > hash` |
| `pdf2john` | PDF file | `pdf2john file.pdf > hash` |
| `office2john` | Office doc | `office2john file.docx > hash` |
| `keepass2john` | KeePass DB | `keepass2john db.kdbx > hash` |
| `pgp2john` | PGP key | `pgp2john key.asc > hash` |
| `pwsafe2john` | Password Safe | `pwsafe2john db.psafe3 > hash` |
| `bitlocker2john` | BitLocker image | `bitlocker2john -i image.img > hash` |
| `luks2john` | LUKS volume | `luks2john /dev/sda > hash` |
| `truecrypt2john` | TrueCrypt volume | `truecrypt2john volume.tc > hash` |

All tools located at `/usr/share/john/` or on PATH in jumbo builds.

## Rule Syntax Reference

Rules go in `john.conf` under `[List.Rules:<name>]`. Applied left-to-right.

### Position / Length Guards

| Command | Meaning |
|---------|---------|
| `>N` | Reject if word length ≤ N |
| `<N` | Reject if word length ≥ N |
| `_N` | Reject if length ≠ N |

### Case / Character Transforms

| Command | Effect |
|---------|--------|
| `l` | Lowercase all |
| `u` | Uppercase all |
| `c` | Capitalize first, lowercase rest |
| `C` | Lowercase first, uppercase rest |
| `t` | Toggle case of all |
| `TN` | Toggle case at position N |
| `r` | Reverse word |
| `d` | Duplicate word |
| `f` | Reflect (word + reversed) |

### Append / Prepend

| Command | Effect |
|---------|--------|
| `Az"X"` | Append string X |
| `A0"X"` | Prepend string X |
| `$X` | Append char X |
| `^X` | Prepend char X |

### Substitution

| Command | Effect |
|---------|--------|
| `sXY` | Replace char X with Y |
| `@X` | Delete all occurrences of X |

### Insertion / Deletion

| Command | Effect |
|---------|--------|
| `iNX` | Insert char X at position N |
| `oNX` | Overwrite char at position N with X |
| `DN` | Delete char at position N |
| `'N` | Truncate to length N |

### Example Rule: Corporate Password Policy

```ini
[List.Rules:Corporate]
# Capitalize + append year 2020-2025
c Az"2020"
c Az"2021"
c Az"2022"
c Az"2023"
c Az"2024"
c Az"2025"
# Capitalize + append ! or @
c Az"!"
c Az"@"
# l33t substitution + capitalize
l sa@ se3 si1 so0 c
```

## Built-in Rule Sets

| Name | Description |
|------|-------------|
| `single` | Username-based mangling (fast) |
| `wordlist` | Basic wordlist rules |
| `best64` | 64 effective rules |
| `jumbo` | Comprehensive jumbo ruleset |
| `KoreLogic` | KoreLogic contest rules |
| `NT` | Rules tuned for NT hashes |
