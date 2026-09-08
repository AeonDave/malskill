# Frida — Android & iOS Instrumentation

## Android Setup

```bash
# Download frida-server matching device arch
# https://github.com/frida/frida/releases
# Architectures: arm, arm64, x86, x86_64

# Push and start
adb push frida-server-<ver>-android-arm64 /data/local/tmp/frida-server
adb shell chmod 755 /data/local/tmp/frida-server
adb shell /data/local/tmp/frida-server &

# List apps
frida-ps -Ua              # USB, applications only
frida-ps -Uai             # With bundle identifiers

# Attach to app
frida -U -n "com.example.app"
frida -U -f com.example.app --no-pause    # Spawn + attach

# Run script
frida -U -f com.example.app -l hook.js --no-pause
```

## SSL Pinning Bypass (Android)

### Universal bypass (Frida CodeShare)

```javascript
// Based on: https://codeshare.frida.re/@pcipolloni/universal-android-ssl-pinning-bypass-with-frida/
Java.perform(() => {
    // Method 1: OkHttp3 pin bypass
    try {
        const CertificatePinner = Java.use('okhttp3.CertificatePinner');
        CertificatePinner.check.overload('java.lang.String', 'java.util.List')
            .implementation = function() {
                console.log('[bypass] OkHttp3 CertificatePinner bypassed');
            };
    } catch(e) {}

    // Method 2: TrustManager bypass
    try {
        const X509TrustManager = Java.use('javax.net.ssl.X509TrustManager');
        const SSLContext = Java.use('javax.net.ssl.SSLContext');
        const TrustManager = Java.registerClass({
            name: 'com.custom.TrustManager',
            implements: [X509TrustManager],
            methods: {
                checkClientTrusted(chain, authType) {},
                checkServerTrusted(chain, authType) {},
                getAcceptedIssuers() { return []; }
            }
        });
        const ctx = SSLContext.getInstance('TLS');
        ctx.init(null, [TrustManager.$new()], null);
        SSLContext.getInstance.overload('java.lang.String')
            .implementation = function(p) { return ctx; };
        console.log('[bypass] TrustManager replaced');
    } catch(e) {}

    // Method 3: Conscrypt
    try {
        const OkHostnameVerifier = Java.use('okhttp3.internal.tls.OkHostnameVerifier');
        OkHostnameVerifier.verify.overload('java.lang.String', 'javax.net.ssl.SSLSession')
            .implementation = function() { return true; };
    } catch(e) {}
});
```

### Root certificate store bypass

```bash
# Use frida-cert-pinning-bypass (all-in-one):
frida -U -f com.example.app \
    --codeshare pcipolloni/universal-android-ssl-pinning-bypass-with-frida \
    --no-pause
```

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

```javascript
Java.perform(() => {
    // javax.crypto.Cipher hook
    const Cipher = Java.use('javax.crypto.Cipher');

    Cipher.doFinal.overload('[B').implementation = function(input) {
        const algorithm = this.getAlgorithm();
        console.log(`[Cipher.doFinal] algo=${algorithm} input=${bytesToHex(input)}`);
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

Packed/obfuscated apps load DEX at runtime via `DexClassLoader`. Hook to capture.

```javascript
Java.perform(() => {
    // Intercept dynamic DEX loading
    const DexClassLoader = Java.use('dalvik.system.DexClassLoader');
    DexClassLoader.$init.implementation = function(dexPath, optDir, libPath, parent) {
        console.log(`[DexClassLoader] dexPath=${dexPath}`);
        return this.$init(dexPath, optDir, libPath, parent);
    };

    // InMemoryDexClassLoader (API 26+) — no file path, DEX in memory
    try {
        const InMemoryDexClassLoader = Java.use('dalvik.system.InMemoryDexClassLoader');
        InMemoryDexClassLoader.$init.overload('java.nio.ByteBuffer', 'java.lang.ClassLoader')
            .implementation = function(buf, parent) {
                const bytes = Java.array('byte', buf.array());
                console.log(`[InMemoryDexClassLoader] ${bytes.length} bytes`);
                // Dump to file:
                const f = Java.use('java.io.FileOutputStream').$new('/sdcard/dumped.dex');
                f.write(bytes);
                f.close();
                return this.$init(buf, parent);
            };
    } catch(e) {}
});
```

## JNI and Native Library Hooking

### Hook JNI_OnLoad

```javascript
Interceptor.attach(Module.getExportByName('libsecure.so', 'JNI_OnLoad'), {
    onEnter(args) {
        console.log('[JNI_OnLoad] native lib initializing');
    },
    onLeave(retval) {
        console.log('[JNI_OnLoad] done, hooking native methods');
        hookNativeMethods();
    }
});

function hookNativeMethods() {
    const lib = 'libsecure.so';
    Interceptor.attach(Module.getExportByName(lib, 'Java_com_example_NativeLib_decrypt'), {
        onEnter(args) {
            // args[0]=JNIEnv, args[1]=jobj, args[2...]=actual params
            console.log(`[JNI decrypt] input: ${args[2]}`);
        },
        onLeave(retval) {
            console.log(`[JNI decrypt] output: ${retval}`);
        }
    });
}
```

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

### Monitor dlopen for late-loaded `.so`

Malware and packers often load `.so` files after initial startup. Hook `dlopen`/`android_dlopen_ext` to catch them.

```javascript
['dlopen', 'android_dlopen_ext'].forEach(fn => {
    const addr = Module.findExportByName(null, fn);
    if (addr) {
        Interceptor.attach(addr, {
            onEnter(args) {
                const path = args[0].readCString();
                if (path) console.log(`[${fn}] loading: ${path}`);
                this.path = path;
            },
            onLeave(retval) {
                if (this.path && !retval.isNull()) {
                    console.log(`[${fn}] loaded at ${retval}: ${this.path}`);
                    // Now you can hook exports from the freshly loaded lib:
                    const mod = Process.getModuleByName(this.path.split('/').pop());
                    if (mod) {
                        mod.enumerateExports().forEach(e => {
                            if (e.name.includes('JNI_OnLoad') || e.name.startsWith('Java_')) {
                                console.log(`  export: ${e.name} @ ${e.address}`);
                            }
                        });
                    }
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

## Modern SSL Pinning (OkHttp4 / gRPC / Cronet / Flutter)

When the basic TrustManager/OkHttp3 bypass doesn't work, the app may use a newer stack.

```javascript
Java.perform(() => {
    // --- OkHttp4 CertificatePinner (internal API changed) ---
    try {
        const Pinner = Java.use('okhttp3.CertificatePinner');
        Pinner.check.overload('java.lang.String', 'java.util.List').implementation = function() {};
        try { Pinner['check$okhttp'].implementation = function() {}; } catch(e) {}
        console.log('[bypass] OkHttp4 CertificatePinner disabled');
    } catch(e) {}

    // --- Cronet / gRPC BoringSSL ---
    try {
        const CronetB = Java.use('org.chromium.net.CronetEngine$Builder');
        CronetB.enablePublicKeyPinningBypassForLocalTrustAnchors
            .overload('boolean').implementation = function() { return this; };
    } catch(e) {}

    // --- Conscrypt (Android 7+ default TLS provider) ---
    try {
        const TMI = Java.use('com.android.org.conscrypt.TrustManagerImpl');
        TMI.verifyChain.implementation = function(untrustedChain) {
            console.log('[bypass] Conscrypt verifyChain bypassed');
            return untrustedChain;
        };
    } catch(e) {}

    // --- WebView SSL errors ---
    try {
        const WebViewClient = Java.use('android.webkit.WebViewClient');
        WebViewClient.onReceivedSslError.implementation = function(view, handler, error) {
            handler.proceed();
        };
    } catch(e) {}
});
```

For **Flutter** apps: Flutter uses BoringSSL compiled into `libflutter.so` — Java hooks don't apply. Patch at the native level:

```javascript
// Flutter SSL bypass — hook ssl_crypto_x509_session_verify_cert_chain in libflutter.so
const flutter = Process.getModuleByName('libflutter.so');
// Pattern for ssl_verify_peer_cert (varies by Flutter version)
// Find via: strings libflutter.so | grep ssl_client
const verifyFunc = Module.findExportByName('libflutter.so', 'ssl_verify_peer_cert');
if (verifyFunc) {
    Interceptor.replace(verifyFunc, new NativeCallback(() => 0, 'int', ['pointer', 'pointer']));
    console.log('[bypass] Flutter SSL verify patched');
} else {
    // Fallback: pattern scan for the verify function
    Memory.scan(flutter.base, flutter.size, '08 40 B9 ?? ?? ?? 94 28 00 80 52', {
        onMatch(addr) {
            console.log('[bypass] Flutter SSL pattern at ' + addr);
            // NOP the branch or replace return
        },
        onComplete() {}
    });
}
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

### iOS SSL pinning bypass

```javascript
// Hook SecTrustEvaluate (common SSL pinning method)
const SecTrustEvaluate = Module.findExportByName('Security', 'SecTrustEvaluate');
if (SecTrustEvaluate) {
    Interceptor.attach(SecTrustEvaluate, {
        onLeave(retval) {
            // errSecSuccess = 0
            retval.replace(ptr(0));
            console.log('[bypass] SecTrustEvaluate → success');
        }
    });
}

// Also hook SecTrustEvaluateWithError (iOS 12+)
const SecTrustEvaluateWithError = Module.findExportByName('Security', 'SecTrustEvaluateWithError');
if (SecTrustEvaluateWithError) {
    Interceptor.attach(SecTrustEvaluateWithError, {
        onLeave(retval) {
            retval.replace(ptr(1)); // Returns bool: true = trusted
        }
    });
}
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

### Operational evasion (before hooking)

```bash
# 1. Rename frida-server binary
cp frida-server /data/local/tmp/fs-16.5.2

# 2. Change default port
/data/local/tmp/fs-16.5.2 -l 127.0.0.1:31337 &
frida -H 127.0.0.1:31337 -f com.example.app

# 3. Use spawn mode (attach before detection code runs)
frida -U -f com.example.app -l bypass.js --no-pause

# 4. Gadget mode (no frida-server process at all)
# See "Frida Gadget Embedding" section above

# 5. Community anti-detection frida-server builds (e.g. hluwa's strongR-frida-android)
# Patch Frida artifacts: rename threads, strip in-memory magic bytes ("frida:rpc", "GUM_"),
# rename modules (linjector, gum-js-loop). Search GitHub for the current maintained fork —
# specific repos and forks come and go; verify signatures before use.
```

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

### Native-level evasion (libc hooks)

```javascript
// Filter /proc/self/maps at the C level (catches native detection too)
const openPtr = Module.findExportByName('libc.so', 'open');
const readPtr = Module.findExportByName('libc.so', 'read');

Interceptor.attach(openPtr, {
    onEnter(args) {
        const path = args[0].readCString();
        this.isMaps = path && (path.includes('/proc/self/maps') || path.includes('/proc/self/status'));
    },
    onLeave(retval) {
        if (this.isMaps) this.fd = retval.toInt32();
    }
});

// Hook pthread_setname_np to hide Frida thread names
const setname = Module.findExportByName('libc.so', 'pthread_setname_np');
if (setname) {
    Interceptor.attach(setname, {
        onEnter(args) {
            const name = args[1].readCString();
            if (name && /gum-js|gmain|gdbus|pool-frida|linjector/.test(name)) {
                args[1].writeUtf8String('binder:' + Process.id);
            }
        }
    });
}

// Block connect() to detection probe ports
const connectPtr = Module.findExportByName('libc.so', 'connect');
Interceptor.attach(connectPtr, {
    onEnter(args) {
        const sockaddr = args[1];
        const family = sockaddr.readU16();
        if (family === 2) { // AF_INET
            const port = (sockaddr.add(2).readU8() << 8) | sockaddr.add(3).readU8();
            if (port === 27042 || port === 27043) {
                console.log('[anti-detect] blocking connect to port ' + port);
                args[0] = ptr(-1); // invalid fd
            }
        }
    }
});

// Neuter ptrace-based anti-debug
const ptrace = Module.findExportByName('libc.so', 'ptrace');
if (ptrace) {
    Interceptor.replace(ptrace, new NativeCallback(function(req, pid, addr, data) {
        if (req === 0) { // PTRACE_TRACEME
            console.log('[anti-debug] ptrace(TRACEME) → 0');
            return 0;
        }
        return -1;
    }, 'long', ['int', 'int', 'pointer', 'pointer']));
}
```

### Combined anti-detection script invocation

```bash
# Rename server + custom port + spawn with bypass:
/data/local/tmp/fs-server -l 127.0.0.1:31337 &
frida -H 127.0.0.1:31337 -f com.example.app -l anti-detect.js --no-pause
```
