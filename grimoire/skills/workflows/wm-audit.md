---
name: wm-audit
description: "Comprehensive system audit — stubs, tests, security, performance, documentation"
version: 1.0.0
author: WhiteMagic Labs
license: MIT
platforms: [linux, macos, windows]
metadata:
  whitemagic:
    tags: [audit, stubs, security, performance, documentation, strata]
---

# System Audit

Comprehensive audit of the WhiteMagic codebase covering stubs, tests, security, performance, and documentation.

## When to Use

- Periodic health checks
- Before major releases
- After large refactors
- When investigating technical debt

## Workflow

1. **Stub detection** — Search for empty methods, simulated returns, placeholders
   ```bash
   grep -rn "pass$\|NotImplemented\|TODO\|FIXME\|HACK" core/whitemagic/ --include="*.py" | grep -v __pycache__
   ```
2. **STRATA analysis** — Run static analysis via `wm(route="gana_chariot.strata")`
3. **Test suite health** — Run with durations to catch slow tests
   ```bash
   python -m pytest tests/unit/ -q --durations=10 --durations-min=1.0 --timeout=30
   ```
4. **Security scan** — Check for common vulnerabilities
   ```bash
   grep -rn "eval(\|exec(\|subprocess.call\|os.system" core/whitemagic/ --include="*.py" | grep -v __pycache__ | grep -v test
   ```
5. **Path hygiene** — Verify no writes outside WM_STATE_ROOT
6. **Doc drift** — `python scripts/check_doc_drift.py`
7. **Ruff lint** — `ruff check core/whitemagic/`
8. **Codebase archaeology** — `wm(route="gana_chariot.archaeology")` for history
9. **Generate report** — Store findings in `docs/reports/`

## Audit Report Format

```markdown
# Audit Report — <date>

## Summary
- Tests: X passed, Y failed, Z skipped
- Stubs found: N
- Security issues: N
- Performance regressions: N
- Doc drift: pass/fail

## Findings
### Critical
### Warnings
### Suggestions
```
