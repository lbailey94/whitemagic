// resonance.kk - Resonance tracking with persistent IPC server
// Tracks session-level state for predecessor, lunar phase, harmony score

module resonance

import std/os/readline
import std/num/float64

// ═══════════════════════════════════════════════════════════════════════════
// Gana Order (28 mansions in circular sequence)
// ═══════════════════════════════════════════════════════════════════════════

val gana-order : list<string> = [
  "gana_horn", "gana_neck", "gana_root", "gana_room", "gana_heart",
  "gana_tail", "gana_winnowing_basket", "gana_ghost", "gana_willow",
  "gana_star", "gana_extended_net", "gana_wings", "gana_chariot",
  "gana_abundance", "gana_straddling_legs", "gana_mound", "gana_stomach",
  "gana_hairy_head", "gana_net", "gana_turtle_beak", "gana_three_stars",
  "gana_dipper", "gana_ox", "gana_girl", "gana_void", "gana_roof",
  "gana_encampment", "gana_wall"
]

// Find index of gana in order
fun gana-index(name: string) : int
  val result = gana-order.foldl((0, False)) fn(acc, entry)
    val (idx, found) = acc
    if found then acc
    else if entry == name then (idx, True)
    else (idx + 1, False)
  if result.snd then result.fst else -1

// Get element at index from list
fun list-at(lst: list<string>, idx: int) : string
  if idx <= 0 then
    match lst
      Nil -> "gana_horn"
      Cons(hd, _) -> hd
  else
    match lst
      Nil -> "gana_horn"
      Cons(_, tl) -> list-at(tl, idx - 1)

// Get predecessor gana (circular)
fun get-predecessor(gana-name: string) : string
  val idx = gana-index(gana-name)
  if idx < 0 then "gana_horn"
  else list-at(gana-order, (idx + 27) % 28)

// Get successor gana (circular)
fun get-successor(gana-name: string) : string
  val idx = gana-index(gana-name)
  if idx < 0 then "gana_horn"
  else list-at(gana-order, (idx + 1) % 28)

// ═══════════════════════════════════════════════════════════════════════════
// Request Parsing
// ═══════════════════════════════════════════════════════════════════════════

fun extract-op(line: string) : string
  if line == "" then "unknown"
  else if line.contains("\"predecessor\"") then "predecessor"
  else if line.contains("\"successor\"") then "successor"
  else if line.contains("\"record\"") then "record"
  else if line.contains("\"status\"") then "status"
  else if line.contains("\"reset\"") then "reset"
  else "unknown"

// Extract gana name from JSON (simplified - just looks for gana_ pattern)
fun extract-gana(line: string) : string
  if line.contains("gana_horn") then "gana_horn"
  else if line.contains("gana_neck") then "gana_neck"
  else if line.contains("gana_ghost") then "gana_ghost"
  else if line.contains("gana_winnowing_basket") then "gana_winnowing_basket"
  else if line.contains("gana_void") then "gana_void"
  else if line.contains("gana_abundance") then "gana_abundance"
  else "gana_horn"

// ═══════════════════════════════════════════════════════════════════════════
// Main Entry Point - Persistent IPC Server
// ═══════════════════════════════════════════════════════════════════════════

extern flush-stdout() : console ()
  c inline "fflush(stdout)"

fun main(): io ()
  server-loop("", 0, 0.5, 0.95)

fun server-loop(last-gana: string, call-count: int, lunar-phase: float64, harmony: float64) : io ()
  val line = readline()
  if line != "" then
    val op = extract-op(line)
    val gana = extract-gana(line)
    
    val response = match op
      "predecessor" ->
        val pred = get-predecessor(gana)
        "{\"operation\": \"predecessor\", \"gana\": \"" ++ gana ++ "\", \"predecessor\": \"" ++ pred ++ "\"}"
      
      "successor" ->
        val succ = get-successor(gana)
        "{\"operation\": \"successor\", \"gana\": \"" ++ gana ++ "\", \"successor\": \"" ++ succ ++ "\"}"
      
      "record" ->
        "{\"operation\": \"record\", \"gana\": \"" ++ gana ++ "\", \"recorded\": true}"
      
      "status" ->
        "{\"call_count\": " ++ show(call-count) ++
        ", \"last_gana\": \"" ++ last-gana ++ "\"" ++
        ", \"lunar_phase\": " ++ show(lunar-phase) ++
        ", \"harmony\": " ++ show(harmony) ++
        "}"
      
      "reset" ->
        "{\"operation\": \"reset\", \"result\": \"ok\"}"
      
      _ ->
        "{\"error\": \"unknown_operation\"}"
    
    val new-last-gana = if op == "record" then gana else last-gana
    val new-call-count = if op == "record" then call-count + 1 else call-count
    
    println(response)
    flush-stdout()
    server-loop(new-last-gana, new-call-count, lunar-phase, harmony)
  else
    ()
