---
name: wm-test-suite
description: "Test suite management — run tests, check durations, verify baseline, test purity"
version: 1.0.0
author: WhiteMagic Labs
license: MIT
platforms: [linux, macos, windows]
metadata:
  whitemagic:
    tags: [testing, pytest, tiers, durations, purity, flaky, baseline]
---

# Test Suite Management

Run tests at the appropriate tier, check for performance regressions, and maintain test purity.

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
- Use `WM_SILENT_INIT=1` to skip broker forwarding in sync tests
- Use `WM_STATE_ROOT` pointing to temp dir for test isolation

## Test Purity

Unit tests must NEVER:
- Spawn subprocesses (Julia, Elixir, Go) — mock at class boundary
- Load ML models (MiniLM, sentence-transformers) — patch `get_hrr_engine`
- Make network calls — mock or skip
- Start asyncio event loops in sync context
- Load production SQLite databases
