from hypothesis import HealthCheck, given, settings, strategies as st
from whitemagic.core.intelligence.hologram.encoder import (
    CoordinateEncoder,
    HolographicCoordinate,
)

# Generate random strings
text_strategy = st.text(min_size=0, max_size=100)
# Generate tags list
tags_strategy = st.lists(st.text(min_size=1, max_size=10), max_size=5)

memory_strategy = st.fixed_dictionaries(
    {
        "id": st.uuids().map(str),
        "content": text_strategy,
        "title": text_strategy,
        "tags": tags_strategy,
        "emotional_valence": st.floats(min_value=-1.0, max_value=1.0) | st.none(),
        "importance": st.floats(min_value=0.0, max_value=1.0) | st.none(),
        "neuro_score": st.floats(min_value=0.0, max_value=2.0) | st.none(),
        "galactic_distance": st.floats(min_value=0.0, max_value=1.0) | st.none(),
        "memory_type": st.sampled_from(
            ["short_term", "long_term", "episodic", "pattern", "log", "unknown"]
        )
        | st.none(),
        "access_count": st.integers(min_value=0, max_value=1000) | st.none(),
        "is_protected": st.booleans(),
        "metadata": st.dictionaries(st.text(), st.text()),
    }
)


@given(memory_strategy)
@settings(suppress_health_check=[HealthCheck.too_slow], deadline=None)
def test_holographic_encoder_bounds(memory):
    encoder = CoordinateEncoder()
    # Disable gardens so we just test the core math
    encoder._garden_bias_enabled = False

    # Run encoder
    coord = encoder.encode(memory)

    # Assert type
    assert isinstance(coord, HolographicCoordinate)

    # Assert coordinate bounds
    assert -1.0 <= coord.x <= 1.0, f"X axis out of bounds: {coord.x}"
    assert -1.0 <= coord.y <= 1.0, f"Y axis out of bounds: {coord.y}"
    assert -1.0 <= coord.z <= 1.0, f"Z axis out of bounds: {coord.z}"
    assert coord.w >= 0.1, f"W axis should be >= 0.1 for visibility but was {coord.w}"
    assert 0.0 <= coord.v <= 1.0, f"V axis out of bounds: {coord.v}"
