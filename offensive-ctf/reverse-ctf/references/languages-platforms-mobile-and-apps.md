# CTF Reverse - Mobile and Application Platform Techniques

Focused platform reference for Android-heavy, app-bundled, or service-backed artifacts where the real logic is split between app code, native helpers, and cloud or local platform services.

## Table of Contents
- [Android JNI RegisterNatives Obfuscation](#android-jni-registernatives-obfuscation)
- [Android DEX Runtime Bytecode Patching](#android-dex-runtime-bytecode-patching)
- [Android Native .so Loading Bypass](#android-native-so-loading-bypass)
- [Frida Firebase Cloud Functions Bypass](#frida-firebase-cloud-functions-bypass)
- [Frida Android Pinning Bypass by Direct Invocation](#frida-android-pinning-bypass-by-direct-invocation)
- [Android Anti-Debug and Root Checks](#android-anti-debug-and-root-checks)
- [Android Log-Based Key Extraction](#android-log-based-key-extraction)
- [Native JNI Key Extraction via Memory Dump and Smali Patching](#native-jni-key-extraction-via-memory-dump-and-smali-patching)
- [Android Smali Injection for Local Broadcast Logic](#android-smali-injection-for-local-broadcast-logic)
- [Electron App plus Native Binary Reversing](#electron-app-plus-native-binary-reversing)
- [Node.js Package Runtime Introspection](#nodejs-package-runtime-introspection)
- [Intel SGX Enclave Reverse Engineering](#intel-sgx-enclave-reverse-engineering)

## Android JNI RegisterNatives Obfuscation

Always inspect `JNI_OnLoad` when native method names do not map to standard JNI exports. `RegisterNatives` arrays often reveal the true native entry points immediately.

## Android DEX Runtime Bytecode Patching

If the native library rewrites Dalvik bytecode in memory, reconstruct the patched DEX offline by extracting the XOR key, offsets, and checksum updates from the native side.

## Android Native .so Loading Bypass

When Java gates are noisy, recreate only the package/class/native signature you need in a clean project and call the original native method directly.

## Frida Firebase Cloud Functions Bypass

Cloud-function validators are often only lightly wrapped. Post-authentication, hook the app, recover the current UID/session state, and call the function directly with a valid payload shape.

## Frida Android Pinning Bypass by Direct Invocation

Sometimes the secret is already in a JNI-accessible method. Calling the method from Frida is faster than proxying traffic.

## Android Anti-Debug and Root Checks

Model the sequence:
- `TracerPid`
- `su` or root binary checks
- system properties
- occasionally timing or emulator markers

Statically derive the success path or patch the gate.

## Android Log-Based Key Extraction

Verbose crypto logging is a gift. Mine `logcat` for base agreements, ephemeral values, counters, or derived IV material before attempting protocol reimplementation.

## Native JNI Key Extraction via Memory Dump and Smali Patching

For request-signing schemes, dumping the post-deobfuscation key plus redirecting which parameter gets signed is often dramatically cheaper than fully reversing the native algorithm.

## Android Smali Injection for Local Broadcast Logic

If `LocalBroadcastManager` hides the only path to the flag, inline or relocate the receiver logic into a code path that runs automatically and log the result.

## Electron App plus Native Binary Reversing

Unpack the ASAR archive first; then hunt for the real native binary and the JS glue that reveals argument shapes, file locations, or crypto flow.

## Node.js Package Runtime Introspection

For heavily obfuscated npm packages, runtime reflection (`Object.getOwnPropertyNames`) beats static beautification more often than not.

## Intel SGX Enclave Reverse Engineering

SGX enclave code is still x86-64. Focus on ECALL tables, attestation flow, and deterministic key derivation rather than mystifying the enclave boundary.
