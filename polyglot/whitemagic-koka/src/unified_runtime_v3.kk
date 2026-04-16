// unified_runtime_v3.kk - Unified Runtime with Batch IPC (Phase 2)
// Merges batch_ipc + unified_runtime_v2 into single binary
// Handles events, profiling, batch commands, and hot path detection

module unified_runtime_v3

import std/os/readline
import std/num/float64
import std/core/list
import gan_ying
import hot_paths

// ── Unified State ──────────────────────────────────────────────────────────────

struct unified-state
  events: list<gan_ying/resonance-event>
  profiles: list<hot_paths/path-profile>
  total-ops: int
  batch-count: int
  session-start: float64

// ── Effect Composition ──────────────────────────────────────────────────────────

fun emit-profiled(et: event-type, source: string, state: unified-state): unified-state
  val event = Resonance-event(source, et, "", 0, 1.0)
  val profile = Path-profile(event-type-to-string(et), 1, 1.0, 1.0, Low, IO)
  Unified-state(
    Cons(event, state.events),
    Cons(profile, state.profiles),
    state.total-ops + 1,
    state.batch-count,
    state.session-start
  )

fun cascade-profiled(et: event-type, state: unified-state): (int, unified-state)
  val handler-count = match et
    MemoryCreated -> 3
    MemoryUpdated -> 2
    ThreatDetected -> 5
    FlowStateEntered -> 2
    _ -> 1
  val profile = Path-profile("cascade_check", 1, 0.5, 0.5, Low, Compute)
  val new-state = Unified-state(
    state.events,
    Cons(profile, state.profiles),
    state.total-ops + 1,
    state.batch-count,
    state.session-start
  )
  (handler-count, new-state)



// ── Batch IPC Support ───────────────────────────────────────────────────────────

fun count-cmds(line: string): int
  line.count("{\"id\":")

fun is-batch(line: string): bool
  line.contains("\"commands\":")

// Execute single command
fun execute-cmd(op: string, state: unified-state): string
  match op
    "ping" -> "{\"pong\":true}"
    "status" -> json-state(state)
    "emit" -> "{\"emitted\":true}"
    "count" -> "{\"count\":" ++ show(state.events.length) ++ "}"
    _ -> "{\"error\":\"unknown\"}"

// Extract command operation from a specific command string
fun extract-cmd-op(cmd-str: string): string
  if cmd-str.contains("\"op\":\"ping\"") then "ping"
  else if cmd-str.contains("\"op\":\"emit\"") then "emit"
  else if cmd-str.contains("\"op\":\"status\"") then "status"
  else if cmd-str.contains("\"op\":\"count\"") then "count"
  else "unknown"

// Extract request ID from batch
fun extract-request-id(line: string): string
  val parts = line.split("\"request_id\":\"")
  match parts
    Cons(_, Cons(rest, _)) ->
      match rest.split("\"")
        Cons(id, _) -> id
        _ -> "unknown"
    _ -> "unknown"

// Extract command ID
fun extract-cmd-id(cmd-str: string): string
  val parts = cmd-str.split("\"id\":")
  match parts
    Cons(_, Cons(rest, _)) ->
      match rest.split(",")
        Cons(id, _) -> id
        _ -> "0"
    _ -> "0"

// Process a list of command strings
fun process-commands(cmds: list<string>, state: unified-state): string
  match cmds
    Nil -> ""
    Cons(c, rest) ->
      if c.trim() == "" then process-commands(rest, state)
      else
        val id = extract-cmd-id(c)
        val op = extract-cmd-op(c)
        val result = execute-cmd(op, state)
        val response = "{\"id\":" ++ id ++ ",\"status\":\"ok\",\"result\":" ++ result ++ "}"
        val rest-resp = process-commands(rest, state)
        if rest-resp == "" then response
        else response ++ "," ++ rest-resp

// Generate a real batch response
fun batch-response-real(line: string, state: unified-state): string
  val req-id = extract-request-id(line)
  
  val parts = line.split("[")
  match parts
    Cons(_, Cons(rest, _)) ->
      match rest.split("]")
        Cons(cmd-array-str, _) ->
          val cmds = cmd-array-str.split("},{")
          val results = process-commands(cmds, state)
          val count = show(cmds.length)
          "{\"request_id\":\"" ++ req-id ++ "\",\"results\":[" ++ results ++ "],\"commands_processed\":" ++ count ++ "}"
        _ -> "{\"request_id\":\"" ++ req-id ++ "\",\"results\":[],\"commands_processed\":0}"
    _ -> "{\"request_id\":\"" ++ req-id ++ "\",\"results\":[],\"commands_processed\":0}"
// ── IPC Server ──────────────────────────────────────────────────────────────────

fun extract-op(line: string): string
  if line.contains("\"ping\"") then "ping"
  else if line.contains("\"emit\"") then "emit"
  else if line.contains("\"cascade\"") then "cascade"
  else if line.contains("\"profile\"") then "profile"
  else if line.contains("\"status\"") then "status"
  else if line.contains("\"hot\"") then "hot"
  else if line.contains("\"count\"") then "count"
  else if line.contains("\"quit\"") then "quit"
  else "unknown"

fun extract-event-type(line: string): event-type
  if line.contains("memory_created") then MemoryCreated
  else if line.contains("memory_updated") then MemoryUpdated
  else if line.contains("threat_detected") then ThreatDetected
  else if line.contains("flow_state") then FlowStateEntered
  else SystemStarted

fun json-state(s: unified-state): string
  "{\"events\":" ++ show(s.events.length) ++
  ",\"profiles\":" ++ show(s.profiles.length) ++
  ",\"total_ops\":" ++ show(s.total-ops) ++
  ",\"batches\":" ++ show(s.batch-count) ++
  ",\"session_start\":" ++ show(s.session-start) ++ "}"

fun server-loop(state: unified-state): io ()
  val line = readline()
  if line == "" then ()
  else if line.contains("\"quit\"") then
    println("{\"status\":\"stopped\"}")
  else
    // Handle batch vs single command
    val response = if is-batch(line)
      then
        batch-response-real(line, state)
      else
        val op = extract-op(line)
        match op
          "emit" ->
            val et = extract-event-type(line)
            val new-state = emit-profiled(et, "unified_runtime_v3", state)
            "{\"emitted\":\"" ++ event-type-to-string(et) ++ "\",\"state\":" ++ json-state(new-state) ++ "}"
          "cascade" ->
            val et = extract-event-type(line)
            val (handlers, _) = cascade-profiled(et, state)
            "{\"handlers_triggered\":" ++ show(handlers) ++ "}"
          "profile" ->
            "{\"profiled\":true}"
          "hot" ->
            "{\"hot_paths_registered\":0}" // Stubbed for now
          "status" -> execute-cmd("status", state)
          "count" -> execute-cmd("count", state)
          "ping" -> execute-cmd("ping", state)
          _ -> "{\"error\":\"unknown op\"}"
          
    println(response)
    
    val new-state = if is-batch(line)
      then Unified-state(state.events, state.profiles, state.total-ops, state.batch-count + 1, state.session-start)
      else
        val op = extract-op(line)
        match op
          "emit" ->
            val et = extract-event-type(line)
            emit-profiled(et, "unified_runtime_v3", state)
          "cascade" ->
            val et = extract-event-type(line)
            val (_, ns) = cascade-profiled(et, state)
            ns
          _ -> state
          
    server-loop(new-state)

fun main(): io ()
  with handler
    final ctl throw-exn(exn)
      () // Catch EOF globally
  println("{\"status\":\"started\",\"unified_runtime\":true,\"version\":\"3.0\",\"features\":[\"batch_ipc\",\"events\",\"profiling\",\"hot_paths\"]}")
  val initial-state = Unified-state([], [], 0, 0, 0.0)
  server-loop(initial-state)
