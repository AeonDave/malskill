# malskill

Agent Skills collection for offensive security, red teaming, and malware development — built on the open [AgentSkills](https://agentskills.io) specification.

Each skill is a self-contained folder with a `SKILL.md` that gives any AI coding agent domain-specific knowledge, workflows, and automation for a particular tool or technique. **152 skills** across six top-level categories.

## Categories

### `offensive-tools/` — Tool skills (115 skills)

One skill per offensive tool, organized by attack phase. Each skill teaches the agent how the tool works, its common flags, target scenarios, and operational caveats.

| Subcategory       | Examples |
|------------------|----------|
| `recon/`         | dnsx, ffuf, feroxbuster, gau, waybackurls |
| `windows/`       | bloodhound, certify, crackmapexec, rubeus, seatbelt |
| `network/`       | bettercap, ligolo-ng, masscan, mitmproxy, nmap |
| `web/`           | arjun, commix, corsy, xsstrike, zap |
| `vuln-scanners/` | burpsuite, dalfox, nuclei, nikto, wpscan |
| `forensic/`      | autopsy, ftk-imager, sleuth-kit, volatility3, yara |
| `rev/`           | binaryninja, binwalk, dnspy, frida, ghidra |
| `wireless/`      | aircrack-ng, kismet, lswifi, sparrow-wifi, wifite2 |
| `osint/`         | amass, ghunt, holehe, maigret, phoneinfoga |
| `shells/`        | reverse-ssh, revshells, shellerator, weevely3 |
| `cracking/`      | hashcat, hydra, john |
| `linux/`         | linpeas, linux-exploit-suggester, mimipenguin |
| `exploits/`      | beef, metasploit, searchsploit |

### `offensive-coding/` — Offensive development skills (7 skills)

Skills for malware and red-team development workflows, including BOF development, syscall/evasion patterns, and Windows internals-focused tradecraft.

- **Examples**: `c-bof`, `cpp-bof`, `adaptixc2-dev`, `edr-evasion`, `indirect-syscall`, `stack-spoofing`, `windows-internals`

### `coding/` — Language patterns and testing (19 skills)

Idiomatic code patterns, testing strategies, and performance profiling for the languages most used in offensive tooling.

- **Assembly** — x86-64/ARM64 patterns, offensive asm (syscalls, shellcode, evasion primitives), performance, testing
- **C / C++** — safe patterns, modern idioms, testing with sanitizers and fuzzing
- **Rust** — ownership, API design, testing, performance
- **Go** — idiomatic patterns, testing, performance
- **Python** — patterns, async patterns, testing with pytest
- **Arduino / Sensors** — embedded development for hardware-based projects

### `knowledge/` — Meta-skills and research (8 skills)

Skills that support the workflow itself rather than a specific tool.

| Skill | Purpose |
|---|---|
| `skill-creator` | Create, validate, and package new skills |
| `agent-md-creator` | Bootstrap and maintain `AGENTS.md` files |
| `readme-md-creator` | Create and maintain concise, high-signal README files |
| `self-improvement` | Capture errors, corrections, and patterns across sessions |
| `deep-research-offensive` | File-backed offensive security research with source chaining |
| `deep-research-generic` | General-purpose deep research |
| `cve-search` | Enumerate CVEs and collect public PoC references |
| `malware-analysis` | Static/dynamic malware analysis workflows and IOC extraction |

### `ai/` — AI framework skills (1 skill)

- **`langchain-py`** — production-oriented LangChain Python workflows.

### `hardware/` — Embedded and sensor skills (2 skills)

- **`arduino`**, **`sensors`**

## Quick start

```
# Clone
git clone <repo-url> && cd malskill

# Interactive install (choose skills, destination, output format, and layout)
./install.sh
.\install.ps1

# Install grouped folders while preserving repo categories
./install.sh --skills offensive-tools/windows/mimikatz --format folder --layout group --destination ~/.agents/skills

# Export grouped .zip archives
./install.sh --skills offensive-tools/windows/mimikatz --format zip --layout group --destination ./dist/skills

# Install a skill (copy its folder into your agent's skill directory)
cp -r offensive-tools/windows/mimikatz ~/.agents/skills/

# Or install all offensive-tools skills at once
cp -r offensive-tools/*/* ~/.agents/skills/
```

Skills are plain folders — no build step, no runtime dependency. Copy a skill folder into wherever your agent reads skills from and it activates automatically.

The repository also includes interactive installers at the repo root:

- `install.sh` — Bash installer for selecting skills, destination root, output format, and layout
- `install.ps1` — PowerShell installer with the same workflow on Windows

Supported output formats:

- `folder` — copies the skill directory into the destination root
- `.skill` — creates a distributable `.skill` archive; in this repo it is a standard zip archive that preserves the skill folder name
- `zip` — creates a standard `.zip` archive with the same packaged contents as `.skill`

Supported install layouts:

- `flat` — installs every selected skill directly under the destination root
- `group` — preserves the source-root-relative category structure under the destination root

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
├── offensive-tools/    # 115 tool skills by attack phase
│   ├── recon/
│   ├── windows/
│   ├── web/
│   ├── forensic/
│   └── ...
├── offensive-coding/   # Offensive development workflows (7)
├── coding/             # Language patterns, testing, performance (19)
├── knowledge/          # Meta-skills and research (8)
├── ai/                 # AI framework skills (1)
├── hardware/           # Embedded/sensor skills (2)
└── AGENTS.md           # Repo-level operational guidance
```

Every skill folder contains at minimum a `SKILL.md` with valid YAML frontmatter. Some include `scripts/`, `references/`, or `assets/` for automation, detailed docs, and templates.

## Conventions

- Skill names use lowercase hyphens (`sql-injection`, not `SQLInjection`)
- `SKILL.md` stays under 500 lines — deep content goes to `references/`
- One skill per PR; include validation output
- See [AGENTS.md](AGENTS.md) for full contribution and operational guidelines
