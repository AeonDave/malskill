# CTF Reverse - Static Patterns: Transforms, Keystreams, and Signal Paths

Focused pattern reference for deterministic reversals: per-byte transforms, keystream families, x86 pitfalls, and signal-driven static reconstruction.

## Table of Contents
- [Known-Plaintext XOR](#known-plaintext-xor)
- [S-Box and Keystream Generation](#s-box-and-keystream-generation)
- [Byte-Wise Uniform Transforms](#byte-wise-uniform-transforms)
- [x86-64 Gotchas](#x86-64-gotchas)
- [Custom Mangle Function Reversing](#custom-mangle-function-reversing)
- [Position-Based Transformation Reversing](#position-based-transformation-reversing)
- [Hex-Encoded String Comparison](#hex-encoded-string-comparison)
- [Signal-Based Binary Exploration](#signal-based-binary-exploration)

## Known-Plaintext XOR

If the format prefix is known, test repeating-key and index-augmented XOR before assuming “custom crypto.”

## S-Box and Keystream Generation

Recognize families before reimplementing them blindly:
- xorshift32 and xorshift64* constants
- Fisher-Yates shuffle layout
- obvious magic multipliers and rotation schedules

## Byte-Wise Uniform Transforms

If one input byte only changes one output byte, brute-force the 256-value map once, invert it, and stop pretending this is a symbolic-execution problem.

## x86-64 Gotchas

Two recurring failure modes:
- sign-extension misunderstandings
- loop-state updates happening on the “wrong” side of a branch

Always re-check raw assembly when the decompiler looks slightly too elegant.

## Custom Mangle Function Reversing

Extract the target bytes from static data, write the inverse, and walk the transform backward rather than simulating the original validator forever.

## Position-Based Transformation Reversing

When the transform includes `i`, parity, or alternating position rules, derive the inverse position-wise and solve directly.

## Hex-Encoded String Comparison

If the binary converts the input to hex before comparing, decode the target constant first. This is the nicest kind of fake complexity.

## Signal-Based Binary Exploration

For signal trees or self-signalling checkers, log signal installation and branch on which next handler appears. The control graph is often literally encoded in the registration sequence.
