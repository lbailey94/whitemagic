"""Temporal Analysis - Mojo 0.26.1"""
from math import exp, log

fn time_decay_weight(timestamp: Float64, now: Float64, halflife: Float64) -> Float32:
    """Compute exponential decay weight."""
    var delta = now - timestamp
    if halflife <= 0.0:
        return 1.0
    var decay = exp(-delta / halflife)
    return Float32(decay)

fn recency_score(timestamps: List[Float64], now: Float64) -> List[Float32]:
    """Compute recency scores for timestamps."""
    var scores = List[Float32]()
    for i in range(len(timestamps)):
        scores.append(time_decay_weight(timestamps[i], now, 86400.0))
    return scores^

fn main():
    print("Temporal Analysis v0.26.1")
