---
name: pwntools
description: "Auth/lab ref: Python CTF/exploitation framework for interacting with remote services, local processes, and binary exploitation."
license: MIT
compatibility: "Python 3.8+; Linux primary (full feature set); macOS partial."
metadata:
  author: AeonDave
  version: "1.0"
  category: offensive-tools
  language: python
---

# pwntools

Service-interaction and binary exploitation framework. The central abstraction is the **tube** — a uniform API for TCP sockets, local processes, and SSH channels. Write your solver once; switch between local and remote with one flag.

## Installation

```bash
pip install pwntools
```

## Canonical solver template

Every CTF solver follows this pattern:

```python
from pwn import *
import sys

# Connection switch: python solver.py host:port
# Local:  python solver.py                 → process(cmd)
# Remote: python solver.py host:1337       → remote(host, port)
# Debug:  python solver.py host:1337 debug → remote(..., level='debug')

if len(sys.argv) > 1:
    host, port = sys.argv[1].split(':')
    level = sys.argv[2] if len(sys.argv) > 2 else 'info'
    io = remote(host, int(port), level=level)
else:
    io = process(['python3', 'challenge/server.py'])

# --- solver logic ---

io.close()
```

This template appears verbatim in HTB Cyber Apocalypse 2025 (Twin Oracles, Kewiri, Traces) and is the de-facto standard.

---

## Tube API — receive

All receive calls block until the delimiter/count is met, or raise `EOFError` on close.

| Method | Description |
|--------|-------------|
| `io.recv(n)` | Up to n bytes, returns as soon as any data is available |
| `io.recvn(n)` | Exactly n bytes — blocks until complete |
| `io.recvline()` | Until `\n` — includes newline by default |
| `io.recvline(drop=True)` | Until `\n` — strips newline |
| `io.recvuntil(b'delim')` | Until delimiter — includes delimiter |
| `io.recvuntil(b'delim', drop=True)` | Until delimiter — strips it |
| `io.recvregex(b'pattern')` | Until regex match |
| `io.recvregex(b'pattern', capture=True)` | Returns `re.Match` object |
| `io.recvall()` | Until EOF |
| `io.recvrepeat(timeout)` | Until timeout or EOF |
| `io.clean()` | Drain buffer (discard pending data) |

### Parsing received data

```python
# Read a line, strip newline, decode to str, extract last token
value = int(io.recvline().decode().strip().split()[-1])

# Read until marker, drop marker, decode, split on ' = '
value = int(io.recvuntil(b'\n', drop=True).decode().split(' = ')[1])

# Read multiple named values from consecutive lines
# Server sends: "n = 12345\ne = 65537\n"
n = int(io.recvline().decode().split(' = ')[1])
e = int(io.recvline().decode().split(' = ')[1])

# Receive until prompt, then parse all hex values from the output
raw = io.recvuntil(b'> ').decode()
import re
values = list(map(bytes.fromhex, re.findall(r'[0-9a-f]{6,}', raw)))
```

---

## Tube API — send

| Method | Description |
|--------|-------------|
| `io.send(data)` | Raw bytes, no newline |
| `io.sendline(data)` | Bytes + `\n` |
| `io.sendafter(b'delim', data)` | `recvuntil(delim)` then `send(data)` |
| `io.sendlineafter(b'delim', data)` | `recvuntil(delim)` then `sendline(data)` |
| `io.sendlinethen(b'delim', data)` | `sendline(data)` then `recvuntil(delim)` |

### Sending values

```python
# Send integer as decimal string
io.sendline(str(value).encode())

# Send integer as hex string (no 0x prefix)
io.sendline(hex(value)[2:].encode())

# Send after prompt: recvuntil(b'> ') then sendline(answer)
io.sendlineafter(b'> ', str(answer).encode())

# Send comma-separated list
io.sendlineafter(b'> ', ','.join(map(str, my_list)).encode())

# Send underscore-separated factorization (HTB Kewiri pattern)
answer = '_'.join([f'{f},{e}' for f, e in factors])
io.sendlineafter(b' > ', answer.encode())
```

---

## Service interaction patterns

### Pattern 1: Single question/answer loop

Server sends a prompt, client sends an answer, repeat.

```python
for _ in range(100):
    io.recvuntil(b'Question: ')
    q = io.recvline(drop=True).decode()
    answer = solve(q)
    io.sendline(str(answer).encode())

flag = io.recvline().decode()
print(flag)
```

### Pattern 2: Oracle query loop (crypto CTF)

Server offers a menu. Client selects an option, sends ciphertext, receives result.
Classic pattern in RSA/AES oracle challenges.

```python
def query_oracle(ciphertext):
    io.sendlineafter(b'> ', b'2')          # select oracle option
    io.recvuntil(b': ')
    io.sendline(hex(ciphertext)[2:].encode())
    return int(io.recvline().decode().split()[-1])

# Binary search using oracle (parity/LSB oracle)
lo, hi = 1, n - 1
for _ in range(n.bit_length()):
    mid = (lo + hi) // 2
    result = query_oracle(pow(2, e, n) * ciphertext % n)
    if result:
        lo = mid + 1
    else:
        hi = mid
```

### Pattern 3: Multi-phase protocol

Server requires: connect → auth/setup → challenge phase → flag retrieval.

```python
# Phase 1: receive server parameters
io.recvuntil(b'n = ')
n = int(io.recvline())
io.recvuntil(b'e = ')
e = int(io.recvline())

# Phase 2: interact with challenge API
io.sendlineafter(b'option > ', b'1')
ct = int(io.recvline().decode().split()[-1])

# Phase 3: send solution
io.sendlineafter(b'answer > ', str(solution).encode())
flag = io.recvline().decode()
```

### Pattern 4: Server sends structured menu

```python
def interact(option, data=None):
    io.sendlineafter(b'> ', str(option).encode())
    if data is not None:
        io.recvuntil(b': ')
        io.sendline(data if isinstance(data, bytes) else str(data).encode())
    return io.recvline().decode().strip()

# Use case
ct = interact(1)          # option 1: encrypt
pt = interact(2, ct)      # option 2: decrypt with ciphertext
```

### Pattern 5: Collect data across multiple connections (HTB Traces)

```python
# Service emits encrypted channel logs on connect
io.sendlineafter(b'> ', b'join #general')
raw = io.recvuntil(b'guest > ').strip().decode()
enc_data = list(map(bytes.fromhex, re.findall(r'[\da-f]{6,}', raw)))
```

---

## Context and logging

```python
context.log_level = 'debug'    # show all send/recv bytes
context.log_level = 'info'     # default — show sent/received sizes
context.log_level = 'warning'  # suppress routine output

# Architecture (needed for ELF/shellcraft)
context.arch = 'amd64'
context.bits = 64
context.os = 'linux'

# Pass log level from command line
io = remote(host, port, level=sys.argv[2] if len(sys.argv) > 2 else 'info')
```

---

## Utility functions

### Encoding and packing

```python
from pwn import *

# Pack integers to bytes (little-endian by default)
p64(0xdeadbeef)          # → b'\xef\xbe\xad\xde\x00\x00\x00\x00'
p32(0xdeadbeef)          # → b'\xef\xbe\xad\xde'
u64(b'\xef\xbe\xad\xde\x00\x00\x00\x00')  # → 0xdeadbeef

# XOR (operates on bytes, handles different lengths)
xor(b'key', b'plaintext')
xor(b'\x41\x42', b'\x01\x02')   # → b'CB'
xor(ciphertext, key, plaintext)  # three-way XOR

# Hex helpers
enhex(b'hello')          # → '68656c6c6f'
unhex('68656c6c6f')       # → b'hello'

# Number ↔ bytes (Crypto.Util.number equivalent)
from pwn import *
# pwntools does not ship long_to_bytes/bytes_to_long
# use pycryptodome for these:
from Crypto.Util.number import long_to_bytes, bytes_to_long
```

### Cyclic patterns (buffer overflow offset finding)

```python
cyclic(100)              # generate 100-byte De Bruijn sequence
cyclic_find(0x61616168)  # find offset of 4-byte sequence
```

---

## Binary exploitation (brief — see reference)

```python
# Load ELF
elf = ELF('./vuln')
libc = ELF('./libc.so.6')

# Address lookup
elf.symbols['main']
elf.got['printf']
elf.plt['system']

# Leak libc base from a leak
libc.address = leaked_puts - libc.symbols['puts']

# ROP chain
rop = ROP(elf)
rop.call('system', [next(elf.search(b'/bin/sh\x00'))])
payload = flat({offset: rop.chain()})

# Shellcode
shellcode = asm(shellcraft.sh())
shellcode = asm(shellcraft.amd64.linux.sh())

# GDB attach (local process)
gdb.attach(io)
gdb.attach(io, gdbscript='b *main+0x42\ncontinue')
```

---

## Debugging workflow

```python
# Option 1: debug flag to process
io = process('./vuln', level='debug')

# Option 2: attach GDB mid-exploit
io = process('./vuln')
gdb.attach(io)
pause()                   # wait for gdb to attach before continuing

# Option 3: pause at specific point
io.sendline(b'A' * 40)
pause()                   # press enter to continue

# Option 4: inspect tube buffer state
io.unrecv(b'debug data')  # push data back into recv buffer
```

---

## Anti-patterns

- Calling `io.recvline()` when the service does not send a newline — use `io.recvuntil(b'prompt')` instead.
- Sending Python `int` directly — always `.encode()` or wrap with `str()`.
- Forgetting `drop=True` on `recvuntil` when the delimiter should not be in the parsed value.
- Using `io.recv()` (non-blocking, may return partial) instead of `io.recvn(n)` when an exact byte count is needed.
- Importing `from Crypto.Util.number import long_to_bytes` but assuming pwntools provides it — it does not.

---

## Resources

- [references/service-interaction.md](references/service-interaction.md) — extended patterns for crypto oracle challenges, multi-round protocols, parsing strategies, error handling.
- [references/binary-exploitation.md](references/binary-exploitation.md) — ELF loading, ROP chains, shellcraft, format string exploitation, GDB integration.
</content>
</invoke>
