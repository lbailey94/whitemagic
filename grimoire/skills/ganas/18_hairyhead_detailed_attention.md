---
name: wm-karma
description: "Karma tracking, anomaly detection, OpenTelemetry, salience, and voice audit"
version: 1.0.0
author: WhiteMagic Labs
license: MIT
platforms: [linux, macos, windows]
metadata:
  whitemagic:
    gana: gana_hairy_head
    tools: [anomaly, anomaly_check, anomaly_history, anomaly_status, otel_metrics, otel_spans, karma_report, karma_trace, karma_anchor, karma_verify, dharma_rules, salience]
    tags: [karma, anomaly, otel, salience, voice_audit, debug, tracing]
---

# Karma & Detailed Attention

Track karma (action consequences), detect anomalies, emit OpenTelemetry metrics/spans, measure salience, and audit voice output.

## When to Use

- Tracking the karma consequences of actions
- Detecting anomalous system behavior
- Emitting OpenTelemetry observability data
- Measuring salience of memories or events
- Auditing voice output for tone compliance
- Debugging via karma traces and anchors

## How to Invoke

```python
# Karma report
wm(route="gana_hairy_head.karma_report", args={})

# Karma trace
wm(route="gana_hairy_head.karma_trace", args={"action_id": "..."})

# Anomaly check
wm(route="gana_hairy_head.anomaly_check", args={})

# Anomaly history
wm(route="gana_hairy_head.anomaly_history", args={})

# OpenTelemetry metrics
wm(route="gana_hairy_head.otel_metrics", args={})

# Salience scoring
wm(route="gana_hairy_head.salience", args={"memory_id": "..."})
```
