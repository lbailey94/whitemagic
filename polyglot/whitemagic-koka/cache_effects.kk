// Cache Effects - Caching Operations (PSR-001/002)
module cache_effects

effect cache
  fun get(key: string): maybe<string>
  fun set(key: string, value: string, ttl: int): ()
  fun invalidate(key: string): ()

fun cached-operation(key: string, compute: () -> <div> string): <cache, div> string
  match cache/get(key)
    Just(v) -> v
    Nothing ->
      val result = compute()
      cache/set(key, result, 3600)
      result
