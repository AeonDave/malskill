# Sanitizers and fuzzing

## Sanitizers (Clang/GCC)

- ASan: `-fsanitize=address -fno-omit-frame-pointer -g -O1`
- UBSan: `-fsanitize=undefined -fno-omit-frame-pointer -g`

References:
- ASan: https://clang.llvm.org/docs/AddressSanitizer.html
- UBSan: https://clang.llvm.org/docs/UndefinedBehaviorSanitizer.html

## Fuzzing (outline)

Use fuzzing for parsers and input validators.

- libFuzzer is commonly used with Clang.
- Keep the target deterministic and side-effect free.

Minimal harness shape:
- accept `data,size`
- call parser
- avoid writing files or network
