# Source Coverage Map

This map is the no-loss checklist for the imported source material. Each file listed here has a debrandized preservation copy under `references/imported/`.

- Source skill: `ctf-forensics`
- Target skill: `forensics-ctf`
- Preserved files: 15

## Imported files and topic cues

### `source-skill.md`

- CTF Forensics & Blockchain
- Prerequisites
- Additional Resources
- When to Pivot
- Quick Start Commands
- File analysis
- Disk forensics
- Memory forensics (Volatility 3)
- Log Analysis
- Windows Event Logs (.evtx)
- When Logs Are Cleared
- Steganography
- PDF Analysis
- Disk / VM / Memory Forensics
- Disk images
- VM images (OVA/VMDK)
- Memory (Volatility 3)
- String carving
- Coredump
- Windows Password Hashes
- Extract with impacket, crack with hashcat -m 1000
- Bitcoin Tracing
- Uncommon File Magic Bytes
- Common Flag Locations

### `3d-printing.md`

- CTF Forensics - 3D Printing / CAD File Forensics
- Table of Contents
- PrusaSlicer Binary G-code (.g /.bgcode)
- QOIF (Quite OK Image Format)
- G-code Analysis Tips
- Search for flag patterns in decompressed gcode
- Look for custom comments at layer changes
- Extract XY coordinates for visual patterns
- G-code Side View Visualization
- Extract XY coordinates from G-code
- Plot with matplotlib for visual patterns
- Uncommon File Magic Bytes

### `disk-advanced.md`

- CTF Forensics - Advanced Disk and Memory Techniques
- Table of Contents
- Deleted Partition Recovery
- Check for partitions
- Recover partition table
- Or use kpartx to map partitions
- Mount recovered partition
- Check for hidden directories
- ZFS Forensics
- GPT Partition GUID Data Encoding
- Parse GPT partition table
- Or with Python:
- GPT header at LBA 1 (offset 512)
- Partition entries start at LBA 2 (offset 1024)
- Each entry is 128 bytes, GUID at offset 16 (16 bytes)
- Windows Minidump String Carving
- VMDK Sparse Parsing
- Memory Dump String Carving
- SSH artifacts reveal source IP and ephemeral port
- Environment variables may contain keys/tokens
- Memory Dump Malware Extraction + XOR
- Extract binary, find XOR key in data section
- Linux Ransomware Memory-Key Recovery
- Compare listed files/sizes vs extracted tree; re-extract cleanly if mismatch

### `disk-and-memory.md`

- CTF Forensics - Disk and Memory Analysis
- Table of Contents
- Memory Forensics (Volatility 3)
- Disk Image Analysis
- Mount read-only
- Autopsy / Sleuth Kit
- Carving deleted files
- VM Forensics (OVA/VMDK)
- OVA = TAR archive containing VMDK + OVF
- 7z reads VMDK directly (no mount needed)
- VMware Snapshot Forensics
- .vmss (suspended state) +.vmem (memory) → memory.dmp
- Output: memory.dmp (analyzable with Volatility/MemprocFS)
- mtime as Unix epoch → seed for PRNG → derive encryption key
- GIMP Raw Memory Dump Visual Inspection
- Alternative: use Python + PIL to scan memory as pixel data
- Try common display widths: 1920, 1366, 1280, 1024
- Coredump Analysis
- Windows KAPE Triage Analysis
- Look for: credential access, lateral movement, data staging
- Parse with Eric Zimmerman's AmcacheParser or regipy
- Parse MFT for resident file data (files < ~700 bytes stored inline)
- Use analyzeMFT or python-ntfs
- Search for flag patterns in raw MFT data

### `disk-recovery.md`

- CTF Forensics - Disk Recovery and Extraction Patterns
- Table of Contents
- LUKS Master Key Recovery from Memory Dump
- Output: candidate AES-256 keys (64 hex chars each)
- Enter new passphrase when prompted
- PRNG Timestamp Seed Brute-Force for Encryption Key Recovery
- Ruby-compatible Random implementation (or use ctypes for C rand)
- VBA Macro Encoded Binary Recovery
- If macro encodes as: cell_value = byte_value * 3 + 78
- Reverse: byte_value = (cell_value - 78) // 3
- FemtoZip Shared Dictionary Decompression
- Install femtozip
- Decompress using provided model
- Filter by metadata fields
- XFS Filesystem Reconstruction from Corrupted Metadata
- Extract file from known inode extent
- startblock=104333, blockcount=256, block_size=4096
- Parse XFS inode structure (at known offset)
- Tar Archive Duplicate Entry Extraction
- List all entries (shows duplicates)
- Extract specific occurrence (1-indexed)
- Extract all occurrences via file carving
- Or iterate programmatically
- Nested Matryoshka Filesystem Extraction

### `linux-forensics.md`

- CTF Forensics - Linux and Application Forensics
- Table of Contents
- Log Analysis
- Search for flag fragments
- Reconstruct fragmented flags
- Find anomalies
- Linux Attack Chain Forensics
- SSH session commands
- User command history
- Downloaded malware
- Network exfiltration
- Docker Image Forensics
- Find config blob (not layer blobs)
- Look for RUN commands with flag data, passwords, secrets
- Browser Credential Decryption
- Load master key (from Local State file, DPAPI-protected)
- Remove DPAPI prefix (5 bytes "DPAPI")
- On Windows: CryptUnprotectData to get master_key
- In lab-style tasks: master_key may be provided separately
- Firefox Browser History (places.sqlite)
- Quick method
- Proper forensic method
- USB Audio Extraction from PCAP
- Export ISO data with tshark

### `network-advanced.md`

- CTF Forensics - Network (Advanced)
- Table of Contents
- Packet Interval Timing-Based Encoding
- 1. Filter to the right interface (e.g., interface 2)
- tshark: tshark -r challenge.pcapng -Y "frame.interface_id == 2" -T fields -e frame.time_epoch
- 2. Compute inter-packet intervals
- 3. Identify binary mapping (two distinct interval values)
- E.g., 10ms → 0, 100ms → 1 (threshold at ~50ms)
- 4. May need to prepend a leading 0 bit (first interval has no predecessor)
- 5. Convert bits to bytes (MSB-first)
- NTLMv2 Hash Cracking from PCAP
- TCP Flag Covert Channel
- Map 6-bit flag value to base64 alphabet
- DNS Query Name Last-Byte Steganography
- Reconstruct message from last bytes
- May need additional decoding (hex, base64, etc.)
- DNS Trailing Byte Binary Encoding
- Convert bit string to ASCII (MSB-first, 8-bit chunks)
- Multi-Layer PCAP with XOR + ZIP
- 1. Extract XOR key from mDNS TXT record
- 2. Extract fake TLS stream (look for PK header in raw TCP data)
- Use Wireshark: tcp.stream eq N → Export raw bytes
- Or extract with scapy by filtering the right stream
- 3. XOR-decrypt two datasets from ZIP contents

### `network.md`

- CTF Forensics - Network
- Table of Contents
- tcpdump Quick Reference
- Basic capture on interface
- Capture to file
- Filter by source IP
- Filter by destination port
- Combined filter with file output
- Read from file with verbose output
- Show packet contents in ASCII
- Show hex + ASCII dump
- Count total packets
- TLS/SSL Decryption via Keylog File
- Set environment variable before running the client
- Import into Wireshark:
- Edit → Preferences → Protocols → TLS → (Pre)-Master-Secret log filename → /tmp/sslkeys.log
- Wireshark: Edit → Preferences → Protocols → TLS → RSA keys list
- IP: 127.0.0.1, Port: 443, Protocol: http, Key File: server.key
- Or via tshark:
- Extract certificate from PCAP
- Factor weak modulus, generate private key with rsatool
- Import key into Wireshark
- Wireshark Basics
- Filters

### `peripheral-capture.md`

- CTF Forensics - Peripheral Capture Analysis
- Table of Contents
- USB HID Mouse/Pen Drawing Recovery
- Extract HID data
- tshark -r capture.pcap -Y "usb.transfer_type==1" -T fields -e usb.capdata
- Accumulate positions per mode
- Render each mode separately (different colors = different text layers)
- Extract capdata and convert to signed deltas in one pass
- USB HID Keyboard Capture Decoding
- USB HID keyboard report format:
- Byte 0: Modifier keys (Shift, Ctrl, Alt)
- Byte 1: Reserved (0x00)
- Bytes 2-7: Up to 6 simultaneous key codes
- HID scan code to character mapping (partial)
- Extract from Wireshark: tshark -r capture.pcapng -T fields -e usb.capdata
- Or from text dump: parse +XX/-XX format (+ = keydown, - = keyup)
- USB Keyboard LED Morse Code Exfiltration
- Convert timing to Morse
- USB HID Keyboard Arrow Key Navigation Tracking
- Skeleton: track line position during HID decode
- Flag is on a specific line determined by arrow navigation
- Bluetooth RFCOMM Packet Reassembly
- Python with pyshark
- GBA USB URB_INTERRUPT Framebuffer Extraction

### `signals-and-hardware.md`

- CTF Forensics - Signals and Hardware
- Table of Contents
- VGA Signal Decoding
- Parse raw samples
- Extract active region, scale 6-bit to 8-bit
- HDMI TMDS Decoding
- Parse: read 10-bit symbols from binary, group into 3 channels
- Frame is 800x525 total, crop to 640x480 active
- DisplayPort 8b/10b + LFSR Decoding
- Standard 8b/10b decode table (partial — full table has 256 entries)
- Use a prebuilt table: map 10-bit symbol -> 8-bit data
- Key: running disparity tracks DC balance
- LFSR descrambler (x^16 + x^5 + x^4 + x^3 + 1)
- Transport Unit layout: 64 columns per TU
- Columns 0-59: pixel data (RGB)
- Columns 60-63: overhead (sync, stuffing)
- LFSR resets on control bytes (BS=0x1C, BE=0xFB)
- Voyager Golden Record Audio
- Find sync pulses (sharp negative spikes below threshold)
- Group consecutive sync samples into pulse starts
- Extract scan lines between pulses, resample to fixed width
- Normalize and save as image
- Side-Channel Power Analysis
- Load power traces: shape = (positions, guesses, traces, samples)

### `steganography.md`

- CTF Forensics - Steganography
- Table of Contents
- Quick Tools
- Steghide brute-force
- Common weak passphrases: "simple", "password", "123456"
- Binary Border Steganography
- Read border clockwise: top → right → bottom (reversed) → left (reversed)
- Convert bits to ASCII
- Multi-Layer PDF Steganography
- Extract post-EOF data
- Advanced PDF Steganography
- SVG Animation Keyframe Steganography
- APNG (Animated PNG) Frame Extraction
- Check if PNG is actually APNG (contains acTL chunk)
- Extract frames using apngdis
- Alternative: use PHP or Python libraries
- pip install apng
- PNG Height/CRC Manipulation for Hidden Content
- PNG Chunk Reordering
- Sort: IHDR first, IEND last, IDATs in original order
- File Format Overlays
- Find IEND, check what follows
- Replace first 6 bytes with 7z magic if they match PNG sig
- Nested PNG with Iterating XOR Keys

### `stego-advanced-2.md`

- CTF Forensics - Advanced Steganography (Part 2)
- Table of Contents
- Video Frame Accumulation for Hidden Image
- Load first frame as base
- Accumulate: take maximum pixel value across all frames
- Scan for QR code
- Reversed Audio Hidden Message
- Extract audio from video
- Reverse audio
- Or: ffmpeg -i audio.wav -af areverse reversed.wav
- Play to hear hidden message
- Video Frame Averaging for Hidden Content
- Accumulate frames as floating-point to preserve precision
- Convert back to uint8
- JPEG XL TOC Permutation Steganography
- Full decode as reference
- Track when each tile converges
- Sort tiles by convergence order
- Modified djxl with debug prints can extract TOC permutation directly
- Look for the permutation array in the JXL frame header
- The TOC permutation maps: stored_order[i] -> logical_group[i]
- Inverse gives: logical_group -> stored_order (convergence priority)
- Arnold's Cat Map Image Descrambling
- Iterate until original image reappears (period depends on N)

### `stego-advanced.md`

- CTF Forensics - Advanced Steganography
- Table of Contents
- FFT Frequency Domain Steganography
- Look for patterns: concentric rings, dots at specific positions
- Bright peak = 0 bit, Dark (no peak) = 1 bit
- SSTV Red Herring + LSB Audio Stego
- Decode SSTV (red herring)
- Extract real flag from LSB
- DotCode Barcode via SSTV
- DTMF Audio Decoding
- Decode DTMF tones
- Convert octal groups to ASCII
- Custom Frequency DTMF / Dual-Tone Keypad Encoding
- 1. Generate spectrogram to identify frequency grid
- Use ffmpeg: ffmpeg -i challenge.wav -lavfi showspectrumpic=s=1920x1080 spec.png
- 2. Map frequencies to keypad (custom grid, NOT standard DTMF)
- Example: rows = [301, 902, 1503, 2104] Hz, cols = [2705, 3306, 3907] Hz
- Forms 4x3 keypad -> digits 0-9 + symbols
- 3. Extract tone pairs per time window
- 4. Convert digit sequence to ASCII
- Split digits into variable-length groups (ASCII range 32-126)
- E.g., "72101108108111" -> [72, 101, 108, 108, 111] -> "Hello"
- Multi-Track Audio Differential Subtraction
- 1. Extract both audio tracks

### `stego-image.md`

- CTF Forensics - Image Steganography
- Table of Contents
- JPEG Unused Quantization Table LSB Steganography
- Access quantization tables (PIL exposes them as dict)
- Standard: tables 0 (luminance) and 1 (chrominance)
- Hidden: tables 2, 3 (unreferenced by SOF marker)
- Convert bits to ASCII
- Parse JPEG manually to find all DQT markers (0xFFDB)
- BMP Bitplane QR Code Extraction + Steghide
- Extract individual bitplanes
- Combined LSB across all channels
- Image Jigsaw Puzzle Reassembly via Edge Matching
- Load all pieces
- Calculate edge compatibility
- Build compatibility matrices
- Greedy placement
- Reassemble
- F5 JPEG DCT Coefficient Ratio Detection
- Combined classifier:
- PNG Unused Palette Entry Steganography
- QR Code Tile Reconstruction
- Load scrambled tiles
- Strategy 1: Edge matching (like jigsaw puzzle)
- Each tile edge has a unique bit pattern — match adjacent edges

### `windows.md`

- CTF Forensics - Windows
- Table of Contents
- Windows Event Logs (.evtx)
- Registry Analysis
- RegRipper
- Key hives
- OEMInformation Backdoor Detection
- SAM Database Analysis
- Crack with hashcat
- hashcat -m 1000 hashes.txt wordlist.txt
- Recycle Bin Forensics
- strings shows original path
- C.:.\.U.s.e.r.s.\.U.s.e.r.4.\.D.o.c.u.m.e.n.t.s.\.file.docx
- Output: 4B4354467B72656330...
- Browser History
- Windows Telemetry (imprbeacons.dat)
- Hosts File Hidden Data
- Detect hidden content
- Contact Files (.contact)
- WinZip AES Encrypted Archives
- Extract hash
- Crack with hashcat (mode 13600)
- Hybrid: word + 4 digits
- NTFS Alternate Data Streams

## Preservation rules

- Treat imported references as deep technique banks, not as routing documents.
- If a preserved section duplicates a stronger local methodology, prefer the local `offensive-techniques` workflow and use the preserved section for edge cases.
- Keep all future edits debrandized: no Task titles, competition names, platform names, or machine labels.
