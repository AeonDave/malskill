# Error handling in C

## Goals

- Return errors consistently.
- Preserve root cause context.
- Avoid leaks/corruption on error paths.

## Pick a policy

Common options:
- `int` return code (0 ok, non-zero error)
- `bool` + `errno` (be careful; errno is global and not always set)
- error enum + optional message

Document the policy per module.

Recommended for most modules:

- Public API: `int`/`enum` return code
- Data output via out-parameters
- Optional `const char *err_to_string(code)` helper

## Avoid in-band error indicators

If a function returns a pointer, prefer returning `NULL` on failure and use an out-parameter for error detail.

```c
typedef enum {
  MOD_OK = 0,
  MOD_EINVAL,
  MOD_ENOMEM,
  MOD_EIO
} mod_err;

void *mod_parse(const uint8_t *buf, size_t len, mod_err *err);
```

## Single-exit cleanup pattern

CERT C recommends a goto cleanup chain for releasing multiple resources.

```c
int f(...) {
  int rc = -1;
  FILE *fp = NULL;
  void *buf = NULL;

  fp = fopen(path, "rb");
  if (!fp) goto cleanup;

  buf = malloc(n);
  if (!buf) goto cleanup;

  rc = 0;
cleanup:
  free(buf);
  if (fp) fclose(fp);
  return rc;
}
```

## Preserve context without global state

- Convert low-level errors at module boundary.
- Keep a stable module-specific code space.
- For logs, include both external and internal code.

```c
/* map errno -> module code */
static mod_err map_errno(int e) {
    switch (e) {
        case ENOMEM: return MOD_ENOMEM;
        case EIO:    return MOD_EIO;
        default:     return MOD_EINVAL;
    }
}
```

## Common anti-patterns

- Returning success while leaving out-params uninitialized.
- Overwriting first error with later cleanup error.
- Mixing `errno` contract with unrelated custom return codes.
- Logging and returning generic failure without actionable code.

## Quick checklist

- [ ] One documented error policy per module.
- [ ] Out-params are valid on success and untouched/defined on failure.
- [ ] Cleanup path releases all resources exactly once.
- [ ] Error codes are stable and testable.

References:
- CERT C Error Handling (ERR): https://wiki.sei.cmu.edu/confluence/spaces/c/pages/87151977/Rec.+12.+Error+Handling+ERR
