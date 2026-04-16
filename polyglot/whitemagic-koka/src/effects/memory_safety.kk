// memory_safety - Memory safety verification for handlers (S022 Phase 2 VC5)
// Leak detection and resource cleanup verification

module memory_safety

// ═══════════════════════════════════════════════════════════════════════════
// Memory Safety Effect Definition
// ═══════════════════════════════════════════════════════════════════════════

effect mem-safe
  // Allocation tracking
  fun track-allocation(id: string, size: int, type: string): ()
  fun track-deallocation(id: string): ()
  fun get-live-allocations(): list<(string, int, string)>
  
  // Leak detection
  fun check-leaks(): list<string>  // returns leaked allocation ids
  fun get-leak-count(): int
  fun assert-no-leaks(): bool
  
  // Resource limits
  fun set-max-allocation(max-bytes: int): ()
  fun get-allocated-bytes(): int
  fun check-limits(): bool
  
  // Handler lifecycle verification
  fun record-handler-entry(handler-name: string): ()
  fun record-handler-exit(handler-name: string): ()
  fun get-active-handlers(): list<string>
  fun assert-handler-balanced(): bool

// ═══════════════════════════════════════════════════════════════════════════
// Memory Safety State
// ═══════════════════════════════════════════════════════════════════════════

struct allocation
  id: string
  size: int
  type: string
  timestamp: int

struct handler-frame
  name: string
  entry-time: int
  allocations: list<string>  // allocation ids made during handler

// ═══════════════════════════════════════════════════════════════════════════
// Memory Safety Handler
// ═══════════════════════════════════════════════════════════════════════════

fun handle-memory-safety(action: () -> <mem-safe> a): (a, bool, int)
  var allocations : list<allocation> := []
  var handlers : list<handler-frame> := []
  var max-bytes := 100000000  // 100MB default
  var total-allocated := 0
  
  val result = handle action
    fun track-allocation(id, size, ty)
      allocations := Cons(allocation(id, size, ty, ticks()), allocations)
      total-allocated := total-allocated + size
    
    fun track-deallocation(id)
      match allocations.find(fn(a) a.id == id)
        Just(alloc) ->
          total-allocated := total-allocated - alloc.size
          allocations := allocations.filter(fn(a) a.id != id)
        Nothing -> ()
    
    fun get-live-allocations()
      allocations.map(fn(a) (a.id, a.size, a.type))
    
    fun check-leaks()
      allocations.map(fn(a) a.id)
    
    fun get-leak-count()
      allocations.length
    
    fun assert-no-leaks()
      allocations.length == 0
    
    fun set-max-allocation(max)
      max-bytes := max
    
    fun get-allocated-bytes()
      total-allocated
    
    fun check-limits()
      total-allocated <= max-bytes
    
    fun record-handler-entry(name)
      handlers := Cons(handler-frame(name, ticks(), []), handlers)
    
    fun record-handler-exit(name)
      handlers := handlers.filter(fn(h) h.name != name)
    
    fun get-active-handlers()
      handlers.map(fn(h) h.name)
    
    fun assert-handler-balanced()
      // Check that no allocations were leaked during handler execution
      allocations.length == 0
  
  val had-leaks = allocations.length > 0
  val leak-count = allocations.length
  (result, !had-leaks, leak-count)

// ═══════════════════════════════════════════════════════════════════════════
// Safe resource management combinators
// ═══════════════════════════════════════════════════════════════════════════

fun with-tracked-allocation(id: string, size: int, ty: string, 
                           action: () -> a): <mem-safe> a
  track-allocation(id, size, ty)
  try
    val result = action()
    track-deallocation(id)
    result
  catch
    track-deallocation(id)
    throw

// ═══════════════════════════════════════════════════════════════════════════
// Handler wrapper with automatic memory verification
// ═══════════════════════════════════════════════════════════════════════════

fun verified-handler(name: string, action: () -> <mem-safe> a): <mem-safe> (a, bool)
  record-handler-entry(name)
  val start-allocations = get-live-allocations()
  
  try
    val result = action()
    val end-allocations = get-live-allocations()
    val leaked = end-allocations.length - start-allocations.length
    record-handler-exit(name)
    (result, leaked == 0)
  catch
    record-handler-exit(name)
    throw

// ═══════════════════════════════════════════════════════════════════════════
// Leak detection report
// ═══════════════════════════════════════════════════════════════════════════

struct leak-report
  total-leaks: int
  total-bytes-leaked: int
  leaks-by-type: list<(string, int, int)>  // type, count, bytes
  
fun generate-leak-report(): <mem-safe> leak-report
  val live = get-live-allocations()
  val total = live.length
  val bytes = live.foldl(0) fn(acc, a) acc + a.snd
  
  // Group by type
  val by-type = live.group-by(fn(a) a.thd).map(fn(g)
    val count = g.length
    val bytes = g.foldl(0) fn(acc, a) acc + a.snd
    (g.head.default(("", 0, "")).thd, count, bytes)
  )
  
  leak-report(total, bytes, by-type)

// ═══════════════════════════════════════════════════════════════════════════
// Memory-safe effect composition
// ═══════════════════════════════════════════════════════════════════════════

fun compose-safely(action1: () -> <mem-safe> a, 
                   action2: a -> <mem-safe> b): <mem-safe> (b, bool)
  val (r1, safe1) = verified-handler("action1", action1)
  val (r2, safe2) = verified-handler("action2", fn() action2(r1))
  (r2, safe1 && safe2)

// ═══════════════════════════════════════════════════════════════════════════
// Test utilities
// ═══════════════════════════════════════════════════════════════════════════

fun run-memory-test(name: string, action: () -> ()): (bool, string)
  val (_, safe, leaks) = handle-memory-safety(action)
  if safe then
    (True, name ++ ": PASS - no leaks")
  else
    (False, name ++ ": FAIL - " ++ leaks.show ++ " leaks detected")
