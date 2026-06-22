"""HRR - Holographic Reduced Representation - Mojo 0.26.1"""
from math import sqrt

fn circular_convolution(a: List[Float32], b: List[Float32]) -> List[Float32]:
    """Circular convolution for HRR binding."""
    var n = len(a)
    var result = List[Float32]()
    for i in range(n):
        var sum: Float32 = 0.0
        for j in range(n):
            var k = i - j
            while k < 0:
                k += n
            while k >= n:
                k -= n
            if k < len(a) and j < len(b):
                sum += a[k] * b[j]
        result.append(sum)
    return result^

fn approx_inverse(v: List[Float32]) -> List[Float32]:
    """Approximate inverse for unbinding."""
    var result = List[Float32]()
    result.append(v[0])
    for i in range(1, len(v)):
        result.append(v[len(v) - i])
    return result^

fn main():
    print("HRR v0.26.1")
