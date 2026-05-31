# ICS Active Enumeration Reference

Commands and workflows for fingerprinting and interrogating ICS/OT devices in authorized assessments. All operations here are read-only unless explicitly noted.

---

## Pre-scan: passive asset discovery first

Always run passive discovery before any active probing. Zeek on a tap/span port reveals the full device inventory without sending a single packet.

```bash
# Zeek passive analysis
zeek -r ot_capture.pcap
# Produces: conn.log, dns.log, and protocol-specific logs

# Extract unique OT hosts and protocols
cat conn.log | zeek-cut id.orig_h id.resp_h id.resp_p service | sort -u | grep -v '-$'

# Modbus-specific: zeek modbus log
cat modbus.log | zeek-cut orig_h resp_h func_code exception 2>/dev/null

# Wireshark passive decode
# Apply display filters: modbus, s7comm, enip, dnp3, iec104, bacnet, pn_dcp, opcua
```

---

## Modbus (TCP 502)

```bash
# nmap Modbus discovery
nmap --script modbus-discover -p 502 <subnet>/24
nmap --script modbus-discover --script-args='modbus-discover.aggressive=true' -p 502 <target>

# Unit ID sweep (pymodbus)
python3 - <<'EOF'
from pymodbus.client import ModbusTcpClient
c = ModbusTcpClient('<target>', port=502, timeout=2)
c.connect()
for uid in range(1, 248):
    r = c.read_holding_registers(0, 1, slave=uid)
    if not r.isError():
        print(f"  Unit ID {uid}: ACTIVE")
c.close()
EOF

# Full read interrogation (all four register types)
python3 - <<'EOF'
from pymodbus.client import ModbusTcpClient
c = ModbusTcpClient('<target>', port=502)
c.connect()
slave = 1

for name, fn, kwargs in [
    ("Coils",     c.read_coils,             {"address":0,"count":128,"slave":slave}),
    ("DI",        c.read_discrete_inputs,   {"address":0,"count":128,"slave":slave}),
    ("HR",        c.read_holding_registers, {"address":0,"count":64, "slave":slave}),
    ("IR",        c.read_input_registers,   {"address":0,"count":64, "slave":slave}),
]:
    r = fn(**kwargs)
    print(f"{name}: {r.bits if hasattr(r,'bits') else r.registers if not r.isError() else r}")
c.close()
EOF
```

---

## Siemens S7comm (TCP 102)

```bash
# nmap fingerprint
nmap -sV --script s7-info -p 102 <target>

# snap7 full enumeration
python3 - <<'EOF'
import snap7

c = snap7.client.Client()
c.connect('<target>', rack=0, slot=1)

info = c.get_cpu_info()
state = c.get_cpu_state()
print(f"Module: {info.ModuleTypeName.decode()}")
print(f"Plant:  {info.PlantIdentification.decode()}")
print(f"State:  {state}")

# Enumerate data blocks (try DB1–DB100)
for db in range(1, 101):
    try:
        data = c.db_read(db, 0, 1)
        print(f"  DB{db}: accessible ({len(data)} bytes)")
    except:
        pass

c.disconnect()
EOF

# Metasploit S7 password enumeration
# use auxiliary/scanner/scada/s7_300_400_passwords
```

---

## EtherNet/IP / CIP (TCP 44818)

```bash
# nmap
nmap -sV --script enip-info -p 44818 <target>

# cpppo CIP identity object read
python3 -m cpppo.server.enip.client --print '<target>' '@0x01/1/1'   # Vendor
python3 -m cpppo.server.enip.client --print '<target>' '@0x01/1/2'   # Product type
python3 -m cpppo.server.enip.client --print '<target>' '@0x01/1/4'   # Product name

# Metasploit
# use auxiliary/scanner/scada/ethernet_ip_reveal
```

---

## DNP3 (TCP/UDP 20000)

```bash
nmap --script dnp3-info -p 20000 <target>
# use auxiliary/scanner/scada/dnp3_device_info (Metasploit)
```

---

## BACnet (UDP 47808)

```bash
nmap --script bacnet-info -p U:47808 <target>

# bacnet-stack WhoIs — discover all BACnet devices on broadcast domain
sudo apt install bacnet-stack-utils
bacwi -1                       # WhoIs broadcast
bacrp <instance_id> DEV 0 OBJECT-NAME    # read device name
bacrp <instance_id> AI 1 PRESENT-VALUE   # read analog input 1
```

---

## OPC-UA (TCP 4840)

```bash
# Endpoint enumeration (no auth required on default installs)
python3 - <<'EOF'
from opcua import Client
c = Client("opc.tcp://<target>:4840/")
c.connect()

# List security policies (check for None/no-auth endpoints)
for ep in c.get_endpoints():
    print(f"URL: {ep.EndpointUrl}")
    print(f"  Security: {ep.SecurityPolicyUri}")
    print(f"  Mode: {ep.SecurityMode}")

# Browse root
root = c.get_root_node()
for child in root.get_children():
    print(child, child.get_browse_name())

c.disconnect()
EOF
```

---

## Profinet DCP (UDP 34964)

Profinet DCP (Discovery and Configuration Protocol) is broadcast-based — passive Wireshark capture on the OT segment reveals all Profinet devices.

```bash
# Wireshark: display filter pn_dcp
# nmap
nmap -sU --script profinet-logo -p 34964 <target>

# Python scapy Profinet DCP identify request (active)
python3 - <<'EOF'
from scapy.all import *
from scapy.contrib.pnio_dcp import *
pkt = Ether(dst="ff:ff:ff:ff:ff:ff") / ProfinetIO() / PNDCPHeader() / PNDCPBlockReq()
sendp(pkt, iface="eth0")
EOF
```

---

## Historian fingerprinting

```bash
# OSIsoft PI
nmap -sV -p 5450,5457,5459 <historian>
curl -k https://<historian>/piwebapi/         # PI Web API if exposed

# SQL Server on historian
nmap -p 1433 <historian>
crackmapexec mssql <historian> -u sa -p '' --local-auth

# GE Proficy Historian
nmap -p 14000-14010 <historian>

# Common historian web UIs
curl http://<historian>:80/
curl http://<historian>:8080/
```

---

## Full scan template for OT engagement

```bash
# Step 1: Ping sweep (gentle)
nmap -sn -T2 <ot_subnet>/24 -oG alive_hosts.txt

# Step 2: Port scan alive hosts — ICS ports only, gentle rate
HOSTS=$(grep "Up" alive_hosts.txt | awk '{print $2}' | tr '\n' ',')
nmap -T2 --max-retries 1 -p 102,502,2404,4840,9100,20000,34964,44818,47808 \
  -sV --script s7-info,modbus-discover,enip-info,dnp3-info,bacnet-info \
  -oA ics_scan $HOSTS

# Step 3: Protocol-specific interrogation (sequential, not parallel)
# Run pymodbus/snap7/cpppo against each identified host manually
```
