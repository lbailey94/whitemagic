// Memory Effects - Effect-Typed Memory Operations (PSR-001)
// Target: Clean effect handling for memory operations

module memory_effects

// Memory operation effects
effect memory
  fun store(key: string, value: string): ()
  fun retrieve(key: string): maybe<string>
  fun delete(key: string): bool

// Transaction effect
effect transaction
  fun begin(): ()
  fun commit(): ()
  fun rollback(): ()

// Cache effect
effect cache
  fun get(key: string): maybe<string>
  fun set(key: string, value: string, ttl: int): ()
  fun invalidate(key: string): ()

// Memory operation with effects
fun store-with-cache(key: string, value: string): <memory, cache> ()
  cache/set(key, value, 3600)
  memory/store(key, value)

// Transactional memory operation
fun transactional-store(key: string, value: string): <memory, transaction> bool
  transaction/begin()
  memory/store(key, value)
  transaction/commit()
  True

// Retrieve with cache fallback
fun retrieve-cached(key: string): <memory, cache> maybe<string>
  match cache/get(key)
    Just(v) -> Just(v)
    Nothing ->
      match memory/retrieve(key)
        Just(v) ->
          cache/set(key, v, 3600)
          Just(v)
        Nothing -> Nothing

// Batch operations
fun batch-store(items: list<(string, string)>): <memory, transaction> ()
  transaction/begin()
  items.foreach fn(item)
    val (k, v) = item
    memory/store(k, v)
  transaction/commit()

// Memory cleanup
fun cleanup-expired(keys: list<string>): <memory, cache> int
  var count := 0
  keys.foreach fn(key)
    cache/invalidate(key)
    if memory/delete(key) then
      count := count + 1
  count
