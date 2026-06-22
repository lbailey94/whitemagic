// Search Orchestration - Multi-Strategy Search (PSR-002)
module search_orchestration

effect search_orchestration
  fun lexical(query: string): list<string>
  fun semantic(query: string): list<string>
  fun fuse-results(results: list<list<string>>): list<string>

fun orchestrated-search(query: string): <search_orchestration> list<string>
  val lexical = search_orchestration/lexical(query)
  val semantic = search_orchestration/semantic(query)
  search_orchestration/fuse-results([lexical, semantic])
