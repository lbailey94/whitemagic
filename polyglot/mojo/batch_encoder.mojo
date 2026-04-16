"""Batch Encoder - Mojo 0.26.1 - Simplified for compilation"""

from math import sqrt

fn batch_encode_similarity(vectors: List[List[Float32]], query: List[Float32]) -> List[Float32]:
    """Batch encode and compute similarities."""
    var results = List[Float32]()
    for i in range(len(vectors)):
        var dot: Float32 = 0.0
        var mag_v: Float32 = 0.0
        var mag_q: Float32 = 0.0
        for j in range(len(query)):
            if j < len(vectors[i]):
                dot += vectors[i][j] * query[j]
                mag_v += vectors[i][j] * vectors[i][j]
                mag_q += query[j] * query[j]
        var denom = sqrt(mag_v * mag_q)
        if denom > 0.0:
            results.append(dot / denom)
        else:
            results.append(0.0)
    return results^

fn main():
    print("Batch Encoder v0.26.1")
