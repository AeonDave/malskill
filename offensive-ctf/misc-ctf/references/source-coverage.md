# Source Coverage Map

This map is the no-loss checklist for the imported source material. Each file listed here has a debrandized preservation copy under `references/imported/`.

- Source skill: `ctf-misc`
- Target skill: `misc-ctf`
- Preserved files: 13

## Imported files and topic cues

### `source-skill.md`

- CTF Miscellaneous
- Prerequisites
- Additional Resources
- When to Pivot
- Quick Start Commands
- File identification
- Encoding detection
- QR code
- Z3 constraint solving
- Python jail test
- General Tips
- Common Encodings
- Base64
- Base32 (A-Z2-7=)
- Hex
- ROT13
- IEEE-754 Float Encoding (Data Hiding)
- USB Mouse PCAP Reconstruction
- File Type Detection
- Archive Extraction
- Nested Archive Script
- QR Codes
- Audio Challenges
- RF / SDR / IQ Signal Processing

### `bashjails.md`

- CTF Misc - Bash Jails & Restricted Shells
- Table of Contents
- Identifying the Jail
- Send each char combined with a known-good payload
- Eval Context Detection
- Character-Restricted Bash: Only `#`, `$`, `\`
- Internal Service Discovery (Post-Shell)
- Find all running processes and their command lines
- Look specifically for flag-serving processes
- Bash built-in TCP (no netcat needed)
- Or with netcat if available
- Other Restricted Character Set Tricks
- Building numbers from `$#` and `${##}`
- Using PID digits
- Octal in ANSI-C quoting
- Dollar-zero variants
- Privilege Escalation Checklist (Post-Shell)
- HISTFILE Trick for Restricted Shell File Reads
- Method 1: HISTFILE loading
- Method 2: bash verbose mode
- Method 3: ctypes.sh direct C library calls
- Bash Jail Bypass via $'...' Octal Encoding
- Encode /get_flag as octal
- Or encode any command character by character:

### `ctfd-navigation.md`

- CTFd Platform Navigation (No Browser)
- Table of Contents
- Detect CTFd
- Check for CTFd signatures in response headers and body
- Check for CTFd API endpoint (returns Swagger UI or JSON)
- Check for CTFd static assets
- Check for CTFd login page structure
- Authentication
- Method 1: API Token (Recommended)
- Generate token via API (requires session auth first)
- Test authentication
- Method 2: Session Login (Cookie-Based)
- Step 1: Get CSRF nonce from login page
- Step 2: Login with credentials
- Step 3: Use cookies for API calls
- List Challenges
- All visible challenges
- Filter by category
- Compact listing: id, name, category, value, solves
- Challenge Details
- Full challenge details (description, files, hints, tags)
- Extract just the description (HTML)
- Strip HTML tags for readable description
- List files attached to challenge

### `dns.md`

- CTF Misc - DNS Exploitation Techniques
- Table of Contents
- EDNS Client Subnet (ECS) Spoofing
- dig with ECS option
- DNSSEC NSEC Walking
- Incremental Zone Transfer (IXFR)
- AXFR blocked? Try IXFR from serial 0
- Look for historical TXT records in the diff output
- DNS Rebinding
- Simple DNS rebinding server (Python + dnslib)
- DNS Tunneling / Exfiltration
- Extract DNS queries from pcap
- Look for encoded subdomains (hex, base32, base64url)
- Subdomain-based exfil: data.chunk1.evil.com, data.chunk2.evil.com
- DNS Round-Robin A Record Enumeration
- Get all A records (query multiple times for round-robin)
- Scan each IP for open port 80 and request with correct Host header
- DNS Maze Traversal
- BFS to find exit
- DNS Enumeration Quick Reference
- Standard zone transfer attempt
- Brute-force subdomains
- Reverse DNS sweep
- Check for wildcard DNS

### `encodings-advanced.md`

- CTF Misc - Advanced Encodings & Specialized Formats
- Table of Contents
- Verilog/HDL
- Translate Verilog logic to Python
- Gray Code Cyclic Encoding
- Generate N-bit Gray code sequence
- 5-bit Gray code: 32 values
- [0, 1, 3, 2, 6, 7, 5, 4, 12, 13, 15, 14, 10, 11, 9, 8,...]
- Rotate sequence by k positions (cyclic property)
- If decoded output is ROT-N shifted, rotate the Gray code start by N positions
- Binary Tree Key Encoding
- RTF Custom Tag Data Extraction
- Extract custom tags: {\*\<N> <DATA>}
- SMS PDU Decoding and Reassembly
- Read PDU hex strings (one per line)
- Sort by concatenation sequence number (bytes 38-40 in hex)
- Extract and concatenate user data
- Payload is often base64 — decode to get embedded file
- Automated Multi-Encoding Sequential Solver
- Chain decoder
- RFC 4042 UTF-9 Decoding
- Convert octal/hex input to binary first
- Pixel Color Binary Encoding
- Hexadecimal Sudoku + QR Assembly

### `encodings.md`

- CTF Misc - Encodings & Media
- Table of Contents
- Common Encodings
- Base64
- Charset: A-Za-z0-9+/=
- Base32
- Charset: A-Z2-7= (no lowercase, no 0,1,8,9)
- Hex
- IEEE 754 Floating Point Encoding
- Each float32 packs to 4 ASCII bytes
- For double precision (8 bytes per value):
- struct.pack('>d', v)
- UTF-16 Endianness Reversal
- If encoded as UTF-16-LE but decoded as UTF-16-BE:
- If encoded as UTF-16-BE but decoded as UTF-16-LE:
- BCD (Binary-Coded Decimal) Encoding
- Then convert decimal string to ASCII
- Multi-Layer Encoding Detection
- URL Encoding
- ROT13 / Caesar
- Caesar Brute Force
- QR Codes
- Basic Commands
- QR Structure

### `games-and-vms-2.md`

- CTF Misc - Games, VMs & Constraint Solving (Part 2)
- Table of Contents
- Cookie Checkpoint Game Brute-Forcing
- Flask Session Cookie Game State Leakage
- Decode Flask session cookie (no secret needed for reading)
- WebSocket Game Manipulation + Cryptic Hint Decoding
- Server Time-Only Validation Bypass
- Wait for required traversal time (e.g., 4800px / 240px/s = 20s + margin)
- De Bruijn Sequence for Substring Coverage
- For 12-bit binary codes: B(2, 12) has length 4096
- Every possible 12-bit code appears as a substring
- Brainfuck Interpreter Instrumentation
- Brute-force: ~40 positions × 95 chars = 3800 runs
- WASM Linear Memory Manipulation
- References

### `games-and-vms-3.md`

- CTF Misc - Games, VMs & Constraint Solving (Part 3)
- Table of Contents
- memfd_create Packed Binaries
- Multi-Phase Interactive Crypto Game
- Flow: send token first, then server reveals state, then send answer
- Server checks: HMAC(nonce, answer) == your_token
- Prevents changing your answer after seeing the state
- Galois Field GF(256) used in some game mechanics (Nim variants)
- Nim-value XOR determines winning/losing positions
- Nim game with GF(256) move rules:
- Position is losing if Nim-value (XOR of pile Grundy values) is 0
- Optimal move: find pile where removing stones makes XOR sum = 0
- Python too slow for large state spaces — use C++ with memoization
- State compression: encode all pile sizes into single integer
- Cache: unordered_map<state_t, bool> for win/loss determination
- Python fallback for small games:
- Emulator ROM-Switching State Preservation
- Load first ROM that initializes secret data
- Step until secret is in memory (determined by analysis)
- Switch to ROM that displays memory at current PC
- Read the leaked secret
- Python Marshal Code Injection
- Craft payload function that exfiltrates data over the socket
- Serialize the function's code object

### `games-and-vms-4.md`

- CTF Misc - Games, VMs & Constraint Solving (Part 4)
- Table of Contents
- XSLT as Turing-Complete VM for Binary Search
- JavaScript MAX_SAFE_INTEGER Successor Equality
- Binary Search Oracle in Comparison-Only DSL
- Blind SQLi via Script-Engine Timeout Error
- OEIS Sequence Lookup Automation for Recurrence Puzzles
- QR Code Reassembly from Format-String Structural Constraints
- Matrix Exponentiation for Fibonacci-Like Recurrence
- Tribonacci Recurrence for Frog Jump Counting
- Selenium + Tesseract for Dynamic Font CAPTCHA
- Brainfuck Decodes Piet Image URL — Multi-Layer Polyglot
- Bytebeat Synth Code Recognition for Hidden Audio

### `games-and-vms.md`

- CTF Misc - Games, VMs & Constraint Solving (Part 1)
- Table of Contents
- WASM Game Exploitation via Patching
- 1. Convert WASM binary to text format
- 2. Find the minimax function (look for bestScore initialization)
- Change initial bestScore from -1000 to 1000
- Flip comparison: i64.lt_s -> i64.gt_s (selects worst moves instead of best)
- 3. Recompile
- Roblox Place File Reversing
- Requires.ROBLOSECURITY cookie
- Pseudocode for extracting scripts
- PyInstaller Extraction
- Look in packed.exe_extracted/
- Opcode Remapping
- Marshal Code Analysis
- Bytecode Inspection Tips
- Python Environment RCE
- Z3 Constraint Solving
- Add constraints...
- YARA Rules with Z3
- Literal bytes
- Character range
- Type Systems as Constraints
- Convert to Z3 constraints and solve

### `linux-privesc.md`

- Linux Privilege Escalation and Service Exploitation
- Table of Contents
- Sudo Wildcard Parameter Injection via fnmatch
- Crafted Pcap for /etc/sudoers.d
- Payload embedded in each UDP packet
- Avoid 10.x.x.x IPs (0x0a byte = newline in binary headers)
- Use 192.168.1.1/192.168.1.2, ports 12345/9999, timestamps 100-109
- Monit confcheck Process Command-Line Injection
- Monit confcheck script pattern:
- pgrep -lfa "^/opt/app/bin/apache2.-k.start.-d./opt/app/conf"
- -> replaces apache2->apache2ctl, appends -t, executes as root
- Inject extra flags via fake process:
- Apache -d Last-Wins ServerRoot Override
- Create malicious Apache config
- Fake process injects -d and -E (error log to readable file)
- After monit triggers confcheck, read error log:
- AH00526: Syntax error on line 1 of /root/root.txt:
- Invalid command 'FLAG_CONTENT_HERE'...
- Backup Cronjob SUID Abuse
- PostgreSQL COPY TO PROGRAM RCE
- PostgreSQL Backup Credential Extraction
- Mount NFS share, extract backup zip
- Extract pg_authid from global/1260 for password hashes
- Restore backup: docker run -v /path/to/backup:/var/lib/postgresql/data postgres:14

### `pyjails.md`

- CTF Misc - Python Jails
- Table of Contents
- Identifying Jail Type
- Systematic Enumeration
- Test Basic Features
- Test Blocked AST Nodes
- Brute-Force Function Names
- Oracle-Based Challenges
- Binary Search
- Linear Search
- Building Strings Without Concat
- Hex escapes
- Classic Escape Techniques
- Via Class Hierarchy
- Find <class 'os._wrap_close'>
- Compile Bypass
- Unicode Bypass
- Getattr Alternatives
- Walrus Operator Reassignment
- Reassign constraint variable
- Octal Escapes
- \141 = 'a', \142 = 'b', etc.
- Magic Comment Escape
- -*- coding: raw_unicode_escape -*-

### `rf-sdr.md`

- CTF Misc - RF / SDR / IQ Signal Processing
- IQ File Formats
- Analysis Pipeline
- 1. Load IQ data
- 2. Spectrum analysis - find occupied bands
- 3. Identify symbol rate via cyclostationary analysis
- Peak in fft_x2 = symbol rate (samples_per_symbol = 1/peak_freq)
- 4. Frequency shift to baseband
- 5. Low-pass filter to isolate band
- QAM-16 Demodulation with Carrier + Timing Recovery
- Loop parameters (2nd order PLL)
- y = received symbol, d = decision (nearest constellation point)
- Key Insights for RF challenges
- Common Framing Patterns

## Preservation rules

- Treat imported references as deep technique banks, not as routing documents.
- If a preserved section duplicates a stronger local methodology, prefer the local `offensive-techniques` workflow and use the preserved section for edge cases.
- Keep all future edits debrandized: no Task titles, competition names, platform names, or machine labels.
