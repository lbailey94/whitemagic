# Wu Xing Phases & Metrics Hooks (v2.2.7)

WhiteMagic v2.2.7 adds a continuous-operations layer that detects which phase of the Wu Xing cycle you're currently in, while streaming quantitative metrics through new MCP tools. This guide shows how to use both.

## 1. Wu Xing Cycle Detection

`whitemagic/wu_xing.py` exposes the `WuXingDetector`, `Phase`, and `Activity` primitives.

```python
from datetime import datetime
from whitemagic import WuXingDetector, Activity

detector = WuXingDetector(window_minutes=90)
activity_log = [
    Activity(datetime.now(), "read", reads=25),
    Activity(datetime.now(), "write", writes=15, files_changed=4),
]

phase, confidence, diagnostics = detector.detect_phase(activity_log)
print(phase.value, confidence, diagnostics["metrics"])
```

### Phase Glossary

| Phase | When it triggers | Recommended focus |
| --- | --- | --- |
| **WOOD (木)** | Heavy reading/searching, low edits | Research, context gathering |
| **FIRE (火)** | High write + churn, many file changes | Implementation bursts |
| **EARTH (土)** | Tests/documentation dominate | Stabilization, QA |
| **METAL (金)** | Numerous small edits, debugging | Refinement, polishing |
| **WATER (水)** | Idle or memory activity | Reflection, consolidation |

### Feeding Activities

You can pipe IDE events, git deltas, or `whitemagic workflow_patterns` counters into the detector. Minimum fields: timestamp, action, and one or more metrics (reads/writes/tests/etc.).

## 2. Linking Phases to Prompts

1. Run the detector after each batch of work (every ~15 minutes or when switching activities).
2. Use the result to adjust prompt tier + workflow:
   - WOOD → Tier 0 context, load more docs.
   - FIRE → Tier 1/2 with file deltas only.
   - EARTH → Require tests to pass before switching.
   - METAL → Invite targeted refactors, linting.
   - WATER → Trigger `whitemagic consolidate` or create memories.

`WorkflowPatterns.get_threading_tier()` pairs nicely with these phases to determine thread budget (8–256 threads as described in `whitemagic/workflow_patterns.py`).

## 3. MCP Metrics Toolkit

The MCP server now exposes two complementary tools:

### 3.1 track_metric

```typescript
await trackMetric(
  "token_efficiency",
  "usage_percent",
  48.2,
  "v2.2.7 Phase 2",
);
```

- **category** – high-level collection (token_efficiency, velocity, tactical, strategic, fatigue, etc.).
- **metric** – short key (`usage_percent`, `tests_per_hour`).
- **value** – numeric reading.
- **context** – free-form string (phase names, task IDs).

Values are appended to `~/.whitemagic/metrics/<category>.jsonl` so you can analyze time series locally or via BI dashboards.

### 3.2 get_metrics_summary

```typescript
const summary = await getMetricsSummary([
  "token_efficiency",
  "tactical",
]);
```

Returns counts, averages, and latest reading per category. Use it to populate dashboards (e.g., in Windsurf or Claude Desktop panels) or to gate workflow transitions (e.g., pause if usage percent exceeds 70%).

## 4. CLI + Automation Recipes

### CLI Proxy

Add helper scripts that call the MCP tools via `whitemagic-mcp`:

```bash
node cli/metrics.js track token_efficiency usage_percent 52.3 "Phase 3"
node cli/metrics.js summary token_efficiency tactical
```

(See `whitemagic-mcp/src/cli/metrics.ts` for reference implementation.)

### Git Hooks

1. Record `tests_run` metrics after CI: `trackMetric("tactical", "tests_passed", 194, "CI main")`.
2. Log token usage before/after running context commands.
3. Use `getMetricsSummary` inside dashboards to show rolling averages.

## 5. Best Practices

- **90-minute window default**: Adjust `WuXingDetector(window_minutes=60)` to better fit your cadence.
- **Yin/Yang balance**: Force a WATER phase after extended FIRE to prevent fatigue.
- **Metric hygiene**: Keep categories coarse (token_efficiency vs. `token_efficiency_phase1`). Use context fields for specifics.
- **Privacy**: Metrics stay local by default. If shipping to remote services, sanitize context strings.

## 6. Troubleshooting

| Symptom | Resolution |
| --- | --- |
| Detector always returns WATER | Ensure `Activity.timestamp` uses timezone-aware datetimes and log window is populated. |
| Metrics files missing | Confirm `WM_BASE_PATH` and home directory are writable; MCP server creates directories lazily. |
| Dashboard mismatch | `get_metrics_summary` caches results per call. Refresh before presenting critical numbers. |

Leverage these capabilities to keep AI+human workflows adaptive, measurable, and energy-aware.
