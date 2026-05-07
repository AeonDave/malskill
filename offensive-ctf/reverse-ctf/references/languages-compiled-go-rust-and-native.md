# CTF Reverse - Compiled Native Languages

Focused language reference for native compiled targets where symbol recovery, runtime layout knowledge, and ABI-aware reading of decompiler output matter more than generic RE basics.

## Table of Contents
- [Go Binary Reversing](#go-binary-reversing)
- [Rust Binary Reversing](#rust-binary-reversing)
- [Swift Binary Reversing](#swift-binary-reversing)
- [D Language Binary Reversing](#d-language-binary-reversing)
- [C++ Quick Reference](#c-quick-reference)
- [Rust Compiler-Bug and Linker Abuse Patterns](#rust-compiler-bug-and-linker-abuse-patterns)
- [Rust Constant Extraction](#rust-constant-extraction)

## Go Binary Reversing

Go binaries are metadata-rich even when stripped.

### Recognition
- `go.buildid`
- `runtime.gopanic`
- very large static output
- source paths under Go toolchain directories

### Best workflow
1. Run `GoReSym` or `redress` first.
2. Load recovered names into Ghidra.
3. Model `string`, `slice`, and `interface` layouts correctly.
4. Trace `main.main`, crypto packages, embedded resources, and goroutines.

```c
struct GoString { char *ptr; int64 len; };
struct GoSlice  { void *ptr; int64 len; int64 cap; };
struct GoIface  { void *type; void *data; };
```

### Common payoff patterns
- direct crypto package usage
- `embed.FS` artifacts in the binary image
- channel-based validators that look harder than they are
- `-ldflags -X` strings patchable in-place

## Rust Binary Reversing

Rust's decompilation is noisy, but panic strings and demangled names are generous.

### Recognition
- `/rustc/` paths
- `core::panicking`
- `.rustc` sections
- `_ZN...` mangled symbols

### Practical workflow
1. `strings | grep panicked`
2. `nm | rustfilt`
3. model `Option`, `Result`, `Vec`, `String`, `&str`
4. follow iterator-fused loops as stateful pipelines, not as “weird compiler junk”

## Swift Binary Reversing

For Apple-native targets, use Swift-specific metadata and demangling before generic pseudocode reading.

```bash
swift demangle 's14MyApp0A8ClassC10checkInput6resultSbSS_tF'
```

Look for `__swift5_*` sections, witness tables, and runtime helpers such as `swift_allocObject`.

## D Language Binary Reversing

D binaries often expose template-instantiated logic through `_D` symbols and Phobos references. When you spot many repeated function variants, script the family instead of reading them one-by-one.

## C++ Quick Reference

Primary recovery anchors:
- vtables and virtual dispatch
- RTTI/typeinfo chains
- `std::string` small-string optimization
- `std::vector` triplets
- `std::map` / `std::unordered_map` storage shapes

## Rust Compiler-Bug and Linker Abuse Patterns

Two high-value task families:
- lifetime/soundness bugs in pinned compiler versions
- `#[no_mangle] extern "C"` symbol shadowing against sandbox harnesses

Treat both as environment/version-driven exploitation surfaces, not just language trivia.

## Rust Constant Extraction

When the program compares against hidden literal buffers, dump `.rodata` or xmmword-backed constants first. For Rust validators this is often much faster than full control-flow recovery.
