# Memory management and ownership

## Ownership rule

Allocate and free in the same module and at the same level of abstraction.

## Common safety rules

- Set pointers to NULL after `free()` if they may be reused.
- Beware of zero-length allocations.
- Avoid large stack allocations.
- Ensure `calloc(count, size)` multiplication does not wrap.

References:
- CERT C Memory Management (MEM): https://wiki.sei.cmu.edu/confluence/spaces/c/pages/87151930/Rec.+08.+Memory+Management+MEM
