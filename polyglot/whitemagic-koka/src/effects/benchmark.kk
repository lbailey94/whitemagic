// benchmark - Handler dispatch speed benchmark (S022 Phase 1 VC5)
// Performance testing for Koka effect handlers

module benchmark

import std/time
import std/num/float64

// ═══════════════════════════════════════════════════════════════════════════
// Benchmark Effects
// ═══════════════════════════════════════════════════════════════════════════

effect bench
  fun record-start(name: string): ()
  fun record-end(name: string): ()
  fun get-result(name: string): float64
  fun get-all-results(): list<(string, float64)>
  fun reset-all(): ()

// ═══════════════════════════════════════════════════════════════════════════
// Benchmark Handler
// ═══════════════════════════════════════════════════════════════════════════

val handle-benchmark = handler
  var starts : list<(string, int)> := []
  var results : list<(string, float64)> := []
  
  fun record-start(name)
    starts := Cons((name, ticks()), starts)
  
  fun record-end(name)
    val end-ticks = ticks()
    match starts.find(fn(p) p.fst == name)
      Just((_, start-ticks)) ->
        val elapsed = float64(end-ticks - start-ticks)
        results := Cons((name, elapsed), results)
      Nothing -> ()
  
  fun get-result(name)
    match results.find(fn(p) p.fst == name)
      Just((_, r)) -> r
      Nothing -> 0.0
  
  fun get-all-results()
    results
  
  fun reset-all()
    starts := []
    results := []

// ═══════════════════════════════════════════════════════════════════════════
// PRAT Handler Dispatch Benchmark
// ═══════════════════════════════════════════════════════════════════════════

// Mock effects for benchmarking

effect mock-prat-route
  fun dispatch-tool(tool-name: string, args: string): string

val handle-mock-prat-fast = handler
  fun dispatch-tool(name, args)
    "result:" ++ name

fun benchmark-prat-dispatch(iterations: int): <bench, mock-prat-route> float64
  bench/record-start("prat_dispatch")
  
  var i := 0
  while i < iterations do
    val _ = mock-prat-route/dispatch-tool("test_tool", "{}")
    i := i + 1
  
  bench/record-end("prat_dispatch")
  bench/get-result("prat_dispatch") / float64(iterations)

// ═══════════════════════════════════════════════════════════════════════════
// Resonance Handler Benchmark
// ═══════════════════════════════════════════════════════════════════════════

effect mock-resonance
  fun record-snapshot(gana: string, tool: string): ()
  fun get-last-gana(): string

val handle-mock-resonance-fast = handler
  var last-gana := ""
  
  fun record-snapshot(g, t)
    last-gana := g
  
  fun get-last-gana()
    last-gana

fun benchmark-resonance-tracking(iterations: int): <bench, mock-resonance> float64
  bench/record-start("resonance_tracking")
  
  var i := 0
  while i < iterations do
    mock-resonance/record-snapshot("gana_test", "tool_" ++ i.show)
    val _ = mock-resonance/get-last-gana()
    i := i + 1
  
  bench/record-end("resonance_tracking")
  bench/get-result("resonance_tracking") / float64(iterations)

// ═══════════════════════════════════════════════════════════════════════════
// Gan Ying Event Bus Benchmark
// ═══════════════════════════════════════════════════════════════════════════

effect mock-gy-event
  fun emit-event(et: string, payload: string): ()
  fun get-pending-count(): int

val handle-mock-gy-fast = handler
  var events := [] : list<string>
  
  fun emit-event(et, p)
    events := Cons(et ++ ":" ++ p, events)
  
  fun get-pending-count()
    events.length

fun benchmark-event-emit(iterations: int): <bench, mock-gy-event> float64
  bench/record-start("event_emit")
  
  var i := 0
  while i < iterations do
    mock-gy-event/emit-event("test_event", "payload_" ++ i.show)
    i := i + 1
  
  bench/record-end("event_emit")
  bench/get-result("event_emit") / float64(iterations)

// ═══════════════════════════════════════════════════════════════════════════
// Composite Handler Chain Benchmark
// ═══════════════════════════════════════════════════════════════════════════

fun benchmark-full-prat-chain(iterations: int): 
  <bench, mock-prat-route, mock-resonance, mock-gy-event> float64
  
  bench/record-start("full_prat_chain")
  
  var i := 0
  while i < iterations do
    // Full chain: route → resonance → event
    val result = mock-prat-route/dispatch-tool("memory.create", "{}")
    mock-resonance/record-snapshot("gana_neck", "memory.create")
    mock-gy-event/emit-event("memory.created", result)
    i := i + 1
  
  bench/record-end("full_prat_chain")
  bench/get-result("full_prat_chain") / float64(iterations)

// ═══════════════════════════════════════════════════════════════════════════
// Main benchmark suite
// ═══════════════════════════════════════════════════════════════════════════

struct benchmark-result
  name: string
  iterations: int
  total-us: float64  // microseconds
  per-op-us: float64
  ops-per-sec: float64

fun run-benchmark(name: string, f: () -> float64, iterations: int): benchmark-result
  val per-op = f()
  val total = per-op * float64(iterations)
  benchmark-result(
    name,
    iterations,
    total,
    per-op,
    1000000.0 / per-op  // ops per second
  )

fun format-result(r: benchmark-result): string
  r.name ++ ":\n" ++
  "  iterations: " ++ r.iterations.show ++ "\n" ++
  "  total: " ++ r.total-us.show ++ " µs\n" ++
  "  per-op: " ++ r.per-op-us.show ++ " µs\n" ++
  "  ops/sec: " ++ r.ops-per-sec.show ++ "\n"

// ═══════════════════════════════════════════════════════════════════════════
// Run all benchmarks
// ═══════════════════════════════════════════════════════════════════════════

fun run-all-benchmarks(): <bench> list<benchmark-result>
  val iterations = 10000
  
  // PRAT dispatch benchmark
  val prat-result = 
    with handle-mock-prat-fast
    run-benchmark("prat_dispatch", fn() benchmark-prat-dispatch(iterations), iterations)
  
  // Resonance benchmark  
  val resonance-result =
    with handle-mock-resonance-fast
    run-benchmark("resonance_tracking", fn() benchmark-resonance-tracking(iterations), iterations)
  
  // Event emit benchmark
  val event-result =
    with handle-mock-gy-fast
    run-benchmark("event_emit", fn() benchmark-event-emit(iterations), iterations)
  
  // Full chain benchmark
  val chain-result =
    with handle-mock-prat-fast
    with handle-mock-resonance-fast
    with handle-mock-gy-fast
    run-benchmark("full_prat_chain", fn() benchmark-full-prat-chain(1000), 1000)
  
  [prat-result, resonance-result, event-result, chain-result]

// ═══════════════════════════════════════════════════════════════════════════
// Benchmark report generation
// ═══════════════════════════════════════════════════════════════════════════

fun generate-benchmark-report(): string
  with handle-benchmark
  val results = run-all-benchmarks()
  
  var report := "# Koka PRAT Handler Benchmark Results\n\n"
  report := report ++ "| Benchmark | Iterations | Per-Op (µs) | Ops/Sec |\n"
  report := report ++ "|-----------|------------|-------------|----------|\n"
  
  results.foreach fn(r)
    report := report ++ "| " ++ r.name ++ " | " ++
              r.iterations.show ++ " | " ++
              r.per-op-us.show ++ " | " ++
              r.ops-per-sec.show ++ " |\n"
  
  report

// ═══════════════════════════════════════════════════════════════════════════
// Comparison with Python baseline
// ═══════════════════════════════════════════════════════════════════════════

struct comparison
  operation: string
  python-us: float64
  koka-us: float64
  speedup: float64

fun compare-with-python-baseline(): list<comparison>
  [
    comparison("handler_dispatch", 5.0, 0.5, 10.0),    // Estimated
    comparison("resonance_record", 8.0, 0.8, 10.0),    // Estimated
    comparison("event_emit", 3.0, 0.3, 10.0),         // Estimated
    comparison("full_chain", 15.0, 1.5, 10.0)          // Estimated
  ]

fun format-comparison(c: comparison): string
  c.operation ++ ": Python=" ++ c.python-us.show ++ 
  "µs, Koka=" ++ c.koka-us.show ++ "µs, speedup=" ++ c.speedup.show ++ "x"
