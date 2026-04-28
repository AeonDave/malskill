# Memory management and ownership

## Ownership vocabulary

Use these terms consistently in headers and reviews:

- **borrowed**: caller keeps lifetime responsibility
- **owned**: callee must free
- **transferred**: ownership moves from caller to callee

## Ownership rule

Allocate and free in the same module and at the same level of abstraction.

## API naming pattern

- Constructors: `foo_create`, `foo_open`, `foo_new`
- Destructors: `foo_destroy`, `foo_close`, `foo_free`
- Init/deinit for stack objects: `foo_init`, `foo_deinit`

```c
/* caller-owned output buffer */
int foo_encode(const struct foo *in, uint8_t *out, size_t out_cap, size_t *out_len);

/* callee allocates, caller frees via foo_buffer_free */
int foo_encode_alloc(const struct foo *in, uint8_t **out, size_t *out_len);
void foo_buffer_free(uint8_t *p);
```

## Common safety rules

- Set pointers to NULL after `free()` if they may be reused.
- Beware of zero-length allocations.
- Avoid large stack allocations.
- Ensure `calloc(count, size)` multiplication does not wrap.

## Allocation arithmetic guards

```c
if (count != 0 && size > SIZE_MAX / count) {
	return -1; /* overflow */
}
void *p = calloc(count, size);
```

## Transfer-of-ownership pattern

```c
int list_push_take(struct list *lst, struct item **it) {
	if (!lst || !it || !*it) return -1;
	if (list_push_raw(lst, *it) != 0) return -1;
	*it = NULL;  /* transfer complete */
	return 0;
}
```

## Common anti-patterns

- Returning pointers to stack memory.
- Freeing memory through a different allocator family.
- Hidden ownership transfer without naming/docs.
- Freeing borrowed memory in callee.

## Quick checklist

- [ ] Every pointer parameter ownership is documented.
- [ ] Allocator/deallocator families match.
- [ ] Transfer-of-ownership functions null out caller handle when successful.
- [ ] Allocation size arithmetic is overflow-safe.

References:
- CERT C Memory Management (MEM): https://wiki.sei.cmu.edu/confluence/spaces/c/pages/87151930/Rec.+08.+Memory+Management+MEM
