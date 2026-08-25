# APK Crypto Patterns

Common cryptographic secret patterns in Android CTF challenges and how to extract and decrypt them.

---

## Contents

- [Trace the complete key dataflow](#trace-the-complete-key-dataflow)
- [Pattern 1 — AES with hardcoded SecretKeySpec](#pattern-1--aes-with-hardcoded-secretkeyspec-most-common)
- [Pattern 2 — Base64-encoded string](#pattern-2--base64-encoded-string-trivial)
- [Pattern 3 — XOR with hardcoded key](#pattern-3--xor-with-hardcoded-key)
- [Pattern 4 — RSA with hardcoded private key](#pattern-4--rsa-with-hardcoded-private-key-in-assets)
- [Pattern 5 — Android Keystore / Tee-backed keys](#pattern-5--android-keystore--tee-backed-keys)
- [Pattern 6 — Firebase Realtime Database public read](#pattern-6--firebase-realtime-database-public-read)
- [Quick crypto identification from DEX strings](#quick-crypto-identification-from-dex-strings)

## Trace the complete key dataflow

Follow source literal/response field → hex/Base64 decode → hash/substring/concat → repeat/pad/truncate → charset encoding → cipher mode, IV, and feedback width. Keep text and bytes distinct, record intermediate lengths/prefixes, and validate each layer independently. Never replace the application's key builder with generic zero-padding or hashing.

## Pattern 1 — AES with hardcoded SecretKeySpec (most common)

**Indicators in jadx/strings:**
- `SecretKeySpec` class reference in DEX strings
- `Cipher.getInstance("AES/ECB/PKCS5Padding")` or `"AES/CBC/PKCS7Padding"`
- A short string literal (8–32 chars) passed directly to SecretKeySpec constructor
- Encrypted byte array or Base64 string in the same class

**Extraction:**
```bash
# From unzipped APK:
strings classes.dex | grep -E "^[A-Za-z0-9!@#$%^&*]{8,32}$" | head -20
# or from jadx output:
grep -r "SecretKeySpec\|\"AES" jadx_out/ -A3 | head -40
```

**Decrypt — AES ECB:**
```python
from Crypto.Cipher import AES
import base64

key = b'<exact_16_24_or_32_byte_key>'  # reproduce the app's derivation exactly

ct = base64.b64decode('...')         # ciphertext from app resources or DEX
cipher = AES.new(key, AES.MODE_ECB)
pt = cipher.decrypt(ct)
# Strip PKCS7 padding
pad = pt[-1]; pt = pt[:-pad]
print(pt.decode())
```

**Java AES/CFB/NoPadding:** confirm the provider's feedback width. PyCryptodome defaults CFB to 8 bits; use `segment_size=128` only when the Java/Android provider resolves the transformation to full-block CFB (`CFB8` maps to 8). `NoPadding` means do not PKCS#5/#7-unpad. Preserve the exact 16-byte IV and ciphertext length, then validate by re-encryption or a known ciphertext. If Java repeats an input until 32 characters, truncates to 32, then UTF-8 encodes it, reproduce that exact sequence.

```python
from Crypto.Cipher import AES

def decrypt_java_cfb(seed: str, iv: bytes, ciphertext: bytes, *, segment_size: int) -> bytes:
    """Pass the exact IV/ciphertext bytes recovered from the application."""
    key = (seed * ((32 + len(seed) - 1) // len(seed)))[:32].encode("utf-8")
    return AES.new(key, AES.MODE_CFB, iv=iv, segment_size=segment_size).decrypt(ciphertext)

# Use segment_size=128 only after confirming full-block CFB in the Java provider.
pt = decrypt_java_cfb(recovered_seed, recovered_iv, recovered_ciphertext, segment_size=128)
```

**Decrypt — AES CBC:**
```python
from Crypto.Cipher import AES
import base64

key = b'<16_or_32_byte_key>'
iv  = b'<16_byte_iv>'          # often hardcoded adjacent to key
ct  = base64.b64decode('...')

cipher = AES.new(key, AES.MODE_CBC, iv=iv)
pt = cipher.decrypt(ct)
pad = pt[-1]; pt = pt[:-pad]
print(pt.decode())
```

---

## Pattern 2 — Base64-encoded string (trivial)

```bash
strings classes.dex | grep -E "^[A-Za-z0-9+/]{20,}={0,2}$" | while read b; do
  echo "$b" | base64 -d 2>/dev/null | grep -a "flag{"
done
```

---

## Pattern 3 — XOR with hardcoded key

```python
key = b'<xor_key>'
ct  = bytes.fromhex('<hex_ciphertext>')
pt  = bytes(c ^ key[i % len(key)] for i, c in enumerate(ct))
print(pt)
```

---

## Pattern 4 — RSA with hardcoded private key in assets

```bash
find apk_out/assets/ -name "*.pem" -o -name "*.key" -o -name "private*"
# Decrypt with openssl or Python cryptography library
```

---

## Pattern 5 — Android Keystore / Tee-backed keys

These are NOT extractable statically — they live in hardware. Requires Frida hooking.

```javascript
// Frida: hook Cipher.doFinal to capture plaintext output
Java.perform(function() {
    var Cipher = Java.use('javax.crypto.Cipher');
    Cipher.doFinal.overload('[B').implementation = function(ct) {
        var result = this.doFinal(ct);
        console.log('[Cipher.doFinal] PT: ' + Java.array('byte', result));
        return result;
    };
});
```

---

## Pattern 6 — Firebase Realtime Database public read

```bash
# Extract project ID from google-services.json or strings
strings classes.dex | grep "firebaseio\|firebase.app"
# Test public access
curl "https://<project_id>.firebaseio.com/.json"
curl "https://<project_id>.firebaseio.com/flags.json"
```

---

## Quick crypto identification from DEX strings

```bash
# Run these on classes.dex after unzip
strings classes.dex | grep -E "AES|DES|RSA|SHA|HMAC|Cipher|KeySpec|encrypt|decrypt" | sort -u | head -20
strings classes.dex | grep -E "^[A-Za-z0-9+/]{16,}={0,2}$" | sort -u | head -10
```
