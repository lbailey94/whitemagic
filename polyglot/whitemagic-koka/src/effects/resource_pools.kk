// resource_pools - Resource pool management effects (S022 Phase 2 VC3)
// Ported from pool management patterns - typed resource effects

module resource_pools

import std/num/float64

// ═══════════════════════════════════════════════════════════════════════════
// Resource Pool Effect Definition
// ═══════════════════════════════════════════════════════════════════════════

effect resource-pool
  // Core pool operations
  fun acquire(pool-name: string, amount: int): bool
  fun release(pool-name: string, amount: int): ()
  fun get-available(pool-name: string): int
  fun get-capacity(pool-name: string): int
  fun resize-pool(pool-name: string, new-capacity: int): bool
  
  // Pool lifecycle
  fun create-pool(name: string, capacity: int, strategy: string): ()
  fun destroy-pool(name: string): ()
  fun list-pools(): list<string>
  
  // Resource tracking
  fun get-allocated(pool-name: string): int
  fun get-waiters(pool-name: string): int
  fun get-utilization(pool-name: string): float64

// ═══════════════════════════════════════════════════════════════════════════
// Pool Types and Strategies
// ═══════════════════════════════════════════════════════════════════════════

type pool-strategy
  Strict      // Never exceed capacity
  Elastic     // Allow temporary overflow
  Priority    // Priority-based allocation
  Fair        // Fair queuing

struct pool-config
  name: string
  capacity: int
  strategy: pool-strategy
  timeout-ms: int

struct pool-state
  allocated: int
  waiters: list<string>  // requester ids waiting
  total-acquisitions: int
  total-releases: int

// ═══════════════════════════════════════════════════════════════════════════
// Pool Handler Implementation
// ═══════════════════════════════════════════════════════════════════════════

fun handle-resource-pools(action: () -> <resource-pool> a): a
  var pools : list<(string, pool-config, pool-state)> := []
  
  handle action
    fun create-pool(name, capacity, strategy-str)
      val strategy = match strategy-str
        "elastic" -> Elastic
        "priority" -> Priority
        "fair" -> Fair
        _ -> Strict
      
      val config = pool-config(name, capacity, strategy, 5000)
      val state = pool-state(0, [], 0, 0)
      pools := Cons((name, config, state), pools)
    
    fun destroy-pool(name)
      pools := pools.filter(fn(p) p.fst != name)
    
    fun list-pools()
      pools.map(fn(p) p.fst)
    
    fun acquire(name, amount)
      match pools.find(fn(p) p.fst == name)
        Just((_, config, state)) ->
          val available = config.capacity - state.allocated
          if amount <= available then
            // Success - allocate
            val new-state = pool-state(
              state.allocated + amount,
              state.waiters,
              state.total-acquisitions + 1,
              state.total-releases
            )
            pools := Cons((name, config, new-state), 
                         pools.filter(fn(p) p.fst != name))
            True
          else
            // Check strategy
            match config.strategy
              Elastic ->
                // Allow allocation beyond capacity
                val new-state = pool-state(
                  state.allocated + amount,
                  state.waiters,
                  state.total-acquisitions + 1,
                  state.total-releases
                )
                pools := Cons((name, config, new-state), 
                             pools.filter(fn(p) p.fst != name))
                True
              _ -> False  // Strict, Priority, Fair - block
        Nothing -> False
    
    fun release(name, amount)
      match pools.find(fn(p) p.fst == name)
        Just((_, config, state)) ->
          val new-allocated = max(0, state.allocated - amount)
          val new-state = pool-state(
            new-allocated,
            state.waiters,
            state.total-acquisitions,
            state.total-releases + 1
          )
          pools := Cons((name, config, new-state), 
                       pools.filter(fn(p) p.fst != name))
        Nothing -> ()
    
    fun get-available(name)
      match pools.find(fn(p) p.fst == name)
        Just((_, config, state)) -> 
          max(0, config.capacity - state.allocated)
        Nothing -> 0
    
    fun get-capacity(name)
      match pools.find(fn(p) p.fst == name)
        Just((_, config, _)) -> config.capacity
        Nothing -> 0
    
    fun resize-pool(name, new-capacity)
      match pools.find(fn(p) p.fst == name)
        Just((_, config, state)) ->
          val new-config = pool-config(name, new-capacity, config.strategy, config.timeout-ms)
          pools := Cons((name, new-config, state), 
                       pools.filter(fn(p) p.fst != name))
          new-capacity >= state.allocated
        Nothing -> False
    
    fun get-allocated(name)
      match pools.find(fn(p) p.fst == name)
        Just((_, _, state)) -> state.allocated
        Nothing -> 0
    
    fun get-waiters(name)
      match pools.find(fn(p) p.fst == name)
        Just((_, _, state)) -> state.waiters.length
        Nothing -> 0
    
    fun get-utilization(name)
      match pools.find(fn(p) p.fst == name)
        Just((_, config, state)) ->
          if config.capacity == 0 then 0.0
          else float64(state.allocated) / float64(config.capacity)
        Nothing -> 0.0

// ═══════════════════════════════════════════════════════════════════════════
// Common Pool Types
// ═══════════════════════════════════════════════════════════════════════════

fun init-standard-pools(): <resource-pool> ()
  create-pool("memory", 10000, "strict")
  create-pool("connections", 100, "elastic")
  create-pool("threads", 50, "priority")
  create-pool("file-handles", 1000, "fair")

// ═══════════════════════════════════════════════════════════════════════════
// Resource Guard Pattern (automatically release after use)
// ═══════════════════════════════════════════════════════════════════════════

fun with-resource(pool: string, amount: int, action: () -> a): <resource-pool> a
  if !acquire(pool, amount) then
    throw("ResourceAcquisitionFailed: " ++ pool)
  
  val result = action()
  release(pool, amount)
  result

// ═══════════════════════════════════════════════════════════════════════════
// Pool monitoring and health
// ═══════════════════════════════════════════════════════════════════════════

struct pool-health
  name: string
  utilization: float64
  available: int
  waiters: int
  healthy: bool

fun check-pool-health(name: string): <resource-pool> pool-health
  pool-health(
    name,
    get-utilization(name),
    get-available(name),
    get-waiters(name),
    get-utilization(name) < 0.9
  )

fun get-all-pool-health(): <resource-pool> list<pool-health>
  list-pools().map(fn(p) check-pool-health(p))

// ═══════════════════════════════════════════════════════════════════════════
// Resource reservation for batch operations
// ═══════════════════════════════════════════════════════════════════════════

fun reserve-for-batch(pool: string, total-amount: int, batch-size: int): 
  <resource-pool> list<() -> bool>
  
  // Create reserver functions for each batch
  val batches = total-amount / batch-size
  list(1, batches).map(fn(_)
    fn() acquire(pool, batch-size)
  )
