// retry_logic - Resumable retry effects (S022 Phase 3 VC2)
// Exponential backoff with algebraic effects

module retry_logic

import std/num/float64

// ═══════════════════════════════════════════════════════════════════════════
// Retry Effect Definition
// ═══════════════════════════════════════════════════════════════════════════

effect retry
  // Core retry operations
  fun attempt(action-desc: string): int  // returns attempt number (1-indexed)
  fun should-retry(): bool
  fun get-attempt-count(): int
  fun get-max-attempts(): int
  
  // Backoff configuration
  fun get-backoff-delay(): int  // milliseconds
  fun set-backoff-strategy(strategy: string, base-delay: int, max-delay: int): ()
  
  // Circuit breaker integration
  fun record-retry-exhausted(): ()
  fun was-successful(): bool

// ═══════════════════════════════════════════════════════════════════════════
// Backoff Strategies
// ═══════════════════════════════════════════════════════════════════════════

type backoff-strategy
  Fixed        // Constant delay
  Linear       // Linear increase
  Exponential  // Exponential increase
  Decorrelated // Randomized exponential

struct retry-config
  max-attempts: int
  strategy: backoff-strategy
  base-delay-ms: int
  max-delay-ms: int
  jitter: bool

struct retry-state
  current-attempt: int
  last-delay: int
  success: bool
  exhausted: bool

// ═══════════════════════════════════════════════════════════════════════════
// Retry Handler
// ═══════════════════════════════════════════════════════════════════════════

fun handle-retry(max-attempts: int, action: () -> <retry> a): (a, int, bool)
  var config := retry-config(
    max-attempts, Exponential, 100, 30000, True
  )
  var state := retry-state(0, 0, False, False)
  
  val result = handle action
    fun attempt(desc)
      state := retry-state(
        state.current-attempt + 1,
        state.last-delay,
        state.success,
        state.exhausted
      )
      state.current-attempt
    
    fun should-retry()
      state.current-attempt < config.max-attempts && !state.success
    
    fun get-attempt-count()
      state.current-attempt
    
    fun get-max-attempts()
      config.max-attempts
    
    fun get-backoff-delay()
      val base = config.base-delay-ms
      val max-d = config.max-delay-ms
      
      val delay = match config.strategy
        Fixed -> base
        Linear -> min(base * state.current-attempt, max-d)
        Exponential -> 
          val exp = pow(2.0, float64(state.current-attempt - 1))
          min(int(float64(base) * exp), max-d)
        Decorrelated -> 
          // Random between base and exponential
          val exp = pow(2.0, float64(state.current-attempt - 1))
          val upper = min(int(float64(base) * exp), max-d)
          base + (upper - base) / 2  // Simplified - would use random
      
      state := retry-state(state.current-attempt, delay, state.success, state.exhausted)
      delay
    
    fun set-backoff-strategy(strat, base, max-d)
      val strategy = match strat
        "fixed" -> Fixed
        "linear" -> Linear
        "exponential" -> Exponential
        "decorrelated" -> Decorrelated
        _ -> Exponential
      config := retry-config(config.max-attempts, strategy, base, max-d, config.jitter)
    
    fun record-retry-exhausted()
      state := retry-state(
        state.current-attempt,
        state.last-delay,
        False,
        True
      )
    
    fun was-successful()
      state.success
  
  (result, state.current-attempt, state.success)

// ═══════════════════════════════════════════════════════════════════════════
// Retry execution with automatic retry
// ═══════════════════════════════════════════════════════════════════════════

fun with-retry(max-attempts: int, action: () -> a): (a, int, bool)
  var last-result : maybe<a> := Nothing
  var last-error : string := ""
  
  with handle-retry(max-attempts)
    var attempt-num := 0
    var success := False
    
    while attempt-num < max-attempts && !success do
      attempt-num := attempt-num + 1
      val _ = attempt("action")
      
      try
        val result = action()
        last-result := Just(result)
        success := True
        // Set success in retry state would happen here
      catch
        if attempt-num >= max-attempts then
          record-retry-exhausted()
        else
          val delay = get-backoff-delay()
          // Would sleep here in real implementation
          ()
    
    match last-result
      Just(r) -> (r, attempt-num, True)
      Nothing -> throw("RetryExhausted: " ++ last-error)

// ═══════════════════════════════════════════════════════════════════════════
// Resumable retry (can resume from last attempt)
// ═══════════════════════════════════════════════════════════════════════════

fun with-resumable-retry(
  max-attempts: int,
  action: (attempt: int) -> a
): (a, int, bool)
  var last-result : maybe<a> := Nothing
  var attempt-num := 0
  var success := False
  
  with handle-retry(max-attempts)
    while attempt-num < max-attempts && !success do
      attempt-num := attempt-num + 1
      val _ = attempt("resumable")
      
      try
        val result = action(attempt-num)
        last-result := Just(result)
        success := True
      catch
        if attempt-num < max-attempts then
          val _ = get-backoff-delay()
          ()  // Continue to next attempt
    
    match last-result
      Just(r) -> (r, attempt-num, True)
      Nothing -> throw("RetryExhausted")

// ═══════════════════════════════════════════════════════════════════════════
// Conditional retry (custom retry condition)
// ═══════════════════════════════════════════════════════════════════════════

fun with-conditional-retry(
  max-attempts: int,
  should-retry-on: string -> bool,
  action: () -> a
): (a, int, bool)
  with-retry(max-attempts, action)
  // Would check should-retry-on for each exception

// ═══════════════════════════════════════════════════════════════════════════
// Retry composition (retry multiple operations)
// ═══════════════════════════════════════════════════════════════════════════

fun retry-all(operations: list<() -> a>, max-per-op: int): list<(a, int, bool)>
  operations.map(fn(op) with-retry(max-per-op, op))

// ═══════════════════════════════════════════════════════════════════════════
// Retry with fallback (use fallback after retries exhausted)
// ═══════════════════════════════════════════════════════════════════════════

fun with-retry-or-fallback(
  max-attempts: int,
  action: () -> a,
  fallback: () -> a
): a
  val (result, _, success) = with-retry(max-attempts, action)
  if success then result else fallback()

// ═══════════════════════════════════════════════════════════════════════════
// Power function for exponential backoff
// ═══════════════════════════════════════════════════════════════════════════

fun pow(base: float64, exp: float64): float64
  if exp == 0.0 then 1.0
  else if exp == 1.0 then base
  else base * pow(base, exp - 1.0)
