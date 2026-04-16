"""Surprise Gate - Mojo 0.26.1"""
from math import exp, log

fn surprise_score(expected: List[Float32], actual: List[Float32]) -> Float32:
    """Compute KL-divergence based surprise."""
    var kl: Float32 = 0.0
    for i in range(len(expected)):
        if expected[i] > 0.0 and actual[i] > 0.0:
            kl += actual[i] * log(actual[i] / expected[i])
    return kl

fn gate_trigger(surprise: Float32, threshold: Float32) -> Bool:
    """Check if surprise exceeds threshold."""
    return surprise > threshold

fn main():
    print("Surprise Gate v0.26.1")
