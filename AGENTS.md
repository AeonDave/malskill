# AGENTS.md — malskill

This repository is a collection of **Agent Skills** for offensive security, following the open [Agent Skills specification](https://agentskills.io/specification).

Skills are organized into top-level sections by type and grow over time:

| Section | Purpose |
|---|---|
| `bof/` | Beacon Object Files — C and C++ BOF development skills |
| `offensive-tools/` | Broad category-level skills (recon, exploitation, lateral movement, etc.) |
| `tools/` | Per-tool skills organized by attack phase — one folder per tool |
| `programming/` | Language and pattern skills for offensive code development |
| `knowledge/` | Meta-skills: skill creation, deep research agents |

**Supported languages**: C, C++, Go, Rust, Nim, Python, x86/x64 Assembly (NASM/MASM).

---

## Project structure

```
malskill/
├── AGENTS.md                    # You are here
├── bof/
│   ├── c-bof/                   # BOF skill for C
│   └── cpp-bof/                 # BOF skill for C++
├── offensive-tools/
│   └── <category>/              # Broad MITRE-phase skills
│       ├── SKILL.md
│       └── references/
├── tools/
│   └── <phase>/                 # Attack phase (recon, initial-access, etc.)
│       └── <tool-name>/         # One skill per tool
│           ├── SKILL.md
│           └── references/
├── programming/                 # Language and pattern skills
└── knowledge/                   # Skill creation and research helpers
    └── skill-creator/
```

### `tools/` phases

Skills under `tools/` follow attack-chain phases:

`recon` · `initial-access` · `lateral-movement` · `execution` · `credential-access` · `persistence` · `defense-evasion` · `exfiltration` · `c2`

Each phase folder contains one sub-folder per tool — add new tools under the appropriate phase.

---

### SKILL.md format (Agent Skills spec)

Every `SKILL.md` must start with YAML frontmatter:

```yaml
---
name: skill-name           # Required — lowercase, hyphens only, must match folder name
description: "..."         # Required — what it does + when to activate it (max 1024 chars)
license: MIT               # Optional
compatibility: "..."       # Optional — OS, deps, install method (max 500 chars)
metadata:
  author: AeonDave
  version: "1.0"
---
```

Use single-line strings for `description` and `compatibility` (avoids YAML parser issues).

The Markdown body contains the actual instructions. Keep `SKILL.md` under **500 lines**; move detailed reference material to `references/`.

### Progressive disclosure

1. **Discovery** (~100 tokens): agents load only `name` + `description` at startup.
2. **Activation** (< 5 000 tokens recommended): full `SKILL.md` body loaded on match.
3. **Resources** (on demand): files in `references/`, `scripts/`, `assets/` loaded only when needed.

---

## Dev environment tips

- **Primary target**: Windows x86/x64. Some skills also target Linux/macOS — check each `SKILL.md`.
- Cross-compile from Linux/WSL with MinGW (`x86_64-w64-mingw32-gcc`) when needed.
- **C/C++**: Visual Studio / `cl.exe` (MSVC) or MinGW-w64.
- **Go**: standard toolchain; `GOOS=windows GOARCH=amd64` for cross-compilation.
- **Rust**: `rustup` with `x86_64-pc-windows-msvc` or `x86_64-pc-windows-gnu`.
- **Nim**: `--os:windows --cpu:amd64` for cross-compilation.
- **Assembly**: NASM or MASM as specified per skill.
- **Python 3**: helper scripts for encoding, shellcode generation, build automation.
- Each skill folder is independent — no shared build system. Always check the skill's `SKILL.md` first.

---

## Writing a new skill

### Tooling

```bash
# Scaffold a new skill directory
python knowledge/skill-creator/scripts/init_skill.py <tool-name> --path tools/<phase> --resources references

# Validate frontmatter and structure
python knowledge/skill-creator/scripts/quick_validate.py tools/<phase>/<tool-name>
```

### Steps

1. Scaffold the directory with `init_skill.py` (creates `SKILL.md` + `references/`).
2. Fill in frontmatter: `name` (must match folder), `description` (include activation triggers), `compatibility`, `metadata`.
3. Write the body: Quick Start → flags/reference table → common workflows → Resources table.
4. Move verbose detail (extended flag lists, deep-dives) to `references/`.
5. Validate with `quick_validate.py` — must show `Skill '<name>' is valid`.
6. Commit.

### Body structure (recommended)

```markdown
# Tool Name

Brief one-line description.

## Quick Start
## Core Flags / Reference Table
## Common Workflows
## Resources

| File | When to load |
|------|--------------|
| `references/foo.md` | ... |
```

---

## Naming conventions

- **Folder names**: lowercase with hyphens — e.g. `evil-winrm`, `ligolo-ng`, `c-bof`.
- **Phase folder names** under `tools/`: `recon`, `initial-access`, `lateral-movement`, `execution`, `credential-access`, `persistence`, `defense-evasion`, `exfiltration`, `c2`.
- **SKILL.md**: always uppercase, always at the skill root.
- **References**: `.md` files only, focused and small to minimize context load.

---

## Validation

```bash
# Validate a single skill
python knowledge/skill-creator/scripts/quick_validate.py tools/<phase>/<tool>

# Validate all skills in a section
Get-ChildItem tools -Recurse -Directory | ForEach-Object {
    python knowledge/skill-creator/scripts/quick_validate.py $_.FullName
}
```

A clean run outputs `Skill '<name>' is valid` for every skill.

---

## Code style

- **C/C++**: prefer clarity over cleverness — these are teaching materials.
- **Go**: `gofmt`, `go vet`. Exported functions need doc comments.
- **Rust**: `clippy` lints. `unsafe` only where strictly necessary, with clear comments.
- **Nim**: follow NEP-1 style guide.
- **Python**: PEP 8, type hints, docstrings.
- **Assembly**: comment every non-obvious instruction.
- All code must compile cleanly with no warnings at the strictest warning level.

---

## Security & ethics disclaimer

This repository is for **authorized security research, red-team exercises, and educational purposes only**. All skills assume the operator has explicit written authorization to test the target environment. The authors are not responsible for misuse.

---

## PR instructions

- Title format: `[tool-name] Short descriptive title`
- Ensure `SKILL.md` frontmatter is valid and `name` matches the folder.
- Run `quick_validate.py` before submitting.
- Include a brief summary of what the skill enables.
- One skill per PR for new additions; group related fixes together.

---

## Useful references

- [Agent Skills Specification](https://agentskills.io/specification)
- [Agent Skills Overview](https://agentskills.io)
- [Example Skills (Anthropic)](https://github.com/anthropics/skills)
- [Agent Skills GitHub](https://github.com/agentskills/agentskills)