"""Embedding Index - Mojo 0.26.1"""
from math import sqrt

fn index_search(index: List[List[Float32]], query: List[Float32], k: Int) -> List[Int]:
    """Search flat index for top-k."""
    var scores = List[Float32]()
    for i in range(len(index)):
        var dot: Float32 = 0.0
        var mag_i: Float32 = 0.0
        var mag_q: Float32 = 0.0
        for j in range(len(query)):
            if j < len(index[i]):
                dot += index[i][j] * query[j]
                mag_i += index[i][j] * index[i][j]
                mag_q += query[j] * query[j]
        var denom = sqrt(mag_i * mag_q)
        if denom > 0.0:
            scores.append(dot / denom)
        else:
            scores.append(0.0)
    
    var topk = List[Int]()
    for i in range(min(k, len(scores))):
        var best = 0
        var best_score: Float32 = -1.0
        for j in range(len(scores)):
            if scores[j] > best_score:
                best_score = scores[j]
                best = j
        topk.append(best)
        scores[best] = -1.0
    return topk^

fn main():
    print("Embedding Index v0.26.1")
