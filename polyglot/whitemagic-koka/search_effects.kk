// Search Effects - Effect-Typed Search Operations (PSR-002)
// Target: Clean effect handling for search operations

module search_effects

// Search effects
effect search
  fun lexical-search(query: string, limit: int): list<string>
  fun semantic-search(query: string, limit: int): list<string>
  fun hybrid-search(query: string, limit: int): list<string>

// Cache effect for search results
effect search-cache
  fun get-cached(query: string): maybe<list<string>>
  fun cache-results(query: string, results: list<string>): ()

// Ranking effect
effect ranking
  fun rank-results(results: list<string>): list<string>
  fun boost-score(result: string, factor: float64): ()

// Search with caching
fun cached-search(query: string, limit: int): <search, search-cache> list<string>
  match search-cache/get-cached(query)
    Just(results) -> results
    Nothing ->
      val results = search/hybrid-search(query, limit)
      search-cache/cache-results(query, results)
      results

// Multi-strategy search
fun multi-strategy-search(query: string, limit: int): <search, ranking> list<string>
  val lexical = search/lexical-search(query, limit)
  val semantic = search/semantic-search(query, limit)
  val combined = lexical ++ semantic
  ranking/rank-results(combined)

// Filtered search
fun filtered-search(query: string, limit: int, filter: string -> bool): <search> list<string>
  val results = search/hybrid-search(query, limit * 2)
  results.filter(filter).take(limit)

// Batch search
fun batch-search(queries: list<string>, limit: int): <search, search-cache> list<list<string>>
  queries.map fn(q)
    cached-search(q, limit)

// Search with boosting
fun boosted-search(query: string, limit: int, boost-terms: list<string>): <search, ranking> list<string>
  val results = search/hybrid-search(query, limit)
  boost-terms.foreach fn(term)
    results.foreach fn(result)
      if result.contains(term) then
        ranking/boost-score(result, 1.5)
  ranking/rank-results(results)
