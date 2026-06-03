---
name: adb
description: "Auth/lab ref: Android Debug Bridge CLI for device discovery, shell access, file transfer, package install, port forwarding, and log collection."
compatibility: "Linux, macOS, Windows; Android platform-tools; works with emulators and USB/TCP devices."
metadata:
  author: AeonDave
  version: "1.0"
---

# adb

The command line hinge between your workstation and an Android device or emulator.

## When to use adb

Use adb when you need to:

- verify connected devices and switch between targets
- open an interactive shell on Android
- install or uninstall APKs during patch/test cycles
- pull or push files, grab logs, or set up forwards for dynamic tooling

## Quick Start

```bash
# List connected devices
adb devices -l

# Open a shell
adb shell

# Install an APK
adb install app.apk
```

## High-Value Workflows

### Files and packages

```bash
adb push local.txt /sdcard/local.txt
adb pull /sdcard/Download/file.txt .
adb uninstall com.example.app
```

### Logs and runtime checks

```bash
adb logcat
adb logcat | grep -i example
adb shell pm list packages
```

### Port bridging for tooling

```bash
adb forward tcp:27042 tcp:27042
adb reverse tcp:8080 tcp:8080
```

## Practical Notes

- Use `adb devices -l` first; it solves a shocking number of "why is nothing happening" moments.
- Pair with `apktool` for patch-and-reinstall loops, `jadx` for static review, and Frida for runtime instrumentation.
- Emulators are great for repeatability; real devices are better for trust-but-verify checks.

## Caveats

- Access to app-private paths depends on device state, app debuggability, and root privileges.
- Patched APKs often need uninstall/reinstall or a matching signing workflow.
- USB authorization dialogs and multiple-device ambiguity can derail automation if you ignore them.

## Resources

No bundled `scripts/`, `references/`, or `assets/`.
Use the official Android platform-tools documentation for device selection, advanced shell subcommands, and wireless debugging.
