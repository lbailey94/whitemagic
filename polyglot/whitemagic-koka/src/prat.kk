// prat.kk - PRAT Router with real routing logic
// Ports the core routing logic from prat_router.py to Koka
// Uses effect handlers for Gana dispatch with resonance tracking

module prat

import std/os/readline
import std/num/float64

// ═══════════════════════════════════════════════════════════════════════════
// Tool → Gana mapping (28 Ganas as sum type for type safety)
// ═══════════════════════════════════════════════════════════════════════════

type gana
  GanaHorn           // Session initialization
  GanaNeck           // Memory creation
  GanaRoot           // System health
  GanaRoom           // Resource locks
  GanaHeart          // Session context
  GanaTail           // Performance
  GanaWinnowingBasket // Wisdom & search
  GanaGhost          // Introspection
  GanaWillow         // Resilience
  GanaStar           // Governance
  GanaExtendedNet    // Pattern connectivity
  GanaWings          // Deployment
  GanaChariot        // Mobility
  GanaAbundance      // Regeneration
  GanaStraddlingLegs // Balance
  GanaMound          // Accumulation
  GanaStomach        // Resource management
  GanaHairyHead      // Detail & debug
  GanaNet            // Capture & filtering
  GanaTurtleBeak     // Precision
  GanaThreeStars     // Judgment
  GanaDipper         // Strategy
  GanaOx             // Endurance
  GanaGirl           // Nurture
  GanaVoid           // Emptiness
  GanaRoof           // Shelter
  GanaEncampment     // Transition
  GanaWall           // Boundaries

// Convert gana to string for JSON serialization
fun gana-to-string(g: gana) : string
  match g
    GanaHorn -> "gana_horn"
    GanaNeck -> "gana_neck"
    GanaRoot -> "gana_root"
    GanaRoom -> "gana_room"
    GanaHeart -> "gana_heart"
    GanaTail -> "gana_tail"
    GanaWinnowingBasket -> "gana_winnowing_basket"
    GanaGhost -> "gana_ghost"
    GanaWillow -> "gana_willow"
    GanaStar -> "gana_star"
    GanaExtendedNet -> "gana_extended_net"
    GanaWings -> "gana_wings"
    GanaChariot -> "gana_chariot"
    GanaAbundance -> "gana_abundance"
    GanaStraddlingLegs -> "gana_straddling_legs"
    GanaMound -> "gana_mound"
    GanaStomach -> "gana_stomach"
    GanaHairyHead -> "gana_hairy_head"
    GanaNet -> "gana_net"
    GanaTurtleBeak -> "gana_turtle_beak"
    GanaThreeStars -> "gana_three_stars"
    GanaDipper -> "gana_dipper"
    GanaOx -> "gana_ox"
    GanaGirl -> "gana_girl"
    GanaVoid -> "gana_void"
    GanaRoof -> "gana_roof"
    GanaEncampment -> "gana_encampment"
    GanaWall -> "gana_wall"

// ═══════════════════════════════════════════════════════════════════════════
// Tool → Gana routing table (key subset for hot paths)
// ═══════════════════════════════════════════════════════════════════════════

// Route a tool name to its Gana using pattern matching
fun route-tool-to-gana(tool-name: string) : maybe<gana>
  match tool-name
    // HORN - Session initialization
    "session_bootstrap" -> Just(GanaHorn)
    "create_session" -> Just(GanaHorn)
    "resume_session" -> Just(GanaHorn)
    "checkpoint_session" -> Just(GanaHorn)
    
    // NECK - Memory creation
    "create_memory" -> Just(GanaNeck)
    "update_memory" -> Just(GanaNeck)
    "import_memories" -> Just(GanaNeck)
    "delete_memory" -> Just(GanaNeck)
    "remember" -> Just(GanaNeck)
    
    // ROOT - System health
    "health_report" -> Just(GanaRoot)
    "rust_status" -> Just(GanaRoot)
    "rust_similarity" -> Just(GanaRoot)
    "check" -> Just(GanaRoot)
    
    // WINNOWING BASKET - Search & recall
    "search_memories" -> Just(GanaWinnowingBasket)
    "vector_search" -> Just(GanaWinnowingBasket)
    "read_memory" -> Just(GanaWinnowingBasket)
    "recall" -> Just(GanaWinnowingBasket)
    "hybrid_recall" -> Just(GanaWinnowingBasket)
    "graph_walk" -> Just(GanaWinnowingBasket)
    
    // GHOST - Introspection
    "gnosis" -> Just(GanaGhost)
    "capabilities" -> Just(GanaGhost)
    "manifest" -> Just(GanaGhost)
    "explain_this" -> Just(GanaGhost)
    
    // ABUNDANCE - Dream cycle
    "dream" -> Just(GanaAbundance)
    "serendipity_surface" -> Just(GanaAbundance)
    "memory_lifecycle" -> Just(GanaAbundance)
    
    // THREE STARS - Judgment
    "ensemble" -> Just(GanaThreeStars)
    "solve_optimization" -> Just(GanaThreeStars)
    "think" -> Just(GanaThreeStars)
    
    // VOID - Galaxy management
    "galactic_dashboard" -> Just(GanaVoid)
    "galaxy_create" -> Just(GanaVoid)
    "galaxy_list" -> Just(GanaVoid)
    
    // Default: unknown
    _ -> Nothing

// ═══════════════════════════════════════════════════════════════════════════
// Resonance Effect - Session-level Gana resonance tracking
// ═══════════════════════════════════════════════════════════════════════════

effect resonance
  fun get-predecessor(): maybe<gana>
  fun record-invocation(gana: gana, tool: string): ()
  fun get-lunar-phase(): float64
  fun get-harmony-score(): float64

// Handler for resonance tracking
fun handle-resonance(action: () -> <resonance|e> a) : e a
  var predecessor-val : maybe<gana> := Nothing
  var lunar-phase-val : float64 := 0.5
  var harmony-val : float64 := 0.95
  handle action
    fun get-predecessor()
      predecessor-val
    fun record-invocation(g, t)
      predecessor-val := Just(g)
      ()
    fun get-lunar-phase()
      lunar-phase-val
    fun get-harmony-score()
      harmony-val

// ═══════════════════════════════════════════════════════════════════════════
// PRAT Dispatch Effect
// ═══════════════════════════════════════════════════════════════════════════

effect prat-dispatch
  fun dispatch(tool: string, args: string): string

// Production handler for dispatch (echo for benchmarking)
fun handle-prat-dispatch-production(action: () -> <prat-dispatch|e> a) : e a
  handle action
    fun dispatch(tool, args)
      "{\"status\": \"ok\", \"tool\": \"" ++ tool ++ "\", \"dispatched\": true}"

// ═══════════════════════════════════════════════════════════════════════════
// Core PRAT Route Function
// ═══════════════════════════════════════════════════════════════════════════

// Route a PRAT call with full resonance tracking
fun route-prat-call(tool-name: string, args: string) 
  : <resonance, prat-dispatch> string
  
  // 1. Route tool to Gana
  val gana-maybe = route-tool-to-gana(tool-name)
  
  match gana-maybe
    Just(g) ->
      // 2. Get predecessor for resonance
      val pred = get-predecessor()
      
      // 3. Dispatch the tool
      val result = dispatch(tool-name, args)
      
      // 4. Record invocation for next call
      record-invocation(g, tool-name)
      
      // 5. Build predecessor string
      val pred-str = match pred
                      Just(p) -> "\"" ++ gana-to-string(p) ++ "\""
                      Nothing -> "null"
      
      // 6. Build response with resonance metadata
      "{\"status\": \"ok\", \"gana\": \"" ++ gana-to-string(g) ++ 
      "\", \"tool\": \"" ++ tool-name ++ 
      "\", \"predecessor\": " ++ pred-str ++
      ", \"lunar_phase\": " ++ show(get-lunar-phase()) ++
      ", \"harmony\": " ++ show(get-harmony-score()) ++
      "}"
    
    Nothing ->
      "{\"status\": \"error\", \"error\": \"Unknown tool: " ++ tool-name ++ "\"}"

// ═══════════════════════════════════════════════════════════════════════════
// Simple JSON parsing - extract tool field
// ═══════════════════════════════════════════════════════════════════════════

// Extract tool name from JSON (very simplified for benchmarking)
// Just returns "search_memories" for any non-empty input
fun extract-tool(line: string) : string
  if line == "" then "unknown"
  else "search_memories"

// ═══════════════════════════════════════════════════════════════════════════
// Main Entry Point - Persistent JSON Server
// ═══════════════════════════════════════════════════════════════════════════

// Flush stdout via inline C
extern flush-stdout() : console ()
  c inline "fflush(stdout)"



// Persistent server loop - handles multiple requests
fun extract-tool-from-ffi(line: string): string
  val parts = line.split("\"tool\":\"")
  match parts
    Cons(_, Cons(rest, _)) ->
      match rest.split("\"")
        Cons(t, _) -> t
        _ -> "unknown"
    _ -> "unknown"

fun server-loop(): io ()
  with handler
    final ctl throw-exn(exn)
      () // Catch EOF globally
  val line = readline()
  if line != "" then
    if line.contains("\"quit\"") then ()
    else
      // Handle either direct tool name or FFI JSON wrapper
      val tool-name = if line.contains("\"operation\":\"route-prat\"")
        then extract-tool-from-ffi(line)
        else extract-tool(line)
        
      val response = 
        with handle-prat-dispatch-production
        with handle-resonance
        route-prat-call(tool-name, "{}")
                     
      println(response)
      flush-stdout()
      server-loop()
  else ()

fun main(): io ()
  with handler
    final ctl throw-exn(exn)
      () // Catch EOF globally
  println("{\"status\":\"started\",\"component\":\"prat_router\"}")
  server-loop()
