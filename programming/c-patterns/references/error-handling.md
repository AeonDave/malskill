# Error handling in C

## Pick a policy

Common options:
- `int` return code (0 ok, non-zero error)
- `bool` + `errno` (be careful; errno is global and not always set)
- error enum + optional message

Document the policy per module.

## Avoid in-band error indicators

If a function returns a pointer, prefer returning `NULL` on failure and use an out-parameter for error detail.

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

References:
- CERT C Error Handling (ERR): https://wiki.sei.cmu.edu/confluence/spaces/c/pages/87151977/Rec.+12.+Error+Handling+ERR
