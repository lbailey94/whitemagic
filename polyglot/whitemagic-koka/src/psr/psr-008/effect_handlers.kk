// effect_handlers - Koka Migration (PSR-008)
// Unified effect handler system for type-safe coordination
// Composes circuit breaker, backpressure, transactions, and coordination effects

module effect_handlers

import circuit_breaker
import backpressure
import transactions
import coordination

// ═══════════════════════════════════════════════════════════════════════════
// Unified Effect Definition
// ═══════════════════════════════════════════════════════════════════════════

effect unified-effects
  // Circuit breaker operations
  fun check-circuit(name: string): string
  fun record-success(name: string): ()
  fun record-failure(name: string): ()
  
  // Backpressure operations
  fun request-admission(priority: int): bool
  fun release-admission(): ()
  
  // Transaction operations
  fun begin-tx(): string
  fun commit-tx(tx-id: string): bool
  fun rollback-tx(tx-id: string): bool
  
  // Coordination operations
  fun acquire-lock(name: string): bool
  fun release-lock(name: string): ()

// ═══════════════════════════════════════════════════════════════════════════
// Effect Handler State
// ═══════════════════════════════════════════════════════════════════════════

struct handler-state
  circuit-config: circuit_breaker/circuit-config
  backpressure-config: backpressure/backpressure-config
  coordination-context: coordination/coordination-context

// ═══════════════════════════════════════════════════════════════════════════
// Unified Effect Handler
// ═══════════════════════════════════════════════════════════════════════════

fun handle-unified-effects(state: handler-state, action: () -> <unified-effects> a): a
  // Compose all effect handlers
  val circuit-action = handle-circuit-breaker(action
    fun check-circuit(name) = circuit_breaker/check-circuit(name)
    fun record-success(name) = circuit_breaker/record-success(name)
    fun record-failure(name) = circuit_breaker/record-failure(name)
    fun configure-circuit(name, threshold, timeout, half-max) = 
      circuit_breaker/configure-circuit(name, threshold, timeout, half-max)
    fun enter-bulkhead(name) = circuit_breaker/enter-bulkhead(name)
    fun exit-bulkhead(name) = circuit_breaker/exit-bulkhead(name)
    fun get-bulkhead-occupancy(name) = circuit_breaker/get-bulkhead-occupancy(name)
    
    fun request-admission(priority) = 
      handle-backpressure(state.backpressure-config, 
        backpressure/request-admission(priority)
      )
    fun release-admission() = backpressure/release-admission()
    fun get-queue-depth() = backpressure/get-queue-depth()
    fun get-current-load() = backpressure/get-current-load()
    fun should-shed-load() = backpressure/should-shed-load()
    fun get-shedding-strategy() = backpressure/get-shedding-strategy()
    fun set-shedding-threshold(t) = backpressure/set-shedding-threshold(t)
    fun get-request-rate() = backpressure/get-request-rate()
    fun set-rate-limit(rps) = backpressure/set-rate-limit(rps)
    fun wait-for-capacity() = backpressure/wait-for-capacity()
    
    fun begin-tx() = transactions/begin-tx()
    fun commit-tx(id) = transactions/commit-tx(id)
    fun rollback-tx(id) = transactions/rollback-tx(id)
    fun get-tx-status(id) = transactions/get-tx-status(id)
    fun create-savepoint(id) = transactions/create-savepoint(id)
    fun rollback-to-savepoint(id, sp) = transactions/rollback-to-savepoint(id, sp)
    fun is-in-tx() = transactions/is-in-tx()
    fun get-current-tx() = transactions/get-current-tx()
    fun set-tx-isolation(level) = transactions/set-tx-isolation(level)
    fun prepare-tx(id) = transactions/prepare-tx(id)
    fun confirm-tx(id) = transactions/confirm-tx(id)
    
    fun acquire-lock(name) = 
      handle-coordination(state.coordination-context,
        coordination/acquire-lock(name)
      )
    fun release-lock(name) = coordination/release-lock(name)
    fun try-acquire-lock(name, timeout) = coordination/try-acquire-lock(name, timeout)
    fun await-barrier(id, participants) = coordination/await-barrier(id, participants)
    fun signal-barrier(id) = coordination/signal-barrier(id)
    fun propose-leader(node-id) = coordination/propose-leader(node-id)
    fun get-current-leader() = coordination/get-current-leader()
    fun resign-leadership() = coordination/resign-leadership()
    fun get-shared-state(key) = coordination/get-shared-state(key)
    fun set-shared-state(key, value) = coordination/set-shared-state(key, value)
    fun cas-state(key, expected, new) = coordination/cas-state(key, expected, new)
    fun get-coordinator-id() = coordination/get-coordinator-id()
    fun get-participant-count() = coordination/get-participant-count()
  )
  
  circuit-action

// ═══════════════════════════════════════════════════════════════════════════
// Initialization Helpers
// ═══════════════════════════════════════════════════════════════════════════

fun init-default-state(coordinator-id: string): handler-state
  val circuit-config = circuit_breaker/circuit-config("default", 5, 30000, 3)
  val bp-config = backpressure/backpressure-config(100, 1000, 1000.0, 0.9, backpressure/DropNewest)
  val coord-context = coordination/coordination-context(
    coordinator-id, [], [], coordination/NoLeader, [], 1
  )
  handler-state(circuit-config, bp-config, coord-context)

fun init-strict-state(coordinator-id: string): handler-state
  val circuit-config = circuit_breaker/circuit-config("strict", 3, 10000, 2)
  val bp-config = backpressure/backpressure-config(10, 100, 100.0, 0.8, backpressure/RejectAll)
  val coord-context = coordination/coordination-context(
    coordinator-id, [], [], coordination/NoLeader, [], 1
  )
  handler-state(circuit-config, bp-config, coord-context)

// ═══════════════════════════════════════════════════════════════════════════
// High-Level Composed Operations
// ═══════════════════════════════════════════════════════════════════════════

fun safe-operation(name: string, action: () -> a): <unified-effects> maybe<a>
  // Check circuit
  val state = check-circuit(name)
  if state == "open" then Nothing
  else
    // Request admission
    if !request-admission(1) then Nothing
    else
      try
        // Begin transaction
        val tx-id = begin-tx()
        
        // Acquire lock
        if !acquire-lock(name ++ "_lock") then
          rollback-tx(tx-id)
          release-admission()
          Nothing
        else
          // Execute action
          val result = action()
          
          // Record success
          record-success(name)
          
          // Commit transaction
          commit-tx(tx-id)
          
          // Release lock
          release-lock(name ++ "_lock")
          
          // Release admission
          release-admission()
          
          Just(result)
      catch
        record-failure(name)
        rollback-tx(begin-tx())
        release-lock(name ++ "_lock")
        release-admission()
        Nothing
