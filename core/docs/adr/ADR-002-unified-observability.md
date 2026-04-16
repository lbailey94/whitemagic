# ADR-002: Unified Observability Pipeline

## Status
Accepted (v15.9)

## Context
WhiteMagic needed a unified observability strategy for monitoring tool performance, error rates, and system health. Previously, metrics were scattered across logging statements with no centralized collection.

## Decision
Implement a dual-track observability system:

1. **Prometheus** for metrics scraping (counters, gauges, histograms)
2. **OpenTelemetry** for distributed tracing (spans, context propagation)

Both are integrated into the middleware pipeline via `mw_observability`:

```python
def mw_observability(ctx: DispatchContext, next_fn: NextFn) -> dict[str, Any] | None:
    start = time.perf_counter()
    result = next_fn(ctx)
    duration = time.perf_counter() - start
    
    # Record to both backends
    _get_prometheus().record_tool_call(ctx.tool_name, duration, status)
    _get_otel().record_tool_span(ctx.tool_name, duration, status)
    
    return result
```

## Consequences

### Positive
- Single middleware handles both backends
- Graceful degradation when dependencies unavailable
- Consistent metric naming across systems
- HTTP endpoint for Prometheus scraping (port 9090)
- OTLP export for Jaeger/Tempo integration

### Negative
- Dual recording adds ~0.5ms overhead per call
- Additional dependencies (prometheus-client, opentelemetry-*)

### Mitigation
- Dependencies are optional; system works without them
- Overhead is negligible compared to typical tool latency (10-100ms)

## Configuration

### Prometheus
```bash
WM_PROMETHEUS_ENABLED=1 WM_PROMETHEUS_PORT=9090
```

### OpenTelemetry
```bash
WM_OTEL_ENABLED=1 OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
```

## Metrics Exposed

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `whitemagic_tool_calls_total` | Counter | tool | Total invocations |
| `whitemagic_tool_errors_total` | Counter | tool | Total errors |
| `whitemagic_tool_duration_seconds` | Histogram | tool | Duration buckets |
| `whitemagic_memory_count` | Gauge | type | Memory count by type |
| `whitemagic_cold_start_seconds` | Gauge | - | Cold start duration |
| `whitemagic_db_connections_active` | Gauge | - | Active DB connections |
| `whitemagic_circuit_breaker_state` | Gauge | tool | Breaker state (0/1/2) |

## References
- `whitemagic/core/monitoring/prometheus_export.py`
- `whitemagic/core/monitoring/otel_export.py`
- `whitemagic/tools/middleware.py:mw_observability`
