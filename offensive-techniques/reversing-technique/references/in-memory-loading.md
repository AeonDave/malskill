# Linux In-Memory Loading (memfd_create + dlopen)

Load after `triage.md` when evidence suggests fileless ELF loading via `memfd_create` + `dlopen`.

---

## Category 1: Recognition

### 1.1 Static indicators

```bash
# Check for memfd_create usage
strings binary | grep -iE "memfd_create|/proc/self/fd|/proc/%d/fd"
nm binary 2>/dev/null | grep memfd_create
objdump -d binary | grep -A2 "syscall" | grep -B1 "0x13f"   # syscall nr 319 (x86-64)

# If binary avoids libc wrappers, check for raw syscall
python3 -c "
import sys
data = open(sys.argv[1],'rb').read()
# memfd_create syscall: 319 = 0x13f
# Pattern: mov eax, 0x13f; syscall
import re
hits = [hex(m.start()) for m in re.finditer(b'\\xb8\\x3f\\x01\\x00\\x00\\x0f\\x05', data)]
print('memfd_create syscall at:', hits)
" binary
```

### 1.2 Dynamic indicators

```bash
# strace: catch memfd_create and the subsequent dlopen/fexecve
strace -f -e trace=memfd_create,openat,mmap,execve,fexecve ./binary 2>&1 | head -50

# Look for pattern:
#   memfd_create("", MFD_CLOEXEC) = 4
#   write(4, ..., N bytes)
#   openat(AT_FDCWD, "/proc/self/fd/4", O_RDONLY) = 5
#   dlopen("/proc/self/fd/4", ...)
```

---

## Category 2: Analysis Workflow

### 2.1 Layer separation

A typical multi-layer binary:

```
Outer ELF (analyzed first)
 ├── Embedded payload blob (encrypted/compressed in .data or .rodata)
 ├── Decrypt/decompress routine
 ├── memfd_create() → write payload → fd N
 └── dlopen("/proc/self/fd/N") OR fexecve("/proc/self/fd/N")
         └── Inner ELF (second layer — analyze separately)
```

**Goal:** extract the inner ELF, analyze both layers independently.

### 2.2 Dump the inner library at runtime

**Option A — GDB breakpoint on `dlopen`:**
```bash
gdb -q ./binary
(gdb) catch syscall memfd_create
(gdb) run
# When hit: fd number is in rax
(gdb) p $rax          # fd = 3 (example)
# After write(fd, ...) completes, dump the fd content:
(gdb) shell dd if=/proc/$(pidof binary)/fd/3 of=/tmp/inner.elf bs=1 2>/dev/null
(gdb) shell file /tmp/inner.elf
(gdb) continue
```

**Option B — Frida hook:**
```javascript
// Intercept dlopen and dump the fd before it's opened
const dlopenPtr = Module.getExportByName(null, 'dlopen');
Interceptor.attach(dlopenPtr, {
  onEnter(args) {
    const path = args[0].readCString();
    console.log('[dlopen] path:', path);
    if (path && path.includes('/proc/self/fd/')) {
      const fd = parseInt(path.split('/').pop());
      // Read from the fd via /proc/self/fd/<fd>
      const data = require('fs').readFileSync(path);
      require('fs').writeFileSync('/tmp/dumped_' + fd + '.elf', data);
      console.log('[dlopen] Dumped', data.length, 'bytes to /tmp/dumped_' + fd + '.elf');
    }
  }
});
```

**Option C — `/proc/<pid>/mem` direct read:**
```bash
# After memfd_create + write, before dlopen completes
# Find the fd size from /proc/<pid>/fdinfo/<fd>
cat /proc/<pid>/fdinfo/<fd>   # shows pos and flags
# Dump via dd
dd if=/proc/<pid>/fd/<fd> of=/tmp/inner.elf
```

**Option D — LD_PRELOAD hook on `memfd_create`:**
```c
// hook_memfd.c
#define _GNU_SOURCE
#include <dlfcn.h>
#include <sys/mman.h>
#include <fcntl.h>
#include <unistd.h>
#include <stdio.h>

int memfd_create(const char *name, unsigned int flags) {
    typedef int (*orig_t)(const char*, unsigned int);
    orig_t orig = (orig_t)dlsym(RTLD_NEXT, "memfd_create");
    int fd = orig(name, flags);
    fprintf(stderr, "[memfd hook] memfd_create(\"%s\") = fd %d\n", name, fd);
    // After write completes, dump in close hook or dlopen hook
    return fd;
}
```
```bash
gcc -shared -fPIC -ldl hook_memfd.c -o hook_memfd.so
LD_PRELOAD=./hook_memfd.so ./binary
```

### 2.3 Extract and analyze inner ELF

```bash
file /tmp/inner.elf          # Confirm it is ELF
sha256sum /tmp/inner.elf     # Dedup / VirusTotal lookup
readelf -h /tmp/inner.elf    # Arch, type (ET_DYN, ET_EXEC)
strings /tmp/inner.elf | head -50
# Load in Ghidra or radare2 as a fresh target
r2 -A /tmp/inner.elf
```

---

## Category 3: `fexecve` Variant

Some loaders use `fexecve(fd, argv, envp)` to execute the inner ELF as a new process (no `dlopen`):

```bash
strace -f -e trace=fexecve,execve ./binary 2>&1 | grep fexecve
# Output: fexecve(4, [...], [...]) = 0
```

**Dump approach:** identical to Option A/C above — catch at `fexecve` entry, dump `fd` before the call.

---

## Category 4: Multi-Stage and Nested Patterns

Some samples chain multiple memfd layers (outer → inner1 → inner2):

- Each stage decrypts and loads the next
- GDB approach: set `catch syscall memfd_create` with commands to auto-dump each new fd
- Frida approach: hook all `dlopen` + `fexecve` calls and log/dump each one

**GDB auto-dump script:**
```python
# Save as memfd_dump.py, load with: gdb -x memfd_dump.py ./binary
import gdb, os

class MemfdBreak(gdb.Breakpoint):
    def stop(self):
        # Get fd from syscall return
        rax = int(gdb.parse_and_eval('$rax'))
        pid = gdb.selected_inferior().pid
        src = f'/proc/{pid}/fd/{rax}'
        dst = f'/tmp/memfd_dump_{rax}.elf'
        os.system(f'dd if={src} of={dst} 2>/dev/null')
        print(f'[memfd] Dumped fd {rax} to {dst}')
        return False  # continue

# Set syscall catchpoint equivalent
gdb.execute('catch syscall memfd_create')
MemfdBreak('dlopen')
gdb.execute('run')
```

---

## Category 5: Outer Binary Reverse Engineering

Even before dumping the inner payload, analyze the outer ELF for:

1. **Decryption key material** — XOR keys, AES keys, hardcoded byte arrays in `.data`/`.rodata`
2. **Decompression** — `zlib`, `lz4`, `zstd` before the write
3. **Anti-debug around memfd** — ptrace checks or timing guards before/after `memfd_create`
4. **Persistence** — does the outer binary also install itself or only load the inner one?

```bash
# Check for compression magic in .data / .rodata
binwalk binary            # Identifies embedded zlib/gzip/lzma blobs
# Or:
python3 -c "
data = open('binary','rb').read()
import re
# zlib: 0x789C, gzip: 1F8B, lzma/xz: FD377A585A00
for magic, name in [(b'\\x78\\x9c','zlib'),(b'\\x1f\\x8b','gzip'),(b'\\xfd\\x37\\x7a','xz')]:
    for m in re.finditer(re.escape(magic), data):
        print(f'{name} at {hex(m.start())}')
" binary
```

---

## Tool citations

- `strace` — first-pass detection of `memfd_create` and `dlopen` calls
- `gdb` — runtime breakpoints, fd-to-file dump
- `frida` — `dlopen`/`fexecve` hook with auto-dump
- `radare2` / `ghidra` — static analysis of outer and inner ELFs separately
- `binwalk` — detect embedded compressed blobs in outer binary
