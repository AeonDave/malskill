---
name: maltego
description: "Visual intelligence and link analysis platform for mapping relationships between people, organizations, domains, IPs, and infrastructure. Use when building entity relationship graphs during recon or threat intelligence gathering."
license: MIT
compatibility: "Java; Linux/macOS/Windows; GUI; maltego.com; Community Edition free"
metadata:
  author: AeonDave
  version: "1.0"
---

# Maltego

Visual OSINT and link analysis — entity graph mapping for people, domains, IPs, orgs.

## Quick Start

1. Download from maltego.com → register for Community Edition (free)
2. Launch Maltego → New Graph
3. Drag entity from palette (e.g., Domain)
4. Type target domain → Run All Transforms

## Key Entity Types

| Entity | Transforms |
|--------|-----------|
| Domain | DNS, WHOIS, subdomains, MX, NS |
| IP Address | Geo, reverse DNS, netblock, Shodan |
| Person | Social accounts, email, phone |
| Organization | People, domains, certificates |
| Email | Breaches, social accounts (Holehe) |
| Website | Tech fingerprint, links |

## Common Transforms

| Transform | Purpose |
|-----------|---------|
| `To DNS Name` | Subdomain enum |
| `To IP Address` | Resolve domain |
| `To Website` | Enumerate web presence |
| `To Email Address` | Find emails |
| `To Social Accounts` | Map social media |
| `Shodan Search` | Enumerate open ports |

## Common Workflows

**Domain recon:**
1. Add Domain entity → target.com
2. Run: `DNS Name – To DNS Name [MX/NS/A]`
3. Run: `Domain – To Website`
4. Run: `IP – To Shodan`

**Person OSINT:**
1. Add Person entity → Full Name
2. Run: `Person – To Email`
3. Run: `Email – To Social Accounts`

## Resources

| File | When to load |
|------|--------------|
| `references/` | Custom transform and API integration notes |
