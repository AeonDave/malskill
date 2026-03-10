# C test harness patterns

## Structure

```
tests/
  test_module_a.c
  test_module_b.c
testdata/
  sample.bin
  expected.txt
```

Each test file targets one module; no shared mutable state between files.

## Minimal assertion helpers

```c
#include <stdio.h>
#include <string.h>

#define ASSERT_EQ_INT(got, want) \
  do { if ((got) != (want)) { \
    fprintf(stderr, "%s:%d FAIL: got=%d want=%d\n", \
            __FILE__, __LINE__, (got), (want)); \
    return 1; } } while (0)

#define ASSERT_EQ_STR(got, want) \
  do { if (strcmp((got), (want)) != 0) { \
    fprintf(stderr, "%s:%d FAIL: got=\"%s\" want=\"%s\"\n", \
            __FILE__, __LINE__, (got), (want)); \
    return 1; } } while (0)

#define ASSERT_NULL(ptr) \
  do { if ((ptr) != NULL) { \
    fprintf(stderr, "%s:%d FAIL: expected NULL, got %p\n", \
            __FILE__, __LINE__, (void*)(ptr)); \
    return 1; } } while (0)

#define ASSERT_NOT_NULL(ptr) \
  do { if ((ptr) == NULL) { \
    fprintf(stderr, "%s:%d FAIL: unexpected NULL\n", \
            __FILE__, __LINE__); \
    return 1; } } while (0)
```

## Test runner main

```c
typedef int (*test_fn)(void);
struct test_case { const char *name; test_fn fn; };

static const struct test_case tests[] = {
  { "test_parse_empty",  test_parse_empty },
  { "test_parse_valid",  test_parse_valid },
  { NULL, NULL }
};

int main(void) {
  int pass = 0, fail = 0;
  for (int i = 0; tests[i].name; i++) {
    int rc = tests[i].fn();
    if (rc == 0) { printf("PASS: %s\n", tests[i].name); pass++; }
    else          { printf("FAIL: %s\n", tests[i].name); fail++; }
  }
  printf("\n%d passed, %d failed\n", pass, fail);
  return fail > 0 ? 1 : 0;
}
```

## Alternative: Unity (C unit test framework)

[Unity](https://github.com/ThrowTheSwitch/Unity) is a lightweight single-file C test framework commonly used in embedded and systems projects.

```c
#include "unity.h"

void setUp(void) {}    /* optional per-test setup */
void tearDown(void) {} /* optional per-test teardown */

void test_add(void) {
  TEST_ASSERT_EQUAL_INT(3, add(1, 2));
}

int main(void) {
  UNITY_BEGIN();
  RUN_TEST(test_add);
  return UNITY_END();
}
```

## Alternative: cmocka

[cmocka](https://cmocka.org/) supports mocking and is CMake-friendly:

```c
#include <stdarg.h>
#include <stddef.h>
#include <setjmp.h>
#include <cmocka.h>

static void test_alloc(void **state) { (void)state; assert_non_null(malloc(1)); }

int main(void) {
  const struct CMUnitTest tests[] = { cmocka_unit_test(test_alloc) };
  return cmocka_run_group_tests(tests, NULL, NULL);
}
```
