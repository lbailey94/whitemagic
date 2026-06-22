// transactions - Transactional operation effects (S022 Phase 2 VC4)
// Atomic operation support with commit/rollback semantics

module transactions

// ═══════════════════════════════════════════════════════════════════════════
// Transaction Effect Definition
// ═══════════════════════════════════════════════════════════════════════════

effect transaction
  // Core transaction operations
  fun begin-tx(): string  // returns tx-id
  fun commit-tx(tx-id: string): bool
  fun rollback-tx(tx-id: string): bool
  fun get-tx-status(tx-id: string): string
  
  // Savepoints
  fun create-savepoint(tx-id: string): string
  fun rollback-to-savepoint(tx-id: string, savepoint: string): bool
  
  // Transaction state
  fun is-in-tx(): bool
  fun get-current-tx(): string
  fun set-tx-isolation(level: string): ()
  
  // Distributed transaction coordination
  fun prepare-tx(tx-id: string): bool  // 2-phase commit: prepare
  fun confirm-tx(tx-id: string): bool  // 2-phase commit: confirm

// ═══════════════════════════════════════════════════════════════════════════
// Transaction Types
// ═══════════════════════════════════════════════════════════════════════════

type tx-status
  Active
  Committed
  RolledBack
  Preparing
  Prepared
  Committing

struct tx-record
  id: string
  status: tx-status
  operations: list<string>
  savepoints: list<string>
  start-time: int

// ═══════════════════════════════════════════════════════════════════════════
// Transaction Handler
// ═══════════════════════════════════════════════════════════════════════════

fun handle-transactions(action: () -> <transaction> a): a
  var txs : list<tx-record> := []
  var current-tx : string := ""
  var next-id := 0
  
  handle action
    fun begin-tx()
      val id = "tx_" ++ next-id.show
      next-id := next-id + 1
      val tx = tx-record(id, Active, [], [], ticks())
      txs := Cons(tx, txs)
      current-tx := id
      id
    
    fun commit-tx(id)
      match txs.find(fn(t) t.id == id)
        Just(tx) ->
          if tx.status == Active then
            val new-tx = tx-record(
              tx.id, Committed, tx.operations, 
              tx.savepoints, tx.start-time
            )
            txs := Cons(new-tx, txs.filter(fn(t) t.id != id))
            if current-tx == id then current-tx := ""
            True
          else
            False
        Nothing -> False
    
    fun rollback-tx(id)
      match txs.find(fn(t) t.id == id)
        Just(tx) ->
          if tx.status == Active then
            val new-tx = tx-record(
              tx.id, RolledBack, tx.operations,
              tx.savepoints, tx.start-time
            )
            txs := Cons(new-tx, txs.filter(fn(t) t.id != id))
            if current-tx == id then current-tx := ""
            True
          else
            False
        Nothing -> False
    
    fun get-tx-status(id)
      match txs.find(fn(t) t.id == id)
        Just(tx) -> 
          match tx.status
            Active -> "active"
            Committed -> "committed"
            RolledBack -> "rolled_back"
            Preparing -> "preparing"
            Prepared -> "prepared"
            Committing -> "committing"
        Nothing -> "unknown"
    
    fun create-savepoint(id)
      val sp = "sp_" ++ ticks().show
      match txs.find(fn(t) t.id == id)
        Just(tx) ->
          val new-tx = tx-record(
            tx.id, tx.status, tx.operations,
            Cons(sp, tx.savepoints), tx.start-time
          )
          txs := Cons(new-tx, txs.filter(fn(t) t.id != id))
          sp
        Nothing -> ""
    
    fun rollback-to-savepoint(id, sp)
      // Would restore state to savepoint
      True
    
    fun is-in-tx()
      current-tx != ""
    
    fun get-current-tx()
      current-tx
    
    fun set-tx-isolation(level)
      ()  // Would set isolation level
    
    fun prepare-tx(id)
      match txs.find(fn(t) t.id == id)
        Just(tx) ->
          val new-tx = tx-record(
            tx.id, Prepared, tx.operations,
            tx.savepoints, tx.start-time
          )
          txs := Cons(new-tx, txs.filter(fn(t) t.id != id))
          True
        Nothing -> False
    
    fun confirm-tx(id)
      commit-tx(id)

// ═══════════════════════════════════════════════════════════════════════════
// Transactional operation helper
// ═══════════════════════════════════════════════════════════════════════════

fun atomic(action: () -> a): <transaction> (a, bool)
  val tx-id = begin-tx()
  try
    val result = action()
    val committed = commit-tx(tx-id)
    (result, committed)
  catch
    rollback-tx(tx-id)
    throw

// ═══════════════════════════════════════════════════════════════════════════
// Nested transaction support
// ═══════════════════════════════════════════════════════════════════════════

fun nested-tx(action: () -> a): <transaction> (a, bool)
  if !is-in-tx() then
    atomic(action)
  else
    val parent-tx = get-current-tx()
    val savepoint = create-savepoint(parent-tx)
    try
      val result = action()
      (result, True)
    catch
      rollback-to-savepoint(parent-tx, savepoint)
      throw

// ═══════════════════════════════════════════════════════════════════════════
// Transaction composition
// ═══════════════════════════════════════════════════════════════════════════

fun compose-txs(actions: list<() -> a>): <transaction> list<(a, bool)>
  actions.map(fn(action) atomic(action))

// ═══════════════════════════════════════════════════════════════════════════
// Distributed transaction coordination (2PC)
// ═══════════════════════════════════════════════════════════════════════════

struct participant
  id: string
  prepare: () -> bool
  commit: () -> bool
  rollback: () -> bool

fun two-phase-commit(coordinator-tx: string, participants: list<participant>): 
  <transaction> bool
  
  // Phase 1: Prepare
  val all-prepared = participants.foldl(True) fn(all, p)
    all && p.prepare()
  
  if !all-prepared then
    // Abort - rollback all
    participants.foreach(fn(p) p.rollback())
    rollback-tx(coordinator-tx)
    False
  else
    // Phase 2: Commit
    participants.foreach(fn(p) p.commit())
    commit-tx(coordinator-tx)
