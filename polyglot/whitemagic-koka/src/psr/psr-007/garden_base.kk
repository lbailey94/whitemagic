// garden_base - Koka Migration
// Garden effects
// Effect handlers for type-safe coordination

module garden_base

effect garden_base_effect {
    fun process(data: string): string
    fun get_state(): int
}

fun garden_base_handler(action: () -> <garden_base_effect> a): a {
    with handler {
        fun process(data) {
            // Garden effect propagation logic
            data
        }
        fun get_state() {
            // Returns resonance energy (0-100)
            100
        }
    }
    action()
}
