---
name: technique-ctf
description: "Lab/CTF: general challenge-solving methodology across every category; artifact triage, spec/protocol identification, oracle-driven iteration from target error messages, minimal-matrix brute forcing, harness building with pwntools, parallelizing independent challenges/variants with subagents, and safe flag extraction, verification, and submission. Use to plan or drive any flag-style challenge, to route to the right domain *-ctf skill, or whenever a remote service replies with parseable errors that can steer the next input."
license: MIT
compatibility: "AgentSkills-compatible agents; local artifacts; authorized isolated lab environments."
metadata:
  author: AeonDave
  version: "1.0"
  category: ctf-solving
---

# Technique CTF

Solve any flag-style challenge with a category-agnostic loop: triage the artifact, identify the exact spec or format, drive the smallest correct interaction, and let the target's own responses steer each next input — then verify and submit the flag.

## When this skill applies

- Any controlled lab/CTF objective: a remote service, a downloadable bundle, a puzzle artifact, or a skeleton client to complete.
- Before reaching for a domain skill, to decide *which* `*-ctf` skill(s) to load and how to structure the attack.
- Whenever a target emits parseable feedback — validation errors, diffs, status codes, timing, or partial output — that can be used as an oracle.
- When several independent challenges (or independent parameter variants of one challenge) can be worked in parallel.

## Operating model

1. **Triage.** Inventory what you were given: hash and list files, read the brief literally, note the target `host:port`, the stated flag format, and every concrete value (IDs, keys, payload strings, ports). Identify the dominant artifact class — it selects the domain skill.
2. **Identify the spec.** Name the exact format/protocol/algorithm before writing an exploit. Match magic bytes, headers, wording, and cited standards. The brief usually states the spec and the exact expected input — build to that, not to placeholder values in any example code.
3. **Minimal correct interaction.** Send the smallest well-formed unit and observe. Probe liveness both ways: some services greet with a banner, others reply only after you send — send-then-recv, do not hang waiting for a banner.
4. **Read the oracle.** Treat every response as signal. Precise validators say exactly what is wrong (`expected X but got Y`, `invalid state`, a stack trace, a length, a 401 vs 403, a timing delta). Walk the error chain field by field; each rejection names the next thing to fix. This beats guessing and beats blind brute force.
5. **Iterate / brute the *smallest* unknown.** When one field is genuinely ambiguous after the oracle is exhausted, brute only that minimal space (e.g. a counter × a type bit), reconnecting/resetting state per attempt. Never brute a large space blindly when a signal exists.
6. **Extract and verify.** Pull the flag with a format regex, sanity-check it, and only then submit. If a submission API exists, use it; confirm acceptance. Do not paste flags into external services.

## Cognitive stance (negative constraints)

- **Evidence first.** Do not claim a solve, a working exploit, or a root cause without a reproduced observation. If a step was skipped or failed, say so.
- **Oracle over guessing.** Exhaust the target's feedback before brute force; exhaust a small brute before a large one.
- **Minimal action.** Prefer offline decode of a supplied artifact over live interaction; prefer one crafted request over a scanner. Loud, broad tooling wastes time and corrupts stateful targets.
- **No rabbit holes.** Time-box a dead end. If the oracle stops yielding, re-triage: wrong layer, wrong spec, or an assumption to test — not more of the same input.
- **Verify the flag.** A plausible-looking string is not a flag until it matches the stated format and (if possible) is accepted.

## Category routing

Load the domain skill that matches the dominant artifact; load more than one only for genuinely cross-domain bundles.

| Cue | Load |
|---|---|
| Web app, HTTP, cookies, SSRF/SQLi/XSS | `web-ctf` |
| Ciphers, RSA/ECC, hashes, custom crypto | `crypto-ctf` |
| Binary exploitation, heap, shellcode, ROP | `pwn-ctf` |
| Disassembly, unpacking, license/keygen | `reverse-ctf` |
| Disk/memory images, PCAP, stego, carving | `forensics-ctf` |
| Spacecraft, CCSDS, telemetry/telecommand, TLE | `satellite-ctf` |
| Modbus/S7/BACnet, PLC, SCADA, OT protocols | `ics-ctf` |
| Logic traces, UART/SPI/JTAG, firmware, RF/SDR | `hardware-ctf` |
| APK/IPA, mobile traffic, Frida | `mobile-ctf` |
| Smart contracts, EVM, on-chain | `blockchain-ctf` |
| Prompt injection, model files, embeddings | `ai-ml-ctf` |
| Malware sample triage in a lab | `malware-ctf` |
| Unity/IL2CPP, native game binaries, saves, GamePwn | `game-ctf` |
| Subdomains, people, leaked creds, public sources | `osint-ctf` |
| Jails (bash/py), encodings, DNS, misc puzzles | `misc-ctf` |
| Cloud/IAM, metadata, buckets | `cloud-ctf` |
| Writing up the solve | `writeup-ctf` |

## Parallelization

Independent work should run concurrently, not serially.

- Dispatch one subagent per independent challenge, or per independent variant of a stubborn challenge (different spec guess, different parameter branch). Give each the concrete target, the exact spec, and any reusable code so it does not rediscover the basics.
- Split a single challenge only along a true seam (recon vs. exploit dev, or independent sub-flags) with no shared mutable state.
- Keep results, not transcripts: each subagent returns the flag and the minimal working method; you retain the conclusion.

## Tool routing

- **Remote loop:** `pwntools` (`remote`, `recvuntil`, `sendline`), or raw `socket` for exact byte control. Script every interaction — never solve a stateful service by hand.
- **Transforms:** CyberChef, `xxd`/`hexdump`, `base64`/`base32`, `jq`, Python `struct`/`construct` for framed formats, `binwalk`/`file`/`strings` for unknown blobs.
- **Recon of the artifact, not the network:** read the files first. Reserve scanners for when the brief points at a broad service surface, and keep them scoped.
- **Reproducibility:** keep a single script per challenge that goes from connect to flag, so a fix is one edit and a re-run.

## Flag discipline

- Match the stated format; default regexes: `HTB\{[^}]+\}`, `flag\{[^}]+\}`, `[A-Za-z0-9_]+\{[^}]+\}`, or the exact prefix the platform uses.
- Verify before submitting; if the platform has a submit API/tool, use it and confirm the acceptance message.
- Do not exfiltrate flags, source, or target data to external/third-party services; keep everything in the lab context.

## Quick pivots

- **Timeout on connect:** the service wants input first — send the minimal frame/request, then read.
- **"Invalid" on a unit you believe is valid:** an encoding assumption is wrong (raw byte vs. ASCII string, endianness, off-by-one length, CRC seed). Try the alternate encoding before rebuilding everything.
- **Errors reference a counter/sequence/state:** the target is a state machine — advance every counter it tracks in lockstep; reconnect to reset when you lose sync.
- **Same error regardless of input:** you are at the wrong layer or failing an earlier gate (auth, framing, checksum) before your payload is even parsed.
- **Big search space:** find the oracle that collapses it (an error that leaks length/position, a timing side channel, a partial match) instead of brute forcing.
- **Stuck:** re-read the brief for an unused concrete value; it is almost always load-bearing.

## Resources

- [references/harness-and-oracle-patterns.md](references/harness-and-oracle-patterns.md) — reusable pwntools/socket remote-loop templates, an oracle-error-walking pattern, a minimal-matrix brute template that reconnects per attempt, flag-regex helpers, and a subagent parallelization pattern for independent challenges. Load when building the solve script for a remote or stateful challenge.
