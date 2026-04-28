# Integers and size calculations

## Rules

- Prefer `size_t` for sizes and counts.
- Validate conversions between signed/unsigned.
- Treat multiplication for buffer sizes as overflow-prone.
- Avoid implicit narrowing conversions in API boundaries.
- Validate shift counts and divisors.

## Patterns

- Check `(count > 0 && size > SIZE_MAX / count)` before allocating `count * size`.

### Safe add/mul helpers

```c
static int add_overflow_size(size_t a, size_t b, size_t *out) {
	if (a > SIZE_MAX - b) return 1;
	*out = a + b;
	return 0;
}

static int mul_overflow_size(size_t a, size_t b, size_t *out) {
	if (a != 0 && b > SIZE_MAX / a) return 1;
	*out = a * b;
	return 0;
}
```

### Signed/unsigned boundary checks

```c
/* ssize_t -> size_t conversion */
if (n < 0) return -1;
size_t un = (size_t)n;
```

### Shift/divide guards

```c
if (shift >= (sizeof(x) * CHAR_BIT)) return -1;
if (den == 0) return -1;
```

## Common anti-patterns

- `int len = strlen(s);` for potentially large buffers.
- Using negative values as sentinel in unsigned variables.
- Pointer arithmetic using signed values without range validation.
- Performing `a + b` then checking `if (sum < a)` only after overflow already occurred in signed domain.

## Quick checklist

- [ ] Allocation math checked for overflow.
- [ ] Signed-to-unsigned conversions guarded.
- [ ] Shifts and divisions validated.
- [ ] API type widths are explicit and intentional.

References:
- CERT C Integers (INT): https://wiki.sei.cmu.edu/confluence/spaces/c/pages/87151979/Rec.+04.+Integers+INT
