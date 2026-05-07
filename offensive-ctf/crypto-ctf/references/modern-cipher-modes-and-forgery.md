# Preserved source: modern-ciphers.md

This reference is a debrandized preservation copy of imported CTF-skill material. It keeps technical techniques, code patterns, workflows, and decision cues while removing challenge, platform, and competition branding. Treat it as a domain knowledge bank loaded after the concise SKILL.md routing guidance.

# CTF Crypto - Modern Cipher Modes and Forgery

## Table of Contents
- [AES-CFB-8 Static IV State Forging](#aes-cfb-8-static-iv-state-forging)
- [ECB Pattern Leakage on Images](#ecb-pattern-leakage-on-images)
- [Padding Oracle Attack](#padding-oracle-attack)
- [CBC-MAC vs OFB-MAC Vulnerability](#cbc-mac-vs-ofb-mac-vulnerability)
- [AES-GCM with Derived Keys](#aes-gcm-with-derived-keys)
- [AES-GCM Nonce Reuse / Forbidden Attack](#aes-gcm-nonce-reuse-forbidden-attack)
- [CBC Padding Oracle Attack](#cbc-padding-oracle-attack)
- [AES Key Recovery via Byte-by-Byte Zeroing Oracle](#aes-key-recovery-via-byte-by-byte-zeroing-oracle)
- [AES-CTR Constant Counter / Repeating Keystream](#aes-ctr-constant-counter-repeating-keystream)
- [AES-CTR Bitflip + CRC Linearity Signature Forgery](#aes-ctr-bitflip-crc-linearity-signature-forgery)
- [AES-CBC Ciphertext Forging via Error-Message Decryption Oracle](#aes-cbc-ciphertext-forging-via-error-message-decryption-oracle)
- [AES-CBC Nonce Strip via Block Boundary Alignment](#aes-cbc-nonce-strip-via-block-boundary-alignment)
- [Compression Oracle / CRIME-Style Attack](#compression-oracle-crime-style-attack)
- [OFB Mode with Invertible RNG Backward Decryption](#ofb-mode-with-invertible-rng-backward-decryption)
- [DES Weak Keys in OFB Mode](#des-weak-keys-in-ofb-mode)
- [Square Attack on Reduced-Round AES](#square-attack-on-reduced-round-aes)
- [AES-ECB Byte-at-a-Time Chosen Plaintext](#aes-ecb-byte-at-a-time-chosen-plaintext)
- [AES-ECB Cut-and-Paste Block Manipulation](#aes-ecb-cut-and-paste-block-manipulation)
- [AES-CBC IV Bit-Flip Authentication Bypass](#aes-cbc-iv-bit-flip-authentication-bypass)
- [CBC IV Forgery + Block Truncation for Authentication Bypass](#cbc-iv-forgery-block-truncation-for-authentication-bypass)
- [Padding Oracle to CBC Bitflip Command Injection](#padding-oracle-to-cbc-bitflip-command-injection)
- [AES-CFB IV Recovery from Timestamp-Seeded PRNG](#aes-cfb-iv-recovery-from-timestamp-seeded-prng)
- [AES-CBC UnicodeDecodeError Side-Channel Oracle](#aes-cbc-unicodedecodeerror-side-channel-oracle)
- [CBC IV Recovery from Block-2 Known Plaintext](#cbc-iv-recovery-from-block-2-known-plaintext)
- [CBC Previous-Block Byte Flipping for Cookie Privilege Escalation](#cbc-previous-block-byte-flipping-for-cookie-privilege-escalation)


-

## AES-CFB-8 Static IV State Forging

**Pattern:** AES-CFB with 8-bit feedback and reused IV allows state reconstruction.

**Key insight:** After encrypting 16 known bytes, the AES internal shift register state is fully determined by those ciphertext bytes. Forge new ciphertexts by continuing encryption from known state.

-

## ECB Pattern Leakage on Images

**Pattern:** AES-ECB on BMP/image data preserves visual patterns.

**Exploitation:** Identical plaintext blocks produce identical ciphertext blocks, revealing image structure even when encrypted. Rearrange or identify patterns visually.

-

## Padding Oracle Attack

**Pattern:** Server reveals whether decrypted padding is valid.

**Byte-by-byte decryption:**
```python
def decrypt_byte(block, prev_block, position, oracle, known):
    """known = bytearray(16) tracking recovered intermediate bytes for this block."""
    for guess in range(256):
        modified = bytearray(prev_block)
        # Set known bytes to produce valid padding
        pad_value = 16 - position
        for j in range(position + 1, 16):
            modified[j] = known[j] ^ pad_value
        modified[position] = guess
        if oracle(bytes(modified) + block):
            return guess ^ pad_value
```

-

## CBC-MAC vs OFB-MAC Vulnerability

OFB mode creates a keystream that can be XORed for signature forgery.

**Attack:** If you have signature for known plaintext P1, forge for P2:
```text
new_sig = known_sig XOR block2_of_P1 XOR block2_of_P2
```

**Important:** Don't forget PKCS#7 padding in calculations! Small bruteforce space? Just try all combinations (e.g., 100 for 2 unknown digits).

**Key insight:** OFB-MAC generates a keystream independent of the plaintext, so knowing one (message, MAC) pair lets you forge MACs for arbitrary messages by XORing the known plaintext blocks out and XORing the new ones in. CBC-MAC does not have this weakness because each block's encryption depends on the previous ciphertext block.

-

## AES-GCM with Derived Keys

**Pattern:** Final decryption step after recovering a secret (e.g., from LWE, key exchange). Session nonce and AES key derived via SHA-256 hashing of the recovered secret.

```python
import hashlib
from Cryptodome.Cipher import AES

# Common key derivation chain:
# 1. Recover secret bytes (s_bytes) from crypto challenge
# 2. Unwrap session nonce: nonce = wrapped_nonce XOR SHA256(s_bytes)[:nonce_len]
# 3. Derive AES key: key = SHA256(s_bytes + session_nonce)
# 4. Decrypt AES-GCM

def decrypt_with_derived_key(s_bytes, wrapped_nonce, ciphertext, aes_nonce, tag, nonce_len=16):
    secret_hash = hashlib.sha256(s_bytes).digest()
    session_nonce = bytes(a ^ b for a, b in zip(wrapped_nonce, secret_hash[:nonce_len]))
    aes_key = hashlib.sha256(s_bytes + session_nonce).digest()
    cipher = AES.new(aes_key, AES.MODE_GCM, nonce=aes_nonce)
    return cipher.decrypt_and_verify(ciphertext, tag)
```

**Key insight:** When AES-GCM authentication fails (`ValueError: MAC check failed`), the derived key is wrong — usually means the upstream secret recovery was incorrect or endianness is swapped.

-

## AES-GCM Nonce Reuse / Forbidden Attack

AES-GCM (Galois/Counter Mode) combines AES-CTR encryption with a GHASH polynomial authentication tag. Reusing a nonce with the same key is catastrophic - it enables both plaintext recovery AND authentication key recovery.

**CTR keystream reuse:** Same nonce = same keystream. XOR two ciphertexts to cancel the keystream: `C1 XOR C2 = P1 XOR P2`. With known plaintext in one message, recover the other.

**GHASH authentication key recovery:** The authentication tag is a polynomial evaluation over GF(2^128). Two messages with the same nonce produce two equations in the same authentication key H. XOR the tag polynomials and factor over GF(2^128) to recover H. With H, forge valid tags for arbitrary messages.

```python
from Crypto.Cipher import AES
from sage.all import GF, PolynomialRing

# Given: two (ciphertext, tag, nonce) pairs with same nonce
# Step 1: Recover plaintext via CTR keystream reuse
keystream = xor(known_plaintext, ciphertext1)
plaintext2 = xor(keystream, ciphertext2)

# Step 2: Recover GHASH auth key H
# Construct tag difference polynomial in GF(2^128)
F = GF(2**128, 'x', modulus=...)  # GCM polynomial
# T1 XOR T2 = P(H) where P is polynomial from ciphertext difference
# Factor P(H) = 0 to find H candidates
# Verify H against known tags

# Step 3: Forge tags for arbitrary messages
# GHASH(H, aad, ciphertext) computed with recovered H
```

**Tool:** [nonce-disrespect](https://github.com/nonce-disrespect/nonce-disrespect) automates GHASH key recovery and tag forgery from nonce-reused GCM ciphertexts.

**Short nonce brute-force:** When GCM uses a short nonce (1-4 bytes), brute-force all nonce values if the key is known. AES-GCM with 1-byte nonce = only 256 candidates.

**Key insight:** AES-GCM is a "one-time nonce" scheme - a single nonce reuse breaks both confidentiality (CTR keystream reuse) AND authenticity. Always check for repeated nonces in GCM challenge traffic.

-

## CBC Padding Oracle Attack

**Pattern:** Server reveals whether CBC-mode ciphertext has valid PKCS#7 padding (via error messages, timing, or status codes). Decrypt any ciphertext block-by-block without the key.

```python
from pwn import *

def padding_oracle(iv, ct):
    """Returns True if server accepts padding."""
    resp = requests.post(URL, data={'iv': iv.hex(), 'ct': ct.hex()})
    return 'padding' not in resp.text.lower()  # or check status code

def decrypt_block(prev_block, target_block):
    """Decrypt one 16-byte block using padding oracle."""
    intermediate = bytearray(16)
    plaintext = bytearray(16)

    for byte_pos in range(15, -1, -1):
        pad_val = 16 - byte_pos
        # Set already-known bytes to produce correct padding
        crafted = bytearray(16)
        for k in range(byte_pos + 1, 16):
            crafted[k] = intermediate[k] ^ pad_val

        for guess in range(256):
            crafted[byte_pos] = guess
            if padding_oracle(bytes(crafted), target_block):
                intermediate[byte_pos] = guess ^ pad_val
                plaintext[byte_pos] = intermediate[byte_pos] ^ prev_block[byte_pos]
                break

    return bytes(plaintext)
```

**Tools:**
```bash
# PadBuster — automated padding oracle exploitation
padbuster http://target/decrypt.php ENCRYPTED_B64 16 \
  -encoding 0 -error "Invalid padding"

# Python: pip install padding-oracle
from padding_oracle import PaddingOracle
oracle = PaddingOracle(block_size=16, oracle_fn=check_padding)
plaintext = oracle.decrypt(ciphertext, iv=iv)
```

**Key insight:** The oracle only needs to distinguish "valid padding" from "invalid padding." This can be a different HTTP status code, error message, response time, or even whether the application processes the request further. A single bit of information per query is sufficient. Decryption requires at most 256 x 16 = 4096 queries per block.

**Detection:** CBC mode encryption + any distinguishable behavior difference on padding errors. Common in cookie encryption, token systems, and encrypted API parameters.

-

## AES Key Recovery via Byte-by-Byte Zeroing Oracle

**Pattern:** When a service allows selective zeroing of key bytes, recover the full AES key by testing one byte at a time.

```python
# Service has key slots and a "regenerate" function with integer overflow
# offset = index * ENTRY_SIZE wraps around, allowing arbitrary byte zeroing

# Strategy: zero bytes progressively, brute-force each unknown byte
for byte_pos in range(16):
    # Zero all bytes EXCEPT byte_pos
    zero_index = (target_offset * modinv(ENTRY_SIZE, 2**32)) % 2**32
    regenerate(zero_index)

    # Key is now: [0,0,...,key[byte_pos],...,0,0]
    # Brute-force the single non-zero byte (256 possibilities)
    known_ct = encrypt(known_pt)
    for guess in range(256):
        test_key = bytes([0]*byte_pos + [guess] + [0]*(15-byte_pos))
        if AES.new(test_key, AES.MODE_ECB).encrypt(known_pt) == known_ct:
            recovered_key[byte_pos] = guess
            break
```

**Key insight:** Integer overflow in `index * ENTRY_SIZE` calculations can target arbitrary memory offsets. By selectively zeroing all-but-one key bytes, the key becomes trivially brute-forceable one byte at a time (256 attempts per byte, 4096 total vs 2^128 for the full key).

-

## AES-CTR Constant Counter / Repeating Keystream

**Pattern:** When an AES-CTR implementation uses `counter=lambda: secret` (a constant function), the counter never increments. AES-CTR with a fixed counter produces the same 16-byte block on every call — equivalent to Vigenère cipher at the byte level with a 16-byte repeating key.

```python
# Constant counter makes CTR equivalent to repeating-key XOR
key_byte = ciphertext_byte ^ known_plaintext_byte
# Apply recovered key bytes across all 16-byte-aligned blocks
for i, ct_byte in enumerate(ciphertext):
    plaintext_byte = ct_byte ^ keystream[i % 16]
```

**Exploit using file format headers:**
1. Identify the file format from context (e.g., `%PDF-1.` for PDF files)
2. XOR the known header bytes against the ciphertext to recover `keystream[0:len(header)]`
3. Iteratively extend: use recovered plaintext to guess the next structural keyword (`endobj`, `/Page`, `stream`, etc.), verify XOR produces consistent ASCII, and extend the keystream further
4. Tool: `otp_pwn` supports interactive block-aligned crib-dragging for this workflow

**Key insight:** Constant AES-CTR counter = repeating 16-byte Vigenère key. Known file format magic bytes bootstrap iterative key recovery via crib-dragging. Any known-plaintext at block-aligned positions reveals the full keystream byte at that position.

-

## AES-CTR Bitflip + CRC Linearity Signature Forgery

**Pattern:** AES-CTR allows targeted plaintext modification via XOR. CRC is linear w.r.t. XOR: `CRC(A ^ B) = CRC(A) ^ CRC(B) ^ CRC(zeros)`. Flip `{admin: 0}` to `{admin: 1}` in ciphertext and fix the encrypted CRC:

```python
import binascii
# X = desired_plaintext XOR original_plaintext (flip bit)
X = b'\x00' * offset + b'\x01' + b'\x00' * remaining
crc_diff = binascii.crc32(X) ^ binascii.crc32(b'\x00' * len(X))
# New ciphertext = old_ciphertext XOR X (for data portion)
# New CRC ciphertext = old_CRC_ciphertext XOR pack(crc_diff)
```

**Key insight:** CRC is GF(2)-linear - XOR-based modifications to plaintext produce predictable CRC changes without knowing the key. When a system uses AES-CTR for confidentiality + CRC for integrity (instead of a proper MAC like HMAC or GCM), you can flip arbitrary plaintext bits and fix the CRC simultaneously. This is a fundamental failure of using CRC as a MAC: CRC detects random errors but provides zero protection against adversarial modification under stream ciphers.

-

### AES-CBC Ciphertext Forging via Error-Message Decryption Oracle

**Pattern:** Server decrypts AES-CBC cookie and displays decrypted value in error messages. Send zero blocks, read decrypted intermediates from error, XOR with desired plaintext to forge ciphertext block-by-block. Use forged ciphertext to deliver blind SQLi payloads through encrypted cookies.

```python
# Forge ciphertext for arbitrary plaintext
for i in range(blocks):
    payload = b'\x00' * 16 * (blocks - 1) + last_forged_block
    response = send_payload(payload)
    decrypted = parse_error_message(response)  # server leaks decrypted bytes
    intermediate = decrypted[-16:]
    new_block = xor(target_plaintext_block, intermediate)
    forged_blocks.append(new_block)
```

**Key insight:** When the server reveals decrypted ciphertext in error messages, you can forge arbitrary plaintext without knowing the key. Send zero IV blocks to learn the intermediate state, then XOR with desired plaintext to produce the correct ciphertext. Build block-by-block from last to first.

-

## AES-CBC Nonce Strip via Block Boundary Alignment

**Pattern:** A server encrypts `nonce | padding | identity | timestamp` with AES-CBC and returns `(iv, ciphertext)`. If the attacker can choose padding such that the first *exactly one* AES block (16 bytes) holds the nonce, then shifting the IV forward by one block — reusing `ciphertext[:16]` as the new IV and `ciphertext[16:]` as the new ciphertext — yields a valid encryption of just `identity | timestamp`. No key is needed because CBC-mode decryption of block 2 is `AES⁻¹(c[16:32]) XOR c[0:16]`, which is exactly the identity-and-timestamp plaintext once the nonce block is promoted to IV.

```python
from Crypto.Cipher import AES
import os

key = os.urandom(16)

# Server builds plaintext and encrypts
def encrypt_with_nonce(identity, timestamp):
    nonce = os.urandom(8)
    padding = b"\x00" * 8          # brings nonce + padding to 16 bytes
    plaintext = nonce + padding + identity + timestamp
    iv = os.urandom(16)
    ct = AES.new(key, AES.MODE_CBC, iv).encrypt(plaintext)
    return iv, ct

iv, ct = encrypt_with_nonce

# Attacker rewrites (iv', ct') to drop the nonce block
new_iv = ct[:16]
new_ct = ct[16:]
recovered = AES.new(key, AES.MODE_CBC, new_iv).decrypt(new_ct)
assert recovered.startswith(b"admin")
```

**Key insight:** CBC's IV is only consulted for the first block — every subsequent block uses the previous ciphertext as its "IV". That means any contiguous slice of a CBC ciphertext is itself a valid CBC ciphertext if you promote the preceding block (or a supplied IV) to the new IV. Whenever a fixed-size header (nonce, magic bytes, counter) occupies exactly one block, the attacker can strip it by reusing that block as an IV. Defend by binding the header into the authentication tag (AEAD) or including its offset in an HMAC.

## Compression Oracle / CRIME-Style Attack

**Pattern:** Server compresses plaintext (LZW, zlib, etc.) before encrypting. By observing ciphertext length changes with chosen plaintexts, leak the unknown plaintext character-by-character.

```python
import base64

def oracle(plaintext):
    """Send chosen plaintext, get ciphertext length."""
    resp = send_to_server(plaintext)
    return len(base64.b64decode(resp))

# Baseline: empty input
base_len = oracle("")

# Recover secret byte-by-byte
known = ""
for pos in range(secret_length):
    for c in string.printable:
        candidate = known + c
        length = oracle(candidate)
        if length <= base_len + len(known):  # Compressed = match
            known += c
            break
```

**Key insight:** Compression algorithms (LZW, DEFLATE, zlib) replace repeated sequences with back-references. If `SALT + user_input` is compressed before encryption, sending input that matches part of the salt produces shorter ciphertext (the match compresses). This is the same class as CRIME (TLS), BREACH (HTTP), and HEIST attacks. The oracle is ciphertext length.

-

## OFB Mode with Invertible RNG Backward Decryption

**Pattern:** A custom block cipher uses OFB (Output Feedback) mode with a homemade RNG as the keystream generator. The last plaintext block is known (zero padding), leaking one RNG state. If the RNG's state transition function is invertible (bijective), all previous states can be recovered by running the RNG backwards, decrypting the entire ciphertext from the end to the beginning.

```python
def rng_forward(state):
    """Custom RNG state transition (from challenge)."""
    # Example: linear congruential or reversible mixing
    return (state * A + B) % M

def rng_inverse(state):
    """Inverted RNG — recover previous state."""
    return ((state - B) * pow(A, -1, M)) % M

# Last block is zero-padded → ciphertext XOR 0 = keystream = RNG state
leaked_state = int.from_bytes(ciphertext_blocks[-2], 'big')

# Decrypt backwards
state = leaked_state
plaintext_blocks = []
for i in range(len(ciphertext_blocks) - 3, -1, -1):
    state = rng_inverse(state)
    pt = xor_bytes(ciphertext_blocks[i], state.to_bytes(block_size, 'big'))
    plaintext_blocks.insert(0, pt)
```

**Key insight:** OFB mode decouples encryption from the plaintext — the keystream is deterministic from the initial state. If ANY block's plaintext is known (padding, headers, magic bytes), the corresponding RNG state is leaked. An invertible RNG then reveals ALL states. Always check if the RNG transition function has a mathematical inverse.

**When to recognize:** Custom OFB/CTR mode with a non-standard PRNG. Look for: (1) XOR-based encryption, (2) a state-update function that's bijective (no information loss), (3) predictable plaintext in any block position. Files with known padding (PKCS#7 zero-fill, null-terminated strings) are ideal leak points.

-

## DES Weak Keys in OFB Mode

**Pattern:** DES has 4 weak keys where `E(E(P,K),K) = P` (encryption is self-inverse). In OFB (Output Feedback) mode this causes the keystream to cycle with period 2: even blocks XOR with IV, odd blocks with E(IV,K). Reduces to a 16-byte repeating XOR key.

```python
# DES weak keys: 0x0000000000000000, 0xFFFFFFFFFFFFFFFF,
#                0xE1E1E1E1F0F0F0F0, 0x1E1E1E1E0F0F0F0F
# OFB with weak key: keystream = [IV, E(IV,K), IV, E(IV,K),...]
# Recovery: try all 4 weak keys; or treat as 16-byte repeating XOR
```

**Key insight:** DES weak keys cause OFB keystream to cycle with period 2. When you see DES+OFB, always try the 4 weak keys first.

-

## Square Attack on Reduced-Round AES

**Pattern:** 4-round AES is vulnerable to the square (integral) attack. Choose 256 plaintexts differing in one byte (a "lambda set"). After 3 rounds, the XOR sum at any byte position epublic source 0. Guess one byte of the last round key and partially decrypt - if XOR sum is 0, the guess is correct.

```python
# For each byte position in the last round key:
for candidate in range(256):
    xor_sum = 0
    for ct in ciphertexts:
        xor_sum ^= inv_sub_bytes(ct[pos] ^ candidate)
    if xor_sum == 0:
        key_byte = candidate  # correct guess
# Reduces 2^128 key recovery to ~16 * 256 = 4096 operations
```

**Key insight:** Integral cryptanalysis exploits the "balanced" property (XOR-sum = 0) that propagates through AES rounds. Effective against 4-round AES; 5+ rounds require more sophisticated variants.

-

## AES-ECB Byte-at-a-Time Chosen Plaintext

**Pattern:** Server encrypts `user_input || secret_suffix` under AES-ECB. Recover the secret suffix one byte at a time by controlling the input length.

1. Send inputs of decreasing length to push one unknown byte into a known block position
2. For each position, try all 256 byte values and compare the encrypted block:

```python
from pwn import *
import cryptanalib as ca  # FeatherDuster's cryptanalib

def oracle(pt):
    """Send plaintext, receive ECB-encrypted ciphertext."""
    r = remote('target', 7765)
    r.recvuntil('Send me some hex-encoded data to encrypt:\n')
    r.sendline(pt.hex())
    r.recvuntil('Here you go:')
    ct = bytes.fromhex(r.recvline().strip().decode())
    r.close()
    return ct

# Automated byte-at-a-time recovery
flag = ca.ecb_cpa_decrypt(oracle, block_size=16, verbose=True)
print(flag)
```

**Manual approach without library:**
```python
block_size = 16
known = b''

for i in range(len(secret)):
    # Pad so next unknown byte is at end of a block
    pad_len = block_size - 1 - (len(known) % block_size)
    pad = b'A' * pad_len

    # Get target block
    target_ct = oracle(pad)
    target_block_idx = (pad_len + len(known)) // block_size
    target_block = target_ct[target_block_idx*16:(target_block_idx+1)*16]

    # Try all 256 byte values
    for byte_val in range(256):
        test = pad + known + bytes([byte_val])
        test_ct = oracle(test)
        if test_ct[target_block_idx*16:(target_block_idx+1)*16] == target_block:
            known += bytes([byte_val])
            break
```

**Key insight:** ECB mode encrypts identical plaintext blocks to identical ciphertext blocks. By controlling the prefix length, the attacker shifts one unknown byte at a time to a position where it completes a known block prefix. Comparing the target ciphertext block against all 256 possibilities recovers each byte in at most 256 queries. Total queries: ~256 * secret_length. Tool: FeatherDuster's `cryptanalib.ecb_cpa_decrypt()` automates this completely.

-

## AES-ECB Cut-and-Paste Block Manipulation

**Pattern:** Server encrypts JSON session data in AES-ECB mode. Fields like `is_admin: false` span predictable block boundaries. Construct chosen plaintext blocks via registration, then splice ciphertext blocks to change `false` to `true`.

1. Detect ECB mode: register with repeating username (e.g., 'A' * 64), look for identical ciphertext blocks
2. Map block boundaries by varying username length until block count changes
3. Determine field ordering by independently varying username and email lengths
4. Craft target block containing `true` by aligning it at a block boundary via padding:

```python
# Align "true" at start of a block using space padding (JSON ignores whitespace)
# Original:  {"username": "AA", "is_admin": false, "email": ""}
# Target:    {"username": "AA", "is_admin":            true, "email": ""}
#                                              ^- 16-byte block boundary

# Get the "            true" block from:
username = "AAA" + " " * 12 + "true"
# Extract block 2 of the resulting ciphertext

# Get prefix blocks from a short username
# Get suffix block from a padded username
# Concatenate: prefix_blocks + true_block + suffix_block
```

**Key insight:** AES-ECB encrypts each 16-byte block independently with no chaining. Identical plaintext blocks produce identical ciphertext blocks, allowing block-level cut-and-paste. JSON's tolerance for extra whitespace enables block alignment without breaking parsing. The attack requires: (a) detecting ECB via repeated blocks, (b) mapping field layout via length probing, (c) crafting and splicing blocks.

-

## AES-CBC IV Bit-Flip Authentication Bypass

**Pattern:** Server encrypts JSON session blob under AES-CBC and returns both IV and ciphertext as a cookie. No integrity check (no MAC/HMAC). Flip bits in the IV to change the first plaintext block.

1. Register with username one bit away from target (e.g., `` `dmin `` instead of `admin` — flip LSB of 'a')
2. Identify the IV byte position corresponding to the target character in the first block
3. Flip the same bit in the IV byte — XOR propagates directly to the plaintext:

```python
import binascii
cookie = binascii.unhexlify(auth_cookie)
iv = bytearray(cookie[:16])
ciphertext = cookie[16:]

# Flip LSB of byte at position where 'a'/'`' appears in first block
# Position depends on JSON structure: {"username":"`dmin"}
# 'a' (0x61) vs '`' (0x60) differ only in bit 0
target_pos = 13  # position of first char of username in block
iv[target_pos] ^= 0x01

forged = binascii.hexlify(bytes(iv) + ciphertext)
```

**Key insight:** AES-CBC decryption XORs the previous ciphertext block (or IV for block 0) with the AES-decrypted block. Flipping bit `i` in the IV flips bit `i` in the first plaintext block with no other side effects. This only works when the server performs no integrity verification (no HMAC, AEAD, or authenticated encryption).

-

## CBC IV Forgery + Block Truncation for Authentication Bypass

**Pattern:** Service encrypts `MD5(padded_name) || padded_name` with AES-CBC. The MD5 serves as an integrity check on login. Two attacks combine: (1) IV manipulation: XOR IV bytes to change the decrypted first block from the source MD5 to the target MD5. (2) Block truncation: register with `pad("admin") + 16_junk_bytes`, then strip trailing ciphertext blocks — AES-CBC has no length field, so shorter ciphertext decrypts validly if PKCS7 padding is correct.

```python
# Forge IV to flip MD5 from registered user to "admin"
source_md5 = md5(pad("admin") + b"A"*16)
target_md5 = md5(pad("admin"))
new_iv = bytes(a ^ b ^ c for a, b, c in zip(original_iv, source_md5, target_md5))

# Strip last 2 blocks (junk + PKCS padding block)
forged_token = new_iv + ciphertext[16:-32]
```

**Key insight:** AES-CBC decryption has no built-in length integrity. Truncating ciphertext blocks from the end is valid as long as the new last block decrypts to valid PKCS7 padding. Combined with IV manipulation of block 0, this forges arbitrary first-block content.

-

## Padding Oracle to CBC Bitflip Command Injection

**Pattern:** Encrypted commands passed via URL parameter. Error messages reveal padding validity (padding oracle). Chain two attacks: (1) Padding oracle recovers the plaintext of the encrypted command. (2) CBC bitflipping modifies a ciphertext block to inject shell metacharacters (`;$(cmd)`) into the decrypted command, achieving RCE through crypto manipulation alone.

```python
# Step 1: Padding oracle recovers plaintext
plaintext = padding_oracle_decrypt(ciphertext, oracle_fn)

# Step 2: CBC bitflip — modify block N-1 to change decrypted block N
target_block = 5
desired = b';$(cat *.txt)   '  # 16 bytes, pad with spaces
original = plaintext[target_block * 16:(target_block + 1) * 16]
ct = bytearray(bytes.fromhex(ciphertext))
for i in range(16):
    ct[(target_block - 1) * 16 + i] ^= original[i] ^ desired[i]
forged = ct.hex()
```

**Key insight:** Padding oracle and CBC bitflipping are usually taught separately. Chaining them converts a pure cryptographic weakness into full command injection: the oracle recovers plaintext needed to compute the XOR mask, and the bitflip injects the payload.

-

## AES-CFB IV Recovery from Timestamp-Seeded PRNG

**Pattern:** Ransomware encrypts files with AES-CFB using a hardcoded password from bash_history. The IV is derived from `random.choice()` seeded with `int(time())` at encryption time. The file's mtime (preserved by the filesystem) epublic source the exact seed used, enabling full decryption without the private key.

```python
import random, os, string, base64
from Crypto.Cipher import AES

password = b'hardcoded_password_from_bash_history'
img = 'encrypted_file.enc'

# File mtime IS the random seed used at encryption time
random.seed(int(os.stat(img).st_mtime))
iv = ''.join(random.choice(string.letters + string.digits) for _ in range(16))

aes = AES.new(password, AES.MODE_CFB, iv.encode())
with open(img, 'rb') as f:
    ciphertext = base64.b64decode(f.read())
plaintext = aes.decrypt(ciphertext)
```

**Key insight:** PRNG seeded with `time()` at encryption time leaks the seed via the filesystem mtime. Always check Python version compatibility — Python 2 and Python 3 have different `random` module implementations producing different sequences from the same seed. The `-it` flag on `cp`/`mv` may reset mtime; work from the original unmodified file.

-

## AES-CBC UnicodeDecodeError Side-Channel Oracle

**Pattern:** Server decrypts AES-CBC ciphertext and attempts to UTF-8 decode the result. Invalid UTF-8 sequences raise a `UnicodeDecodeError` (or equivalent). This error is distinguishable from other errors (e.g., application-level errors), creating a decryption oracle analogous to a padding oracle.

**Attack:** Standard CBC bit-flip oracle technique, using UTF-8 validity as the distinguisher:
1. For each target plaintext byte at position `i` in block `b`, modify byte `i` in block `b-1`
2. Cycle through all 256 XOR values; when the decrypted byte produces valid UTF-8 in context, the server returns a non-`UnicodeDecodeError` response
3. From the XOR value that passes and the known modification to `c[b-1][i]`, recover `plaintext[b][i]`

```python
# CBC bit-flip oracle using UTF-8 validity
for guess in range(256):
    modified = bytearray(prev_block)
    modified[pos] = known_intermediate[pos] ^ guess  # produce desired output byte
    if not unicode_error(modified_block + target_block):
        plaintext_byte = guess  # valid UTF-8 at this position
        break
```

**Key insight:** Any error that distinguishes valid from invalid plaintext content serves as a decryption oracle — not just PKCS#7 padding errors. UTF-8 validity, base64 decodability, JSON parsability, and ASCII-only constraints are all valid oracle conditions. The only requirement is a server-side distinguishable response.

-

### CBC IV Recovery from Block-2 Known Plaintext

**Pattern:** AES-CBC given: full ciphertext, known plaintext from block 2 onward, partial key. Recover the missing IV by first brute-forcing missing key bytes via block 2 (which does not depend on the IV), then XOR plaintext[0] with `AES_decrypt(ct[0], K)` to get the IV.

```python
for tail in itertools.product(string.printable, repeat=2):
    K = base_key + ''.join(tail).encode()
    if AES.new(K, AES.MODE_ECB).decrypt(ct)[16:32] == plaintext[16:32]:
        raw = AES.new(K, AES.MODE_ECB).decrypt(ct[:16])
        IV = bytes(a ^ b for a, b in zip(raw, plaintext[:16]))
        break
```

**Key insight:** Block 2 of CBC decrypts with `prev_ct XOR raw_decrypt` where `prev_ct` is from the ciphertext itself — IV-independent. Use it to recover the key first, then XOR back to the IV.

-

## CBC Previous-Block Byte Flipping for Cookie Privilege Escalation

**Pattern:** Server stores `{"username": "...", "admin": 0,...}` encrypted with AES-CBC + base64, returned as a cookie. No MAC. To escalate from `admin: 0` to `admin: 1`, locate the byte offset of `'0'` inside some plaintext block `P_{n+1}`, then XOR the corresponding byte in the *previous* ciphertext block `C_n` with `ord('0') ^ ord('1')`. The attacker block `C_n` decrypts to garbage (which may break the preceding JSON field), but the targeted byte in `P_{n+1}` flips cleanly because `P_{n+1} = AES_dec(C_{n+1}) XOR C_n`.

```python
from base64 import b64encode, b64decode

cookie = b64decode(stolen_cookie)              # IV || C1 || C2 ||... (or C0||... )
buf    = bytearray(cookie)

# Block layout for plaintext {'username': '', 'admin': 0, 'password': ''}:
#   block 1: "{'username': '',"      <- will decrypt to garbage after flip
#   block 2: " 'admin': 0, 'pa"      <- target byte 10 (the '0')
#   block 3: "ssword': ''}"

# To flip byte 10 of plaintext block 2, XOR byte 10 of ciphertext block 1.
# With IV-prefixed layout: index = 16 (IV) + 0*16 (C1) + 10 = 26
#   (or 0*16 + 10 = 10 if there is no separate IV prepended)
offset = 10
buf[offset] ^= ord('0') ^ ord('1')             # 0x30 ^ 0x31 = 0x01

forged_cookie = b64encode(bytes(buf)).decode()
```

**Key insight:** In AES-CBC, `P_{n+1} = AES_dec(C_{n+1}) XOR C_n`. Flipping byte `i` of `C_n` flips byte `i` of `P_{n+1}` with zero side effects on `P_{n+1}`, but turns `P_n` (which was `AES_dec(C_n) XOR C_{n-1}`) into pseudo-random garbage. Works whenever the server (a) uses CBC without integrity checks, (b) parses the JSON/cookie leniently enough to tolerate a corrupted earlier block (unknown-key field, ignored garbage, lenient JSON parser), and (c) exposes the block boundary offset of the target byte. Contrast with [AES-CBC IV Bit-Flip], which targets block 0 by flipping the IV and leaves all later blocks intact.
