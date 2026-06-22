// Consolidation Effects - Memory Consolidation (PSR-001)
module consolidation_effects

effect consolidation
  fun detect-constellations(): list<string>
  fun merge-similar(threshold: float64): int

fun consolidate-memories(): <consolidation> (list<string>, int)
  val constellations = consolidation/detect-constellations()
  val merged = consolidation/merge-similar(0.9)
  (constellations, merged)
