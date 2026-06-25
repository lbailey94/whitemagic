// galaxy_semantics - Effect tracking for cross-galaxy operations
// Phase 8: Galaxy Semantics (Koka)
//
// Tracks which effects each galaxy operation has, enabling
// static reasoning about side effects across galaxy boundaries.

module src/effects/galaxy_semantics

// ═══════════════════════════════════════════════════════════════════════════
// Galaxy Effect Types
// ═══════════════════════════════════════════════════════════════════════════

// Unified galaxy effect covering read, write, transfer, audit, and meta operations
effect galaxy
  fun query-galaxy(galaxy-id: string, query: string): string
  fun get-stats(galaxy-id: string): galaxy-stats
  fun store-memory(galaxy-id: string, content: string, importance: float64): string
  fun migrate-memory(memory-id: string, from-galaxy: string, to-galaxy: string): bool
  fun export-galaxy(galaxy-id: string): string
  fun import-galaxy(galaxy-id: string, data: string): int
  fun log-operation(op: galaxy-operation): ()
  fun get-operations(): list<galaxy-operation>
  fun list-galaxies(): list<string>
  fun get-active-galaxy(): string
  fun set-active-galaxy(galaxy-id: string): ()

// ═══════════════════════════════════════════════════════════════════════════
// Data Types
// ═══════════════════════════════════════════════════════════════════════════

struct galaxy-stats
  galaxy-id: string
  memory-count: int
  mean-importance: float64
  min-importance: float64
  max-importance: float64

struct galaxy-operation
  op-type: op-type
  source-galaxy: string
  target-galaxy: string
  memory-id: string
  timestamp: string

type op-type
  OpRead
  OpWrite
  OpMigrate
  OpExport
  OpImport
  OpMerge
  OpCompare

// ═══════════════════════════════════════════════════════════════════════════
// Effect Tracking
// ═══════════════════════════════════════════════════════════════════════════

// Track all galaxy operations in a log (part of galaxy effect)
// galaxy-audit operations are included in the unified galaxy effect

// ═══════════════════════════════════════════════════════════════════════════
// Semantic Operations (Pure)
// ═══════════════════════════════════════════════════════════════════════════

// Classify the effect profile of an operation
fun classify-operation(op: op-type): effect-profile
  match op
    OpRead    -> Effect-profile(True, False, False)
    OpWrite   -> Effect-profile(False, True, False)
    OpMigrate -> Effect-profile(True, True, False)
    OpExport  -> Effect-profile(True, False, True)
    OpImport  -> Effect-profile(False, True, True)
    OpMerge   -> Effect-profile(True, True, False)
    OpCompare -> Effect-profile(True, False, False)

struct effect-profile
  reads: bool
  writes: bool
  transfers: bool

// Check if two operations can run concurrently
fun concurrent-safe(a: op-type, b: op-type): bool
  val pa = classify-operation(a)
  val pb = classify-operation(b)
  // Safe only if neither operation writes
  if not(pa.writes) && not(pb.writes) then True
  else False

fun galaxy-allowed(gid: string, allowed: list<string>): bool
  match allowed.find(fn(g) g == gid)
    Just(_) -> True
    Nothing -> False

// Validate that a galaxy operation is permitted
fun validate-operation(op: galaxy-operation, allowed-galaxies: list<string>): maybe<string>
  if not(galaxy-allowed(op.source-galaxy, allowed-galaxies)) then
    Just("Source galaxy not allowed: " ++ op.source-galaxy)
  else if op.target-galaxy != "" && not(galaxy-allowed(op.target-galaxy, allowed-galaxies)) then
    Just("Target galaxy not allowed: " ++ op.target-galaxy)
  else
    Nothing

// ═══════════════════════════════════════════════════════════════════════════
// High-Level Galaxy Operations (with effects)
// ═══════════════════════════════════════════════════════════════════════════

// Read from a galaxy with audit logging
fun galaxy-query(galaxy-id: string, query: string): <galaxy> string
  val result = query-galaxy(galaxy-id, query)
  log-operation(Galaxy-operation(OpRead, galaxy-id, "", "", ""))
  result

// Store to a galaxy with audit logging
fun galaxy-store(galaxy-id: string, content: string, importance: float64): <galaxy> string
  val memory-id = store-memory(galaxy-id, content, importance)
  log-operation(Galaxy-operation(OpWrite, "", galaxy-id, memory-id, ""))
  memory-id

// Migrate a memory between galaxies
fun galaxy-migrate(memory-id: string, from-galaxy: string, to-galaxy: string): <galaxy> bool
  val success = migrate-memory(memory-id, from-galaxy, to-galaxy)
  log-operation(Galaxy-operation(OpMigrate, from-galaxy, to-galaxy, memory-id, ""))
  success

// Export a galaxy (read + transfer effect)
fun galaxy-export(galaxy-id: string): <galaxy> string
  val data = export-galaxy(galaxy-id)
  log-operation(Galaxy-operation(OpExport, galaxy-id, "", "", ""))
  data

// Import into a galaxy (write + transfer effect)
fun galaxy-import(galaxy-id: string, data: string): <galaxy> int
  val count = import-galaxy(galaxy-id, data)
  log-operation(Galaxy-operation(OpImport, "", galaxy-id, "", ""))
  count

// ═══════════════════════════════════════════════════════════════════════════
// Test Handler (In-memory implementation for testing)
// ═══════════════════════════════════════════════════════════════════════════

val test-galaxy-stats = Galaxy-stats("test", 10, 0.5, 0.1, 0.9)

fun run-galaxy-test(action: () -> <galaxy|e> string): e string
  handle action
    fun query-galaxy(gid, q)
      "query-result-for-" ++ gid
    fun get-stats(gid)
      test-galaxy-stats
    fun store-memory(gid, content, imp)
      "mem-" ++ gid ++ "-1"
    fun migrate-memory(mid, from, to)
      True
    fun export-galaxy(gid)
      "WMGX"
    fun import-galaxy(gid, data)
      42
    fun log-operation(op)
      ()
    fun get-operations()
      []
    fun list-galaxies()
      ["universal", "oracle", "insight"]
    fun get-active-galaxy()
      "universal"
    fun set-active-galaxy(gid)
      ()

// ═══════════════════════════════════════════════════════════════════════════
// Tests
// ═══════════════════════════════════════════════════════════════════════════

fun test-classify-read()
  val p = classify-operation(OpRead)
  if p.reads && not(p.writes) && not(p.transfers) then "PASS"
  else "FAIL: classify Read"

fun test-classify-write()
  val p = classify-operation(OpWrite)
  if not(p.reads) && p.writes && not(p.transfers) then "PASS"
  else "FAIL: classify Write"

fun test-classify-migrate()
  val p = classify-operation(OpMigrate)
  if p.reads && p.writes && not(p.transfers) then "PASS"
  else "FAIL: classify Migrate"

fun test-classify-export()
  val p = classify-operation(OpExport)
  if p.reads && not(p.writes) && p.transfers then "PASS"
  else "FAIL: classify Export"

fun test-concurrent-safe-reads()
  if concurrent-safe(OpRead, OpRead) then "PASS"
  else "FAIL: concurrent reads"

fun test-concurrent-unsafe-write-read()
  // Write + Read on potentially same data is not safe
  if not(concurrent-safe(OpWrite, OpRead)) then "PASS"
  else "FAIL: write+read should not be concurrent-safe"

fun test-validate-allowed()
  val op = Galaxy-operation(OpRead, "oracle", "", "m1", "2026-01-01")
  match validate-operation(op, ["oracle", "universal"])
    Nothing -> "PASS"
    Just(m) -> "FAIL: " ++ m

fun test-validate-disallowed()
  val op = Galaxy-operation(OpWrite, "restricted", "", "m1", "2026-01-01")
  match validate-operation(op, ["oracle", "universal"])
    Just(_) -> "PASS"
    Nothing -> "FAIL: should have been rejected"

fun test-galaxy-query()
  val result = run-galaxy-test(fn() -> galaxy-query("oracle", "test"))
  if result == "query-result-for-oracle" then "PASS"
  else "FAIL: galaxy-query returned " ++ result

fun test-galaxy-store()
  val result = run-galaxy-test(fn() -> galaxy-store("oracle", "content", 0.8))
  if result == "mem-oracle-1" then "PASS"
  else "FAIL: galaxy-store returned " ++ result

pub fun run-all-tests(): list<string>
  [ test-classify-read()
  , test-classify-write()
  , test-classify-migrate()
  , test-classify-export()
  , test-concurrent-safe-reads()
  , test-concurrent-unsafe-write-read()
  , test-validate-allowed()
  , test-validate-disallowed()
  , test-galaxy-query()
  , test-galaxy-store()
  ]

pub fun main(): console ()
  val results = run-all-tests()
  results.foreach(fn(r)
    println(r)
  )
  val failures = results.filter(fn(r) 
    match r.find("FAIL")
      Just(_) -> True
      Nothing -> False
  )
  if failures.is-empty then
    println("\nAll galaxy semantics tests PASSED")
  else
    println("\n" ++ failures.length.show ++ " test(s) FAILED")
