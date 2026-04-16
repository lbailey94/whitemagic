// effect_visualization - Trace and visualize effect flows (S022 Phase 6 VC3)
// Debugging and visualization for effect handlers

module effect_visualization

// ═══════════════════════════════════════════════════════════════════════════
// Visualization Effect Definition
// ═══════════════════════════════════════════════════════════════════════════

effect viz-trace
  // Trace operations
  fun trace-enter(effect: string, operation: string): ()
  fun trace-exit(effect: string, operation: string, result: string): ()
  fun trace-state(effect: string, state: string): ()
  fun trace-error(effect: string, error: string): ()
  
  // Visualization queries
  get-trace-tree(): trace-node
  get-effect-connections(): list<(string, string)>
  get-hot-paths(): list<(string, int)>
  
  // Export
  export-dot(): string
  export-json(): string
  export-mermaid(): string

// ═══════════════════════════════════════════════════════════════════════════
// Trace Types
// ═══════════════════════════════════════════════════════════════════════════

struct trace-node
  effect: string
  operation: string
  timestamp: int
  duration: int
  children: list<trace-node>
  state-snapshot: string
  result: string

struct trace-event
  event-type: string  // "enter", "exit", "state", "error"
  effect: string
  operation: string
  timestamp: int
  data: string

// ═══════════════════════════════════════════════════════════════════════════
// Visualization Handler
// ═══════════════════════════════════════════════════════════════════════════

fun handle-visualization(action: () -> <viz-trace> a): (a, list<trace-event>)
  var events : list<trace-event> := []
  var event-id := 0
  
  val result = handle action
    fun trace-enter(eff, op)
      events := Cons(
        trace-event("enter", eff, op, ticks(), ""),
        events
      )
      event-id := event-id + 1
    
    fun trace-exit(eff, op, res)
      events := Cons(
        trace-event("exit", eff, op, ticks(), res),
        events
      )
    
    fun trace-state(eff, st)
      events := Cons(
        trace-event("state", eff, "", ticks(), st),
        events
      )
    
    fun trace-error(eff, err)
      events := Cons(
        trace-event("error", eff, "", ticks(), err),
        events
      )
    
    fun get-trace-tree()
      // Build tree from flat events
      trace-node("root", "root", 0, 0, [], "", "")
    
    fun get-effect-connections()
      // Find parent-child relationships
      []
    
    fun get-hot-paths()
      // Count effect-operation frequencies
      events.foldl([] : list<(string, int)>) fn(acc, e)
        val key = e.effect ++ "/" ++ e.operation
        match acc.find(fn(p) p.fst == key)
          Just((_, count)) ->
            Cons((key, count + 1), acc.filter(fn(p) p.fst != key))
          Nothing ->
            Cons((key, 1), acc)
    
    fun export-dot()
      // Graphviz DOT format
      var dot := "digraph EffectFlow {\\n"
      events.foreach(fn(e)
        dot := dot ++ "  \\"" ++ e.effect ++ "\\" [label=\\"" ++ e.effect ++ "\\"];\\n"
      )
      dot := dot ++ "}"
      dot
    
    fun export-json()
      // JSON representation
      "[" ++ events.map(fn(e)
        "{" ++
        "\\"type\\": \"" ++ e.event-type ++ "\"," ++
        "\\"effect\\": \"" ++ e.effect ++ "\"," ++
        "\\"operation\\": \"" ++ e.operation ++ "\"," ++
        "\\"timestamp\\": " ++ e.timestamp.show ++
        "}"
      ).join(",") ++ "]"
    
    fun export-mermaid()
      // Mermaid flowchart format
      var mmd := "graph TD\\n"
      events.foreach(fn(e)
        mmd := mmd ++ "  " ++ e.effect ++ "[" ++ e.operation ++ "]\\n"
      )
      mmd
  
  (result, events)

// ═══════════════════════════════════════════════════════════════════════════
// Instrumented Handler Wrapper
// ═══════════════════════════════════════════════════════════════════════════

fun with-tracing(handler-name: string, action: () -> <viz-trace> a): a
  viz-trace/trace-enter(handler-name, "handler")
  val result = action()
  viz-trace/trace-exit(handler-name, "handler", result.show)
  result

// ═══════════════════════════════════════════════════════════════════════════
// Visual Effect Tree Builder
// ═══════════════════════════════════════════════════════════════════════════

struct effect-tree
  name: string
  children: list<effect-tree>
  operations: list<string>

fun build-effect-tree(events: list<trace-event>): effect-tree
  // Build hierarchical tree from trace events
  effect-tree("root", [], [])

// ═══════════════════════════════════════════════════════════════════════════
// Heat Map Generation
// ═══════════════════════════════════════════════════════════════════════════

struct heat-cell
  effect: string
  operation: string
  count: int
  avg-duration: float64

fun generate-heat-map(events: list<trace-event>): list<heat-cell>
  // Aggregate events by effect/operation
  []

// ═══════════════════════════════════════════════════════════════════════════
// Flow Analysis
// ═══════════════════════════════════════════════════════════════════════════

struct effect-flow
  from-effect: string
  to-effect: string
  count: int
  avg-time: float64

fun analyze-effect-flows(events: list<trace-event>): list<effect-flow>
  // Detect effect hand-off patterns
  []

// ═══════════════════════════════════════════════════════════════════════════
// HTML Report Generation
// ═══════════════════════════════════════════════════════════════════════════

fun generate-html-report(events: list<trace-event>): string
  "<!DOCTYPE html>\\n" ++
  "<html>\\n" ++
  "<head><title>Effect Trace Report</title></head>\\n" ++
  "<body>\\n" ++
  "  <h1>Effect Execution Trace</h1>\\n" ++
  "  <p>Events: " ++ events.length.show ++ "</p>\\n" ++
  "  <!-- Visualization would go here -->\\n" ++
  "</body>\\n" ++
  "</html>"
