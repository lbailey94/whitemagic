module unified_fast_brain

import std/os/readline
import std/num/int64
import std/core/int
import std/core/string
import std/core/list
import std/core/delayed
import std/num/float64


extern import
  c file "unified_fast_brain.h"


extern get-time-ms(): float64
  c "kk_unified_time_ms"

extern shm-ring-open(name: string, size: int): int64
  c "kk_unified_ring_open"

extern shm-ring-poll(addr: int64): string
  c "kk_unified_ring_poll"

extern shm-embed-open(name: string): int64
  c "kk_unified_embed_open"
  
extern shm-embed-search(addr: int64): int
  c "kk_unified_embed_search"

extern shm-graph-open(name: string, size: int): int64
  c "kk_unified_graph_open"
  
extern shm-graph-walk(addr: int64, start-id: int, hops: int): string
  c "kk_unified_graph_walk"

extern flush-stdout() : console ()
  c inline "fflush(stdout)"

extern sleep-us(us: int): ()
  c inline "usleep(kk_integer_clamp32(us, kk_context()))"

val ring-name = "/whitemagic_event_ring"
val ring-size = 64 + (65536 * 256)

val embed-name = "/whitemagic_embed_bridge_real"

val graph-name = "/whitemagic_graph_bridge"
val graph-size = 64 + (3000000 * 16)

// --- PRAT Routing Core ---
// We define a basic effect to handle tool dispatch natively in Koka
effect prat-route
  fun dispatch-tool(tool-name: string, args: string): string

// A basic handler for the PRAT route effect that routes to the correct Gana
fun with-prat-router(action: () -> <prat-route|e> a): e a
  with handler
    fun dispatch-tool(tool, args)
      val gana = route-to-gana(tool)
      "{\"status\":\"routed\", \"gana\":\"" ++ gana ++ "\", \"tool\":\"" ++ tool ++ "\"}"
  action()

// PRAT Tool Router via Koka Effect matching
fun route-to-gana(tool: string) : string
  match tool
    "session_bootstrap" -> "gana_horn"
    "create_memory" -> "gana_neck"
    "update_memory" -> "gana_neck"
    "search_memories" -> "gana_winnowing_basket"
    "vector_search" -> "gana_winnowing_basket"
    "hybrid_recall" -> "gana_winnowing_basket"
    "graph_walk" -> "gana_winnowing_basket"
    "health_report" -> "gana_root"
    "gnosis" -> "gana_ghost"
    "dream" -> "gana_abundance"
    "ensemble" -> "gana_three_stars"
    "galactic_dashboard" -> "gana_void"
    "check" -> "gana_root"
    "manifest" -> "gana_ghost"
    "capabilities" -> "gana_ghost"
    "recall" -> "gana_winnowing_basket"
    _ -> "gana_unknown"

fun handle-event(ring-addr: int64, embed-addr: int64, graph-addr: int64, event: string) : <io,prat-route> ()
  val start-time = get-time-ms()
  if event.contains("\"query\":") && embed-addr != std/num/int64/int64(0) && graph-addr != std/num/int64/int64(0) then
    val start-id = shm-embed-search(embed-addr)
    val graph-res = shm-graph-walk(graph-addr, start-id, 3)
    val end-time = get-time-ms()
    val dur = show(end-time - start-time) ++ "ms"
    println("{\"status\":\"system_resonance_achieved\", \"latency\":\"" ++ dur ++ "\", \"input_event\":" ++ event ++ ", \"context\":" ++ graph-res ++ "}")
    flush-stdout()
  elif event.contains("\"prat_route\":") then
    val tool = if event.contains("search_memories") then "search_memories" else (if event.contains("create_memory") then "create_memory" else "unknown")
    val res = dispatch-tool(tool, "{}")
    val end-time = get-time-ms()
    val dur = show(end-time - start-time) ++ "ms"
    println("{\"status\":\"prat_routed\", \"latency\":\"" ++ dur ++ "\", \"result\":" ++ res ++ "}")
    flush-stdout()
  else
    val end-time = get-time-ms()
    val dur = show(end-time - start-time) ++ "ms"
    println("{\"status\":\"telemetry_processed\", \"latency\":\"" ++ dur ++ "\", \"input_event\":" ++ event ++ "}")
    flush-stdout()

fun server-loop(ring-addr: int64, embed-addr: int64, graph-addr: int64) : io ()
  with handler
    final ctl throw-exn(exn)
      () // Catch EOF globally
  
  val event = shm-ring-poll(ring-addr)
  if event != "" then
    with-prat-router
      handle-event(ring-addr, embed-addr, graph-addr, event)
    server-loop(ring-addr, embed-addr, graph-addr)
  else
    sleep-us(1000)
    server-loop(ring-addr, embed-addr, graph-addr)

fun main() : io ()
  with handler
    final ctl throw-exn(exn)
      () // Catch EOF globally
      
  println("{\"status\":\"starting\",\"unified_fast_brain\":true}")
  flush-stdout()
  
  val ring = shm-ring-open(ring-name, ring-size)
  val embed = shm-embed-open(embed-name)
  val graph = shm-graph-open(graph-name, graph-size)
  
  if ring == std/num/int64/int64(0) then
    println("{\"error\":\"failed to open event ring\"}")
    flush-stdout()
  else
    if graph == std/num/int64/int64(0) then
      println("{\"error\":\"failed to open graph topology\"}")
      flush-stdout()
    println("{\"status\":\"started\",\"connected\":true}")
    flush-stdout()
    server-loop(ring, embed, graph)
