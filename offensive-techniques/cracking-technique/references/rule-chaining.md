# Rule Chaining Reference

Rule-based transformations for hash cracking wordlists.

## Rule Fundamentals

Rules transform words from wordlists:
- **Case**: `c` (capitalize), `t` (toggle case), `u` (uppercase)
- **Append/prepend**: `$1` (append '1'), `^1` (prepend '1')
- **Replace**: `s$a` (replace 'a' with '$'), `s?d1` (replace digit with '1')
- **Duplicate**: `d` (duplicate word), `p` (duplicate + reverse)
- **Truncate**: `[` (truncate left), `]` (truncate right)

## Rule Types and Effects

| Rule | Name | Effect | Example |
|------|------|--------|---------|
| `best64.rule` | Best64 | 64 common transformations | Multiple case/append/prepend |
| `toggles1.rule` | Toggles1 | Case toggling | `Password` → `pASSWORd` |
| `leetspeak.rule` | Leetspeak | Leet conversion | `Password` → `P@ssw0rd` |
| `specifics_append.rule` | Specifics append | Append specials | `Password` → `Password!` |
| `digits_append.rule` | Digits append | Append digits | `Password` → `Password123` |
| `simple_case.rule` | Simple case | Basic case changes | `password` → `Password` |
| `date_append.rule` | Date append | Append years | `Password` → `Password2024` |
| `date_prepend.rule` | Date prepend | Prepend years | `Password` → `2024Password` |

## Rule Chaining (Order Matters!)

### Basic chaining

```bash
# Single rule
hashcat -m 0 hashes.txt wordlist.txt -r rules/best64.rule

# Chain rules (ORDER MATTERS!)
hashcat -m 0 hashes.txt wordlist.txt -r rules/best64.rule -r rules/toggles1.rule

# Combined rule file
cat rules/best64.rule rules/toggles1.rule rules/leetspeak.rule > combined.rule
hashcat -m 0 hashes.txt wordlist.txt -r combined.rule
```

### Recommended chaining order

```
1. best64.rule        # Base transformations first
2. toggles1.rule       # Case variations
3. leetspeak.rule      # Leet speak
4. digits_append.rule   # Append digits
5. specials_append.rule # Append specials
```

**Why order matters:**
- `best64` creates base variants
- `toggles1` toggles case on those variants
- `leetspeak` converts to leet on expanded set
- `digits_append` adds numbers to leet variants
- Result: exponential coverage

## Rule Attack Execution

### Dictionary + single rule

```bash
# Basic rule application
hashcat -m 0 hashes.txt wordlist.txt -r rules/best64.rule

# Multiple rules (chained)
hashcat -m 0 hashes.txt wordlist.txt -r rules/best64.rule -r rules/toggles1.rule
```

### Rule + mask hybrid

```bash
# Dict + mask with rules
hashcat -m 0 hashes.txt -a 6 wordlist.txt ?d?d?d -r rules/best64.rule

# Mask + dict with rules
hashcat -m 0 hashes.txt -a 7 ?u?l?l?l?l?l?l wordlist.txt -r rules/toggles1.rule
```

## Progressive Rule Strategy

### Pass 1: Large dict + light rules

```bash
# Catch common passwords quickly
hashcat -m 0 hashes.txt broad-wordlist.txt -r rules/best64.rule
```

### Pass 2: Targeted dict + comprehensive rules

```bash
# Increase coverage with more rules
hashcat -m 0 hashes.txt osint-wordlist.txt -r rules/best64.rule -r rules/toggles1.rule
```

### Escalation policy: wordlist → rules → hybrid

Prefer this order unless recovered passwords prove another pattern:

1. **High-signal wordlists**: usernames, company/product names, local language terms, seasons, project names, small top lists.
2. **Rules**: mutate those words with capitalization, digits, years, separators, symbols, and light leet.
3. **Hybrid suffix/prefix**: only after cracked samples show consistent suffix/prefix structure.
4. **Masks**: last resort for known policy formats; keep them narrow and time-boxed.

Why: real user passwords often preserve meaningful words. Rules mutate meaning-bearing words intelligently; broad masks spend most cycles on strings humans rarely choose.

### Pass 3: Small dict + micro-rules

```bash
# Highly targeted with micro-transformations
hashcat -m 0 hashes.txt osint-words.txt -r rules/digits_append.rule -r rules/specials_append.rule -r rules/date_append.rule
```

## Creating Custom Rules

### Basic rule syntax

```
# Append digit 1-9
$1
$2
$3
...

# Prepend digit
^1
^2
^3
...

# Toggle case (invert case)
t
t1  # Toggle first char
t2  # Toggle second char
...

# Replace
s$a  # Replace 'a' with '$'
s$e  # Replace 'e' with '3'
s?d0  # Replace any digit with '0'

# Duplicate + reverse
p  # Duplicate word + reverse second
d  # Duplicate word
```

### Example custom rule file

```bash
# Append years 2000-2026
$2$0$0$0
$2$0$0$1
$2$0$0$2
...
$2$0$2$6
```

## Common Pitfalls

- **Wrong rule order** → suboptimal results (best64 should be first)
- **Too many rules** → keyspace explosion, slow execution
- **Rules on huge noisy lists** → wastes GPU time; use smaller target-aware lists when chaining heavy rules
- **Ignoring results** → not analyzing cracked to refine rules
- **Single rule only** → missing variations
- **Not chaining** → poor coverage compared to chained rules

## Rule Coverage Examples

| Base word | Rule applied | Result |
|-----------|---------------|--------|
| `password` | `best64` | `Password`, `PASSWORD`, `Password1!` |
| `Password` | `toggles1` | `pASSWORd`, `PaSsWoRd` |
| `Password` | `leetspeak` | `P@ssw0rd`, `P4ssw0rd` |
| `Password` | `digits_append` | `Password123`, `Password2024` |
| `Password` | `specials_append` | `Password!`, `Password@` |

## Tool References

| Tool | When to use |
|------|-------------|
| `hashcat` | Apply rules (-r flag) |
| `rules/best64.rule` | 64 common transformations |
| `rules/toggles1.rule` | Case toggling variations |
| `rules/leetspeak.rule` | Leet speak conversion |
| `rules/*_append.rule` | Append digits/specials/dates |
