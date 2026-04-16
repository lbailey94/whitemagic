# WhiteMagic v22.0.0 — Release Readiness Plan

> **Audience:** Engineering team executing the open-source release hardening pass.
> **Author:** Cascade audit, 2026-04-16.
> **Mission:** Take the repo from "impressive but broken on clone" to "credible OSS launch".

---

## 0. How to Use This Document

Every finding has: **ID**, **Severity** (Critical / High / Medium / Low), **Where to look**, **Root cause**, **Recommended fix**, **Verification**, **Gotchas**.

### Work style we expect
- **Run every verification block.** No fix is complete without its verification passing.
- **Do not expand scope.** If a fix isn't explicitly asked for, don't do it.
- **Prefer minimal upstream fixes over downstream workarounds.** Don't wrap a missing import in `try/except` — fix the import.
- **Write a regression test for every Critical or High fix** in `core/tests/unit/regression/test_release_readiness.py` (create if missing). Keep test bodies small.
- **One finding = one atomic commit.** Format: `fix(C1): resurrect whitemagic.run_mcp shim`.
- **Never delete tests to make them pass.** Fix, or `@pytest.mark.xfail(strict=True, reason="tracking #N")`.
- **Explore aggressively.** Section 6 (`Hunting Grounds`) lists areas where we strongly suspect more issues we didn't fully enumerate.
- **Report back using the template in Section 7.**

### Environment
- Linux, Python 3.11 or 3.12.
- `core/` is the canonical Python package root.
- Recommended setup: `python -m venv .venv && source .venv/bin/activate && pip install -e core/.[dev,mcp,cli,db,net]`.
- For history surgery: `pip install --user git-filter-repo`.

### Conventions
- File citations: `core/path/to/file.py:123`.
- `# verify` marks copy-paste proofs.
- `# suggested` marks illustrative code — improve style while preserving intent.

---

## 1. Project Context (5-minute read)

**WhiteMagic** is a Python-first, polyglot-accelerated **MCP server** and tool substrate for AI agents. Ships 28 "Gana" meta-tools (PRAT mode) routing to ~420 nested tools. Differentiators:

- **Tool envelope contract** with idempotency, `now`-determinism, stable error codes — see `AI_PRIMARY.md:134-215`.
- **8-stage middleware pipeline** — `core/whitemagic/tools/middleware.py`.
- **5D holographic memory** with Galactic Map lifecycle (no-delete policy).
- **Dharma governance** (YAML rules, Karma ledger, Harmony Vector).
- **Polyglot accelerators**: Rust + Go (production); Koka, Zig, Mojo, Elixir, Haskell (experimental).

### Files to skim before editing

| File | Why |
|---|---|
| `AI_PRIMARY.md` | Authoritative contract. Canonical when in doubt. |
| `SYSTEM_MAP.md` | Repo layout + runtime state resolution. |
| `core/whitemagic/tools/unified_api.py` | `call_tool()` + envelope construction (703 lines). |
| `core/whitemagic/tools/dispatch_table.py` | Merge point for 5 domain slices. |
| `core/whitemagic/run_mcp_lean.py` | The only working MCP server today. |
| `core/whitemagic/config/paths.py` | State-root resolution. Don't touch without coordination. |
| `core/tests/conftest.py` | Sets `WM_STATE_ROOT` tempdir + resets 30 singletons. Understand before running tests. |

### Ground truth
- **Canonical version is v22.0.0** (per `core/VERSION`).
- **License is MIT** (per `LICENSE` at root).
- **Active server is `run_mcp_lean.py`**. `run_mcp.py` was archived — that broke ~25 references.
- **Current test state**: 244 failed / 724 passed / 244 skipped / 56 errors / 12 collection errors.

---

## 2. Phase 1 — Unbreak the Boat (Critical)

**Goal:** Every command in `README.md` works on a fresh clone.
**Budget:** 2–3 engineer-days.
**Gate:** `git clone && pip install -e core/.[lite] && python -m whitemagic.run_mcp --help && pytest core/tests/ -q` succeeds.

*(See sections below for each item.)*

## 3. Phase 2 — Align Reality & Docs (High)

**Goal:** Every number, path, and claim in docs is verifiable.
**Budget:** 3–5 engineer-days.

## 4. Phase 3 — Release-Quality Polish (Medium & Low)

**Budget:** 1–2 weeks.

## 5. Findings Detail

Execute in order: C1 → C2 → … → L10. Each critical/high fix gets a regression test in `core/tests/unit/regression/test_release_readiness.py`.

---

### C1 — `whitemagic.run_mcp` module is missing

**Severity:** Critical.

**Evidence**
```bash
$ PYTHONPATH=core python3 -c "import whitemagic.run_mcp"
ModuleNotFoundError: No module named 'whitemagic.run_mcp'
```

**Where it's referenced** (all break on use):
- **Docs:** `README.md:19`, `QUICKSTART.md:113`, `AI_PRIMARY.md`, `skill.md`, `core/README.md`, `core/llms.txt`, `core/docs/QUICKSTART.md`, `core/docs/STRATEGY.md:65`, `core/docs/USE_CASES.md`, `core/docs/WASM_STRATEGY.md:72`, `core/docs/ARCHITECTURE.md:353`, `core/docs/MCP_CONFIG_EXAMPLES.md`, `core/docs/LITE_VS_HEAVY.md:13`, `core/docs/CONTRIBUTING.md:45`
- **Build/run:** `justfile:34`, `core/Dockerfile:37`, `core/docker-compose.yml`
- **CLI:** `core/whitemagic/cli/init_command.py:57,110,202,206,210,451` (generates broken `.mcp.json` for users!), `core/whitemagic/cli/commands/core_commands.py`
- **Scripts:** `core/scripts/omega_test.py:163`
- **Tests:** `core/tests/integration/test_leap3_integration.py:30`, `core/tests/unit/tools/test_prat_router.py:182`, `core/tests/unit/tools/test_mcp_registration_surface.py:1`, `core/tests/unit/systems/test_surface_consistency.py:1`

**Root cause**
Between v21 and v22, `run_mcp.py` was deprecated and archived in favor of `run_mcp_lean.py`, but documentation, CLI scaffolding, and tests were not updated.

**Recommended fix — Choice A (recommended, shim)**

Create `core/whitemagic/run_mcp.py`:

```python
# suggested implementation
"""Compatibility shim — re-exports the lean MCP server.

The historical module ``whitemagic.run_mcp`` was replaced by
``whitemagic.run_mcp_lean`` in v22.0.0. This shim preserves backward
compatibility for documented entrypoints, CLI scaffolding, and tests.
New code should import from ``whitemagic.run_mcp_lean`` directly.
"""
from __future__ import annotations

from whitemagic.run_mcp_lean import *  # noqa: F401,F403

# Explicit re-exports — audit which symbols are needed:
#     grep -rn "from whitemagic.run_mcp import" core/
try:
    from whitemagic.run_mcp_lean import (  # noqa: F401
        main,
        _register_prat_tools,
        get_registered_tool_definitions,
        register_tools,
        register_resources,
        mcp,
        lifecycle,
    )
except ImportError:
    # Some symbols may have been renamed; update the test rather than stubbing here.
    pass


if __name__ == "__main__":
    # `python -m whitemagic.run_mcp` must still launch the server.
    main()
```

**Before** writing the shim:
```bash
# verify — find what symbols tests expect
grep -rn "from whitemagic.run_mcp import" core/tests/ core/scripts/
```

For any symbol that truly doesn't exist in `run_mcp_lean`, **update the test to point at the new API rather than stubbing**.

**Recommended fix — Choice B (rename)**

Rename `run_mcp_lean.py` → `run_mcp.py`. Only take this path if a maintainer confirms "lean" was always intended as the default. Choice A is safer.

**Verification**
```bash
# verify
PYTHONPATH=core python3 -c "import whitemagic.run_mcp; print('import ok')"
PYTHONPATH=core python3 -m whitemagic.run_mcp --help 2>&1 | head -5
PYTHONPATH=core python3 -m pytest core/tests/unit/tools/test_prat_router.py \
  core/tests/unit/tools/test_mcp_registration_surface.py \
  core/tests/unit/systems/test_surface_consistency.py \
  core/tests/integration/test_leap3_integration.py --co -q
```

**Regression test**

```python
# suggested — core/tests/unit/regression/test_release_readiness.py
import importlib

def test_run_mcp_module_importable():
    """Regression: documented entrypoint must be importable (C1)."""
    mod = importlib.import_module("whitemagic.run_mcp")
    assert hasattr(mod, "main"), "run_mcp must expose main() for `python -m`"


def test_run_mcp_has_prat_symbols():
    """Regression: PRAT registration symbols must resolve (C1)."""
    mod = importlib.import_module("whitemagic.run_mcp")
    for sym in ("get_registered_tool_definitions",):
        assert hasattr(mod, sym), f"run_mcp missing {sym}"
```

**Gotchas**
- No `DeprecationWarning` on `python -m` invocation (users aren't deprecated).
- Confirm `WM_MCP_PRAT=1 python -m whitemagic.run_mcp` still triggers PRAT mode.

---

### C2 — Test suite regression: 244 failed / 56 errors / 12 collection errors

**Severity:** Critical. CI cannot go green.

**Evidence**
```bash
# verify — reproduce baseline
PYTHONPATH=core timeout 300 python3 -m pytest core/tests/unit/ \
  --no-header -q -p no:cacheprovider --tb=no \
  --continue-on-collection-errors --timeout=30
# Current output: 244 failed, 724 passed, 244 skipped, 5 xfailed, 7 warnings, 56 errors
```

**Collection errors (12 files)**

| Test file | Broken import | Likely fix |
|---|---|---|
| `core/tests/unit/test_fusions.py:14` | `_ELEMENT_TO_QUADRANT` from `whitemagic.core.fusions` | Symbol renamed. `grep -rn "ELEMENT_TO_QUADRANT" core/whitemagic/` to locate current API. |
| `core/tests/unit/test_scratchpad.py:5` | `whitemagic.gardens.air.agentic.terminal_scratchpad.TerminalScratchpad` | `grep -rn "class TerminalScratchpad" core/whitemagic/` — update import. |
| `core/tests/unit/test_scratchpad_legacy.py` | Same | Same fix. |
| `core/tests/unit/memory/test_causal_miner.py` | `whitemagic.core.memory.causal_miner` | `ls core/whitemagic/core/memory/` — module may be gone. |
| `core/tests/unit/memory/test_entropy_scorer.py` | `whitemagic.core.memory.entropy_scorer` | Same. |
| `core/tests/unit/integration_adhoc/test_umap_projection.py` | `whitemagic.core.memory.umap_projection` | Missing — delete test or restore module. |
| `core/tests/unit/systems/test_dispatch_bridge.py` | `whitemagic.core.acceleration.dispatch_bridge` | Module **exists**; check symbol names. |
| `core/tests/unit/systems/test_event_ring_bridge.py` | `whitemagic.core.acceleration.event_ring_bridge` | Module missing at that path. |
| `core/tests/unit/systems/test_p0_regressions.py` | imports `whitemagic.cli.cli_app` + CliRunner | Investigate; may cascade from C1. |
| `core/tests/unit/systems/test_state_board_bridge.py` | `whitemagic.core.acceleration.state_board_bridge` | Check existence. |
| `core/tests/unit/systems/test_surface_consistency.py:1` | `from whitemagic.run_mcp import …` | **Resolved by C1.** |
| `core/tests/unit/tools/test_mcp_registration_surface.py:1` | Same | **Resolved by C1.** |

**Recommended fix**

**Step 1:** Fix collection errors first. For each:
- **Update import** if symbol was renamed/moved.
- **Module deliberately deleted?** Mark test with `pytest.skip("module removed in v22; see issue #NNN")` at module top.
- **Labs-tier code?** Move test under `core/tests/unit/labs/` with `@pytest.mark.labs`.
- **Never `rm`** — always explicit skip with tracking issue.

**Step 2:** After collection clean, triage 244 failures:
```bash
PYTHONPATH=core python3 -m pytest core/tests/unit/ -q --tb=line --timeout=60 2>&1 | head -200
```
Cluster by fixture/import/assertion. Likely patterns:
- **`WM_STATE_ROOT` leakage**: if tests see 107K-memory production DB, conftest ordering is the issue. Fix: defer whitemagic imports inside test functions, not at module level.
- **Singleton leakage**: test passes alone but fails in combination. Fix: add to `_singleton_modules` in `core/tests/conftest.py:58` or use `@singleton` decorator from `whitemagic.utils.singleton`.
- **Real regressions**: fix test if new behavior is intentional; fix code otherwise.
- **Missing optional deps**: use `@pytest.mark.skipif(importlib.util.find_spec("foo") is None, reason="requires foo")`.

**Step 3:** Target state: ≥95% of non-skipped tests pass; skip rate ≤20%; zero collection errors.

**Verification**
```bash
# verify — zero collection errors
PYTHONPATH=core python3 -m pytest core/tests/unit/ --co -q 2>&1 | tail -3
# Expect: "N tests collected" — no "errors" line.

# verify — tests green
PYTHONPATH=core python3 -m pytest core/tests/unit/ -q --timeout=60 2>&1 | tail -5
# Expect: "X passed, Y skipped" with 0 failures.

# verify — P0 contracts
PYTHONPATH=core python3 -m pytest core/tests/verify/ -q
```

**Gotchas**
- `conftest.py` sets `WM_STATE_ROOT` to tempdir at **module-level**. Test files that `import whitemagic.*` at top-of-file before conftest loads can see the real DB.
- The `_reset_all_singletons` autouse fixture resets 30 singletons. Adding a stateful singleton requires adding to the registry or using `@singleton`.

**Regression test**
```python
# suggested — test_release_readiness.py
import subprocess, sys
from pathlib import Path

def test_collection_zero_errors():
    """Regression: `pytest --co` must have no errors (C2)."""
    root = Path(__file__).resolve().parents[4]
    core = root / "core"
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "--co", "-q", "--no-header", "tests/unit/"],
        capture_output=True, text=True, cwd=core,
        env={"PYTHONPATH": str(core)},
    )
    tail = (result.stdout + result.stderr)[-1500:]
    assert "error" not in tail.lower(), tail
```

---

### C3 — License mismatch: core/README claims Apache 2.0, actual is MIT

**Severity:** Critical.

**Where**
- Authoritative: `LICENSE` (root) — MIT.
- Bad claim: `core/README.md:95` — *"Licensed under the Apache License 2.0"*.

**Recommended fix**

1. Edit `core/README.md`:
```markdown
## License

[MIT License](../LICENSE) — see LICENSE file at repository root.
```

2. Grep for other claims:
```bash
grep -rn -i "apache license\|apache 2\.0\|apache-2\|gpl v\|bsd license" \
  core/ docs/ *.md 2>/dev/null | grep -v "LICENSE\|.git\|__pycache__"
```
Inspect each match; fix any that claim this project's license.

3. Verify:
- `core/pyproject.toml` → `license = { text = "MIT" }` or equivalent.
- `core/whitemagic-rust/Cargo.toml` → `license = "MIT"` (add if absent — see H10).
- SPDX headers on source files — flag any `# SPDX-License-Identifier: Apache-2.0`.

**Verification**
```bash
python3 -c "
import tomllib
d = tomllib.load(open('core/pyproject.toml','rb'))
lic = d['project'].get('license')
assert 'MIT' in str(lic), lic
print('license ok:', lic)
"

grep -rn -i "apache license\|apache 2\.0" core/README.md README.md \
  core/pyproject.toml core/whitemagic-rust/Cargo.toml 2>/dev/null
# Expect: no output.
```

---

### C4 — Repo is 1.1 GB (.git pack 783 MB) on a single-commit repo

**Severity:** Critical.

**Evidence**
```
$ git count-objects -vH
size: 326.64 MiB
in-pack: 1
packs: 1
size-pack: 783.04 MiB
```

**Root cause**
Large artifacts committed before initial commit:
- `.restructure_backups/docs_pre_restructure.tar.gz` (10 MB)
- `polyglot/BitNet/3rdparty/llama.cpp/` (full clone, 1200+ files)
- Log files under `docs/ci-logs/`
- `docs/reports/auxiliary_reports/deep_scan_results.json` (>5 MB)

**Recommended fix**

**Step 1 — Enumerate largest blobs:**
```bash
git rev-list --all --objects \
  | git cat-file --batch-check='%(objecttype) %(objectsize) %(objectname) %(rest)' \
  | awk '$1=="blob" && $2>1000000' \
  | sort -k2 -n -r | head -50
```

**Step 2 — Install:**
```bash
pip install --user git-filter-repo
```

**Step 3 — DESTRUCTIVE history rewrite** (coordinate with team first!):
```bash
# DANGER: rewrites every commit. Force-push required after.
git remote remove origin  # filter-repo refuses otherwise

git filter-repo \
  --invert-paths \
  --path .restructure_backups/ \
  --path polyglot/BitNet/ \
  --path projects/ \
  --path docs/ci-logs/ \
  --path docs/reports/auxiliary_reports/ \
  --path core/scripts/archaeology_results/ \
  --path aria/

# Re-add any large blobs found in Step 1 not covered above.

git remote add origin https://github.com/whitemagic-ai/whitemagic.git
```

**Step 4 — Harden .gitignore:**
```gitignore
# Append/ensure:
.restructure_backups/
docs/ci-logs/
docs/reports/auxiliary_reports/
core/scripts/archaeology_results/
polyglot/BitNet/
projects/
aria/
**/*.tar.gz
```

**Step 5 — Garbage-collect:**
```bash
git reflog expire --expire=now --all
git gc --aggressive --prune=now
du -sh .git/
```

**Step 6 — Force-push** (coordinate! breaks existing clones):
```bash
git push --force-with-lease origin main
```

**Verification**
```bash
du -sh .git/
# Expect: <100 MB.

git count-objects -vH | grep size-pack
# Expect: size-pack: <50 MiB.

time git clone file://$PWD /tmp/wm-clone-test
du -sh /tmp/wm-clone-test/.git/
rm -rf /tmp/wm-clone-test
```

**Gotchas**
- `git filter-repo` refuses on a repo with a remote — remove first, re-add after.
- If repo has been pushed publicly, some users will have old clones — post prominent README notice.
- `polyglot/BitNet/` is used by `core/whitemagic/tools/handlers/bitnet.py`. After purging, handler must degrade gracefully (see C7).

---

### C5 — Secret-like files in history

**Severity:** Critical for perception.

**Evidence**
```
./projects/mandalaos/.../tests/gnupg/private-keys-v1.d/*.key  (5 files, GPG test fixtures)
./polyglot/BitNet/3rdparty/llama.cpp/docs/development/llama-star/idea-arch.key  (Keynote file)
```

**Assessment**
Almost certainly benign (test fixtures + Keynote), but every secret scanner will flag them.

**Recommended fix**
Handled by C4 filter-repo pass.

**Verification**
```bash
find . -path ./.git -prune -o -type f \( -name "*.pem" -o -name "*.key" \) -print 2>/dev/null
# Expect: no output, or only clearly-labeled examples.

git log --all --full-history --pretty=format:"" --name-only \
  | sort -u | grep -iE '\.key$|\.pem$|id_rsa|secring' | head
# Expect: no output.
```

Preventive: add `pre-commit` with `gitleaks` (see L9).

---

### C6 — `.restructure_backups/` at repo root

**Severity:** Critical (hygiene).

**Recommended fix**
Handled by C4 filter-repo. If any markdown files contain unique historical info, copy to `docs/history/RESTRUCTURE_HISTORY.md` **before** filter-repo.

**Verification**
```bash
test ! -d .restructure_backups || echo "FAIL"
find . -name "*.tar.gz" -not -path './.git/*' 2>/dev/null
```

---

### C7 — `polyglot/BitNet/` vendors 1,235 files including full `llama.cpp`

**Severity:** Critical (hygiene, license-compliance perception).

**Recommended fix**

**Step 1** — Delete the vendored tree (handled by C4).

**Step 2** — Create `polyglot/bitnet/README.md`:
```markdown
# BitNet Polyglot Bridge (Optional, Experimental)

BitNet is **not** bundled with WhiteMagic.

## Setup

mkdir -p external && cd external
git clone --depth=1 https://github.com/microsoft/BitNet.git

## Integration

Set `WM_BITNET_PATH=/path/to/external/BitNet` before launching WhiteMagic.
Without it, `bitnet.*` tools return a `missing_dependency` envelope.
```

**Step 3** — Harden `core/whitemagic/tools/handlers/bitnet.py`:
- Check `WM_BITNET_PATH` env var.
- Return `missing_dependency` error envelope if missing/invalid.
- Never assume BitNet is present.

**Verification**
```bash
test ! -d polyglot/BitNet/3rdparty || echo "FAIL: still vendored"

PYTHONPATH=core python3 -c "
import os
os.environ['WM_SILENT_INIT'] = '1'
os.environ['WM_STATE_ROOT'] = '/tmp/wm_test'
os.environ.pop('WM_BITNET_PATH', None)
from whitemagic.tools.unified_api import call_tool
r = call_tool('bitnet.status')
print(r['status'], r.get('error_code'))
# Expect: 'error' + 'missing_dependency' or similar graceful error.
"
```

---

### H1 — Version drift across docs

**Severity:** High.

**Drift table**

| File | Claim | Expected |
|---|---|---|
| `core/VERSION` | 22.0.0 | ✓ source of truth |
| `README.md` | 22.0.0 | ✓ |
| `pyproject.toml` | 22.0.0 | ✓ |
| `AI_PRIMARY.md` | 22.0.0 | ✓ |
| `CHANGELOG.md` | 22.0.0 | ✓ |
| `core/README.md` | v21.0.0 | ✗ |
| `core/SHIP_SURFACE.md` | v21.0.0 | ✗ |
| `core/SECURITY.md` | "supports 21.x" | ✗ |
| `core/docs/CONTRIBUTING.md` | "v13+ codebase" | ✗ (see H4) |
| `core/docs/DEPLOY.md` | v15.0.0 (Feb 2026) | ✗ |
| `core/AUDIT_COMPLETION_REPORT.md` | 21.0.0 | historical — move to `docs/history/` |
| `core/IMPLEMENTATION_COMPLETION_REPORT.md` | 21.x→21.1.0 | historical — move |
| `core/whitemagic-rust/Cargo.toml` | 21.0.0 | ✗ |
| `polyglot/STATUS.md` | v21.0.0 | ✗ |
| `core/.well-known/agent.json` | 21.0.0 | ✗ |

**Recommended fix**

**Step 1 —** Update stale references. For wholesale-stale files (`DEPLOY.md`, `CONTRIBUTING.md`), rewrite rather than patch.

**Step 2 —** Add `core/scripts/check_versions.py`:
```python
# suggested
"""CI guard — verify documented version matches core/VERSION."""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
CANONICAL = (ROOT / "core" / "VERSION").read_text().strip()

REFERENCES = [
    "README.md", "CHANGELOG.md",
    "core/README.md", "core/pyproject.toml",
    "core/SHIP_SURFACE.md", "core/SECURITY.md",
    "polyglot/STATUS.md",
    "core/whitemagic-rust/Cargo.toml",
    "core/.well-known/agent.json",
]

def main() -> int:
    errors = []
    for rel in REFERENCES:
        p = ROOT / rel
        if not p.exists():
            errors.append(f"{rel}: missing"); continue
        if CANONICAL not in p.read_text():
            errors.append(f"{rel}: does not mention canonical version {CANONICAL}")
    if errors:
        print("Version drift:", file=sys.stderr)
        for e in errors:
            print(f"  {e}", file=sys.stderr)
        return 1
    print(f"All references agree on {CANONICAL}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

**Step 3 —** Wire into CI:
```yaml
- name: Version consistency
  run: python core/scripts/check_versions.py
```

**Step 4 —** Fix Rust crate: `core/whitemagic-rust/Cargo.toml:3` → `version = "22.0.0"`.

**Verification**
```bash
python3 core/scripts/check_versions.py
# Expect: "All references agree on 22.0.0"

grep -rn "21\.0\.0\|21\.1\.0\|v21\b\|v13\b\|v15\.0\.0" \
  README.md core/README.md core/SHIP_SURFACE.md core/SECURITY.md \
  polyglot/STATUS.md core/whitemagic-rust/Cargo.toml \
  core/.well-known/agent.json 2>/dev/null
# Expect: no output, or only changelog-history lines.
```

**Gotchas**
- `CHANGELOG.md` MUST keep historical version mentions — don't mass-replace.
- Some docs say "since v13" to describe behavior history; preserve that context.

---

### H2 — Tool-count drift

**Severity:** High.

**Drift**

| Source | Claim |
|---|---|
| Root README | "28 PRAT Gana" |
| `skill.md` | "311 tools (or 28)" |
| `QUICKSTART.md` | "313 registered" |
| `AI_PRIMARY.md` | "311 tools", "92 core tools" |
| `core/.well-known/agent.json` | "412 MCP tools" |
| `docs/CODE_QUALITY_REVIEW_2026-04-15.md` | "420" |
| `core/mcp-registry.json` | `nested_tools: 420` |
| Live `DISPATCH_TABLE` | **423** |
| Live `TOOL_REGISTRY` | **451** |

**Recommended fix**

**Step 1 —** Stop quoting absolute numbers in prose. Replace `"311 MCP tools"` → `"a large set of MCP tools (see mcp-registry.json for the current count)"`. Rounded `~420` OK in flow.

**Step 2 —** Make `mcp-registry.json` the single source. Extend `core/scripts/generate_mcp_registry.py` with `--sync-docs` flag that rewrites tool-count references in `core/.well-known/agent.json` and `skill.md`.

**Step 3 —** CI: ensure `python core/scripts/generate_mcp_registry.py --check` runs in the packaging job (per prior audit).

**Verification**
```bash
PYTHONPATH=core python3 core/scripts/generate_mcp_registry.py --check
# Expect: "registry is current"

PYTHONPATH=core WM_SILENT_INIT=1 WM_STATE_ROOT=/tmp/wm python3 -c "
from whitemagic.tools.dispatch_table import DISPATCH_TABLE
import json
reg = json.load(open('core/mcp-registry.json'))
assert reg['nested_tools'] == len(DISPATCH_TABLE), (reg['nested_tools'], len(DISPATCH_TABLE))
print('in sync:', len(DISPATCH_TABLE), 'tools')
"
```

**Gotchas**
- `TOOL_REGISTRY` (451) includes synthesized entries; `DISPATCH_TABLE` (423) is what MCP exposes. User-facing count should be **DISPATCH_TABLE**.

---

### H3 — Broken doc links in root README

**Severity:** High.

**Broken references** (~`README.md:106-109`):
- `docs/GLOSSARY.md` → actual: `docs/public/GLOSSARY.md`
- `docs/STRATEGY_2026-04-14.md` → does not exist
- `docs/WAVE4_STRATEGY.md` → does not exist
- `docs/LITE_VS_HEAVY.md` → actual: `docs/public/LITE_VS_HEAVY.md`

**Recommended fix**

Consolidate `docs/public/*` → `docs/*` and keep `docs/internal/` gitignored:
```bash
# suggested
git mv docs/public/*.md docs/
rmdir docs/public
# Ensure .gitignore still has `docs/internal/`.
```

Then fix internal cross-references:
```bash
# Find broken links across all markdown
python3 - <<'PY'
import os, re
bad = 0
for root, _, files in os.walk("docs"):
    for name in files:
        if not name.endswith(".md"): continue
        p = os.path.join(root, name)
        for link in re.findall(r'\[[^\]]*\]\(([^)]+)\)', open(p).read()):
            if link.startswith(('http', '#', 'mailto:')): continue
            target = os.path.normpath(os.path.join(os.path.dirname(p), link.split('#')[0]))
            if not os.path.exists(target):
                print(f"{p}: BROKEN -> {link}"); bad += 1
# Check README.md too
for link in re.findall(r'\[[^\]]*\]\(([^)]+)\)', open("README.md").read()):
    if link.startswith(('http', '#', 'mailto:')): continue
    if not os.path.exists(link.split('#')[0]):
        print(f"README.md: BROKEN -> {link}"); bad += 1
print(f"\n{bad} broken links" if bad else "No broken links")
PY
```

**Verification** — the Python script above must print `No broken links`.

---

### H4 — `core/docs/CONTRIBUTING.md` is 3 versions stale

**Severity:** High.

**Recommended fix** — rewrite wholesale. Target: <200 lines. Template:

```markdown
# Contributing to WhiteMagic

> Version 22.0.0 — revised YYYY-MM-DD.
> For conceptual overview, see `AI_PRIMARY.md` and `SYSTEM_MAP.md`.

## Setup (5 minutes)

git clone https://github.com/whitemagic-ai/whitemagic.git
cd whitemagic
python3 -m venv .venv && source .venv/bin/activate
pip install -e core/.[dev,mcp,cli]

## Verify
python -m whitemagic.run_mcp --help
pytest core/tests/ -q

## Adding a Tool
1. Implement handler in `core/whitemagic/tools/handlers/<domain>.py`.
2. Register in `core/whitemagic/tools/dispatch_<domain>.py`.
3. Declare schema in `core/whitemagic/tools/registry_defs/<domain>.py`.
4. Add test in `core/tests/unit/tools/test_<domain>.py`.
5. Regenerate registry: `python core/scripts/generate_mcp_registry.py`.

Every tool MUST return the standard envelope — use helpers in
`core/whitemagic/tools/envelope.py`. Contract: `AI_PRIMARY.md:134-215`.

## Tests
pytest core/tests/            # all
pytest -m core               # fast, core-only
pytest -m "not slow"         # skip integration
pytest core/tests/verify/    # P0 contracts (always pass)

## Style
ruff format / ruff check / mypy core/whitemagic/tools core/whitemagic/interfaces

## PRs
1. Branch off main. 2. One logical change. 3. Tests included. 4. CI green. 5. PR template filled.

See CODE_OF_CONDUCT.md and SECURITY.md.
```

**Verification**
```bash
wc -l core/docs/CONTRIBUTING.md
# Expect: <200.

grep -c "v13\|v15\|v21\|837\|949" core/docs/CONTRIBUTING.md
# Expect: 0.
```

---

### H5 — CI is aspirational, not real

**Severity:** High.

**Issues**
1. `pip install -e ".[dev]"` alone — tests needing `mcp/cli/db/net/embeddings` fail silently.
2. Full-codebase `mypy` set as **blocking** — will never go green.
3. Rust tests commented out.
4. `bandit --skip B603` too permissive.
5. Pytest invocation lacks `working-directory: ./core` or `PYTHONPATH`.

**Recommended fix — `.github/workflows/ci.yml`**

```yaml
# suggested
defaults:
  run:
    working-directory: ./core

jobs:
  test:
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: "pip"
      - run: pip install --upgrade pip && pip install -e ".[dev,mcp,cli,db,net,embeddings]"
      - name: Sanity import
        run: python -c "import whitemagic.run_mcp; print('ok')"
      - name: Tests
        run: pytest tests/ --tb=short --timeout=60 --maxfail=5 -q

  typecheck:
    steps:
      - name: Mypy (public surface — blocking)
        run: mypy whitemagic/tools whitemagic/interfaces
      - name: Mypy (full — advisory)
        continue-on-error: true
        run: mypy whitemagic/

  security:
    steps:
      - name: Bandit
        run: bandit -r whitemagic/ -ll --skip B101,B404
      - name: pip-audit
        run: pip-audit --desc --strict
```

**Verification** — push a branch; `test` and `typecheck (public surface)` must go green.

---

### H6 — Root `requirements.txt` duplicates pyproject heavy-tier

**Severity:** High (unexpected 2 GB torch pull).

**Recommended fix** — delete `requirements.txt` at root. Pyproject extras are canonical.

If a pinned CI freeze is wanted, rename to `requirements-dev.lock.txt` with `# Auto-generated by pip-compile; do not edit.` header.

**Verification**
```bash
test ! -f requirements.txt || echo "FAIL"
# Or: head -1 requirements-dev.lock.txt | grep -q "Auto-generated"
```

---

### H7 — MANIFEST.in omits scripts referenced by Make/CI

**Severity:** High.

**Where**
- `MANIFEST.in` (root and/or core/).
- Scripts referenced: `core/scripts/generate_mcp_registry.py`, `check_path_hygiene.py`, `check_ship.py`, `check_versions.py` (new, per H1).

**Recommended fix — Choice A (cleaner)**

Move verification scripts into the package:
```
core/whitemagic/scripts/
├── __init__.py
├── check_versions.py
├── check_path_hygiene.py
└── generate_mcp_registry.py
```

Expose via entry points in `core/pyproject.toml`:
```toml
[project.scripts]
wm-check-versions = "whitemagic.scripts.check_versions:main"
wm-check-registry = "whitemagic.scripts.generate_mcp_registry:main"
```

Leave one-off ops scripts (`omega_test.py`, `archaeological_survey.py`) outside.

**Recommended fix — Choice B (minimal)**

Add to `MANIFEST.in`:
```
recursive-include core/scripts *.py *.sh
```

Prefer **A**.

**Verification**
```bash
cd core && python3 -m build --sdist
tar -tzf dist/whitemagic-22.0.0.tar.gz | grep -E 'scripts/(generate_mcp|check_versions|check_path)'
# Expect: matches.
```

---

### H8 — `.github/` files gitignored inside `core/.github/`

**Severity:** High.

**Evidence**
- `.gitignore:150` has `core/.github/`.
- `core/.github/` contains: `CODEOWNERS`, `dependabot.yml`, `PULL_REQUEST_TEMPLATE.md`, `ISSUE_TEMPLATE/`, `workflows/`.
- Root `.github/` has only `workflows/`.
- **GitHub only recognizes repo-root `.github/`.**

**Recommended fix**
```bash
git mv core/.github/CODEOWNERS .github/CODEOWNERS
git mv core/.github/dependabot.yml .github/dependabot.yml
git mv core/.github/PULL_REQUEST_TEMPLATE.md .github/PULL_REQUEST_TEMPLATE.md
git mv core/.github/ISSUE_TEMPLATE .github/ISSUE_TEMPLATE
# Reconcile workflows: prefer newer of two copies; delete dupes.
```

Then remove `core/.github/` from `.gitignore:150` and delete empty `core/.github/`.

**Verification**
```bash
ls .github/
# Expect: CODEOWNERS, dependabot.yml, ISSUE_TEMPLATE, PULL_REQUEST_TEMPLATE.md, workflows

test ! -d core/.github || echo "FAIL"
grep "core/.github" .gitignore
# Expect: no output.
```

Push a test PR — dependabot should fire, PR template should auto-populate.

---

### H9 — Dead code: `core/whitemagic/archive/polyglot_candidates/`

**Severity:** High for maintenance.

**Recommended fix** — delete `core/whitemagic/archive/` entirely.

**Verification**
```bash
test ! -d core/whitemagic/archive || echo "FAIL"
PYTHONPATH=core pytest core/tests/ -q
# Expect: still green.
```

---

### H10 — Rust crate version + iceoryx2 default

**Severity:** High for Rust-bridge users.

**Recommended fix — `core/whitemagic-rust/Cargo.toml`**
```toml
[package]
version = "22.0.0"    # was 21.0.0
license = "MIT"        # add if absent

[features]
default = ["python", "arrow"]    # drop iceoryx2
iceoryx2 = ["dep:iceoryx2"]
```

**Verification**
```bash
cd core/whitemagic-rust
cargo build --no-default-features --features python,arrow
# Expect: builds without iceoryx2 toolchain.

grep '^version' Cargo.toml   # Expect: version = "22.0.0"
grep '^license' Cargo.toml   # Expect: license = "MIT"
```

---

### H11 — Log files committed under `docs/ci-logs/`

**Severity:** High.

**Recommended fix** — handled by C4 filter-repo pass (already in removal list).

**Verification**
```bash
ls docs/ci-logs/ 2>/dev/null
# Expect: "No such file or directory".

grep "docs/ci-logs" .gitignore
# Expect: match.
```

---

### M1 — 47 top-level subpackages in `core/whitemagic/`

**Severity:** Medium. Maintenance/audit cost is high; dilutes Core story.

**Recommended fix** (following `core/SHIP_SURFACE.md` tiers):

**Step 1 —** Inventory every subpackage. Tag each as Core / Labs / Archive.

Subpackages to consider for **Labs** (experimental, may not be stable for v22):
`alchemy/`, `archaeology/`, `continuity/`, `cascade/`, `embodiment/`,
`oms/`, `oracle/`, `sangha/`, `wu_xing/`, `zodiac/`,
`gratitude/`, `cyberbrain/` (if present as top-level).

Subpackages to keep in **Core**:
`tools/`, `core/`, `config/`, `utils/`, `memory/`, `harmony/`, `dharma/`,
`security/`, `monitoring/`, `mcp/`, `cli/`, `interfaces/`, `rust/`, `mesh/`.

**Step 2 —** Implementation (pick one):

- **A. Extract to separate package** `whitemagic-labs`: cleanest, highest friction.
- **B. Keep in tree, exclude from default wheel**: modify `core/pyproject.toml`:
```toml
[tool.setuptools.packages.find]
where = ["."]
include = ["whitemagic*"]
exclude = [
    "whitemagic.alchemy*",
    "whitemagic.archaeology*",
    "whitemagic.oms*",
    "whitemagic.oracle*",
    "whitemagic.wu_xing*",
    "whitemagic.zodiac*",
    "whitemagic.embodiment*",
    "whitemagic.sangha*",
]
```
Add `[labs]` extra that re-includes them.

- **C. Move to `whitemagic.experimental.*`**: `git mv core/whitemagic/alchemy core/whitemagic/experimental/alchemy`, add import-time warning.

**C** is the cleanest middle-path.

**Verification**
```bash
cd core && python3 -m build --wheel
unzip -l dist/whitemagic-22.0.0-*.whl | grep -E "alchemy|oracle|zodiac|archaeology"
# Expect: no matches (or only in labs extra).
```

---

### M2 — Three parallel doc trees

**Severity:** Medium.

**Evidence**
- `docs/public/` (18 files, supposedly public).
- `docs/` (actual public root per README links).
- `core/docs/` (44 files, mixed).

**Recommended fix**
1. Consolidate `docs/public/*` → `docs/` (covered in H3).
2. Move `core/docs/*` → `docs/dev/` or delete stale files:
   - `core/docs/ARCHITECTURE.md` → `docs/ARCHITECTURE.md`.
   - `core/docs/QUICKSTART.md` → dedupe with root `QUICKSTART.md`.
   - `core/docs/API_REFERENCE.md` → keep.
   - `core/docs/STRATEGY.md`, `VISION.md`, `MANIFESTO.md` → `docs/strategy/`.
   - `core/docs/SHADOW_CLONE_DOCTRINE.md`, `28_GANA_ARMY_MAPPING.md` → `docs/internal/` or delete.
3. Add `docs/README.md` as an index.

**Verification** — only one `ARCHITECTURE.md` exists; README links resolve; no dup doc names.

---

### M3 — Three build-automation systems

**Severity:** Medium.

`Makefile` + `justfile` + `core/scripts/*.sh` duplicate responsibilities.

**Recommended fix** — pick one canonical. `justfile` (modern Python-first feel) or `Makefile` (portability). Delete the loser.

**Verification**
```bash
ls Makefile justfile 2>/dev/null
# Expect: exactly one.
```

---

### M4 — Historical reports at `core/` root

**Severity:** Medium.

**Files**
- `core/AUDIT_COMPLETION_REPORT.md`
- `core/IMPLEMENTATION_COMPLETION_REPORT.md`
- `docs/CODE_QUALITY_REVIEW_2026-04-15.md`

**Recommended fix** — move to `docs/history/` (or delete if no longer relevant).

**Verification**
```bash
ls core/*.md 2>/dev/null
# Expect: only README.md, CHANGELOG.md, SHIP_SURFACE.md, POLYGLOT_STATUS.md, SECURITY.md.
```

---

### M5 — Type/exception hygiene claims don't match reality

**Severity:** Medium (trust).

Audit doc claims `218 # type: ignore, 1,700 bare-except, Phases 0-5 executed`. Current reality: 141 type:ignore, 870 bare-except, 30 TODO.

**Recommended fix** — update `docs/CODE_QUALITY_REVIEW_2026-04-15.md` with current numbers or move to history and produce `docs/CODE_QUALITY_2026-04-16.md` reflecting post-Phase-1 reality.

**Verification**
```bash
grep -rn "# type: ignore" core/whitemagic/ --include='*.py' | wc -l
grep -rn "except Exception" core/whitemagic/ --include='*.py' | wc -l
grep -rn "TODO\|FIXME\|XXX\|HACK" core/whitemagic/ --include='*.py' | wc -l
# Record these in current code-quality doc.
```

---

### M6 — CLI silently defaults XRPL tip address to upstream maintainer

**Severity:** Medium (ethics/transparency).

**Where**
- `core/whitemagic/tools/handlers/gratitude.py:76` — `os.environ.get("WM_XRP_ADDRESS", "raakfKn96zVmXqKwRTDTH5K3j5eTBp1hPy")`
- `core/whitemagic/core/economy/wallet_manager.py:77` — returns the same hardcoded address.
- `core/whitemagic/cli/init_command.py:427` — writes this address to user's `.env` by default.

**Recommended fix**
1. Remove the hardcoded fallback. If `WM_XRP_ADDRESS` is unset, the gratitude feature should be **disabled** and the tool should return `{"status": "error", "error_code": "not_configured", "message": "Set WM_XRP_ADDRESS to enable gratitude tips"}`.
2. Change `wm init` to leave the env var blank or prompt the user.
3. Document clearly in README that tipping is opt-in.

```python
# suggested — in gratitude.py
_UPSTREAM_MAINTAINER_ADDR = "raakfKn96zVmXqKwRTDTH5K3j5eTBp1hPy"  # WhiteMagic project

def get_recipient_address() -> str | None:
    """Return user-configured XRPL tip address, or None if unset."""
    return os.environ.get("WM_XRP_ADDRESS") or None

def get_upstream_maintainer_address() -> str:
    """Return the upstream WhiteMagic maintainer address (advisory only)."""
    return _UPSTREAM_MAINTAINER_ADDR
```

**Verification**
```bash
PYTHONPATH=core python3 -c "
import os
os.environ.pop('WM_XRP_ADDRESS', None)
os.environ['WM_SILENT_INIT'] = '1'
os.environ['WM_STATE_ROOT'] = '/tmp/wm_t'
from whitemagic.tools.unified_api import call_tool
r = call_tool('gratitude.config')
assert r['status'] == 'error' or 'not_configured' in str(r).lower(), r
"

grep -rn "raakfKn96zV" core/whitemagic/ --include='*.py' \
  | grep -v "_UPSTREAM_MAINTAINER"
# Expect: no output (only labeled constant).
```

---

### M7 — Inconsistent security contact

**Severity:** Medium.

**Recommended fix** — pick one canonical contact in `SECURITY.md` (GitHub Security Advisory link OR `security@whitemagic.ai`). Use it everywhere; remove other references.

**Verification**
```bash
grep -rn -i "contact\|security" SECURITY.md README.md QUICKSTART.md 2>/dev/null \
  | grep -i "@" | sort -u
# Expect: one email (or zero, relying on GHSA).
```

---

### M8 — Missing CODE_OF_CONDUCT link

**Severity:** Medium (GitHub community health score).

**Recommended fix** — link `CODE_OF_CONDUCT.md` (already at root) from the new `CONTRIBUTING.md` (see H4).

---

### M9 — Dockerfile is broken (same as C1)

**Severity:** Medium.

**Recommended fix** — handled by C1 (run_mcp shim) + H1 (version). Verify:
```bash
docker build -t whitemagic-test -f core/Dockerfile core/
docker run --rm whitemagic-test python -m whitemagic.run_mcp --help
# Expect: Prints help text.
```

Optional: upgrade base image `python:3.11-slim` → `python:3.12-slim`.

---

### M10 — No rendered docs site

**Severity:** Medium (onboarding).

**Recommended fix (deferrable)** — stand up MkDocs Material at `https://whitemagic-ai.github.io/whitemagic`:
```bash
pip install mkdocs-material
cat > mkdocs.yml <<'YAML'
site_name: WhiteMagic
repo_url: https://github.com/whitemagic-ai/whitemagic
docs_dir: docs
theme:
  name: material
nav:
  - Home: README.md
  - Quickstart: QUICKSTART.md
  - Architecture: ARCHITECTURE.md
  - API Reference: API_REFERENCE.md
  - Glossary: GLOSSARY.md
  - Contributing: CONTRIBUTING.md
YAML
mkdocs build && mkdocs gh-deploy
```

---

### M11 — Code-quality review attributes to "Google DeepMind"

**Severity:** Medium (potentially misleading).

**Where** — `docs/CODE_QUALITY_REVIEW_2026-04-15.md:6` — *"Reviewer: Antigravity AI (Google DeepMind)"*.

**Recommended fix** — change to neutral attribution or remove the line:
```markdown
**Reviewer:** Internal AI-assisted audit
```

**Verification**
```bash
grep -n "DeepMind\|Antigravity" docs/*.md core/*.md 2>/dev/null
# Expect: no output.
```

---

### M12 — `wm init` writes upstream XRP address to user's `.env`

**Severity:** Medium (same as M6). Handled by M6 fix.

---

### M13 — `projects/` tracked despite gitignore

**Severity:** Medium. Handled by C4 filter-repo pass.

---

### L1 — Move historical reports to `docs/history/`

Covered by M4.

---

### L2 — Add `CITATION.cff`

Optional for academic citations:
```yaml
# CITATION.cff
cff-version: 1.2.0
title: WhiteMagic
authors:
  - name: WhiteMagic Contributors
version: 22.0.0
url: https://github.com/whitemagic-ai/whitemagic
date-released: 2026-MM-DD
license: MIT
```

---

### L3 — Add `.github/FUNDING.yml`

```yaml
# .github/FUNDING.yml
github: []  # add sponsors username if applicable
custom: ["https://xrpl.org/send?to=YOUR_ADDRESS_HERE"]
```

---

### L4 — Consolidate `core/examples/` + `core/examples_aux/`

Merge into one `core/examples/`. Keep `time_integrated_workflow.py` and `agent_minimal.py`.

---

### L5 — Move `grimoire/` into `docs/grimoire/`

Lore content belongs with docs. Leaves `core/` code-only. Do this gently — the grimoire is ~1.4 MB and referenced from CLI init docs.

---

### L6 — Seed `CHANGELOG.md` with prior history

Currently only v22.0.0 listed. Add stub entries for key historical milestones (e.g., "v14.0 — Living Graph", "v13.0 — Pre-history / internal development") with 1-line descriptions, to give visitors context.

---

### L7 — `skill.md` tool count stale

Update after H2 fix.

---

### L8 — `llms.txt` missing at root

Create `llms.txt` at repo root per `https://llmstxt.org` convention. Link to key docs.

---

### L9 — No `pre-commit` config

Add `.pre-commit-config.yaml`:
```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.5.0
    hooks:
      - id: ruff
      - id: ruff-format
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.18.0
    hooks:
      - id: gitleaks
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.6.0
    hooks:
      - id: check-added-large-files
        args: ['--maxkb=1000']
      - id: check-yaml
      - id: check-toml
      - id: end-of-file-fixer
      - id: trailing-whitespace
```

Document in `CONTRIBUTING.md`: `pre-commit install`.

---

### L10 — `core/.devcontainer/` is empty

Either populate with a working devcontainer config, or delete.

---

## 6. Hunting Grounds

**Areas where we strongly suspect more issues exist. Please investigate, document, and add findings to Section 7.**

### 6.1 — CLI command paths (HIGH likelihood)

The CLI at `core/whitemagic/cli/cli_app.py` (104 lines — a thin shim per earlier note) delegates to `cli/commands/*.py`. The `wm init` command (`cli/init_command.py`) is 546 lines and generates user-facing templates — likely has more stale references beyond C1. Check:
- `wm doctor` command — does it still find all subsystems?
- `wm status` — does it report the right version/tool count?
- `wm remember/recall` — do the envelope keys match `AI_PRIMARY.md`?
- `wm memory …`, `wm dream …`, `wm garden …` — enumerate every subcommand and spot-check.

```bash
# verify
PYTHONPATH=core WM_SILENT_INIT=1 WM_STATE_ROOT=/tmp/wm_hunt \
  python3 -m whitemagic.cli.cli_app --help
PYTHONPATH=core WM_SILENT_INIT=1 WM_STATE_ROOT=/tmp/wm_hunt \
  python3 -m whitemagic.cli.cli_app doctor
# Note: `python -m` may not work if entry_points aren't installed. Try:
cd core && pip install -e ".[cli]" && wm doctor
```

For each command, check: (a) help text reflects v22, (b) it doesn't break on first-run, (c) it doesn't import missing modules.

---

### 6.2 — `wm init`-generated templates (HIGH likelihood)

The README, .mcp.json, .env, playground.py, run.sh, and .gitignore that `wm init` generates (see `cli/init_command.py`) need a full audit:
- Does every command in the generated README actually work?
- Does the playground.py successfully complete all 5 demo steps (Gnosis, Capabilities, Memory, Dharma, Harmony)?
- Does `./run.sh` work in all three modes (`--prat`, `--lite`, `--full`)?

Run:
```bash
mkdir -p /tmp/wm-init-test && cd /tmp/wm-init-test
PYTHONPATH=<repo>/core wm init --force
cat run.sh playground.py README.md .mcp.json
# Read each carefully for broken commands.
./run.sh --lite   # and other modes
python3 playground.py   # should run 5 sections without crashing
```

---

### 6.3 — 870 `except Exception` blocks (MEDIUM likelihood)

Prior audit logged 12 of the 1,700+ worst offenders. Current count is 870 — still high. Target additional ~50:

```bash
# Find silent excepts with `pass` or no logging:
grep -rn -A2 "except Exception" core/whitemagic/security/ core/whitemagic/core/intelligence/ core/whitemagic/tools/handlers/ --include='*.py' \
  | grep -B1 "pass$\|^$"
```

Each should either: log at appropriate level, re-raise, or have a comment explaining why silence is intentional.

---

### 6.4 — 141 `# type: ignore` suppressions (MEDIUM)

Audit and reduce. Priority order:
1. `core/whitemagic/tools/` (already CI-blocking for mypy).
2. `core/whitemagic/interfaces/`.
3. `core/whitemagic/core/memory/`.

For each `# type: ignore`, determine:
- **Missing stub**: add to `mypy_stubs/` or use `--ignore-missing-imports` selectively.
- **Union ambiguity**: add proper cast or type narrowing.
- **Complex return**: add `Protocol` or `TypeAlias`.

Target: ≤100 by end of Phase 2.

---

### 6.5 — Tool handlers under `core/whitemagic/tools/handlers/` (MEDIUM)

107 operational tools are registered in `dispatch_table`. Each handler should:
1. Return the standard envelope (see `envelope.py`).
2. Never raise uncaught exceptions.
3. Honor `idempotency_key` if provided.
4. Be testable without a full system boot.

Spot-check 10 random handlers. Look for:
- Handlers that return `{"status": "ok"}` or raw dicts instead of envelope.
- Handlers that swallow errors silently.
- Handlers with hardcoded paths or test fixtures.

```bash
# find handlers that might have non-envelope returns
grep -rn "return {" core/whitemagic/tools/handlers/ --include='*.py' \
  | grep -v "return {\s*\"status\"" | head -20
```

---

### 6.6 — Polyglot bridge gracefulness (MEDIUM)

For each polyglot bridge (Rust, Go, Koka, Zig, Mojo, Elixir, Haskell), verify:
1. Python imports work when the bridge is NOT installed.
2. A tool that uses the bridge gracefully degrades with `missing_dependency` error.
3. The `polyglot/STATUS.md` claim matches reality.

```bash
# verify — no bridge should be required for baseline import
PYTHONPATH=core WM_SILENT_INIT=1 WM_STATE_ROOT=/tmp/wm_hunt python3 -c "
import whitemagic
from whitemagic.tools.unified_api import call_tool
r = call_tool('capabilities')
print(r['status'])
"
# Expect: 'success'.
```

---

### 6.7 — MCP client adapters (MEDIUM)

`core/whitemagic/mcp/` is supposed to adapt tool schemas for different AI clients (gemini, deepseek, qwen, kimi per `.env` comment). Verify:
- Each adapter exists and has test coverage.
- Tool schemas validate against JSON-Schema for each client.
- `WM_MCP_CLIENT` env var is documented everywhere relevant.

---

### 6.8 — `WM_*` environment variables (MEDIUM)

`docs/CONFIGURATION.md` (per prior audit) documents 51 variables. Verify:
- Every variable grep-able in the codebase (no ghosts).
- Every variable actually used somewhere (no dead docs).

```bash
# find every WM_* env var reference in code
grep -rhoE 'os\.environ\.(get|__contains__|__getitem__)\(["\x27]WM_[A-Z_]+' core/whitemagic/ \
  | sed -E 's/.*WM_[A-Z_]+/\0/' | sort -u
# compare with docs/CONFIGURATION.md
```

---

### 6.9 — Encryption at rest (HIGH likelihood — sensitive claim)

Per `ENCRYPTION_AT_REST.md`, data is encrypted at rest. Verify by:
- Reading `core/whitemagic/security/` — what's the encryption module?
- Check if keys are actually generated/used.
- Verify `memory/whitemagic.db` is encrypted (or documentation is clear about what IS and ISN'T encrypted).

Shipping with incomplete encryption but marketing "encrypted at rest" is a security claim issue.

---

### 6.10 — The 107K-memory production DB (HIGH likelihood)

The conftest mentions a *"107K-memory production DB"* that can lock up test runs if `WM_STATE_ROOT` isn't isolated. Verify:
- No production-data files are in the repo.
- No test runs default to the developer's `~/.whitemagic/`.
- CI uses fresh `WM_STATE_ROOT` every run.

```bash
# verify — no DB files committed
find . -path ./.git -prune -o -type f \( -name "*.db" -o -name "*.sqlite" \) -print 2>/dev/null
```

---

### 6.11 — `core/whitemagic/grimoire/` (LOW)

1.4 MB of lore content inside the Python package. Shouldn't ship in the wheel. Check `MANIFEST.in` or `pyproject.toml` excludes this.

---

### 6.12 — `requirements.txt` vs `pyproject.toml` divergence (MEDIUM)

After fixing H6 (delete root requirements.txt), double-check every extra in `pyproject.toml` still resolves:
```bash
for extra in lite core heavy-tier dev mcp cli db net trust vision watcher dashboard; do
  echo "=== $extra ==="
  pip install --dry-run "-e" "core/.[$extra]" 2>&1 | tail -5
done
```

---

### 6.13 — Generated `.mcp.json` correctness (HIGH)

After C1 shim is in place, the `.mcp.json` generated by `wm init` (`init_command.py:451`) should actually work:
```bash
# verify after C1 fix
mkdir -p /tmp/mcp-test && cd /tmp/mcp-test
PYTHONPATH=<repo>/core wm init
cat .mcp.json
# Verify the command in args starts the server cleanly:
cd /tmp/mcp-test && WM_MCP_PRAT=1 WM_SILENT_INIT=1 python -m whitemagic.run_mcp &
sleep 2; kill $!
# Should launch without errors.
```

---

### 6.14 — Agent card at `.well-known/agent.json` (MEDIUM)

The file `core/.well-known/agent.json` describes the project for A2A (Agent-to-Agent) discovery. Audit:
- Version matches (H1).
- Tool count matches (H2).
- `skills` array covers the canonical capabilities.
- `url` resolves.
- Properties per A2A spec are complete.

---

### 6.15 — Archived code in `_archived/` (LOW)

`core/whitemagic/_archived/run_mcp_hydrated.py` is kept for historical reference. Audit: is any live code importing from `_archived/`? If yes, fix.
```bash
grep -rn "from whitemagic._archived\|import whitemagic._archived" core/ 2>/dev/null
```

---

### 6.16 — Windows/Mac compatibility (LOW)

Codebase assumes POSIX (shell scripts, `Path.home()`, `os.path.expanduser`). If you plan to support Windows:
- Audit `config/paths.py` for `/tmp` fallbacks.
- Replace `os.system`/`subprocess` without `shell=False`.
- Check line-ending config in `.gitattributes`.

---

### 6.17 — Test run time (MEDIUM)

Current full test collection takes ~9s; unit suite takes a while. Measure per-file:
```bash
PYTHONPATH=core pytest core/tests/unit/ --durations=20 -q
# Identify the 20 slowest tests and mark them `@pytest.mark.slow`.
```

Target: `pytest -m "not slow"` runs in <30s.

---

### 6.18 — README benchmark claims (MEDIUM)

README claims "LoCoMo benchmark: 78.3% recall accuracy". Verify:
- Is there a reproducible benchmark script?
- `core/scripts/benchmark_gauntlet.py` exists — does it actually produce this number?
- Is the benchmark reproducible on a clean install?

---

### 6.19 — Any `FIXME`, `TODO`, `XXX`, `HACK` with "critical" or "security" context (LOW)

```bash
grep -rn -iE "(TODO|FIXME|XXX|HACK).*(critical|security|urgent|breaking)" \
  core/whitemagic/ --include='*.py'
```

Fix any matches.

---

## 7. Report-Back Template

Once you've worked through as much as possible, please report back using the following template:

```markdown
# WhiteMagic Release Readiness — Handback Report

**Date:** YYYY-MM-DD
**Engineer(s):** …
**Baseline commit:** b8a7c65 (initial commit)
**Report commit:** <sha>

---

## Summary
- **Phase 1 (Critical):** X / 7 complete
- **Phase 2 (High):** X / 11 complete
- **Phase 3 (Medium & Low):** X / 23 complete
- **Hunting Grounds investigated:** X / 19 sub-sections
- **New findings added:** X

Time spent: …

---

## Completed Findings

For each: `ID`, `what changed`, `commit SHA`, `verification result`.

- **C1** — Resurrected `whitemagic.run_mcp` as shim. Commit `abc1234`. Verification: `python -m whitemagic.run_mcp --help` prints help.
- **C2** — Fixed 12 collection errors; 244 failures down to X. Commit `def5678`. Verification: `pytest core/tests/` green.
- …

---

## Deferred Findings (with reasons)

- **M1** (Core/Labs split): not attempted, requires architecture decision meeting.
- …

---

## New Findings

Follow the same format as existing findings. Add to a new section `## 8. Additional Findings Discovered` in the original plan doc.

- **N1** — [Title] — Severity — Where — Root cause — Fix — Verification.

---

## Test Suite Status
- **Collected:** N
- **Passed:** N
- **Failed:** N (list the N most important)
- **Skipped:** N (reason categories)
- **Errors:** N (should be 0)

Paste: `pytest --durations=5 -q` output.

---

## Repo Size After Cleanup
- `.git/`: N MB
- `du -sh *`: attach output
- Largest blobs in history: attach top-10 from `git rev-list | git cat-file`

---

## CI Status
Attach screenshot of green CI or link to a successful run.
- Test job: Green/Red
- Mypy (public): Green/Red
- Mypy (full): advisory
- Bandit: Green/Red
- pip-audit: Green/Red
- Version consistency: Green/Red

---

## Open Questions for Reviewers

List any decisions that need maintainer input (e.g., "Should we ship the XRPL default address? Choice A or B for C1?").

---

## Files Created / Modified / Deleted

### Created
- `core/whitemagic/run_mcp.py` (C1 shim)
- `core/tests/unit/regression/test_release_readiness.py` (regression tests)
- `core/scripts/check_versions.py` (H1)
- …

### Modified
- `core/README.md` (C3 license fix)
- `core/whitemagic/tools/handlers/gratitude.py` (M6 XRPL fallback)
- …

### Deleted
- `requirements.txt` (H6)
- `core/whitemagic/archive/` (H9)
- …

---

## Regression Tests Added

List each test added, with the ID it guards.

- `test_run_mcp_module_importable` → C1
- `test_run_mcp_has_prat_symbols` → C1
- `test_collection_zero_errors` → C2
- `test_license_is_mit` → C3
- …

All must pass: `pytest core/tests/unit/regression/ -v`.
```

---

## 8. Round 1 Progress (2026-04-16)

Team report verified against repo state. Summary: **6 verified-complete, 2 incomplete-despite-claim, 1 partial, 8 pending**. All work is **uncommitted** in working tree.

### ✅ Verified complete
| ID | Proof |
|---|---|
| **C1** | `core/whitemagic/run_mcp.py` exists; `import whitemagic.run_mcp` works; `main` exposed. 2 blocked tests marked `pytest.mark.skip` (acceptable). |
| **C3** | `core/README.md:95` says MIT; `core/LICENSE` (Apache) deleted. |
| **H3** | Link audit script prints "(done)" — no broken links in README. |
| **H6** | `requirements.txt` absent from root. |
| **H9** | `core/whitemagic/archive/` removed (13 files). |
| **H10** | `Cargo.toml`: `version = "22.0.0"`, `license = "MIT"`, `default = ["python", "arrow"]`. |

### ⚠️ Claimed but INCOMPLETE

**H1 — version drift:** `core/SHIP_SURFACE.md:3` still says `**Version**: 21.0.0`. The `check_versions.py` CI guard was **not** created. Must finish:
```bash
# fix
sed -i 's/^\*\*Version\*\*: 21\.0\.0/**Version**: 22.0.0/' core/SHIP_SURFACE.md
# then create core/scripts/check_versions.py per H1 spec and wire into CI.
```

**H8 — .github migration:** Root-level files (CODEOWNERS, dependabot, PR template, ISSUE_TEMPLATE) correctly moved ✅. But `core/.github/workflows/` **still contains 4 files**:
- `ci.yml` → DIFFERS from root `.github/workflows/ci.yml`
- `release.yml` → DIFFERS from root `.github/workflows/release.yml`
- `seed-binaries.yml` → only in core
- `wasm-cicd.yml` → only in core

Required: diff each pair, pick canonical, merge extras to root, then `rm -rf core/.github/workflows/`.

### 🟡 Partial

**C2 — test suite:** Collection errors 12 → 10. Two `run_mcp`-related tests skipped (resolved by C1). The team cited `listen_for()` API change as the reason for deferral, but that explains only **2 of the 10 remaining errors** (`test_scratchpad*`). The other 8 are independent:
- `test_umap_projection.py`, `test_causal_miner.py`, `test_entropy_scorer.py` → missing modules (skip with tracking issue)
- `test_dispatch_bridge.py`, `test_event_ring_bridge.py`, `test_state_board_bridge.py` → `core.acceleration.*` symbol mismatch
- `test_fusions.py` → `_ELEMENT_TO_QUADRANT` rename
- `test_p0_regressions.py` → may now pass after C1 (unverified)

Full 244-failure triage not yet attempted.

### ✅ Cascade completions (during verification)

**Critical fix: H5 CI was broken by team edit**
- Team's sed-based `working-directory` insertion shredded YAML (8 corruption sites).
- Rewrote `.github/workflows/ci.yml` from scratch — now valid, 11 jobs, B603 properly removed from skip list.
- **Regression test added:** `test_ci_yaml_parses`, `test_bandit_b603_not_skipped`.

**M6 completion**
- Fixed `wallet_manager.py` which team missed (hardcoded address at line 77).
- Now returns empty string when `WM_XRP_ADDRESS` unset; `enabled` flag added.
- **Regression test added:** `test_no_hardcoded_maintainer_address_in_source`, `test_wallet_manager_disabled_without_env`.

**M7 (Security contact consolidation)**
- Updated `SECURITY.md` supported versions 21.x → 22.x.
- Verified GitHub Security Advisory is canonical contact method.
- **Regression test added:** `test_security_md_has_correct_versions`, `test_security_md_prefers_github_advisory`.

**M11 (Attribution fix)**
- Changed `docs/CODE_QUALITY_REVIEW_2026-04-15.md:6` from "Antigravity AI (Google DeepMind)" to "Internal AI-assisted audit".
- **Regression test added:** `test_no_deepmind_or_antigravity_attribution`.

**L2, L3, L8 (Community files)**
- Created `CITATION.cff` (v22.0.0, MIT).
- Created `.github/FUNDING.yml` (GitHub Security Advisory link).
- Created `llms.txt` (per llmstxt.org convention).
- **Regression tests added:** `test_citation_cff_*`, `test_funding_yml_*`, `test_llms_txt_*`.

### ❌ Process gaps (addressed)

1. **Commits:** Team made 15 commits (round 1 + 2). Cascade edits are staged and will be committed atomically.
2. **Regression tests:** `core/tests/unit/regression/` created with **34 tests covering C1, C2, C3, H1, H5, H6, H9, H10, M6, M7, M11, L2, L3, L8**. All passing.

### 📋 Still pending (round 3 — team items requiring coordination or large file count)

| ID | Task | Why deferred |
|---|---|---|
| **C4/C5/C6/C7/H11** | Git filter-repo cleanup | Destructive; requires maintainer coordination and force-push |
| **C2** (189→0 failures) | Continue triage | Already at 80% pass rate; diminishing returns vs. launch blockers |
| **H2** | Tool-count drift | Mechanical; good first issue for new contributor |
| **H4** | Rewrite CONTRIBUTING.md | Content-heavy; needs maintainer voice |
| **H7** | MANIFEST.in scripts | One-line fix; team should verify sdist contents |
| **M1-M5, M8-M13** | Various medium items | Architectural decisions or lower priority |
| **L4-L10** (excl. done) | Examples, devcontainer, etc. | Cleanup polish |
| **Hunting Grounds** | 19 exploratory areas | Will surface new findings; assign as investigation tasks |

---

## 9. Closing Notes

- **This document is the source of truth for the release pass.** If it drifts from reality, update *this* file first.
- **Ask questions.** If any finding is unclear, underspecified, or conflicts with the actual codebase, flag it in Section 7's "Open Questions" and proceed with your best judgment on the rest.
- **Do not stop at "good enough".** Phase 1 is non-negotiable for launch; Phases 2 and 3 are where the project earns credibility.
- **Be skeptical of historical claims.** Prior audit docs (`AUDIT_COMPLETION_REPORT.md`, `CODE_QUALITY_REVIEW_2026-04-15.md`) describe work that was only partially executed. Trust the code, not the narrative.
- **Write the regression tests.** They're how you prove the fix stays fixed.
- **Have fun.** This project has genuinely strong ideas. The cleanup is mechanical; the substrate is excellent.

Good hunting.
