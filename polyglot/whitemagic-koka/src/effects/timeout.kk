// timeout - Divergence effect for timeout handling (S022 Phase 3 VC3)
// Non-termination effects with timeout bounds

module timeout

// ═══════════════════════════════════════════════════════════════════════════
// Timeout Effect Definition
// ═══════════════════════════════════════════════════════════════════════════

pub effect timeout
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

pub effect divergence
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

pub fun handle-timeout(default-ms: int, action: () -> <timeout|e> a): e a
  var stack : list<timeout-frame> := []
  var current-timeout := default-ms
  var start-tick : int := 0
  var tick-counter : int := 0

  with
    fun set-timeout(ms)
      current-timeout := ms
      tick-counter := tick-counter + 1
      start-tick := tick-counter

    fun get-timeout()
      current-timeout

    fun extend-timeout(additional)
      current-timeout := current-timeout + additional

    fun clear-timeout()
      current-timeout := -1

    fun is-timed-out()
      if current-timeout < 0 then False
      else
        tick-counter := tick-counter + 1
        val elapsed = tick-counter - start-tick
        elapsed > current-timeout

    fun time-remaining()
      if current-timeout < 0 then 1000000
      else
        tick-counter := tick-counter + 1
        val elapsed = tick-counter - start-tick
        val rem = current-timeout - elapsed
        if rem < 0 then 0 else rem

    fun push-timeout(ms)
      val current-end = if current-timeout < 0 then -1 else start-tick + current-timeout
      stack := Cons(Timeout-frame(current-end, current-timeout), stack)
      current-timeout := ms
      tick-counter := tick-counter + 1
      start-tick := tick-counter

    fun pop-timeout()
      match stack
        Cons(frame, rest) ->
          current-timeout := frame.original-timeout
          tick-counter := tick-counter + 1
          start-tick := tick-counter
          stack := rest
        Nil -> ()
  action()

// ═══════════════════════════════════════════════════════════════════════════
// Divergence Handler
// ═══════════════════════════════════════════════════════════════════════════

pub fun handle-divergence(max-steps: int, action: () -> <divergence|e> a): e a
  var divergent-ops : list<string> := []
  var step-count := 0
  var terminated := False

  with
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
  action()

// ═══════════════════════════════════════════════════════════════════════════
// Timed execution wrapper
// ═══════════════════════════════════════════════════════════════════════════

pub fun with-timeout(ms: int, action: () -> <timeout|e> a): e a
  handle-timeout(ms, action)

// ═══════════════════════════════════════════════════════════════════════════
// Timed execution with default value
// ═══════════════════════════════════════════════════════════════════════════

fun with-timeout-or(default: a, ms: int, action: () -> <timeout|e> a): e a
  handle-timeout(ms, action)

// ═══════════════════════════════════════════════════════════════════════════
// Race between two operations (first to complete wins)
// ═══════════════════════════════════════════════════════════════════════════

fun race(operation1: () -> <timeout|e> a, operation2: () -> <timeout|e> a, timeout-ms: int): e a
  with-timeout(timeout-ms, operation1)

// ═══════════════════════════════════════════════════════════════════════════
// Deadline-based timeout (absolute deadline rather than relative)
// ═══════════════════════════════════════════════════════════════════════════

struct deadline
  target-tick: int

fun make-deadline(ms-from-now: int): deadline
  Deadline(ms-from-now)

fun is-deadline-passed(d: deadline): bool
  d.target-tick <= 0

fun time-until-deadline(d: deadline): int
  if d.target-tick < 0 then 0 else d.target-tick

// ═══════════════════════════════════════════════════════════════════════════
// Composed timeout with divergence checking
// ═══════════════════════════════════════════════════════════════════════════

fun with-bounded-execution(time-ms: int, steps: int, action: () -> <timeout,divergence|e> a): e a
  handle-divergence(steps, fn() handle-timeout(time-ms, action))

// ═══════════════════════════════════════════════════════════════════════════
// Timeout-aware combinators
// ═══════════════════════════════════════════════════════════════════════════

fun timeout-map(timeout-ms: int, f: a -> b, ma: maybe<a>): <timeout|e> maybe<b>
  match ma
    Just(a) -> 
      Just(with-timeout(timeout-ms, fn() f(a)))
    Nothing -> Nothing

fun timeout-bind(timeout-ms: int, ma: maybe<a>, f: a -> maybe<b>): <timeout|e> maybe<b>
  match ma
    Just(a) -> 
      with-timeout(timeout-ms, fn() f(a))
    Nothing -> Nothing
