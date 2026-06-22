// State Effects - State Management (PSR-007)
module state_effects

effect state
  fun get-state(entity: string): string
  fun set-state(entity: string, new-state: string): ()

fun transition-state(entity: string, from: string, to: string): <state> bool
  if state/get-state(entity) == from then
    state/set-state(entity, to)
    True
  else
    False
