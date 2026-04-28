// ============================================================================
// Function Template — ARM64 (GAS)
// Target: AAPCS64 (Linux, macOS)
// Usage:  Copy, rename function, fill in body.
// ============================================================================

    .text
    .align  4

// ----------------------------------------------------------------------------
// int64_t my_function(int64_t a, int64_t b, int64_t c)
//   Args: x0=a, x1=b, x2=c   Returns: x0
// ----------------------------------------------------------------------------
    .global my_function
my_function:
    // Non-leaf prologue — save fp, lr, and callee-saved registers
    stp     x29, x30, [sp, #-32]!   // allocate 32 bytes, save fp+lr
    mov     x29, sp
    stp     x19, x20, [sp, #16]     // save callee-saved pair

    // Map args to callee-saved registers (survive across bl calls)
    mov     x19, x0                  // a
    mov     x20, x1                  // b
    // x2 = c (use before any bl, or save to x21)

    // ---- function body ----
    // TODO: replace with actual logic
    mov     x0, x19                  // placeholder: return a

    // Epilogue — restore in reverse order
    ldp     x19, x20, [sp, #16]
    ldp     x29, x30, [sp], #32
    ret

// ============================================================================
// Leaf function variant (no bl calls, no callee-saved needed)
// ============================================================================
    .global my_leaf_function
my_leaf_function:
    // No prologue needed — use only x0-x15
    add     x0, x0, x1              // placeholder: return a + b
    ret
