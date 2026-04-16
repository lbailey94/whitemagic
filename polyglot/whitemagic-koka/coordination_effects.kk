// Coordination Effects - System Coordination (PSR-009)
module coordination_effects

effect coordination
  fun publish-event(event-type: string, data: string): ()
  fun subscribe(event-type: string, handler: string): ()

fun coordinate-components(components: list<string>): <coordination> ()
  components.foreach fn(comp)
    coordination/publish-event("component_ready", comp)
