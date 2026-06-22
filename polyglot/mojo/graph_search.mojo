"""Graph Search - Mojo 0.26.1"""

fn bfs_distance(adj: List[List[Int]], start: Int, target: Int) -> Int:
    """BFS shortest path distance."""
    if start == target:
        return 0
    
    var visited = List[Bool]()
    for i in range(len(adj)):
        visited.append(False)
    
    var queue = List[Int]()
    var distances = List[Int]()
    
    queue.append(start)
    distances.append(0)
    visited[start] = True
    
    var head = 0
    while head < len(queue):
        var node = queue[head]
        var dist = distances[head]
        head += 1
        
        for i in range(len(adj[node])):
            var neighbor = adj[node][i]
            if not visited[neighbor]:
                if neighbor == target:
                    return dist + 1
                visited[neighbor] = True
                queue.append(neighbor)
                distances.append(dist + 1)
    
    return -1

fn main():
    print("Graph Search v0.26.1")
