# Hooking vs Patching — Choosing the Intervention

Load when planning: static patch (this skill), Frida hook, LSPosed module, or a combination? Each has trade-offs.

## Decision matrix

| Situation | Prefer |
|-----------|--------|
| Target detects Frida (`TracerPid`, port 27042 scan, `libfrida-gadget.so` name) | **Static patch** |
| Target ships a `.so` that verifies its own hash → any repack fails | **Frida hook** |
| Need persistent effect across app updates from Play | **Neither works** long-term; patch each release |
| Rapid iteration, exploration ("what does this method do if I return X?") | **Frida hook** |
| Locked-down device without root or Frida server | **Static patch** |
| CTF flag extraction, offline analysis | **Static patch** (simpler PoC) |
| Runtime data collection (network calls, argument values) | **Frida hook** |
| System-wide behavior across multiple apps | **LSPosed module** |
| Native code checks (`.so` returns "tampered") | **Frida hook** on the native function OR patch the `.so` |
| Need to inject a whole new library / new feature | **LSPosed module** or static patch + injected classes |

## Static patch (this skill)

**Pros:**

- Works on locked-down devices — no root, no Frida server, no Magisk.
- Detection-resistant: no runtime footprint, no unusual `.so` loaded, no proc scan visible.
- Persistent across reboots and app data wipes.
- Faster to hand off ("here's the patched APK").

**Cons:**

- Slow iteration: decompile → edit → rebuild → sign → install per change.
- Cannot easily observe runtime state (arguments, return values) without adding log statements.
- Breaks with each app update — requires re-patching new versions.
- Signature key differs from Play install; app can't receive Play updates without uninstall/reinstall.

## Frida hooking

**Pros:**

- Rapid iteration; hook, test, re-hook without APK rebuild.
- Observe and modify state at runtime (arguments, return values, native memory).
- Works on already-installed apps without repacking.
- Handles arbitrary native and Java code uniformly.

**Cons:**

- Detected easily by apps that scan for it:
  - `frida-server` port scan
  - `libfrida-gadget.so` name in `/proc/self/maps`
  - `TracerPid != 0` in `/proc/self/status`
  - Named threads (`gum-js-loop`, `gmain`, `frida-server`)
- Requires either root + `frida-server` running on device, or `frida-gadget` embedded in a patched APK (which converges to static patching).
- Non-persistent: reboot loses the hook.
- Modification limited to what the runtime API exposes (no bytecode structure changes).

## LSPosed / Xposed modules

**Pros:**

- System-wide hooks across apps (persistent, one module targets many apps).
- Rich hook API; can replace method implementations at load time.
- Works well for platform-level modifications (bypass ads, integrity, etc.).

**Cons:**

- Requires rooted device + Zygisk (LSPosed) / classic Xposed (deprecated).
- Detected by integrity checks (some apps scan for LSPosed).
- Module development curve steeper than Frida script.

## Combined approach

The most effective real-world flow is often a combination:

1. **Frida to explore**: hook every promising method, observe arguments, understand the check logic.
2. **Static patch to persist**: once you know exactly what to change, patch the smali for a stable PoC or handoff artifact.

Example workflow for SSL pinning bypass in a hostile target:

1. Try Frida universal SSL bypass script → app crashes with "Frida detected".
2. Read the Frida-detection code with jadx.
3. Static-patch the Frida detector to return false → rebuild, sign, install.
4. Run Frida universal bypass → works.
5. Confirm interception, dump traffic, done.

Or for pure static:

1. Read code with jadx, identify pinning classes.
2. Patch OkHttp `CertificatePinner.check` and custom `TrustManager` returns.
3. Rebuild, sign, install.
4. Configure Burp with user CA in `network_security_config.xml`.
5. Traffic flows to Burp without Frida involvement.

## When patching fails: switch to Frida

Symptoms that suggest patching won't work:

- APK has a native `.so` that computes a hash of `classes.dex` on load → your patched DEX fails the check.
- APK uses code-integrity via `libjnisig.so` or similar → the `.so` refuses to load with a modified APK.
- APK uses `MethodHandles` and dynamic invocation such that method names are computed at runtime → static patching by name misses call sites.
- Play Integrity is gating server-side, and the client-side bypass alone isn't enough.

Frida on a jailbroken/rooted device sidesteps these because the DEX on disk is unchanged.

## When Frida fails: switch to static patching

Symptoms:

- Every Frida script attach fails with `Frida detected → System.exit(1)`.
- Target uses `ptrace(TRACEME)` self-attach to block debuggers → native anti-debug.
- Target scans `/proc/self/maps` for Frida gadget name.
- Device is a customer-owned test device without root permission.

Static patching's zero-runtime-footprint wins here.

## Native code checks

If the target's tamper-detection is native:

**Option A — patch the `.so` binary**

1. Decompile with `apktool d` (extracts `.so` files).
2. Load `libtarget.so` in Ghidra / Binary Ninja / radare2.
3. Identify the check function (usually a small function returning an int → boolean).
4. Patch bytes to force the return value:
   - x86-64: `mov eax, 1; ret` = `B8 01 00 00 00 C3`
   - arm64: `mov w0, #1; ret` = `20 00 80 52 C0 03 5F D6`
5. Overwrite in the `.so`, replace in `unpacked/lib/<abi>/`.
6. Rebuild APK.

**Option B — Frida hook the native symbol**

```javascript
Interceptor.attach(Module.findExportByName("libtarget.so", "check_integrity"), {
    onLeave: function (retval) {
        retval.replace(1);   // force success
    }
});
```

Frida is faster for exploration; patching wins for handoff and persistence.

## Alternative: `apk-mitm`

For "just get through SSL pinning fast":

```bash
npm install -g apk-mitm
apk-mitm target.apk
```

Automatically strips `network_security_config.xml`, injects a permissive one, patches OkHttp/`TrustManager`. Doesn't cover custom implementations but catches ~80% of cases in ~5 seconds.

## Handoff considerations

- **Static-patched APK** — hand this to your client / write-up; anyone can install and repro.
- **Frida script** — hand off with clear "requires rooted device + frida-server X.Y.Z". Less reproducible for non-technical stakeholders.
- **PoC video** — always safer than either; screen-record the exploitation for report attachments.

## Anti-patterns

- Using Frida to bypass every check when the target detects Frida — wastes time; patch the detector first.
- Static-patching when server-side integrity blocks anyway — the effort doesn't map to impact.
- Not documenting what you patched — six months later, you can't reproduce your own work.
- Combining Frida hooks with unrelated static patches in the same PR — hard to attribute regressions.
- Assuming an installed patched APK will survive Play auto-update — it won't; Play refuses to update over a mismatched signing key.

## Rule of thumb

- **Fast triage / exploration**: Frida.
- **Handoff artifact / persistence / detection resistance**: static patch.
- **Native code**: Frida for exploration, `.so` byte patch for handoff.
- **System-wide behavior**: LSPosed module (root required).

Frida and this skill are complementary. Neither is universally superior.
