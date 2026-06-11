# BOF Anti-Patterns and Crash Diagnosis

**Load when**: The BOF compiles successfully but crashes the beacon process or behaves unpredictably at runtime.

## 1. Stack Strings over 4096 bytes
**Anti-Pattern**: `char buffer[8192];`
**Why it fails**: When you declare variables larger than 4KB, `gcc` implicitly inserts `___chkstk_ms` to probe the stack. This symbol doesn't exist unless you manually link gcc libraries. *The BOF will fail to link or crash.*
**Fix**: Use `HeapAlloc` / `HeapFree` via `KERNEL32$HeapAlloc(KERNEL32$GetProcessHeap(), HEAP_ZERO_MEMORY, 8192)`.

## 2. Missing `extern "C"` (C++ Only)
**Anti-Pattern**: `void go(char* args, int alen) { ... }` in a `.cpp` file.
**Why it fails**: C++ mangles the function name (e.g., `_Z2gopci`). The loader searches for the literal string `go` and fails to launch.
**Fix**: `extern "C" void go(char* args, int alen) { ... }`

## 3. Library Unloading
**Anti-Pattern**: `FreeLibrary(hModule)` at the end of the BOF.
**Why it fails**: If you loaded a DLL (e.g., `USER32.dll`) explicitly with `LoadLibraryA`, and the C2 framework or another thread relies on it, freeing it will cause widespread process violation. Always ensure it's safe to unload, or intentionally accept the memory leak in favor of process stability.

## 4. Unhandled Thread Exits
**Why it fails**: Using `ExitProcess(0)` inside a BOF terminates the entire C2 host process, killing your session alongside it.
**Fix**: Always return gracefully from the entry point (`return;`) or use `ExitThread(0)` if you spawned a worker thread safely.
