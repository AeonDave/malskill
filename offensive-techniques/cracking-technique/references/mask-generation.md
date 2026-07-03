# Mask Strategy Reference

Mask-based attacks for hash cracking when password policies are known.

## Mask Fundamentals

Masks define password structure using placeholders:
- `?l` = lowercase letters (a-z)
- `?u` = uppercase letters (A-Z)
- `?d` = digits (0-9)
- `?s` = special characters (!@#$% etc.)
- `?h` = hex lowercase (0-9, a-f)
- `?H` = hex uppercase (0-9, A-F)
- `?a` = `?l?u?d?s` (letters + digits + specials, ~95 chars)
- `?b` = 0x00-0xff (all bytes; use `--hex-charset` for binary keyspaces)

**Examples:**
- `?l?l?l?l?l?l?l` → 6 lowercase chars
- `?u?l?l?l?l?l?l?d` → 5 chars + digit (common policy)
- `?l?l?l?l?s?d?d` → 4 chars + special + 2 digits
- `?a?a?a?a?a` → 5 printable chars

## Mask Generation (CLI)

```bash
# Generate candidates inline with hashcat
hashcat --stdout -a 3 ?l?l?l?l?l?l?l --increment

# Use maskprocessor for .hcmask files
mp64.bin ?l?l?l?l?l?l?l > policy.hcmask

# PRINCE algorithm for advanced pattern generation
princeprocessor --elem-cnt-min=4 --elem-cnt-max=8 wordlist.txt > candidates.txt
```

## Mask Attack Execution

### Basic mask attack

```bash
# Simple mask
hashcat -m 0 hashes.txt -a 3 ?l?l?l?l?l?l?l

# With custom charset
hashcat -m 0 hashes.txt -a 3 -1 ?l?u ?l?l?l?l?l?l?l?d

# Increment (try shorter first)
hashcat -m 0 hashes.txt -a 3 ?l?l?l?l?l?l?l --increment --increment-min 4 --increment-max 8
```

### Advanced mask patterns

```bash
# Known prefix pattern (e.g., fixed company name as prefix)
hashcat -m 0 hashes.txt -a 3 CompanyName?d?d?d?d

# Corporate policy (1 uppercase, 6 lowercase, 1 digit)
hashcat -m 0 hashes.txt -a 3 ?u?l?l?l?l?l?l?l?d

# Complex policy (min 8, must have special)
hashcat -m 0 hashes.txt -a 3 ?l?l?l?l?l?l?l?l?l?s?d

# Multiple lengths with increment
hashcat -m 0 hashes.txt -a 3 ?l?l?l?l?l?l?l?l?l?l --increment --increment-min 6 --increment-max 10
```

## Mask File (.hcmask) Format

One mask per line:

```
# 6-char lowercase
?l?l?l?l?l?l

# 7-char with digit
?l?l?l?l?l?l?d

# 8-char corporate
?u?l?l?l?l?l?l?l?d

# Fixed prefix + variable suffix
Company?d?d?d?d
```

## Recommended Mask Sets

### Corporate policy (8+ chars, complexity)

```
# Min 8 chars, mix of cases, digits, specials
?u?l?l?l?l?l?l?l?l?d?s
?u?l?l?l?l?l?l?l?l?l?d?s
?u?l?l?l?l?l?l?l?l?l?l?d?s
```

### Simple passwords (6-8 chars)

```
?l?l?l?l?l?l?l
?l?l?l?l?l?l?l?l
?l?l?l?l?l?l?l?l?l
?d?d?d?d?d?d?d?d
```

## Mask vs Dictionary

| Scenario | Prefer | Why |
|----------|---------|-----|
| Known policy | Mask | Precise structure |
| Unknown policy | Dict + rules | Better coverage |
| Fixed-format password | Mask | Known format |
| Leak analysis | Dict + rules | Real-world patterns |
| Quick test | Mask | Fast feedback |

## Common Pitfalls

- **Too complex mask** → keyspace explosion (billions of combinations)
- **Wrong charset** → missing valid passwords
- **No increment** → fixed length may miss variants
- **Ignoring policy** → wasting time on wrong patterns
- **Not combining** → masks + dict often better (hybrid mode `-a 6` or `-a 7`)

## Hybrid Attacks (Dict + Mask)

```bash
# Dict + mask (dict = prefix, mask = suffix)
hashcat -m 0 hashes.txt -a 6 wordlist.txt ?d?d?d

# Mask + dict (mask = prefix, dict = suffix)
hashcat -m 0 hashes.txt -a 7 ?u?l?l?l?l?l?l?l wordlist.txt
```

## Tool References

| Tool | When to use |
|------|-------------|
| `hashcat` | Execute mask attacks (-a 3) |
| `hashcat --increment` | Try multiple lengths efficiently |
| `hashcat -1` | Custom charset definition |
