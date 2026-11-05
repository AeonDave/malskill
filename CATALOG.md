# Malskill Catalog

Category guide with selected skills and tool examples. Browse the category directories for every skill. For project overview, install steps, and maintenance commands see [README.md](README.md).

---

## `offensive-tools/` - Attack tool skills

One skill per tool, organized by attack phase. Each skill covers how the tool works, key flags, target scenarios, output parsing, and OPSEC notes. This area is about **how to use a specific tool** to reach an objective.

| Subcategory | Examples |
|------------|---------|
| `windows/` | bloodhound, certipy, crackmapexec, impacket, mimikatz, rubeus |
| `vuln-scanners/` | burpsuite, dalfox, nuclei, sqlmap, testssl, trivy |
| `recon/` | dnsx, feroxbuster, gobuster, httpx, massdns, shodan |
| `network/` | chisel, masscan, mitmproxy, nmap, responder, wireshark |
| `cryptography/` | rsactftool, sagemath, cyberchef |
| `web/` | commix, corsy, jwt-tool, smuggler, xsstrike, zap |
| `fuzzing/` | aflplusplus, arjun, boofuzz, dotdotpwn, ffuf, restler |
| `osint/` | amass, ghunt, maigret, phoneinfoga, spiderfoot, theharvester |
| `forensic/` | capa, tcpdump, volatility3, yara, zeek |
| `rev/` | binaryninja, frida, gdb, ghidra, radare2, windbg |
| `wireless/` | aircrack-ng, kismet, lswifi, sparrow-wifi, wifite |
| `linux/` | linpeas, linux-persistence, mimipenguin, pwncat, ssh-key-scanner |
| `shells/` | reverse-ssh, revshells, shellerator, weevely3 |
| `cracking/` | hashcat, hydra, john |
| `exploits/` | beef, metasploit, pwntools, searchsploit, foundry-cast, vuln-research |
| `mcp/` | mcpwn, neuromatrix |

## `offensive-coding/` - Offensive development skills

Building offensive tooling from scratch: shellcode, loaders, BOFs, syscall stubs, evasion primitives, and OS internals. For agents doing tool development, not just tool execution.

- **BOF**: `bof-dev/c-bof`, `bof-dev/cpp-bof` - Beacon Object File development workflows.
- **Evasion**: `edr-evasion-dev`, `indirect-syscall-dev`, `sleep-masking-dev`, `stack-spoofing-dev` - technique-level development patterns.
- **Exploit and payload development**: `heap-exploitation-dev`, `rop-development-dev`, `shellcode-dev`, `fsop-dev`, `stack-exploitation-dev`.
- **Internals**: `windows-internals-dev`, `linux-internals-dev` - OS APIs, structures, memory layout, and native PE/ELF startup. Windows [survey interpretation](offensive-coding/windows-internals-dev/references/build-survey.md) includes a numerical CSV cohort and collection limits; use `reversing-technique` for matching-build source/symbol checks and observed OS/runtime behavior.
- **Assembly patterns**: `asm-offensive-patterns` - x86-64/ARM64 patterns tuned for shellcode, syscall stubs, and evasion primitives.
- **Android RE**: `smali-dex-patching` - APK patch/rebuild/resign cycle, smali syntax, common bypass patterns (root, pinning, license, integrity).
- **C2**: `adaptixc2-dev` - framework-specific development.

## `offensive-techniques/` - Methodology and tradecraft skills

About **how to perform a technique in general**, independent of one specific tool: strategy, process, decision flow, and workflow patterns. May mention suitable tools but does **not** become a tool manual.

Example: `offensive-tools/fuzzing/` gives tool-level guides (flags, command patterns), while `offensive-techniques/fuzzing-technique/` gives the methodology (harnessing mindset, corpus strategy, campaign design, validation logic). The two layers are complementary and intentionally separate.

Covers active-directory, binary-exploitation, cicd, cloud-security, container, cracking, crypto, emulation, forensic, fuzzing, game, hardware, ics, llm, mobile, network, oracle-verification, osint, phishing, post-exploit, recon, report-generation, reversing, social-engineering, source-review, vibe-audit, vuln-exploit, vuln-search, web-exploit, and wireless.

## `offensive-roles/` - Supervisor and operator role skills

Mission-focused role skills for supervising and delegating offensive work across precise vertical operators. Roles compose `*-technique` methodology skills with optimized tool skills; they do not replace either layer.

| Skill | Role |
|-------|------|
| `offensive-supervisor-role` | OODA orchestrator. Owns mission, scope, delegation, and strict evidence gates |
| `offensive-recon-role` | Produces scoped target packages, asset inventory, and external attack-surface discovery |
| `offensive-osint-role` | Passive, zero-touch public-source, identity, and leaked-credential research |
| `offensive-web-role` | App-layer operator. API mapping, input tampering, and OWASP-tier vulnerability validation |
| `offensive-cloud-role` | Cloud/SaaS/IAM operator. Principal identities, metadata endpoints, and blob storage |
| `offensive-windows-role` | Windows operator. AD enumeration, access tokens, IPC, and OPSEC-aware local escalation |
| `offensive-linux-role` | Linux operator. Living-off-the-Land execution, host triage, and Unix privilege escalation |
| `offensive-mobile-role` | Mobile operator. APK/IPA static analysis, traffic interception, and Frida instrumentation |
| `offensive-reverse-role` | Reverse engineer. Static and dynamic analysis of binaries, malware, and unknown protocols |
| `offensive-hardware-role` | Hardware operator. Physical device compromise via UART, JTAG, SPI, and embedded extraction |
| `offensive-forensic-role` | Forensic operator. Credentials and timelines from memory dumps, disk images, and PCAP |

## `offensive-ctf/` - Private offensive CTF and lab-solving skills

Challenge-solving workflows for flag-style objectives, puzzle-like artifacts, offline target bundles, and private lab scenarios. Intentionally separate from field methodology in `offensive-techniques/`.

- `technique-ctf` is the category-agnostic entry point: it drives the oracle-driven solve loop and routes to the right domain skill.
- Dedicated `*-ctf` skills cover web, crypto, pwn, reverse, forensics, OSINT, AI/ML, malware, misc, ICS/OT, hardware/embedded, blockchain/Web3, cloud, mobile, game/GamePwn, satellite/space-link, and writeup workflows.
- Pick the `*-ctf` that matches the dominant artifact; load multiple in parallel only when the bundle is genuinely cross-domain.

CTF skills may reference technique and tool skills, but stay optimized for controlled lab objectives rather than real-world engagement tradecraft.

## `offensive-hardware/` - Hardware-focused assessments

On-device compromise, firmware extraction, and signal reversing. Live-hardware attack surface that complements `offensive-techniques/hardware-technique/` methodology.

- **`flipper-zero`** - Sub-GHz, RFID/NFC, iButton, BadUSB, BLE offensive workflows.
- **`jtag-swd`** - JTAG/SWD probe workflows and IDCODE walking.
- **`saleae-logic-2`** - Logic-analyzer capture and protocol export.
- **`spi-flash`** - In-circuit SPI flash dump and reflash.
- **`uart-console`** - UART discovery, baud detection, and root-shell recovery.

## `coding/` - Language patterns and tooling

Idiomatic code patterns, testing strategies, and performance guidance for the languages most used in security tooling. These skills let an agent write, review, and improve code, not just run existing tools.

- **Assembly** - x86-64/ARM64 patterns, syscall stubs, shellcode, evasion primitives, testing.
- **C / C++** - safe patterns, modern idioms, fuzzing, sanitizers.
- **Rust** - ownership, API design, performance, unsafe patterns.
- **Go** - idiomatic patterns, concurrency, performance.
- **Python** - patterns, async, pytest, performance (GIL / free-threading / profilers).
- **Kotlin / Android** - idiomatic Kotlin (null-safety, coroutines, sealed hierarchies, Java interop), Android testing (JUnit/Robolectric/Compose/screenshot/instrumented), Kotlin performance (Macrobenchmark, Baseline Profiles, R8 full mode, Compose recomposition, Perfetto), Android JNI/NDK bridging (16 KB pages, `@FastNative`/`@CriticalNative`, Rust-on-Android).

## `coding-behaviours/` - Engineering discipline skills

Cross-cutting software-engineering stances that shape *how* code work is done, independent of language.

| Skill | Role |
|-------|------|
| [`software-architecture`](coding-behaviours/software-architecture/SKILL.md) | Boundaries, contracts, state, failure recovery, delivery, and simplification for small tools through larger systems |
| [`software-guidelines`](coding-behaviours/software-guidelines/SKILL.md) | Complete, scoped repository edits and their affected consumers |
| [`test-driven-development`](coding-behaviours/test-driven-development/SKILL.md) | Test-first implementation |
| [`testing-reliability`](coding-behaviours/testing-reliability/SKILL.md) | Trustworthy assertions, doubles, fixtures, and mutation-result triage |
| [`systematic-debugging`](coding-behaviours/systematic-debugging/SKILL.md) | Root-cause failure diagnosis |

## `knowledge/` - Research and meta-skills

Skills that support the workflow itself: skill authoring, research helpers, and documentation automation. Load when a task needs them, not as background reading.

| Skill | Role |
|-------|------|
| `skill-creator` | Create, validate, and package new skills |
| `skill-app-creator` | Build skills with executable workflows, consistent deliverables, diagnostics, and optional resumable sessions or UI |
| `agent-md-creator` | Maintain durable agent instructions, project constraints, and task-specific documentation routes |
| `readme-md-creator` | Create clear, destination-aware READMEs for repositories, packages, and document folders |
| `mcp-creator` | Build, audit, integrate, and validate MCP servers, including local host setup |
| `external-feedback-triage` | Evaluate technical feedback, choose evidence-backed dispositions, and complete warranted fixes |
| `deep-research-generic` | Investigate topics and compare options through primary evidence, counterchecks, and gap-driven research |
| `known-problem-hint-research` | Find actionable research leads for stuck, unfamiliar, or unexplained technical problems |

## `knowledge-offensive/` - Assessment research and evidence

Research and development support for authorized security assessments. Use the narrowest skill that answers the current decision, and preserve the distinction between published claims and observations from the assessed environment.

| Skill | Role |
|-------|------|
| `cve-search` | Build bounded vulnerability inventories with source coverage, package/build matching, and explicit unknowns |
| `deep-research-offensive` | Investigate security hypotheses, attack-path prerequisites, mitigation limits, and detection coverage |
| `poc-weaponization` | Review public PoC artifacts, dependency risks, and bounded diagnostic checks |
| `prompt-engineering-patterns` | Design and evaluate prompts for security-artifact extraction, triage, and reporting |
| `agentic-offensive-orchestration` | Coordinate multi-agent security work, job lifecycle, evidence reconciliation, and trust boundaries |

## `harness-dev/` - Agent harness development

Vendor-specific agent and extension authoring. Load the skill matching the host and artifact being created.

| Skill | Role |
|-------|------|
| `claude-agents-creator` | Claude Code subagents and Claude Managed Agents |
| `opencode-agent-creator` | OpenCode agent definitions and delegation |
| `opencode-plugin-creator` | OpenCode plugins, hooks, and custom tools |
| `pi-extension-creator` | Pi extensions, tools, renderers, and packages |

Delete the old malskill skill folders and reinstall the latest version.

## `behaviours/` - Cognitive discipline skills

Cross-cutting behavioral guardrails that shape *how* an agent works. Load these to change the agent's operating stance, not its domain knowledge.

| Skill | Role |
|-------|------|
| `1337` | Concise, methodical red/blue/purple security mode with task knowledge in Markdown or Obsidian |
| `design-before-implementation` | Clarify scope, alternatives, constraints, and success criteria before building |
| `evidence-before-claims` | Gate security claims on reproducible evidence and honest uncertainty |
| `handoff` | Verified session transfers and readable handoffs for colleagues, reviewers, or managers |
| `humanizer` | Write or revise natural prose from drafts or notes, preserving author voice, facts, and evidence limits |
| `hypothesis-driven` | Force explicit hypotheses and falsifiable predictions for hard problems |
| `implementation-planning` | Turn approved designs into executable, verifiable task plans |
| `loop-control-and-pivots` | Retry discipline; pivot dead paths, honest BLOCKED reporting |
| `memory-hygiene` | Retrieve, correct, and verify scoped persistent memory with source provenance |
| `reading-budget-discipline` | Keep the context window lean when reading large data |
| `untrusted-input-hygiene` | Use external data without accepting embedded commands or losing the legitimate task |
| `verification-before-completion` | Require fresh verification before claiming work is done or fixed |

## `ai/` - AI framework skills

Support skills for building or auditing AI/ML pipelines used inside security tooling.

- **`keras`** / **`pytorch`** / **`scikit-learn`** - ML framework patterns for security models and adversarial workflows.
- **`langchain-py`** - Production-oriented LangChain Python workflows.
- **`vec2text`** - Embedding-inversion attack against vector databases.

## `hardware/` - Embedded and maker-platform support

General hardware/embedded platform skills. Load when a security task needs them (build a custom probe, bring up a CAN tap, capture radio traffic).

- **`arduino`**, **`esp32`**, **`raspberry-pi`** - dev-board bring-up and firmware patterns.
- **`can-bus-modules`**, **`gps-modules`**, **`gsm-lte-modules`**, **`lora-modules`**, **`rfid-nfc-modules`** - communication-stack helpers.
- **`sensors`** - common sensor interfacing.
