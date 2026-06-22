"""Vector Index - Mojo 0.26.1"""
from math import sqrt

fn vector_cosine(a: List[Float32], b: List[Float32]) -> Float32:
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

fn topk_search(vectors: List[List[Float32]], query: List[Float32], k: Int) -> List[Int]:
    var scores = List[Float32]()
    for i in range(len(vectors)):
        scores.append(vector_cosine(vectors[i], query))
    
    var indices = List[Int]()
    for i in range(min(k, len(scores))):
        var max_idx = 0
        var max_score: Float32 = -1.0
        for j in range(len(scores)):
            if scores[j] > max_score:
                max_score = scores[j]
                max_idx = j
        indices.append(max_idx)
        scores[max_idx] = -1.0
    return indices^

fn main():
    print("Vector Index v0.26.1 ready")
