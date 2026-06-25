// transactions - Transactional operation effects (S022 Phase 2 VC4)
// Atomic operation support with commit/rollback semantics

module transactions

// ═══════════════════════════════════════════════════════════════════════════
// Transaction Effect Definition
// ═══════════════════════════════════════════════════════════════════════════

pub effect transaction
  fun begin-tx(): string
  fun commit-tx(tx-id: string): bool
  fun rollback-tx(tx-id: string): bool
  fun get-tx-status(tx-id: string): string
  fun create-savepoint(tx-id: string): string
  fun rollback-to-savepoint(tx-id: string, savepoint: string): bool
  fun is-in-tx(): bool
  fun get-current-tx(): string
  fun set-tx-isolation(level: string): ()
  fun prepare-tx(tx-id: string): bool
  fun confirm-tx(tx-id: string): bool

type tx-status
  Active
  Committed
  RolledBack
  Preparing
  Prepared
  Committing

struct tx-record
  tx-id: string
  status: tx-status
  operations: list<string>
  savepoints: list<string>
  start-time: int

fun is-active-status(s: tx-status): bool
  match s
    Active -> True
    _ -> False

pub fun handle-transactions(action: () -> <transaction|e> a): e a
  var txs : list<tx-record> := []
  var current-tx : string := ""
  var next-id := 0
  var tick-counter : int := 0

  with
    fun begin-tx()
      val new-id = "tx_" ++ next-id.show
      next-id := next-id + 1
      tick-counter := tick-counter + 1
      val tx = Tx-record(new-id, Active, [], [], tick-counter)
      txs := Cons(tx, txs)
      current-tx := new-id
      new-id

    fun commit-tx(target-id)
      match txs.find(fn(t) t.tx-id == target-id)
        Just(tx) ->
          if is-active-status(tx.status) then
            val new-tx = Tx-record(
              tx.tx-id, Committed, tx.operations,
              tx.savepoints, tx.start-time
            )
            txs := Cons(new-tx, txs.filter(fn(t) t.tx-id != target-id))
            if current-tx == target-id then current-tx := ""
            True
          else
            False
        Nothing -> False

    fun rollback-tx(target-id)
      match txs.find(fn(t) t.tx-id == target-id)
        Just(tx) ->
          if is-active-status(tx.status) then
            val new-tx = Tx-record(
              tx.tx-id, RolledBack, tx.operations,
              tx.savepoints, tx.start-time
            )
            txs := Cons(new-tx, txs.filter(fn(t) t.tx-id != target-id))
            if current-tx == target-id then current-tx := ""
            True
          else
            False
        Nothing -> False

    fun get-tx-status(target-id)
      match txs.find(fn(t) t.tx-id == target-id)
        Just(tx) ->
          match tx.status
            Active -> "active"
            Committed -> "committed"
            RolledBack -> "rolled_back"
            Preparing -> "preparing"
            Prepared -> "prepared"
            Committing -> "committing"
        Nothing -> "unknown"

    fun create-savepoint(target-id)
      tick-counter := tick-counter + 1
      val sp = "sp_" ++ tick-counter.show
      match txs.find(fn(t) t.tx-id == target-id)
        Just(tx) ->
          val new-tx = Tx-record(
            tx.tx-id, tx.status, tx.operations,
            Cons(sp, tx.savepoints), tx.start-time
          )
          txs := Cons(new-tx, txs.filter(fn(t) t.tx-id != target-id))
          sp
        Nothing -> ""

    fun rollback-to-savepoint(tx-id, sp)
      True

    fun is-in-tx()
      current-tx != ""

    fun get-current-tx()
      current-tx

    fun set-tx-isolation(level)
      ()

    fun prepare-tx(target-id)
      match txs.find(fn(t) t.tx-id == target-id)
        Just(tx) ->
          val new-tx = Tx-record(
            tx.tx-id, Prepared, tx.operations,
            tx.savepoints, tx.start-time
          )
          txs := Cons(new-tx, txs.filter(fn(t) t.tx-id != target-id))
          True
        Nothing -> False

    fun confirm-tx(target-id)
      // Inline commit logic to avoid recursive effect call
      match txs.find(fn(t) t.tx-id == target-id)
        Just(tx) ->
          if is-active-status(tx.status) then
            val new-tx = Tx-record(
              tx.tx-id, Committed, tx.operations,
              tx.savepoints, tx.start-time
            )
            txs := Cons(new-tx, txs.filter(fn(t) t.tx-id != target-id))
            if current-tx == target-id then current-tx := ""
            True
          else
            False
        Nothing -> False
  action()

fun atomic(action: () -> <transaction,exn|e> a): <transaction|e> maybe<a>
  val tx-id = begin-tx()
  try(fn() {
    val result = action()
    commit-tx(tx-id)
    Just(result)
  }, fn(_exn) {
    rollback-tx(tx-id)
    Nothing
  })

fun nested-tx(action: () -> <transaction,exn|e> a): <transaction|e> maybe<a>
  if !is-in-tx() then
    atomic(action)
  else
    val parent-tx = get-current-tx()
    val savepoint = create-savepoint(parent-tx)
    try(fn() {
      val result = action()
      Just(result)
    }, fn(_exn) {
      rollback-to-savepoint(parent-tx, savepoint)
      Nothing
    })

fun compose-txs(actions: list<() -> <transaction,exn|e> a>): <transaction|e> list<maybe<a>>
  actions.map(fn(action) atomic(action))

struct participant
  p-id: string
  prepare: () -> bool
  commit: () -> bool
  rollback: () -> bool

fun two-phase-commit(coordinator-tx: string, participants: list<participant>): <transaction> bool
  val all-prepared = participants.foldl(True, fn(all, p)
    val prep = p.prepare
    all && prep()
  )
  if !all-prepared then
    participants.foreach(fn(p)
      val rb = p.rollback
      val _ = rb()
      ()
    )
    rollback-tx(coordinator-tx)
    False
  else
    participants.foreach(fn(p)
      val cm = p.commit
      val _ = cm()
      ()
    )
    commit-tx(coordinator-tx)
    True
