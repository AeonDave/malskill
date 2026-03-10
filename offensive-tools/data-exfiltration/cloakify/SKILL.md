---
name: cloakify
description: "Exfiltrate data by encoding it as innocuous-looking strings (tweets, chess moves, cat names). Use when needing to bypass DLP tools by disguising exfiltrated data as benign traffic or files."
license: MIT
compatibility: "Python 2/3; Linux/macOS; github.com/TryCatchHCF/Cloakify"
metadata:
  author: AeonDave
  version: "1.0"
---

# Cloakify

Data exfiltration via steganographic encoding — disguise payloads as benign content.

## Quick Start

```bash
git clone https://github.com/TryCatchHCF/Cloakify
cd Cloakify

# Encode file into disguised output
python cloakify.py payload.zip ciphers/desserts.ciph > exfil.txt

# Decode on attacker side
python decloakify.py exfil.txt ciphers/desserts.ciph > payload.zip
```

## Core Usage

| Command | Purpose |
|---------|---------|
| `cloakify.py <file> <cipher>` | Encode payload with cipher |
| `decloakify.py <file> <cipher>` | Decode back to original |
| `listCiphers.py` | Show available ciphers |
| `addNoise.py` | Add noise lines to output |
| `removeNoise.py` | Strip noise before decoding |

## Available Ciphers (examples)

`desserts` · `movies1984` · `chessOpenings` · `twitterFavoriteEmoji` · `ATampTAreaCodes` · `geo_lattitude`

## Common Workflows

**Exfil over DNS (combine with dnscat):**
```bash
# 1. Encode
python cloakify.py secrets.txt ciphers/desserts.ciph > encoded.txt
# 2. Paste each line as DNS query hostname
# 3. Decode on C2
python decloakify.py captured.txt ciphers/desserts.ciph
```

**Add noise to evade pattern matching:**
```bash
python cloakify.py payload.zip ciphers/movies1984.ciph | python addNoise.py 10 > noisy.txt
python removeNoise.py noisy.txt 10 | python decloakify.py /dev/stdin ciphers/movies1984.ciph
```

## Resources

| File | When to load |
|------|--------------|
| `references/` | Cipher creation guide |
