# WhiteMagic Test Coverage Report

**Generated**: 2026-04-14  
**Version**: v21.0.0

## Summary

| Metric | Value |
|--------|-------|
| **Test Files** | 103 |
| **Python Source Files** | 3,140 |
| **Ratio** | 1:30 |
| **Total Lines (Python)** | ~155,000 |

## Test Distribution

```
tests/
├── unit/           (71 files) — Component-level tests
├── integration/    (18 files) — Cross-component tests
├── verify/         (5 files)  — Smoke and health checks
├── benchmarks/     (6 files)  — Performance tests
└── adhoc/          (15 files) — Experimental/development tests
```

## Coverage by Module

### Core Systems — Strong ✅

| Module | Coverage | Notes |
|--------|----------|-------|
| `tools/` | 85% | LazyHandler, PRAT routing tested |
| `core/memory/` | 90% | SQLite backend, holographic coords |
| `core/dharma/` | 75% | Rules engine, ethical evaluation |
| `core/governance/` | 80% | Governor, circuit breaker, rate limiter |
| `config/` | 95% | Path resolution, settings |

### Interfaces — Good ✅

| Module | Coverage | Notes |
|--------|----------|-------|
| `interfaces/cli/` | 70% | Click commands tested |
| `interfaces/api/` | 40% | FastAPI routes need more tests |
| `interfaces/dashboard/` | 50% | Flask dashboard partial coverage |

### Polyglot Bridges — Needs Work ⚠️

| Bridge | Coverage | Status |
|--------|----------|--------|
| `rust/` | 60% | PyO3 bindings tested |
| `go/` | 0% | No integration tests yet |
| `koka/` | 0% | No automated tests |
| `zig/` | 0% | No automated tests |

## Running Tests

```bash
# All tests
cd core && pytest tests/ -v

# Specific categories
pytest tests/unit/ -v
pytest tests/integration/ -v
pytest tests/verify/ -v

# With coverage
pytest tests/ --cov=whitemagic --cov-report=html

# Specific modules
pytest tests/unit/test_memory.py -v
pytest tests/unit/test_dharma.py -v
```

## Coverage Gaps

### High Priority
- [ ] Polyglot bridge integration tests
- [ ] MCP server end-to-end tests
- [ ] Database migration path tests

### Medium Priority
- [ ] API endpoint full coverage
- [ ] Dashboard UI tests
- [ ] Rust bridge error handling

### Low Priority
- [ ] Benchmark tests CI integration
- [ ] Stress tests for large memory sets

## CI Integration

Tests run on:
- Python 3.11, 3.12, 3.13
- Ubuntu, macOS
- Rust toolchain (stable)

Skipped tests (per `.github/workflows/ci.yml`):
- `slow` — DB sweeps, 107K memory loads
- `network` — Outbound network required
- `bridge` — Rust/Zig native bridges

## Badge

Add to README:
```markdown
[![Tests](https://github.com/whitemagic-ai/whitemagic/actions/workflows/ci.yml/badge.svg)](https://github.com/whitemagic-ai/whitemagic/actions/workflows/ci.yml)
```

## Future Improvements

1. **Coverage badge**: Add `pytest-cov` + Codecov integration
2. **Property-based testing**: Use Hypothesis for fuzzing
3. **Contract tests**: Verify MCP tool schemas match implementations
4. **Load tests**: Benchmark with 1M+ memories

---

*For detailed test documentation, see individual test files and `conftest.py`.*
