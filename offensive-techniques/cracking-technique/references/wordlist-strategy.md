# Wordlist Strategy Reference

Objective-driven wordlist construction and selection for hash cracking.

## Core Principle

Do not rely on generic pre-made wordlists by name. Build or select wordlists based on the **target context**: who are the users, what language/culture/domain do they operate in, what patterns are visible from OSINT or policy?

## Wordlist Selection by Target Context

| Context | Primary approach | Secondary |
|---------|-----------------|-----------|
| **General breach/leak** | High-frequency vocabulary, known pattern distributions | Combine multiple context sources |
| **Corporate environment** | Employee names, org terms, founding year, product names | Job titles, department names, internal acronyms |
| **Regional/cultural** | Language-specific vocabulary, religious terms, local references | Keyboard layout patterns, regional naming conventions |
| **WiFi/WPA** | ISP/router defaults, location names, ISP naming conventions | Address fragments, installer-default patterns |
| **OSINT-driven** | All terms scraped/collected from the target's public footprint | Social profile data, documents, press releases |

## Target-Specific Wordlist Construction

### Step 1: OSINT Collection

Gather raw material from target context before building any wordlist:

- **LinkedIn / social profiles**: full names, surnames, job titles, departments, connections
- **Target website**: product names, slogans, technical vocabulary, team names
- **Public documents**: presentations, PDFs, announcements — extract domain language
- **Cultural/religious context**: if users share a background, include relevant vocabulary
- **Date patterns**: company founding year, notable events, common birth year ranges (1970–2005)
- **Breach metadata**: if a prior leak exists for the same org, extract known passwords as seeds

### Step 2: Website Scraping with cewl

```bash
# Scrape target website for vocabulary (depth 2, min word length 5)
cewl -d 2 -m 5 https://target.com -w company-words.txt

# Include email addresses (for username-as-password patterns)
cewl -d 2 -m 5 --email https://target.com -w company-words-email.txt
```

### Step 3: Build and Clean the Wordlist

```bash
# Merge all OSINT sources
cat names-osint.txt dates-osint.txt context-words.txt company-words.txt | sort -u > raw-combined.txt

# Clean: remove non-ASCII, enforce length constraints
python3 -c "
with open('raw-combined.txt') as f:
    words = [w.strip() for w in f if 4 <= len(w.strip()) <= 20 and w.isascii()]
with open('clean-wordlist.txt', 'w') as out:
    for w in sorted(set(words)): out.write(w + '\n')
"

# Extract passwords from structured breach data
grep -i "target.com" breach-data.txt | cut -d: -f2 | sort -u > leak-extracted.txt
```

### Step 4: Expand with Masks and Rules

After building the base wordlist, apply rules and masks to generate variations:

```bash
# Apply rules to generate variations of base words
hashcat -m 0 hashes.txt clean-wordlist.txt -r rules/best64.rule -r rules/toggles1.rule

# Hybrid: base word + numeric suffix (e.g., name + year)
hashcat -m 0 hashes.txt -a 6 clean-wordlist.txt ?d?d?d?d

# Hybrid: uppercase prefix + base word (common corporate pattern)
hashcat -m 0 hashes.txt -a 7 ?u clean-wordlist.txt

# PRINCE algorithm: combine word elements from the list
princeprocessor --elem-cnt-min=2 --elem-cnt-max=4 clean-wordlist.txt > prince-candidates.txt
hashcat -m 0 hashes.txt -a 0 prince-candidates.txt
```

## Pattern-Based Generation (No Prior Wordlist)

When no OSINT is available, generate candidates from known policy constraints:

```bash
# Policy-driven mask (e.g., 8-char: uppercase + lowercase + digit)
hashcat --stdout -a 3 ?u?l?l?l?l?l?l?d --increment > policy-candidates.txt

# Use maskprocessor for batch .hcmask generation
mp64.bin ?l?l?l?l?l?l?l > policy.hcmask
hashcat -m 0 hashes.txt -a 3 policy.hcmask

# Markov-chain based generation (statsprocessor)
# Requires a training corpus; builds statistically likely passwords
sp64.bin hcstat2 --pw-min=8 > markov-candidates.txt
```

## Wordlist Combinations (Combinator Attack)

When passwords follow a `word1 + word2` pattern (e.g., name + date, company + year):

```bash
# Combine two wordlists (all pairs)
hashcat -m 0 hashes.txt -a 1 names-list.txt dates-list.txt

# Combine with modifiers applied to each word
hashcat -m 0 hashes.txt -a 1 names-list.txt dates-list.txt -j '$!' -k '$1'
```

## Wordlist Usage in Hashcat

### Basic dictionary attack

```bash
# Single wordlist
hashcat -m 0 hashes.txt wordlist.txt

# Multiple wordlists (order matters for coverage)
hashcat -m 0 hashes.txt osint-words.txt context-words.txt

# With rules
hashcat -m 0 hashes.txt wordlist.txt -r rules/best64.rule
hashcat -m 0 hashes.txt wordlist.txt -r rules/best64.rule -r rules/toggles1.rule
```

### Wordlist + rule chaining

```bash
# Order matters: best64 first, then toggles
hashcat -m 0 hashes.txt wordlist.txt -r rules/best64.rule -r rules/toggles1.rule

# Combined rule file
cat rules/best64.rule rules/toggles1.rule rules/leetspeak.rule > combined.rule
hashcat -m 0 hashes.txt wordlist.txt -r combined.rule
```

## Common Pitfalls

- **Using undifferentiated generic lists first** → slow feedback, misses target-specific patterns
- **Ignoring policy** → missing complex passwords (special chars)
- **No deduplication** → wasted work on duplicates
- **Wrong encoding** → hashcat fails on binary data
- **Not monitoring** → letting sessions run too long on dead ends
- **Skipping OSINT** → the most effective wordlist material comes from the target itself

## Tool References

| Tool | When to use |
|------|-------------|
| `hashcat` | Primary cracking engine (CPU/GPU), all attack modes |
| `hashid` | Identify unknown hash types |
| `cewl` | Scrape target website for domain-specific vocabulary |
| `princeprocessor` | PRINCE algorithm: multi-element candidate generation from a base wordlist |
| `statsprocessor` | Markov chain: statistically likely candidates from a training corpus |
| `maskprocessor` | Generate candidates matching a specific mask structure |
