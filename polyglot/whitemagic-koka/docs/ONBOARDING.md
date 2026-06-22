# Koka for Python Developers - Onboarding Guide (S022 Phase 6 VC4)

## Introduction

Welcome to Koka development for WhiteMagic! This guide will help Python developers quickly become productive with Koka's algebraic effects system.

## Quick Start

### 1. Understanding Algebraic Effects

If you've used Python context managers or decorators, you already understand the basic idea:

**Python Context Manager:**
```python
with database.transaction() as tx:
    tx.execute("INSERT ...")
```

**Koka Effect Handler:**
```koka
with handle-transactions
  transaction/execute("INSERT ...")
```

The key difference: Koka effects are typed and composable.

### 2. Your First Koka Module

**File: `hello_effects.kk`**
```koka
module hello_effects

// Define an effect
effect greeting
  fun say-hello(name: string): string
  fun say-goodbye(): string

// Implement the handler
val handle-greeting = handler
  fun say-hello(name) "Hello, " ++ name ++ "!"
  fun say-goodbye() "Goodbye!"

// Use the effect
fun main()
  with handle-greeting
  println(greeting/say-hello("Developer"))
  println(greeting/say-goodbye())
```

### 3. Key Differences from Python

| Python | Koka | Notes |
|--------|------|-------|
| `self.method()` | `effect/operation()` | Explicit effect |
| `self.variable` | `var variable` | Mutable state |
| `try/except` | `try/catch` | Similar syntax |
| `with x as y:` | `with handler` | Similar concept |
| `lambda x: x` | `fn(x) x` | Anonymous functions |
| `None` | `Nothing` | Null handling |
| `True/False` | `True/False` | Same bools |

### 4. Common Patterns Translated

#### Class with State → Effect + Handler

**Python:**
```python
class Counter:
    def __init__(self):
        self.count = 0
    
    def increment(self):
        self.count += 1
        return self.count
```

**Koka:**
```koka
effect counter
  fun increment(): int

val handle-counter = handler
  var count := 0
  fun increment()
    count := count + 1
    count
```

#### Exception Handling → Try/Catch

**Python:**
```python
try:
    risky_operation()
except ValueError as e:
    print(f"Error: {e}")
```

**Koka:**
```koka
try
  risky-operation()
catch
  println("Error occurred")
```

#### Decorators → Handler Composition

**Python:**
```python
@log_calls
@validate_args
def my_function(x):
    return x * 2
```

**Koka:**
```koka
with handle-log-calls
  with handle-validate-args
    my-function(x)
```

### 5. Type System Basics

#### Basic Types
```koka
// Numbers
let x : int = 42
let y : float64 = 3.14

// Strings  
let s : string = "hello"

// Booleans
let b : bool = True

// Lists
let xs : list<int> = [1, 2, 3]

// Maybe (like Optional)
let m : maybe<int> = Just(42)
let n : maybe<int> = Nothing
```

#### Functions
```koka
// Simple function
fun add(x: int, y: int): int
  x + y

// Function with effects
fun greet(name: string): <greeting> string
  greeting/say-hello(name)

// Generic function
fun identity(x: a): a
  x
```

#### Structs (like dataclasses)
```koka
struct person
  name: string
  age: int

fun make-person(n: string, a: int): person
  person(n, a)
```

### 6. Effect System Deep Dive

#### Defining Effects
```koka
// Effect with multiple operations
effect database
  fun query(sql: string): list<row>
  fun insert(sql: string): int
  fun transaction-begin(): string
  fun transaction-commit(tx: string): bool
```

#### Implementing Handlers
```koka
// Production handler
val handle-database-prod = handler
  fun query(sql)
    // Real database query
    []
  
  fun insert(sql)
    // Real insert
    1
  
  // ... other operations

// Test/mock handler
val handle-database-mock = handler
  fun query(sql)
    // Return mock data
    [mock-row-1, mock-row-2]
  
  fun insert(sql)
    // Just pretend
    1
```

#### Effect Row Polymorphism
```koka
// Function works with ANY effects
fun do-something(): e ()
  // Can be used in any effect context

// Function requires specific effects
fun do-database-thing(): <database, logging> ()
  // Requires database and logging effects
```

### 7. Common WhiteMagic Effects

#### PRAT Router Effects
```koka
with handle-prat-auth-production
  with handle-prat-rate-production
    prat-route/dispatch-tool("memory.create", "{}")
```

#### Session Effects
```koka
with handle-session-state("session-123")
  val id = session-st/get-session-id()
  session-st/set-last-gana("gana_horn")
```

#### Circuit Breaker
```koka
with handle-circuit-breaker
  with-circuit-protection("database", fn()
    database/query("SELECT * FROM memories")
  )
```

### 8. Testing Koka Code

#### Unit Tests
```koka
fun test-counter-increments(): bool
  with handle-counter
    val first = counter/increment()
    val second = counter/increment()
    first == 1 && second == 2
```

#### Mock Effects
```koka
fun test-with-mock-database(): bool
  with handle-database-mock
    val results = database/query("SELECT *")
    results.length > 0
```

#### Property Tests
```koka
fun test-increment-always-positive(): bool
  with handle-counter
    val result = counter/increment()
    result > 0
```

### 9. Debugging Tips

#### Trace Effect Execution
```koka
with handle-visualization
  with handle-my-effect
    // Operations will be traced
    my-effect/do-something()
```

#### Inspect Handler State
```koka
val handle-my-effect-debug = handler
  var state := initial-state
  
  fun operation()
    println("DEBUG: State before = " ++ state.show)
    val result = compute-result()
    state := new-state
    println("DEBUG: State after = " ++ state.show)
    result
```

### 10. Performance Considerations

#### Handler Composition Order
```koka
// Good: Resources outermost
with handle-resource-pools
  with handle-circuit-breaker
    with handle-retry
      // business logic

// Avoid: Deep nesting (>7 levels)
```

#### State Management
```koka
// Prefer: Immutable updates
var list := Cons(item, list)

// Avoid: Frequent mutations in tight loops
```

### 11. Migration Workflow

1. **Identify** Python patterns suitable for Koka
   - Handler chains
   - State machines
   - Error handling
   - Resource management

2. **Translate** using patterns from `TRANSLATION_PATTERNS.md`

3. **Test** with mock handlers

4. **Integrate** with Python via FFI bridge

5. **Benchmark** against Python baseline

### 12. Resources

- **Style Guide**: `docs/KOKA_STYLE_GUIDE.md`
- **Translation Patterns**: `docs/TRANSLATION_PATTERNS.md`
- **Effect Reference**: `src/effects/README.md`
- **Examples**: `src/examples/`

### 13. Common Pitfalls

#### Forgetting Effect Declarations
```koka
// Wrong
fun my-fun(): string
  effect/operation()  // Error: effect not in signature

// Right
fun my-fun(): <my-effect> string
  effect/operation()
```

#### Misplacing State Initialization
```koka
// Wrong
val handle-effect = handler
  var state := []  // Shared across all invocations!

// Right
fun handle-effect(config)
  var state := initial-state  // Per-invocation
```

#### Ignoring Effect Rows
```koka
// Wrong
fun compose(f: () -> e a, g: a -> e b): () -> b
  fn() g(f())

// Right
fun compose(f: () -> e a, g: a -> e b): () -> e b
  fn() g(f())
```

### 14. Getting Help

- Check existing effect implementations in `src/effects/`
- Review translation patterns for your use case
- Test incrementally with mock handlers
- Use visualization to debug effect flows

## Next Steps

1. Port a simple Python class to Koka
2. Write tests using mock handlers
3. Compose your effect with existing WhiteMagic effects
4. Benchmark and compare with Python

Welcome to effect-typed programming!
