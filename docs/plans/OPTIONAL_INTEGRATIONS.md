# WhiteMagic Optional Integrations

WhiteMagic ships with zero external vendors enabled by default. Use this guide to plug in third-party services when you’re ready.

> Tip: `pip install -r requirements-plugins.txt` installs every optional dependency referenced below in one shot.

---

## 1. Sentry (Error Tracking)

**Why:** Capture stack traces, request context, and release metadata whenever an exception bubbles out of FastAPI.

**How to enable:**

```bash
pip install "sentry-sdk[fastapi]>=2.6.5"
export SENTRY_DSN="https://public@sentry.io/123456"
export SENTRY_TRACES_SAMPLE_RATE=0.1   # optional
export ENVIRONMENT=production
```

WhiteMagic detects `SENTRY_DSN` at startup and auto-initializes the FastAPI integration. Remove the variable (or uninstall `sentry-sdk`) to disable it again.

---

## 2. Logtail / LogDNA / Papertrail (Log Shipping)

**Why:** Ship structured JSON logs to a managed log search UI.

**How to enable:** point your container logs to the collector of choice (e.g., sidecar agent, Docker logging driver). WhiteMagic already formats logs as JSON when `LOG_FORMAT=json`, so most services ingest them without changes.

Recommended services (see `requirements-plugins.txt` for optional helpers):

- [Logtail](https://logtail.com)
- [Papertrail](https://papertrailapp.com)
- [Vector.dev](https://vector.dev) (self-hosted)

---

## 3. PostHog or Segment (Product Analytics)

**Why:** Track adoption of dashboard features or API usage events outside of raw logs.

**How to enable:** instrument the dashboard frontend (React) with the vendor’s snippet. No backend changes are required.

---

## 4. Prometheus / Grafana (Metrics)

**Why:** Collect latency, throughput, and resource metrics.

**How to enable:** run the API behind an ingress/controller that scrapes `/metrics` (add the endpoint via [`prometheus-fastapi-instrumentator`](https://github.com/trallnag/prometheus-fastapi-instrumentator)) and expose it to Prometheus. This keeps the core app vendor-neutral while letting you add metrics when needed.

---

Each integration is opt-in. Keep this document updated as you add more plugin hooks (e.g., email providers, feature flags). PRs welcome!
