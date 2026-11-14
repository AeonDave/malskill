# Malskill Catalog

Category guide with selected skills and tool examples. Browse the category directories for every skill. For project overview, install steps, and maintenance commands see [README.md](README.md).

---

## `offensive-tools/` - Attack tool skills

One skill per tool, organized by attack phase: version-aware setup, useful commands, output interpretation, and failure modes. Check the installed release before using version-specific flags; retain legacy tools only for a distinct supported use.

| Subcategory | Examples |
|------------|---------|
| `windows/` | bloodhound, certipy, enum4linux-ng, impacket, ldaprelayscan, netexec, sharphound |
| `vuln-scanners/` | burpsuite, dalfox, nuclei, osv-scanner, sqlmap, titus, trivy |
| `recon/` | dnsx, feroxbuster, gobuster, httpx, massdns, shodan |
| `network/` | chisel, masscan, mitmproxy, nmap, responder, wireshark |
| `cryptography/` | rsactftool, sagemath, cyberchef |
| `web/` | commix, jwt-tool, waymore, xsstrike, zap |
| `fuzzing/` | aflplusplus, arjun, boofuzz, dotdotpwn, ffuf, restler |
| `osint/` | amass, ghunt, maigret, phoneinfoga, spiderfoot, theharvester |
| `forensic/` | capa, hayabusa, tcpdump, volatility3, yara, zeek |
| `rev/` | binaryninja, frida, gdb, ghidra, radare2, windbg |
| `wireless/` | aircrack-ng, kismet, lswifi, sparrow-wifi, wifite |
| `linux/` | linpeas, linux-persistence, mimipenguin, pspy, pwncat |
| `shells/` | reverse-ssh, revshells, shellerator, weevely3 |
| `cracking/` | hashcat, hydra, john |
| `exploits/` | beef, metasploit, pwntools, searchsploit, foundry-cast |
| `mcp/` | mcpwn, neuromatrix |

## `offensive-coding/` - Offensive development skills

Building offensive tooling from scratch: shellcode, loaders, BOFs, syscall stubs, evasion primitives, and OS internals. For agents doing tool development, not just tool execution.

- **BOF**: [bof-dev](offensive-coding/bof-dev/SKILL.md) - Beacon Object File development workflows.
- **Evasion**: `edr-evasion-dev`, `indirect-syscall-dev`, `sleep-masking-dev`, `stack-spoofing-dev` - technique-level development patterns.
- **Elevation**: `uac-evasion-dev` - in-tool UAC bypass implementation (auto-elevate mechanics, bypass families, BOF integrations, UAC→admin→SYSTEM chain).
- **Exploit and payload development**: `heap-exploitation-dev`, `rop-development-dev`, `shellcode-dev`, `fsop-dev`, `stack-exploitation-dev`.
- **Internals**: `windows-internals-dev`, `linux-internals-dev` - OS APIs, structures, memory layout, and native PE/ELF startup. Windows [survey interpretation](offensive-coding/windows-internals-dev/references/build-survey.md) includes a numerical CSV cohort and collection limits; use `reversing-technique` for matching-build source/symbol checks and observed OS/runtime behavior.
- **Assembly patterns**: `asm-offensive-patterns` - x86-64/ARM64 patterns tuned for shellcode, syscall stubs, and evasion primitives.
- **Android RE**: `smali-dex-patching` - APK patch/rebuild/resign cycle, smali syntax, common bypass patterns (root, pinning, license, integrity).
- **C2**: `adaptixc2-dev` - framework-specific development.

## `offensive-techniques/` - Methodology and tradecraft skills

About **how to perform a technique in general**, independent of one specific tool: strategy, process, decision flow, and workflow patterns. May mention suitable tools but does **not** become a tool manual.

Example: `offensive-tools/fuzzing/` gives tool-level guides (flags, command patterns), while `offensive-techniques/fuzzing-technique/` gives the methodology (harnessing mindset, corpus strategy, campaign design, validation logic). The two layers are complementary and intentionally separate.

Covers active-directory, binary-exploitation, cicd, cloud-security, container, cracking, crypto, emulation, forensic, fuzzing, game, hardware, ics, llm, mobile, network, oracle-verification, osint, phishing, post-exploit, recon, report-generation, reversing, social-engineering, source-review, vibe-audit, vuln-exploit, web-exploit, and wireless.

For vulnerability discovery, assessment coverage, and scanner-finding validation, use [vuln-research](knowledge-offensive/vuln-research/SKILL.md) in `knowledge-offensive/`.

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
| [`dependency-discipline`](coding-behaviours/dependency-discipline/SKILL.md) | Evaluate, pin, hash-verify, and audit dependencies at adoption/upgrade time; incident response |
| [`secure-tooling-implementation`](coding-behaviours/secure-tooling-implementation/SKILL.md) | Write offensive tooling that is not itself the vulnerability: trust boundaries, subprocess/path/TLS/secrets discipline |

## `knowledge/` - Research and meta-skills

Skills that support the workflow itself: skill authoring, research helpers, agent coordination, and documentation automation. Load when a task needs them, not as background reading.

| Skill | Role |
|-------|------|
| `skill-creator` | Create, validate, and package new skills |
| `skill-app-creator` | Build skills with executable workflows, consistent deliverables, diagnostics, and optional resumable sessions or UI |
| [`orchestration`](knowledge/orchestration/SKILL.md) | General delegation: choose workers, models and effort, schedule dependencies, and integrate results; optional Claude Code reference |
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
| [`vuln-research`](knowledge-offensive/vuln-research/SKILL.md) | Plan assessment coverage, validate scanner and bug-bounty leads, and investigate root causes, patches, and variants |
| `deep-research-offensive` | Investigate security hypotheses, attack-path prerequisites, mitigation limits, and detection coverage |
| `poc-weaponization` | Review public or generated PoCs, dependency risks, diagnostic checks, and replay evidence |
| `prompt-engineering-patterns` | Design and evaluate prompts for security-artifact extraction, triage, and reporting |
| [`offensive-orchestration`](knowledge-offensive/offensive-orchestration/SKILL.md) | Route security questions to technical skills, coordinate target/session ownership, and reconcile evidence across workers |
| [`threat-modeling`](knowledge-offensive/threat-modeling/SKILL.md) | Decompose a target (DFD/STRIDE/attack trees), prioritize threats, map to ATT&CK to feed the assessment plan |
| [`adversary-emulation-planning`](knowledge-offensive/adversary-emulation-planning/SKILL.md) | Build a CTI-driven emulation plan: extract TTPs, map to ATT&CK, prioritize against the target stack, structure phased procedures with detection expectations |

## `harness-dev/` - Agent harness development

Vendor-specific agent and extension authoring. Load the skill matching the host and artifact being created.

| Skill | Role |
|-------|------|
| `claude-agents-creator` | Claude Code subagents and Claude Managed Agents |
| `opencode-agent-creator` | OpenCode agent definitions and delegation |
| `opencode-plugin-creator` | OpenCode plugins, hooks, and custom tools |
| `pi-extension-creator` | Pi extensions, tools, renderers, and packages |

## `behaviours/` - Cognitive discipline skills

Cross-cutting behavioral guardrails that shape *how* an agent works. Load these to change the agent's operating stance, not its domain knowledge.

| Skill | Role |
|-------|------|
| `design-before-implementation` | Clarify scope, alternatives, constraints, and success criteria before building |
| `evidence-before-claims` | Gate security claims on reproducible evidence and honest uncertainty |
| `handoff` | Verified session transfers and readable handoffs for colleagues, reviewers, or managers |
| `humanizer` | Write or revise natural prose from drafts or notes, preserving author voice, facts, and evidence limits |
| `hypothesis-driven` | Force explicit hypotheses and falsifiable predictions for hard problems |
| `implementation-planning` | Turn approved designs into executable, verifiable task plans |
| `irreversible-action-gate` | One-line impact/rollback/scope brief before destructive operations, then execute the operator's call; target-safety ordering |
| `loop-control-and-pivots` | Retry discipline; pivot dead paths, honest BLOCKED reporting |
| `memory-hygiene` | Retrieve, correct, and verify scoped persistent memory with source provenance |
| `offensive-operator-mode` | Sustained, evidence-driven offensive-security operating posture (elite/1337); task knowledge in Markdown or Obsidian |
| `pushback-over-agreement` | Disagree with evidence instead of yes-manning; hold correct refusals under pressure, concede fast when wrong |
| `reading-budget-discipline` | Keep the context window lean when reading large data |
| `rules-of-engagement` | Know the engagement contract (authorization, targets, techniques, window, data handling) and surface it during work; the operator owns the decisions |
| `scope-discipline` | Stay on the requested task mid-flight: ledger drive-by findings, re-plan grown requests, state the boundary |
| `uncertainty-calibration` | State confidence in proportion to evidence; label verified vs inferred vs guessed; test or escalate instead of asserting |
| `untrusted-input-hygiene` | Use external data without accepting embedded commands or losing the legitimate task |
| `verification-before-completion` | Require fresh verification before claiming work is done or fixed |

## `ai/` - AI framework skills

Support skills for building or auditing AI/ML pipelines used inside security tooling.

- **`keras`** / **`pytorch`** / **`scikit-learn`** / **[`transformers`](ai/transformers/SKILL.md)** - ML framework loading, inspection, and safe-deserialization patterns for model artifacts.
- **`langchain-py`** - Production-oriented LangChain Python workflows.
- **[`adversarial-robustness-toolbox`](ai/adversarial-robustness-toolbox/SKILL.md)** - ART estimator adapters, bounded adversarial experiments, and evidence-based evaluation for ML security assessments.
- **`vec2text`** - Embedding-inversion attack against vector databases.
- **Artifact security**: [`model-scanning`](ai/model-scanning/SKILL.md) - scan untrusted pickle/PyTorch/Keras/ONNX/GGUF model files (picklescan/fickling/modelscan/modelaudit) before loading; a clean scan is not proof of safety.
- **Model adaptation & modification**: [`model-finetuning`](ai/model-finetuning/SKILL.md) (LoRA/QLoRA SFT + preference optimization DPO/ORPO/KTO/GRPO), [`abliteration`](ai/abliteration/SKILL.md) (training-free refusal/behavior editing via residual-direction ablation), and [`model-merging`](ai/model-merging/SKILL.md) (weight-space merges: SLERP/TIES/DARE/task-arithmetic/MoE).
- **Interpretability**: [`interpretability`](ai/interpretability/SKILL.md) - explain model decisions and locate behaviors: SHAP/LIME/Captum attribution (ML/DL) and TransformerLens/SAE mechanistic analysis (LLM).
- **LLM red-teaming stack**: [`garak`](ai/garak/SKILL.md) (probe catalog scanner), [`pyrit`](ai/pyrit/SKILL.md) (adaptive multi-turn orchestration), [`promptfoo`](ai/promptfoo/SKILL.md) (app-level eval + CI red-team gate).
- **LLM lab infrastructure**: [`ollama`](ai/ollama/SKILL.md) (local runtime, airgapped targets), [`litellm`](ai/litellm/SKILL.md) (provider gateway; includes the 2026-10 supply-chain incident notes).

## `hardware/` - Embedded and maker-platform support

General hardware/embedded platform skills. Load when a security task needs them (build a custom probe, bring up a CAN tap, capture radio traffic).

- **`arduino`**, **`esp32`**, **`raspberry-pi`** - dev-board bring-up and firmware patterns.
- **`can-bus-modules`**, **`gps-modules`**, **`gsm-lte-modules`**, **`lora-modules`**, **`rfid-nfc-modules`** - communication-stack helpers.
- **`sensors`** - common sensor interfacing.
