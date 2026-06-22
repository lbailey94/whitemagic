// Phase 14 Enterprise: Service 144
package enterprise

import (
    "context"
    "log"
    "time"
    "github.com/prometheus/client_golang/prometheus"
    "go.opentelemetry.io/otel/trace"
)

type EnterpriseHandler struct {
    metrics *prometheus.CounterVec
    tracer  trace.Tracer
}

func (h *EnterpriseHandler) HandleWithObservability(
    ctx context.Context,
    req Request,
) (*Response, error) {
    ctx, span := h.tracer.Start(ctx, "handle_request")
    defer span.End()

    start := time.Now()
    resp, err := h.process(ctx, req)
    duration := time.Since(start)

    h.metrics.WithLabelValues("duration").Inc()
    log.Printf("Request processed in %v", duration)

    return resp, err
}
