// backpressure - Flow control effects (S022 Phase 3 VC4)
// Rate limiting and load shedding with algebraic effects

module backpressure

import std/num/float64

// ═══════════════════════════════════════════════════════════════════════════
// Backpressure Effect Definition
// ═══════════════════════════════════════════════════════════════════════════

pub effect backpressure
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

pub fun handle-backpressure(config: backpressure-config, action: () -> <backpressure|e> a): e a
  var state := Backpressure-state(0, 0, 0, 0, 0, 0.0, 0)
  var tick-counter : int := 0
  
  with
    fun request-admission(priority)
      val current-load = float64(state.current-concurrent) / float64(config.max-concurrent)
      
      // Check if we should shed
      if current-load > config.shed-threshold then
        match config.strategy
          RejectAll ->
            state := Backpressure-state(
              state.current-concurrent, state.queued,
              state.admitted, state.rejected + 1, state.shedded,
              state.current-rps, state.last-reset
            )
            False
          DropNewest ->
            // Admit but queue depth limits apply
            if state.queued < config.max-queue-depth then
              state := Backpressure-state(
                state.current-concurrent + 1, state.queued + 1,
                state.admitted + 1, state.rejected, state.shedded,
                state.current-rps, state.last-reset
              )
              True
            else
              state := Backpressure-state(
                state.current-concurrent, state.queued,
                state.admitted, state.rejected + 1, state.shedded + 1,
                state.current-rps, state.last-reset
              )
              False
          _ ->
            // Other strategies
            if state.current-concurrent < config.max-concurrent then
              state := Backpressure-state(
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
          state := Backpressure-state(
            state.current-concurrent + 1, state.queued,
            state.admitted + 1, state.rejected, state.shedded,
            state.current-rps, state.last-reset
          )
          True
        else if state.queued < config.max-queue-depth then
          // Queue it
          state := Backpressure-state(
            state.current-concurrent, state.queued + 1,
            state.admitted + 1, state.rejected, state.shedded,
            state.current-rps, state.last-reset
          )
          True
        else
          state := Backpressure-state(
            state.current-concurrent, state.queued,
            state.admitted, state.rejected + 1, state.shedded,
            state.current-rps, state.last-reset
          )
          False
    
    fun release-admission()
      val new-concurrent = if state.current-concurrent - 1 < 0 then 0 else state.current-concurrent - 1
      state := Backpressure-state(
        new-concurrent,
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
      val load = if config.max-concurrent == 0 then 0.0
                 else float64(state.current-concurrent) / float64(config.max-concurrent)
      load > config.shed-threshold
    
    fun get-shedding-strategy()
      match config.strategy
        DropNewest -> "drop_newest"
        DropOldest -> "drop_oldest"
        DropRandom -> "drop_random"
        RejectAll -> "reject_all"
        Degrade -> "degrade"
    
    fun set-shedding-threshold(t)
      ()
    
    fun get-request-rate()
      state.current-rps
    
    fun set-rate-limit(rps)
      ()
    
    fun wait-for-capacity()
      // No-op in synchronous implementation — real version would check load
      ()
  action()

// ═══════════════════════════════════════════════════════════════════════════
// Admission-controlled execution
// ═══════════════════════════════════════════════════════════════════════════

fun with-admission-control(priority: int, action: () -> <backpressure,exn|e> a): <backpressure|e> maybe<a>
  if !request-admission(priority) then
    Nothing
  else
    try(fn() {
      val result = action()
      release-admission()
      Just(result)
    }, fn(_exn) {
      release-admission()
      Nothing
    })

// ═══════════════════════════════════════════════════════════════════════════
// Bulkhead pattern (limit concurrent by category)
// ═══════════════════════════════════════════════════════════════════════════

struct bulkhead
  name: string
  max-concurrent: int
  current: int

fun handle-bulkhead(bulkheads: list<bulkhead>, action: () -> <backpressure|e> a): <backpressure|e> a
  // Would track per-bulkhead admission
  action()

// ═══════════════════════════════════════════════════════════════════════════
// Rate limiting with token bucket (simplified)
// ═══════════════════════════════════════════════════════════════════════════

pub effect token-bucket
  fun consume-tokens(n: int): bool
  fun get-available-tokens(): int
  fun refill-rate(): int  // tokens per second

pub fun handle-token-bucket(capacity: int, refill: int, action: () -> <token-bucket|e> a): e a
  var tokens := capacity
  var tick-counter : int := 0
  
  with
    fun consume-tokens(n)
      tick-counter := tick-counter + 1
      val elapsed = tick-counter - tick-counter  // no real time; always 0
      val new-tokens = if tokens + (elapsed * refill / 1000) > capacity then capacity else tokens + (elapsed * refill / 1000)
      
      if new-tokens >= n then
        tokens := new-tokens - n
        True
      else
        tokens := new-tokens
        False
    
    fun get-available-tokens()
      tokens
    
    fun refill-rate()
      refill
  action()

// ═══════════════════════════════════════════════════════════════════════════
// Combined backpressure strategies
// ═══════════════════════════════════════════════════════════════════════════

pub fun init-strict-backpressure(): backpressure-config
  Backpressure-config(10, 100, 100.0, 0.8, RejectAll)

pub fun init-lenient-backpressure(): backpressure-config
  Backpressure-config(100, 1000, 1000.0, 0.95, DropNewest)

pub fun init-adaptive-backpressure(): backpressure-config
  Backpressure-config(50, 500, 500.0, 0.9, Degrade)

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
  
  System-health(load, queue, 0.0, healthy)
