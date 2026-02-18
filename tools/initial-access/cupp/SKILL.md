---
name: cupp
description: "Custom User Password Profiler that generates targeted wordlists from personal information about a target. Use when asked to generate a targeted wordlist, profile a specific person for password guessing, create a custom dictionary from OSINT data, or prepare a personalized password list for brute-force attacks."
license: GPL-3.0
compatibility: "Linux, Windows, macOS. Install: git clone https://github.com/Mebus/cupp + python3 cupp.py. No external dependencies."
metadata:
  author: AeonDave
  version: "1.0"
---

# CUPP

Custom User Password Profiler — generate targeted wordlists from personal OSINT data.

## Quick Start

```bash
# Interactive profile mode
python3 cupp.py -i

# Download predefined wordlists
python3 cupp.py -l

# Show all options
python3 cupp.py -h
```

## Core Flags

| Flag | Description |
|------|-------------|
| `-i` | Interactive — prompts for target info |
| `-w <file>` | Improve existing wordlist with leet-speak + special chars |
| `-l` | Download wordlists from repository |
| `-a` | Parse default usernames from Alecto DB |
| `-v` | Verbose |

## Interactive Profile Fields

When running `-i`, CUPP asks for:

```
Name, surname, nickname
Birthdate (DDMMYYYY)
Partner name, nickname, birthdate
Child name, nickname, birthdate
Pet name
Company name
Keywords (e.g., favorite team, car, city)
Special chars to append? [y/N]
Random numbers to append? [y/N]
Leet mode? [y/N]
```

## What CUPP Generates

From the provided data, CUPP creates permutations:
- Name + birth year: `john1990`, `John1990!`
- Reversed + numbers: `nhoj123`
- Combined names: `johnjane`, `jane&john`
- Leet substitutions: `j0hn`, `p@ssword`
- Upper/lower variants: `JOHN`, `John`
- Special char appends: `john!`, `john@`, `john#`
- Date combinations: `01011990`, `john1990!`

## Common Workflows

```bash
# Build a targeted wordlist interactively
python3 cupp.py -i
# Output: john.txt (or custom name)

# Use the generated list with Hydra
hydra -l john.doe@company.com -P john.txt smtp://mail.company.com

# Use with Hashcat
hashcat -a 0 -m 1000 hashes.txt john.txt

# Augment an existing wordlist with cupp transformations
python3 cupp.py -w existing_list.txt

# Combine with Hashcat rules for more coverage
hashcat -a 0 -m 0 hash.txt john.txt -r /usr/share/hashcat/rules/best64.rule
```

## OSINT Sources for Profiling

- LinkedIn (name, company, job title, dates)
- Facebook / Instagram (relationships, birthdays, pets)
- Twitter/X (interests, nicknames, keywords)
- Company website (employee names, products)
- HaveIBeenPwned (leaked passwords as baseline)

## Resources

| File | When to load |
|------|--------------|
| `references/wordlist-strategy.md` | OSINT gathering workflow, combining with rules, wordlist expansion techniques |
