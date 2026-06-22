// garden_resonance - Koka Migration
// Resonance
// Effect handlers for type-safe coordination

module garden_resonance

effect garden_resonance_effect {
    fun process(data: string): string
    fun get_state(): int
}

fun garden_resonance_handler(action: () -> <garden_resonance_effect> a): a {
    with handler {
        fun process(data) {
            // TODO: Implement effect handler
            data
        }
        fun get_state() {
            0
        }
    }
    action()
}
