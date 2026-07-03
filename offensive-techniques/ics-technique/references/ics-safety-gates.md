# ICS Safety Gates and Engagement Rules

Operational constraints for authorized ICS/OT assessments. Safety of the physical process is a hard constraint that overrides all other objectives.

---

## Why ICS safety differs from IT

In IT pentesting, a failed exploit causes a process to crash and restart. In ICS:
- A force-written output coil can open a valve, trip a breaker, or disable an emergency stop.
- A PLC CPU halt stops all control logic — outputs freeze at last state, sensors stop being read.
- A historian exploit can expose weeks of process data including production quantities, safety setpoints, and personnel shifts.
- Physical equipment damage from incorrect outputs may take weeks and significant cost to repair.

These are not theoretical risks. FrostyGoop (2024, ninth known ICS-specific malware; Golang; abuses Modbus TCP FC06 to manipulate ENCO controller setpoints — disrupted district heating in Lviv). Fuxnet (2024, Blackjack group vs Moskollektor sensor-gateways; wipes NAND, floods RS-485/M-Bus to disable field sensors). Prior classes still relevant: PIPEDREAM/INCONTROLLER (2022, modular attack framework targeting Schneider/OMRON/CODESYS and OPC UA); Industroyer2 (2022, IEC 60870-5-104 payload); CosmicEnergy (2023, IEC-104 red-team tool leaked publicly).

---

## Pre-engagement checklist

Before any active ICS testing:

- [ ] Scope document explicitly names target devices, segments, and authorized actions.
- [ ] Client's OT/process engineer has reviewed and signed off on the test plan.
- [ ] Emergency contact for process shutdown is identified and reachable during testing.
- [ ] A maintenance window or production freeze is scheduled for any write-phase testing.
- [ ] All test PLCs/RTUs in scope are confirmed as lab units or isolated test segments — not connected to live actuators, valves, motors, or field devices.
- [ ] Rollback procedure documented: who does what if a write test causes process disruption.
- [ ] Scan rate and timing agreed: OT devices often cannot tolerate scan rates safe for IT (see below).

---

## Action risk classification

| Action | Risk | Approval required |
|--------|------|------------------|
| Passive traffic capture | Negligible | Standard engagement authorization |
| Active port scan (gentle, -T2) | Low | Standard authorization; avoid broadcast/syn-flood |
| Protocol fingerprinting (read FC only) | Low | Standard authorization |
| Read coils / registers (FC01-04) | Low | Standard authorization |
| Read device identification (FC43) | Low | Standard authorization |
| Write single register (FC06) — lab PLC | Medium | Written client approval + rollback plan |
| Write coils (FC05/15) — lab PLC | High | Written approval + engineer present + actuator disconnected |
| PLC CPU stop/start | High | Written approval + engineer present + lab target confirmed |
| Write safety-linked output | Critical | **Out of scope** unless SIS engineer explicitly clears and isolates |
| Replay captured Modbus write | Medium-High | Written approval + captured payload reviewed for safety impact |
| Historian database write | High | Written approval; treat as same risk as production change |
| Aggressive scan (masscan, default Nessus) | Critical | **Never on live OT segment** — documented to cause PLC CPU overload |

---

## Safety-linked output identification

Before any write test, identify which registers and coils map to physical actuators:

1. **Request I/O mapping from client**: the site engineer has the PLC I/O documentation.
2. **Review ladder logic** (if accessible via engineering software): trace coil addresses to physical outputs.
3. **Cross-reference process P&ID diagrams**: identify which outputs control valves, pumps, heaters, emergency stops.
4. **Conservative default**: if you cannot confirm an output is safe to write, **do not write it**.

Safety Instrumented Systems (SIS) — emergency shutdown systems, relief valve controls, fire and gas detection outputs — are **always out of scope for write operations** unless the SIS is physically isolated and the test is SIS-specific with the SIS engineer present.

---

## Scan rate guidance

| Device type | Safe scan rate | Notes |
|-------------|---------------|-------|
| Modern SCADA servers (historian, EWS) | Normal IT rates | Treat as Windows server |
| Soft PLCs (PC-based, Ignition, etc.) | T3 or lower | Monitor for CPU spike |
| Hardware PLC (S7-300, ControlLogix) | T2 (polite) | Single target at a time |
| RTU / legacy SCADA equipment | Manual single-target queries only | Many cannot handle concurrent connections |
| Safety controllers (SIS, SIL-rated) | **Do not scan** | Even read traffic can affect timing |

In practice: use nmap with `-T2 --max-retries 1 --host-timeout 30s` on OT segments. For ICS protocol queries, use single sequential requests rather than parallel scanners.

---

## Rollback procedures

For every write test, document before executing:

```
Target: <IP>:<port>, slave ID: <n>, address: <addr>
Original value: <read and record>
Test value: <what will be written>
Restoration command: <exact command to restore>
Process impact if not restored: <description>
Engineer on call: <name, phone>
```

Template for Modbus rollback:

```python
# Step 1: Read and save
before = c.read_coils(address, 1, slave=slave).bits[0]
before_reg = c.read_holding_registers(address, 1, slave=slave).registers[0]

# Step 2: Write test value
c.write_coil(address, True, slave=slave)

# Step 3: Observe
# ...

# Step 4: Restore (always, even if test succeeds)
c.write_coil(address, before, slave=slave)
```

---

## Reporting ICS findings

ICS risk ratings differ from IT CVSS — physical and process impact must be explicit:

| Finding | IT severity | ICS severity | Why different |
|---------|------------|--------------|--------------|
| Unauthenticated Modbus read | Low | Medium | Exposes setpoints, process state, production data |
| Unauthenticated Modbus write | Medium | Critical | Direct physical process manipulation |
| PLC remote CPU stop | High | Critical | Complete process shutdown — physical equipment risk |
| Historian SQL injection | High | Critical | Process data exposure + IT/OT pivot path |
| Default credentials on EWS | High | Critical | Full HMI control = full process control |

Always link each finding to:
1. The specific process it affects (heating system, water treatment, conveyor).
2. The physical impact if exploited (valve opens, pump stops, temperature uncontrolled).
3. A realistic attacker scenario (insider threat, IT/OT pivot, remote access compromise).

---

## Emergency stop during testing

If at any point during testing a process anomaly is observed that may be related to test activity:

1. Stop all active test commands immediately.
2. Restore all written values to their recorded original state.
3. Notify the client's on-call engineer immediately by phone (not email).
4. Document the exact sequence of actions and timestamps.
5. Do not resume testing until the engineer confirms process is stable.

This is a contractual and ethical obligation, not optional.
