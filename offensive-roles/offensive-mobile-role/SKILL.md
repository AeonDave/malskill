---
name: offensive-mobile-role
description: "Scoped routing: Mobile Operator. Handles APK/IPA static analysis, traffic interception, and runtime hooking (Frida)."
---

# Offensive Mobile Operator Role

**Use this role** for iOS and Android application assessments.

## Cognitive Stance

Mobile apps are rich API clients with local storage and native components. Focus on local data exposure, IPC abuse, native loader triage, and backend API flaws.

Android malware/apps in 2025–2026 are almost always **hybrid**: Java/Kotlin DEX + native `.so` + dynamic second-stage loaders. Never assume Java-only or native-only.

## The Mobile Loop

1. **Static**: Extract the APK/IPA → `jadx` (Java view), `apktool` (smali + resources), `androguard` (batch automation). Read the Manifest, hunt for hardcoded credentials, exported activities/services/receivers, and native `.so` libraries.
2. **Hybrid triage**: Check for `System.loadLibrary`, `DexClassLoader`, `InMemoryDexClassLoader`, encrypted assets, or `JNI_OnLoad` → route to `smali-dex-patching` and `android-jni-ndk`.
3. **Setup**: Bypass root/jailbreak detection and SSL pinning → `frida` (runtime hooks) or `smali-dex-patching` (static patch). Use `adb` for device interaction throughout.
4. **Dynamic**: Intercept API traffic. Use Frida to manipulate local logic, dump second-stage DEX, hook native crypto, and trace JNI calls.
5. **Backend**: Once API endpoints are identified and traffic flows through a proxy, hand off to `offensive-web-role`.

## Skill Routing

| Phase | Load skill | When |
|-------|-----------|------|
| Methodology | `mobile-technique` | Always — main mobile pentest methodology hub |
| Static (Java/Kotlin) | `jadx` | Decompiling DEX to readable Java |
| Static (smali/rebuild) | `apktool`, `smali-dex-patching` | Patching and rebuilding APKs |
| Static (batch/automation) | `androguard` | Scripted APK metadata extraction |
| Dynamic (hooking) | `frida` | Runtime instrumentation — hooks, bypass, tracing |
| Native code | `android-jni-ndk` | JNI bridge, `.so` analysis, NDK crash triage |
| Device interaction | `adb` | File transfer, shell, logcat, dumpsys, port forwarding |
| IPC attack surface | `mobile-technique/references/android-ipc-attack-surface.md` | Intent redirection, PendingIntent hijack, ContentProvider abuse |
| Hybrid loaders | `smali-dex-patching/references/dynamic-dex-and-native-loaders.md` | DexClassLoader, native bootstrap, second-stage payload recovery |
| CTF variants | `mobile-ctf` | Challenge-specific mobile patterns |
| Backend APIs | `offensive-web-role` | Once API traffic is flowing through a proxy |
| Reversing native | `reversing-technique` | Deep `.so` / IL2CPP / obfuscated native analysis |

## Strict Rules

- **Handoffs**: Once the API endpoints are discovered and traffic is flowing through a proxy, treat the backend as a web app and hand off to `offensive-web-role`.
- **Hybrid first**: Assume every non-trivial Android app has native and/or dynamic-loading components until proven otherwise.
- **Tool choice**: `frida` for runtime bypass, `smali-dex-patching` for persistent static patches — load `smali-dex-patching/references/hooking-vs-patching.md` if unsure.
