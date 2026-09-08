# Smali Syntax and Opcode Reference

Load when writing non-trivial smali patches — anything beyond `const/4 v0, 0x0; return v0`.

## File anatomy

```smali
.class public Lcom/target/Foo;                    ← class name (fully qualified, L prefix, ; suffix)
.super Ljava/lang/Object;                          ← parent
.source "Foo.java"                                 ← source hint (optional, discarded by ART)

.field private static final TAG:Ljava/lang/String; = "Foo"   ← constant field

.field private mCount:I                            ← instance field

.method public constructor <init>()V               ← constructor
    .registers 1
    invoke-direct { p0 }, Ljava/lang/Object;-><init>()V
    return-void
.end method

.method public getCount()I                         ← method
    .registers 2
    iget v0, p0, Lcom/target/Foo;->mCount:I
    return v0
.end method
```

## Type descriptors

Full form: `L<package>/<class>;`. Nested classes: `L<outer>$<inner>;` (dollar sign).

| Java type | Smali |
|-----------|-------|
| `void` | `V` |
| `boolean` | `Z` |
| `byte` | `B` |
| `short` | `S` |
| `char` | `C` |
| `int` | `I` |
| `long` | `J` |
| `float` | `F` |
| `double` | `D` |
| `String` | `Ljava/lang/String;` |
| `int[]` | `[I` |
| `String[]` | `[Ljava/lang/String;` |
| `int[][]` | `[[I` |
| `List<String>` | `Ljava/util/List;` (generics erased) |

Method descriptors:

- `()V` — takes nothing, returns void.
- `(I)Z` — takes int, returns boolean.
- `(Ljava/lang/String;I)Ljava/lang/String;` — takes String and int, returns String.
- `([BLjava/lang/String;)V` — takes byte[] and String, returns void.

## Register conventions

- **`.registers N`** — total register count including parameters.
- **`.locals M`** — local count only; the assembler computes total by adding parameter count.
- Parameters occupy the **high-numbered** registers:
  - Non-static: `p0` = `this`, `p1..pN` = args in declaration order.
  - Static: `p0..pN-1` = args (no `this`).
- Wide types (`J`, `D`) use two consecutive registers; only refer to the low-numbered one in instructions.

Example, non-static `boolean equals(int a, long b)`:

```
Total registers: 4 (3 params + 1 local?)
  v0 = local
  p0 = this
  p1 = int a
  p2, p3 = long b (wide, two regs)
```

`.locals 1` = 1 local (`v0`); total = 4.

Instructions come in 4-bit and 8-bit register variants:

- `move v0, v1` — both regs < 16.
- `move/from16 v0, v20` — source > 15; assembler picks this.
- `move/16 v20, v21` — both > 15.

If you add local usage that pushes registers past 15, either move registers down or rely on `/from16`.

## Opcodes by group

### Constants

| Opcode | Meaning |
|--------|---------|
| `const/4 vA, #B` | 4-bit constant: -8..7 |
| `const/16 vA, #BB` | 16-bit signed |
| `const vA, #BBBB` | 32-bit |
| `const/high16 vA, #B0000` | High 16 bits, low 16 zero |
| `const-wide/16 vA, #BB` | 16-bit signed to wide reg (long/double) |
| `const-wide vA, #BBBBBBBBBBBBBBBB` | 64-bit |
| `const-string vA, "text"` | Loads a String reference |
| `const-string/jumbo vA, "text"` | For > 65k string pool index |
| `const-class vA, Lcls;` | Class reference |

### Move (register-to-register)

- `move vA, vB` — primitive 32-bit.
- `move-wide vA, vB` — wide (2 regs each).
- `move-object vA, vB` — reference.
- `move-result vA` / `move-result-wide vA` / `move-result-object vA` — grab the last invoke's return.
- `move-exception vA` — copy the caught exception (only valid in `catch` block first instruction).

### Return

- `return-void`
- `return vA` (primitive)
- `return-wide vA` (long/double)
- `return-object vA` (reference)

The return type of the instruction must match the method's declared return type.

### Comparisons and branches

`if-<cond> vA, vB, :label` — two-register comparison, jumps if condition:

| Opcode | Meaning |
|--------|---------|
| `if-eq vA, vB, :label` | `vA == vB` |
| `if-ne` | `vA != vB` |
| `if-lt` | `vA < vB` |
| `if-ge` | `vA >= vB` |
| `if-gt` | `vA > vB` |
| `if-le` | `vA <= vB` |

`if-<cond>z vA, :label` — compare against zero:

| Opcode | Meaning |
|--------|---------|
| `if-eqz vA, :label` | `vA == 0` (false, null, zero) |
| `if-nez vA, :label` | `vA != 0` |
| `if-ltz` | `vA < 0` |
| `if-gez` | `vA >= 0` |
| `if-gtz` | `vA > 0` |
| `if-lez` | `vA <= 0` |

`goto :label` / `goto/16 :label` / `goto/32 :label` — unconditional.

### Method invocation

| Opcode | Meaning |
|--------|---------|
| `invoke-virtual { }, Lcls;->method(...)T` | Instance method, dynamic dispatch |
| `invoke-super { }, Lcls;->method(...)T` | Superclass method |
| `invoke-direct { }, Lcls;->method(...)T` | `<init>`, private, or forced non-virtual |
| `invoke-static { }, Lcls;->method(...)T` | Static method |
| `invoke-interface { }, Lifc;->method(...)T` | Interface method |

Argument list `{v0, v1, v2}` — comma-separated. For non-static: first is `this`. Wide args use one register slot in the list but count as two toward the total register requirement.

`/range` variants for > 5 args or registers > 15:

```smali
invoke-virtual/range { v0 .. v6 }, Lcls;->method(IIIIIII)V
```

### Field access

| Opcode | Meaning |
|--------|---------|
| `iget vA, vB, Lcls;->field:T` | Read instance field from object in `vB` into `vA` |
| `iget-wide vA, vB, Lcls;->field:T` | Wide read (uses `vA` and `vA+1`) |
| `iget-object vA, vB, Lcls;->field:T` | Reference read |
| `iget-boolean vA, vB, Lcls;->field:Z` | Boolean-specific |
| `iput vA, vB, Lcls;->field:T` | Write |
| `sget vA, Lcls;->field:T` | Static read (no object arg) |
| `sput vA, Lcls;->field:T` | Static write |

Type-suffixed variants (`iget-boolean`, `iget-byte`, `iget-char`, `iget-short`) match the field descriptor.

### Object creation

```smali
new-instance v0, Lcom/target/Foo;                  ← allocate (uninitialized)
invoke-direct { v0 }, Lcom/target/Foo;-><init>()V   ← run constructor
```

Never use `v0` between `new-instance` and the `<init>` call — the object is uninitialized and the verifier rejects it.

### Casts

```smali
check-cast v0, Lcom/target/Foo;                    ← ClassCastException on failure
instance-of v1, v0, Lcom/target/Foo;               ← v1 = 1 if instanceof, else 0
```

### Arrays

```smali
const/4 v0, 0xa
new-array v1, v0, [Ljava/lang/String;              ← String[] of length 10

array-length v2, v1                                ← get length into v2
aput-object v3, v1, v0                             ← store v3 at v1[v0]
aget-object v4, v1, v0                             ← load v1[v0] into v4
```

Type-suffixed: `aput-boolean`, `aput-byte`, `aput-char`, `aput-short`, `aput-wide`, `aput-object`, `aput` (int/float).

Array literal via `fill-array-data`:

```smali
fill-array-data v0, :arr

:arr
.array-data 4
    0x1
    0x2
    0x3
.end array-data
```

### Exception handling

```smali
:try_start_0
    invoke-virtual { p0 }, Lcom/target/Foo;->risky()V
    goto :cont
:try_end_0
.catch Ljava/io/IOException; { :try_start_0 .. :try_end_0 } :catch_io
.catch Ljava/lang/Exception; { :try_start_0 .. :try_end_0 } :catch_all

:catch_io
    move-exception v0
    # handle IOException
    goto :cont

:catch_all
    move-exception v0
    # handle any other Exception
    goto :cont

:cont
    return-void
```

- Catch blocks must start with `move-exception` (or nothing, if you don't need the exception).
- The range `:try_start_0 .. :try_end_0` is inclusive-exclusive (like Java bytecode).
- `.catchall` catches `Throwable` — use sparingly; it also catches `Error` subclasses that shouldn't be swallowed.

### Arithmetic

Standard forms: `<op>-int vA, vB, vC`, `<op>-int/2addr vA, vB` (`vA = vA op vB`), `<op>-int/lit8 vA, vB, #C`, `<op>-int/lit16 vA, vB, #CCCC`.

Operations: `add`, `sub`, `mul`, `div`, `rem`, `and`, `or`, `xor`, `shl`, `shr`, `ushr`.

Type suffixes: `-int`, `-long`, `-float`, `-double`.

Type conversion: `int-to-long v0, v1` etc.

## `.line` directives

```smali
.line 42
    const/4 v0, 0x0
```

Source line hints. Debuggers use them. When patching, keep or remove — they don't affect execution.

## Access flags

Class/method/field level:

- `public`, `private`, `protected`
- `static`, `final`, `abstract`, `synthetic`
- `native` — native method, no body (implementation in `.so`).
- `bridge`, `varargs` — compiler-generated hints.
- `constructor` — on `<init>`, `<clinit>`.
- `declared-synchronized` — synchronized method.

Example:

```smali
.method public static final constructor <clinit>()V
```

## Annotations

```smali
.annotation runtime Lcom/target/Marker;
    value = "abc"
.end annotation
```

- `runtime` — retained at runtime, reflection can see it.
- `build` — compile-time only (usually discarded).
- `system` — internal.

Field/parameter annotations attach to the field/parameter directive.

## Common gotchas

- **`.registers` off by one** — verifier error `VFY_ERROR_BAD_INSTRUCTION` at load. Recount both directives.
- **Using an object register after `new-instance` without invoking `<init>`** — verifier rejects.
- **Mismatched wide-register pair** — `move-wide v0, v1` reads two regs starting at v1; if you didn't set both, undefined.
- **Method descriptor typo** — `(Ljava/lang/String)V` (missing semicolon) — assembler catches; runtime never sees it.
- **`invoke-direct` on a public non-final method** — bypasses virtual dispatch; behavior often wrong.
- **`.method` without `.end method`** — assembler error.
- **Adding code between `try_start` and `try_end` without updating the catch block bounds** — new instructions unprotected.
