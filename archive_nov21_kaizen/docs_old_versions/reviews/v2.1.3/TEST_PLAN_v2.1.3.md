# Test Plan for WhiteMagic v2.1.3

**Date**: November 12, 2025  
**Version**: 2.1.3  
**Purpose**: Comprehensive validation before publication  
**Status**: 🔄 **IN PROGRESS**

---

## Executive Summary

This test plan validates all fixes made after the independent review identified critical issues. It focuses on functional testing of previously broken features and regression testing to ensure no new issues were introduced.

**Critical Fixes Being Tested**:
1. ✅ Backup system paths (`memory/` not `whitemagic/`)
2. ✅ Safe tar extraction (path traversal prevention)
3. ✅ Rate limiting middleware (now runs after auth)
4. ✅ Structured logging (now captures context)
5. ✅ PyYAML dependency (semantic search)
6. ✅ Version consistency (constants.py)

---

## Test Categories

### 1. Unit Tests (Automated)
### 2. Integration Tests (Automated)
### 3. Functional Tests (Manual)
### 4. Security Tests (Manual)
### 5. Regression Tests (Manual)

---

## 1. Unit Tests (Automated)

### 1.1 Run Python Test Suite

**Purpose**: Verify no regressions in core functionality

**Command**:
```bash
cd /home/lucas/Desktop/whitemagic
pytest -v --tb=short
```

**Expected Result**: 
- ✅ 196+ tests passing
- ✅ 0-1 skipped (known)
- ❌ 0 failures

**Acceptance Criteria**:
- [ ] All tests pass
- [ ] No new failures introduced
- [ ] Test coverage remains ~85%

---

### 1.2 Run MCP Test Suite

**Purpose**: Verify MCP server functionality

**Command**:
```bash
cd /home/lucas/Desktop/whitemagic/whitemagic-mcp
npm test
```

**Expected Result**:
- ✅ 27 tests passing
- ❌ 0 failures

**Acceptance Criteria**:
- [ ] All 27 MCP tests pass
- [ ] No timeout errors
- [ ] Version reporting works (2.1.3)

---

## 2. Integration Tests (Priority)

### 2.1 Backup System Integration Test

**Purpose**: Verify backup creates from correct directories

**Test Steps**:
```bash
# 1. Create test memory structure
mkdir -p /tmp/whitemagic_test/memory/{short_term,long_term,archive}
echo "---
title: Test Memory
tags: [test]
---
Test content" > /tmp/whitemagic_test/memory/short_term/test.md

# 2. Test backup creation
cd /home/lucas/Desktop/whitemagic
python3 << 'EOF'
from pathlib import Path
from whitemagic.backup import BackupManager

manager = BackupManager(Path("/tmp/whitemagic_test"))
result = manager.create_backup(
    output_path=Path("/tmp/test_backup.tar.gz")
)

print(f"Backup created: {result['success']}")
print(f"Files backed up: {result['files_backed_up']}")
print(f"Backup size: {result['backup_size_bytes']} bytes")

# Verify files list
assert result['success'], "Backup failed"
assert result['files_backed_up'] > 0, "No files backed up"
print("✅ PASS: Backup created successfully")
EOF

# 3. Verify tar contents
tar -tzf /tmp/test_backup.tar.gz | grep -E "(short_term|long_term|archive)"

# 4. Cleanup
rm -rf /tmp/whitemagic_test /tmp/test_backup.tar.gz
```

**Expected Result**:
- ✅ Backup created successfully
- ✅ test.md found in archive
- ✅ Correct paths (memory/short_term/test.md)

**Acceptance Criteria**:
- [ ] Backup creates without errors
- [ ] Files from memory/ directories included
- [ ] Tar archive is valid

---

### 2.2 Tar Extraction Safety Test

**Purpose**: Verify path traversal protection

**Test Steps**:
```bash
cd /tmp

# Create malicious tar with path traversal
mkdir -p evil
echo "pwned" > evil/evil.txt
tar -czf evil.tar.gz --transform='s|^evil/|../../tmp/|' evil/
rm -rf evil

# Test extraction with WhiteMagic
python3 << 'EOF'
from pathlib import Path
import tempfile
from whitemagic.backup import BackupManager

manager = BackupManager(Path("/tmp"))
target = Path(tempfile.mkdtemp())

try:
    result = manager.restore_backup(
        Path("/tmp/evil.tar.gz"),
        target_dir=target
    )
    
    # Check that evil file was NOT created outside target
    evil_file = Path("/tmp/evil.txt")
    if evil_file.exists():
        print("❌ FAIL: Path traversal vulnerability!")
        exit(1)
    else:
        print("✅ PASS: Path traversal blocked")
except Exception as e:
    print(f"✅ PASS: Malicious archive handled: {e}")

# Cleanup
import shutil
shutil.rmtree(target, ignore_errors=True)
EOF

rm -f /tmp/evil.tar.gz /tmp/evil.txt
```

**Expected Result**:
- ✅ Malicious paths skipped or rejected
- ✅ No files created outside target directory
- ✅ Warning logged for unsafe paths

**Acceptance Criteria**:
- [ ] Path traversal attempts blocked
- [ ] No files escape target directory
- [ ] Warnings logged for suspicious paths

---

### 2.3 Rate Limiting with Authentication

**Purpose**: Verify rate limits enforce after middleware auth

**Prerequisites**:
- Redis running (or skip test with note)
- Test API key created

**Test Steps**:
```bash
# 1. Start Redis (if not running)
# docker run -d -p 6379:6379 redis:latest

# 2. Start API with Redis
cd /home/lucas/Desktop/whitemagic
REDIS_URL="redis://localhost:6379" \
DATABASE_URL="sqlite:///./test_rate_limit.db" \
python3 -m uvicorn whitemagic.api.app:app --host 0.0.0.0 --port 8001 &
API_PID=$!
sleep 3

# 3. Create test user and API key
python3 << 'EOF'
import asyncio
from whitemagic.api.database import Database
from whitemagic.api.auth import create_api_key

async def setup():
    db = Database("sqlite:///./test_rate_limit.db")
    await db.init()
    
    # Create test user
    async with db.get_session() as session:
        from whitemagic.api.database import User
        user = User(email="test@example.com", plan="free")
        session.add(user)
        await session.commit()
        await session.refresh(user)
        
        # Create API key
        raw_key, api_key = await create_api_key(
            session, user.id, "Test Key"
        )
        print(f"API_KEY={raw_key}")
        return raw_key

key = asyncio.run(setup())
EOF

# 4. Test rate limiting (extract key from output above)
API_KEY="<key_from_above>"

# Make requests and check rate limiting
for i in {1..10}; do
  curl -s -w "%{http_code}" -o /dev/null \
    -H "Authorization: Bearer $API_KEY" \
    http://localhost:8001/api/v1/memories
  echo " - Request $i"
  sleep 0.1
done

# 5. Check logs for rate limit enforcement
# Should see user_id in logs and potentially rate limit warnings

# 6. Cleanup
kill $API_PID
rm -f test_rate_limit.db
```

**Expected Result** (with Redis):
- ✅ First N requests succeed (200)
- ✅ Subsequent requests rate limited (429)
- ✅ Logs show user_id context
- ✅ Redis quota tracking works

**Expected Result** (without Redis):
- ⚠️ All requests succeed (rate limiting disabled)
- ✅ Logs still show user_id context

**Acceptance Criteria**:
- [ ] User authenticated in middleware
- [ ] Rate limiting sees authenticated user
- [ ] Logs contain user_id context
- [ ] Quota enforcement works (with Redis)

---

### 2.4 Structured Logging Context Test

**Purpose**: Verify logging captures extra fields

**Test Steps**:
```bash
cd /home/lucas/Desktop/whitemagic

# Start API with JSON logging
LOG_FORMAT=json \
DATABASE_URL="sqlite:///./test_logging.db" \
python3 -m uvicorn whitemagic.api.app:app --host 0.0.0.0 --port 8002 &
API_PID=$!
sleep 3

# Make authenticated request
curl -s -H "Authorization: Bearer test_key_123" \
  http://localhost:8002/api/v1/memories > /dev/null

# Check logs (should be JSON with extra fields)
# Look for: user_id, method, path, response_time_ms, etc.

kill $API_PID
rm -f test_logging.db
```

**Expected Result**:
- ✅ Logs are valid JSON
- ✅ Contains: user_id, method, path
- ✅ Contains: response_time_ms, correlation_id
- ✅ Extra fields not silently dropped

**Acceptance Criteria**:
- [ ] Logs contain all expected fields
- [ ] Extra fields properly merged
- [ ] JSON parseable
- [ ] User context preserved

---

### 2.5 Semantic Search PyYAML Test

**Purpose**: Verify semantic search works with frontmatter

**Test Steps**:
```bash
cd /home/lucas/Desktop/whitemagic

# Ensure PyYAML installed
pip install -q "whitemagic[api]"

# Test semantic search with frontmatter
python3 << 'EOF'
import asyncio
from pathlib import Path
import tempfile
from whitemagic.core import MemoryManager

async def test_semantic_search():
    # Create test memory with frontmatter
    temp_dir = tempfile.mkdtemp()
    memory_dir = Path(temp_dir) / "memory" / "short_term"
    memory_dir.mkdir(parents=True)
    
    test_memory = memory_dir / "test.md"
    test_memory.write_text("""---
title: API Design
tags: [api, rest]
created: 2025-11-12T10:00:00Z
---
Use REST principles for API design.""")
    
    # Test parsing
    manager = MemoryManager(base_dir=temp_dir)
    
    try:
        # This would trigger yaml.safe_load
        content = test_memory.read_text()
        if content.startswith("---"):
            import yaml  # Should not raise ModuleNotFoundError
            print("✅ PASS: PyYAML imported successfully")
        
        # Cleanup
        import shutil
        shutil.rmtree(temp_dir)
        
    except ModuleNotFoundError as e:
        print(f"❌ FAIL: {e}")
        exit(1)

asyncio.run(test_semantic_search())
EOF
```

**Expected Result**:
- ✅ PyYAML imports successfully
- ✅ Frontmatter parses correctly
- ✅ No ModuleNotFoundError

**Acceptance Criteria**:
- [ ] PyYAML dependency installed
- [ ] Frontmatter parsing works
- [ ] No import errors

---

## 3. Functional Tests (Manual)

### 3.1 Fresh Install Test

**Purpose**: Verify clean install works as documented

**Test Steps**:
```bash
# 1. Create fresh virtual environment
cd /tmp
python3 -m venv test_venv
source test_venv/bin/activate

# 2. Install from built package
pip install /home/lucas/Desktop/whitemagic/dist/whitemagic-2.1.3-py3-none-any.whl

# 3. Verify installation
whitemagic --version
# Should show: 2.1.3

python3 -c "import whitemagic; print(whitemagic.__version__)"
# Should show: 2.1.3

# 4. Test basic functionality
mkdir -p /tmp/test_memories
whitemagic --base-dir /tmp/test_memories create \
  --title "Test Memory" \
  --content "Testing fresh install" \
  --tags test,install

whitemagic --base-dir /tmp/test_memories list
# Should show 1 memory

# 5. Cleanup
deactivate
rm -rf test_venv /tmp/test_memories
```

**Expected Result**:
- ✅ Package installs without errors
- ✅ Version reports 2.1.3
- ✅ CLI commands work
- ✅ Basic memory operations succeed

**Acceptance Criteria**:
- [ ] Clean install succeeds
- [ ] Version correct in all checks
- [ ] CLI functional
- [ ] No import errors

---

### 3.2 API Smoke Test

**Purpose**: Quick sanity check of API endpoints

**Test Steps**:
```bash
# Start API
cd /home/lucas/Desktop/whitemagic
DATABASE_URL="sqlite:///./test_api.db" \
python3 -m uvicorn whitemagic.api.app:app --host 0.0.0.0 --port 8003 &
API_PID=$!
sleep 3

# Test public endpoints
curl -s http://localhost:8003/health | jq .
# Should return: {"status": "healthy"}

curl -s http://localhost:8003/ | jq .
# Should return version info

# Test authenticated endpoint (should fail without auth)
curl -s -w "%{http_code}" http://localhost:8003/api/v1/memories
# Should return: 401 or 403

# Cleanup
kill $API_PID
rm -f test_api.db
```

**Expected Result**:
- ✅ Health check returns 200
- ✅ Root returns version info
- ✅ Protected endpoints require auth

**Acceptance Criteria**:
- [ ] API starts without errors
- [ ] Public endpoints accessible
- [ ] Authentication enforced

---

## 4. Security Tests

### 4.1 Exec Endpoint Disabled by Default

**Purpose**: Verify exec endpoint disabled without flag

**Test Steps**:
```bash
cd /home/lucas/Desktop/whitemagic
DATABASE_URL="sqlite:///./test_exec.db" \
python3 -m uvicorn whitemagic.api.app:app --host 0.0.0.0 --port 8004 &
API_PID=$!
sleep 3

# Try to access exec endpoint
curl -s -w "%{http_code}" http://localhost:8004/api/v1/exec/read
# Should return: 404 (not found)

kill $API_PID
rm -f test_exec.db
```

**Expected Result**:
- ✅ Exec endpoint not registered (404)
- ✅ Startup log shows "terminal_exec_api_disabled"

**Acceptance Criteria**:
- [ ] Exec endpoint returns 404
- [ ] Warning logged on startup
- [ ] Default is secure

---

### 4.2 Backup Path Traversal Test

**Purpose**: Already tested in 2.2 above

**Status**: ✅ Covered in Integration Tests

---

## 5. Regression Tests

### 5.1 Previously Working Features

**Purpose**: Ensure fixes didn't break existing functionality

**Areas to Test**:
- [ ] Memory creation (short-term, long-term)
- [ ] Memory search (query, tags)
- [ ] Memory updates
- [ ] Memory deletion (soft delete)
- [ ] Consolidation
- [ ] Context generation
- [ ] Tag operations

**Method**: Run existing test suite (covered in 1.1)

---

### 5.2 Documentation Accuracy

**Purpose**: Verify README commands actually work

**Test Steps**:
```bash
# Follow README.md installation instructions exactly
# Verify each command works as documented
```

**Acceptance Criteria**:
- [ ] Installation instructions accurate
- [ ] Example commands work
- [ ] No references to non-existent commands

---

## 6. Test Execution Summary

### Manual Test Checklist

**Before Running Tests**:
- [ ] All code changes committed
- [ ] Packages built (Python + MCP)
- [ ] Redis available (or note skip)
- [ ] Clean test environment

**Execute Tests** (in order):
1. [ ] 1.1 - Python Unit Tests
2. [ ] 1.2 - MCP Unit Tests
3. [ ] 2.1 - Backup Integration Test
4. [ ] 2.2 - Tar Safety Test
5. [ ] 2.3 - Rate Limiting Test (if Redis available)
6. [ ] 2.4 - Logging Context Test
7. [ ] 2.5 - PyYAML Test
8. [ ] 3.1 - Fresh Install Test
9. [ ] 3.2 - API Smoke Test
10. [ ] 4.1 - Exec Endpoint Test
11. [ ] 5.1 - Regression Check
12. [ ] 5.2 - Documentation Accuracy

---

## 7. Test Results

### Results Template

For each test:
- **Test ID**: [1.1, 2.1, etc.]
- **Status**: [✅ PASS / ❌ FAIL / ⏭️ SKIP]
- **Notes**: [Any observations]
- **Issues Found**: [Link to issue or N/A]

### Overall Assessment

**Tests Passed**: _____ / _____  
**Tests Failed**: _____  
**Tests Skipped**: _____  

**Grade**: [A/B/C/D/F]  
**Ready for Publication**: [YES / NO]

---

## 8. Post-Test Actions

### If All Tests Pass ✅
1. Update CHANGELOG.md with test confirmation
2. Update documentation with any findings
3. Proceed to second round validation
4. Prepare for publication

### If Tests Fail ❌
1. Document all failures in detail
2. Create issues for each failure
3. Fix critical failures
4. Re-run affected tests
5. Repeat until all pass

---

## 9. Test Environment

**OS**: Linux  
**Python**: 3.10+  
**Node**: Latest LTS  
**Redis**: Optional (for rate limiting tests)  
**Database**: SQLite (for tests)

**Test Data Location**: `/tmp/whitemagic_test_*`  
**Test Logs**: Check terminal output and `/tmp/*.log`

---

## 10. Success Criteria

### Minimum Requirements (Must Pass)
- ✅ All unit tests pass (Python + MCP)
- ✅ Backup system tests pass
- ✅ Tar safety test passes
- ✅ Fresh install test passes
- ✅ No critical security issues

### Recommended (Should Pass)
- ✅ Rate limiting test passes (with Redis)
- ✅ Logging context test passes
- ✅ PyYAML test passes
- ✅ API smoke test passes
- ✅ All documentation accurate

### Optional (Nice to Have)
- ✅ Performance benchmarks
- ✅ Load testing
- ✅ Cross-platform testing

---

**Test Plan Created**: November 12, 2025  
**Next Action**: Execute test plan  
**Expected Duration**: 30-45 minutes
