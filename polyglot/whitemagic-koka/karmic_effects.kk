// karmic_effects.kk — MandalaOS Phase C: Koka effect signature types and comparison
//
// Defines the effect-sig struct and karmic-result that Koka uses
// for compile-time effect tracking. The IPC server accepts tool dispatch
// requests with declared effects, compares them against actual effects,
// and returns mismatch information + debt calculation.

module karmic_effects

import std/os/readline
import std/num/float64

// ── Effect Types ──────────────────────────────────────────────────────────────

type effect-type
  Pure
  Local
  Network
  Destructive
  Observation

fun effect-type-to-string(et: effect-type): string
  match et
    Pure -> "pure"
    Local -> "local"
    Network -> "network"
    Destructive -> "destructive"
    Observation -> "observation"

fun string-to-effect-type(s: string): effect-type
  if s == "pure" then Pure
  else if s == "local" then Local
  else if s == "network" then Network
  else if s == "destructive" then Destructive
  else if s == "observation" then Observation
  else Pure

// ── Effect Signature ──────────────────────────────────────────────────────────

struct effect-sig
  effect-type: effect-type
  target: string
  declared: bool

// ── Karmic Result ─────────────────────────────────────────────────────────────

struct karmic-result
  output: string
  actual-effects: list<effect-sig>
  mismatch: bool
  debt: float64
  mismatches: list<string>

// ── Effect Comparison ─────────────────────────────────────────────────────────

// Check if an effect type is "more severe" than another
fun is-more-severe(a: effect-type, b: effect-type): bool
  fun rank(et: effect-type): int
    match et
      Pure -> 0
      Observation -> 1
      Local -> 2
      Network -> 3
      Destructive -> 4
  rank(a) > rank(b)

// Debt weight for an undeclared effect type
fun debt-for-undeclared(et: effect-type): float64
  match et
    Destructive -> 2.0
    Network -> 1.5
    Local -> 1.0
    Observation -> 0.0
    Pure -> 0.0

// Compare declared vs actual effect lists
// Returns (mismatch, total_debt, mismatch_descriptions)
fun compare-effects(declared: list<effect-sig>, actual: list<effect-sig>): (bool, float64, list<string>)
  // Check for undeclared effects (in actual but not in declared by type)
  fun has-declared-type(et: effect-type, sigs: list<effect-sig>): bool
    match sigs
      Nil -> False
      Cons(sig, rest) ->
        if sig.effect-type == et then True
        else has-declared-type(et, rest)

  fun check-undeclared(actuals: list<effect-sig>, debt: float64, mismatches: list<string>): (float64, list<string>)
    match actuals
      Nil -> (debt, mismatches)
      Cons(sig, rest) ->
        if not(has-declared-type(sig.effect-type, declared)) and sig.effect-type != Pure and sig.effect-type != Observation then
          val d = debt-for-undeclared(sig.effect-type)
          val msg = "Undeclared " ++ effect-type-to-string(sig.effect-type) ++ " effect"
          check-undeclared(rest, debt + d, Cons(msg, mismatches))
        else
          check-undeclared(rest, debt, mismatches)

  // Check for declared but not actualized (no-op)
  fun check-noop(declared-sigs: list<effect-sig>, debt: float64, mismatches: list<string>): (float64, list<string>)
    match declared-sigs
      Nil -> (debt, mismatches)
      Cons(sig, rest) ->
        if not(has-declared-type(sig.effect-type, actual)) and sig.declared and sig.effect-type != Pure and sig.effect-type != Observation then
          check-noop(rest, debt + 0.1, Cons("Declared " ++ effect-type-to-string(sig.effect-type) ++ " but no effect observed", mismatches))
        else
          check-noop(rest, debt, mismatches)

  val (debt1, mismatches1) = check-undeclared(actual, 0.0, [])
  val (total-debt, all-mismatches) = check-noop(declared, debt1, mismatches1)
  (total-debt > 0.0, total-debt, all-mismatches)

// ── JSON Helpers ──────────────────────────────────────────────────────────────

fun extract-field(line: string, field: string): string
  val marker = "\"" ++ field ++ "\":\""
  val start = line.find(marker)
  if start < 0 then ""
  else
    val val-start = start + marker.length
    val val-end = line.find_from("\"", val-start)
    if val-end < 0 then ""
    else line.substring(val-start, val-end)

fun extract-field-int(line: string, field: string): int
  val marker = "\"" ++ field ++ "\":"
  val start = line.find(marker)
  if start < 0 then 0
  else
    val val-start = start + marker.length
    val rest = line.substring(val-start, line.length)
    // Parse leading digits
    fun parse-digits(s: string, acc: string): string
      if s.length == 0 then acc
      else
        val c = s[0]
        if c >= '0' and c <= '9' then parse-digits(s.substring(1, s.length), acc ++ string(c))
        else acc
    val digits = parse-digits(rest, "")
    if digits == "" then 0
    else
      match int-parse(digits)
        Just(n) -> n
        Nothing -> 0

fun extract-field-bool(line: string, field: string): bool
  val marker = "\"" ++ field ++ "\":"
  val start = line.find(marker)
  if start < 0 then False
  else
    val val-start = start + marker.length
    val rest = line.substring(val-start, line.length)
    rest.startswith("true")

// Extract effect types from a JSON array like "declared_effects":[{"effect_type":"local",...}]
fun extract-effect-types(line: string, field: string): list<effect-type]
  val marker = "\"" ++ field ++ "\":["
  val start = line.find(marker)
  if start < 0 then []
  else
    val arr-start = start + marker.length
    val arr-end = line.find_from("]", arr-start)
    if arr-end < 0 then []
    else
      val arr = line.substring(arr-start, arr-end)
      // Find all "effect_type":"xxx" within the array
      fun find-types(s: string, types: list<effect-type>): list<effect-type>
        val et-marker = "\"effect_type\":\""
        val pos = s.find(et-marker)
        if pos < 0 then types
        else
          val et-start = pos + et-marker.length
          val et-end = s.find_from("\"", et-start)
          if et-end < 0 then types
          else
            val et-name = s.substring(et-start, et-end)
            val et = string-to-effect-type(et-name)
            find-types(s.substring(et-end + 1, s.length), Cons(et, types))
      find-types(arr, [])

// ── IPC Server ───────────────────────────────────────────────────────────────

fun extract-op(line: string): string
  if line.contains("\"compare\"") then "compare"
  else if line.contains("\"dispatch\"") then "dispatch"
  else if line.contains("\"status\"") then "status"
  else if line.contains("\"quit\"") then "quit"
  else "unknown"

fun json-effect-sig(sig: effect-sig): string
  "{\"effect_type\":\"" ++ effect-type-to-string(sig.effect-type) ++
  "\",\"target\":\"" ++ sig.target ++
  "\",\"declared\":" ++ (if sig.declared then "true" else "false") ++ "}"

fun json-effect-list(effects: list<effect-sig>): string
  fun join(sigs: list<effect-sig>, acc: string): string
    match sigs
      Nil -> acc
      Cons(sig, Nil) -> acc ++ json-effect-sig(sig)
      Cons(sig, rest) -> join(rest, acc ++ json-effect-sig(sig) ++ ",")
  "[" ++ join(effects, "") ++ "]"

fun json-mismatches(mismatches: list<string>): string
  fun join(msgs: list<string>, acc: string): string
    match msgs
      Nil -> acc
      Cons(msg, Nil) -> acc ++ "\"" ++ msg ++ "\""
      Cons(msg, rest) -> join(rest, acc ++ "\"" ++ msg ++ "\",")
  "[" ++ join(mismatches, "") ++ "]"

fun server-loop(): io ()
  val line = readline()
  if line == "" then ()
  else if line.contains("\"quit\"") then
    println("{\"status\":\"stopped\"}")
  else
    val op = extract-op(line)
    val response = match op
      "compare" ->
        // Extract declared and actual effect types
        val declared-types = extract-effect-types(line, "declared")
        val actual-types = extract-effect-types(line, "actual")
        // Build effect-sig lists
        fun to-sigs(types: list<effect-type], declared: bool): list<effect-sig>
          match types
            Nil -> Nil
            Cons(et, rest) -> Cons(Effect-sig(et, "", declared), to-sigs(rest, declared))
        val declared-sigs = to-sigs(declared-types, True)
        val actual-sigs = to-sigs(actual-types, False)
        val (mismatch, debt, mismatches) = compare-effects(declared-sigs, actual-sigs)
        "{\"status\":\"success\",\"mismatch\":" ++ (if mismatch then "true" else "false") ++
        ",\"debt\":" ++ show(debt) ++
        ",\"mismatches\":" ++ json-mismatches(mismatches) ++
        ",\"declared_count\":" ++ show(declared-types.length) ++
        ",\"actual_count\":" ++ show(actual-types.length) ++ "}"

      "dispatch" ->
        // Extract tool name and declared effects, return karmic-result structure
        val tool = extract-field(line, "tool")
        val declared-types = extract-effect-types(line, "declared")
        val (mismatch, debt, mismatches) = if declared-types == Nil
          then (False, 0.0, Nil)
          else
            // For dispatch, we assume actual = declared (the handler will update)
            val declared-sigs = 
              fun to-sigs(types: list<effect-type>): list<effect-sig>
                match types
                  Nil -> Nil
                  Cons(et, rest) -> Cons(Effect-sig(et, "", True), to-sigs(rest))
              to-sigs(declared-types)
            compare-effects(declared-sigs, declared-sigs)  // No mismatch on dispatch
        "{\"status\":\"success\",\"tool\":\"" ++ tool ++
        "\",\"mismatch\":" ++ (if mismatch then "true" else "false") ++
        ",\"debt\":" ++ show(debt) ++
        ",\"declared_effects\":" ++ json-effect-list(
          match declared-types
            Nil -> Nil
            Cons(et, rest) -> 
              fun to-sigs(types: list<effect-type>): list<effect-sig>
                match types
                  Nil -> Nil
                  Cons(et2, rest2) -> Cons(Effect-sig(et2, "", True), to-sigs(rest2))
              to-sigs(declared-types)
        ) ++ "}"

      "status" ->
        "{\"status\":\"success\",\"module\":\"karmic_effects\",\"version\":\"1.0\",\"features\":[\"compare\",\"dispatch\",\"effect_types\"]}"

      _ ->
        "{\"status\":\"error\",\"error\":\"unknown op\"}"

    println(response)
    server-loop()

fun main(): io ()
  println("{\"status\":\"started\",\"module\":\"karmic_effects\",\"version\":\"1.0\",\"features\":[\"compare\",\"dispatch\",\"effect_types\",\"debt_calculation\"]}")
  server-loop()
