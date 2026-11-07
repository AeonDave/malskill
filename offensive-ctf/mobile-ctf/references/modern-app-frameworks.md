# Mobile framework artifacts

## Flutter / Dart AOT

Android packages containing `libflutter.so` and `libapp.so` warrant inspection of the Dart snapshot as well as Java/Kotlin and native code. [Blutter](https://github.com/worawit/blutter) detects the Dart version from the Flutter engine and extracts information from `libapp.so` for supported builds. Check its output against the binary; missing names or strings are not proof that a behavior is absent.

## React Native / Hermes

Inspect the bundle, often `assets/index.android.bundle`, to distinguish JavaScript from Hermes bytecode. Hermes defines the integer magic `0x1F1903C103BC1FC6` in its [bytecode format](https://github.com/facebook/hermes/blob/main/include/hermes/BCGen/HBC/BytecodeFileFormat.h); interpret byte order when inspecting raw bytes. Check the bytecode version against the selected disassembler's supported versions. React Native 0.70 made Hermes the default for new projects, but an individual app's configuration determines its engine ([React Native](https://reactnative.dev/blog/2022/07/08/hermes-as-the-default)).

For supported bytecode versions, [hermes-dec](https://github.com/P1sec/hermes-dec) provides disassembly and decompilation. [hbctool](https://github.com/bongtrop/hbctool) provides assembly/disassembly but its documented support is limited to versions 59, 62, 74 and 76. Match the actual bundle version before interpreting a tool failure or incomplete output.

## App data

For a debuggable app on a device supporting `run-as`, inspect the package's own data with `adb shell run-as <package>`. Also consider supplied backups and application exports. Identify whether needed values are files, database records, or protected keys before choosing a recovery path; Android Keystore key material is non-exportable by design ([Android documentation](https://developer.android.com/privacy-and-security/keystore)).
