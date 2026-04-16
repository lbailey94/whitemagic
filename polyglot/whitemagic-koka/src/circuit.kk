// circuit.kk - Circuit Breaker with persistent IPC server

module circuit

import std/os/readline

// ═══════════════════════════════════════════════════════════════════════════
// Circuit Breaker Types
// ═══════════════════════════════════════════════════════════════════════════

type circuit-state
  Closed
  Open
  HalfOpen

fun state-to-string(s: circuit-state) : string
  match s
    Closed -> "closed"
    Open -> "open"
    HalfOpen -> "half-open"

// ═══════════════════════════════════════════════════════════════════════════
// Circuit Operations - pure functions
// ═══════════════════════════════════════════════════════════════════════════

fun check-state(st: circuit-state, failures: int, successes: int, tick: int, last-fail: int) : string
  val threshold = 5
  val timeout-ms = 30000
  val half-max = 3
  
  match st
    Closed ->
      if failures >= threshold then "open"
      else "closed"
    Open ->
      val elapsed = tick - last-fail
      if elapsed > timeout-ms then "half-open"
      else "open"
    HalfOpen ->
      if successes >= half-max then "closed"
      else "half-open"

// ═══════════════════════════════════════════════════════════════════════════
// Request Parsing
// ═══════════════════════════════════════════════════════════════════════════

fun extract-op(line: string) : string
  if line == "" then "unknown"
  else if line.contains("\"check\"") then "check"
  else if line.contains("\"success\"") then "success"
  else if line.contains("\"failure\"") then "failure"
  else if line.contains("\"reset\"") then "reset"
  else if line.contains("\"status\"") then "status"
  else "unknown"

// ═══════════════════════════════════════════════════════════════════════════
// Main Entry Point - State passed through recursion
// ═══════════════════════════════════════════════════════════════════════════

extern flush-stdout() : console ()
  c inline "fflush(stdout)"

fun main(): io ()
  server-loop(0, Closed, 0, 0, 0, 0)

fun server-loop(tick: int, st: circuit-state, failures: int, successes: int, last-fail: int, total: int) : io ()
  val line = readline()
  if line != "" then
    val new-tick = tick + 1
    val op = extract-op(line)
    
    val response = match op
      "check" -> 
        "{\"operation\": \"check\", \"state\": \"" ++ check-state(st, failures, successes, new-tick, last-fail) ++ "\"}"
      
      "success" ->
        match st
          Closed ->
            "{\"operation\": \"success\", \"result\": \"ok\"}"
          HalfOpen ->
            "{\"operation\": \"success\", \"result\": \"ok\"}"
          Open ->
            "{\"operation\": \"success\", \"result\": \"ok\"}"
      
      "failure" ->
        match st
          Closed ->
            "{\"operation\": \"failure\", \"result\": \"ok\"}"
          HalfOpen ->
            "{\"operation\": \"failure\", \"result\": \"ok\"}"
          Open ->
            "{\"operation\": \"failure\", \"result\": \"ok\"}"
      
      "reset" ->
        "{\"operation\": \"reset\", \"result\": \"ok\"}"
      
      "status" ->
        "{\"state\": \"" ++ state-to-string(st) ++
         "\", \"failures\": " ++ show(failures) ++
         ", \"successes\": " ++ show(successes) ++
         ", \"total_calls\": " ++ show(total) ++
         ", \"tick\": " ++ show(new-tick) ++
         "}"
      
      _ ->
        "{\"error\": \"unknown_operation\"}"
    
    // Calculate next state based on operation
    val next-state = match op
      "success" ->
        match st
          HalfOpen ->
            val new-s = successes + 1
            if new-s >= 3 then Closed else HalfOpen
          _ -> st
      "failure" ->
        match st
          Closed ->
            val new-f = failures + 1
            if new-f >= 5 then Open else Closed
          HalfOpen -> Open
          _ -> st
      "reset" -> Closed
      _ -> st
    
    val next-failures = match op
      "success" -> 0
      "failure" -> failures + 1
      "reset" -> 0
      _ -> failures
    
    val next-successes = match op
      "success" -> successes + 1
      "failure" -> 0
      "reset" -> 0
      _ -> successes
    
    val next-last-fail = match op
      "failure" -> new-tick
      "reset" -> 0
      _ -> last-fail
    
    val next-total = total + 1
    
    println(response)
    flush-stdout()
    server-loop(new-tick, next-state, next-failures, next-successes, next-last-fail, next-total)
  else
    ()
