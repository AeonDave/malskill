# Sanitizers and fuzzing

## Sanitizers (Clang/GCC)

- ASan: `-fsanitize=address -fno-omit-frame-pointer -g -O1`
- UBSan: `-fsanitize=undefined -fno-omit-frame-pointer -g`
- Combined (common): `-fsanitize=address,undefined -fno-omit-frame-pointer -g -O1`

Runtime options:

- `ASAN_OPTIONS=detect_leaks=1:symbolize=1`
- `UBSAN_OPTIONS=print_stacktrace=1:halt_on_error=1`

References:
- ASan: https://clang.llvm.org/docs/AddressSanitizer.html
- UBSan: https://clang.llvm.org/docs/UndefinedBehaviorSanitizer.html

## Fuzzing (outline)

Use fuzzing for parsers and input validators.

- libFuzzer is commonly used with Clang.
- Keep the target deterministic and side-effect free.

### Minimal target

```c
#include <stddef.h>
#include <stdint.h>

extern int parse_message(const uint8_t *data, size_t len);

int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size) {
	(void)parse_message(data, size);
	return 0;
}
```

### Build and run

```sh
clang -g -O1 -fsanitize=fuzzer,address fuzz_parse.c parser.c -o fuzz_parse
mkdir -p corpus
./fuzz_parse corpus -max_len=4096
```

### Corpus handling

- Seed with diverse valid + invalid examples.
- Minimize large corpus while preserving coverage:

```sh
mkdir -p corpus_min
./fuzz_parse -merge=1 corpus_min corpus_full
```

### Parallel fuzzing

```sh
./fuzz_parse corpus -jobs=20 -workers=4
```

### Harness quality rules

- No `exit()` inside target.
- No persistent global state between runs.
- Avoid heavy logging in target loop.
- Join spawned threads before returning.
- Reject structurally irrelevant inputs with `return -1` only when intentional.

Minimal harness shape:
- accept `data,size`
- call parser
- avoid writing files or network

References:
- libFuzzer: https://llvm.org/docs/LibFuzzer.html
- LeakSanitizer: https://clang.llvm.org/docs/LeakSanitizer.html
