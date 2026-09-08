---
name: adb
description: "Auth/lab ref: Android Debug Bridge CLI for device discovery, shell access, package management, `pm`/`am`/`dumpsys`/`cmd` service commands, port forwarding, log collection, wireless debugging (`adb pair` + mDNS on Android 11+), storage/keyboard/screen automation, and baseline-profile inspection. Companion tool to `apktool`, `frida`, `jadx`, Macrobenchmark, and mobile-technique triage."
compatibility: "Linux, macOS, Windows. Android platform-tools 34.0.0+ (guidance covers up to 35.x). Works with USB devices, emulators, and TCP/Wi-Fi devices (mDNS pair on Android 11+). Some commands require rooted / userdebug devices; `pm`/`am`/`dumpsys`/`cmd` typically work on stock retail devices for the user's own installed apps."
metadata:
  author: AeonDave
  version: "1.1"
---

# adb

The command-line hinge between your workstation and an Android device or emulator. Learn the small surface of `adb` itself (device selection, transport, files) and the huge surface of the on-device commands it exposes (`pm`, `am`, `dumpsys`, `cmd`, `settings`, `input`, `screenrecord`, `wm`, `getprop`).

Pair with `apktool` for patch cycles, `frida` for runtime hooking, `jadx` for static review, `mobile-technique` for triage, and Macrobenchmark for on-device performance work.

## Fundamentals

```bash
adb devices -l                      # first line every session — solves 80% of "why nothing works"
adb -s <serial> shell               # target a specific device when multiple attached
adb -e shell                        # emulator only
adb -d shell                        # physical device only

adb kill-server && adb start-server # reset when adb behaves erratically
adb reconnect                       # force USB re-enumeration
adb root                            # request root (userdebug/eng only; noop on stock)
adb unroot                          # revert to shell UID
```

## Wireless debugging (Android 11+)

Modern flow (no USB required after initial pairing):

```bash
# On device: Settings → Developer options → Wireless debugging → Pair device with pairing code
# Note the IP:port and 6-digit code

adb pair <ip>:<port>                # enter the pairing code when prompted
adb connect <ip>:<port>             # actual connect port shown separately in the UI
adb devices -l                      # confirm

# mDNS-based discovery (Android 11+, when device is on same network)
adb mdns services                   # list discoverable devices
adb mdns check                      # verify mDNS working (needs Bonjour/Avahi)
```

Legacy adbd-over-TCP (pre-Android 11, requires root or `su`):

```bash
adb tcpip 5555
adb connect <ip>:5555
```

## Files and packages

```bash
adb push local.txt /sdcard/local.txt
adb pull /sdcard/Download/file.txt .
adb pull /data/data/com.target.app/databases/     # requires root or debuggable app
adb sync                                          # legacy AOSP flow; rarely needed

adb install app.apk
adb install -r app.apk                            # reinstall keeping data
adb install -g app.apk                            # grant all runtime permissions
adb install -t app.apk                            # allow test-only APKs
adb install-multiple base.apk split_*.apk         # split-APK / App Bundle install
adb uninstall com.target.app
adb uninstall -k com.target.app                   # keep app data on uninstall
```

## Shell entry points and `cmd`

Since Android 7 (API 24), `cmd` on-device provides a fast IPC path into system services — often faster than `pm`/`am` wrappers:

```bash
adb shell pm list packages -3                     # third-party (installed by you)
adb shell pm list packages -s                     # system packages
adb shell pm list packages -u                     # includes uninstalled
adb shell pm path com.target.app                  # APK path(s) — output includes splits
adb shell pm dump com.target.app                  # long form: signatures, permissions, activities
adb shell pm grant com.target.app android.permission.CAMERA
adb shell pm revoke com.target.app android.permission.CAMERA
adb shell pm reset-permissions com.target.app
adb shell pm clear com.target.app                 # wipe data
adb shell pm disable-user --user 0 com.target.app # hide without uninstalling
adb shell pm enable com.target.app
adb shell pm compile -m speed-profile com.target.app  # apply Baseline Profile now
adb shell pm dump-profiles com.target.app         # dump ART profile

adb shell cmd package install-existing com.target.app       # re-install pre-existing archive
adb shell cmd package resolve-activity -c android.intent.category.LAUNCHER com.target.app
adb shell cmd notification post -S bigtext tag "Title" "Body"
adb shell cmd overlay list                         # RRO / theming overlays
```

## Starting activities, services, broadcasts

```bash
adb shell am start -n com.target.app/.MainActivity
adb shell am start -a android.intent.action.VIEW -d "https://example.com"
adb shell am start -a android.intent.action.SEND -t text/plain --es android.intent.extra.TEXT "hello"

adb shell am start-service -n com.target.app/.MyService
adb shell am start-foreground-service -n com.target.app/.MyService
adb shell am broadcast -a com.target.CUSTOM_ACTION --es key value

adb shell am force-stop com.target.app             # kill without wiping data
adb shell am kill com.target.app                   # kill background process
adb shell am kill-all                              # kill all background procs

adb shell am switch-user 10                        # multi-user
adb shell am set-debug-app -w com.target.app       # wait for debugger on next launch
adb shell am clear-debug-app
```

## dumpsys — the observability layer

`dumpsys` produces a text dump of a system service's state. Every service has different output; useful subsets:

```bash
adb shell dumpsys activity activities              # activity stack (top of stack, back stack)
adb shell dumpsys activity processes com.target    # process state of your app
adb shell dumpsys activity services com.target     # running services
adb shell dumpsys activity broadcasts               # broadcast queue state (with recent history)
adb shell dumpsys activity intents                  # pending intents
adb shell dumpsys package com.target.app            # everything about installed package
adb shell dumpsys battery                           # battery state (charging, level, etc.)
adb shell dumpsys battery unplug                    # simulate unplugged (for perf tests)
adb shell dumpsys battery reset                     # revert
adb shell dumpsys deviceidle                        # doze / app standby buckets
adb shell dumpsys jobscheduler                      # scheduled jobs; useful for WorkManager triage
adb shell dumpsys alarm                             # alarm manager state
adb shell dumpsys location                          # location providers state
adb shell dumpsys sensorservice                     # active sensors (drain source)
adb shell dumpsys power                             # wakelocks
adb shell dumpsys meminfo com.target.app -d          # detailed memory breakdown
adb shell dumpsys meminfo com.target.app -a          # even more detail (native refs)
adb shell dumpsys gfxinfo com.target.app framestats  # per-frame render timing (jank analysis)
adb shell dumpsys gfxinfo com.target.app reset
adb shell dumpsys window                             # window manager (rotation, keyguard)
adb shell dumpsys input                              # input devices, IME
adb shell dumpsys wifi                               # Wi-Fi state
adb shell dumpsys netstats                           # per-app data usage
adb shell dumpsys statusbar                          # SystemUI status bar
adb shell dumpsys media_session                      # active audio sessions
adb shell dumpsys package packages | grep -i target  # search all packages
```

Pipe through `less` or filter with `grep` — full dumps often exceed 10k lines.

## Logs

```bash
adb logcat                                          # all
adb logcat -c                                       # clear buffer
adb logcat -d                                       # dump and exit
adb logcat -v threadtime                            # richer format with tid
adb logcat -v time,color,tag                        # colored, prefixed by tag

adb logcat *:E                                      # errors and above from all tags
adb logcat -s ActivityManager:V AndroidRuntime:E    # specific tags + level
adb logcat --pid $(adb shell pidof com.target.app) # only your app
adb logcat | grep -iE 'crash|exception|died'

adb logcat -f /sdcard/log.txt &                     # write to file on device
adb bugreport bugreport.zip                         # comprehensive dump (dumpstate + logcat + kernel)
```

## Property system (`getprop` / `setprop`)

```bash
adb shell getprop                                   # all properties
adb shell getprop ro.build.version.release          # Android version (e.g. "14")
adb shell getprop ro.build.version.sdk              # API level (e.g. "34")
adb shell getprop ro.product.model                  # device model
adb shell getprop ro.product.manufacturer
adb shell getprop ro.product.cpu.abilist            # supported ABIs
adb shell getprop ro.serialno
adb shell getprop dalvik.vm.heapmaxfree             # ART memory tuning
adb shell getprop ro.build.fingerprint              # useful for emulator detection

adb shell setprop <key> <value>                     # requires root; runtime-only
```

## Port forwarding

```bash
adb forward tcp:8888 tcp:80                         # forward host:8888 → device:80
adb forward tcp:27042 tcp:27042                     # Frida default
adb forward tcp:0 tcp:80                            # let host pick a free port; prints assigned
adb forward --list
adb forward --remove tcp:8888
adb forward --remove-all

adb reverse tcp:8080 tcp:8080                       # forward device:8080 → host:8080 (mock server)
adb reverse --list
```

Reverse is invaluable during dev — the device can `curl http://localhost:8080` and hit your workstation.

## UI automation and screen

```bash
adb shell input tap 500 900                         # tap at coords
adb shell input swipe 100 500 900 500 200           # swipe (x1 y1 x2 y2 duration_ms)
adb shell input text "hello"                        # type
adb shell input keyevent KEYCODE_HOME               # or POWER, BACK, MENU, VOLUME_UP, ...
adb shell input keyevent 66                         # ENTER by keycode

adb shell screencap -p > screen.png                 # PNG to stdout (Windows PowerShell needs `-P`)
adb exec-out screencap -p > screen.png              # binary-safe on macOS/Linux (avoids CRLF conversion)
adb shell screenrecord /sdcard/rec.mp4 --time-limit 60 --size 1080x1920
adb pull /sdcard/rec.mp4

# UI hierarchy inspection
adb shell uiautomator dump                           # writes /sdcard/window_dump.xml
adb pull /sdcard/window_dump.xml
```

## Window manager / display

```bash
adb shell wm size                                    # current dimensions
adb shell wm size 1080x1920                          # override (needs userdebug or `adb shell`)
adb shell wm size reset
adb shell wm density                                 # current DPI
adb shell wm density 320
adb shell wm density reset

adb shell settings put global window_animation_scale 0
adb shell settings put global transition_animation_scale 0
adb shell settings put global animator_duration_scale 0
# → disable animations for stable Macrobenchmark / Espresso runs
```

## Simulation and testing helpers

```bash
adb shell svc data disable / enable                  # toggle cellular
adb shell svc wifi enable / disable
adb shell svc bluetooth enable / disable

adb shell cmd connectivity airplane-mode enable / disable

adb shell settings put system font_scale 1.5         # accessibility large-text simulation
adb shell settings put secure ui_night_mode 2        # force dark theme (2=dark, 1=light, 0=auto)

adb emu geo fix -122.084 37.4220                     # emulator: set GPS coordinates
adb emu battery level 20                             # emulator: battery level
adb emu sms send +15551234567 "test message"
adb emu gsm call +15551234567
```

## Content provider access

```bash
adb shell content query --uri content://com.target.provider/table
adb shell content insert --uri content://com.target.provider/table \
    --bind name:s:testvalue --bind count:i:42
adb shell content update --uri content://com.target.provider/table/1 \
    --bind name:s:updated
adb shell content delete --uri content://com.target.provider/table/1
adb shell content read --uri content://com.target.provider/files/1     # binary content
```

## Baseline profile inspection

```bash
adb shell cmd package dump-profiles com.target.app   # dumps ART profile
# outputs the compiled/hot method list — verify Baseline Profile coverage

adb shell cmd package compile -m speed-profile com.target.app
adb shell cmd package compile -m verify com.target.app
adb shell dumpsys package dexopt | grep com.target.app  # verify compilation state
```

## Backup / restore (legacy, restricted since Android 12)

```bash
adb backup -apk -shared -all -f full.ab              # full backup (requires user confirmation on device)
adb restore full.ab
adb backup com.target.app -f target.ab                # single package
# Note: many apps set allowBackup="false" and get an empty archive.
# See mobile-technique for post-Android-12 alternatives.
```

## Multi-device / shell selectors

```bash
adb devices -l
# List of devices attached
# emulator-5554         device product:sdk_gphone_x86_64 model:sdk_gphone_x86_64 device:generic
# R5C123456789          device usb:1-2 product:aosp_pixel model:AOSP_on_Pixel device:generic

adb -s emulator-5554 shell dumpsys package com.target.app
adb -s R5C123456789 install app.apk

export ANDROID_SERIAL=emulator-5554                  # env var — every adb call uses this
```

## Package sources and deltas

Google's `android` CLI uses fast delta install. For plain adb:

```bash
adb install --incremental app.apk                    # streaming install; Android 11+
```

## Common pitfalls

- **"more than one device"** — set `ANDROID_SERIAL` or use `-s <serial>`.
- **Push to `/system/*`** — needs `adb root` + `adb remount` (userdebug/eng only).
- **`adb pull /data/data/...`** silently produces empty file — the app must be debuggable OR you must `adb root`.
- **`screencap -p`** on Windows PowerShell corrupts binary output (CRLF conversion); use `adb exec-out` or run under WSL/`cmd.exe`.
- **`adb shell` on Wi-Fi drops after 5–10 min idle** — reconnect with `adb connect <ip>:<port>`. Enable "Stay awake" in dev options during work sessions.
- **Wireless pair fails** — device and host must be on the same subnet with mDNS working (many corporate/coffee-shop Wi-Fi block mDNS). Use USB for pairing, then switch to Wi-Fi.
- **`adb install-multiple` split mismatch** — every split must be signed with the same key; the patched base + original splits fails.
- **Permission dialogs during `am start`** — apps requesting runtime permissions block the intent; use `pm grant` before start.
- **`dumpsys` output truncated on old devices** — pipe to `> file.txt` or increase logcat buffer.

## Ecosystem tools worth pairing with adb

- **scrcpy** (github.com/Genymobile/scrcpy) — screen mirroring + control from the host over adb. Zero-latency alternative to a physical device on your desk.
- **Vysor** — commercial equivalent to scrcpy with app-store convenience.
- **fastboot** — sibling tool for bootloader-mode (unlock, flash boot images). Use when you need to root or install a custom recovery.
- **Android platform-tools** package includes `adb`, `fastboot`, `systrace`, `simpleperf`, `traceconv`, `zipalign`, `apksigner`, `mke2fs.android`.

## Handoff

- For deep on-device performance work (Baseline Profiles, Macrobenchmark), see `kotlin-performance`.
- For patching APKs pulled via `adb`, see `smali-dex-patching`.
- For JNI/NDK crashes surfaced via `logcat`, see `android-jni-ndk/references/native-crashes-and-debugging.md`.
- For mobile assessment methodology, see `mobile-technique`.
