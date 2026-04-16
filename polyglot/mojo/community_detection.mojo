"""Community Detection - Mojo 0.26.1"""
from math import sqrt

fn modularity_score(adj: List[List[Float32]], communities: List[Int]) -> Float32:
    """Compute modularity of community assignment."""
    var m: Float32 = 0.0
    var n = len(adj)
    
    for i in range(n):
        for j in range(n):
            m += adj[i][j]
    
    if m == 0.0:
        return 0.0
    
    var q: Float32 = 0.0
    for i in range(n):
        for j in range(n):
            if communities[i] == communities[j]:
                var ki: Float32 = 0.0
                var kj: Float32 = 0.0
                for k in range(n):
                    ki += adj[i][k]
                    kj += adj[j][k]
                q += (adj[i][j] - ki * kj / (2.0 * m)) / (2.0 * m)
    
    return q

fn main():
    print("Community Detection v0.26.1")
