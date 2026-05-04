# Progressive Cracking Strategy Reference

Multi-pass approach to maximize results and time efficiency.

## Strategy Overview

**Progressive approach**: Start with fast signal → move into target-specific wordlists + rules → use hybrid/mask only when the observed pattern justifies it.

```
Pass 1: Small/high-signal baselines + light rules (catch low-hanging fruit)
Pass 2: Target-specific dictionaries + comprehensive rules (names, org terms, dates, local context)
Pass 3: Small/specific dictionaries + micro-rules (targeted variations)
Pass 4: Hybrid wordlist+suffix/prefix or narrow masks only when pattern evidence supports them
```

## Pass 1: High-signal dictionaries + light rules

### Objective

Quickly catch the most common passwords without exploding the keyspace.

### Execution

```bash
# Top/common baseline + light rules
hashcat -m 0 hashes.txt top1000.txt -r rules/best64.rule

# Multiple high-signal context sources combined
hashcat -m 0 hashes.txt top1000.txt context-wordlist.txt -r rules/best64.rule

# With potfile (save progress)
hashcat -m 0 hashes.txt broad-wordlist.txt -r rules/best64.rule --potfile=pass1.pot
```

### Expected results

- 30-50% of "weak" passwords cracked
- Fast feedback and early pattern discovery
- Identifies common patterns for next passes

## Pass 2: Targeted dictionaries + comprehensive rules

### Objective

Increase coverage while staying relevant to the target/context. This is the main escalation path: target words plus rules usually beat broad masks.

### Execution

```bash
# Target-specific wordlists (OSINT-derived: names, org terms, cultural context)
hashcat -m 0 hashes.txt osint-wordlist.txt -r rules/best64.rule -r rules/toggles1.rule

# Add leak-derived wordlist if available for the same org/domain
hashcat -m 0 hashes.txt osint-wordlist.txt leak-wordlist.txt -r rules/best64.rule -r rules/toggles1.rule -r rules/leetspeak.rule

# With potfile from pass 1
hashcat -m 0 hashes.txt osint-wordlist.txt -r rules/best64.rule --potfile=pass1.pot
```

### Expected results

- Additional 20-30% of passwords cracked
- More complex patterns (leet speak, case toggling)
- Context-driven (corporate terms, regional vocabulary, OSINT)

## Pass 3: Small/Targeted Dictionaries + Micro-Rules

### Objective

Highly targeted attacks with maximum variation from small wordlists.

### Execution

```bash
# Start from highly targeted OSINT wordlists
hashcat -m 0 hashes.txt osint-words.txt -r rules/digits_append.rule -r rules/specials_append.rule -r rules/date_append.rule

# Generate from cracked patterns
hashcat --stdout -a 3 ?l?l?l?l?l?l?d --increment | head -1000000 > generated.txt
hashcat -m 0 hashes.txt generated.txt -r rules/best64.rule

# Combine micro-rules
cat rules/digits_append.rule rules/specials_append.rule rules/date_append.rule > micro.rule
hashcat -m 0 hashes.txt targeted.txt -r micro.rule
```

### Expected results

- Target-specific passwords cracked
- Variations with digits, specials, dates
- High efficiency (small keyspace, high hit rate)

## Pass 4: Hybrid / narrow masks (evidence-driven)

### Objective

Catch passwords that follow specific policies or known formats. Use this after recovered patterns justify the structure; masks that only express hope waste time.

### Execution

```bash
# From known words + mask
hashcat -m 0 hashes.txt -a 6 known-words.txt ?d?d?d

# Preferred hybrid: target-specific words + likely suffix from observed policy
hashcat -m 0 hashes.txt -a 6 org-products-names.txt ?d?d?s

# Policy-driven masks
hashcat -m 0 hashes.txt -a 3 ?u?l?l?l?l?l?l?l?d?s

# Generate .hcmask from policy constraints
echo "?u?l?l?l?l?l?l?l?d?s" > policy.hcmask
hashcat -m 0 hashes.txt -a 3 policy.hcmask

# Increment for multiple lengths
hashcat -m 0 hashes.txt -a 3 ?l?l?l?l?l?l?l?l?l --increment --increment-min 6 --increment-max 10
```

### Expected results

- Policy-compliant passwords cracked
- Known formats (corporate policy, fixed-structure formats)
- Final cleanup of remaining hashes

## Monitoring and Iteration

### Monitor progress

```bash
# Check potfile
wc -l *.pot

# View cracked passwords
hashcat --show-potfile --potfile=pass1.pot
```

### Analyze results for next pass

1. **Identify patterns** in cracked passwords:
   - Common words, structures, policies
   - Append/prepend patterns (digits, specials)
   - Case patterns (capitalize, toggle, leet)

2. **Generate targeted wordlists** from patterns:
   ```bash
   # Extract base words from cracked
   cut -d: -f2 pass1.pot | cut -d' -f1 > base-words.txt
   ```

3. **Refine masks** based on observed patterns:
   ```bash
   # If most cracked are 8 chars with digit
   echo "?l?l?l?l?l?l?l?l?d" > refined.hcmask
   ```

4. **Iterate** to next step or refine current approach

## Time Allocation (example: 100 hashes, GPU)

| Pass | Attack | Expected time | Expected cracks |
|------|--------|---------------|-------------------|
| 1 | broad-wordlist + best64 | 30 min | 30-50% |
| 2 | osint-wordlist + best64+toggles1 | 1 hour | +20-30% |
| 3 | targeted-wordlist + micro-rules | 30 min | +10-15% |
| 4 | policy.hcmask | 2 hours | +5-10% |
| **Total** | | **4 hours** | **65-105%** |

## Common Pitfalls

- **Starting too large** → slow feedback, poor iteration
- **Jumping to masks too early** → explores structure without target vocabulary signal
- **Not analyzing cracked** → missing pattern insights
- **Ignoring potfile** → re-cracking same passwords
- **Wrong pass order** → inefficient use of time
- **Not iterating** → leaving easy cracks on the table

## Tool References

| Tool | When to use |
|------|-------------|
| `hashcat` | Execute all passes (-a 0/1/3/6/7) |
| `hashcat --potfile` | Save/resume progress |
| `hashcat --show-potfile` | Analyze cracked passwords |
| `hashcat --stdout` | Generate wordlists from masks |
