# Independent Review Findings - v2.2.0

**Date**: November 11, 2025  
**Reviewer**: External AI System  
**Status**: Critical issues identified

---

## 🔴 CRITICAL ISSUES (Must Fix)

### 1. Terminal Allowlist Security Bug
**Severity**: HIGH  
**Files**: `whitemagic/api/routes/exec.py:13`, `whitemagic/terminal/allowlist.py:24`

**Problem**: Allowlist only checks raw `cmd` string, not `cmd + args`. Multi-word commands like "git status" fail validation because args are stripped, making safe commands unusable while dangerous ones might slip through.

**Impact**: Feature is simultaneously broken and potentially dangerous.

**Fix**: Normalize `cmd + args` before allowlist check.

### 2. Numpy Dependency Packaging Bug  
**Severity**: MEDIUM  
**Files**: `pyproject.toml:28`, `whitemagic/search/semantic.py:1`, `whitemagic/api/routes/search.py:6`

**Problem**: Semantic search imports numpy unconditionally, but it's only in optional `embeddings` extra, not `api` extra. Installing `whitemagic[api]` and hitting `/search/semantic` raises `ModuleNotFoundError`.

**Impact**: Shipped API endpoint fails at runtime.

**Fix**: Move numpy to base or api extras.

### 3. Memory Manager Concurrency Issues
**Severity**: MEDIUM  
**Files**: `whitemagic/api/memory_service.py:14`, `whitemagic/core.py:422`

**Problem**: Managers cached forever in module-level dict, no LRU eviction, no file locking, no protection against concurrent mutations of `metadata.json`.

**Impact**: Multi-worker deployments risk data corruption.

**Fix**: Add file locking, LRU cache, atomic writes.

---

## ⚠️ HIGH PRIORITY (Should Fix)

### 4. CI MCP Test Escape Hatch
**Files**: `.github/workflows/ci.yml:152`, `whitemagic-mcp/tests/client.test.ts:12`

**Problem**: `npm test || echo "No MCP tests yet"` swallows failures even though tests exist.

**Impact**: MCP regressions won't fail builds.

**Fix**: Remove escape hatch, fail on test failures.

### 5. Docker Compose Uses Prebuilt Image
**Files**: `compose.yaml:34`

**Problem**: Ships prebuilt image (`lbailey94/whitemagic:2.1.0`) instead of building from checked-in code.

**Impact**: Local testing doesn't exercise actual code changes.

**Fix**: Use `build: .` to build from local Dockerfile.

### 6. Documentation Drift
**Files**: `COMPREHENSIVE_REVIEW_ASSESSMENT.md:108`, `PHASE_2B_DAY3_COMPLETE.md:1`

**Problem**: Root cluttered with day-by-day phase journals, outdated assessments claiming work is missing when it exists.

**Impact**: Undermines trust, confuses newcomers.

**Fix**: Archive historical docs, update assessments.

---

## ✅ STRENGTHS (Keep These)

1. **Excellent Documentation Structure**: README + DOCUMENTATION_MAP + INDEX provides multiple entry points
2. **Solid FastAPI Architecture**: Async handling, thread pools for blocking work
3. **Good Test Coverage**: Real integration tests for both Python and MCP
4. **Rate Limiting Ready**: Quota enforcement and plan configuration already modeled
5. **Pragmatic Dashboard**: Simple but functional, no build step required

---

## 📋 ACTION PLAN

### Immediate (Before v2.2.0 release)
1. ✅ Fix terminal allowlist bug
2. ✅ Fix numpy packaging
3. ✅ Clean up documentation drift
4. ✅ Fix CI escape hatch

### Short-term (v2.2.1)
5. Add file locking to MemoryManager
6. Fix Docker Compose
7. Add LRU eviction to memory cache

### Medium-term (v2.3.0)
8. Per-user terminal instances
9. Repository layer for MemoryManager
10. Coverage thresholds for MCP tests

---

**Reviewer Assessment**: "Production ready" needs these fixes first, especially #1-3.
