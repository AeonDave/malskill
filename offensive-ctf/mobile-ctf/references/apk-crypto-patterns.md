# APK Crypto Patterns

Common cryptographic secret patterns in Android CTF challenges and how to extract and decrypt them.

---

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

key = b'LmBf5G6h9j'                 # 10-byte key → padded or truncated by impl
# if key is shorter than 16 bytes, check if app pads it:
key_padded = key.ljust(16, b'\x00')  # zero-pad to 16 bytes

ct = base64.b64decode('...')         # ciphertext from app resources or DEX
cipher = AES.new(key_padded, AES.MODE_ECB)
pt = cipher.decrypt(ct)
# Strip PKCS7 padding
pad = pt[-1]; pt = pt[:-pad]
print(pt.decode())
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
