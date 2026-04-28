# Common BOF anti-patterns

## 1) Parse mismatch between pack and unpack

Symptom: random values, crashes, corrupted pointers.  
Fix: document argument protocol and keep parser order identical to pack order.

## 2) `malloc`/`free` usage in BOF code

Symptom: allocator/runtime issues across loaders.  
Fix: use `GetProcessHeap` + `HeapAlloc`/`HeapFree` only.

## 3) RWX everywhere

Symptom: easy memory-scanner detections.  
Fix: stage as RW, then `VirtualProtect(Ex)` to RX.

## 4) Over-broad DFR import lists

Symptom: large objects, linker pressure, maintenance pain.  
Fix: modularize imports; runtime-resolve non-core APIs.

## 5) Missing cleanup on error paths

Symptom: leaked handles, stale KV pointers, unstable long sessions.  
Fix: single cleanup label + idempotent free/close helpers.

## 6) Hardcoded environment assumptions

Symptom: fragile execution outside one lab host.  
Fix: no absolute paths, no username-specific paths, no static PID assumptions.

## 7) Verbose operator output in production mode

Symptom: noisy telemetry and easy triage by defenders.  
Fix: keep compact output by default; add explicit debug mode.

## 8) One massive monolithic source file

Symptom: difficult review, larger `.text`, slower iteration.  
Fix: isolate helpers in headers/modules and keep `go()` orchestration-focused.
