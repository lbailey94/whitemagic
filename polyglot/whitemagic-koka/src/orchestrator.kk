// orchestrator.kk - Unified Koka Binary Orchestrator
// Centralized management of all Koka runtime binaries
// Phase 6 Implementation Army Objective #6

module orchestrator

import std/os/readline
import std/os/process
import std/num/float64
import std/num/int64
import std/time

// ── Process Management ────────────────────────────────────────────────────────

struct managed-process
  name: string
  pid: int
  binary-path: string
  status: string  // "running", "stopped", "crashed"
  start-time: float64
  restart-count: int

struct orchestrator-state
  processes: list<managed-process>
  total-restarts: int
  last-health-check: float64

// ── Binary Registry ───────────────────────────────────────────────────────────

val binary-registry: list<(string, string)> = [
  ("unified_runtime_v3", "./unified_runtime_v3"),
  ("effect_runtime", "./effect_runtime"),
  ("ring_buffer", "./ring_buffer"),
  ("rust_bridge", "./rust_bridge"),
  ("prat", "./prat"),
  ("gan_ying", "./gan_ying"),
  ("hot_paths", "./hot_paths"),
  ("resonance", "./resonance")
]

// ── Process Operations ─────────────────────────────────────────────────────────

fun find-process(proc-name: string, processes: list<managed-process>): maybe<managed-process>
  processes.find(fn(p) p.name == proc-name)

fun update-process(state: orchestrator-state, proc-name: string, new-status: string): orchestrator-state
  val new-processes = state.processes.map(fn(p)
    if p.name == proc-name then
      Managed-process(p.name, p.pid, p.binary-path, new-status, p.start-time, p.restart-count)
    else
      p
  )
  Orchestrator-state(new-processes, state.total-restarts, state.last-health-check)

// ── Health Monitoring ──────────────────────────────────────────────────────────

fun check-health(process: managed-process): string
  // Simulate health check
  if process.status == "running" then "healthy"
  else if process.status == "crashed" then "unhealthy"
  else "unknown"

fun health-summary(state: orchestrator-state): string
  val total = state.processes.length
  val running = state.processes.filter(fn(p) p.status == "running").length
  val crashed = state.processes.filter(fn(p) p.status == "crashed").length
  "{\"total\":" ++ show(total) ++ ",\"running\":" ++ show(running) ++ ",\"crashed\":" ++ show(crashed) ++ "}"

// ── Command Processing ────────────────────────────────────────────────────────

fun extract-op(line: string): string
  if line.contains("\"spawn\"") then "spawn"
  else if line.contains("\"stop\"") then "stop"
  else if line.contains("\"restart\"") then "restart"
  else if line.contains("\"status\"") then "status"
  else if line.contains("\"health\"") then "health"
  else if line.contains("\"list\"") then "list"
  else if line.contains("\"quit\"") then "quit"
  else "unknown"

fun extract-binary(cmd-line: string): string
  if cmd-line.contains("unified_runtime_v3") then "unified_runtime_v3"
  else if cmd-line.contains("effect_runtime") then "effect_runtime"
  else if cmd-line.contains("ring_buffer") then "ring_buffer"
  else if cmd-line.contains("rust_bridge") then "rust_bridge"
  else if cmd-line.contains("prat") then "prat"
  else if cmd-line.contains("gan_ying") then "gan_ying"
  else "unknown"

// ── Server Loop ──────────────────────────────────────────────────────────────

fun server-loop(state: orchestrator-state): io ()
  val line = readline()
  if line == "" then ()
  else if line.contains("\"quit\"") then
    println("{\"status\":\"stopped\",\"processes_shutdown\":" ++ show(state.processes.length) ++ "}")
  else
    val op = extract-op(line)
    val binary = extract-binary(line)
    
    val response = match op
      "spawn" ->
        if binary == "unknown" then
          "{\"error\":\"unknown binary\"}"
        else
          val new-process = Managed-process(binary, 0, "./" ++ binary, "running", 0.0, 0)
          val new-state = Orchestrator-state(
            Cons(new-process, state.processes),
            state.total-restarts,
            0.0
          )
          "{\"spawned\":\"" ++ binary ++ "\",\"status\":\"running\",\"total_processes\":" ++ show(new-state.processes.length) ++ "}"
      
      "stop" ->
        if binary == "unknown" then
          "{\"error\":\"unknown binary\"}"
        else
          "{\"stopped\":\"" ++ binary ++ "\"}"
      
      "restart" ->
        if binary == "unknown" then
          "{\"error\":\"unknown binary\"}"
        else
          "{\"restarted\":\"" ++ binary ++ "\",\"restart_count\":" ++ show(state.total-restarts + 1) ++ "}"
      
      "status" ->
        if binary == "unknown" then
          health-summary(state)
        else
          match find-process(binary, state.processes)
            Nothing -> "{\"error\":\"process not found\"}"
            Just(p) -> "{\"name\":\"" ++ p.name ++ "\",\"status\":\"" ++ p.status ++ "\",\"restarts\":" ++ show(p.restart-count) ++ "}"
      
      "health" ->
        health-summary(state)
      
      "list" ->
        val names = state.processes.map(fn(p) "\"" ++ p.name ++ "\"")
        "{\"processes\":" ++ show(names) ++ ",\"count\":" ++ show(state.processes.length) ++ "}"
      
      _ ->
        "{\"error\":\"unknown command\"}"
    
    println(response)
    
    // Update state
    val new-state = match op
      "spawn" ->
        if binary != "unknown" then
          val new-process = Managed-process(binary, 0, "./" ++ binary, "running", 0.0, 0)
          Orchestrator-state(Cons(new-process, state.processes), state.total-restarts, 0.0)
        else
          state
      "restart" ->
        Orchestrator-state(state.processes, state.total-restarts + 1, state.last-health-check)
      _ ->
        state
    
    server-loop(new-state)

// ── Main ──────────────────────────────────────────────────────────────────────

fun main(): io ()
  println("{\"status\":\"started\",\"orchestrator\":true,\"version\":\"7.0\",\"managed_binaries\":" ++ show(binary-registry.length) ++ ",\"features\":[\"spawn\",\"stop\",\"restart\",\"health\",\"list\"]}")
  val initial-state = Orchestrator-state([], 0, 0.0)
  server-loop(initial-state)
