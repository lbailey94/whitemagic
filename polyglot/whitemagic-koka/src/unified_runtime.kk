// Unified Koka Runtime - Chained effects for WhiteMagic hot paths
// Combines gan_ying event bus with hot_paths profiling in a single process
// Demonstrates Koka effect composition and inter-module communication

module unified_runtime

import std/os/readline
import std/num/float64

// ── Re-exported Types from gan_ying ─────────────────────────────────────────────

type event-type
  SystemStarted
  SystemStopped
  MemoryCreated
  MemoryUpdated
  ThreatDetected
  FlowStateEntered
  FlowStateExited

type complexity
  Low
  Medium
  High

// ── Unified State ──────────────────────────────────────────────────────────────

struct runtime-state
  event-count: int
  total-calls: int
  total-time-ms: float64
  last-event: string
  hot-paths-count: int

// ── Event Operations ───────────────────────────────────────────────────────────

fun event-type-to-string(et: event-type): string
  match et
    SystemStarted -> "system_started"
    SystemStopped -> "system_stopped"
    MemoryCreated -> "memory_created"
    MemoryUpdated -> "memory_updated"
    ThreatDetected -> "threat_detected"
    FlowStateEntered -> "flow_state_entered"
    FlowStateExited -> "flow_state_exited"

fun string-to-event-type(s: string): event-type
  match s
    "system_started" -> SystemStarted
    "system_stopped" -> SystemStopped
    "memory_created" -> MemoryCreated
    "memory_updated" -> MemoryUpdated
    "threat_detected" -> ThreatDetected
    "flow_state_entered" -> FlowStateEntered
    "flow_state_exited" -> FlowStateExited
    _ -> SystemStarted

// ── Profiling Operations ───────────────────────────────────────────────────────

fun estimate-complexity(avg-time-ms: float64, call-count: int): complexity
  if call-count > 100 && avg-time-ms > 10.0 then High
  else if call-count > 10 || avg-time-ms > 5.0 then Medium
  else Low

fun complexity-to-string(c: complexity): string
  match c
    Low -> "low"
    Medium -> "medium"
    High -> "high"

// ── Chained Operations ────────────────────────────────────────────────────────

// Emit event and profile it atomically
fun emit-and-profile(et: event-type, time-ms: float64, state: runtime-state): runtime-state
  val new-event-count = state.event-count + 1
  val new-total-calls = state.total-calls + 1
  val new-total-time = state.total-time-ms + time-ms
  val event-name = event-type-to-string(et)
  
  // Determine if this path is hot
  val new-hot-count = if time-ms > 10.0 
    then state.hot-paths-count + 1 
    else state.hot-paths-count
  
  Runtime-state(
    new-event-count,
    new-total-calls,
    new-total-time,
    event-name,
    new-hot-count
  )

// Check cascade and profile the check
fun check-cascade-profiled(et: event-type, state: runtime-state): (int, runtime-state)
  val handler-count = match et
    MemoryCreated -> 3
    MemoryUpdated -> 2
    ThreatDetected -> 5
    _ -> 1
  
  val new-state = Runtime-state(
    state.event-count,
    state.total-calls + 1,
    state.total-time-ms + 0.5,  // Cascade check is fast
    state.last-event,
    state.hot-paths-count
  )
  
  (handler-count, new-state)

// ── IPC Server ─────────────────────────────────────────────────────────────────

fun extract-op(line: string): string
  if line.contains("\"emit\"") then "emit"
  else if line.contains("\"cascade\"") then "cascade"
  else if line.contains("\"profile\"") then "profile"
  else if line.contains("\"status\"") then "status"
  else if line.contains("\"hot\"") then "hot"
  else if line.contains("\"quit\"") then "quit"
  else "unknown"

fun extract-event-type(line: string): event-type
  if line.contains("memory_created") then MemoryCreated
  else if line.contains("memory_updated") then MemoryUpdated
  else if line.contains("threat_detected") then ThreatDetected
  else if line.contains("flow_state") then FlowStateEntered
  else SystemStarted

fun json-state(s: runtime-state): string
  "{\"events\":" ++ show(s.event-count) ++
  ",\"total_calls\":" ++ show(s.total-calls) ++
  ",\"total_time_ms\":" ++ show(s.total-time-ms) ++
  ",\"last_event\":\"" ++ s.last-event ++ "\"" ++
  ",\"hot_paths\":" ++ show(s.hot-paths-count) ++ "}"

fun server-loop(state: runtime-state): io ()
  val line = readline()
  if line != "" then
    val op = extract-op(line)
    val response = match op
      "emit" ->
        val et = extract-event-type(line)
        val new-state = emit-and-profile(et, 1.5, state)
        "{\"emitted\":\"" ++ event-type-to-string(et) ++ "\",\"state\":" ++ json-state(new-state) ++ "}"
      "cascade" ->
        val et = extract-event-type(line)
        val (handlers, _new-state) = check-cascade-profiled(et, state)
        "{\"cascade\":\"" ++ event-type-to-string(et) ++ "\",\"handlers\":" ++ show(handlers) ++ "}"
      "profile" ->
        "{\"profile\":\"enabled\",\"calls\":" ++ show(state.total-calls) ++ "}"
      "status" ->
        json-state(state)
      "hot" ->
        "{\"hot_paths\":" ++ show(state.hot-paths-count) ++ ",\"threshold_ms\":10.0}"
      "quit" ->
        "{\"status\":\"stopped\"}"
      _ ->
        "{\"error\":\"unknown op\"}"
    
    println(response)
    
    if op != "quit" then
      // Update state based on operation
      val new-state = match op
        "emit" ->
          val et = extract-event-type(line)
          emit-and-profile(et, 1.5, state)
        "cascade" ->
          val et = extract-event-type(line)
          val (_, ns) = check-cascade-profiled(et, state)
          ns
        _ -> state
      
      server-loop(new-state)
    else
      ()
  else
    ()

fun main(): io ()
  val initial-state = Runtime-state(0, 0, 0.0, "none", 0)
  server-loop(initial-state)
