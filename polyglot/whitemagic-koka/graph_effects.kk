// Graph Effects - Effect-Typed Graph Operations (PSR-003)
// Target: Clean effect handling for graph operations

module graph_effects

// Graph operation effects
effect graph
  fun add-edge(source: string, target: string, weight: float64): ()
  fun get-neighbors(node: string): list<string>
  fun remove-edge(source: string, target: string): bool

// Graph traversal effects
effect traversal
  fun bfs(start: string, max-depth: int): list<string>
  fun dfs(start: string, max-depth: int): list<string>
  fun shortest-path(start: string, end: string): maybe<list<string>>

// Graph analysis effects
effect analysis
  fun compute-pagerank(iterations: int): list<(string, float64)>
  fun detect-communities(): list<list<string>>
  fun find-bridges(): list<(string, string)>

// Build graph from edges
fun build-graph(edges: list<(string, string, float64)>): <graph> ()
  edges.foreach fn(edge)
    val (src, tgt, weight) = edge
    graph/add-edge(src, tgt, weight)

// Walk graph with visitor pattern
fun walk-graph(start: string, visitor: string -> <graph> bool): <graph, traversal> list<string>
  val visited = traversal/bfs(start, 100)
  visited.filter(visitor)

// Find connected components
fun find-components(nodes: list<string>): <graph, traversal> list<list<string>>
  var components := []
  var remaining := nodes
  
  while !remaining.is-nil do
    match remaining
      Cons(node, rest) ->
        val component = traversal/bfs(node, 1000)
        components := Cons(component, components)
        remaining := rest.filter(fn(n) !component.contains(n))
      Nil -> ()
  
  components

// Analyze graph structure
fun analyze-structure(nodes: list<string>): <graph, analysis> (list<(string, float64)>, list<list<string>>)
  val ranks = analysis/compute-pagerank(20)
  val communities = analysis/detect-communities()
  (ranks, communities)

// Find critical paths
fun find-critical-paths(start: string, ends: list<string>): <graph, traversal> list<list<string>>
  ends.map fn(end)
    match traversal/shortest-path(start, end)
      Just(path) -> path
      Nothing -> []
