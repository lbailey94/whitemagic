# WhiteMagic API Quick Reference — v15.9

## Core Memory Operations

### Store Memory
```python
from whitemagic.core.memory.unified import get_unified_memory

um = get_unified_memory()
memory_id = um.store(
    content="Important insight about consciousness",
    tags={"insight", "consciousness"},
    metadata={"source": "meditation", "importance": 0.8}
)
```

### Retrieve Memory
```python
memory = um.get_memory(memory_id)
print(memory.content)
print(memory.tags)
```

### Search Memories
```python
# Full-text search
results = list(um.backend.search("consciousness", limit=10))

# Vector similarity search
similar = um.search_similar("consciousness and awareness", limit=5)
```

### List Recent
```python
recent = list(um.backend.list_recent(limit=20, memory_type="episodic"))
```

## Embedding Operations

### Single Embedding
```python
from whitemagic.core.memory.embeddings import EmbeddingEngine

engine = EmbeddingEngine()
embedding = engine.encode("text to embed")  # Returns 384-dim vector
```

### Batch Embedding
```python
embeddings = engine.encode_batch(["text 1", "text 2", "text 3"])
# Returns list of 384-dim vectors, ~312/sec throughput
```

## Graph Operations

### Get Associations
```python
associations = um.backend.get_associations(memory_id)
# Returns dict[target_id -> strength]
```

### Traverse Graph
```python
# Batch traversal (optimized)
visited = set()
frontier = [start_id]
while frontier and len(visited) < 100:
    placeholders = ','.join('?' * len(frontier))
    cursor = conn.execute(f'''
        SELECT target_id FROM associations WHERE source_id IN ({placeholders})
        UNION SELECT source_id FROM associations WHERE target_id IN ({placeholders})
    ''', frontier + frontier)
    new_frontier = [row[0] for row in cursor.fetchall() if row[0] not in visited]
    visited.update(new_frontier)
    frontier = new_frontier[:50]
```

## Observability

### Prometheus Metrics
```python
from whitemagic.core.monitoring.prometheus_export import get_prometheus, start_prometheus_server

# Start HTTP server on port 9090
start_prometheus_server()

# Record custom metric
prom = get_prometheus()
prom.record_tool_call("my_tool", 0.042, "success")
```

### OpenTelemetry Traces
```python
from whitemagic.core.monitoring.otel_export import get_otel

otel = get_otel()
otel.record_tool_span("my_tool", 0.042, "success")

# Get recent spans
spans = otel.recent_spans(limit=20)

# Get metrics summary
summary = otel.metrics_summary()
```

## Circuit Breaker

### Check Status
```python
from whitemagic.tools.circuit_breaker import get_breaker_registry

registry = get_breaker_registry()
status = registry.get("ollama.generate").status()
# {'tool': 'ollama.generate', 'state': 'closed', 'recent_failures': 0, ...}
```

### All Breakers
```python
all_status = registry.all_status()
tripped = registry.tripped()  # Only breakers that have tripped
```

## Error Handling

### Retry with Backoff
```python
from whitemagic.core.memory.db_manager import retry_with_backoff

@retry_with_backoff
def flaky_db_operation():
    # Automatically retries on transient SQLite errors
    # (BUSY, LOCKED, PROTOCOL)
    ...
```

## Environment Variables

```bash
# Performance
WM_SILENT_INIT=1           # Suppress startup logs
WM_SKIP_HOLO_INDEX=1       # Skip holographic index entirely

# Observability
WM_PROMETHEUS_ENABLED=1    # Enable Prometheus metrics
WM_PROMETHEUS_PORT=9090    # Prometheus HTTP port
WM_OTEL_ENABLED=1          # Enable OpenTelemetry
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317

# Security
WM_DB_PASSPHRASE=secret    # SQLCipher encryption key
```

## Performance Characteristics

| Operation | p50 | p95 | Notes |
|-----------|-----|-----|-------|
| Cold start | 740ms | - | First load |
| Store | 26ms | 71ms | After warmup |
| FTS search | 8ms | 10ms | Optimized index |
| Embedding (batch) | 3.2ms/each | - | 100+ batch size |
| Graph 100-hop | 315ms | - | Batch queries |

## Database Locations

| Database | Path | Purpose |
|----------|------|---------|
| Primary | `~/.whitemagic/memory/whitemagic.db` | Active memories |
| Cold storage | `~/.whitemagic/memory/whitemagic_cold.db` | Archived memories |
| Galaxy | `~/.whitemagic/memory/galaxies/{name}/whitemagic.db` | Per-client isolation |
