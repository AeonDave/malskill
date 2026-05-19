# TIA Portal and PLC fundamentals (engineering-workstation pivot)

Audit/CTF-oriented synthesis of Siemens S7-1500 / TIA Portal / PLCSim Advanced / HMI Basic Panel
fundamentals, distilled from a real PLC-HMI test-bench project (Polito MSc thesis 14472,
Shekasteh, 2019/2020, supervisor Mazza — pneumatic cylinder lifetime test bench, WEAR/LEAK/BOTH
modes). Vendor-neutral framing is preserved; Siemens names appear because TIA Portal is the
dominant engineering workstation toolchain on European OT estates.

Use this file when a challenge or assessment exposes engineering workstations, project archives,
HMI panels, or PLC simulators rather than only wire traffic.

## 1. Engineering toolchain layering

| Layer | Tool | Role | Artifacts you may receive |
| --- | --- | --- | --- |
| Engineering IDE | TIA Portal | Project authoring, block editor, HW config, HMI design | `.ap1x` project folder, `.zap1x` archive, `.s7p` legacy |
| Hardware catalog | HSP (Hardware Support Package) | Adds new CPU/IO modules to TIA catalog | `.isp1x` HSP files, must match TIA Portal major version |
| Simulator | PLCSim Advanced | Virtual S7-1500 CPU, executes downloaded project without hardware | runtime config, simulation tables |
| Field simulator | Festo FluidSim (and similar) | Pneumatic/hydraulic circuit sim wired to PLC IO via a comms bridge | `.ct` / `.circ` circuits |
| HMI runtime | Basic Panel / Comfort Panel (WinCC) | Operator-facing screens, alarms, archives | HMI tag table, screens, archive on internal SD / USB |

Key reasoning hooks for CTF/audit:

- A `.zap1x` archive is a self-contained project archive. Opening it in TIA Portal reconstructs
  blocks, HW config, IP plan, HMI screens, tag tables, and embedded comments. Treat it the same
  as source code: searchable, diffable, and often containing default credentials in comments,
  IP plans, and HMI tooltips.
- PLCSim Advanced lets you run that project offline against a virtual CPU. This is the single
  most important offline lab primitive: you can drive inputs, observe outputs, set breakpoints
  on networks, and watch tag values without ever touching the real plant — ideal for safe logic
  reverse engineering and exploit validation.
- HSP version drift is the most common reason a seized archive fails to open. Match TIA Portal
  major version to the archive, then add the HSP matching the CPU firmware (e.g., S7-1516 FW
  V2.8.x ↔ specific HSP). Without HSP match, devices appear as `unknown` in the topology.

## 2. Block taxonomy (S7-1500)

The CPU executes a small set of block types in deterministic order. Recognizing the type tells
you what each block can carry.

| Block | Role | State | Typical CTF/audit angle |
| --- | --- | --- | --- |
| OB (Organization Block) | Entry points called by the OS | None (uses L stack) | OB1 = main cyclic; other OBs handle startup, interrupts, faults; OB1 wires the program |
| FB (Function Block) | Reusable subroutine **with** state | Persistent in instance DB | Carry the actual control logic (PID, sequencers, mode managers); compare networks across FBs |
| FC (Function) | Reusable subroutine **without** state | Local only | Often pure helpers (scaling, conversions, lamp logic); cheaper to audit |
| DB (Data Block) | Structured memory | Global or instance | Recipe data, setpoints, counters, alarms; usually the easiest place to read/poison |

OB1 is implemented as a series of "networks" (ladder rungs or FBD segments). The reference
project has 34 networks in OB1 covering: input mapping, mode selection, HMI button handling,
counter reset chains, indicator-light feedback, and FB/FC calls. When you reverse a project,
read OB1 networks **in order** — the cyclic flow is essentially the program's main loop.

## 3. Memory areas (S7-1500)

Address letters that appear in tag tables and decompiled blocks:

| Area | Meaning | Read/write | Typical use |
| --- | --- | --- | --- |
| `I` (`%I`) | Input process image | Read | Mirrors physical inputs at cycle start |
| `Q` (`%Q`) | Output process image | Write | Pushed to physical outputs at cycle end |
| `M` (`%M`) | Marker / bit memory | Read/write | Internal flags, edge memory, HMI buttons |
| `DB` | Data blocks | Read/write | Setpoints, counters, recipes, alarms |
| `L` | Local/temp stack | Block-scoped | Block-local working variables |
| `T` / `C` | Timers / counters (legacy mapping) | Read/write | Replaced by `IEC_TIMER` / `IEC_COUNTER` in S7-1500 |

Audit/CTF hooks:

- DB tags are the cleanest lever in a logic-replacement attack: change a setpoint or threshold
  inside a global DB and the cyclic logic accepts the new value on the next scan without any
  block reload signature on the wire.
- M-area flags are often used as HMI button proxies. A network like
  `M0.0 (Start_HMI) -> reset_counter` is a classic giveaway that the HMI tag binds directly to
  the same M bit; mapping the HMI tag table back to M addresses reconstructs operator intent.
- I/Q traffic on PROFINET is what defenders see on the wire; modifying behavior via DB or M
  does **not** look like a write to Q, so it is harder to detect.

## 4. Tag tables and HMI binding

A TIA project ships two related tag tables: the **PLC tag table** (canonical, addresses + types)
and the **HMI tag table** (names + bindings to PLC tags, possibly via OPC UA or Profinet).

What this lets you do offline:

- Reconstruct operator intent: every HMI button on a screen maps to an HMI tag, which maps to a
  PLC tag (usually an M bit or a DB field). The HMI screen + tag table is essentially a labeled
  index of the control surface.
- Identify writable surfaces: HMI tags marked read/write are the operator-reachable knobs;
  read-only tags are status indicators.
- Spot archives: Basic/Comfort panels can archive analog tags to internal storage and to a USB
  stick attached to the back of the panel. Treat that USB as a forensic artifact when you have
  physical access — historian-grade data without touching the SCADA server.

## 5. Network layout

A minimal S7-1500 + HMI cell uses PROFINET over copper with a small managed switch (Siemens
Scalance is the reference family). Each device — PLC CPU, HMI panel, engineering PC, and any
IO device — has an explicit IPv4 address on the same subnet. Discovery is via DCP (Discovery
and Configuration Protocol), which is broadcast and runs even when IP addresses are blank.

CTF/audit hooks:

- A PCAP with PROFINET DCP frames lets you enumerate devices and their names ("PLC_1",
  "HMI_1", "S7-1516-3 PN/DP") without ever sending a packet. This is the wireless-equivalent
  passive survey for OT cells.
- Scalance switches often expose web management with default credentials. Default-cred photos
  on plant file shares (see the IT→OT chain reference) frequently include switch labels too.
- A misconfigured engineering PC sometimes bridges IT and OT subnets through a second NIC —
  this is the canonical OT-DMZ bypass and shows up immediately in `ip route` on the workstation.

## 6. Practical workflow when you receive a project archive

1. **Identify**: file extension (`.zap1x`, `.ap1x`, `.s7p`), TIA Portal version embedded in the
   archive metadata, and CPU family. Mismatch ⇒ install correct TIA Portal + HSP.
2. **Open read-only**: extract the archive in a sandbox, never directly into a TIA Portal
   workspace pointing at the live plant. Pull HW config, IP plan, and HMI screens first.
3. **Map the surface**: dump PLC tag table and HMI tag table to CSV; cross-reference to find
   operator-reachable writable tags.
4. **Reverse OB1 networks**: read in order; capture mode-selection logic and any safety
   interlocks (E-stop, safety-bus inputs — never bypass).
5. **Simulate offline**: load into PLCSim Advanced; drive inputs from a simulation table;
   observe DB and M evolution; build an oracle for live testing.
6. **Plan minimal write**: pick a single DB field or M bit; predict observable effect on HMI
   and outputs; confirm against simulator before touching the real PLC.
7. **Document**: blocks read, networks reversed, tags identified, hypotheses validated against
   PLCSim Advanced, and the exact minimum write you would issue on the real CPU.

## 7. Cross-links

- [attack-patterns.md](attack-patterns.md) — protocol-level write/upload patterns once the
  logic is understood.
- [fundamentals-and-it-to-ot-chain.md](fundamentals-and-it-to-ot-chain.md) — how attackers
  reach this engineering workstation in the first place (IT → AD → DMZ → eng-WS).
- [signal-decoding-and-testing.md](signal-decoding-and-testing.md) — once you know which DB
  field is the setpoint, the test-cycle discipline tells you how to write it safely.
- [plc-interaction-recipes.md](plc-interaction-recipes.md) — concrete client commands once
  the writable surface is mapped.

## 8. Sources

- Politecnico di Torino MSc thesis 14472, Mohammad Shekasteh, "Automation and PLC-HMI
  Programming & Configuration", supervisor Prof. Luigi Mazza, AY 2019/2020 — Siemens S7-1500
  + TIA Portal + PLCSim Advanced + Festo FluidSim test bench for pneumatic cylinder lifetime
  testing (WEAR/LEAK/BOTH modes).
- Siemens SIMATIC S7-1500 system manual and PLCSim Advanced V2.x function manual.
