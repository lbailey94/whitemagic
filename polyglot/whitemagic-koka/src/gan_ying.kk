// Gan Ying (感應) - Sympathetic Resonance Event Bus
// "Things that accord in tone vibrate together"
// Port of Python gan_ying_enhanced.py for type-safe event handling

module gan_ying

import std/os/readline
import std/num/float64

// ── Event Types ────────────────────────────────────────────────────────────────

pub type event-type
  SystemStarted
  SystemStopped
  SystemHealthChanged
  MemoryCreated
  MemoryUpdated
  MemoryRecalled
  MemoryConsolidated
  GardenActivated
  JoyTriggered
  WisdomIntegrated
  ThreatDetected
  AnomalyDetected
  FlowStateEntered
  FlowStateExited

// ── Event Structure ───────────────────────────────────────────────────────────

pub struct resonance-event
  source: string
  event-type: event-type
  data: string
  timestamp: int
  confidence: float64

pub struct cascade-trigger
  event-type: event-type
  handler-count: int
  priority: int

// ── Core Operations ───────────────────────────────────────────────────────────

pub fun event-type-to-string(et: event-type): string
  match et
    SystemStarted -> "system_started"
    SystemStopped -> "system_stopped"
    SystemHealthChanged -> "system_health_changed"
    MemoryCreated -> "memory_created"
    MemoryUpdated -> "memory_updated"
    MemoryRecalled -> "memory_recalled"
    MemoryConsolidated -> "memory_consolidated"
    GardenActivated -> "garden_activated"
    JoyTriggered -> "joy_triggered"
    WisdomIntegrated -> "wisdom_integrated"
    ThreatDetected -> "threat_detected"
    AnomalyDetected -> "anomaly_detected"
    FlowStateEntered -> "flow_state_entered"
    FlowStateExited -> "flow_state_exited"

pub fun string-to-event-type(s: string): event-type
  match s
    "system_started" -> SystemStarted
    "system_stopped" -> SystemStopped
    "system_health_changed" -> SystemHealthChanged
    "memory_created" -> MemoryCreated
    "memory_updated" -> MemoryUpdated
    "memory_recalled" -> MemoryRecalled
    "memory_consolidated" -> MemoryConsolidated
    "garden_activated" -> GardenActivated
    "joy_triggered" -> JoyTriggered
    "wisdom_integrated" -> WisdomIntegrated
    "threat_detected" -> ThreatDetected
    "anomaly_detected" -> AnomalyDetected
    "flow_state_entered" -> FlowStateEntered
    "flow_state_exited" -> FlowStateExited
    _ -> SystemStarted

// ── Event Operations ───────────────────────────────────────────────────────────

fun emit-event(source: string, et: event-type, data: string, confidence: float64, count: int): (resonance-event, int)
  val new-count = count + 1
  (Resonance-event(source, et, data, 0, confidence), new-count)

fun check-cascade(et: event-type): cascade-trigger
  val handler-count = match et
    MemoryCreated -> 3
    MemoryUpdated -> 2
    ThreatDetected -> 5
    _ -> 1
  val priority = match et
    ThreatDetected -> 10
    MemoryCreated -> 5
    _ -> 1
  Cascade-trigger(et, handler-count, priority)

// ── IPC Server ─────────────────────────────────────────────────────────────────

fun json-response(op: string, result: string): string
  "{\"op\":\"" ++ op ++ "\",\"result\":\"" ++ result ++ "\"}"

fun json-event-response(event: resonance-event): string
  "{\"source\":\"" ++ event.source ++ "\",\"type\":\"" ++ 
  event-type-to-string(event.event-type) ++ "\",\"confidence\":" ++
  show(event.confidence) ++ "}"

fun extract-op(line: string): string
  if line.contains("\"emit\"") then "emit"
  else if line.contains("\"count\"") then "count"
  else if line.contains("\"reset\"") then "reset"
  else if line.contains("\"cascade\"") then "cascade"
  else if line.contains("\"status\"") then "status"
  else if line.contains("\"quit\"") then "quit"
  else if line.contains("\"invoke-gana\"") then "invoke-gana"
  else if line.contains("\"route-prat\"") then "route-prat"
  else "unknown"

fun extract-type(line: string): event-type
  if line.contains("\"system_started\"") then SystemStarted
  else if line.contains("\"system_stopped\"") then SystemStopped
  else if line.contains("\"memory_created\"") then MemoryCreated
  else if line.contains("\"memory_updated\"") then MemoryUpdated
  else if line.contains("\"threat_detected\"") then ThreatDetected
  else if line.contains("\"joy_triggered\"") then JoyTriggered
  else SystemStarted


extern flush-stdout() : console ()
  c inline "fflush(stdout)"

fun server-loop(event-count: int): io ()

  with handler
    final ctl throw-exn(exn)
      () // Catch EOF
  val line = readline()
  if line != "" then
    val op = extract-op(line)
    val response = match op
      "emit" ->
        val et = extract-type(line)
        val (event, _new-count) = emit-event("ipc", et, "{}", 1.0, event-count)
        json-event-response(event)
      "count" ->
        json-response("count", show(event-count))
      "reset" ->
        json-response("reset", show(event-count))
      "cascade" ->
        val et = extract-type(line)
        val trigger = check-cascade(et)
        "{\"type\":\"" ++ event-type-to-string(trigger.event-type) ++ 
        "\",\"handlers\":" ++ show(trigger.handler-count) ++
        ",\"priority\":" ++ show(trigger.priority) ++ "}"
      "status" ->
        "{\"status\":\"ok\",\"events\":" ++ show(event-count) ++ "}"
      "ping" ->
        "{\"pong\":true}"
      "invoke-gana" ->
        "{\"status\":\"ok\",\"result\":\"gana invoked\"}"
      "route-prat" ->
        "{\"status\":\"ok\",\"routed\":true}"
      _ ->
        "{\"error\":\"unknown_operation\"}"
        
    println(response)
    flush-stdout()
    
    val next-count = match op
      "emit" -> event-count + 1
      "reset" -> 0
      _ -> event-count
      
    if op != "quit" then server-loop(next-count) else ()
    
fun main(): io ()
  with handler
    final ctl throw-exn(exn)
      () // Catch EOF globally
  println("{\"status\":\"started\",\"component\":\"gan_ying\"}")
  flush-stdout()
  server-loop(0)
