// gan_ying - Gan Ying event bus effects (S022 Phase 1 VC3)
// Ported from gan_ying_enhanced.py - Async event handling with algebraic effects

module gan_ying

import std/async
import std/time

// ═══════════════════════════════════════════════════════════════════════════
// Gan Ying Event Effects
// ═══════════════════════════════════════════════════════════════════════════

// Core event bus effect
effect gy-event
  fun emit-event(event-type: string, payload: string): ()
  fun subscribe(filter: string): string  // returns subscription id
  fun unsubscribe(sub-id: string): bool
  fun get-pending-events(): list<event>
  fun process-events(): int  // returns count processed

// Event handler chain effect
effect gy-handler
  fun register-handler(event-type: string, handler: string): ()
  fun unregister-handler(event-type: string): ()
  fun get-handlers(event-type: string): list<string>
  fun invoke-handler-chain(event-type: string, payload: string): string

// Async event processing effect
effect gy-async
  fun schedule-async(task: () -> ()): string  // returns task id
  fun await-task(task-id: string): string
  fun cancel-task(task-id: string): bool
  fun get-running-tasks(): list<string>

// ═══════════════════════════════════════════════════════════════════════════
// Event Types
// ═══════════════════════════════════════════════════════════════════════════

struct event
  id: string
  event-type: string
  payload: string
  timestamp: float64
  priority: int

struct subscription
  id: string
  filter: string
  active: bool

// ═══════════════════════════════════════════════════════════════════════════
// Handler implementations
// ═══════════════════════════════════════════════════════════════════════════

// Production event bus handler
val handle-gy-event-production = handler
  var events := [] : list<event>
  var subs := [] : list<subscription>
  var next-id := 0
  
  fun emit-event(et, payload)
    val e = event(
      "evt_" ++ next-id.show,
      et,
      payload,
      time/now().ticks.float64,
      5
    )
    next-id := next-id + 1
    events := Cons(e, events)
  
  fun subscribe(filter)
    val sid = "sub_" ++ next-id.show
    next-id := next-id + 1
    subs := Cons(subscription(sid, filter, True), subs)
    sid
  
  fun unsubscribe(sid)
    val before = subs.length
    subs := subs.filter(fn(s) s.id != sid)
    subs.length < before
  
  fun get-pending-events()
    events
  
  fun process-events()
    val count = events.length
    events := []
    count

// Handler chain implementation
val handle-gy-handler-production = handler
  var handlers : list<(string, string)> := []
  
  fun register-handler(et, h)
    handlers := Cons((et, h), handlers)
  
  fun unregister-handler(et)
    handlers := handlers.filter(fn(p) p.fst != et)
  
  fun get-handlers(et)
    handlers.filter(fn(p) p.fst == et).map(fn(p) p.snd)
  
  fun invoke-handler-chain(et, payload)
    val hs = get-handlers(et)
    hs.foldl(payload) fn(acc, h)
      // In production, would call actual handler
      "[" ++ h ++ ":" ++ acc ++ "]"

// Async task handler
val handle-gy-async-production = handler
  var tasks : list<(string, ()) -> ())> := []
  var running : list<string> := []
  var next-task := 0
  
  fun schedule-async(task)
    val tid = "task_" ++ next-task.show
    next-task := next-task + 1
    tasks := Cons((tid, task), tasks)
    running := Cons(tid, running)
    tid
  
  fun await-task(tid)
    // Would block and wait for task completion
    "completed:" ++ tid
  
  fun cancel-task(tid)
    val before = running.length
    running := running.filter(fn(t) t != tid)
    running.length < before
  
  fun get-running-tasks()
    running

// ═══════════════════════════════════════════════════════════════════════════
// Event bus operations (ported from gan_ying_enhanced.py)
// ═══════════════════════════════════════════════════════════════════════════

fun emit(event-type: string, payload: string): <gy-event> ()
  gy-event/emit-event(event-type, payload)

fun on(event-type: string, handler: string): <gy-handler> ()
  gy-handler/register-handler(event-type, handler)

fun off(event-type: string): <gy-handler> ()
  gy-handler/unregister-handler(event-type)

// ═══════════════════════════════════════════════════════════════════════════
// Async event processing
// ═══════════════════════════════════════════════════════════════════════════

fun process-async-events(): <gy-event, gy-async> int
  val pending = gy-event/get-pending-events()
  
  pending.foldl(0) fn(count, evt)
    val _ = gy-async/schedule-async(fn()
      // Process event asynchronously
      ()
    )
    count + 1

// ═══════════════════════════════════════════════════════════════════════════
// Event filtering and transformation
// ═══════════════════════════════════════════════════════════════════════════

fun filter-events-by-type(events: list<event>, et: string): list<event>
  events.filter(fn(e) e.event-type == et)

fun filter-events-by-priority(events: list<event>, min-priority: int): list<event>
  events.filter(fn(e) e.priority >= min-priority)

fun sort-events-by-time(events: list<event>): list<event>
  events.sort-by(fn(e) e.timestamp, Lt)

// ═══════════════════════════════════════════════════════════════════════════
// Event bus lifecycle
// ═══════════════════════════════════════════════════════════════════════════

fun start-event-bus(): <gy-event, gy-handler, gy-async> string
  // Initialize all handlers
  gy-handler/register-handler("memory.created", "log_handler")
  gy-handler/register-handler("memory.accessed", "cache_handler")
  gy-handler/register-handler("session.start", "init_handler")
  gy-handler/register-handler("dream.cycle", "dream_handler")
  
  // Subscribe to all events
  val sub-id = gy-event/subscribe("*")
  
  "event_bus_started:" ++ sub-id

fun stop-event-bus(): <gy-event, gy-handler, gy-async> bool
  // Cancel all running tasks
  val running = gy-async/get-running-tasks()
  running.foreach fn(tid)
    gy-async/cancel-task(tid)
  
  // Process remaining events
  val processed = gy-event/process-events()
  
  processed > 0

// ═══════════════════════════════════════════════════════════════════════════
// Event composition (monadic-style event chaining)
// ═══════════════════════════════════════════════════════════════════════════

fun and-then(first: () -> <gy-event> a, second: a -> <gy-event> b): <gy-event> b
  val result = first()
  second(result)

fun map-event(et: string, f: string -> string): <gy-event, gy-handler> ()
  gy-handler/register-handler(et, "transform:" ++ et)
  // Handler would apply f to payload

// ═══════════════════════════════════════════════════════════════════════════
// Performance utilities
// ═══════════════════════════════════════════════════════════════════════════

fun batch-emit(events: list<(string, string)>): <gy-event> int
  events.foreach fn(pair)
    val (et, payload) = pair
    gy-event/emit-event(et, payload)
  events.length

fun get-event-stats(): <gy-event, gy-handler> (int, int, int)
  val pending = gy-event/get-pending-events().length
  val handlers = 4  // Approximate
  val subs = 1      // Approximate
  (pending, handlers, subs)
