"""Mojo 0.26.1 Compatibility Module - Math Utilities"""

from math import sqrt

fn dot_product(a: List[Float32], b: List[Float32]) -> Float32:
    var result: Float32 = 0.0
    var n = min(len(a), len(b))
    for i in range(n):
        result += a[i] * b[i]
    return result

fn magnitude_squared(v: List[Float32]) -> Float32:
    var result: Float32 = 0.0
    for i in range(len(v)):
        result += v[i] * v[i]
    return result

fn magnitude(v: List[Float32]) -> Float32:
    return sqrt(magnitude_squared(v))

fn cosine_similarity_compat(a: List[Float32], b: List[Float32]) -> Float32:
    var dot = dot_product(a, b)
    var mag_a = magnitude(a)
    var mag_b = magnitude(b)
    var denom = mag_a * mag_b
    if denom > 0.0:
        return dot / denom
    return 0.0

fn main():
    print("Mojo Compat v0.26.1 - Math utilities loaded")
