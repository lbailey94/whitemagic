// disinhibition.kk — Koka bridge for sleep/wake state-dependent gating
//
// Implements a state machine: Wake → LightSleep → DeepSleep → REM
// Each state modulates galaxy gating weights differently:
//   Wake:       full gating (all galaxies accessible)
//   LightSleep: reduced gating (sessions/citta dampened, consolidation begins)
//   DeepSleep:  minimal gating (only consolidation pathways active)
//   REM:        creative gating (dreams/aria boosted, codex dampened)
//
// Based on PLOS Comp Bio 2025: "Sleep-modulated disinhibition enables replay
// for memory consolidation."

module disinhibition

import std/os/readline
import std/num/float64

extern flush-stdout() : console ()
  c inline "fflush(stdout)"

// State definitions
fun state-name(s: int) : string
  match s
    0 -> "Wake"
    1 -> "LightSleep"
    2 -> "DeepSleep"
    3 -> "REM"
    _ -> "Unknown"

// Galaxy gating weights per state
// Returns JSON fragment: "galaxy": weight
fun state-weights(s: int) : string
  match s
    0 -> // Wake: full access
      "\"universal\": 1.0, \"codex\": 1.0, \"sessions\": 1.0, \"citta\": 1.0, \"dreams\": 1.0, \"research\": 1.0, \"aria\": 1.0, \"journals\": 1.0, \"substrate\": 1.0, \"tutorial\": 1.0"
    1 -> // LightSleep: consolidation begins
      "\"universal\": 0.7, \"codex\": 0.8, \"sessions\": 0.3, \"citta\": 0.4, \"dreams\": 0.6, \"research\": 0.5, \"aria\": 0.6, \"journals\": 0.4, \"substrate\": 0.5, \"tutorial\": 0.3"
    2 -> // DeepSleep: only consolidation pathways
      "\"universal\": 0.3, \"codex\": 0.6, \"sessions\": 0.1, \"citta\": 0.2, \"dreams\": 0.3, \"research\": 0.4, \"aria\": 0.3, \"journals\": 0.2, \"substrate\": 0.3, \"tutorial\": 0.1"
    3 -> // REM: creative boosting
      "\"universal\": 0.6, \"codex\": 0.3, \"sessions\": 0.2, \"citta\": 0.8, \"dreams\": 1.5, \"research\": 0.5, \"aria\": 1.3, \"journals\": 0.7, \"substrate\": 0.4, \"tutorial\": 0.3"
    _ -> "\"universal\": 1.0"

// Disinhibition level per state (0=full inhibition, 1=full disinhibition)
fun disinhibition-level(s: int) : float64
  match s
    0 -> 1.0   // Wake: full disinhibition (full cognitive access)
    1 -> 0.5   // LightSleep: partial disinhibition
    2 -> 0.2   // DeepSleep: strong inhibition (only consolidation)
    3 -> 0.7   // REM: high disinhibition (creative associations)
    _ -> 1.0

// Transition state machine
fun next-state(current: int) : int
  match current
    0 -> 1  // Wake → LightSleep
    1 -> 2  // LightSleep → DeepSleep
    2 -> 3  // DeepSleep → REM
    3 -> 0  // REM → Wake
    _ -> 0

// Build response JSON
fun state-response(s: int) : string
  val name = state-name(s)
  val level = disinhibition-level(s)
  val weights = state-weights(s)
  "{\"status\": \"ok\", \"state\": \"" ++ name ++ "\", \"state_code\": " ++ s.show ++ ", \"disinhibition_level\": " ++ level.show ++ ", \"weights\": {" ++ weights ++ "}}"

// Dispatch
fun dispatch(line: string, state: int) : (string, int)
  if line.contains("\"method\": \"ping\"") then
    ("{\"status\": \"ok\", \"backend\": \"koka-disinhibition\"}", state)
  else if line.contains("\"method\": \"get_state\"") then
    (state-response(state), state)
  else if line.contains("\"method\": \"transition\"") then
    val new_state = next-state(state)
    (state-response(new_state), new_state)
  else if line.contains("\"method\": \"set_state\"") then
    // Parse state from input (simple substring search)
    val new_state = if line.contains("\"state\": 0") then 0
                    else if line.contains("\"state\": 1") then 1
                    else if line.contains("\"state\": 2") then 2
                    else if line.contains("\"state\": 3") then 3
                    else state
    (state-response(new_state), new_state)
  else if line.contains("\"method\": \"get_weights\"") then
    val weights = state-weights(state)
    ("{\"status\": \"ok\", \"weights\": {" ++ weights ++ "}}", state)
  else
    ("{\"status\": \"error\", \"error\": \"unknown method\"}", state)

fun server-loop(state: int): io ()
  val line = readline()
  if line != "" then
    val (response, new_state) = dispatch(line, state)
    println(response)
    flush-stdout()
    server-loop(new_state)
  else
    ()

fun main(): io ()
  println("{\"status\": \"started\", \"backend\": \"koka-disinhibition\"}")
  flush-stdout()
  server-loop(0)  // Start in Wake state
  ()
