"""Cosine Similarity Benchmark - Mojo 0.26.1 Compatible"""

from math import sqrt

fn cosine_similarity(a: List[Float32], b: List[Float32]) -> Float32:
    var dot: Float32 = 0.0
    var mag_a: Float32 = 0.0
    var mag_b: Float32 = 0.0
    var n = len(a)
    
    for i in range(n):
        dot += a[i] * b[i]
        mag_a += a[i] * a[i]
        mag_b += b[i] * b[i]
    
    var denom = sqrt(mag_a * mag_b)
    if denom > 0.0:
        return dot / denom
    return 0.0

fn main():
    var dim = 384
    var num_vecs = 1000
    
    # Build vectors
    var vecs = List[List[Float32]]()
    for i in range(num_vecs):
        var v = List[Float32]()
        for j in range(dim):
            v.append(Float32((i + j) % 100) / 100.0)
        vecs.append(v^.copy())
    
    # Query vector
    var q = List[Float32]()
    for j in range(dim):
        q.append(Float32(j % 100) / 100.0)
    
    # Compute similarities (no timing - compare externally)
    var total_sim: Float32 = 0.0
    for i in range(num_vecs):
        total_sim += cosine_similarity(vecs[i], q)
    
    print("Mojo 0.26.1 Results:")
    print(num_vecs, "vectors,", dim, "dimensions")
    print("Average similarity:", total_sim / Float32(num_vecs))
    print("Last similarity:", cosine_similarity(vecs[num_vecs-1], q))
