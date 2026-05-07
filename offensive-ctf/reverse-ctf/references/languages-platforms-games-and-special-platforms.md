# CTF Reverse - Games and Special Platform Targets

Focused platform reference for games, nonstandard packaged content, hardware-description artifacts, legacy encodings, and exotic runtimes that still reward structured extraction.

## Table of Contents
- [Roblox Place File Analysis](#roblox-place-file-analysis)
- [Godot Game Asset Extraction](#godot-game-asset-extraction)
- [Rust serde_json Schema Recovery](#rust-serde_json-schema-recovery)
- [Verilog and Hardware Reverse Engineering](#verilog-and-hardware-reverse-engineering)
- [Prefix-by-Prefix Hash Reversal](#prefix-by-prefix-hash-reversal)
- [Ruby and Perl Polyglot Constraint Satisfaction](#ruby-and-perl-polyglot-constraint-satisfaction)
- [IBM AS/400 SAVF File EBCDIC Decoding](#ibm-as400-savf-file-ebcdic-decoding)
- [Glulx Interactive Fiction Bytecode](#glulx-interactive-fiction-bytecode)

## Roblox Place File Analysis

Version history matters. Diff `Script.Source` across place versions before assuming the newest asset contains the truth.

## Godot Game Asset Extraction

The standard path is:
1. extract the encryption key from the executable
2. unpack the `.pck`
3. inspect scripts/resources in editor-friendly form

## Rust serde_json Schema Recovery

Serde visitors leak the expected JSON shape through field names, traversal order, and value-type-specific callbacks.

## Verilog and Hardware Reverse Engineering

Treat HDL as a timed state machine. Work backward from shift-register taps or hidden-state predicates to the exact action schedule.

## Prefix-by-Prefix Hash Reversal

Language-specific runtime doesn’t matter if the binary itself can act as the oracle. Recover one prefix at a time by running the real transform and matching per-position outputs.

## Ruby and Perl Polyglot Constraint Satisfaction

Polyglot files are usually two different validators sharing one file. Separate which syntax is active per interpreter, then intersect the constraints.

## IBM AS/400 SAVF File EBCDIC Decoding

If a binary blob looks text-like but nothing parses cleanly, test EBCDIC early. Filtering by expected flag charset often reveals the pattern immediately.

## Glulx Interactive Fiction Bytecode

Interactive-fiction VMs still ship dictionaries, object tables, and developer verbs. Grep the story data for hidden commands before solving the validator itself.
