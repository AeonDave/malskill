# Frida — Hooks Catalog for Common Scenarios

## Windows Malware

### Injection API monitoring

```javascript
// Monitor all common injection APIs
const INJECT_APIS = [
    ['kernel32.dll', 'VirtualAlloc'],
    ['kernel32.dll', 'VirtualAllocEx'],
    ['kernel32.dll', 'VirtualProtect'],
    ['kernel32.dll', 'WriteProcessMemory'],
    ['kernel32.dll', 'CreateRemoteThread'],
    ['kernel32.dll', 'CreateRemoteThreadEx'],
    ['ntdll.dll',    'NtCreateThreadEx'],
    ['ntdll.dll',    'NtMapViewOfSection'],
    ['ntdll.dll',    'NtUnmapViewOfSection'],
    ['ntdll.dll',    'NtAllocateVirtualMemory'],
    ['ntdll.dll',    'NtWriteVirtualMemory'],
];

INJECT_APIS.forEach(([mod, fn]) => {
    const addr = Module.findExportByName(mod, fn);
    if (!addr) return;
    Interceptor.attach(addr, {
        onEnter(args) {
            const frame = this.returnAddress;
            const callerMod = Process.findModuleByAddress(frame);
            const callerName = callerMod ? callerMod.name : 'unknown';
            console.log(`[${fn}] called from ${callerName}+0x${frame.sub(callerMod ? callerMod.base : ptr(0))}`);
            if (fn === 'VirtualAlloc' || fn === 'VirtualAllocEx') {
                const protect = args[3].toInt32();
                if (protect === 0x40) console.log(`  ⚠ PAGE_EXECUTE_READWRITE requested!`);
            }
            if (fn === 'WriteProcessMemory') {
                const size = args[3].toInt32();
                console.log(`  Writing ${size} bytes to ${args[1]}`);
            }
        }
    });
});
```

### Network interception (Windows)

```javascript
// Intercept WSA and WinInet/WinHTTP
const NET_HOOKS = [
    { mod: 'ws2_32.dll', fn: 'connect' },
    { mod: 'ws2_32.dll', fn: 'send' },
    { mod: 'ws2_32.dll', fn: 'recv' },
    { mod: 'ws2_32.dll', fn: 'WSASend' },
    { mod: 'wininet.dll', fn: 'InternetConnectW' },
    { mod: 'wininet.dll', fn: 'HttpSendRequestW' },
    { mod: 'winhttp.dll', fn: 'WinHttpConnect' },
];

NET_HOOKS.forEach(({ mod, fn }) => {
    const addr = Module.findExportByName(mod, fn);
    if (!addr) return;
    Interceptor.attach(addr, {
        onEnter(args) {
            if (fn === 'connect') {
                // Parse sockaddr_in
                const sa = args[1];
                const family = sa.readU16();
                if (family === 2) {
                    const portBE = sa.add(2).readU16();
                    const port = ((portBE & 0xFF) << 8) | (portBE >> 8);
                    const ip = [0,1,2,3].map(i => sa.add(4+i).readU8()).join('.');
                    console.log(`[connect] → ${ip}:${port}`);
                }
            } else if (fn === 'send' || fn === 'WSASend') {
                const buf = args[1], len = args[2].toInt32();
                console.log(`[${fn}] ${len} bytes`);
                if (len > 0 && len <= 4096) {
                    const data = buf.readByteArray(Math.min(len, 256));
                    console.log(hexdump(buf, { length: Math.min(len, 128) }));
                }
            } else if (fn === 'InternetConnectW') {
                console.log(`[InternetConnectW] host=${args[1].readUtf16String()} port=${args[2]}`);
            } else if (fn === 'HttpSendRequestW') {
                const headers = args[2] ? args[2].readUtf16String() : '';
                console.log(`[HttpSendRequest] headers: ${headers?.substring(0, 200)}`);
            }
        }
    });
});
```

### Anti-debug bypass (Windows)

```javascript
// Bypass common anti-debug checks
const ANTI_DEBUG_HOOKS = [
    ['kernel32.dll', 'IsDebuggerPresent'],
    ['kernel32.dll', 'CheckRemoteDebuggerPresent'],
    ['ntdll.dll',    'NtQueryInformationProcess'],
    ['kernel32.dll', 'OutputDebugStringA'],
    ['kernel32.dll', 'OutputDebugStringW'],
];

ANTI_DEBUG_HOOKS.forEach(([mod, fn]) => {
    const addr = Module.findExportByName(mod, fn);
    if (!addr) return;
    Interceptor.attach(addr, {
        onLeave(retval) {
            if (fn === 'IsDebuggerPresent') {
                retval.replace(ptr(0));
                console.log(`[bypass] ${fn} → 0`);
            } else if (fn === 'CheckRemoteDebuggerPresent') {
                if (this.pbDebuggerPresent) {
                    this.pbDebuggerPresent.writeU32(0);
                }
            } else if (fn === 'NtQueryInformationProcess') {
                // Class 7 = ProcessDebugPort
                if (this.infoClass === 7) {
                    this.buffer.writeU64(ptr(0));
                }
            }
        },
        onEnter(args) {
            if (fn === 'NtQueryInformationProcess') {
                this.infoClass = args[1].toInt32();
                this.buffer = args[2];
            } else if (fn === 'CheckRemoteDebuggerPresent') {
                this.pbDebuggerPresent = args[1];
            }
        }
    });
});
```

### Crypto/encryption interception

```javascript
// Intercept Windows CryptoAPI
['CryptEncrypt', 'CryptDecrypt'].forEach(fn => {
    const addr = Module.findExportByName('advapi32.dll', fn);
    if (!addr) return;
    Interceptor.attach(addr, {
        onEnter(args) {
            this.data = args[4];
            this.len = args[5].readU32();
            console.log(`[${fn}] BEFORE (${this.len} bytes):`);
            if (this.len > 0 && this.len <= 4096)
                console.log(hexdump(this.data, { length: Math.min(this.len, 256) }));
        },
        onLeave(retval) {
            if (this.len > 0) {
                console.log(`[${fn}] AFTER:`);
                console.log(hexdump(this.data, { length: Math.min(this.len, 256) }));
            }
        }
    });
});

// BCrypt (modern crypto API)
const BCryptEncrypt = Module.findExportByName('bcrypt.dll', 'BCryptEncrypt');
if (BCryptEncrypt) {
    Interceptor.attach(BCryptEncrypt, {
        onEnter(args) {
            this.plaintext = args[1];
            this.len = args[2].toInt32();
            console.log(`[BCryptEncrypt] plaintext (${this.len} bytes):`);
            console.log(hexdump(this.plaintext, { length: Math.min(this.len, 256) }));
        }
    });
}
```

## Linux Malware

### System call monitoring

```javascript
// Hook libc wrappers (or use Stalker for raw syscalls)
const LIBC_HOOKS = ['open', 'read', 'write', 'connect', 'send', 'recv',
                    'execve', 'fork', 'ptrace', 'mprotect', 'mmap'];

LIBC_HOOKS.forEach(fn => {
    const addr = Module.findExportByName(null, fn);
    if (!addr) return;
    Interceptor.attach(addr, {
        onEnter(args) {
            if (fn === 'open') {
                const path = args[0].readUtf8String();
                if (path) console.log(`[open] "${path}"`);
            } else if (fn === 'execve') {
                const path = args[0].readUtf8String();
                console.log(`[execve] "${path}"`);
            } else if (fn === 'ptrace') {
                console.log(`[ptrace] request=${args[0].toInt32()}`);
            } else if (fn === 'mprotect') {
                const prot = args[2].toInt32();
                if (prot === 7) console.log(`[mprotect] ⚠ RWX at ${args[0]} size=${args[1]}`);
            }
        }
    });
});
```

### File operation monitoring

```javascript
// Track all file reads and identify interesting data
Interceptor.attach(Module.getExportByName(null, 'read'), {
    onEnter(args) {
        this.buf = args[1];
        this.len = args[2].toInt32();
    },
    onLeave(retval) {
        const bytesRead = retval.toInt32();
        if (bytesRead > 0 && bytesRead <= 1024) {
            try {
                const content = this.buf.readByteArray(bytesRead);
                const str = new TextDecoder().decode(content);
                if (/password|secret|key|token|BEGIN/i.test(str)) {
                    console.log(`[read] Interesting content: ${str.substring(0, 200)}`);
                }
            } catch(e) {}
        }
    }
});
```

## Persistence and Registry (Windows)

```javascript
// Monitor registry persistence
const REG_HOOKS = [
    'RegSetValueExA', 'RegSetValueExW',
    'RegCreateKeyExA', 'RegCreateKeyExW',
];

REG_HOOKS.forEach(fn => {
    const addr = Module.findExportByName('advapi32.dll', fn);
    if (!addr) return;
    Interceptor.attach(addr, {
        onEnter(args) {
            const isW = fn.endsWith('W');
            if (fn.startsWith('RegSetValue')) {
                const valueName = isW ? args[1].readUtf16String() : args[1].readAnsiString();
                console.log(`[${fn}] key=${args[0]} value="${valueName}"`);
            } else {
                const keyName = isW ? args[1].readUtf16String() : args[1].readAnsiString();
                console.log(`[${fn}] creating key "${keyName}"`);
            }
        }
    });
});
```

## Stalker — Coverage Tracing

```javascript
// Trace all instructions in a thread and report unique blocks
const visited = new Set();

Stalker.follow(Process.getCurrentThreadId(), {
    events: { block: true },
    onReceive(events) {
        const reader = Stalker.parse(events, { annotate: false, stringify: false });
        let event;
        while ((event = reader.next()) !== null) {
            const [type, , , target] = event;
            if (type === 'block') {
                const mod = Process.findModuleByAddress(ptr(target));
                if (mod && mod.name === 'target.exe' && !visited.has(target)) {
                    visited.add(target);
                    // console.log(`Block: ${target.toString(16)}`);
                }
            }
        }
    }
});

// Stop after 10 seconds, print stats
setTimeout(() => {
    Stalker.unfollow(Process.getCurrentThreadId());
    console.log(`Unique blocks visited: ${visited.size}`);
    // Export for use with Lighthouse/coverage tools
    const coverage = [...visited].map(a => `0x${a.toString(16)}`).join('\n');
    send({type: 'coverage', data: coverage});
}, 10000);
```

## CModule — Compile C into Target Process

Compiles C string directly to machine code via TinyCC, mapped into target process memory.
Use for performance-critical callbacks in Interceptor/Stalker (avoids JS overhead).

```javascript
// Define C code as string → compiled in-memory, never touches filesystem
const cm = new CModule(`
#include <stdio.h>
#include <gum/gumstalker.h>

// Exported function: accessible as NativePointer
void on_call(GumCallSite * site, gpointer user_data) {
    printf("[CModule] call at %p\\n", site->target_address);
}
`);

// Access exported symbol as NativePointer
console.log('on_call at:', cm.on_call);

// Pass to Stalker as high-performance callback
Stalker.follow(Process.getCurrentThreadId(), {
    events: { call: true },
    onCallSummary: cm.on_call   // C function pointer, no JS overhead
});
```

```javascript
// Simpler: patch a function with compiled C stub
const cm2 = new CModule(`
int always_true(void) { return 1; }
`);

// Replace target function with compiled stub
Memory.patchCode(targetFuncPtr, 16, code => {
    // or just redirect:
});
// Or: override implementation directly
Interceptor.replace(targetFuncPtr, cm2.always_true);
```
