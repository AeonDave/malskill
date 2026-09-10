# Frida: Dynamic instrumentation

Python is the **host**. Hooks run as **GumJS** inside the target. Do not write hooks as Python.

Frida **17+** (2025): static `Module.findExportByName` / `Module.getExportByName` were **removed**. Resolve a module first, or use the global-export helpers.

## Host: attach vs spawn

```python
import frida

def on_message(message, data):
    if message["type"] == "send":
        print(message["payload"])
    elif message["type"] == "error":
        print(message.get("stack", message))

# Already running: attach by name or PID
session = frida.attach("target")           # or frida.attach(pid)

# Constructor / early init: spawn, load script, then resume
# pid = frida.spawn(["./target"])
# session = frida.attach(pid)

JS = """
const m = Process.getModuleByName("libc.so"); // Windows: kernel32.dll
Interceptor.attach(m.getExportByName("open"), {
  onEnter(args) {
    try { send(args[0].readUtf8String()); } catch (e) { send(String(e)); }
  }
});
"""

script = session.create_script(JS)
script.on("message", on_message)
script.load()
# frida.resume(pid)  # only after spawn + load
input()
session.detach()
```

## JS: resolve exports (Frida 17+)

```javascript
// Known module (preferred; do not look the module up twice)
const libc = Process.getModuleByName("libc.so");  // Windows: "kernel32.dll"
const openPtr = libc.getExportByName("open");     // throws if missing
// findExportByName on the Module object returns null instead of throwing

// Unknown module (slow; last resort)
const printfPtr = Module.getGlobalExportByName("printf");  // throws if missing
```

`get*` throws; `find*` returns `null`. Check null before `Interceptor.attach`.

## Hook: Interceptor.attach

```javascript
Interceptor.attach(openPtr, {
  onEnter(args) {
    try {
      this.path = args[0].readUtf8String();
    } catch (e) {
      this.path = "<unreadable>";
    }
  },
  onLeave(retval) {
    send({ path: this.path, fd: retval.toInt32() });
  }
});
```

Windows strings: `readUtf16String()` for `*W` APIs.

## Replace: NativeCallback only

`Interceptor.replace(ptr, NativeCallback)` — not an `{ onEnter, onLeave }` object. To also call the original, wrap it with `NativeFunction`.

```javascript
const open = new NativeFunction(openPtr, "int", ["pointer", "int"]);
Interceptor.replace(openPtr, new NativeCallback((pathPtr, flags) => {
  send(pathPtr.readUtf8String());
  return open(pathPtr, flags);
}, "int", ["pointer", "int"]));
```

Bypass a check without knowing the full ABI: `attach` + `retval.replace(...)` in `onLeave`.

## Anti-patterns

- **Python inside `create_script`**: the VM is JS.
- **Removed Module statics** on Frida 17+: `Module.findExportByName(null, "open")`.
- **`replace` with attach-style callbacks**.
- **Hooking without null checks**: inlined functions, wrong module, or `find*` miss.
- Logging every call on a hot path; filter in JS and `send()` summaries.

## References

- https://frida.re/docs/javascript-api/
- https://frida.re/news/2025/05/17/frida-17-0-0-released/
- https://frida.re/docs/functions/
