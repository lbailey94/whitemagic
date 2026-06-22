"""Causal Miner - Mojo 0.26.1"""
from math import sqrt
from python import Python

fn temporal_correlation(times_a: List[Float64], times_b: List[Float64]) -> Float32:
    """Compute temporal correlation between two time series."""
    if len(times_a) == 0 or len(times_b) == 0:
        return 0.0
    
    var mean_a: Float64 = 0.0
    var mean_b: Float64 = 0.0
    
    for i in range(len(times_a)):
        mean_a += times_a[i]
    mean_a /= Float64(len(times_a))
    
    for i in range(len(times_b)):
        mean_b += times_b[i]
    mean_b /= Float64(len(times_b))
    
    var num: Float64 = 0.0
    var den_a: Float64 = 0.0
    var den_b: Float64 = 0.0
    
    var n = min(len(times_a), len(times_b))
    for i in range(n):
        var da = times_a[i] - mean_a
        var db = times_b[i] - mean_b
        num += da * db
        den_a += da * da
        den_b += db * db
    
    var denom = sqrt(den_a * den_b)
    if denom > 0.0:
        return Float32(num / denom)
    return 0.0

fn main():
    print("Causal Miner v0.26.1")
