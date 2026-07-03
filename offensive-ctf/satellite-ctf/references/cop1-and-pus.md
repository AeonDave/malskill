# COP-1 Sequence Control and ECSS PUS

Load for sequence-controlled (AD) uplink and for PUS application-layer command/report grammar.

## Contents

- COP-1 roles and variables
- FARM-1 acceptance logic (the CTF-relevant part)
- AD / BD / BC frame types
- BC directives: Unlock and Set V(R)
- CLCW bit map
- ECSS PUS packet structure
- PUS service catalog
- PUS CRC

## COP-1 roles and variables (CCSDS 232.1-B)

COP-1 guarantees ordered, gap-free delivery of telecommand frames over a virtual channel.

- **FOP-1** — Frame Operation Procedure, the *sending* (ground) side. Holds `V(S)` = sequence number to assign to the next AD frame.
- **FARM-1** — Frame Acceptance and Reporting Mechanism, the *receiving* (spacecraft) side. Holds `V(R)` = the `N(S)` it expects next.
- `N(S)` — Frame Sequence Number in the TC transfer frame primary header.
- `N(R)` — Next Expected Frame Sequence Number, reported back to ground inside the **CLCW** (in downlink telemetry OCF). `N(R) == V(R)`.

## FARM-1 acceptance logic

For each received **AD** frame on a virtual channel, FARM compares `N(S)` against `V(R)`:

- `N(S) == V(R)` → **accept** the frame, deliver its data, then `V(R) = (V(R)+1) mod 256`.
- `N(S) < V(R)` (within the negative window) → **discard** as a duplicate; no state change.
- `N(S) > V(R)` (ahead) → **discard**; after the sliding window is exceeded, FARM enters **Lockout** and rejects everything until unlocked.

CTF impact: `V(R)` starts at 0. Your first AD frame must carry `N(S)=0`, the second `N(S)=1`, and so on. If the service also runs an application-level counter in the payload, that counter is independent and must be advanced in step too — the server's error messages tell you each expected value. BD frames bypass this check entirely (use when order does not matter); BC frames carry the recovery directives.

## AD / BD / BC frame types

Set by the Bypass Flag and Control Command Flag in the TC primary header:

| Bypass | Ctrl | Type | Meaning |
|---|---|---|---|
| 0 | 0 | **AD** | Sequence-Controlled data; FARM checks `N(S)`. Default for reliable command. |
| 1 | 0 | **BD** | Expedited data; FARM acceptance bypassed. |
| 1 | 1 | **BC** | Control command (Unlock / Set V(R)); FARM bypassed. |
| 0 | 1 | — | Reserved. |

## BC directives (data field of a BC frame)

- **Unlock** — single octet `0x00`. Clears the Lockout flag and resumes AD acceptance.
- **Set V(R)** — three octets `0x82 0x00 <VR>`, where `<VR>` is the value FARM should load into `V(R)` (i.e. the `N(S)` of the next AD frame you will send). Use to resynchronize after a sequence error or lockout.

Both are sent inside a BC frame (bypass=1, ctrl=1) with a normal primary header and FECF. See `bc_set_vr()` in `ccsds-frame-construction.md`.

**Security note (SDLS-relevant):** SDLS deliberately does **not** protect BC directives or the CLCW in the TM OCF. Even against a fully SDLS-secured link, an attacker who can inject BC frames can flip the FARM into lockout (or reset `V(R)`) and disrupt commanding without breaking crypto. Load `sdls-and-ground-cves.md` for the complete list of SDLS gaps.

## CLCW bit map (32-bit OCF in downlink TM)

| Field | Bits | Notes |
|---|---|---|
| Control Word Type | 1 | `0` for CLCW |
| CLCW Version Number | 2 | `00` |
| Status Field | 3 | mission-defined |
| COP in Effect | 2 | `01` for COP-1 |
| Virtual Channel ID | 6 | matches the VC |
| Reserved Spare | 2 | `00` |
| No RF Available | 1 | flag |
| No Bit Lock | 1 | flag |
| Lockout | 1 | **1 = FARM locked out** — send BC Unlock |
| Wait | 1 | receiver out of resources |
| Retransmit | 1 | sequence error detected; FOP must retransmit |
| FARM-B Counter | 2 | low bits of the FARM-B counter |
| Reserved Spare | 1 | `0` |
| Report Value N(R) | 8 | **= V(R)**, the next expected `N(S)` |

Read the CLCW from the TM OCF to learn the spacecraft's current `V(R)` and whether it is locked out or requesting retransmit.

## ECSS PUS packet structure (ECSS-E-ST-70-41C)

PUS packets are CCSDS space packets (`sechdr=1`) carrying a standardized secondary header. Requests go up as TC, reports come down as TM. Denote a request `TC[service,subservice]` and a report `TM[service,subservice]`.

- **TC secondary header (data field header):** PUS version(4) + ack flags(4) + **service type(8)** + **service subtype(8)** + source ID(n). Then the application data, then the packet CRC.
- **TM secondary header:** PUS version(4) + spare(4) + **service type(8)** + **service subtype(8)** + message-type-counter + destination ID + time. Then the report data, then CRC.
- Data types used in fields: boolean, enumerated, (un)signed integer, real, bit/octet/character string, absolute/relative time, deduced.

## PUS service catalog (standard service types)

| ST | Service | Common subservices |
|---|---|---|
| 1 | Request verification | `TM[1,1/2]` accept ok/fail, `TM[1,7/8]` complete ok/fail |
| 2 | Device access | raw device command/read |
| 3 | Housekeeping & diagnostics | `TC[3,1]` define HK, `TM[3,25]` HK report |
| 4 | Parameter statistics | |
| 5 | Event reporting | `TM[5,1..4]` info→high-severity events |
| 6 | Memory management | `TC[6,2]` load, `TC[6,5]` dump, `TM[6,6]` dump report |
| 8 | Function management | `TC[8,1]` perform function |
| 9 | Time management | time reports / rate |
| 11 | Time-based scheduling | insert/delete time-tagged commands |
| 12 | On-board monitoring | limit checks |
| 13 | Large packet transfer | up/downlink segmentation |
| 14 | Real-time forwarding control | enable/disable TM forwarding |
| 15 | On-board storage & retrieval | packet stores, downlink |
| 17 | **Test** | `TC[17,1]` ping → `TM[17,2]` connection report |
| 20 | Parameter management | `TC[20,1]` get, `TC[20,3]` set parameter |
| 23 | File management | file ops (later revisions) |

Custom/mission services use type ≥ 128 (e.g. `TC[128,1]`). When a brief names a service or an opcode like `TC[8,1]` or a `perform function`, build the PUS secondary header with that type/subtype and put the argument bytes in the application data.

## PUS CRC

Every PUS TC/TM packet ends with a 16-bit CRC: **CRC-CCITT, poly `0x1021`, init `0xFFFF`** — the `crc-ccitt-false` variant, identical to the TC FECF routine in `ccsds-frame-construction.md`. Compute over the whole packet from the primary header through the last data octet.

## PUS acknowledgement flags (CTF-relevant)

The TC secondary header's 4-bit ack flags request four separate reports:

| Bit | Report | PUS service |
|---|---|---|
| Acceptance | acknowledge acceptance | `TM[1,1]` ok / `TM[1,2]` fail |
| Start of execution | started executing | `TM[1,3]` / `TM[1,4]` |
| Progress of execution | intermediate progress | `TM[1,5]` / `TM[1,6]` |
| Completion | finished executing | `TM[1,7]` ok / `TM[1,8]` fail |

Set **all four** during triage — each downlink report is an independent oracle telling you exactly where the command was rejected (validation before dispatch, mid-execution fault, or after-completion status). A challenge that returns only silence often just has the ack flags disabled; toggle them on and re-send.

## PUS Service 8 (function management) and Service 20 (parameters)

These two collect most "mission custom" commands. If the brief names a `perform function` opcode (`TC[8,1]`) with a function ID and argument bytes — or a `set parameter` (`TC[20,3]`) with a parameter ID + value — that *is* the challenge grammar. The function/parameter ID list is usually in the MDB (Yamcs) or the mission command DB (COSMOS); enumerating it is often the actual first step of the challenge (see `sdls-and-ground-cves.md`).
