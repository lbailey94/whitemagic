// metrics.kk - Prometheus Metrics Export for Koka Binaries
// Provides standardized metrics export for observability

module metrics

import std/num/float64
import std/num/int64
import std/time

// ── Metric Types ──────────────────────────────────────────────────────────────

pub struct counter
  name: string
  value: int64
  help: string

pub struct gauge
  name: string
  value: float64
  help: string

pub struct histogram
  name: string
  buckets: list<(float64, int64)>  // (upper_bound, count)
  sum: float64
  count: int64
  help: string

pub struct metrics-snapshot
  counters: list<counter>
  gauges: list<gauge>
  histograms: list<histogram>
  timestamp: float64

// ── Metric Operations ──────────────────────────────────────────────────────────

pub fun increment(c: counter): counter
  Counter(c.name, c.value + std/num/int64/int64(1), c.help)

pub fun add(c: counter, n: int): counter
  Counter(c.name, c.value + std/num/int64/int64(n), c.help)

pub fun set(g: gauge, v: float64): gauge
  Gauge(g.name, v, g.help)

pub fun observe(h: histogram, v: float64): histogram
  // Find appropriate bucket and increment
  val new-buckets = h.buckets.map(fn(bucket)
    val (upper, count) = bucket
    if v <= upper then (upper, count + std/num/int64/int64(1))
    else bucket
  )
  Histogram(h.name, new-buckets, h.sum + v, h.count + std/num/int64/int64(1), h.help)

// ── Prometheus Format Export ───────────────────────────────────────────────────

pub fun export-counter(c: counter): string
  "# HELP " ++ c.name ++ " " ++ c.help ++ "\n" ++
  "# TYPE " ++ c.name ++ " counter\n" ++
  c.name ++ " " ++ std/num/int64/show(c.value)

pub fun export-gauge(g: gauge): string
  "# HELP " ++ g.name ++ " " ++ g.help ++ "\n" ++
  "# TYPE " ++ g.name ++ " gauge\n" ++
  g.name ++ " " ++ show(g.value)

pub fun export-histogram(h: histogram): string
  val bucket-lines = h.buckets.map(fn(b)
    val (upper, count) = b
    h.name ++ "_bucket{le=\"" ++ show(upper) ++ "\"} " ++ std/num/int64/show(count)
  )
  val lines = [
    "# HELP " ++ h.name ++ " " ++ h.help,
    "# TYPE " ++ h.name ++ " histogram"
  ] ++ bucket-lines ++ [
    h.name ++ "_sum " ++ show(h.sum),
    h.name ++ "_count " ++ std/num/int64/show(h.count)
  ]
  list/join(lines, "\n")

pub fun export-all(snapshot: metrics-snapshot): string
  val counter-lines = snapshot.counters.map(export-counter)
  val gauge-lines = snapshot.gauges.map(export-gauge)
  val hist-lines = snapshot.histograms.map(export-histogram)
  
  list/join(counter-lines ++ gauge-lines ++ hist-lines, "\n\n")

// ── Standard Metrics for IPC Binaries ──────────────────────────────────────────

pub fun standard-ipc-metrics(binary-name: string): metrics-snapshot
  Metrics-snapshot(
    [
      Counter("koka_ipc_commands_total", std/num/int64/int64(0), "Total IPC commands processed"),
      Counter("koka_ipc_errors_total", std/num/int64/int64(0), "Total IPC errors")
    ],
    [
      Gauge("koka_ipc_latency_ms", 0.0, "Current IPC latency in milliseconds"),
      Gauge("koka_process_uptime_seconds", 0.0, "Process uptime in seconds")
    ],
    [
      Histogram(
        "koka_ipc_duration_ms",
        [(0.1, std/num/int64/int64(0)), (1.0, std/num/int64/int64(0)), (10.0, std/num/int64/int64(0)), (100.0, std/num/int64/int64(0))],
        0.0,
        std/num/int64/int64(0),
        "IPC command duration in milliseconds"
      )
    ],
    0.0
  )

// ── Utility ────────────────────────────────────────────────────────────────────

fun list/join(xs: list<string>, sep: string): string
  match xs
    Nil -> ""
    Cons(s, Nil) -> s
    Cons(s, rest) -> s ++ sep ++ list/join(rest, sep)

// ── Main (for testing) ─────────────────────────────────────────────────────────

fun main(): io ()
  val snapshot = standard-ipc-metrics("test")
  println(export-all(snapshot))
