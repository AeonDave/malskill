---
name: solve-challenge-ctf
description: "Fast challenge-solving router for multi-category CTF tasks. Integrates recon-technique, forensic-technique, reversing-technique, web-exploit-technique, network-technique, wireless-technique, and crypto-technique to classify unknown bundles, remote services, mixed artifacts, and category-ambiguous tasks, then route immediately to the smallest dedicated CTF skill chain. Use for unknown artifacts, partial hints, firmware, RF/SDR, blockchain/Web3, cloud, ICS/OT, hardware captures, AI/ML artifacts, malware samples, or any challenge where speed, precision, and shortest-path solving matter more than explanation."
license: MIT
compatibility: "AgentSkills-compatible agents; local challenge artifacts; authorized training and lab environments."
metadata:
  author: AeonDave
  version: "1.0"
  category: ctf-solving
---

# Solve Challenge CTF

Goal: solve multi-category challenge tasks fast, precisely, and with the shortest reproducible path to objective proof.

## When this skill applies

- unknown challenge bundles, remote services, partial hints, mixed artifacts, or category-ambiguous tasks
- dispatch involving blockchain/Web3, ICS/OT, hardware/embedded, RF/SDR, firmware, logic analyzer traces, industrial PCAPs, or smart-contract frontends
- work requiring first-pass triage and immediate dispatch to the right specialized ctf skill

## Category coverage

- **Web Exploitation** -> route to `offensive-ctf/web-ctf`
- **Binary Exploitation (Pwn)** -> route to `offensive-ctf/pwn-ctf`
- **Reverse Engineering** -> route to `offensive-ctf/reverse-ctf`
- **Cryptography** -> route to `offensive-ctf/crypto-ctf`
- **Forensics** -> route to `offensive-ctf/forensics-ctf`
- **Steganography Toolkit** -> treat as `offensive-ctf/forensics-ctf` first; pivot to `offensive-ctf/misc-ctf` only if evidence shows custom encoding or mixed-puzzle logic
- **Privilege Escalation** -> route by substrate: `offensive-ctf/pwn-ctf` for local binary/kernel primitives, `offensive-ctf/misc-ctf` for host/service puzzle chains, and dedicated domain skill if the target is clearly Windows/Linux post-exploit style
- **OSINT** -> route to `offensive-ctf/osint-ctf`
- **Cloud** -> route to `offensive-ctf/cloud-ctf`
- **AI/ML** -> route to `offensive-ctf/ai-ml-ctf`
- **Malware** -> route to `offensive-ctf/malware-ctf`
- **Hardware / Embedded / RF** -> route to `offensive-ctf/hardware-ctf`
- **ICS / OT / SCADA** -> route to `offensive-ctf/ics-ctf`
- **Blockchain / Web3** -> route to `offensive-ctf/blockchain-ctf`
- **Mixed / ambiguous / puzzle-chain** -> route to `offensive-ctf/misc-ctf`
- **Beginner / unknown category** -> route to `offensive-ctf/beginner-ctf` only long enough to classify dominant category, then exit to dedicated skill
- **Writeup / solve report** -> route to `offensive-ctf/writeup-ctf` only after objective proof is already recovered

## Operating model

1. Classify dominant artifact, protocol, primitive, or objective in one pass.
2. Route to one primary methodology and one primary dedicated `*-ctf` skill only.
3. Choose smallest tool chain that can produce objective proof.
4. Execute shortest viable path first; pivot only on evidence.
5. Stop once objective proof is recovered and reproducible.

## Methodology

Use this loop, but keep it compressed and objective-driven:

1. **Enumerate** -> extract only signal needed to classify artifact, interface, protections, and obvious constraints.
2. **Identify** -> decide dominant category and primary primitive.
3. **Research** -> load one best-fit skill or reference only if it changes next local test.
4. **Attempt** -> run shortest viable solve path against current hypothesis.
5. **Pivot** -> if test fails, use evidence to switch category, primitive, or tool chain.
6. **Document** -> record minimal proof path, recovered objective, and exact validation signal; no writeup expansion unless asked.

## Technique integration

Primary methodology to load:

- `recon-technique`
- `forensic-technique`
- `reversing-technique`
- `crypto-technique`
- `web-exploit-technique`
- `network-technique`
- `wireless-technique`

Use these as decision engines. This skill adds challenge-oriented triage, fast routing, and shortest-path execution discipline.

## Tool routing

Prefer these skill families when the corresponding signal appears:

- `offensive-ctf/web-ctf`
- `offensive-ctf/pwn-ctf`
- `offensive-ctf/reverse-ctf`
- `offensive-ctf/crypto-ctf`
- `offensive-ctf/forensics-ctf`
- `offensive-ctf/misc-ctf`
- `offensive-ctf/osint-ctf`
- `offensive-ctf/malware-ctf`
- `offensive-ctf/ai-ml-ctf`
- `offensive-ctf/cloud-ctf`
- `offensive-ctf/ics-ctf`
- `offensive-ctf/hardware-ctf`
- `offensive-ctf/blockchain-ctf`
- `offensive-ctf/beginner-ctf`
- `offensive-ctf/writeup-ctf`
- `coding/systematic-debugging`
- `knowledge/evidence-before-claims`

Tool syntax belongs in the downstream skill. This skill decides first route, proof condition, and pivot timing.

## Fast-solve rules

- No pedagogy, no hand-holding, no writeup coaching unless user asks.
- No beginner mode, no tutorial mode, no “intended path” speculation unless evidence requires it.
- Enumerate only until route is clear; stop broad discovery once dominant primitive is identified.
- Prefer single decisive test over long exploratory chains.
- Prefer direct artifact interaction over commentary, theory, or generic checklists.
- Keep one active hypothesis; keep one fallback only.
- End at first reproducible objective proof: flag, secret, code-exec, oracle break, decoded artifact, or validated exploit output.

## Category-specific quick pivots

- Use direct triage mode when the user provides concrete artifacts, URLs, endpoints, binaries, captures, or source.
- Classify by artifact and objective, not supplied category label.
- Route to one primary skill; add secondary skill only after evidence-based mismatch.
- Route Solidity/EVM/ABI/RPC/deployed addresses/contract frontends to `offensive-ctf/blockchain-ctf`.
- Route cloud credentials, cloud metadata, buckets, IAM artifacts, signed URLs, serverless code, or cloud control-plane puzzles to `offensive-ctf/cloud-ctf`.
- Route model files, checkpoints, embeddings, classifiers, inference endpoints, prompts, or ML pipelines to `offensive-ctf/ai-ml-ctf`.
- Route suspicious binaries, scripts, configs, implants, loaders, C2 traffic, or unpacking tasks to `offensive-ctf/malware-ctf`.
- Route ICS/SCADA/OT PCAPs, process logs, register dumps, setpoint histories, or isolated lab services to `offensive-ctf/ics-ctf`.
- Route logic analyzer captures, UART/I2C/SPI/CAN/JTAG/SWD traces, firmware/SPI dumps, RF/SDR samples, CAD/G-code, side-channel data, or peripheral captures to `offensive-ctf/hardware-ctf`.
- Keep `offensive-ctf/web-ctf`, `offensive-ctf/forensics-ctf`, and `offensive-ctf/misc-ctf` as secondary pivots only when evidence crosses domains.
- Use `offensive-ctf/beginner-ctf` only as temporary intake for vague prompts; do not stay there once category is clear.
- Use `offensive-ctf/writeup-ctf` only after solve is done and user asks for reproducible reporting.
- When stuck, re-check the category assumption, inspect hidden files/metadata/comments/headers/alternate ports, and simplify to the smallest primitive before expanding the chain.
- Treat multiple recovered secret-like strings as candidates until validated by the intended workflow, corpus uniqueness, source path, or success oracle.

## Quality gates

- No claim without a validation signal: recovered secret, replayed exploit, decoded artifact, reproduced model behavior, or corroborated evidence.
- Do not brute force before representation, constraints, and success oracle are known.
- Keep pivots minimal: failed test -> evidence -> next shortest path.
- Ignore documentation/walkthrough concerns unless user asks for them.
- Prefer clean, low-noise, deterministic solves over exhaustive exploration.

## Resources

- Self-contained in `SKILL.md`.
- Route immediately into dedicated `offensive-ctf/*-ctf` skills once category is clear.
