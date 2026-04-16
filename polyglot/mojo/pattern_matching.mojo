"""Pattern Matching - Mojo 0.26.1"""
from math import sqrt

fn hamming_distance(a: List[Int], b: List[Int]) -> Int:
    """Count bit differences."""
    var dist = 0
    var n = min(len(a), len(b))
    for i in range(n):
        if a[i] != b[i]:
            dist += 1
    return dist

fn pattern_score(pattern: List[Float32], target: List[Float32]) -> Float32:
    """Correlation-based pattern match."""
    var dot: Float32 = 0.0
    var mag_p: Float32 = 0.0
    var mag_t: Float32 = 0.0
    
    var n = min(len(pattern), len(target))
    for i in range(n):
        dot += pattern[i] * target[i]
        mag_p += pattern[i] * pattern[i]
        mag_t += target[i] * target[i]
    
    var denom = sqrt(mag_p * mag_t)
    if denom > 0.0:
        return dot / denom
    return 0.0

fn main():
    print("Pattern Matching v0.26.1")
