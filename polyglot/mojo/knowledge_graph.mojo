"""Knowledge Graph - Mojo 0.26.1"""

fn pagerank_step(adj: List[List[Float32]], ranks: List[Float32], damping: Float32) -> List[Float32]:
    """Single PageRank iteration."""
    var n = len(adj)
    var new_ranks = List[Float32]()
    
    for i in range(n):
        var sum: Float32 = 0.0
        for j in range(n):
            var out_sum: Float32 = 0.0
            for k in range(n):
                out_sum += adj[j][k]
            if out_sum > 0.0:
                sum += adj[j][i] * ranks[j] / out_sum
        new_ranks.append((1.0 - damping) / Float32(n) + damping * sum)
    
    return new_ranks^

fn main():
    print("Knowledge Graph v0.26.1")
