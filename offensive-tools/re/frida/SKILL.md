---
name: frida
description: "Dynamic instrumentation toolkit for hooking functions, tracing APIs, and manipulating running processes across Windows, Linux, macOS, Android, and iOS. Use when performing runtime analysis, bypassing protections, intercepting crypto/network calls, or building custom instrumentation scripts."
license: MIT
compatibility: "Python/JS; Windows/Linux/macOS/Android/iOS; pip install frida-tools"
metadata:
  author: AeonDave
  version: "1.0"
---

# Frida

Dynamic instrumentation — inject JavaScript into running processes to hook, trace, and modify behavior at runtime.

## Installation

```bash
# CLI tools
pip install frida-tools

# Python bindings
pip install frida

# For Android: push frida-server to device
# Download from https://github.com/frida/frida/releases (match arch)
adb push frida-server /data/local/tmp/
adb shell chmod 755 /data/local/tmp/frida-server
adb shell /data/local/tmp/frida-server &
```

## Quick Start

```bash
# List running processes
frida-ps                        # Local
frida-ps -U                     # USB (Android/iOS)

# Attach to process
frida -p PID
frida -n process_name

# Spawn and attach
frida -f /path/to/binary

# Run a script
frida -p PID -l hook.js

# Trace functions matching pattern
frida-trace -i "recv*" -p PID
frida-trace -i "open*" -f ./binary
```

## Core JavaScript API

### Interceptor — Hook Functions

```javascript
// Hook a native function
Interceptor.attach(Module.getExportByName(null, 'connect'), {
    onEnter(args) {
        const sockaddr = args[1];
        const family = sockaddr.readU16();
        if (family === 2) { // AF_INET
            const port = (sockaddr.add(2).readU8() << 8) | sockaddr.add(3).readU8();
            const ip = [
                sockaddr.add(4).readU8(), sockaddr.add(5).readU8(),
                sockaddr.add(6).readU8(), sockaddr.add(7).readU8()
            ].join('.');
            console.log(`[connect] ${ip}:${port}`);
        }
    },
    onLeave(retval) {
        console.log(`[connect] returned ${retval}`);
    }
});
```

### Replace Function Return

```javascript
// Force IsDebuggerPresent to return 0 (Windows anti-debug bypass)
Interceptor.attach(Module.getExportByName('kernel32.dll', 'IsDebuggerPresent'), {
    onLeave(retval) {
        retval.replace(ptr(0));
    }
});
```

### Module and Memory

```javascript
// List loaded modules
Process.enumerateModules().forEach(m => {
    console.log(`${m.name} @ ${m.base} size=${m.size}`);
});

// Find export
const addr = Module.getExportByName('libc.so', 'open');

// Read/write memory
const buf = Memory.readByteArray(ptr(0x401000), 64);
Memory.writeByteArray(ptr(0x401000), [0x90, 0x90, 0x90]);

// Scan memory for pattern
Memory.scan(module.base, module.size, 'MZ', {
    onMatch(address, size) { console.log(`Found MZ at ${address}`); },
    onComplete() { console.log('Scan done'); }
});
```

### Stalker — Instruction Tracing

```javascript
Stalker.follow(Process.getCurrentThreadId(), {
    events: { call: true, ret: true },
    onCallSummary(summary) {
        for (const [addr, count] of Object.entries(summary)) {
            const mod = Process.findModuleByAddress(ptr(addr));
            if (mod) console.log(`${mod.name}+${ptr(addr).sub(mod.base)}: ${count} calls`);
        }
    }
});
```

## Common Workflows

### Malware — trace network calls (Linux)

```javascript
['connect', 'send', 'sendto', 'recv', 'recvfrom'].forEach(fn => {
    const p = Module.getExportByName(null, fn);
    if (p) {
        Interceptor.attach(p, {
            onEnter(args) {
                console.log(`[${fn}] fd=${args[0]}, buf=${args[1]}, len=${args[2]}`);
                if (fn.startsWith('send')) {
                    console.log(hexdump(args[1], { length: Math.min(args[2].toInt32(), 128) }));
                }
            }
        });
    }
});
```

### Malware — intercept crypto (Windows)

```javascript
Interceptor.attach(Module.getExportByName('bcrypt.dll', 'BCryptEncrypt'), {
    onEnter(args) {
        this.plaintext = args[1];
        this.len = args[2].toInt32();
        console.log(`[BCryptEncrypt] plaintext (${this.len} bytes):`);
        console.log(hexdump(this.plaintext, { length: Math.min(this.len, 256) }));
    }
});
```

### Android — bypass SSL pinning

```javascript
Java.perform(() => {
    const TrustManager = Java.registerClass({
        name: 'com.frida.TrustManager',
        implements: [Java.use('javax.net.ssl.X509TrustManager')],
        methods: {
            checkClientTrusted(chain, authType) {},
            checkServerTrusted(chain, authType) {},
            getAcceptedIssuers() { return []; }
        }
    });
    const SSLContext = Java.use('javax.net.ssl.SSLContext');
    const ctx = SSLContext.getInstance('TLS');
    ctx.init(null, [TrustManager.$new()], null);
    SSLContext.getInstance.overload('java.lang.String').implementation = function(protocol) {
        return ctx;
    };
    console.log('[bypass] SSL pinning disabled');
});
```

### Android — hook Java methods

```javascript
Java.perform(() => {
    const clazz = Java.use('com.example.app.LoginActivity');
    clazz.validatePassword.implementation = function(password) {
        console.log(`[hook] validatePassword("${password}")`);
        const result = this.validatePassword(password);
        console.log(`[hook] returned ${result}`);
        return result;
    };
});
```

### Windows — trace injection APIs

```javascript
const apis = ['VirtualAlloc', 'VirtualProtect', 'CreateRemoteThread',
              'WriteProcessMemory', 'CreateProcessW'];
apis.forEach(api => {
    const p = Module.getExportByName('kernel32.dll', api);
    if (p) {
        Interceptor.attach(p, {
            onEnter(args) {
                console.log(`[${api}] called from ${this.returnAddress}`);
                console.log(`  args: ${args[0]}, ${args[1]}, ${args[2]}, ${args[3]}`);
            },
            onLeave(retval) {
                console.log(`[${api}] returned ${retval}`);
            }
        });
    }
});
```

## frida-trace

```bash
# Trace all open* calls
frida-trace -i "open*" -f ./binary

# Trace specific library functions
frida-trace -i "SSL_*" -f ./binary

# Trace ObjC methods (iOS/macOS)
frida-trace -m "-[NSURLSession *]" -p PID

# Trace Java methods (Android)
frida-trace -j "com.example.app.LoginActivity!*" -U -f com.example.app
```

## Python API

```python
import frida

def on_message(message, data):
    if message['type'] == 'send':
        print(f"[*] {message['payload']}")

device = frida.get_local_device()
session = device.attach("target_process")
script = session.create_script("""
    Interceptor.attach(Module.getExportByName(null, 'connect'), {
        onEnter(args) { send('connect called'); }
    });
""")
script.on('message', on_message)
script.load()
input("Press Enter to detach...")
session.detach()
```

## Resources

| File | When to load |
|------|--------------|
| [references/hooks-catalog.md](references/hooks-catalog.md) | Ready-made hook scripts for common scenarios |
| [references/android-ios.md](references/android-ios.md) | Mobile-specific instrumentation patterns |
