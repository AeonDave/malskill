---
name: beginner-ctf
description: "Beginner-friendly challenge-solving entrypoint for users who do not know which CTF category or skill to use. Use when the prompt contains a vague challenge description, unknown artifact, URL, service, source bundle, binary, PCAP, image, model, smart contract, hardware trace, or the user asks what to do first. Explains category choice in plain language, chooses the smallest next 1-3 actions, and then hands off to the correct dedicated ctf-solving skill."
license: MIT
compatibility: "AgentSkills-compatible agents; local challenge artifacts; authorized training and lab environments."
metadata:
  author: AeonDave
  version: "1.0"
  category: ctf-solving
---

# Beginner CTF

Help a beginner get unstuck without forcing them to know the right category, jargon, or tool chain first.

## When this skill applies

- The user has a challenge bundle, URL, service, attachment, binary, PCAP, image, model, smart contract, firmware, hardware trace, or only a vague prompt and does not know where to begin.
- The user asks for the first step, category identification, simple explanation, or a minimal plan.
- The task is still in triage; once the dominant category is clear, hand off to the dedicated skill.

## Operating model

1. Identify what the user provided: file, URL, host/port, source code, binary, network capture, media, model, contract, hardware trace, or text clue.
2. Explain the likely category in one plain-language sentence.
3. Pick one primary `ctf-solving/*-ctf` skill and at most one backup pivot.
4. Give only the next 1-3 actions, each with what it is checking and what result would prove progress.
5. Avoid tool spam. Use the smallest safe inspection before scanners, brute force, fuzzing, exploitation, or writes.
6. Once evidence points to a category, switch to that dedicated skill for deep work.

## Category handoff map

- Unknown or mixed bundle: `solve-challenge-ctf`.
- Web app, API, auth, browser, upload, SSRF, SQLi, XSS, SSTI, deserialization: `web-ctf`.
- Solidity, EVM, ABI, RPC, smart contract, transaction trace, on-chain state: `blockchain-ctf`.
- Binary exploitation, remote native service, memory corruption, heap, ROP, shellcode: `pwn-ctf`.
- Reverse engineering, validation binary, bytecode, custom VM, obfuscation, firmware logic: `reverse-ctf`.
- Crypto, ciphertext, key material, oracle, signature, PRNG, RSA/ECC/lattice: `crypto-ctf`.
- Disk, memory, PCAP, stego, archive, image/audio/video hidden data: `forensics-ctf`.
- ICS, SCADA, PLC/HMI/RTU, Modbus, DNP3, BACnet, S7comm, OPC UA, MQTT, process state: `ics-ctf`.
- Hardware, UART/I2C/SPI/CAN/JTAG/SWD, RF/SDR, firmware dump, logic analyzer, side-channel, CAD/G-code: `hardware-ctf`.
- AI/ML model, checkpoint, embedding, classifier, LLM app, prompt injection, model extraction: `ai-ml-ctf`.
- Malware sample, C2 protocol, packed PE/.NET/ELF, shellcode, config extraction: `malware-ctf`.
- OSINT, usernames, domains, geolocation, social/media clues, public records: `osint-ctf`.
- Encodings, jails, esolangs, games, DNS oddities, RF puzzle layer, Linux privesc puzzle: `misc-ctf`.
- Final explanation or reproducible report: `writeup-ctf`.

## Beginner-friendly output

Use this shape while triaging:

1. **What this looks like:** category guess in simple words.
2. **Why:** 1-3 evidence bullets from the artifact or prompt.
3. **Do next:** 1-3 concrete actions, each with the expected signal.
4. **If that fails:** the next likely pivot skill.
5. **Plain term:** define one important term if the user may not know it.

## Guardrails

- Do not overwhelm the user with a full tool list before the category is known.
- Do not assume a challenge category from the label alone; verify from artifact evidence.
- Do not brute force, scan aggressively, fuzz, or exploit before representation and success oracle are known.
- Keep explanations short, concrete, and friendly; beginners need orientation more than jargon.

## Resources

- `references/beginner-flow.md` — examples of beginner-friendly triage outputs and category decision cues.
