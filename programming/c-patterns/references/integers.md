# Integers and size calculations

## Rules

- Prefer `size_t` for sizes and counts.
- Validate conversions between signed/unsigned.
- Treat multiplication for buffer sizes as overflow-prone.

## Patterns

- Check `(count > 0 && size > SIZE_MAX / count)` before allocating `count * size`.

References:
- CERT C Integers (INT): https://wiki.sei.cmu.edu/confluence/spaces/c/pages/87151979/Rec.+04.+Integers+INT
