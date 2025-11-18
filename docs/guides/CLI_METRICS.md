# CLI Metrics Guide (v2.2.7)

WhiteMagic v2.2.7 keeps the comprehensive metrics stack introduced in earlier releases and pairs it with the new parallel/scratchpad infrastructure. This guide covers all metrics commands, how to pair them with the upcoming `whitemagic audit`, `docs-check`, and `exec plan` helpers, and best practices for keeping AI workflows measurable.

---

## 1. Quick Start

```bash
# Track a metric
whitemagic track token_efficiency usage_percent 45.2 "Phase 2 complete"

# View summary for one or more categories
whitemagic summary token_efficiency tactical

# Export metrics to file
whitemagic export token_efficiency --format json --output metrics.json
```

Metrics are stored in `~/.whitemagic/metrics/<category>.jsonl` as append-only logs.

---

## 2. Metrics Categories

WhiteMagic tracks six primary metric categories:

### 2.1 Token Efficiency

**Purpose**: Monitor token budget usage and optimization effectiveness

**Key Metrics**:

- `usage_percent` - Current token budget used (0-100)
- `tokens_saved` - Tokens saved by optimizations
- `efficiency_ratio` - Speedup factor (e.g., 17.9x)
- `tier_used` - Context tier loaded (0/1/2)

**Example** *(capture both raw usage + efficiency gains from the new parallel pools)*:

```bash
whitemagic track token_efficiency usage_percent 38.5 "After Tier 1 load"
whitemagic track token_efficiency efficiency_ratio 17.9 "Tier 1 vs baseline"
```

Pair this with the `whitemagic audit` command (v2.2.8) to ensure every session records token deltas before and after parallel pool bursts.

### 2.2 Velocity

**Purpose**: Track development speed and throughput

**Key Metrics**:

- `features_per_day` - Feature completion rate
- `bugs_fixed_per_session` - Bug resolution speed
- `files_modified_per_hour` - Code churn rate
- `commits_per_day` - Commit frequency

**Example** *(align sprint plans with Wu Xing + threading tiers so the audit report can map strategic progress to terrain assessments)*:

```bash
whitemagic track velocity features_per_day 3 "v2.2.7 week 1"
whitemagic track velocity bugs_fixed_per_session 5 "Debug marathon"
```

### 2.3 Tactical Progress

**Purpose**: Measure task-level execution

**Key Metrics**:

- `tasks_complete` - Completed tasks count
- `tests_passing` - Test pass count
- `tests_total` - Total test count
- `coverage_percent` - Code coverage (0-100)

**Example** *(align sprint plans with Wu Xing + threading tiers so the audit report can map strategic progress to terrain assessments)*:

```bash
whitemagic track tactical tests_passing 194 "Test suite run"
whitemagic track tactical tasks_complete 7 "Phase 1 done"
```

### 2.4 Strategic Progress

**Purpose**: Track high-level goals and milestones

**Key Metrics**:

- `version_progress` - Version completion (0-100)
- `milestones_hit` - Milestone count
- `timeline_variance` - Ahead/behind schedule (hours)
- `scope_completion` - Feature scope done (0-100)

**Example** *(log review + documentation coverage before/after running `whitemagic docs-check`)*:

```bash
whitemagic track strategic version_progress 75 "v2.2.7 75% complete"
whitemagic track strategic timeline_variance -12 "12 hours ahead"
```

### 2.5 Quality

**Purpose**: Monitor code and output quality

**Key Metrics**:

- `bugs_introduced` - New bugs per session
- `rollback_count` - Times had to revert changes
- `review_score` - Code quality rating (1-10)
- `documentation_coverage` - Docs completion (0-100)

**Example**:

```bash
whitemagic track quality review_score 9 "Phase 2 code review"
whitemagic track quality bugs_introduced 0 "Clean session!"
```

### 2.6 Fatigue (AI & Human)

**Purpose**: Monitor cognitive load and workflow health

**Key Metrics**:

- `stress_level` - Subjective stress (0-10)
- `context_switches` - Task switching count
- `session_duration_hours` - Time spent working
- `break_frequency` - Breaks taken per session

**Example**:

```bash
whitemagic track fatigue stress_level 2 "Feeling good"
whitemagic track fatigue session_duration_hours 4.5 "Afternoon session"
```

---

## 3. Command Reference

### 3.1 `whitemagic track`

**Syntax**:

```bash
whitemagic track <category> <metric> <value> [context]
```

**Arguments**:

- `category` - One of: token_efficiency, velocity, tactical, strategic, quality, fatigue
- `metric` - Short metric name (e.g., `usage_percent`, `tests_passing`)
- `value` - Numeric value (float or int)
- `context` - Optional description (e.g., "Phase 2", "v2.2.7")

**Examples**:

```bash
# Simple tracking
whitemagic track tactical tests_passing 194

# With context
whitemagic track token_efficiency usage_percent 42.5 "Mid-session checkpoint"

# Negative values allowed
whitemagic track strategic timeline_variance -8 "8 hours ahead of schedule"
```

**Output**:

```
✅ Metric tracked: tactical.tests_passing = 194
   Context: [no context provided]
   File: ~/.whitemagic/metrics/tactical.jsonl
```

---

### 3.2 `whitemagic summary`

**Syntax**:

```bash
whitemagic summary [categories...] [--days N] [--format FORMAT]
```

**Arguments**:

- `categories` - One or more categories (default: all)
- `--days N` - Include only last N days (default: 30)
- `--format` - Output format: `table` (default), `json`, `markdown`

**Examples**:

```bash
# Summary of all categories (last 30 days)
whitemagic summary

# Specific categories
whitemagic summary token_efficiency tactical

# Last 7 days only
whitemagic summary --days 7

# JSON output for scripts
whitemagic summary token_efficiency --format json
```

**Output** (table format):

```
📊 Metrics Summary (Last 30 Days)

Category: token_efficiency
┏━━━━━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━┳━━━━━━━━┳━━━━━━━┓
┃ Metric         ┃ Count ┃ Mean   ┃ Min    ┃ Max   ┃
┡━━━━━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━╇━━━━━━━━╇━━━━━━━┩
│ usage_percent  │    45 │  38.2  │  12.0  │  68.5 │
│ efficiency_... │     8 │  16.7  │   9.2  │  19.4 │
└────────────────┴───────┴────────┴────────┴───────┘

Category: tactical
┏━━━━━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━┳━━━━━━━━┳━━━━━━━┓
┃ Metric         ┃ Count ┃ Mean   ┃ Min    ┃ Max   ┃
┡━━━━━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━╇━━━━━━━━╇━━━━━━━┩
│ tests_passing  │    23 │ 189.4  │  165   │  194  │
│ tasks_complete │    15 │   5.2  │    2   │   12  │
└────────────────┴───────┴────────┴────────┴───────┘
```

---

### 3.3 `whitemagic export`

**Syntax**:

```bash
whitemagic export [categories...] [OPTIONS]
```

**Options**:

- `--format FORMAT` - Export format: `json`, `csv`, `jsonl` (default: json)
- `--output FILE` - Output file path (default: stdout)
- `--days N` - Include only last N days
- `--pretty` - Pretty-print JSON (json format only)

**Examples**:

```bash
# Export all metrics to JSON
whitemagic export --format json --output metrics.json

# Export specific categories to CSV
whitemagic export token_efficiency tactical --format csv --output metrics.csv

# Last 7 days, pretty JSON
whitemagic export --days 7 --format json --pretty --output weekly.json

# Pipe to other tools
whitemagic export token_efficiency --format jsonl | jq '.value'
```

**JSON Format**:

```json
{
  "token_efficiency": [
    {
      "timestamp": "2025-11-16T14:30:00Z",
      "metric": "usage_percent",
      "value": 38.5,
      "context": "After Tier 1 load"
    }
  ],
  "tactical": [...]
}
```

**CSV Format**:

```csv
category,timestamp,metric,value,context
token_efficiency,2025-11-16T14:30:00Z,usage_percent,38.5,"After Tier 1 load"
tactical,2025-11-16T14:45:00Z,tests_passing,194,"Test suite run"
```

---

## 4. Workflow Integration

### 4.1 Session Start/End Protocol

**Session Start**:

```bash
# Baseline token check
whitemagic track token_efficiency usage_percent 0 "Session start"
whitemagic track fatigue stress_level 0 "Fresh start"
```

**Session End**:

```bash
# Final metrics
whitemagic track token_efficiency usage_percent 55.5 "Session complete"
whitemagic track tactical tasks_complete 7 "Phase 1 done"
whitemagic track fatigue session_duration_hours 6 "Full session"

# Generate summary
whitemagic summary --days 1
```

### 4.2 Phase Boundaries

Track metrics at every phase transition:

```bash
# Phase 1 complete
whitemagic track tactical tasks_complete 4 "Phase 1: CLI commands"
whitemagic track token_efficiency usage_percent 35 "Post-Phase 1"

# Phase 2 start
whitemagic track strategic version_progress 40 "40% v2.2.7 complete"
```

### 4.3 Git Hooks

Automate tracking with git hooks:

**`.git/hooks/post-commit`**:

```bash
#!/bin/bash
# Track commits
whitemagic track velocity commits_per_day 1 "$(git log -1 --pretty=%B)"

# Count files changed
FILES_CHANGED=$(git diff HEAD~1 --name-only | wc -l)
whitemagic track velocity files_modified $FILES_CHANGED "Latest commit"
```

**`.git/hooks/pre-push`**:

```bash
#!/bin/bash
# Count passing tests
TESTS_PASSING=$(pytest --co -q | grep "test" | wc -l)
whitemagic track tactical tests_passing $TESTS_PASSING "Pre-push validation"
```

### 4.4 CI/CD Integration

Add the forthcoming automation commands to your workflow once v2.2.8 lands:

```bash
# Verify docs + versions before CI
whitemagic audit --strict
whitemagic docs-check docs/ README.md
```

```bash
# Stage batched terminal operations for approvals
whitemagic exec plan plan.yaml
```

**GitHub Actions** (`.github/workflows/metrics.yml`):

```yaml
name: Track Metrics
on: [push, pull_request]

jobs:
  metrics:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Install WhiteMagic
        run: pip install whitemagic

      - name: Run tests
        id: tests
        run: |
          pytest --junitxml=report.xml
          PASSING=$(xmllint --xpath "count(//testcase)" report.xml)
          echo "passing=$PASSING" >> $GITHUB_OUTPUT

      - name: Track test metrics
        run: |
          whitemagic track tactical tests_passing ${{ steps.tests.outputs.passing }} "CI: ${{ github.sha }}"

      - name: Export metrics artifact
        run: whitemagic export --format json --output metrics.json

      - uses: actions/upload-artifact@v3
        with:
          name: metrics
          path: metrics.json
```

---

## 5. Analysis & Visualization

### 5.1 Time Series Analysis

```bash
# Export for analysis
whitemagic export token_efficiency --format jsonl --days 30 > tokens.jsonl

# Plot with Python
python3 << EOF
import json
import matplotlib.pyplot as plt
from datetime import datetime

data = [json.loads(line) for line in open('tokens.jsonl')]
timestamps = [datetime.fromisoformat(d['timestamp']) for d in data]
values = [d['value'] for d in data]

plt.plot(timestamps, values)
plt.xlabel('Date')
plt.ylabel('Token Usage %')
plt.title('Token Efficiency Over Time')
plt.savefig('token_efficiency.png')
EOF
```

### 5.2 Dashboard Integration

Export to dashboard (e.g., Grafana, custom React app):

```bash
# Export for v2.2.7 React dashboard
whitemagic export --format json --pretty --output dashboard/data/metrics.json

# Or serve via API
whitemagic api --enable-metrics-endpoint
```

### 5.3 Alerts & Thresholds

```bash
# Check if token usage exceeds 70%
USAGE=$(whitemagic summary token_efficiency --format json | jq '.token_efficiency.usage_percent.latest')

if (( $(echo "$USAGE > 70" | bc -l) )); then
    echo "⚠️  Token budget > 70%! Consider consolidation or session break."
    whitemagic track fatigue stress_level 7 "Token budget warning"
fi
```

---

## 6. Best Practices

### 6.1 Frequency

**Track often, but not obsessively**:

- ✅ Start/end of sessions
- ✅ Phase boundaries
- ✅ After significant changes (tests pass, features complete)
- ❌ Not every single command

### 6.2 Context Strings

Use consistent, meaningful context strings:

- ✅ `"v2.2.7 Phase 1 complete"`
- ✅ `"After Tier 1 optimization"`
- ✅ `"Debug session - auth bug"`
- ❌ `"stuff"`
- ❌ `"test"`

### 6.3 Metrics Hygiene

- Keep categories coarse (use context for details)
- Use standard metric names consistently
- Don't create new categories without reason
- Consolidate/export periodically (storage management)

### 6.4 Privacy

Metrics stay local by default. If exporting:

- Sanitize context strings (remove sensitive info)
- Review JSON/CSV before sharing
- Use `.gitignore` for metrics files if in repo

---

## 7. Troubleshooting

### Issue: "Metrics file not found"

**Cause**: Metrics directory doesn't exist yet

**Solution**: Track any metric to create directory structure:

```bash
whitemagic track tactical test 1 "Initialize"
```

### Issue: "Summary shows no data"

**Check**:

1. Are metrics within the time window? Try `--days 365`
2. Correct category name? Use `whitemagic summary` (no args) to see all
3. Metrics file corrupted? Verify `~/.whitemagic/metrics/<category>.jsonl` is valid JSONL

### Issue: "Export fails with 'invalid JSON'"

**Cause**: Corrupted JSONL file (incomplete write)

**Solution**:

```bash
# Validate and fix
cat ~/.whitemagic/metrics/tactical.jsonl | jq -c . > fixed.jsonl
mv fixed.jsonl ~/.whitemagic/metrics/tactical.jsonl
```

---

## 8. Advanced: Custom Metrics

### 8.1 Add New Categories

Edit `whitemagic/cli/app.py` to add custom categories:

```python
METRIC_CATEGORIES = [
    "token_efficiency",
    "velocity",
    "tactical",
    "strategic",
    "quality",
    "fatigue",
    "custom_category",  # Add here
]
```

### 8.2 Automated Tracking

Create wrapper scripts for automatic metric collection:

```bash
#!/bin/bash
# track_session.sh - Wrap work sessions with automatic metrics

start_time=$(date +%s)
whitemagic track fatigue stress_level 0 "Session start"

# Do work...
"$@"

end_time=$(date +%s)
duration=$(( (end_time - start_time) / 3600 ))
whitemagic track fatigue session_duration_hours $duration "Session complete"
```

Usage:

```bash
./track_session.sh python cli.py work-on-feature
```

---

## 9. Integration with Wu Xing

Metrics pair with Wu Xing phase detection (v2.2.7) for adaptive workflows:

```python
from whitemagic import WuXingDetector, Activity
from datetime import datetime

# Detect current phase
detector = WuXingDetector()
activities = [Activity(datetime.now(), "write", writes=20)]
phase, confidence, _ = detector.detect_phase(activities)

# Track phase-specific metrics
if phase.value == "FIRE":
    # High implementation phase - track velocity
    track_metric("velocity", "files_modified_per_hour", 12, "FIRE phase")
elif phase.value == "WATER":
    # Reflection phase - consolidate
    track_metric("fatigue", "stress_level", 1, "WATER phase - relaxed")
```

---

## 10. Future Enhancements (v2.2.7+)

Planned improvements:

- **Real-time dashboard** (React + D3 visualization)
- **Metric predictions** (forecast token usage, estimate completion time)
- **Automated alerts** (Slack/email when thresholds crossed)
- **Multi-user tracking** (team metrics aggregation)
- **Metric templates** (pre-configured metric sets for common workflows)

---

## Summary

CLI metrics in v2.2.7 provide quantitative visibility into your AI workflow:

✅ **Track 6 categories** - token efficiency, velocity, tactical, strategic, quality, fatigue
✅ **Simple commands** - `track`, `summary`, `export`
✅ **Workflow integration** - git hooks, CI/CD, dashboards
✅ **Privacy-first** - all data stays local
✅ **Actionable insights** - identify bottlenecks, optimize processes

Start tracking today:

```bash
whitemagic track token_efficiency usage_percent 0 "First metric!"
whitemagic summary
```

---

**See also**:

- `WU_XING_AND_METRICS.md` - Combine metrics with phase detection
- `META_OPTIMIZATION.md` - Track optimization effectiveness
- `QUICKSTART.md` - Basic CLI usage
