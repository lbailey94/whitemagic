"""HRR Engine - Mojo 0.26.1"""
from math import sqrt

fn hrr_bind(a: List[Float32], b: List[Float32]) -> List[Float32]:
    """Holographic Reduced Representation: binding via circular convolution."""
    var n = len(a)
    var result = List[Float32]()
    for i in range(n):
        var sum: Float32 = 0.0
        for j in range(n):
            var k = (i - j) % n
            if k < 0:
                k += n
            if j < len(b) and k < len(a):
                sum += a[k] * b[j]
        result.append(sum)
    return result^

fn hrr_similarity(a: List[Float32], b: List[Float32]) -> Float32:
    """Dot product similarity."""
    var dot: Float32 = 0.0
    var n = min(len(a), len(b))
    for i in range(n):
        dot += a[i] * b[i]
    return dot

fn main():
    print("HRR Engine v0.26.1")
