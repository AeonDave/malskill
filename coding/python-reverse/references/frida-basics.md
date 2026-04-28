# Frida: Dynamic instrumentation

Frida allows you to inject Python code into running processes to hook functions, intercept calls, and modify behavior.

## Basics: Attach and hook

### Process attachment

```python
import frida

# Attach to process by name
session = frida.attach("notepad.exe")

# Or by PID
session = frida.attach(1234)

# Detach
session.detach()
```

### Simple function hook

```python
import frida

def on_message(message, data):
    if message['type'] == 'send':
        print(f"[*] {message['payload']}")
    elif message['type'] == 'error':
        print(f"[!] {message['stack']}")

session = frida.attach("target.exe")

# Frida script (JavaScript/TypeScript)
script_code = """
Interceptor.attach(Module.findExportByName(null, "printf"), {
    onEnter: function(args) {
        console.log("[*] printf called");
        console.log("[*] First arg: " + args[0].readCString());
    }
});
"""

script = session.create_script(script_code)
script.on('message', on_message)
script.load()
input()  # Keep process running
session.detach()
```

## Common hooks

### Intercept malloc/free

```javascript
Interceptor.attach(Module.findExportByName(null, "malloc"), {
    onEnter: function(args) {
        var size = args[0].toInt32();
        console.log("[malloc] size: " + size);
    },
    onLeave: function(retval) {
        console.log("[malloc] allocated at: " + retval);
    }
});
```

### Syscall tracing

```javascript
// On Linux: trace open() syscall
Interceptor.attach(Module.findExportByName(null, "open"), {
    onEnter: function(args) {
        console.log("[open] file: " + args[0].readCString());
    }
});
```

### Bypass function

```javascript
// Skip function; return hardcoded value
Interceptor.replace(Module.findExportByName(null, "check_license"), {
    onEnter: function(args) {
        console.log("[check_license] bypassed");
    },
    onLeave: function(retval) {
        retval.replace(1);  // Return 1 (success)
    }
});
```

## Data inspection

### Read strings from memory

```javascript
var ptr = args[0];
if (ptr !== null) {
    var string = ptr.readCString();
    console.log("[*] String: " + string);
}
```

### Read structures

```javascript
var struct_ptr = args[0];
var field1 = struct_ptr.add(0).readU32();
var field2 = struct_ptr.add(4).readCString();
console.log("[*] Field1: " + field1 + ", Field2: " + field2);
```

## Anti-patterns

- **Crashing the target with bad pointers**: Always check nulls and offsets.
- **Logging too much**: Frida's overhead is high; filter aggressively.
- **Not handling exceptions**: Wrap hooks in try/catch to prevent session death.
- **Assuming ASLR is off**: Always use `Module.findExportByName()` or dynamic base address resolution.

## Common pitfalls

- **Hook doesn't fire**: Function may be inlined, use a different calling convention, or be in a different module.
- **Infinite recursion in hook**: Don't call the hooked function from inside the hook without careful guard.
- **Process crashes after detach**: If you modified memory/registers, crashes may occur on detach; use safe detach patterns.

---

## References

- https://frida.re/
- https://frida.re/docs/home/
- https://github.com/frida/frida
