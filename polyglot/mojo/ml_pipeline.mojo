"""ML Pipeline - Mojo 0.26.1"""
from math import sqrt

fn normalize_vector(v: List[Float32]) -> List[Float32]:
    """L2 normalize vector."""
    var sum_sq: Float32 = 0.0
    for i in range(len(v)):
        sum_sq += v[i] * v[i]
    var mag = sqrt(sum_sq)
    
    var result = List[Float32]()
    for i in range(len(v)):
        if mag > 0.0:
            result.append(v[i] / mag)
        else:
            result.append(0.0)
    return result^

fn batch_normalize(vectors: List[List[Float32]]) -> List[List[Float32]]:
    """Normalize batch of vectors."""
    var result = List[List[Float32]]()
    for i in range(len(vectors)):
        var normalized = normalize_vector(vectors[i])
        result.append(normalized^.copy())
    return result^

fn main():
    print("ML Pipeline v0.26.1")
