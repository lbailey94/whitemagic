---
description: WhiteMagic test suite management — run tests, check durations, verify baseline
---

# WhiteMagic Test Suite

## Test Tiers
```bash
# Tier 1: Fast feedback (<30s) — during active development
cd core && python -m pytest tests/unit/ -q --timeout=5 -x --tb=short

# Tier 2: Medium validation (<3min) — before commit
python -m pytest tests/unit/ tests/integration/ -q --timeout=15 --tb=short

# Tier 3: Full suite — release verification
python -m pytest tests/ --ignore=tests/archive_v14 --ignore=tests/archive_v11 --ignore=tests/archive --ignore=tests/archive_polyglot --ignore=tests/legacy --ignore=tests/adhoc --ignore=tests/verify -q --timeout=30
```

## Performance Regression Check
```bash
python -m pytest tests/unit/ -q --durations=10 --durations-min=1.0 --timeout=30
```

## Rules
- No unit test >5s without explicit skip reason
- No integration test >15s without skip reason
- Suite runtime >10% growth → investigate before merging
- Never mark tests flaky — fix the root cause
- Unit tests must mock subprocesses, ML models, network, event loops
