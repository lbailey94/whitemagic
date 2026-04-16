// koka_style_guide - WhiteMagic Koka Style Guide (S022 Phase 6 VC1)
// Complete style guide for Koka development in WhiteMagic

module koka_style_guide

// ═══════════════════════════════════════════════════════════════════════════
// STYLE GUIDE DOCUMENTATION
// ═══════════════════════════════════════════════════════════════════════════
/*

# WhiteMagic Koka Style Guide

## Naming Conventions

### Effects
- Use lowercase with hyphens: `effect prat-route`, `effect memory-ops`
- Group related effects by prefix: `prat-*`, `gana-*`, `dream-*`

### Functions
- Use kebab-case: `route-prat-call`, `get-predecessor-gana`
- Predicates end with ? (when possible): `is-valid?`, `has-capacity?`
- Actions use verbs: `emit-event`, `record-snapshot`

### Types
- Use PascalCase: `gana-meta`, `spell-registry`, `circuit-state`
- Struct fields use kebab-case

### Modules
- Use snake_case: `prat_effects`, `gana_base`, `grimoire_spells`
- Match Python file names where porting

## Effect Organization

### Effect Definition Pattern
```koka
effect effect-name
  fun operation-1(param: type): return-type
  fun operation-2(param: type): return-type
```

### Handler Implementation Pattern
```koka
val handle-effect-name = handler
  var state := initial-state
  
  fun operation-1(p)
    // implementation
  fun operation-2(p)
    // implementation
```

### Handler with Parameters
```koka
fun handle-effect-name(config: config-type, action: () -> <effect-name> a): a
  var state := initial-state
  handle action
    fun operation(p)
      // use config and state
```

## Effect Composition Guidelines

### 1. Effect Stacking Order
Place most-specific effects innermost:
```koka
with handle-backpressure(config)
  with handle-circuit-breaker
    with handle-retry(3)
      // operation
```

### 2. Error Effect Placement
Error effects (circuit, retry, timeout) should wrap business logic:
```koka
with handle-timeout(5000)
  with handle-circuit("memory-ops")
    memory-ops/store-data(key, value)
```

### 3. Resource Effects
Resource effects (pools, transactions) should be outermost:
```koka
with handle-transactions
  with handle-resource-pools
    // database operations
```

## Type Safety Patterns

### Maybe Type Usage
Use maybe for optional values:
```koka
fun find-spell(name: string): maybe<spell>
```

### Result Type for Operations
Return tuples for operations with status:
```koka
fun with-retry(max: int, action: () -> a): (a, int, bool)
// returns (result, attempts, success)
```

### Effect Row Polymorphism
Always declare full effect rows:
```koka
fun my-function(x: int): <effect1, effect2, effect3> return-type
```

## Documentation Standards

### Module Header
```koka
// module-name - Brief description (Campaign ID VC#)
// Longer description explaining purpose

module module-name
```

### Function Documentation
```koka
// Brief description
// Longer explanation if needed
// Parameters: name - description
// Returns: description
fun function-name(param: type): return-type
```

## Testing Patterns

### Test Function Naming
```koka
fun test-<component>-<scenario>-<expected-result>(): test-result
```

### Test Structure
```koka
fun run-<component>-tests(): list<test-result>
  [
    test-case-1(),
    test-case-2(),
    // ...
  ]
```

## FFI Integration

### Python FFI Calls
```koka
fun python-function-via-ffi(arg: string): <py-ffi> string
  py-ffi/py-call(
    "python.module.name",
    "function_name",
    json-encode(arg)
  )
```

### JSON Encoding
Always encode complex types to JSON for FFI:
```koka
fun data-to-json(d: data-type): string
  // implementation
```

## Performance Considerations

### 1. Minimize Effect Rows
Don't add unnecessary effects to rows

### 2. Handler State Efficiency
Use appropriate data structures:
- Lists for small collections (< 100)
- Consider custom structures for larger

### 3. Avoid Deep Nesting
Limit handler nesting to 5-7 levels

## Common Patterns

### State Management
```koka
fun with-state(initial: state-type, action: () -> <state-effect> a): a
  var current := initial
  handle action
    fun get() current
    fun set(new) current := new
```

### Resource Guard Pattern
```koka
fun with-resource(acquire: () -> bool, release: () -> (), action: () -> a): a
  if !acquire() then throw("acquire_failed")
  try
    val result = action()
    release()
    result
  catch
    release()
    throw
```

### Retry with Backoff
```koka
fun with-exponential-backoff(attempt: int): int
  min(30000, 100 * pow(2, attempt))
```

## Porting Guidelines (Python → Koka)

### Class → Effect + Handler
```python
# Python
class MyClass:
  def __init__(self): self.state = {}
  def method(self): pass
```

```koka
// Koka
effect my-effect
  fun method(): return-type

val handle-my-effect = handler
  var state := empty-map()
  fun method() 
    // implementation
```

### Exception Handling → Effect
```python
# Python
try:
  risky_operation()
except Exception:
  handle_error()
```

```koka
// Koka
try
  risky-operation()
catch
  handle-error()
```

### Context Managers → Resource Effect
```python
# Python
with resource_manager() as r:
  use_resource(r)
```

```koka
// Koka
with-resource(
  fn() acquire(),
  fn() release(),
  fn() use-resource()
)
```

## Best Practices

1. **Always declare effect rows explicitly** - No implicit effects
2. **Use typed effects over generic state** - Prefer `effect session-st` over generic `ref`
3. **Handle effects at appropriate boundaries** - Don't leak internal effects
4. **Compose handlers in dependency order** - Resources outermost, errors inner
5. **Test with mock handlers** - Create test handlers for unit tests
6. **Document effect semantics** - Explain what each effect operation does
7. **Keep handlers focused** - One handler per concern
8. **Avoid handler state mutation** - Use immutable updates where possible

## Migration Priority

Priority order for porting Python to Koka:
1. Handler chains (prat_router, middleware)
2. State machines (dream_cycle, session)
3. Error handling (circuit_breaker, retry)
4. Resource management (pools, transactions)
5. Async/event handling (gan_ying)
6. Business logic (ganas, spells)

*/

// ═══════════════════════════════════════════════════════════════════════════
// Style Guide Enforcement Helpers
// ═══════════════════════════════════════════════════════════════════════════

// Check function name follows kebab-case
fun is-valid-function-name(name: string): bool
  // Contains only lowercase, numbers, and hyphens
  name.all(fn(c) c.is-lower || c.is-digit || c == '-')

// Check effect name follows lowercase-hyphen
fun is-valid-effect-name(name: string): bool
  name.all(fn(c) c.is-lower || c == '-')

// Check module name follows snake_case
fun is-valid-module-name(name: string): bool
  name.all(fn(c) c.is-lower || c.is-digit || c == '_')

// ═══════════════════════════════════════════════════════════════════════════
// Style Violation Reporting
// ═══════════════════════════════════════════════════════════════════════════

struct style-violation
  file: string
  line: int
  rule: string
  message: string

// This would be populated by a linter
fun report-style-violations(): list<style-violation>
  []  // Populated by external analysis
