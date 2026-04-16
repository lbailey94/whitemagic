// backpressure - Flow control effects (S022 Phase 3 VC4)
// Rate limiting and load shedding with algebraic effects

module backpressure

import std/num/float64

// ═══════════════════════════════════════════════════════════════════════════
// Backpressure Effect Definition
// ═══════════════════════════════════════════════════════════════════════════

effect backpressure
  // Admission control
  fun request-admission(priority: int): bool  // returns true if admitted
  fun release-admission(): ()
  fun get-queue-depth(): int
  fun get-current-load(): float64
  
  // Load shedding
  fun should-shed-load(): bool
  fun get-shedding-strategy(): string
  fun set-shedding-threshold(threshold: float64): ()
  
  // Flow rate control
  fun get-request-rate(): float64  // requests per second
  fun set-rate-limit(rps: float64): ()
  fun wait-for-capacity(): ()  // block until capacity available

// ═══════════════════════════════════════════════════════════════════════════
// Backpressure Types
// ═══════════════════════════════════════════════════════════════════════════

type shedding-strategy
  DropNewest      // Drop newest requests first
  DropOldest      // Drop oldest requests first
  DropRandom      // Random drop
  RejectAll       // Reject everything when overloaded
  Degrade         // Reduce quality but accept

struct backpressure-config
  max-concurrent: int
  max-queue-depth: int
  target-rps: float64
  shed-threshold: float64  // load at which to start shedding
  strategy: shedding-strategy

struct backpressure-state
  current-concurrent: int
  queued: int
  admitted: int
  rejected: int
  shedded: int
  current-rps: float64
  last-reset: int

// ═══════════════════════════════════════════════════════════════════════════
// Backpressure Handler
// ═══════════════════════════════════════════════════════════════════════════

fun handle-backpressure(config: backpressure-config, action: () -> <backpressure> a): a
  var state := backpressure-state(0, 0, 0, 0, 0, 0.0, ticks())
  
  handle action
    fun request-admission(priority)
      val current-load = float64(state.current-concurrent) / float64(config.max-concurrent)
      
      // Check if we should shed
      if current-load > config.shed-threshold then
        match config.strategy
          RejectAll ->
            state := backpressure-state(
              state.current-concurrent, state.queued,
              state.admitted, state.rejected + 1, state.shedded,
              state.current-rps, state.last-reset
            )
            False
          DropNewest ->
            // Admit but queue depth limits apply
            if state.queued < config.max-queue-depth then
              state := backpressure-state(
                state.current-concurrent + 1, state.queued + 1,
                state.admitted + 1, state.rejected, state.shedded,
                state.current-rps, state.last-reset
              )
              True
            else
              state := backpressure-state(
                state.current-concurrent, state.queued,
                state.admitted, state.rejected + 1, state.shedded + 1,
                state.current-rps, state.last-reset
              )
              False
          _ ->
            // Other strategies
            if state.current-concurrent < config.max-concurrent then
              state := backpressure-state(
                state.current-concurrent + 1, state.queued,
                state.admitted + 1, state.rejected, state.shedded,
                state.current-rps, state.last-reset
              )
              True
            else
              False
      else
        // Normal admission
        if state.current-concurrent < config.max-concurrent then
          state := backpressure-state(
            state.current-concurrent + 1, state.queued,
            state.admitted + 1, state.rejected, state.shedded,
            state.current-rps, state.last-reset
          )
          True
        else if state.queued < config.max-queue-depth then
          // Queue it
          state := backpressure-state(
            state.current-concurrent, state.queued + 1,
            state.admitted + 1, state.rejected, state.shedded,
            state.current-rps, state.last-reset
          )
          True
        else
          state := backpressure-state(
            state.current-concurrent, state.queued,
            state.admitted, state.rejected + 1, state.shedded,
            state.current-rps, state.last-reset
          )
          False
    
    fun release-admission()
      state := backpressure-state(
        max(0, state.current-concurrent - 1),
        state.queued,
        state.admitted, state.rejected, state.shedded,
        state.current-rps, state.last-reset
      )
    
    fun get-queue-depth()
      state.queued
    
    fun get-current-load()
      if config.max-concurrent == 0 then 0.0
      else float64(state.current-concurrent) / float64(config.max-concurrent)
    
    fun should-shed-load()
      get-current-load() > config.shed-threshold
    
    fun get-shedding-strategy()
      match config.strategy
        DropNewest -> "drop_newest"
        DropOldest -> "drop_oldest"
        DropRandom -> "drop_random"
        RejectAll -> "reject_all"
        Degrade -> "degrade"
    
    fun set-shedding-threshold(t)
      ()  // Would update config
    
    fun get-request-rate()
      state.current-rps
    
    fun set-rate-limit(rps)
      ()  // Would update config
    
    fun wait-for-capacity()
      // In real implementation, would block
      while get-current-load() >= 1.0 do
        ()  // Busy wait placeholder

// ═══════════════════════════════════════════════════════════════════════════
// Admission-controlled execution
// ═══════════════════════════════════════════════════════════════════════════

fun with-admission-control(priority: int, action: () -> a): <backpressure> maybe<a>
  if !request-admission(priority) then
    Nothing
  else
    try
      val result = action()
      release-admission()
      Just(result)
    catch
      release-admission()
      throw

// ═══════════════════════════════════════════════════════════════════════════
// Bulkhead pattern (limit concurrent by category)
// ═══════════════════════════════════════════════════════════════════════════

struct bulkhead
  name: string
  max-concurrent: int
  current: int

fun handle-bulkhead(bulkheads: list<bulkhead>, action: () -> <backpressure> a): a
  // Would track per-bulkhead admission
  action()

// ═══════════════════════════════════════════════════════════════════════════
// Rate limiting with token bucket (simplified)
// ═══════════════════════════════════════════════════════════════════════════

effect token-bucket
  fun consume-tokens(n: int): bool
  fun get-available-tokens(): int
  fun refill-rate(): int  // tokens per second

fun handle-token-bucket(capacity: int, refill: int, action: () -> <token-bucket> a): a
  var tokens := capacity
  var last-refill := ticks()
  
  handle action
    fun consume-tokens(n)
      // Refill based on time elapsed
      val now = ticks()
      val elapsed = now - last-refill
      val new-tokens = min(capacity, tokens + (elapsed * refill / 1000))
      
      if new-tokens >= n then
        tokens := new-tokens - n
        last-refill := now
        True
      else
        tokens := new-tokens
        last-refill := now
        False
    
    fun get-available-tokens()
      tokens
    
    fun refill-rate()
      refill

// ═══════════════════════════════════════════════════════════════════════════
// Combined backpressure strategies
// ═══════════════════════════════════════════════════════════════════════════

fun init-strict-backpressure(): backpressure-config
  backpressure-config(10, 100, 100.0, 0.8, RejectAll)

fun init-lenient-backpressure(): backpressure-config
  backpressure-config(100, 1000, 1000.0, 0.95, DropNewest)

fun init-adaptive-backpressure(): backpressure-config
  backpressure-config(50, 500, 500.0, 0.9, Degrade)

// ═══════════════════════════════════════════════════════════════════════════
// Health check integration
// ═══════════════════════════════════════════════════════════════════════════

struct system-health
  load: float64
  queue-depth: int
  admission-rate: float64
  healthy: bool

fun check-health(): <backpressure> system-health
  val load = get-current-load()
  val queue = get-queue-depth()
  val healthy = load < 0.9 && queue < 100
  
  system-health(load, queue, 0.0, healthy)
