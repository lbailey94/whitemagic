// session_state - Session state management effects (S022 Phase 2 VC1)
// Ported from session management patterns - Koka state effect implementation

module session_state

import std/time

// ═══════════════════════════════════════════════════════════════════════════
// Session State Effect Definition
// ═══════════════════════════════════════════════════════════════════════════

effect session-st
  // Core session operations
  fun get-session-id(): string
  fun get-session-context(): string
  fun set-session-context(ctx: string): ()
  fun get-creation-time(): float64
  fun get-last-activity(): float64
  fun touch-session(): ()
  
  // PRAT-specific session state
  fun get-last-gana(): string
  fun set-last-gana(gana: string): ()
  fun get-invocation-count(): int
  fun increment-invocation(): ()
  
  // Galaxy context
  fun get-current-galaxy(): string
  fun set-current-galaxy(galaxy: string): ()
  
  // Resonance hints
  fun get-resonance-hints(): string
  fun set-resonance-hints(hints: string): ()

// ═══════════════════════════════════════════════════════════════════════════
// Session State Types
// ═══════════════════════════════════════════════════════════════════════════

struct session-data
  id: string
  context: string
  created: float64
  last-activity: float64
  last-gana: string
  invocations: int
  current-galaxy: string
  resonance-hints: string

fun empty-session(id: string): session-data
  session-data(
    id,
    "",
    time/now().ticks.float64,
    time/now().ticks.float64,
    "",
    0,
    "default",
    "{}"
  )

// ═══════════════════════════════════════════════════════════════════════════
// Session State Handler
// ═══════════════════════════════════════════════════════════════════════════

fun handle-session-state(session-id: string, action: () -> <session-st> a): a
  var state := empty-session(session-id)
  
  handle action
    fun get-session-id()
      state.id
    
    fun get-session-context()
      state.context
    
    fun set-session-context(ctx)
      state := session-data(
        state.id, ctx, state.created,
        time/now().ticks.float64,
        state.last-gana, state.invocations,
        state.current-galaxy, state.resonance-hints
      )
    
    fun get-creation-time()
      state.created
    
    fun get-last-activity()
      state.last-activity
    
    fun touch-session()
      state := session-data(
        state.id, state.context, state.created,
        time/now().ticks.float64,
        state.last-gana, state.invocations,
        state.current-galaxy, state.resonance-hints
      )
    
    fun get-last-gana()
      state.last-gana
    
    fun set-last-gana(gana)
      state := session-data(
        state.id, state.context, state.created,
        time/now().ticks.float64,
        gana, state.invocations,
        state.current-galaxy, state.resonance-hints
      )
    
    fun get-invocation-count()
      state.invocations
    
    fun increment-invocation()
      state := session-data(
        state.id, state.context, state.created,
        time/now().ticks.float64,
        state.last-gana, state.invocations + 1,
        state.current-galaxy, state.resonance-hints
      )
    
    fun get-current-galaxy()
      state.current-galaxy
    
    fun set-current-galaxy(galaxy)
      state := session-data(
        state.id, state.context, state.created,
        time/now().ticks.float64,
        state.last-gana, state.invocations,
        galaxy, state.resonance-hints
      )
    
    fun get-resonance-hints()
      state.resonance-hints
    
    fun set-resonance-hints(hints)
      state := session-data(
        state.id, state.context, state.created,
        time/now().ticks.float64,
        state.last-gana, state.invocations,
        state.current-galaxy, hints
      )

// ═══════════════════════════════════════════════════════════════════════════
// Session lifecycle operations
// ═══════════════════════════════════════════════════════════════════════════

fun create-session(id: string): <session-st> ()
  // Session initialized by handler
  ()

fun checkpoint-session(): <session-st> string
  val snap = "{" ++
    "\"id\": \"" ++ get-session-id() ++ "\"," ++
    "\"context\": \"" ++ get-session-context() ++ "\"," ++
    "\"invocations\": " ++ get-invocation-count().show ++ "," ++
    "\"last_gana\": \"" ++ get-last-gana() ++ "\"" ++
  "}"
  touch-session()
  snap

fun resume-from-checkpoint(checkpoint: string): <session-st> bool
  // Would parse checkpoint and restore state
  touch-session()
  True

// ═══════════════════════════════════════════════════════════════════════════
// Session with PRAT integration
// ═══════════════════════════════════════════════════════════════════════════

fun prat-invoke-with-session(tool: string, args: string): <session-st> string
  increment-invocation()
  touch-session()
  
  // Would dispatch to PRAT router
  "invoked:" ++ tool ++ ":" ++ get-session-id()

// ═══════════════════════════════════════════════════════════════════════════
// Session statistics
// ═══════════════════════════════════════════════════════════════════════════

fun get-session-stats(): <session-st> (int, float64, string)
  val invocations = get-invocation-count()
  val created = get-creation-time()
  val age = time/now().ticks.float64 - created
  val galaxy = get-current-galaxy()
  (invocations, age, galaxy)

// ═══════════════════════════════════════════════════════════════════════════
// Multiple session management (for testing/advanced use)
// ═══════════════════════════════════════════════════════════════════════════

struct session-registry
  sessions: list<(string, session-data)>

fun create-session-registry(): session-registry
  session-registry([])

fun register-session(reg: session-registry, id: string): session-registry
  session-registry(Cons((id, empty-session(id)), reg.sessions))

fun lookup-session(reg: session-registry, id: string): maybe<session-data>
  reg.sessions.find(fn(p) p.fst == id).map(fn(p) p.snd)
