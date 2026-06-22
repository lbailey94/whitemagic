// grimoire_spells - Spell system with extensible handlers (S022 Phase 5)
// Ported from grimoire/auto_cast.py - effectful dispatch

module grimoire_spells

// ═══════════════════════════════════════════════════════════════════════════
// Spell System Effect Definition
// ═══════════════════════════════════════════════════════════════════════════

effect spell-system
  // Spell registry
  fun register-spell(name: string, handler: string, confidence: float64): ()
  fun unregister-spell(name: string): ()
  fun get-spell(name: string): maybe<(string, float64)>
  fun list-spells(): list<(string, float64)>
  
  // Spell casting
  fun cast-spell(name: string, args: string): string
  fun suggest-spells(context: string): list<(string, float64)>
  fun auto-cast(context: string): maybe<(string, string)>
  
  // Spell confidence
  fun get-confidence(name: string): float64
  fun update-confidence(name: string, delta: float64): ()
  fun set-confidence-threshold(threshold: float64): ()
  
  // Spell composition
  fun chain-spells(names: list<string>, args: string): string
  fun fuse-spells(name1: string, name2: string): maybe<string>

// ═══════════════════════════════════════════════════════════════════════════
// Spell Types
// ═══════════════════════════════════════════════════════════════════════════

struct spell
  name: string
  handler: string
  confidence: float64
  tags: list<string>
  usage-count: int

struct spell-registry
  spells: list<spell>
  confidence-threshold: float64

// ═══════════════════════════════════════════════════════════════════════════
// Spell System Handler
// ═══════════════════════════════════════════════════════════════════════════

fun handle-spell-system(threshold: float64, action: () -> <spell-system> a): a
  var registry := spell-registry([], threshold)
  
  handle action
    fun register-spell(name, handler, confidence)
      val spell = spell(name, handler, confidence, [], 0)
      registry := spell-registry(
        Cons(spell, registry.spells.filter(fn(s) s.name != name)),
        registry.confidence-threshold
      )
    
    fun unregister-spell(name)
      registry := spell-registry(
        registry.spells.filter(fn(s) s.name != name),
        registry.confidence-threshold
      )
    
    fun get-spell(name)
      registry.spells.find(fn(s) s.name == name).map(fn(s) (s.handler, s.confidence))
    
    fun list-spells()
      registry.spells.map(fn(s) (s.name, s.confidence))
    
    fun cast-spell(name, args)
      match get-spell(name)
        Just((handler, confidence)) ->
          if confidence >= registry.confidence-threshold then
            "{" ++
            "\"spell\": \"" ++ name ++ "\"," ++
            "\"handler\": \"" ++ handler ++ "\"," ++
            "\"confidence\": " ++ confidence.show ++ "," ++
            "\"args\": " ++ args ++ "," ++
            "\"result\": \"cast_success\"" ++
            "}"
          else
            "{\"error\": \"confidence_too_low\", \"required\": " ++ registry.confidence-threshold.show ++ "}"
        Nothing ->
          "{\"error\": \"spell_not_found\", \"name\": \"" ++ name ++ "\"}"
    
    fun suggest-spells(context)
      // Simple matching - would use more sophisticated algorithm
      registry.spells
        .filter(fn(s) s.confidence >= registry.confidence-threshold)
        .sort-by(fn(s) s.confidence, Gt)
        .take(5)
        .map(fn(s) (s.name, s.confidence))
    
    fun auto-cast(context)
      val suggestions = suggest-spells(context)
      match suggestions.head
        Just((name, confidence)) ->
          val result = cast-spell(name, "{\"context\": \"" ++ context ++ "\"}")
          Just((name, result))
        Nothing -> Nothing
    
    fun get-confidence(name)
      match registry.spells.find(fn(s) s.name == name)
        Just(s) -> s.confidence
        Nothing -> 0.0
    
    fun update-confidence(name, delta)
      registry := spell-registry(
        registry.spells.map(fn(s)
          if s.name == name then
            spell(s.name, s.handler, max(0.0, min(1.0, s.confidence + delta)), s.tags, s.usage-count)
          else s
        ),
        registry.confidence-threshold
      )
    
    fun set-confidence-threshold(t)
      registry := spell-registry(registry.spells, t)
    
    fun chain-spells(names, args)
      names.foldl("{\"initial\": true}") fn(acc, name)
        val result = cast-spell(name, "{\"input\": " ++ acc ++ "}")
        result
    
    fun fuse-spells(name1, name2)
      match (get-spell(name1), get-spell(name2))
        (Just((h1, c1)), Just((h2, c2))) ->
          val fused-name = name1 ++ "_" ++ name2
          val fused-confidence = (c1 + c2) / 2.0
          register-spell(fused-name, "fused:" ++ h1 ++ ":" ++ h2, fused-confidence)
          Just(fused-name)
        _ -> Nothing

// ═══════════════════════════════════════════════════════════════════════════
// Standard Grimoire Spells
// ═══════════════════════════════════════════════════════════════════════════

fun init-standard-spells(): <spell-system> ()
  register-spell("summon_memory", "memory_handler", 0.9)
  register-spell("weave_narrative", "narrative_handler", 0.85)
  register-spell("forge_connection", "association_handler", 0.8)
  register-spell("illuminate", "gnosis_handler", 0.95)
  register-spell("transmute", "alchemy_handler", 0.75)
  register-spell("cascade", "cascade_handler", 0.7)

// ═══════════════════════════════════════════════════════════════════════════
// Auto-cast logic (from auto_cast.py)
// ═══════════════════════════════════════════════════════════════════════════

fun auto-cast-with-context(context: string, min-confidence: float64): <spell-system> maybe<string>
  set-confidence-threshold(min-confidence)
  
  match auto-cast(context)
    Just((spell-name, result)) -> Just(result)
    Nothing -> Nothing

// ═══════════════════════════════════════════════════════════════════════════
// Spell confidence calibration
// ═══════════════════════════════════════════════════════════════════════════

fun calibrate-confidence(spell-name: string, successes: int, failures: int): <spell-system> ()
  val total = successes + failures
  if total == 0 then ()
  else
    val new-confidence = float64(successes) / float64(total)
    val current = get-confidence(spell-name)
    val delta = new-confidence - current
    update-confidence(spell-name, delta * 0.5)  // Gradual update

// ═══════════════════════════════════════════════════════════════════════════
// Spell composability via handler stacking
// ═══════════════════════════════════════════════════════════════════════════

fun stack-spells(base: string, modifiers: list<string>): <spell-system> string
  modifiers.foldl(cast-spell(base, "{}")) fn(acc, mod)
    cast-spell(mod, "{\"input\": " ++ acc ++ "}")

// ═══════════════════════════════════════════════════════════════════════════
// Spell recommendations based on context
// ═══════════════════════════════════════════════════════════════════════════

struct spell-recommendation
  spell: string
  confidence: float64
  reason: string

fun recommend-spell(context: string): <spell-system> list<spell-recommendation>
  suggest-spells(context).map(fn(s)
    spell-recommendation(s.fst, s.snd, "context_match")
  )
