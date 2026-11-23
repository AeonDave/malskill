# Frida — Android & iOS Instrumentation

## Android session and hook qualification

Record OS/build, process ABI, root/debug state, Frida core/server or Gadget versions and bridge version. Match the core client and server/Gadget releases; frida-tools has its own version scheme. A successful process listing does not prove Java or native instrumentation works on this build.

- For custom agents, apply the bridge-packaging rule in [Frida](../SKILL.md); do not diagnose an undefined `Java` global as an app defense.
- For startup observations through bindings, spawn suspended, attach, register message/error handlers, load the agent, then resume. `Java.perform()` defers until the app class loader is available: distinguish script loaded from hook installed. Avoid a fixed sleep followed by attach; it can miss the relevant event.
- Exercise one known method on the relevant path and require a hook-hit marker. If absent, check process, overload, loader and timing before concluding the operation never occurs. Report installation errors instead of swallowing them.
- Preserve return values and exceptions for observational hooks. Compare uninstrumented behavior when a hook changes timing or state. Detach and clean up the test session.

See [Frida JavaScript API](https://frida.re/docs/javascript-api/) and [Gadget lifecycle](https://frida.re/docs/gadget/).

## TLS and application data (Android)

Baseline first: trust the lab CA through the app's own configuration (a debug build's `debug-overrides` or a repackaged Network Security Configuration) and record the exact failing check. A hook loaded before the baseline hides pinning and custom trust.

| Stack or check | Hook point | Scope and limit |
|---|---|---|
| Default trust (JSSE through Conscrypt) | `com.android.org.conscrypt.TrustManagerImpl.checkTrustedRecursive` | Private method whose arity differs by release: hook every overload. Covers default `TrustManagerFactory` managers. |
| App-supplied trust managers | `javax.net.ssl.SSLContext.init` | Replaces only the server-trust decision. Stacks that never call `init` are not reached. |
| Custom `X509TrustManager` or `HostnameVerifier` | App class `checkServerTrusted`, `verify` | Find by `implements X509TrustManager` and `implements HostnameVerifier`. |
| Network Security Configuration `<pin-set>` | `android.security.net.config.NetworkSecurityTrustManager` | `checkServerTrusted` runs `checkPins()` on the chain the delegate returned: an accepted but empty chain still fails the pins. |
| OkHttp | `okhttp3.CertificatePinner`: `check` overloads and `check$okhttp`; `OkHostnameVerifier.verify` | R8 renames these classes unless keep rules retain them. In minified apps locate the pinner by its `sha256/` pin literals. |
| Native TLS | `SSL_CTX_set_custom_verify`, `SSL_verify_cert_chain` in the engine's library | Per library. Frida 17 resolves exports with `Process.getModuleByName().findExportByName()`. |
| WebView, Flutter, Cronet | Own Chromium/BoringSSL stack | JSSE hooks do not reach them. WebView follows the app's NSC trust; the others need engine-specific hooks. |

For breadth use the maintained scripts in [httptoolkit/frida-interception-and-unpinning](https://github.com/httptoolkit/frida-interception-and-unpinning) (`android/android-certificate-unpinning.js`, `native-tls-hook.js`, Flutter and proxy-override scripts) and match its hook list against the stack actually found.

```javascript
// 1. Default Conscrypt trust: observe, or return an empty list to accept the chain
Java.perform(() => {
    const TMI = Java.use('com.android.org.conscrypt.TrustManagerImpl');
    TMI.checkTrustedRecursive.overloads.forEach(ov => {
        ov.implementation = function () {
            console.log(`[tls] checkTrustedRecursive host=${arguments[3]}`);
            return ov.apply(this, arguments);
            // to accept: return Java.use('java.util.ArrayList').$new();
        };
    });
});
```

```javascript
// 2. App-supplied managers: replace only the trust decision passed to SSLContext.init
Java.perform(() => {
    const Lab = Java.registerClass({
        name: 'org.lab.TrustAll',
        implements: [Java.use('javax.net.ssl.X509TrustManager')],
        methods: {
            checkClientTrusted(chain, authType) {},
            checkServerTrusted(chain, authType) {},
            getAcceptedIssuers() { return []; }
        }
    });
    const SSLContext = Java.use('javax.net.ssl.SSLContext');
    SSLContext.init.overload('[Ljavax.net.ssl.KeyManager;', '[Ljavax.net.ssl.TrustManager;', 'java.security.SecureRandom')
        .implementation = function (km, tm, sr) {
            console.log(`[tls] SSLContext.init trust=${tm ? tm.length : 'default'}`);
            this.init(km, [Lab.$new()], sr);
        };
});
```

```javascript
// 3. OkHttp: the List overload, the vararg overload and the internal check$okhttp
Java.perform(() => {
    const Pinner = Java.use('okhttp3.CertificatePinner');
    const noop = function () { console.log(`[tls] CertificatePinner ${arguments[0]}`); };
    Pinner.check.overloads.forEach(ov => { ov.implementation = noop; });
    if (Pinner['check$okhttp']) Pinner['check$okhttp'].overloads.forEach(ov => { ov.implementation = noop; });
});
```

- Wrap each block in its own `try`/`catch` and print the error: a missing class is a stack finding, not a reason to skip silently.
- Expect a hook-hit marker per block. No hit on a request that is known to fail means the stack does not use that path.
- A log line proves only that the script ran. Require a correlated request/response through the proxy after installation.
- Replacing `SSLContext.getInstance()` with one fixed context breaks callers that request another protocol; the `init` hook does not.

For trust configuration, session-bound encryption and serialization, load [Android traffic and custom protocols](../../../../offensive-techniques/mobile-technique/references/android-traffic-and-custom-protocols.md).

## Java Method Hooking

### Hook any Java method

```javascript
Java.perform(() => {
    // Hook instance method
    const TargetClass = Java.use('com.example.app.SomeClass');

    // Overload variant (if multiple signatures)
    TargetClass.someMethod.overload('java.lang.String', 'int')
        .implementation = function(arg1, arg2) {
            console.log(`[hook] someMethod("${arg1}", ${arg2})`);
            const result = this.someMethod(arg1, arg2);
            console.log(`[hook] → returned: ${result}`);
            return result;  // Or return modified value
        };

    // Hook all overloads
    TargetClass.someMethod.overloads.forEach(overload => {
        overload.implementation = function(...args) {
            console.log(`[hook] someMethod called with ${args.length} args`);
            return overload.call(this, ...args);
        };
    });
});
```

### Hook static method + modify return

```javascript
Java.perform(() => {
    const Utils = Java.use('com.example.app.Utils');

    // Static method returning boolean
    Utils.isRooted.implementation = function() {
        console.log('[bypass] isRooted → false');
        return false;
    };

    Utils.isEmulator.implementation = function() {
        return false;
    };

    Utils.isDebuggerConnected.implementation = function() {
        return false;
    };
});
```

### Intercept crypto in Java

This example observes the `doFinal(byte[])` overload with the mode recorded at `init`. It does not reconstruct streamed operations (`update`, output-buffer and `ByteBuffer` variants); use the protocol reference below when correlating complete operations. Restrict plaintext capture to controlled test data.

```javascript
Java.perform(() => {
    // javax.crypto.Cipher hook
    const Cipher = Java.use('javax.crypto.Cipher');
    const modes = {};                                      // cipher hashCode -> opmode: no public getter exists

    Cipher.init.overloads.forEach(ov => {
        ov.implementation = function() {
            modes[this.hashCode()] = arguments[0];         // 1 ENCRYPT, 2 DECRYPT, 3 WRAP, 4 UNWRAP
            const key = arguments[1];
            const enc = key ? key.getEncoded() : null;     // null for keys without an encoding (Keystore)
            console.log(`[Cipher.init] ${this.getAlgorithm()} opmode=${arguments[0]} key=${enc ? bytesToHex(enc) : 'unextractable'}`);
            return ov.apply(this, arguments);
        };
    });

    Cipher.doFinal.overload('[B').implementation = function(input) {
        const algorithm = this.getAlgorithm();
        console.log(`[Cipher.doFinal] algo=${algorithm} opmode=${modes[this.hashCode()]} input=${bytesToHex(input)}`);
        const output = this.doFinal(input);
        console.log(`[Cipher.doFinal] output=${bytesToHex(output)}`);
        return output;
    };

    // MessageDigest (MD5/SHA1/SHA256)
    const MessageDigest = Java.use('java.security.MessageDigest');
    MessageDigest.digest.overload('[B').implementation = function(input) {
        const algo = this.getAlgorithm();
        const output = this.digest(input);
        console.log(`[MessageDigest.${algo}] input=${bytesToHex(input)} hash=${bytesToHex(output)}`);
        return output;
    };
});

function bytesToHex(bytes) {
    return Array.from(bytes).map(b => ('0' + (b & 0xff).toString(16)).slice(-2)).join('');
}
```

### Enumerate loaded classes

```javascript
Java.perform(() => {
    // Find all loaded classes matching pattern
    Java.enumerateLoadedClasses({
        onMatch(name) {
            if (name.includes('crypto') || name.includes('pin') || name.includes('cert')) {
                console.log(`[class] ${name}`);
            }
        },
        onComplete() { console.log('Done'); }
    });
});
```

## DEX Dumping (Packed Android Malware)

For loader patterns and artifact validation, load [DEX/native recovery](../../../../offensive-coding/smali-dex-patching/references/dynamic-dex-and-native-loaders.md). A loader event alone is not a complete artifact capture.

Capture at the loader constructor, before the original runs. `InMemoryDexClassLoader` takes the DEX between `position()` and `limit()` of each buffer (three constructors: one buffer, an array, an array plus a library path). `ByteBuffer.array()` throws on direct and read-only buffers, so read through a duplicate with one bulk `get`:

```javascript
Java.perform(() => {
    const ByteBuffer = Java.use('java.nio.ByteBuffer');

    function bytesOf(buf) {
        const dup = buf.duplicate();                        // independent position and limit
        const n = dup.remaining();
        const tmp = Java.array('byte', new Array(n).fill(0));
        dup.get(tmp);                                       // bulk copy: one JNI call
        const ab = new ArrayBuffer(n);
        const view = new Uint8Array(ab);
        for (let i = 0; i < n; i++) view[i] = tmp[i] & 0xff;
        return ab;
    }

    const DexClassLoader = Java.use('dalvik.system.DexClassLoader');
    DexClassLoader.$init.overloads.forEach(ov => {
        ov.implementation = function () {
            console.log(`[dex] DexClassLoader ${arguments[0]}`);   // file on disk: pull it
            return ov.apply(this, arguments);
        };
    });

    const InMemory = Java.use('dalvik.system.InMemoryDexClassLoader');
    InMemory.$init.overloads.forEach(ov => {
        ov.implementation = function () {
            const isArray = ov.argumentTypes[0].className === '[Ljava.nio.ByteBuffer;';
            const list = isArray ? arguments[0] : [arguments[0]];
            console.log(`[dex] InMemoryDexClassLoader buffers=${list.length}`);
            for (let i = 0; i < list.length; i++)
                send({ tag: 'inmemory-dex', index: i, count: list.length }, bytesOf(Java.cast(list[i], ByteBuffer)));
            return ov.apply(this, arguments);
        };
    });
});
```

The host receives the bytes in the second argument of the message handler:

```python
def on_message(message, data):
    payload = message.get('payload') or {}           # send(obj, data): obj is under 'payload'
    if message.get('type') == 'send' and payload.get('tag') == 'inmemory-dex':
        with open(f"{payload['index']}.dex", 'wb') as f:
            f.write(data)
```

- Validate each artifact before analysis: `dex` magic, header size and checksum. A truncated or zeroed buffer means the wrong slice or the wrong overload.
- Loaders that avoid these classes (reflection, `dalvik.system.DexFile` static `openInMemoryDexFile`/`openInMemoryDexFiles`, JNI) need the same treatment on `DexFile`, or a breakpoint on the native `DexFile` constructor.
- After the load, enumerate class loaders (`Java.enumerateClassLoaders`), assign the new one to `Java.classFactory.loader` and enumerate its classes to confirm the stage is live. See [InMemoryDexClassLoader](https://developer.android.com/reference/dalvik/system/InMemoryDexClassLoader) and [ByteBuffer](https://developer.android.com/reference/java/nio/ByteBuffer).

## JNI and Native Library Hooking

### Intercept RegisterNatives (dynamic JNI registration)

Apps that use `RegisterNatives` in `JNI_OnLoad` don't export `Java_com_...` symbols — `nm` and `strings` won't find them. Hook `RegisterNatives` itself to discover them.

```javascript
// Hook RegisterNatives to capture dynamically registered JNI methods
Java.perform(() => {
    const artModule = Process.getModuleByName('libart.so');
    // RegisterNatives is exported from libart.so
    const symbols = artModule.enumerateExports();
    const regNatives = symbols.find(s => s.name.includes('RegisterNatives'));
    if (regNatives) {
        Interceptor.attach(regNatives.address, {
            onEnter(args) {
                const env = args[0];
                const jclass = args[1];
                const methods = args[2];
                const nMethods = args[3].toInt32();
                console.log(`[RegisterNatives] registering ${nMethods} methods`);
                for (let i = 0; i < nMethods; i++) {
                    const namePtr = methods.add(i * Process.pointerSize * 3).readPointer();
                    const sigPtr  = methods.add(i * Process.pointerSize * 3 + Process.pointerSize).readPointer();
                    const fnPtr   = methods.add(i * Process.pointerSize * 3 + Process.pointerSize * 2).readPointer();
                    console.log(`  [${i}] ${namePtr.readCString()} ${sigPtr.readCString()} → ${fnPtr}`);
                    // Now hook the actual native function:
                    Interceptor.attach(fnPtr, {
                        onEnter(args) {
                            console.log(`[native] ${namePtr.readCString()} called`);
                        }
                    });
                }
            }
        });
    }
});
```

### Hook non-exported symbols (offset/pattern-based)

When a function is stripped (no symbol in `.dynsym`), find it by offset from Ghidra/IDA or by byte pattern.

```javascript
// By offset (get offset from Ghidra: Function address - image base)
const mod = Process.getModuleByName('libprotected.so');
const targetAddr = mod.base.add(0x1A3C); // offset from static analysis
Interceptor.attach(targetAddr, {
    onEnter(args) {
        console.log('[stripped_fn] called');
        console.log('  arg0=' + args[0] + ' arg1=' + args[1]);
    },
    onLeave(retval) {
        console.log('[stripped_fn] returned ' + retval);
    }
});
```

```javascript
// By pattern scan (ARM64 instruction sequence from disassembly)
const mod = Process.getModuleByName('libprotected.so');
Memory.scan(mod.base, mod.size, 'FF 43 01 D1 F8 5F 02 A9', {
    onMatch(address, size) {
        console.log('[pattern] found target at ' + address);
        Interceptor.attach(address, {
            onEnter(args) { console.log('[target] hit'); }
        });
    },
    onComplete() { console.log('[pattern] scan done'); }
});
```

### Trace JNI string/data crossing the bridge

```javascript
// Hook GetStringUTFChars to see every string passed across JNI
const libart = Process.getModuleByName('libart.so');
const getStr = libart.findExportByName('_ZN3art3JNI18GetStringUTFCharsEP7_JNIEnvP8_jstringPh');
if (getStr) {
    Interceptor.attach(getStr, {
        onLeave(retval) {
            if (!retval.isNull()) {
                console.log('[JNI] GetStringUTFChars → ' + retval.readCString());
            }
        }
    });
}
```

## Frida Gadget Embedding (No Root Required)

When root is unavailable, embed Frida Gadget (a `.so` library) directly in the APK. The app loads it on startup, enabling instrumentation without `frida-server`.

### Automated: objection patchapk

```bash
# Requires: apktool, aapt, jarsigner/apksigner, adb
objection patchapk --source target.apk
# Produces: target.objection.apk (Gadget injected, re-signed)
adb install target.objection.apk

# Connect (Gadget listens on USB by default):
frida -U Gadget
# Or with a script:
frida -U Gadget -l hook.js
```

### Manual Gadget injection

```bash
# 1. Decompile
apktool d target.apk -o unpacked

# 2. Download matching Gadget .so
# https://github.com/frida/frida/releases → frida-gadget-<ver>-android-arm64.so.xz
xz -d frida-gadget-*-android-arm64.so.xz
mkdir -p unpacked/lib/arm64-v8a/
cp frida-gadget-*-android-arm64.so unpacked/lib/arm64-v8a/libfrida-gadget.so

# 3. Inject smali loader in the main Activity's <clinit> or onCreate:
#    Add to smali: const-string v0, "frida-gadget"
#                  invoke-static {v0}, Ljava/lang/System;->loadLibrary(Ljava/lang/String;)V

# 4. Add INTERNET permission if missing:
#    <uses-permission android:name="android.permission.INTERNET"/>

# 5. Rebuild + sign
apktool b unpacked -o patched.apk
zipalign -v 4 patched.apk aligned.apk
apksigner sign --ks debug.keystore aligned.apk
adb install aligned.apk
```

### Script-mode Gadget (auto-load a JS agent)

Place a config file alongside the `.so`:

```json
// unpacked/lib/arm64-v8a/libfrida-gadget.config.so  (yes, .config.so)
{
    "interaction": {
        "type": "script",
        "path": "/data/local/tmp/agent.js"
    }
}
```

Push the agent: `adb push agent.js /data/local/tmp/agent.js`. The Gadget loads and executes it automatically on app start — persistent instrumentation without root or USB.

## Comprehensive Root Detection Bypass

Simple `isRooted → false` stubs catch trivial checks. Real apps (banking, fintech) use layered detection: file checks, property checks, package manager, `Runtime.exec`, process listing, and SafetyNet/Play Integrity.

```javascript
Java.perform(() => {
    // --- File.exists() for su/magisk/busybox ---
    const File = Java.use('java.io.File');
    const rootPaths = ['su', 'busybox', 'magisk', 'Superuser.apk', 'daemonsu',
                       'supersu', '.magisk', 'init.magisk.rc'];
    File.exists.implementation = function() {
        const path = this.getAbsolutePath();
        if (rootPaths.some(p => path.toLowerCase().includes(p))) {
            console.log('[root-bypass] File.exists(' + path + ') → false');
            return false;
        }
        return this.exists();
    };

    // --- Runtime.exec() for 'which su', 'id' ---
    const Runtime = Java.use('java.lang.Runtime');
    Runtime.exec.overload('java.lang.String').implementation = function(cmd) {
        if (/\bsu\b|\bmagisk\b|\bbusybox\b/.test(cmd)) {
            console.log('[root-bypass] exec("' + cmd + '") → IOException');
            throw Java.use('java.io.IOException').$new('denied');
        }
        return this.exec(cmd);
    };
    Runtime.exec.overload('[Ljava.lang.String;').implementation = function(cmds) {
        const joined = cmds.join(' ');
        if (/\bsu\b|\bmagisk\b|\bbusybox\b/.test(joined)) {
            console.log('[root-bypass] exec(' + joined + ') → IOException');
            throw Java.use('java.io.IOException').$new('denied');
        }
        return this.exec(cmds);
    };

    // --- PackageManager: hide root packages ---
    const rootPkgs = ['eu.chainfire.supersu', 'com.topjohnwu.magisk',
                      'com.koushikdutta.superuser', 'com.noshufou.android.su',
                      'com.thirdparty.superuser', 'me.phh.superuser',
                      'com.yellowes.su', 'com.kingroot.kinguser'];
    const PM = Java.use('android.app.ApplicationPackageManager');
    PM.getPackageInfo.overload('java.lang.String', 'int').implementation = function(pkg, flags) {
        if (rootPkgs.includes(pkg)) {
            console.log('[root-bypass] getPackageInfo(' + pkg + ') → NameNotFound');
            throw Java.use('android.content.pm.PackageManager$NameNotFoundException').$new(pkg);
        }
        return this.getPackageInfo(pkg, flags);
    };

    // --- Build properties (emulator/root indicators) ---
    const Build = Java.use('android.os.Build');
    Build.TAGS.value = 'release-keys';  // hide 'test-keys'

    // --- Debug detection ---
    const Debug = Java.use('android.os.Debug');
    Debug.isDebuggerConnected.implementation = function() { return false; };

    // --- RootBeer (common library) ---
    try {
        const RootBeer = Java.use('com.scottyab.rootbeer.RootBeer');
        RootBeer.isRooted.implementation = function() { return false; };
        RootBeer.isRootedWithoutBusyBoxCheck.implementation = function() { return false; };
        RootBeer.detectRootManagementApps.implementation = function() { return false; };
        RootBeer.detectPotentiallyDangerousApps.implementation = function() { return false; };
        RootBeer.detectTestKeys.implementation = function() { return false; };
        RootBeer.checkForBinary.overload('java.lang.String').implementation = function() { return false; };
        RootBeer.checkForDangerousProps.implementation = function() { return false; };
        RootBeer.checkForRWPaths.implementation = function() { return false; };
        RootBeer.checkSuExists.implementation = function() { return false; };
        RootBeer.checkForRootNative.implementation = function() { return false; };
        RootBeer.checkForMagiskBinary.implementation = function() { return false; };
        console.log('[root-bypass] RootBeer neutralized');
    } catch(e) {}

    console.log('[root-bypass] all layers active');
});
```

## iOS Setup

```bash
# Requirements: jailbroken device with frida-server
# Install via Cydia: Frida (from https://build.frida.re)

# Or SSH + install manually:
scp frida-server-<ver>-ios-arm64 root@<device_ip>:/usr/sbin/frida-server
ssh root@<device_ip> "chmod 755 /usr/sbin/frida-server && frida-server &"

# List apps
frida-ps -Ua                          # USB
frida-ps -Ha                          # SSH (frida-ps -H <host>)

# Attach
frida -U -n "com.example.app"
frida -U -f com.example.app
```

## ObjC Method Hooking (iOS)

```javascript
// Hook ObjC method
const hook = ObjC.classes.SomeClass['- someMethod:withArg:'];
Interceptor.attach(hook.implementation, {
    onEnter(args) {
        // args[0] = self, args[1] = selector, args[2...] = method args
        const self = new ObjC.Object(args[0]);
        const arg = new ObjC.Object(args[2]);
        console.log(`[hook] -[SomeClass someMethod:${arg.toString()}]`);
    },
    onLeave(retval) {
        console.log(`[hook] returned ${retval}`);
        retval.replace(ptr(1)); // Modify return value
    }
});
```

### Enumerate ObjC classes

```javascript
// Find classes with specific keywords
Object.keys(ObjC.classes).forEach(name => {
    if (/ssl|cert|pin|trust|http/i.test(name)) {
        console.log(`[class] ${name}`);
    }
});

// List all methods of a class
const clazz = ObjC.classes.AFSecurityPolicy;
clazz.$ownMethods.forEach(m => console.log(m));
```

## frida-trace Usage

```bash
# Trace all ObjC methods in a module
frida-trace -U -f com.example.app \
    -m "-[NSURLSession *]" \
    -m "-[NSURLConnection *]"

# Trace Java methods
frida-trace -U -f com.example.app \
    -j "com.example.app.CryptoManager!*"

# Trace native exports
frida-trace -U -f com.example.app \
    -i "SSL_*" \
    -i "AES*"
```

Generated handlers are in `__handlers__/` — edit them to customize output.

## Anti-Frida Detection and Evasion

Apps detect Frida through several vectors. Returning `-1` on `/proc/self/maps` open crashes any app that legitimately reads it — use **filter-and-rewrite** instead.

### Detection vectors

| Vector | What the app checks |
|--------|--------------------|
| `/proc/self/maps` | Entries containing `frida`, `gadget`, `gum`, `linjector` |
| Thread names | `/proc/self/task/<tid>/comm`: `gum-js-loop`, `gmain`, `gdbus`, `pool-frida` |
| TCP ports | `connect()` to `127.0.0.1:27042` / `27043` |
| Named pipes | `/proc/self/fd` symlinks containing `frida` |
| File existence | `access("/data/local/tmp/frida-server")`, `libfrida-gadget.so` |
| Memory scan | Byte patterns `FRIDA`, `GUM_`, frida-agent magic in `rwxp` pages |
| D-Bus probe | Send `AUTH\r\n` to open ports, check for frida-server D-Bus response |

### Filter /proc/self/maps (rewrite, don't block)

```javascript
// Hook BufferedReader.readLine() to filter frida entries from /proc/self/maps
// This is safer than blocking open() — the app still reads maps, just without frida lines
Java.perform(() => {
    const BufferedReader = Java.use('java.io.BufferedReader');
    const original = BufferedReader.readLine.overload();
    original.implementation = function() {
        const line = original.call(this);
        if (line !== null) {
            const l = line.toLowerCase();
            if (l.includes('frida') || l.includes('gadget') || l.includes('gum-js') ||
                l.includes('linjector') || l.includes('agent-') || l.includes('/data/local/tmp/')) {
                // Return next non-frida line instead of null
                return original.call(this);
            }
        }
        return line;
    };
});
```
