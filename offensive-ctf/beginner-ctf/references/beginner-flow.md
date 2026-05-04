# Beginner Flow

Use this reference when the user needs orientation before a specialized challenge skill.

## Intake questions to answer internally

- What did the user provide: file, URL, service, source, binary, PCAP, media, model, contract, hardware trace, or clue text?
- What is the safest first inspection that does not change remote or device state?
- What category has the strongest evidence?
- What result would prove the next pivot?

## Minimal first actions by artifact

| Artifact | First action | Success signal | Likely skill |
|---|---|---|---|
| URL or web app | Map pages, auth, parameters, and state-changing actions | endpoint map or reproducible request | `web-ctf` |
| Smart contract address/source | Identify chain, ABI, bytecode, proxy, and success oracle | contract graph and storage targets | `blockchain-ctf` |
| Native binary/service | Run file/checksec/basic strings and reproduce run | architecture and mitigation profile | `pwn-ctf` or `reverse-ctf` |
| Ciphertext/key snippets | Identify primitive, encoding, oracle, and known values | plausible attack class | `crypto-ctf` |
| PCAP/log/archive/image | Identify format, hash, metadata, and conversations | evidence class and timeline start | `forensics-ctf` |
| PLC/SCADA trace | Identify protocol, roles, polling, and write events | process-state map | `ics-ctf` |
| Logic/RF/firmware artifact | Identify capture format, sample rate, bus, or architecture | decoder path | `hardware-ctf` |
| Model/checkpoint/API | Identify model format, task, input/output, and oracle | reproducible prediction path | `ai-ml-ctf` |
| Malware sample | Hash, file type, strings, safe sandbox assumptions | family/config/protocol hypothesis | `malware-ctf` |
| Public clue | Identify entity type and evidence sources | reproducible public-source lead | `osint-ctf` |

## Output examples

### Unknown file bundle

1. **What this looks like:** likely forensics first, because we have files rather than a live exploit target.
2. **Why:** the bundle has archives and media; no binary service or source code is identified yet.
3. **Do next:** identify file types, compute hashes, inspect metadata. If a binary or PCAP appears, pivot accordingly.
4. **If that fails:** switch to `misc-ctf` for encoding or puzzle-layer transforms.
5. **Plain term:** metadata means information stored about a file, such as timestamps, creator tools, dimensions, or embedded comments.

### URL plus source code

1. **What this looks like:** web challenge.
2. **Why:** there is a URL, routes, and state-changing endpoints.
3. **Do next:** map auth boundary, list parameters, replay one harmless request.
4. **If that fails:** if the source includes Solidity/ABI/RPC, switch to `blockchain-ctf`.
5. **Plain term:** auth boundary means where behavior changes between logged-out, user, and admin states.

### Logic analyzer capture

1. **What this looks like:** hardware capture.
2. **Why:** the artifact is timing/edge data, not a normal file format.
3. **Do next:** identify sample rate, channels, idle levels, then test UART/I2C/SPI decoders.
4. **If that fails:** use `forensics-ctf` only if the decoded bytes become a file, image, or archive.
5. **Plain term:** idle level is the voltage state a digital line sits at when no data is being transmitted.
