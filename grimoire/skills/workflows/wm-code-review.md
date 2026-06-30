---
name: wm-code-review
description: "Review code changes for bugs, security issues, and improvements using WhiteMagic conventions"
version: 1.0.0
author: WhiteMagic Labs
license: MIT
platforms: [linux, macos, windows]
metadata:
  whitemagic:
    tags: [review, code, bugs, security, quality, ruff]
---

# Code Review

Perform a thorough code review identifying bugs, security issues, and improvements.

## When to Use

- After making code changes, before committing
- When reviewing a pull request
- As a pre-commit quality gate
- When investigating reported issues

## Workflow

1. **Identify changes** — `git diff` to see what changed
2. **Check for bugs** — Logic errors, edge cases, null references, race conditions
3. **Check security** — Injection vulnerabilities, improper resource management
4. **Check conventions** — PEP 8, type hints, absolute imports, ruff compliance
5. **Check path hygiene** — No `Path.home()` outside `config/paths.py`, no writes to repo root
6. **Check for stubs** — No empty methods, no simulated returns, no TODOs without dates
7. **Run linting** — `ruff check` on changed files
8. **Run tests** — Appropriate test tier for the change scope
9. **Report findings** — Categorize by severity (critical, warning, suggestion)

## Quality Gates

```bash
# Linting
ruff check <changed_files> --select F401,I001,E999,logging-f-string

# Type checking
python3 -c "import ast; ast.parse(open('file').read()); print('OK')"

# Test tiers
python -m pytest tests/unit/ -q --timeout=5 -x --tb=short          # Tier 1: <30s
python -m pytest tests/unit/ tests/integration/ -q --timeout=15     # Tier 2: <3min
python -m pytest tests/ --ignore=tests/archive* -q --timeout=30    # Tier 3: full
```

## Review Checklist

- [ ] No f-strings in logging calls (use %-style formatting)
- [ ] No `Path.home()` or `.expanduser()` outside `config/paths.py`
- [ ] All public functions have type hints
- [ ] No empty methods or stub returns
- [ ] Error handling returns stable JSON envelope
- [ ] Optional features fail safely (graceful degradation)
- [ ] No subprocess calls in unit tests (mock at class boundary)
- [ ] No network/socket calls in unit tests
- [ ] No ML model loading in unit tests
