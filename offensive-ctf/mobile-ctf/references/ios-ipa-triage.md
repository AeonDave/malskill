# iOS / IPA Triage

Load when the artifact is an `.ipa`, `.app` bundle, Mach-O binary, `.dylib`, or `.framework` and the task is to recover a flag, secret, or app logic. Static analysis works on Linux/macOS from an extracted bundle; dynamic steps (Frida/objection, keychain) need a jailbroken or repackaged device.

## IPA structure

An `.ipa` is a ZIP. `unzip -o app.ipa -d app/` exposes:
- `Payload/<App>.app/` — the bundle: main Mach-O (same name as the app, no extension), assets, storyboards, `.plist`, `.car` asset catalogs.
- `Payload/<App>.app/Info.plist` — bundle ID, version, `CFBundleURLTypes` (custom URL schemes), `NSAppTransportSecurity` (ATS), background modes, supported architectures.
- `Payload/<App>.app/embedded.mobileprovision` — provisioning profile; check for debug entitlements and the team/cert.
- `Payload/<App>.app/Frameworks/` — third-party `.dylib`/`.framework`, each its own Mach-O worth analysing.
- `_CodeSignature/CodeResources` — signing manifest; any patched file invalidates it.

## Quick wins first

```bash
strings -a Payload/*.app/<AppName> | grep -iE 'flag\{|secret|api[_-]?key|password|token'
# binary plists are not text — convert before grepping
find Payload -name '*.plist' -exec plutil -convert xml1 -o - {} \;
```

Common plain-text storage holding flags: `Info.plist`, app-bundle `.plist`, `.strings`, `.json`, embedded SQLite (`.db`/`.sqlite`), `.car` catalogs (extract images with `acextract`/`assetutil`).

## Static binary analysis

```bash
file Payload/*.app/<AppName>            # Mach-O, fat (universal) vs thin, arch
otool -hv <bin>                         # header, flags (PIE, encryption)
otool -L <bin>                          # linked dylibs / frameworks
otool -arch arm64 -Vt <bin>            # disassemble
plutil -p Info.plist                    # readable plist dump
codesign -dv --entitlements - <bin>     # entitlements, signing
```

Class/method recovery from Objective-C metadata (Swift is partially stripped — fall back to `nm`/decompiler):
```bash
ipsw class-dump <bin>      # or classdump-dyld / class-dump
nm -gU <bin>               # exported symbols
```
Load into Ghidra/IDA/Binary Ninja/radare2 for control-flow on the flag check.

## FairPlay encryption

App Store binaries are FairPlay-encrypted: `otool -l <bin> | grep -A4 LC_ENCRYPTION_INFO` shows `cryptid 1`. Encrypted regions disassemble as garbage. You cannot statically decrypt — get a decrypted copy from a jailbroken device:
- `frida-ios-dump` — pulls a decrypted IPA over USB.
- `dumpdecrypted.dylib` via `DYLD_INSERT_LIBRARIES` against the running app.
- `bfinject` / `bagbak` as alternatives.

CTF/lab artifacts are usually already decrypted (`cryptid 0`) — check before assuming you need a device.

## Dynamic analysis (device or patched IPA)

`objection` runs Frida and needs no jailbreak if the IPA is patched (`objection patchipa`):
```
frida-ps -Uai                          # list installed apps + bundle IDs
objection -g <bundle-id> explore
  ios plist cat Info.plist             # inspect plists in-app
  ios keychain dump                    # app keychain items + accessibility attrs
  ios nsuserdefaults get               # NSUserDefaults
  ios nsurlcredentialstorage dump      # stored credentials
  ios cookies get                      # binary cookies
  sqlite connect <file>.sqlite         # query app databases
  ios sslpinning disable               # strip TLS pinning for traffic capture
  ios jailbreak disable                # bypass jailbreak detection
  memory dump all mem.dmp              # dump process memory, then strings it
```

Keychain notes: `ios keychain dump` only returns items the app itself can read; on a jailbroken device `keychain-dumper` reads the full keychain. Flag insecure accessibility (`kSecAttrAccessibleAlways`, `kSecAttrAccessibleAfterFirstUnlock`).

## Where flags hide in iOS apps

- `Info.plist` URL schemes and custom keys; binary plists elsewhere in the bundle.
- Keychain items, `NSUserDefaults`, `NSURLCredentialStorage`, binary cookies.
- SQLite databases and Core Data stores in the app sandbox `Documents/`/`Library/`.
- Hardcoded strings, `__cstring`/`__objc_methname` sections in the Mach-O.
- Asset catalogs (`Assets.car`) and storyboard/nib resources.
- Custom crypto in app logic — trace with `objection`'s `ios monitor crypto` or Frida hooks on `CCCrypt`/`CommonCrypto`.

## Validation

A recovered secret needs the exact path: file + key, keychain item + service, or the Mach-O offset/function that produces it, replayable from the bundle (static) or a scripted Frida/objection session (dynamic).
