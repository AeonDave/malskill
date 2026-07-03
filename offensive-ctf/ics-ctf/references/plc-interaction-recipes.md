# PLC Interaction Recipes

Use this reference when `ics-ctf` is active and the task moves from passive decode to authorized interaction with an isolated lab target. Read-only first; write only with a defined oracle and read-back.

## Safe interaction ladder (recap)

1. Decode from artifact only.
2. Read-only query against the lab service.
3. Local simulation of the write against a sandbox PLC simulator (OpenPLC, ModbusPal, `snap7-server`, free OPC UA server).
4. Single idempotent write on target with immediate read-back.
5. Stop after validation; do not enumerate further.

For every recipe below: replace `TARGET`, `PORT`, addresses, and values with task-specific evidence. Avoid broadcast writes, mass writes, FC 8 sub-functions that reset/restart the device, and engineering-software downloads unless the task explicitly requires that exact action.

## Modbus enumeration and interaction

### Passive identify from PCAP

```bash
tshark -r capture.pcapng -Y modbus -T fields -e ip.src -e ip.dst \
  -e modbus.unit_id -e modbus.func_code -e modbus.reference_num \
  -e modbus.regval_uint16 | sort -u | head
```

### Service fingerprint

```bash
nmap -sV -p 502 --script modbus-discover --script-args='modbus-discover.aggressive=true' TARGET
```

`modbus-discover` walks unit IDs 1–247 and asks FC 43 (Read Device Identification) when available — minimal load and useful for vendor/product/firmware tags.

### Read sweep with `pymodbus`

```python
# pymodbus >= 3.10 uses device_id=; on 3.9 and earlier substitute slave=.
from pymodbus.client import ModbusTcpClient

c = ModbusTcpClient("TARGET", port=502)
assert c.connect()
try:
    holding = c.read_holding_registers(address=0, count=64, device_id=1)
    inputs  = c.read_input_registers(address=0, count=64, device_id=1)
    coils   = c.read_coils(address=0, count=64, device_id=1)
    discr   = c.read_discrete_inputs(address=0, count=64, device_id=1)
    print("HR :", holding.registers if not holding.isError() else holding)
    print("IR :", inputs.registers  if not inputs.isError()  else inputs)
    print("CO :", coils.bits        if not coils.isError()   else coils)
    print("DI :", discr.bits        if not discr.isError()   else discr)
finally:
    c.close()
```

Walk wider ranges only if narrow ranges return noise. Many lab targets use addresses 0..15 for the interesting tags.

### Coil discovery loop

```python
from pymodbus.client import ModbusTcpClient

c = ModbusTcpClient("TARGET", 502); c.connect()
for base in range(0, 1000, 16):
    r = c.read_coils(base, count=16, device_id=1)
    if not r.isError() and any(r.bits):
        print(base, r.bits)
c.close()
```

### Single safe write with read-back

```python
from pymodbus.client import ModbusTcpClient

c = ModbusTcpClient("TARGET", 502); c.connect()
prev = c.read_holding_registers(0, 1, device_id=1).registers[0]
c.write_register(0, 1234, device_id=1)
after = c.read_holding_registers(0, 1, device_id=1).registers[0]
print(prev, "->", after)
c.write_register(0, prev, device_id=1)  # restore when scope allows
c.close()
```

Restoring the prior value is the default unless the oracle requires the new state to persist (for example, an HMI page or score endpoint reflecting the change).

### Process-effect patterns to expect

- Holding register 0–3 often holds primary process values (pressure, temperature, level, flow).
- A coil tied to a "cooler", "pump", "valve", or "alarm" flag often gates the success oracle.
- Setpoint registers that exceed a documented limit trigger interlocks or alarms; some labs solve only when the alarm fires.
- Watch for register values that update on their own — that register is being driven by the PLC program and should not be written naively.

### Modbus CLI alternatives

```bash
# modbus-cli (Ruby): read 10 holding regs starting at 40001
modbus read TARGET 40001 10

# mbtget (Perl/C): write coil 0 to ON
mbtget -w5 1 -a 0 TARGET
```

These are useful when no Python is available or when scripting a quick sweep from the shell.

## Siemens S7 enumeration

### Service fingerprint

```bash
nmap -sV -p 102 --script s7-info TARGET
plcscan TARGET           # legacy banner enumeration
s7scan --range TARGET/24 # modern scanner with rack/slot detection
```

### Read with `python-snap7`

```python
import snap7
from snap7.util import get_int, get_real

cli = snap7.client.Client()
cli.connect("TARGET", rack=0, slot=1)        # confirm rack/slot from PCAP or nmap
data = cli.db_read(db_number=1, start=0, size=64)
print(get_int(data, 0), get_real(data, 4))
cli.disconnect()
```

If `rack`/`slot` are wrong, the session is closed by the PLC; never brute-force across many combinations against a real device.

### S7 cues in PCAP

- `s7comm.header.rosctr == 1` (Job) followed by `== 3` (Ack-Data) is a normal request/response.
- `s7comm.param.func == 0x04` (Read Var) and `0x05` (Write Var) carry the area type and address.
- SZL reads live in userdata (ROSCTR 0x07), CPU funcgroup: filter `s7comm.header.rosctr == 7 and s7comm.param.userdata.funcgroup == 4 and s7comm.param.userdata.subfunc == 1`, or just `s7comm.data.userdata.szl_id` to see every SZL. Common IDs: 0x0011 (module identification / order code), 0x001C (CPU details), 0x0017 (LED status).

## OPC UA

### Discovery and anonymous policy

```bash
python -m asyncua.tools.uadiscover opc.tcp://TARGET:4840
```

Look for endpoints with `SecurityPolicy: None` and `MessageSecurityMode: None`; these accept anonymous connections without certificates.

### Browse and read

```python
import asyncio
from asyncua import Client

async def main():
    async with Client("opc.tcp://TARGET:4840") as c:
        root = c.nodes.root
        objects = await root.get_child(["0:Objects"])
        for n in await objects.get_children():
            print(await n.read_browse_name(), n.nodeid)

asyncio.run(main())
```

### Targeted read/write

```python
# Read a known node, write only if the oracle requires it
node = c.get_node("ns=2;s=Setpoint")
print(await node.read_value())
# await node.write_value(123.0)
```

## MQTT broker enumeration

```bash
# Wildcard subscribe to map topics
mosquitto_sub -h TARGET -p 1883 -t "#"   -v
mosquitto_sub -h TARGET -p 1883 -t "$SYS/#" -v   # broker stats and clients
```

Useful follow-ups:

- Inspect retained messages on each topic by subscribing with `-t "topic/+"`.
- Probe authentication by connecting with and without `-u/-P` and observing `CONNACK` codes.
- Correlate publisher client IDs and `lwt` (last-will) topics with PLC/HMI roles.

## CAN bus

```bash
# bring up a virtual interface for replay tests
sudo modprobe vcan
sudo ip link add dev vcan0 type vcan
sudo ip link set up vcan0

candump vcan0
cansniffer vcan0
cansend vcan0 123#DEADBEEF
```

For real hardware, prefer `candump` and `cansniffer` first to learn periodicity and arbitration IDs before injecting frames. Counter and checksum fields often need to be reconstructed for the message to be accepted.

## Engineering-software pivot patterns

When a PLC port sits next to a web UI or scripting runtime, treat the runtime as a second target:

- OpenPLC runtime/editor: web panel commonly on TCP 8080; supports a Python scripting module (PSM) that runs as part of the PLC scan cycle. If PSM access is unlocked, custom Python in the cycle is a known initial-access path on lab installations (see CVE-2021-31630 for one historical pattern). Treat such pivots as initial-access and pass the resulting shell to `post-exploit-technique`.
- Node-RED: web editor commonly on TCP 1880; function nodes execute Node.js, and dashboards can expose flows that talk to PLCs. Check for unauthenticated admin access, default credentials, and exposed `/settings` or admin API.
- ScadaBR, FUXA, Rapid SCADA, Codesys WebVisu, ifix, WinCC web: HMI/historian panels that may store credentials, dashboards, and historian data; default creds and known CVEs are the usual first checks.
- Honeypots (ConPot) and simulators (MiniCPS, ICSsim, ModbusPal, QModMaster, Modbus Poll) emulate protocols; if responses look too uniform across function codes or banners match known honeypot strings, validate before assuming a real PLC.

## Validation and stop conditions

- Read-back confirms the intended state change, or the HMI/scoreboard/oracle reports the solved condition.
- Decoded secret recovered from a register, tag, topic, or device-identification field.
- Process timeline shows the expected cause and effect, with no unrelated side effects on adjacent registers/coils.

Stop after the proof is captured. Restore prior values when scope allows and document the exact sequence of operations in the writeup.
