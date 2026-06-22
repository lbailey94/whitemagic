"""Emergence Detection - Mojo 0.26.1"""
from math import sqrt, exp, log

fn entropy(values: List[Float32]) -> Float32:
    """Compute Shannon entropy."""
    var total: Float32 = 0.0
    for i in range(len(values)):
        total += values[i]
    
    if total <= 0.0:
        return 0.0
    
    var h: Float32 = 0.0
    for i in range(len(values)):
        if values[i] > 0.0:
            var p = values[i] / total
            h -= p * log(p)
    return h

fn emergence_score(historical: List[Float32], current: List[Float32]) -> Float32:
    """Detect emergence via entropy delta."""
    var h_hist = entropy(historical)
    var h_curr = entropy(current)
    return abs(h_curr - h_hist)

fn main():
    print("Emergence Detection v0.26.1")
