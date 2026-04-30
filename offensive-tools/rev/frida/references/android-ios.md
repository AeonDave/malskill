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

## JNI (Native Library) Hooking

```javascript
// Hook JNI_OnLoad to intercept native library initialization
Interceptor.attach(Module.getExportByName('libsecure.so', 'JNI_OnLoad'), {
    onEnter(args) {
        console.log('[JNI_OnLoad] native lib initializing');
    },
    onLeave(retval) {
        // After JNI_OnLoad: native methods are registered, safe to hook them now
        console.log('[JNI_OnLoad] done, registering hooks on native methods');
        // Hook exported native methods here
        hookNativeMethods();
    }
});

function hookNativeMethods() {
    // Hook native method exported from JNI library
    const lib = 'libsecure.so';
    Interceptor.attach(Module.getExportByName(lib, 'Java_com_example_NativeLib_decrypt'), {
        onEnter(args) {
            // JNI args: args[0]=JNIEnv, args[1]=jobj, args[2...]=actual args
            const ciphertext = args[2];
            console.log(`[JNI decrypt] input: ${ciphertext}`);
        },
        onLeave(retval) {
            console.log(`[JNI decrypt] output: ${retval}`);
        }
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

## Anti-Frida Detection Bypass

```javascript
// Some apps detect Frida by checking:
// 1. /proc/self/maps for frida-agent
// 2. Port 27042 open
// 3. Module name "frida"
// 4. Memory scan for FRIDA_INIT pattern

// Bypass: use -gadget or custom frida-server port
frida -U -f com.example.app --runtime=v8

// Or patch detection with:
Interceptor.attach(Module.findExportByName(null, 'open'), {
    onEnter(args) {
        const path = args[0].readUtf8String();
        if (path && path.includes('/proc/self/maps')) {
            this.fake = true;
        }
    },
    onLeave(retval) {
        if (this.fake) retval.replace(ptr(-1)); // ENOENT
    }
});
```
