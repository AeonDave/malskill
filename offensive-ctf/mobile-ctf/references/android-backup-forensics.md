# Android Backup Forensics

Reference for extracting and analyzing Android backup (.ab) files in CTF challenges.

---

## Android backup format

```
Header (ASCII):
  "ANDROID BACKUP\n"  →  15 bytes
  "<version>\n"       →  2 bytes (e.g., "5\n")
  "<compressed>\n"    →  2 bytes ("1\n" = zlib compressed)
  "<encryption>\n"    →  5 bytes ("none\n" = no encryption)
  Total typical header = 24 bytes

Body:
  zlib-compressed tar archive containing:
    apps/<package>/_manifest        — app metadata
    apps/<package>/sp/*.xml         — SharedPreferences
    apps/<package>/db/*.db          — SQLite databases
    apps/<package>/f/*              — app files
    shared/0/Pictures/              — device photos
    shared/0/DCIM/                  — camera roll
    shared/0/Download/              — downloads
```

---

## Extraction workflow

```bash
# Step 1: Read header to find exact byte count
python3 -c "
with open('backup.ab', 'rb') as f:
    h = f.read(60)
print(repr(h))
# Count bytes up to and including the last \n before zlib data
"

# Step 2: Locate zlib start (0x78 0xDA or 0x78 0x9C or 0x78 0x01)
python3 -c "
with open('backup.ab', 'rb') as f:
    data = f.read(200)
for i, b in enumerate(data):
    if b == 0x78 and data[i+1] in (0xda, 0x9c, 0x01):
        print(f'zlib magic at byte {i}')
        break
"

# Step 3: Extract with exact header skip
SKIP=24  # or whatever the header byte count is
dd if=backup.ab bs=$SKIP skip=1 2>/dev/null \
  | python3 -c "import sys,zlib; sys.stdout.buffer.write(zlib.decompress(sys.stdin.buffer.read()))" \
  > backup.tar

# Verify tar
file backup.tar    # should show: POSIX tar archive

# Step 4: Extract
mkdir extracted && tar xf backup.tar -C extracted/
```

---

## Triage after extraction

### Fast flag search

```bash
# Plain text
grep -r "flag{" extracted/ 2>/dev/null

# Binary search (flag in SQLite, images, or binary app data)
python3 -c "
import os, re
for root, _, files in os.walk('extracted/'):
    for fn in files:
        p = os.path.join(root, fn)
        try:
            d = open(p,'rb').read()
            for m in re.findall(b'HTB\{[^}]{1,60}\}', d):
                print(p, m)
        except: pass
"
```

### SharedPreferences XML

```bash
find extracted/apps/ -name "*.xml" | sort
cat extracted/apps/<package>/sp/<package>.xml
# Look for: account tokens, auth keys, saved PINs, sensitive settings
```

### SQLite databases

```python
import sqlite3, os

for root, _, files in os.walk('extracted/'):
    for fn in files:
        if fn.endswith('.db') and not fn.endswith('-shm') and not fn.endswith('-wal'):
            db = os.path.join(root, fn)
            try:
                con = sqlite3.connect(db)
                tables = con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
                for (t,) in tables:
                    rows = con.execute(f'SELECT * FROM "{t}" LIMIT 5').fetchall()
                    if rows:
                        print(f'{db} [{t}]:', rows[:2])
            except: pass
```

### Image inspection

**Critical pattern (Cat/Easy Leaks style):** The flag may be physically printed on a document that the device owner photographed. Not steganography — just look at the image content.

```bash
# List all images by size (largest first = most likely interesting)
find extracted/ -name "*.jpg" -o -name "*.png" | xargs ls -lh | sort -k5 -rh | head -20

# View images — check for document photos, printed text, credentials on paper
# Use a multimodal LLM or image viewer

# Crop and zoom on suspicious documents in photos
python3 -c "
from PIL import Image
img = Image.open('IMAG0004.jpg')
print(img.size)
# Crop to document area, enlarge, save for reading
crop = img.crop((400, 1500, 2000, 3500))
crop = crop.resize((crop.width*2, crop.height*2))
crop.save('/tmp/doc_zoom.jpg')
"

# EXIF metadata (GPS, camera model, timestamp)
python3 -c "
from PIL import Image
from PIL.ExifTags import TAGS
img = Image.open('photo.jpg')
exif = img._getexif()
if exif:
    for tag_id, val in exif.items():
        print(TAGS.get(tag_id, tag_id), val)
"
```

---

## Common backup contents by app package

| Package | Interesting content |
|---------|-------------------|
| `com.android.contacts` | Google account email, contact data |
| `com.android.inputmethod.latin` | Keyboard user dictionary (typed words) |
| `com.android.dialer` | Call history, voicemail metadata |
| `com.android.providers.telephony` | SMS messages (if backed up) |
| `com.example.android.notepad` | Notes app — may have flag as note content |
| `com.google.android.*` | Gmail token, Maps history |
| Custom app package | App-specific data — check DB and SP |

---

## Encrypted backup (.ab with AES-256)

If encryption is set:
```
Header ends with: "AES-256\n"
Followed by: salt, IV, rounds, key material
```

Extract with Android Backup Extractor (ABE):
```bash
# https://github.com/nelenkov/android-backup-extractor
java -jar abe.jar unpack backup.ab backup.tar <password>
# or brute-force with wordlist
```
