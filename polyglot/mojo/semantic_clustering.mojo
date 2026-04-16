"""Semantic Clustering - Mojo 0.26.1"""
from math import sqrt

fn euclidean_distance(a: List[Float32], b: List[Float32]) -> Float32:
    """Compute Euclidean distance."""
    var sum_sq: Float32 = 0.0
    var n = min(len(a), len(b))
    for i in range(n):
        var diff = a[i] - b[i]
        sum_sq += diff * diff
    return sqrt(sum_sq)

fn kmeans_assign(vectors: List[List[Float32]], centroids: List[List[Float32]]) -> List[Int]:
    """Assign each vector to nearest centroid."""
    var assignments = List[Int]()
    for i in range(len(vectors)):
        var min_dist: Float32 = 1e9
        var best = 0
        for j in range(len(centroids)):
            var d = euclidean_distance(vectors[i], centroids[j])
            if d < min_dist:
                min_dist = d
                best = j
        assignments.append(best)
    return assignments^

fn main():
    print("Semantic Clustering v0.26.1")
