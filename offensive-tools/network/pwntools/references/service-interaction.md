# Service Interaction — Deep Dive

Extended patterns for scripting interactive network services with pwntools tubes.
Most CTF crypto and pwn challenges reduce to a service interaction problem.

---

## Parsing strategies

### Parse by position

```python
# Server: "The value is: 42\n"
line = io.recvline().decode().strip()
value = int(line.split(': ')[1])

# Server: "n = 12345\n"
value = int(io.recvuntil(b'\n', drop=True).decode().split(' = ')[1])

# Server: "Result: 0x1a2b3c\n"
value = int(io.recvline().decode().split(': ')[1], 16)

# Server: "p = 7\nq = 11\nr = 13\n"
p, q, r = [int(io.recvline().decode().split(' = ')[1]) for _ in range(3)]
```

### Parse with regex

Useful when the format is mixed or unpredictable:

```python
import re

# Receive a block of output, extract all hex blobs
raw = io.recvuntil(b'prompt > ').decode()
hex_values = re.findall(r'[0-9a-f]{16,}', raw)
blobs = [bytes.fromhex(h) for h in hex_values]

# Extract a decimal number from a line
m = re.search(r'value: (\d+)', line)
if m:
    value = int(m.group(1))

# Extract multiple named fields
m = re.search(r'n=(\d+), e=(\d+)', raw)
n, e = int(m.group(1)), int(m.group(2))
```

### Parse JSON response

Some modern CTF services respond in JSON:

```python
import json

io.sendlineafter(b'> ', b'getparams')
raw = io.recvline().decode().strip()
data = json.loads(raw)
n = data['n']
ct = data['ciphertext']
```

### Parse multi-line blocks

Server sends a variable number of lines ending with a sentinel:

```python
lines = []
while True:
    line = io.recvline(drop=True).decode()
    if line == 'END' or line.startswith('flag'):
        break
    lines.append(line)
```

---

## Oracle interaction patterns

### LSB / parity oracle (RSA bit-by-bit attack)

Classic pattern from HTB Twin Oracles and similar challenges:

```python
def ask_oracle(ctxt):
    io.sendlineafter(b'> ', b'2')          # select oracle menu option
    io.recvuntil(b': ')
    io.sendline(hex(ctxt)[2:].encode())
    return int(io.recvline().decode().split()[-1])

def lsb_oracle_attack(ciphertext, e, n):
    """Binary search using LSB oracle to recover plaintext bit by bit."""
    lo, hi = 0, n
    f = pow(2, e, n)    # Enc(2) — multiply by 2 under RSA (homomorphic)
    curr = ciphertext
    for _ in range(n.bit_length()):
        curr = curr * f % n
        lsb = ask_oracle(curr)
        mid = (lo + hi) // 2
        if lsb == 1:    # plaintext is odd → lower half
            hi = mid
        else:           # plaintext is even → upper half
            lo = mid
    return lo
```

### Decryption oracle (AES, RSA)

```python
def decrypt(ciphertext_hex):
    io.sendlineafter(b'> ', b'decrypt')
    io.sendlineafter(b'ciphertext: ', ciphertext_hex.encode())
    return bytes.fromhex(io.recvline().decode().strip())
```

### Signature oracle

```python
def sign(message_hex):
    io.sendlineafter(b'> ', b'1')       # option 1: sign
    io.sendlineafter(b'msg: ', message_hex.encode())
    return int(io.recvline().decode().split(': ')[1], 16)
```

### Repeated query loop (collect N samples)

```python
samples = []
for _ in range(N):
    io.sendlineafter(b'> ', b'encrypt')
    ct = bytes.fromhex(io.recvline().decode().strip())
    samples.append(ct)
```

---

## Multi-phase protocol patterns

### Setup phase → challenge phase → solve phase

```python
# --- Phase 1: receive public parameters ---
io.recvuntil(b'Public key:\n')
n = int(io.recvuntil(b'\n', drop=True).decode().split(' = ')[1])
e = int(io.recvuntil(b'\n', drop=True).decode().split(' = ')[1])
ct = int(io.recvuntil(b'\n', drop=True).decode().split(' = ')[1])

# --- Phase 2: interact with oracle ---
solution = attack(ct, e, n)

# --- Phase 3: submit answer ---
io.sendlineafter(b'answer: ', str(solution).encode())
print(io.recvline().decode())
```

### Proof of work (PoW) bypass

Many services require solving a PoW before proceeding:

```python
import hashlib, itertools, string

line = io.recvline().decode().strip()
prefix = re.search(r"starts with '([0-9a-f]+)'", line).group(1)
salt = re.search(r"sha256\(X \+ b'(.+?)'\)", line).group(1).encode()

for chars in itertools.product(string.ascii_letters + string.digits, repeat=6):
    candidate = ''.join(chars).encode()
    h = hashlib.sha256(candidate + salt).hexdigest()
    if h.startswith(prefix):
        io.sendlineafter(b'> ', candidate)
        break
```

### Multi-round interactive challenge

```python
correct = 0
for round_num in range(100):
    io.recvuntil(f'Round {round_num + 1}: '.encode())
    challenge = io.recvline(drop=True).decode()
    answer = solve_round(challenge)
    io.sendlineafter(b'answer: ', str(answer).encode())
    result = io.recvline().decode().strip()
    if 'correct' in result.lower():
        correct += 1

flag = io.recvline().decode()
print(f'Score: {correct}/100, Flag: {flag}')
```

---

## Error handling and robustness

### Retry on failure

```python
from pwn import *

def solve():
    io = process(['python3', 'server.py'])
    try:
        flag = io.recvline().decode()
        if 'HTB{' in flag:
            return flag
    except EOFError:
        pass
    finally:
        io.close()
    return None

for attempt in range(20):
    result = solve()
    if result:
        print(result)
        break
```

### Timeout handling

```python
io.settimeout(10)

data = io.recvuntil(b'prompt', timeout=5)
if not data:
    io.close()
    raise RuntimeError('timed out')
```

### Catching EOFError

```python
try:
    flag = io.recvall().decode()
    print(flag)
except EOFError:
    print('Connection closed early')
```

---

## Sending structured data

### Comma / underscore delimited lists (factorization, coordinates)

```python
# HTB Kewiri pattern: "7,1_11,1_13,1" for [(7,1),(11,1),(13,1)]
factors = [(7, 1), (11, 1), (13, 1)]
answer = '_'.join([f'{p},{e}' for p, e in factors])
io.sendlineafter(b' > ', answer.encode())
```

### Binary data

```python
# Send raw bytes
io.send(crafted_block)

# Send hex-encoded for text protocol
io.sendline(crafted_block.hex().encode())

# Send base64-encoded
import base64
io.sendline(base64.b64encode(crafted_block))
```

---

## SSH and listen tubes

```python
# SSH
s = ssh('user', 'host', port=22, password='pass')
io = s.process('/path/to/challenge')
io = s.run('cat /flag')
print(io.recvall().decode())

# Listen for callback
l = listen(port=4444)
conn = l.wait_for_connection()
conn.sendline(b'id')
print(conn.recvline().decode())
```

---

## Timing and rate limiting

```python
from time import sleep

for i in range(queries):
    result = query_oracle(ciphertext_list[i])
    sleep(0.05)   # avoid triggering rate limit
```

---

## Common one-liners

```python
# Receive until flag pattern
flag = io.recvregex(rb'HTB\{[^}]+\}').decode()

# Quick interactive session
remote('host', 1337).interactive()

# Receive banner and close
banner = remote('host', 1337).recvall().decode()
```
