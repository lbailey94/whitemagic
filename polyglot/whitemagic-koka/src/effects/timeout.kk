// timeout - Divergence effect for timeout handling (S022 Phase 3 VC3)
// Non-termination effects with timeout bounds

module timeout

// ═══════════════════════════════════════════════════════════════════════════
// Timeout Effect Definition
// ═══════════════════════════════════════════════════════════════════════════

effect timeout
  // Set timeout for operations
  fun set-timeout(ms: int): ()
  fun get-timeout(): int
  fun extend-timeout(additional-ms: int): ()
  fun clear-timeout(): ()
  
  // Timeout check
  fun is-timed-out(): bool
  fun time-remaining(): int  // milliseconds remaining
  
  // Nested timeout
  fun push-timeout(ms: int): ()  // save current, set new
  fun pop-timeout(): ()  // restore previous

// ═══════════════════════════════════════════════════════════════════════════
// Divergence Effect (non-termination tracking)
// ═══════════════════════════════════════════════════════════════════════════

effect divergence
  // Track potentially non-terminating operations
  fun mark-divergent(op-name: string): ()
  fun check-termination-bound(): bool  // returns true if should continue
  fun get-divergence-depth(): int
  fun assert-terminates(max-steps: int): bool

// ═══════════════════════════════════════════════════════════════════════════
// Timeout State
// ═══════════════════════════════════════════════════════════════════════════

struct timeout-frame
  timeout-at: int  // absolute tick count
  original-timeout: int

// ═══════════════════════════════════════════════════════════════════════════
// Timeout Handler
// ═══════════════════════════════════════════════════════════════════════════

fun handle-timeout(default-ms: int, action: () -> <timeout> a): (a, bool)
  var stack : list<timeout-frame> := []
  var current-timeout := default-ms
  var start-tick := ticks()
  
  val result = handle action
    fun set-timeout(ms)
      current-timeout := ms
      start-tick := ticks()
    
    fun get-timeout()
      current-timeout
    
    fun extend-timeout(additional)
      current-timeout := current-timeout + additional
    
    fun clear-timeout()
      current-timeout := -1  // No timeout
    
    fun is-timed-out()
      if current-timeout < 0 then False
      else
        val elapsed = ticks() - start-tick
        elapsed > current-timeout
    
    fun time-remaining()
      if current-timeout < 0 then 1000000  // "Infinite"
      else
        val elapsed = ticks() - start-tick
        max(0, current-timeout - elapsed)
    
    fun push-timeout(ms)
      val current-end = if current-timeout < 0 then -1 else start-tick + current-timeout
      stack := Cons(timeout-frame(current-end, current-timeout), stack)
      current-timeout := ms
      start-tick := ticks()
    
    fun pop-timeout()
      match stack
        Cons(frame, rest) ->
          current-timeout := frame.original-timeout
          start-tick := ticks()
          stack := rest
        Nil -> ()
  
  val did-timeout = current-timeout >= 0 && (ticks() - start-tick) > current-timeout
  (result, !did-timeout)

// ═══════════════════════════════════════════════════════════════════════════
// Divergence Handler
// ═══════════════════════════════════════════════════════════════════════════

fun handle-divergence(max-steps: int, action: () -> <divergence> a): (a, bool)
  var divergent-ops : list<string> := []
  var step-count := 0
  var terminated := False
  
  val result = handle action
    fun mark-divergent(name)
      divergent-ops := Cons(name, divergent-ops)
    
    fun check-termination-bound()
      step-count := step-count + 1
      if step-count > max-steps then
        terminated := True
        False
      else
        True
    
    fun get-divergence-depth()
      divergent-ops.length
    
    fun assert-terminates(max)
      step-count <= max
  
  (result, !terminated)

// ═══════════════════════════════════════════════════════════════════════════
// Timed execution wrapper
// ═══════════════════════════════════════════════════════════════════════════

fun with-timeout(ms: int, action: () -> a): maybe<a>
  val (result, completed) = handle-timeout(ms, action)
  if completed then Just(result) else Nothing

// ═══════════════════════════════════════════════════════════════════════════
// Timed execution with default value
// ═══════════════════════════════════════════════════════════════════════════

fun with-timeout-or(default: a, ms: int, action: () -> a): a
  val (result, completed) = handle-timeout(ms, action)
  if completed then result else default

// ═══════════════════════════════════════════════════════════════════════════
// Race between two operations (first to complete wins)
// ═══════════════════════════════════════════════════════════════════════════

fun race(operation1: () -> a, operation2: () -> a, timeout-ms: int): maybe<a>
  // Simplified - would actually run both and take first result
  with-timeout(timeout-ms, operation1)

// ═══════════════════════════════════════════════════════════════════════════
// Deadline-based timeout (absolute deadline rather than relative)
// ═══════════════════════════════════════════════════════════════════════════

struct deadline
  target-tick: int

fun make-deadline(ms-from-now: int): deadline
  deadline(ticks() + ms-from-now)

fun is-deadline-passed(d: deadline): bool
  ticks() > d.target-tick

fun time-until-deadline(d: deadline): int
  max(0, d.target-tick - ticks())

// ═══════════════════════════════════════════════════════════════════════════
// Composed timeout with divergence checking
// ═══════════════════════════════════════════════════════════════════════════

fun with-bounded-execution(time-ms: int, steps: int, action: () -> a): (maybe<a>, string)
  // First check time bound
  val (time-result, time-ok) = handle-timeout(time-ms, action)
  
  if !time-ok then
    (Nothing, "TIMEOUT_EXCEEDED")
  else
    // Then check divergence bound
    val (div-result, div-ok) = handle-divergence(steps, fn() time-result)
    
    if !div-ok then
      (Nothing, "DIVERGENCE_DETECTED")
    else
      (Just(div-result), "SUCCESS")

// ═══════════════════════════════════════════════════════════════════════════
// Timeout-aware combinators
// ═══════════════════════════════════════════════════════════════════════════

fun timeout-map(timeout-ms: int, f: a -> b, ma: maybe<a>): maybe<b>
  match ma
    Just(a) -> 
      with-timeout(timeout-ms, fn() f(a))
    Nothing -> Nothing

fun timeout-bind(timeout-ms: int, ma: maybe<a>, f: a -> maybe<b>): maybe<b>
  match ma
    Just(a) -> 
      with-timeout(timeout-ms, fn() f(a)).flatten
    Nothing -> Nothing
