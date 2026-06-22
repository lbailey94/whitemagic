// garden_resonance - Garden resonance and event composition (S022 Phase 4 VC3)
// Ported from garden resonance patterns

module garden_resonance

// ═══════════════════════════════════════════════════════════════════════════
// Garden Resonance Effect Definition
// ═══════════════════════════════════════════════════════════════════════════

effect garden-resonance
  // Core garden resonance operations
  fun get-garden-state(garden: string): string
  fun set-garden-state(garden: string, state: string): ()
  fun emit-garden-event(garden: string, event: string): ()
  fun get-resonance-level(garden: string): float64
  
  // Garden-to-Gana mapping
  fun get-gana-for-garden(garden: string): list<string>
  fun get-garden-for-gana(gana: string): string
  
  // Harmony tracking
  fun get-garden-harmony(): float64
  fun get-quadrant-balance(): list<(string, float64)>

// ═══════════════════════════════════════════════════════════════════════════
// Garden Types
// ═══════════════════════════════════════════════════════════════════════════

struct garden-state
  name: string
  quadrant: string
  resonance: float64
  active-ganas: list<string>
  event-count: int

// 12 Gardens mapping to 28 Ganas
val garden-mapping : list<(string, string, list<string>)> = [
  // (garden-name, quadrant, associated-ganas)
  ("Courage", "East", ["gana_horn"]),
  ("Practice", "East", ["gana_neck"]),
  ("Truth", "East", ["gana_root"]),
  ("Sanctuary", "East", ["gana_room"]),
  ("Love", "East", ["gana_heart"]),
  ("Metal", "East", ["gana_tail"]),
  ("Wisdom", "East", ["gana_winnowing_basket"]),
  
  ("Grief", "South", ["gana_ghost"]),
  ("Play", "South", ["gana_willow"]),
  ("Beauty", "South", ["gana_star"]),
  ("Connection", "South", ["gana_extended_net"]),
  ("Adventure", "South", ["gana_wings"]),
  ("Transformation", "South", ["gana_chariot"]),
  ("Joy", "South", ["gana_abundance"]),
  
  ("Patience", "West", ["gana_straddling_legs"]),
  ("Gratitude", "West", ["gana_mound"]),
  ("Healing", "West", ["gana_stomach"]),
  ("Presence", "West", ["gana_hairy_head"]),
  ("Mystery", "West", ["gana_net"]),
  ("Voice", "West", ["gana_turtle_beak"]),
  ("Dharma", "West", ["gana_three_stars"]),
  
  ("Awe", "North", ["gana_dipper"]),
  ("Reverence", "North", ["gana_ox"]),
  ("Wonder", "North", ["gana_girl"]),
  ("Stillness", "North", ["gana_void"]),
  ("Protection", "North", ["gana_roof"]),
  ("Sangha", "North", ["gana_encampment"]),
  ("Air", "North", ["gana_wall"])
]

// ═══════════════════════════════════════════════════════════════════════════
// Garden Resonance Handler
// ═══════════════════════════════════════════════════════════════════════════

fun handle-garden-resonance(action: () -> <garden-resonance> a): a
  var gardens : list<garden-state> := 
    garden-mapping.map(fn(g)
      val (name, quadrant, ganas) = g
      garden-state(name, quadrant, 1.0, ganas, 0)
    )
  
  handle action
    fun get-garden-state(name)
      match gardens.find(fn(g) g.name == name)
        Just(g) -> "{" ++
          "\"resonance\": " ++ g.resonance.show ++ "," ++
          "\"ganas\": [" ++ g.active-ganas.join(",") ++ "]," ++
          "\"events\": " ++ g.event-count.show ++
        "}"
        Nothing -> "{}"
    
    fun set-garden-state(name, state)
      // Parse state and update
      gardens := gardens.map(fn(g)
        if g.name == name then
          garden-state(name, g.quadrant, g.resonance, g.active-ganas, g.event-count + 1)
        else g
      )
    
    fun emit-garden-event(name, event)
      gardens := gardens.map(fn(g)
        if g.name == name then
          garden-state(name, g.quadrant, g.resonance, g.active-ganas, g.event-count + 1)
        else g
      )
    
    fun get-resonance-level(name)
      match gardens.find(fn(g) g.name == name)
        Just(g) -> g.resonance
        Nothing -> 0.0
    
    fun get-gana-for-garden(name)
      match garden-mapping.find(fn(g) g.fst == name)
        Just((_, _, ganas)) -> ganas
        Nothing -> []
    
    fun get-garden-for-gana(gana)
      match garden-mapping.find(fn(g) g.thd.any(fn(gg) gg == gana))
        Just((name, _, _)) -> name
        Nothing -> "Unknown"
    
    fun get-garden-harmony()
      if gardens.length == 0 then 1.0
      else
        val total = gardens.foldl(0.0) fn(acc, g) acc + g.resonance
        total / float64(gardens.length)
    
    fun get-quadrant-balance()
      val quadrants = ["East", "South", "West", "North"]
      quadrants.map(fn(q)
        val q-gardens = gardens.filter(fn(g) g.quadrant == q)
        val q-resonance = if q-gardens.length == 0 then 0.0
          else q-gardens.foldl(0.0) fn(acc, g) acc + g.resonance
        val avg = if q-gardens.length == 0 then 0.0
          else q-resonance / float64(q-gardens.length)
        (q, avg)
      )

// ═══════════════════════════════════════════════════════════════════════════
// Garden Event Composition
// ═══════════════════════════════════════════════════════════════════════════

struct garden-event
  source-garden: string
  target-garden: string
  event-type: string
  payload: string
  resonance-strength: float64

fun emit-cross-garden-event(
  source: string, 
  target: string, 
  event-type: string,
  payload: string
): <garden-resonance> ()
  
  val source-res = get-resonance-level(source)
  val target-res = get-resonance-level(target)
  val strength = (source-res + target-res) / 2.0
  
  emit-garden-event(source, "outgoing:" ++ event-type ++ ":" ++ target)
  emit-garden-event(target, "incoming:" ++ event-type ++ ":" ++ source)

// ═══════════════════════════════════════════════════════════════════════════
// Garden Harmony Calculations
// ═══════════════════════════════════════════════════════════════════════════

struct harmony-snapshot
  overall: float64
  by-quadrant: list<(string, float64)>
  strongest-garden: string
  weakest-garden: string
  balance-score: float64

fun calculate-harmony(): <garden-resonance> harmony-snapshot
  val by-quadrant = get-quadrant-balance()
  val overall = get-garden-harmony()
  
  // Balance is inverse of variance
  val values = by-quadrant.map(fn(p) p.snd)
  val mean = values.foldl(0.0) fn(a, v) a + v / float64(values.length)
  val variance = values.foldl(0.0) fn(a, v) 
    val diff = v - mean
    a + (diff * diff) / float64(values.length)
  
  harmony-snapshot(
    overall,
    by-quadrant,
    "Courage",  // Would calculate actual
    "Air",      // Would calculate actual
    1.0 - variance
  )

// ═══════════════════════════════════════════════════════════════════════════
// Garden cascade effects (events flow between gardens)
// ═══════════════════════════════════════════════════════════════════════════

fun cascade-event(
  event: string, 
  source: string,
  max-hops: int
): <garden-resonance> list<string>
  
  var visited := [source]
  var affected := [source]
  var hops := 0
  
  while hops < max-hops do
    val current = affected
    // Find connected gardens (simplified - all gardens in same quadrant connected)
    val quadrant = match garden-mapping.find(fn(g) g.fst == source)
      Just((_, q, _)) -> q
      Nothing -> ""
    
    val connected = garden-mapping
      .filter(fn(g) g.snd == quadrant && !visited.any(fn(v) v == g.fst))
      .map(fn(g) g.fst)
    
    if connected.length == 0 then
      hops := max-hops  // Stop
    else
      connected.foreach(fn(c)
        emit-garden-event(c, "cascaded:" ++ event)
        affected := Cons(c, affected)
        visited := Cons(c, visited)
      )
      hops := hops + 1
  
  affected

// ═══════════════════════════════════════════════════════════════════════════
// Garden activation patterns
// ═══════════════════════════════════════════════════════════════════════════

fun activate-garden-sequence(gardens: list<string>): <garden-resonance> bool
  gardens.foreach(fn(g)
    emit-garden-event(g, "activated")
  )
  True

fun deactivate-garden-sequence(gardens: list<string>): <garden-resonance> bool
  gardens.reverse.foreach(fn(g)
    emit-garden-event(g, "deactivated")
  )
  True
