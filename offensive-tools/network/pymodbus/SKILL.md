---
name: pymodbus
description: "Auth/lab ref: Python library for Modbus TCP and serial communication."
compatibility: "Linux, Windows, macOS; Python 3."
metadata:
  author: AeonDave
  version: "1.0"
---

# PyModbus

Programmatic Modbus access for the moments when register poking stops being a one-off curiosity.

## When to use PyModbus

Use PyModbus when you need to:

- read coils, discrete inputs, input registers, or holding registers
- write single or multiple coils/registers in an authorized lab
- script repeatable ICS/OT probes against Modbus TCP or RTU endpoints

## Quick Start

```python
from pymodbus.client import ModbusTcpClient

client = ModbusTcpClient("192.168.1.10", port=502)
client.connect()
result = client.read_holding_registers(address=0, count=2, slave=1)
print(result.registers)
client.close()
```

## High-Value Workflows

### Read holding registers

```python
from pymodbus.client import ModbusTcpClient

client = ModbusTcpClient("192.168.1.10", port=502)
client.connect()
resp = client.read_holding_registers(address=100, count=4, slave=1)
print(resp.registers)
client.close()
```

### Write a register or coil

```python
client.write_register(address=10, value=1234, slave=1)
client.write_coil(address=5, value=True, slave=1)
```

## Practical Notes

- Confirm unit/slave ID, register base, and endianness assumptions before concluding a read is wrong.
- Read operations are the right first move; write operations should be deliberate and explicitly authorized.
- Pair with packet captures or device manuals when register meaning is unclear.

## Caveats

- Modbus address numbering in documentation may not match library expectations exactly.
- Write calls can affect real processes; stay inside lab scope and use safe targets.
- Timeouts, serial settings, and endian interpretation cause a lot of false negatives.

## Resources

No bundled `scripts/`, `references/`, or `assets/`.
Use the current PyModbus docs for async clients, serial/RTU examples, and payload decoding helpers.
