# Autopsy — Deep Reference

## Windows Registry Artifact Map

High-value registry keys for investigation. Extract hive from disk image → analyze with RegRipper or Registry Explorer.

### Startup / Persistence

```
HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Run
HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce
HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\Run
HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce
HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon  → Userinit, Shell
HKLM\SYSTEM\CurrentControlSet\Services                       → services + drivers
HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Image File Execution Options  → debugger hijack
```

### User Activity

```
NTUSER.DAT\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\RecentDocs
NTUSER.DAT\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\RunMRU        → run dialog history
NTUSER.DAT\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\TypedPaths    → Explorer typed paths
NTUSER.DAT\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\ComDlg32\OpenSavePidlMRU
NTUSER.DAT\SOFTWARE\Microsoft\Windows\CurrentVersion\Search\RecentApps
```

### Program Execution Evidence

```
HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\AppCompatCache   → ShimCache (programs run)
HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\AppCompatFlags\Layers
NTUSER.DAT\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\UserAssist   → GUI execution count + timestamp
```

### Network / Connection History

```
HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\NetworkList\Profiles   → past WiFi/Ethernet
HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\NetworkList\Signatures
HKCU\SOFTWARE\Microsoft\Terminal Server Client\Default                   → RDP targets
HKCU\SOFTWARE\Microsoft\Terminal Server Client\Servers                   → RDP credentials
```

### USB / Device History

```
HKLM\SYSTEM\CurrentControlSet\Enum\USBSTOR     → USB storage history (serial numbers)
HKLM\SYSTEM\CurrentControlSet\Enum\USB         → all USB devices
HKLM\SOFTWARE\Microsoft\Windows Portable Devices
```

### Credentials / Autologon

```
HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon  → DefaultUserName, DefaultPassword
HKLM\SECURITY\Policy\Secrets                                 → LSA secrets (needs SYSTEM)
HKLM\SAM\SAM\Domains\Account\Users                           → local account hashes
```

---

## Hive Extraction from Disk Image

```bash
# After mounting image or using TSK:

# Find hive inodes
fls -r -o 2048 disk.img | grep -i "ntuser.dat\|system\|sam\|security\|software"

# Extract specific hive
icat -o 2048 disk.img <INODE> > system.hive

# Parse with RegRipper (Linux)
sudo apt install libregf-utils
regripper -r system.hive -f system > system_report.txt

# Parse with python-registry
pip install python-registry
python3 -c "
from Registry import Registry
reg = Registry.Registry('system.hive')
key = reg.open('ControlSet001\\Services')
for subkey in key.subkeys():
    print(subkey.name())
"
```

---

## Email Artifact Analysis

Autopsy's Email Parser module handles:

| Format | Container | Key data |
|--------|-----------|---------|
| Outlook | `.pst` / `.ost` | From, To, Subject, Body, Attachments |
| Mozilla | `.mbox` | Raw RFC822 messages |
| Thunderbird | `prefs.js` + mail dir | Account info + messages |

```bash
# Extract PST offline with readpst
sudo apt install pst-utils
readpst outlook.pst -o pst_output/

# Parse extracted mbox
python3 -c "
import mailbox
for msg in mailbox.mbox('Inbox'):
    print('From:', msg['From'])
    print('Subject:', msg['Subject'])
    print('---')
"

# Find email-related files in image
fls -r -o 2048 disk.img | grep -iE "\.pst$|\.ost$|\.mbox$|\.eml$|\.msg$"
```

---

## Steganography Detection Workflow

```bash
# After Autopsy extracts image files:

# 1. Check file sizes (stego images often larger than expected)
ls -la *.jpg *.png | sort -k5 -n

# 2. Check with steghide (password-protected stego)
steghide extract -sf suspicious.jpg  # prompt for password
steghide info suspicious.jpg

# 3. zsteg for PNG/BMP LSB stego
sudo gem install zsteg
zsteg suspicious.png
zsteg -a suspicious.png   # try all methods

# 4. stegsolve / stegoveritas (visual analysis)
stegoveritas suspicious.png

# 5. strings in image
strings suspicious.jpg | grep -iE "flag|key|pass|hidden"

# 6. binwalk — files hidden inside image
binwalk suspicious.jpg
binwalk -e suspicious.jpg -C extracted/
```

---

## Python: Post-Extraction Analysis

```python
# Scan all extracted files for flag patterns
import os, re

FLAG_PATTERN = re.compile(rb'flag\{[^\}]+\}', re.IGNORECASE)

def scan_dir(path):
    for root, dirs, files in os.walk(path):
        for f in files:
            fp = os.path.join(root, f)
            try:
                with open(fp, 'rb') as fh:
                    data = fh.read()
                    matches = FLAG_PATTERN.findall(data)
                    if matches:
                        print(f"[MATCH] {fp}")
                        for m in matches:
                            print(f"  → {m.decode(errors='replace')}")
            except Exception:
                pass

scan_dir('/path/to/autopsy/extracted/')
```

---

## Volume Shadow Copy Analysis

```bash
# VSS from Windows image — often contains previous file versions
# Mount image, then:
fls -r -o 2048 disk.img | grep -i "shadow"

# Or access VSS via Autopsy: Tools → Volume Shadow Copies (Windows only)
# On Linux: vss-mounter or libvshadow
sudo apt install libvshadow-utils
vshadowmount disk.img /mnt/vss/
ls /mnt/vss/   # vss1, vss2, ...
mount -o ro,offset=$((2048*512)) /mnt/vss/vss1 /mnt/shadow1
```

---

## Browser Artifact Locations

| Browser | Profile path | Key artifacts |
|---------|-------------|---------------|
| Chrome | `Users\<user>\AppData\Local\Google\Chrome\User Data\Default\` | History, Cookies, Login Data, Downloads |
| Firefox | `Users\<user>\AppData\Roaming\Mozilla\Firefox\Profiles\*.default\` | places.sqlite, cookies.sqlite, logins.json |
| Edge | `Users\<user>\AppData\Local\Microsoft\Edge\User Data\Default\` | History, Cookies, Login Data |
| IE | `Users\<user>\AppData\Local\Microsoft\Windows\WebCache\WebCacheV01.dat` | History, cookies |

```bash
# Extract Chrome history (SQLite)
sqlite3 "History" "SELECT url, title, visit_count, last_visit_time FROM urls ORDER BY last_visit_time DESC LIMIT 50;"

# Chrome saved passwords (encrypted — needs DPAPI or mimikatz)
sqlite3 "Login Data" "SELECT origin_url, username_value FROM logins;"

# Firefox history
sqlite3 places.sqlite "SELECT url, title, visit_count FROM moz_places ORDER BY frecency DESC LIMIT 50;"
```
