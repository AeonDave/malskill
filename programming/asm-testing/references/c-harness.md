# C Harness Patterns for Assembly Testing

Templates for building test drivers that call hand-written assembly functions.

---

## Project Layout

```
project/
├── src/
│   └── hot_fn.asm         (or .s)
├── test/
│   ├── test_hot_fn.c
│   └── harness.h          (optional helpers)
└── Makefile
```

---

## Makefile — NASM + GCC

```makefile
CC      = gcc
CFLAGS  = -g -Wall -Wextra -O0 -std=c11
NASM    = nasm
NASMFLAGS = -f elf64 -g -F dwarf

# Object files
ASM_OBJ  = hot_fn.o
TEST_OBJ = test_hot_fn.o

.PHONY: all test clean

all: test_hot_fn

hot_fn.o: src/hot_fn.asm
	$(NASM) $(NASMFLAGS) $< -o $@

test_hot_fn.o: test/test_hot_fn.c
	$(CC) $(CFLAGS) -c $< -o $@

test_hot_fn: $(ASM_OBJ) $(TEST_OBJ)
	$(CC) $(CFLAGS) -o $@ $^

test: test_hot_fn
	./test_hot_fn

clean:
	rm -f *.o test_hot_fn
```

---

## Makefile — GAS + GCC

```makefile
CC     = gcc
CFLAGS = -g -Wall -O0 -std=c11
AS     = as
ASFLAGS = -g --gstabs+

hot_fn.o: src/hot_fn.s
	$(AS) $(ASFLAGS) $< -o $@
```

---

## harness.h — Assertion Helpers

```c
/* test/harness.h */
#ifndef HARNESS_H
#define HARNESS_H

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <math.h>
#include <string.h>

/* Counter */
static int _pass = 0, _fail = 0;

/* Integer equality */
#define ASSERT_EQ_I64(got, exp, label) do { \
    int64_t _g = (int64_t)(got), _e = (int64_t)(exp); \
    if (_g == _e) { _pass++; } \
    else { fprintf(stderr, "FAIL [%s]: got %ld, want %ld\n", label, _g, _e); _fail++; } \
} while(0)

/* Float equality within tolerance */
#define ASSERT_NEAR_F(got, exp, tol, label) do { \
    float _g = (float)(got), _e = (float)(exp); \
    if (fabsf(_g - _e) <= (tol)) { _pass++; } \
    else { fprintf(stderr, "FAIL [%s]: got %f, want %f (tol %f)\n", label, _g, _e, (float)(tol)); _fail++; } \
} while(0)

/* Memory equality */
#define ASSERT_MEM_EQ(got, exp, nbytes, label) do { \
    if (memcmp((got), (exp), (nbytes)) == 0) { _pass++; } \
    else { fprintf(stderr, "FAIL [%s]: memory mismatch (%zu bytes)\n", label, (size_t)(nbytes)); _fail++; } \
} while(0)

/* Pointer non-null */
#define ASSERT_NOTNULL(ptr, label) do { \
    if ((ptr) != NULL) { _pass++; } \
    else { fprintf(stderr, "FAIL [%s]: got NULL\n", label); _fail++; } \
} while(0)

/* Summary */
#define HARNESS_SUMMARY() do { \
    printf("%d passed, %d failed\n", _pass, _fail); \
    return (_fail > 0) ? 1 : 0; \
} while(0)

#endif /* HARNESS_H */
```

---

## Integer Function Template

```c
/* test/test_hot_fn.c */
#include "harness.h"

extern int64_t hot_fn(int64_t a, int64_t b);   /* defined in hot_fn.asm */

typedef struct { int64_t a; int64_t b; int64_t want; const char *label; } Case;

static const Case cases[] = {
    {  0,  0,  0, "zero+zero" },
    {  1,  2,  3, "one+two"   },
    { -1,  1,  0, "neg+pos"   },
    { INT64_MAX, 0, INT64_MAX, "max+zero" },
    { INT64_MIN, 0, INT64_MIN, "min+zero" },
};

int main(void) {
    for (size_t i = 0; i < sizeof cases / sizeof cases[0]; i++) {
        int64_t got = hot_fn(cases[i].a, cases[i].b);
        ASSERT_EQ_I64(got, cases[i].want, cases[i].label);
    }
    HARNESS_SUMMARY();
}
```

---

## Float / SIMD Function Template

```c
/* test/test_vec_add.c */
#include "harness.h"
#include <stdlib.h>

/* void vec_add(float *dst, const float *src, int n) */
extern void vec_add(float *dst, const float *src, int n);

/* Aligned allocation helper */
static float *alloc_aligned(size_t n) {
    float *p;
    if (posix_memalign((void**)&p, 32, n * sizeof(float)) != 0) {
        perror("posix_memalign");
        exit(1);
    }
    return p;
}

static void test_basic(void) {
    float *dst = alloc_aligned(8);
    float *src = alloc_aligned(8);
    float exp[8];

    for (int i = 0; i < 8; i++) { dst[i] = (float)i; src[i] = 1.0f; exp[i] = i + 1.0f; }
    vec_add(dst, src, 8);

    for (int i = 0; i < 8; i++) {
        char lbl[32];
        snprintf(lbl, sizeof lbl, "basic[%d]", i);
        ASSERT_NEAR_F(dst[i], exp[i], 1e-6f, lbl);
    }
    free(dst); free(src);
}

int main(void) {
    test_basic();
    HARNESS_SUMMARY();
}
```

---

## Memory Function Template

```c
/* test/test_memcpy_asm.c */
#include "harness.h"
#include <stdlib.h>
#include <stdio.h>

/* void *asm_memcpy(void *dst, const void *src, size_t n) */
extern void *asm_memcpy(void *dst, const void *src, size_t n);

static void test_copy(size_t n, const char *label) {
    unsigned char *src = malloc(n);
    unsigned char *dst = calloc(n, 1);
    if (!src || !dst) { perror("malloc"); exit(1); }

    for (size_t i = 0; i < n; i++) src[i] = (unsigned char)(i & 0xFF);
    asm_memcpy(dst, src, n);
    ASSERT_MEM_EQ(dst, src, n, label);

    free(src); free(dst);
}

int main(void) {
    test_copy(1,    "1-byte");
    test_copy(7,    "7-byte unaligned");
    test_copy(16,   "16-byte aligned");
    test_copy(64,   "64-byte (1 cache line)");
    test_copy(1024, "1KiB");
    test_copy(4096, "4KiB");
    HARNESS_SUMMARY();
}
```

---

## Cycle Measurement Helper

```c
/* Include in test driver for cycle counting */
#include <stdint.h>

static inline uint64_t cycles_now(void) {
    uint32_t lo, hi;
    __asm__ volatile (
        "lfence\n"
        "rdtsc\n"
        "lfence\n"
        : "=a"(lo), "=d"(hi)
    );
    return ((uint64_t)hi << 32) | lo;
}

#define BENCH(label, n, expr) do { \
    uint64_t _t0 = cycles_now(); \
    for (int _i = 0; _i < (n); _i++) { expr; } \
    uint64_t _t1 = cycles_now(); \
    printf("BENCH [%s] avg=%.2f cycles (%d runs)\n", label, (double)(_t1-_t0)/(n), n); \
} while(0)
```

Usage: `BENCH("hot_fn", 100000, hot_fn(i, i+1));`

---

## Notes

- Always compile test drivers with `-O0` unless you explicitly want to test optimization interactions
- Use `-fsanitize=address` to catch out-of-bounds from the C side (not applicable to hand-written asm itself)
- Link order matters: `$(CC) -o test_hot_fn test_hot_fn.o hot_fn.o` — the object defining `hot_fn` must follow the object referencing it on most linkers
