# Koka Language Guide for WhiteMagic Polyglot

## Version & Installation

- **Installed**: Koka v3.2.2 (Jul 22, 2025)
- **Latest**: v3.2.3 (Mar 17, 2026) — minor bugfix release
- **Install dir**: `/home/lucas/.local/bin/koka`
- **Lib dir**: `/home/lucas/.local/share/koka/v3.2.2/lib`
- **Backend**: GCC (C compilation with evidence translation)

### Upgrading

```bash
# Download v3.2.3 from https://github.com/koka-lang/koka/releases
# Or use VS Code extension which auto-updates
```

## Key Syntax (v3)

### Module Declaration

```koka
module my-module
import std/os/readline
import another-module
```

- Everything is **private by default**
- Use `pub` to export: `pub fun`, `pub val`, `pub type`, `pub effect`, `pub struct`
- Module name must match file path (e.g. `src/effects/circuit_breaker.kk` → module `circuit_breaker`)

### Effect Declaration

```koka
pub effect my-effect
  fun operation-name(params): return-type   // resumable (auto-resumes with return value)
  ctl operation-name(params): return-type   // general control (must call resume explicitly)
  final ctl operation-name(params): a       // non-resumable (like exceptions, no resume)
```

- `fun` operations: **auto-resumable** — the handler body's return value is the resume value
- `ctl` operations: **manual resume** — handler must call `resume(x)` to continue
- `final ctl`: **non-resumable** — handler cannot resume (like throwing an exception)

### Handler Syntax (v3 — `with`)

The **preferred v3 syntax** uses `with`:

```koka
fun my-handler(action: () -> <my-effect> a): a
  var state := 0
  with
    fun get-state() state          // auto-resumes with `state`
    fun set-state(new-val) state := new-val  // auto-resumes with ()
  action()
```

The `with` binds the handler over the rest of the function body. `var` declarations before `with` are captured by the handler clauses.

### Handler Syntax (v2 — `handle`, still works but deprecated)

```koka
fun my-handler(action: () -> <my-effect> a): a
  var state := 0
  handle action
    fun get-state() state
    fun set-state(new-val) state := new-val
```

**Prefer `with` over `handle`** in new code.

### First-Class Handler Values

```koka
val my-handler = handler
  fun get() state
  fun set(x) state := x

// Use later:
with my-handler
  some-action()
```

### Multiple Effects

Chain `with` handlers:

```koka
with handler1
  with handler2
    action()
```

Or use indented blocks to limit scope:

```koka
val result =
  with handler1
    action()
// handler1 no longer in scope here
```

### Cross-Module Effect Usage

Effect operations are **not regular functions** — they're part of the effect type. When you `import` a module with a `pub effect`, the operations become available:

```koka
// module A
pub effect foo
  fun bar(): int

pub fun handle-foo(action: () -> <foo> a): a
  with
    fun bar() 42
  action()

// module B
import A
// bar() is available here — it has type `<foo> int`
// handle-foo is available as a regular function
```

**Key insight**: You don't qualify effect operations with module paths. They're in scope directly when the effect is imported. However, the **handler function** (like `handle-foo`) is a regular function and may need qualification.

### Mutable State

- `var x := 0` — mutable local (inside function bodies only)
- `val x = 0` — immutable (works at module level and inside functions)
- **No module-level `var`** — use `var` inside handler functions instead
- For "global" mutable state, use a handler that captures a `var`

### Types

```koka
// Algebraic data type
type color
  Red
  Green
  Blue

// Struct (constructor is Capitalized)
struct point
  x: int
  y: int

// Constructor: Point(x, y) — note capital P
// Accessor: p.x, p.y
```

**Important**: Struct constructors are **Capitalized** (e.g. `Circuit-config`, not `circuit-config`).

### Standard Library

| Module | Key Functions |
|--------|--------------|
| `std/core/console` | `println`, `print` (auto-imported) |
| `std/os/readline` | `readline` |
| `std/num/float64` | Float arithmetic |
| `std/time/timer` | `ticks()` → duration |
| `std/core/exn` | `throw`, `try`, `catch` |
| `std/core/maybe` | `Just`, `Nothing`, `maybe` |
| `std/core/list` | `Cons`, `Nil`, `map`, `filter`, `find`, `head`, `drop` |

### String Operations

- Concatenation: `s1 ++ s2`
- Split: `s.split(":")` → returns `list<string>`
- Show: `x.show` or `show(x)`
- String-to-int: `string-to-int(s)` (from `std/core`)
- Int-to-string: `int-to-string(i)` or `i.show`

### List Operations

- `xs.find(fn(x) x == target)` → `maybe<a>`
- `xs.filter(fn(x) predicate)` → `list<a>`
- `xs.head()` → `maybe<a>` (safe head)
- `xs.drop(n)` → `list<a>` (drop first n elements)
- `xs.length` → `int` (on vectors; for lists use `xs.count`)

### Compilation

```bash
# Compile to native binary
koka -e --cc gcc -O2 -o output_name source.kk

# Compile only (type check)
koka -e --cc gcc -O2 -c source.kk -o /dev/null

# Include paths for module resolution
koka -e --cc gcc -O2 -I src/effects -o output source.kk
```

- `-e`: evaluate/compile mode
- `--cc gcc`: use GCC backend
- `-O2`: optimization level 2
- `-o name`: output binary name
- `-c`: compile only (no linking)
- Koka auto-resolves modules in the same directory as the source file

### Try/Catch (Exception Handling)

In Koka v3, use `try` as a **function**, not syntax:

```koka
// Correct v3 syntax
try(fn() { risky-action() }, fn(exn) { handle-error(exn) })

// NOT this (v2 syntax, doesn't work in v3)
try
  risky-action()
catch exn
  handle-error(exn)
```

`throw` takes a **string** message: `throw("error message")`

### Common Pitfalls

1. **`handle` vs `with`**: Use `with` in v3. `handle` still works but syntax is awkward.
2. **Constructor capitalization**: `Circuit-status(...)`, not `circuit-status(...)`
3. **Module-level `var`**: Not allowed. Use `var` inside functions.
4. **`std/json`**: Doesn't exist in v3.2.2. Use line-based protocol or write your own parser.
5. **Effect operation qualification**: Don't qualify with module path. They're in scope directly.
6. **`if` without `else`**: Returns `()` (unit). Both branches needed for non-unit types.
7. **`catch` syntax**: Use `try(action_fn, handler_fn)` function form, not `try/catch` syntax.
8. **`throw` type**: Takes `string`, not `exception` object. Use `throw("msg")`.
9. **`resume`**: Only available inside `ctl` handler clauses. `fun` operations auto-resume.
10. **Tuple destructuring**: Match the exact order. `(name, config, status)` — first element is `name`, not `config`.

### WhiteMagic Koka Architecture

```
polyglot/whitemagic-koka/
├── src/
│   ├── effects/
│   │   ├── circuit_breaker.kk      # Circuit breaker effect + handler
│   │   ├── circuit_dispatch.kk     # Standalone binary: line protocol bridge
│   │   ├── backpressure.kk         # Backpressure effect
│   │   └── error_tests.kk          # Test suite
│   └── psr/psr-008/
│       └── effect_handlers.kk      # Unified effect composition
```

### Compilation Protocol

Koka binaries communicate with Python via **line-based stdio protocol**:

```
# Request:  op:name:arg1:arg2:...
# Response: ok:result  or  error:message

check:ollama           → ok:closed
failure:ollama         → ok:recorded
check:ollama           → ok:open
reset:ollama           → ok:reset
configure:tool:5:10000:3 → ok:configured
quit                   → ok:bye
```

Python side uses `subprocess.Popen` with stdin/stdout pipes.

### References

- [Koka Book](https://koka-lang.github.io/koka/doc/book.html)
- [Koka GitHub](https://github.com/koka-lang/koka)
- [Effect Handlers Blog (Tim Whiting)](https://timwhiting.dev/blog/effect-handlers.html)
- [ICFP'21 Tutorial](https://www.youtube.com/watch?v=6OFhD_mHtKA)
- [Generalized Evidence Passing Paper](https://xnning.github.io/papers/multip.pdf)
- [LWN.net Article](https://lwn.net/Articles/1033050/)
