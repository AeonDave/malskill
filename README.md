# malskill

Agent Skills collection for offensive security, red teaming, and malware development — built on the open [AgentSkills](https://agentskills.io) specification.

Each skill is a self-contained folder with a `SKILL.md` that gives any AI coding agent domain-specific knowledge, workflows, and automation for a particular tool or technique. **128 skills** across four categories.

## Categories

### `offensive-tools/` — Tool skills (101 skills)

One skill per offensive tool, organized by attack phase. Each skill teaches the agent how the tool works, its common flags, target scenarios, and operational caveats.

| Subcategory | Examples |
|---|---|
| `recon/` | amass, subfinder, ffuf, feroxbuster, httpx, shodan |
| `windows/` | mimikatz, bloodhound, rubeus, crackmapexec, certify, nanodump |
| `network/` | nmap, responder, masscan, wireshark, ligolo-ng, bettercap |
| `c2/` | cobalt-strike, sliver, poshc2, merlin, covenant |
| `web-app/` | sqlmap, xsstrike, commix, tplmap, corsy |
| `vuln-scanners/` | burpsuite, nuclei, nikto, openvas, wpscan |
| `evasion/` | donut, shellter, veil, shellcode-fluctuation |
| `social-engineering/` | gophish, evilginx2, set, modlishka, cupp |
| `cracking/` | hashcat, john, hydra, cain-and-abel |
| `privilege-escalation/` | linpeas, winpeas, privesccheck |
| `re/` | ghidra, radare2, x64dbg, binwalk |
| `shells/` | revshells, weevely3, reverse-ssh, shellerator |
| `osint/` | maltego, sherlock, holehe, phoneinfoga |
| `cloud/` | pacu, scoutsuite, gitleaks, trufflehog |
| `data-exfiltration/` | dnsexfiltrator, cloakify, pyexfil |
| `linux/` | linux-exploit-suggester, mimipenguin |
| `exploits/` | searchsploit, beef |
| `api/` | kiterunner, arjun |
| `wireless/` | (3 tools) |

### `bof/` — Beacon Object Files (2 skills)

Skills for writing, compiling, and debugging BOFs in C and C++ for Cobalt Strike and compatible C2 frameworks. Cover DFR, heap management, injection patterns, and dual-build (BOF+EXE) workflows.

### `programming/` — Language patterns and testing (19 skills)

Idiomatic code patterns, testing strategies, and performance profiling for the languages most used in offensive tooling.

- **Assembly** — x86-64/ARM64 patterns, offensive asm (syscalls, shellcode, evasion primitives), performance, testing
- **C / C++** — safe patterns, modern idioms, testing with sanitizers and fuzzing
- **Rust** — ownership, API design, testing, performance
- **Go** — idiomatic patterns, testing, performance
- **Python** — patterns, async patterns, testing with pytest
- **Arduino / Sensors** — embedded development for hardware-based projects

### `knowledge/` — Meta-skills and research (6 skills)

Skills that support the workflow itself rather than a specific tool.

| Skill | Purpose |
|---|---|
| `skill-creator` | Create, validate, and package new skills |
| `agent-md-creator` | Bootstrap and maintain `AGENTS.md` files |
| `self-improvement` | Capture errors, corrections, and patterns across sessions |
| `deep-research-offensive` | File-backed offensive security research with source chaining |
| `deep-research-generic` | General-purpose deep research |
| `cve-search` | Enumerate CVEs and collect public PoC references |

## Quick start

```
# Clone
git clone <repo-url> && cd malskill

# Install a skill (copy its folder into your agent's skill directory)
cp -r offensive-tools/windows/mimikatz ~/.agents/skills/

# Or install all offensive-tools skills at once
cp -r offensive-tools/*/* ~/.agents/skills/
```

Skills are plain folders — no build step, no runtime dependency. Copy a skill folder into wherever your agent reads skills from and it activates automatically.

## Validation

```bash
# Validate a single skill
python knowledge/skill-creator/scripts/quick_validate.py offensive-tools/recon/nmap

# Validate an entire section
Get-ChildItem offensive-tools/recon -Directory | ForEach-Object {
  python knowledge/skill-creator/scripts/quick_validate.py $_.FullName
}

# Package a skill into a .skill archive
python knowledge/skill-creator/scripts/package_skill.py offensive-tools/windows/mimikatz
```

## Structure

```
malskill/
├── offensive-tools/    # 101 tool skills by attack phase
│   ├── recon/
│   ├── windows/
│   ├── c2/
│   └── ...
├── bof/                # BOF development (C, C++)
├── programming/        # Language patterns, testing, performance
├── knowledge/          # Meta-skills, research, CVE search
└── AGENTS.md           # Repo-level operational guidance
```

Every skill folder contains at minimum a `SKILL.md` with valid YAML frontmatter. Some include `scripts/`, `references/`, or `assets/` for automation, detailed docs, and templates.

## Conventions

- Skill names use lowercase hyphens (`sql-injection`, not `SQLInjection`)
- `SKILL.md` stays under 500 lines — deep content goes to `references/`
- One skill per PR; include validation output
- See [AGENTS.md](AGENTS.md) for full contribution and operational guidelines
