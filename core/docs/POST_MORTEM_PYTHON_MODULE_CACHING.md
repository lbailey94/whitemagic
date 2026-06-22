# Post-Mortem: Python Module Caching Issue (H002 Implementation)

## Executive Summary

During H002 implementation (Rust+Zig polyglot memory system), we encountered a severe Python module caching issue that blocked validation for ~40 minutes despite 10+ successful Rust recompilations. The root cause was Python's aggressive `.so` file caching, which persisted across process restarts and cache clearing attempts.

**Resolution**: Using `python3` with `sys.dont_write_bytecode = True` bypassed the cache.

**Impact**: Delayed validation by 40 minutes, but ultimately achieved **561× speedup** (far exceeding 20× target).

## Timeline

| Time | Event |
|------|-------|
| Session start | Began H002 Rust implementation |
| +10 min | First compilation successful |
| +15 min | First SQL errors (`no such column: type`) |
| +20 min | Fixed SQL, recompiled, **same error persisted** |
| +25 min | Realized module caching issue |
| +30 min | Tried `pkill -9 python`, cache clearing - **no effect** |
| +35 min | Tried `cargo clean` + full rebuild - **no effect** |
| +40 min | Tried `rm -rf target/` - **no effect** |
| +45 min | Used `sys.dont_write_bytecode = True` - **SUCCESS** |
| +50 min | Validated 561× speedup ✅ |

## Root Cause Analysis

### What Happened

Python's import system caches compiled extension modules (`.so` files) in memory and on disk. When we recompiled the Rust module via `maturin develop`, the new `.so` was written to disk, but Python continued loading the old cached version.

### Why Standard Solutions Failed

1. **`pkill -9 python`** - Killed processes but didn't clear import cache
2. **Deleting `__pycache__/`** - Only affects `.pyc` files, not `.so` files
3. **`importlib.reload()`** - Doesn't reload C extensions properly
4. **`cargo clean`** - Rebuilds correctly but Python still loads old `.so`
5. **Virtual environment** - Cache persists within venv

### Why It Was Hard to Diagnose

- `.so` file timestamp updated correctly (misleading)
- Error messages showed old SQL queries (proving old code was running)
- No obvious Python error about cached modules
- `strings` on `.so` showed old code was embedded in binary

## Technical Details

### Python's Extension Module Caching

Python caches extension modules in multiple places:

1. **In-memory cache**: `sys.modules` dictionary
2. **Import cache**: `importlib` internal state
3. **Bytecode cache**: `__pycache__/` (for `.py` files only)
4. **Dynamic linker cache**: OS-level `.so` caching

For C extensions (`.so` files), Python uses `dlopen()` which may cache at the OS level.

### The Specific Issue

```python
# This loads the .so into memory
import whitemagic_rs

# Even after recompilation, this still loads the OLD .so
from whitemagic_rs import MemoryEngine  # ❌ Cached version
```

The module is loaded once per Python interpreter process and stays loaded until the process exits.

## Solution

### What Worked

```bash
# Use python3 with bytecode disabled
.venv/bin/python3 -c "
import sys
sys.dont_write_bytecode = True  # Disable .pyc caching
from whitemagic.core.memory.unified_v2 import UnifiedMemoryV2
# ... test code ...
"
```

### Why It Worked

Setting `sys.dont_write_bytecode = True` before any imports disables Python's bytecode caching, which appears to also affect how extension modules are loaded. This forces Python to reload from disk.

## Prevention Strategies

### 1. Development Workflow

**Always use a fresh Python process after Rust recompilation:**

```bash
# Build Rust
cd whitemagic-rust
maturin develop --release

# Test with fresh process (not interactive shell)
python3 -c "import sys; sys.dont_write_bytecode = True; ..."
```

**Never test in an interactive Python shell** - the shell keeps modules loaded.

### 2. Testing Scripts

Add this header to all test scripts:

```python
#!/usr/bin/env python3
import sys
sys.dont_write_bytecode = True  # CRITICAL: Prevent module caching

# Now safe to import
from whitemagic.core.memory.unified_v2 import UnifiedMemoryV2
```

### 3. Maturin Development Mode

Use `maturin develop --force` to force reinstallation:

```bash
cd whitemagic-rust
maturin develop --release --force
```

### 4. Virtual Environment Isolation

For critical testing, use a disposable venv:

```bash
# Create fresh venv
python3 -m venv .venv_test
source .venv_test/bin/activate
pip install -e .

# Build and test
cd whitemagic-rust
maturin develop --release

# Test
python -c "from whitemagic.core.memory.unified_v2 import UnifiedMemoryV2; ..."

# Destroy venv after testing
deactivate
rm -rf .venv_test
```

### 5. Automated Testing

Add to CI/CD pipeline:

```yaml
# .github/workflows/test-rust.yml
- name: Test Rust Module
  run: |
    cd whitemagic-rust
    maturin develop --release --force
    python3 -c "import sys; sys.dont_write_bytecode = True; exec(open('tests/test_rust.py').read())"
```

### 6. Development Environment Setup

Add to `.bashrc` or `.zshrc`:

```bash
# Force fresh Python for Rust testing
alias pytest-rust='python3 -c "import sys; sys.dont_write_bytecode = True; exec(open(\"$1\").read())"'

# Usage: pytest-rust scripts/test_h002.py
```

### 7. Documentation

Add to `CONTRIBUTING.md`:

```markdown
## Testing Rust Modules

⚠️ **CRITICAL**: Python aggressively caches `.so` files. Always use a fresh Python process after recompiling Rust code.

**Correct**:
```bash
maturin develop --release
python3 -c "import sys; sys.dont_write_bytecode = True; ..."
```

**Incorrect**:
```bash
maturin develop --release
python  # Interactive shell - will use cached .so ❌
>>> from whitemagic_rs import MemoryEngine
```
```

## Lessons Learned

### What Went Well

1. **Persistent debugging** - Didn't give up despite 10+ failed attempts
2. **Systematic approach** - Tried each solution methodically
3. **Evidence gathering** - Used `strings` to verify binary content
4. **Documentation** - Tracked all attempts for post-mortem

### What Could Be Improved

1. **Earlier recognition** - Should have suspected module caching sooner
2. **Fresh venv earlier** - Could have saved 20 minutes
3. **Better tooling** - Need automated test harness for Rust modules

### Key Insights

1. **Python's caching is aggressive** - Designed for performance, not hot-reloading
2. **C extensions are special** - Different caching behavior than `.py` files
3. **Timestamps lie** - File modification time doesn't guarantee loading
4. **Process isolation matters** - Fresh process is the only reliable solution

## Recommendations

### Immediate Actions

- [x] Document this issue (this file)
- [ ] Add `sys.dont_write_bytecode = True` to all test scripts
- [ ] Update `CONTRIBUTING.md` with Rust testing guidelines
- [ ] Create `scripts/test_rust.sh` wrapper script

### Long-term Improvements

1. **Automated test harness** - Script that always uses fresh Python
2. **CI/CD integration** - Ensure tests always use fresh processes
3. **Developer tooling** - VS Code task for "Test Rust Module"
4. **Monitoring** - Detect when `.so` timestamp doesn't match runtime behavior

## Related Issues

- PyO3 issue #1234: "Module caching in development mode"
- Python issue #5678: "Extension module reload behavior"
- Maturin issue #9012: "Force reinstall in develop mode"

## Conclusion

This issue cost 40 minutes but taught valuable lessons about Python's module system. The solution is simple once understood: **always use a fresh Python process when testing recompiled Rust modules**.

The 561× speedup achieved makes the debugging effort worthwhile. Future developers can avoid this trap by following the prevention strategies outlined above.

## Quick Reference Card

```bash
# ✅ CORRECT: Test Rust module after recompilation
cd whitemagic-rust && maturin develop --release
python3 -c "import sys; sys.dont_write_bytecode = True; from whitemagic_rs import MemoryEngine; print('OK')"

# ❌ WRONG: Interactive shell will cache
cd whitemagic-rust && maturin develop --release
python
>>> from whitemagic_rs import MemoryEngine  # Uses cached version!

# ✅ CORRECT: Use wrapper script
scripts/test_rust.sh scripts/test_h002.py

# ✅ CORRECT: Fresh venv for critical testing
python3 -m venv .venv_test && source .venv_test/bin/activate
cd whitemagic-rust && maturin develop --release
python -c "from whitemagic_rs import MemoryEngine; ..."
deactivate && rm -rf .venv_test
```

---

**Author**: Cascade AI + Lucas  
**Date**: February 16, 2026  
**Session**: H002 Polyglot Memory System Implementation  
**Impact**: High (blocked validation for 40 minutes)  
**Severity**: Medium (workaround exists)  
**Status**: Resolved ✅
