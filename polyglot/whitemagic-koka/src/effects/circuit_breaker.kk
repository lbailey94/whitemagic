// circuit_breaker - Circuit breaker pattern effects (S022 Phase 3 VC1)
// Ported from circuit_breaker.py - fault tolerance with algebraic effects

module circuit_breaker

import std/num/float64

// ═══════════════════════════════════════════════════════════════════════════
// Circuit Breaker Effect Definition
// ═══════════════════════════════════════════════════════════════════════════

effect circuit
  // Core circuit operations
  fun check-circuit(name: string): string  // returns state: closed, open, half-open
  fun record-success(name: string): ()
  fun record-failure(name: string): ()
  fun reset-circuit(name: string): ()
  
  // Circuit configuration
  fun configure-circuit(
    name: string,
    failure-threshold: int,
    recovery-timeout: int,
    half-open-max-calls: int
  ): ()
  
  // Bulkhead isolation
  fun enter-bulkhead(name: string): bool
  fun exit-bulkhead(name: string): ()
  fun get-bulkhead-occupancy(name: string): int

// ═══════════════════════════════════════════════════════════════════════════
// Circuit Breaker Types
// ═══════════════════════════════════════════════════════════════════════════

type circuit-state
  Closed         // Normal operation
  Open           // Failing, rejecting calls
  HalfOpen       // Testing if recovered

struct circuit-config
  name: string
  failure-threshold: int     // failures before opening
  recovery-timeout: int      // ms before attempting half-open
  half-open-max-calls: int   // successful calls to close
  
struct circuit-status
  state: circuit-state
  failure-count: int
  success-count: int
  last-failure-time: int
  total-calls: int
  rejected-calls: int

// ═══════════════════════════════════════════════════════════════════════════
// Circuit Breaker Handler
// ═══════════════════════════════════════════════════════════════════════════

fun handle-circuit-breaker(action: () -> <circuit> a): a
  var circuits : list<(string, circuit-config, circuit-status)> := []
  var bulkheads : list<(string, int, int)> := []  // name, max, current
  
  handle action
    fun check-circuit(name)
      match circuits.find(fn(c) c.fst == name)
        Just((_, config, status)) ->
          match status.state
            Closed ->
              if status.failure-count >= config.failure-threshold then
                // Transition to Open
                "open"
              else
                "closed"
            Open ->
              // Check recovery timeout
              val elapsed = ticks() - status.last-failure-time
              if elapsed > config.recovery-timeout then
                "half-open"
              else
                "open"
            HalfOpen ->
              if status.success-count >= config.half-open-max-calls then
                "closed"
              else
                "half-open"
        Nothing -> "closed"  // Default if not configured
    
    fun record-success(name)
      match circuits.find(fn(c) c.fst == name)
        Just((config, _, status)) ->
          val new-status = match status.state
            Closed ->
              circuit-status(
                Closed, 0, 0, status.last-failure-time,
                status.total-calls + 1, status.rejected-calls
              )
            HalfOpen ->
              circuit-status(
                HalfOpen, 0, status.success-count + 1, 
                status.last-failure-time,
                status.total-calls + 1, status.rejected-calls
              )
            Open -> status
          circuits := Cons((config, name, new-status), 
                            circuits.filter(fn(c) c.fst != name))
        Nothing -> ()
    
    fun record-failure(name)
      match circuits.find(fn(c) c.fst == name)
        Just((config, _, status)) ->
          val new-status = match status.state
            Closed ->
              val new-failures = status.failure-count + 1
              val new-state = if new-failures >= config.failure-threshold 
                             then Open else Closed
              circuit-status(
                new-state, new-failures, 0, ticks(),
                status.total-calls + 1, status.rejected-calls
              )
            HalfOpen ->
              // Back to open on failure in half-open
              circuit-status(
                Open, status.failure-count + 1, 0, ticks(),
                status.total-calls + 1, status.rejected-calls
              )
            Open -> status
          circuits := Cons((config, name, new-status), 
                            circuits.filter(fn(c) c.fst != name))
        Nothing -> ()
    
    fun reset-circuit(name)
      match circuits.find(fn(c) c.fst == name)
        Just((config, _, _)) ->
          val fresh = circuit-status(Closed, 0, 0, 0, 0, 0)
          circuits := Cons((config, name, fresh), 
                            circuits.filter(fn(c) c.fst != name))
        Nothing -> ()
    
    fun configure-circuit(name, threshold, timeout, half-max)
      val config = circuit-config(name, threshold, timeout, half-max)
      val status = circuit-status(Closed, 0, 0, 0, 0, 0)
      circuits := Cons((name, config, status), 
                        circuits.filter(fn(c) c.fst != name))
    
    fun enter-bulkhead(name)
      match bulkheads.find(fn(b) b.fst == name)
        Just((_, max, current)) ->
          if current < max then
            bulkheads := Cons((name, max, current + 1), 
                             bulkheads.filter(fn(b) b.fst != name))
            True
          else
            False
        Nothing ->
          // Create default bulkhead
          bulkheads := Cons((name, 10, 1), bulkheads)
          True
    
    fun exit-bulkhead(name)
      match bulkheads.find(fn(b) b.fst == name)
        Just((_, max, current)) ->
          val new-current = max(0, current - 1)
          bulkheads := Cons((name, max, new-current), 
                           bulkheads.filter(fn(b) b.fst != name))
        Nothing -> ()
    
    fun get-bulkhead-occupancy(name)
      match bulkheads.find(fn(b) b.fst == name)
        Just((_, _, current)) -> current
        Nothing -> 0

// ═══════════════════════════════════════════════════════════════════════════
// Protected execution with circuit breaker
// ═══════════════════════════════════════════════════════════════════════════

fun with-circuit-protection(name: string, action: () -> a): <circuit> maybe<a>
  val state = check-circuit(name)
  
  if state == "open" then
    Nothing  // Circuit open - reject call
  else
    try
      val result = action()
      record-success(name)
      Just(result)
    catch
      record-failure(name)
      Nothing

// ═══════════════════════════════════════════════════════════════════════════
// Protected execution with bulkhead isolation
// ═══════════════════════════════════════════════════════════════════════════

fun with-bulkhead-isolation(name: string, action: () -> a): <circuit> maybe<a>
  if !enter-bulkhead(name) then
    Nothing  // Bulkhead full - reject
  
  try
    val result = action()
    exit-bulkhead(name)
    Just(result)
  catch
    exit-bulkhead(name)
    throw

// ═══════════════════════════════════════════════════════════════════════════
// Combined circuit + bulkhead protection
// ═══════════════════════════════════════════════════════════════════════════

fun with-full-protection(name: string, action: () -> a): <circuit> maybe<a>
  // First check circuit
  val state = check-circuit(name)
  if state == "open" then
    Nothing
  
  // Then check bulkhead
  if !enter-bulkhead(name) then
    Nothing
  
  try
    val result = action()
    record-success(name)
    exit-bulkhead(name)
    Just(result)
  catch
    record-failure(name)
    exit-bulkhead(name)
    Nothing

// ═══════════════════════════════════════════════════════════════════════════
// Standard circuit configurations
// ═══════════════════════════════════════════════════════════════════════════

fun init-strict-circuit(name: string): <circuit> ()
  configure-circuit(name, 3, 30000, 2)  // 3 failures, 30s timeout, 2 test calls

fun init-lenient-circuit(name: string): <circuit> ()
  configure-circuit(name, 10, 60000, 5)  // 10 failures, 60s timeout, 5 test calls

fun init-fast-circuit(name: string): <circuit> ()
  configure-circuit(name, 5, 10000, 3)  // 5 failures, 10s timeout, 3 test calls
