"""Association Miner - Mojo 0.26.1"""
from math import sqrt

fn similarity_score(a: List[Float32], b: List[Float32]) -> Float32:
    var dot: Float32 = 0.0
    var mag_a: Float32 = 0.0
    var mag_b: Float32 = 0.0
    for i in range(len(a)):
        dot += a[i] * b[i]
        mag_a += a[i] * a[i]
        mag_b += b[i] * b[i]
    var denom = sqrt(mag_a * mag_b)
    if denom > 0.0:
        return dot / denom
    return 0.0

fn main():
    print("Association Miner v0.26.1")
