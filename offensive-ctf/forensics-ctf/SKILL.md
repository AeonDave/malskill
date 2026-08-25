---
name: forensics-ctf
description: "Lab/CTF: forensics/stego challenges; disk, memory, PCAP, EVTX/logs, archives, media, firmware-like blobs, evidence recovery."
license: MIT
compatibility: "AgentSkills-compatible agents; local challenge artifacts; authorized training and lab environments."
metadata:
  author: AeonDave
  version: "1.0"
  category: ctf-solving
---

# Forensics CTF

Goal: solve forensics and steganography challenge solving tasks with professional offensive methodology, preserved imported technique coverage, and reproducible evidence.

## When this skill applies

- disk images, memory dumps, PCAPs, event logs, archives, media files, firmware-like blobs, steganography, signals, RF/SDR captures, CAD/G-code, or peripheral captures
- artifact recovery, timeline reconstruction, embedded data extraction, traffic carving, or hidden-message analysis

## Operating model

1. Classify the dominant artifact, primitive, or objective.
2. Load the closest `offensive-techniques` methodology before selecting tools.
3. Load debrandized imported references only for deep technique details.
4. Choose the smallest tool chain that can produce a validation signal.
5. Record the exact proof path and stop once the objective is reproducible.

## Technique integration

Primary methodology to load:

- `forensic-technique`
- `network-technique`
- `reversing-technique`
- `wireless-technique`

Use these as decision engines. This skill adds challenge-oriented triage, time-boxing, and preserved specialized patterns from the imported corpus.

## Tool routing

Prefer these tool families when the corresponding signal appears:

- `volatility3`
- `sleuth-kit`
- `autopsy`
- `zeek`
- `wireshark`
- `tcpdump`
- `binwalk`
- `cyberchef`
- `exiftool`
- `foremost`
- `steghide`
- `zsteg`

Tool syntax belongs in the tool skills. This skill decides when a tool family fits and what output should validate progress.

## Writeup-derived patterns

- Public writeup patterns favor artifact-first triage, shortest reproducible path, and explicit validation signal before pivoting.
- Record failed hypotheses with evidence so an agent does not repeat expensive dead paths.
- Prefer category-specific tools after surface classification instead of running every scanner or brute-forcer by habit.
- End with a replayable proof: recovered secret, local verification, exploit output, decoded artifact, or correlated evidence chain.

## Category-specific quick pivots

- Preserve first: identify format, hash evidence, then choose disk, memory, network, or file workflow.
- For mixed incident bundles, build a UTC timeline and entity graph across identity, process/service, credential-access, lateral-movement, proxy, and DNS/flow records before answering individual questions.
- Use metadata and timeline pivots before deep carving everything.
- For stego and signal tasks, test format-native structures before brute-force extraction.
- For custom malware traffic, separate framing, key derivation, and payload decoding; accept a decode only when it produces a structured message or other artifact-level oracle.

## Quality gates

- No claim without a validation signal: recovered secret, replayed exploit, decoded artifact, reproduced model behavior, or corroborated evidence.
- Do not brute force before representation, constraints, and success oracle are known.
- Keep a pivot ledger: hypothesis, evidence, result, next shortest path.
- Keep challenge/platform/competition names out of notes and generated reports.

## Resources

- [references/disk-memory-and-vm-triage.md](references/disk-memory-and-vm-triage.md) — First-pass disk, VM, container, cloud-storage, coredump, and Volatility memory workflows.
- [references/filesystem-and-archive-recovery.md](references/filesystem-and-archive-recovery.md) — Filesystem and archive recovery: LUKS, XFS/BTRFS/FAT/ext, corrupted ZIP/XZ, nested archives, deleted Git, and known-plaintext ZipCrypto.
- [references/advanced-disk-and-memory.md](references/advanced-disk-and-memory.md) — Advanced disk and memory pivots: partition/ZFS/GPT/APFS/RAID recovery, VMDK sparse parsing, minidumps, malware extraction, and database history reconstruction.
- [references/linux-forensics.md](references/linux-forensics.md) — Linux/browser/container/application artifacts: Docker layers, Chromium secrets, Git history, KeePass, VBA recovery, blockchain traces, and in-memory Python source.
- [references/windows-forensics.md](references/windows-forensics.md) — Windows artifacts: registry hives, LNK/jumplists, SRUM, prefetch, USN journal, event logs, Volatility plugins, clipboard, credentials, and wipe artifacts.
- [references/network-triage.md](references/network-triage.md) — Core packet triage: tcpdump/Wireshark, TLS key logs, HTTP/SMB/WiFi/SAP traffic, uploads, split archives, HID-over-PCAP, and simple covert channels.
- [references/network-covert-and-protocols.md](references/network-covert-and-protocols.md) — Advanced PCAP analysis: timing/flag/DNS/ICMP covert channels, NTLMv2/MS-SNTP/RADIUS cracking, RDP decryption, dnscat2, PDF object recovery, and RC4 shellcode streams.
- [references/usb-and-peripheral-captures.md](references/usb-and-peripheral-captures.md) — USB/Bluetooth peripheral captures: HID mouse, pen, keyboard, LED Morse, arrow navigation, RFCOMM, and framebuffer extraction.
- [references/signal-and-hardware-captures.md](references/signal-and-hardware-captures.md) — Signal and hardware captures: VGA/HDMI/DisplayPort, UART/I2C, SDR/audio decoding, punched cards, logic analyzer CSV, MIDI, and acoustic/LED side channels.
- [references/cad-and-3d-printing.md](references/cad-and-3d-printing.md) — 3D-printing and fabrication artifacts: G-code visualization, Prusa/G-code thumbnail extraction, and CAD-like motion reconstruction.
- [references/steganography.md](references/steganography.md) — General and non-image stego: PDF/SVG/GIF/APNG/terminal/spreadsheet/text/container overlays, nested formats, QR recovery, and PNG chunk manipulation.
- [references/image-stego.md](references/image-stego.md) — Image-specific stego: JPEG DQT/F5/slack, BMP/PNG bitplanes and palettes, pixel permutations, jigsaw/QR reconstruction, thumbnails, and visual filters.
- [references/audio-and-archive-stego.md](references/audio-and-archive-stego.md) — Advanced audio/archive stego: FFT, SSTV, DotCode, DTMF, multi-track subtraction, MIDI, DeepSound, spectrograms, and bidirectional archives.
- [references/video-and-container-stego.md](references/video-and-container-stego.md) — Advanced video/image-container stego: frame accumulation, reversed audio, JPEG XL permutations, cat maps, MJPEG slack, PDF xref channels, ANSI-in-PCAP, and multi-color QR mapping.
