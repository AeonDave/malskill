# CTF Reverse - Dynamic Analysis and Instrumentation Tools

Focused tool reference for runtime observation, path exploration, and debugger-assisted or injected instrumentation.

## Table of Contents
- [Frida](#frida)
- [angr](#angr)
- [lldb](#lldb)
- [x64dbg](#x64dbg)
- [Register and Output Side-Channel Breakpoints](#register-and-output-side-channel-breakpoints)
- [radare2 Panels for VM Tracing](#radare2-panels-for-vm-tracing)
- [libSegFault Register Dumps](#libsegfault-register-dumps)
- [r2pipe plus Constraint Extraction](#r2pipe-plus-constraint-extraction)
- [strcmp and memcmp Oracle Breakpoints](#strcmp-and-memcmp-oracle-breakpoints)

## Frida

Use Frida when you need runtime truth faster than static certainty.

Best targets:
- `strcmp`, `memcmp`, crypto APIs, anti-debug helpers
- Java methods in Android apps
- hot-patching return values or side-step logic

## angr

Use angr for validators with clear success/failure states and manageable symbolic state.

Best practices:
- constrain input early
- hook expensive functions
- start from the simplest find/avoid strategy first

## lldb

lldb is the natural debugger for Mach-O, Swift, and Apple-heavy artifacts.

## x64dbg

x64dbg is the quickest Windows-first debugger for CTF binaries when you want GUI breakpointing, hardware breakpoints, and lightweight scripting.

## Register and Output Side-Channel Breakpoints

Breaking on output functions like `putchar` or `write` often turns fake delays into instant extraction.

## radare2 Panels for VM Tracing

`V!` panel layouts are extremely effective for custom VMs: next opcode, stack, heap, and host locals all visible together.

## libSegFault Register Dumps

If GDB is blocked or noisy, `libSegFault.so` can still give you a crash-time register snapshot with almost zero setup.

## r2pipe plus Constraint Extraction

When a giant binary is really just a repeated hash/compare machine, parse blocks into machine-readable constraints and solve outside the disassembler.

## strcmp and memcmp Oracle Breakpoints

Late-stage comparisons are gold. The final compare site often leaks the entire target transformation in one run.
