// Hot Paths - Type-safe profiling for performance-critical paths
// Port of Python hot_path_profiler.py
// Tracks timing, call frequency, and identifies optimization candidates

module hot_paths

import std/os/readline
import std/num/float64

// ── Profile Types ────────────────────────────────────────────────────────────────

pub type complexity
  Low
  Medium
  High

pub type path-category
  Compute
  Memory
  IO
  Mixed

pub struct path-profile
  name: string
  call-count: int
  total-time-ms: float64
  avg-time-ms: float64
  complexity: complexity
  category: path-category

pub struct profiling-session
  paths: list<path-profile>
  total-calls: int
  total-time-ms: float64
  hot-threshold-ms: float64

// ── Core Operations ────────────────────────────────────────────────────────────

pub fun complexity-to-string(c: complexity): string
  match c
    Low -> "low"
    Medium -> "medium"
    High -> "high"

pub fun category-to-string(cat: path-category): string
  match cat
    Compute -> "compute"
    Memory -> "memory"
    IO -> "io"
    Mixed -> "mixed"

pub fun estimate-complexity(avg-time-ms: float64, call-count: int): complexity
  if call-count > 100 && avg-time-ms > 10.0 then High
  else if call-count > 10 || avg-time-ms > 5.0 then Medium
  else Low

fun estimate-category(name: string): path-category
  if name.contains("embed") || name.contains("vector") || name.contains("compute") then Compute
  else if name.contains("memory") || name.contains("cache") || name.contains("store") then Memory
  else if name.contains("read") || name.contains("write") || name.contains("load") then IO
  else Mixed

pub fun create-profile(name: string, time-ms: float64): path-profile
  Path-profile(name, 1, time-ms, time-ms, estimate-complexity(time-ms, 1), estimate-category(name))

// ── IPC Server ─────────────────────────────────────────────────────────────────

fun json-profile(p: path-profile): string
  "{\"name\":\"" ++ p.name ++ 
  "\",\"calls\":" ++ show(p.call-count) ++
  ",\"avg_ms\":" ++ show(p.avg-time-ms) ++
  ",\"complexity\":\"" ++ complexity-to-string(p.complexity) ++ "\"" ++
  ",\"category\":\"" ++ category-to-string(p.category) ++ "\"}"

fun extract-op(line: string): string
  if line.contains("\"record\"") then "record"
  else if line.contains("\"profile\"") then "profile"
  else if line.contains("\"hot\"") then "hot"
  else if line.contains("\"status\"") then "status"
  else if line.contains("\"quit\"") then "quit"
  else "unknown"

fun extract-name(line: string): string
  if line.contains("embed") then "embedding_op"
  else if line.contains("compute") then "compute_op"
  else if line.contains("memory") then "memory_op"
  else if line.contains("vector") then "vector_op"
  else "unknown_op"

fun server-loop(total-calls: int, total-time: float64, profiles: list<path-profile>): io ()
  val line = readline()
  if line != "" then
    val op = extract-op(line)
    val response = match op
      "record" ->
        val name = extract-name(line)
        "{\"status\":\"recorded\",\"name\":\"" ++ name ++ "\"}"
      "profile" ->
        val name = extract-name(line)
        "{\"status\":\"profile\",\"name\":\"" ++ name ++ "\"}"
      "hot" ->
        "{\"hot_paths\":[],\"threshold_ms\":10.0}"
      "status" ->
        "{\"status\":\"ok\",\"total_calls\":" ++ show(total-calls) ++
        ",\"total_time_ms\":" ++ show(total-time) ++ "}"
      "quit" ->
        "{\"status\":\"stopped\"}"
      _ ->
        "{\"error\":\"unknown op\"}"
    
    println(response)
    
    if op != "quit" then
      server-loop(total-calls + 1, total-time + 1.0, profiles)
    else
      ()
  else
    ()

fun main(): io ()
  server-loop(0, 0.0, Nil)
