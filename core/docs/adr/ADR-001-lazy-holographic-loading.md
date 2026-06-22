# ADR-001: Lazy Holographic Index Loading

## Status
Accepted (v15.9)

## Context
WhiteMagic's holographic memory uses a 5D spatial index (x, y, z, w, v) for semantic clustering. At startup, the `UnifiedMemory` class eagerly loaded all 111,846 coordinates from SQLite into an in-memory `Holographic` index, causing cold start times of 4.7+ seconds.

## Decision
Implement lazy loading of the holographic index via a `@property` accessor:

```python
@property
def holographic(self):
    if not self._holographic:
        return None
    if self._holographic_loaded:
        return self._holographic
    with self._holographic_lock:
        # Load coordinates on first access
        coords_map = self.backend.get_all_coords()
        for mem_id, coords in coords_map.items():
            self._holographic.add_memory_with_coords(mem_id, *coords)
        self._holographic_loaded = True
    return self._holographic
```

## Consequences

### Positive
- Cold start reduced from 4.7s to 740ms (6.4x improvement)
- Memory footprint reduced until spatial queries are needed
- Thread-safe initialization prevents race conditions

### Negative
- First spatial query has ~300ms latency spike
- Code complexity increased slightly

### Mitigation
The first-spike latency is acceptable because:
1. Most operations (store, search, retrieve) don't need spatial queries
2. Users can warm the index proactively if needed
3. The spike is still far better than the previous 4.7s cold start

## Alternatives Considered

1. **Background loading**: Load in a daemon thread
   - Rejected: Adds complexity, potential race conditions, unpredictable timing

2. **Subset loading**: Load only "hot" memories
   - Rejected: Requires pre-computing hot set, adds complexity

3. **Skip index entirely**: Don't use holographic indexing
   - Rejected: Loses semantic clustering benefits

## References
- `whitemagic/core/memory/unified.py:67-99`
- `whitemagic/core/memory/sqlite_backend.py:get_all_coords()`
