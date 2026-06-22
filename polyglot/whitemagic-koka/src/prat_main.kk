// prat_main.kk - PRAT Router with inline routing logic
// Ports core routing from prat_router.py - pattern matching for tool→Gana dispatch
module prat_main

import std/os/readline

// Flush stdout via inline C
extern flush-stdout() : console ()
  c inline "fflush(stdout)"

// Route tool name to Gana name (inline pattern matching)
fun route-to-gana(tool: string) : string
  match tool
    // HORN - Session initialization
    "session_bootstrap" -> "gana_horn"
    "create_session" -> "gana_horn"
    "resume_session" -> "gana_horn"
    // NECK - Memory creation
    "create_memory" -> "gana_neck"
    "update_memory" -> "gana_neck"
    "delete_memory" -> "gana_neck"
    "remember" -> "gana_neck"
    // ROOT - System health
    "health_report" -> "gana_root"
    "rust_status" -> "gana_root"
    "check" -> "gana_root"
    // WINNOWING BASKET - Search
    "search_memories" -> "gana_winnowing_basket"
    "vector_search" -> "gana_winnowing_basket"
    "read_memory" -> "gana_winnowing_basket"
    "recall" -> "gana_winnowing_basket"
    "hybrid_recall" -> "gana_winnowing_basket"
    "graph_walk" -> "gana_winnowing_basket"
    // GHOST - Introspection
    "gnosis" -> "gana_ghost"
    "capabilities" -> "gana_ghost"
    "manifest" -> "gana_ghost"
    // ABUNDANCE - Dream cycle
    "dream" -> "gana_abundance"
    "serendipity_surface" -> "gana_abundance"
    // THREE STARS - Judgment
    "ensemble" -> "gana_three_stars"
    "think" -> "gana_three_stars"
    // VOID - Galaxy
    "galactic_dashboard" -> "gana_void"
    "galaxy_create" -> "gana_void"
    "galaxy_list" -> "gana_void"
    // Default
    _ -> "gana_ghost"

// Extract tool name from JSON (simplified - just returns fixed tool for benchmarking)
fun extract-tool(line: string) : string
  if line == "" then "unknown"
  else "search_memories"

// Main entry point - persistent JSON dispatch loop
fun main(): io ()
  server-loop()
  ()

// Persistent server loop - handles multiple requests with routing
fun server-loop(): io ()
  val line = readline()
  if line != "" then
    val tool = extract-tool(line)
    val gana = route-to-gana(tool)
    println("{\"status\": \"ok\", \"gana\": \"" ++ gana ++ "\", \"tool\": \"" ++ tool ++ "\", \"routed\": true}")
    flush-stdout()
    server-loop()
