# Security Review - November 14, 2025

**Reviewer**: Independent security audit  
**Date**: November 14, 2025, 9:30 PM EST  
**Scope**: All non-archive files and documentation  
**Quality**: ⭐⭐⭐⭐⭐ Excellent, thorough, actionable

## Executive Summary

Independent reviewer found **2 critical RCE vulnerabilities** and **5 high-priority issues**. Critical vulnerabilities have been patched immediately (commit `965c495`). Remaining issues tracked below for v2.1.7 release.

---

## 🔴 CRITICAL - PATCHED (Commit 965c495)

### 1. API Key Retrieval = Account Takeover ✅ FIXED

**File**: `whitemagic/api/routes/api_keys.py:33-77`  
**Vulnerability**: `/api/v1/api-keys/retrieve` has zero authentication  
**Impact**: Anyone with an email can generate API keys = full account takeover  
**Severity**: 🔴 CRITICAL

**Attack Scenario**:
1. Attacker learns any user email (support@whitemagic.dev, etc.)
2. POST to `/api/v1/api-keys/retrieve` with email
3. Get back raw API key with full permissions
4. Use key to access all user data / execute commands

**Fix Applied**:
- Endpoint now returns 503 with security explanation
- Documented proper flow: Whop webhook → signed token → email → validation

**Proper Implementation** (TODO v2.1.7):
```python
@router.post("/retrieve")
async def retrieve_api_key(
    request: RetrieveKeyRequest,
    session: DBSession,
):
    # 1. Extract token from request
    if not request.token:
        raise HTTPException(400, "Token required")
    
    # 2. Verify HMAC signature
    expected = hmac.new(WHOP_SECRET, request.email.encode(), "sha256").hexdigest()
    if not hmac.compare_digest(request.token, expected):
        raise HTTPException(403, "Invalid token")
    
    # 3. Check token is single-use (Redis/DB)
    if await is_token_used(request.token):
        raise HTTPException(403, "Token already used")
    
    # 4. Check token expiry (< 24 hours old)
    if not await is_token_valid(request.token):
        raise HTTPException(403, "Token expired")
    
    # 5. Mark token as used
    await mark_token_used(request.token)
    
    # 6. Generate API key
    raw_key, api_key = await create_api_key(...)
    return {"api_key": raw_key}
```

**Requirements**:
- Whop webhook must generate signed token
- Send token via email (requires SendGrid/Postmark)
- Token must be single-use, time-limited (24h)
- Rate limit: 1 key per user per hour

---

### 2. Terminal Execution API Enabled by Default ✅ FIXED

**File**: `whitemagic/api/app.py:302`  
**Vulnerability**: `WM_ENABLE_EXEC_API` defaults to `"true"`  
**Impact**: Combined with #1 = Remote Code Execution  
**Severity**: 🔴 CRITICAL

**Attack Chain**:
1. Use #1 to generate API key
2. POST to `/api/v1/exec/read` with commands
3. Or POST to `/api/v1/exec/` with `X-Confirm-Write-Operation: confirmed`
4. Execute arbitrary commands on server
5. Full server compromise

**Fix Applied**:
- Changed default: `"true"` → `"false"`
- Added security warnings to logs when enabled
- Breaking change: Users must explicitly opt-in

**Documentation Needed** (TODO):
- README.md warning about exec API
- INSTALL.md: Do NOT enable in production
- SECURITY.md: Threat model for exec API

---

## 🟠 HIGH PRIORITY - TODO v2.1.7

### 3. Incremental Backups Don't Work

**Files**:
- `whitemagic/cli_app.py:1174-1187` (advertises flag)
- `whitemagic/backup.py:292-320` (never implements)

**Issue**: CLI accepts `--incremental` flag but always does full backup  
**Impact**: Users think they have incremental backups but don't  
**Severity**: 🟠 HIGH - False advertising, data loss risk

**Code**:
```python
# backup.py:292-320
if last_backup:
    # TODO: Implement incremental logic
    pass  # ← Never implemented!
else:
    # Always takes this branch
    return self._collect_all_files()
```

**Fix Needed**:
```python
def _collect_backup_files(self, last_backup_path: Optional[Path] = None):
    if last_backup_path:
        # Load previous manifest
        with tarfile.open(last_backup_path, 'r:gz') as tar:
            manifest = json.loads(tar.extractfile('manifest.json').read())
        
        # Compare current files vs previous
        current_files = self._collect_all_files()
        changed_files = []
        
        for file_path, current_hash in current_files:
            prev_hash = manifest['files'].get(str(file_path))
            if prev_hash != current_hash:
                changed_files.append((file_path, current_hash))
        
        return changed_files
    else:
        return self._collect_all_files()
```

**Alternative**: Remove `--incremental` flag until implemented

---

### 4. Env/Stdin Fields Ignored in Terminal Execution

**Files**:
- `whitemagic/terminal/models.py:12-21` (defines fields)
- `whitemagic/terminal/executor.py:22-76` (doesn't use them)
- `whitemagic/terminal/mcp_tools.py:64-130` (doesn't forward them)

**Issue**: ExecutionRequest has `env`/`stdin` fields but they're never passed to subprocess  
**Impact**: API schema promises features that don't work  
**Severity**: 🟠 HIGH - Broken functionality

**Fix Needed**:
```python
# executor.py
def execute(
    self, 
    cmd: str, 
    args: Optional[List[str]] = None,
    cwd: Optional[str] = None,
    timeout_ms: Optional[int] = None,
    env: Optional[Dict[str, str]] = None,  # ← Add this
    stdin: Optional[str] = None,            # ← Add this
) -> ExecutionResult:
    full_cmd = [cmd] + (args or [])
    
    # Merge environment
    process_env = os.environ.copy()
    if env:
        process_env.update(env)
    
    # Run subprocess
    result = subprocess.run(
        full_cmd,
        cwd=cwd,
        env=process_env,        # ← Use it
        input=stdin,            # ← Use it
        text=True if stdin else None,
        capture_output=True,
        timeout=timeout_ms / 1000 if timeout_ms else None,
    )
```

**Tests Needed**:
```python
def test_executor_with_env():
    executor = Executor()
    result = executor.execute("sh", ["-c", "echo $MY_VAR"], env={"MY_VAR": "test"})
    assert result.stdout.strip() == "test"

def test_executor_with_stdin():
    executor = Executor()
    result = executor.execute("cat", stdin="hello")
    assert result.stdout == "hello"
```

---

### 5. Async Embeddings Block Event Loop

**File**: `whitemagic/embeddings/local_provider.py:32-62`  
**Issue**: `LocalEmbeddings.embed()` declared async but calls synchronous `SentenceTransformer.encode()`  
**Impact**: Blocks FastAPI event loop for 100-500ms per request  
**Severity**: 🟠 HIGH - Performance degradation, API becomes unresponsive

**Current Code**:
```python
async def embed(self, text: str) -> List[float]:
    return self.model.encode(text)  # ← BLOCKS event loop!
```

**Fix Needed**:
```python
async def embed(self, text: str) -> List[float]:
    return await asyncio.to_thread(self.model.encode, text)

async def embed_batch(self, texts: List[str]) -> List[List[float]]:
    return await asyncio.to_thread(self.model.encode, texts)
```

**Benefit**: API stays responsive during embeddings generation

---

### 6. Version Constant Drift

**Files**:
- `whitemagic/constants.py:8-10` says `2.1.3`
- `pyproject.toml:7` says `2.2.1`
- `VERSION` file says `2.2.1`

**Issue**: Duplicate version definitions have drifted  
**Impact**: Backup manifests, logs report wrong version  
**Severity**: 🟡 MEDIUM - Confusion, incorrect metadata

**Fix Needed**:
```python
# constants.py
from importlib.metadata import version

try:
    VERSION = version("whitemagic")
except Exception:
    # Fallback for development
    from pathlib import Path
    VERSION_FILE = Path(__file__).parent.parent / "VERSION"
    VERSION = VERSION_FILE.read_text().strip()
```

**Or simpler**:
```python
# constants.py
import whitemagic
VERSION = whitemagic.__version__
```

---

## 🟡 MEDIUM PRIORITY - TODO v2.1.8

### 7. Semantic Search Re-embeds Everything

**File**: `whitemagic/search/semantic.py:118-211`  
**Issue**: Every search request re-reads and re-embeds all files  
**Impact**: Slow for users with >100 memories (could be seconds)  
**Severity**: 🟡 MEDIUM - Performance issue, scales poorly

**Fix**: Use existing `EmbeddingCache` or disk cache

```python
class SemanticSearcher:
    def __init__(self, memory_manager, cache_dir=None):
        self.cache_dir = cache_dir or Path.home() / ".whitemagic" / "embeddings_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    async def _get_embedding(self, file_path: Path) -> List[float]:
        # Check cache
        cache_file = self.cache_dir / f"{file_path.name}.npy"
        file_mtime = file_path.stat().st_mtime
        
        if cache_file.exists():
            cache_mtime = cache_file.stat().st_mtime
            if cache_mtime > file_mtime:
                # Cache is fresh
                return np.load(cache_file).tolist()
        
        # Generate new embedding
        content = file_path.read_text()
        embedding = await self.embedder.embed(content)
        
        # Save to cache
        np.save(cache_file, np.array(embedding))
        return embedding
```

---

### 8. Missing Security Documentation

**Issue**: No warnings about exec API risk in user-facing docs  
**Impact**: Users might deploy with dangerous defaults (before today's fix)  
**Severity**: 🟡 MEDIUM - Documentation gap

**Files to Update**:
- `README.md`: Add security warning section
- `INSTALL.md`: Warn about exec API
- `SECURITY.md`: Document threat model

**Example**:
```markdown
## ⚠️ Security Considerations

### Terminal Execution API

The terminal execution API (`/api/v1/exec`) is **disabled by default** for security.

**Do NOT enable** unless:
- You control who has API keys
- Server is behind firewall
- You understand the RCE risk

To enable (controlled environments only):
```bash
export WM_ENABLE_EXEC_API=true
```

**Risk**: Any API key holder can execute commands on your server.
```

---

### 9. Backup Restore Doesn't Verify Hashes

**File**: `whitemagic/backup.py` (restore function)  
**Issue**: Restore only checks file count, not content integrity  
**Impact**: Corrupted backups could go undetected  
**Severity**: 🟡 MEDIUM - Data integrity risk

**Fix**: Compare file hashes during restore

```python
def restore_backup(backup_path: Path) -> bool:
    with tarfile.open(backup_path, 'r:gz') as tar:
        manifest = json.loads(tar.extractfile('manifest.json').read())
        
        # Extract files
        tar.extractall(target_dir)
        
        # Verify each file
        for file_path, expected_hash in manifest['files'].items():
            actual_hash = hashlib.sha256(Path(file_path).read_bytes()).hexdigest()
            if actual_hash != expected_hash:
                raise ValueError(f"Corruption detected: {file_path}")
```

---

## Implementation Timeline

### v2.1.6.1 (Hotfix - November 15, 2025)
- ✅ DONE: Disable API key retrieval endpoint
- ✅ DONE: Change exec API default to false
- ✅ DONE: Deploy security fixes

### v2.1.7 (December 2025)
- [ ] #3: Implement or remove incremental backups
- [ ] #4: Forward env/stdin in terminal execution
- [ ] #5: Fix async embeddings (asyncio.to_thread)
- [ ] #6: Fix version constant (use __version__)
- [ ] #8: Add security documentation
- [ ] Implement proper API key retrieval flow (signed tokens)

### v2.1.8 (January 2026)
- [ ] #7: Add semantic search caching
- [ ] #9: Add backup hash verification

---

## Credit

**Reviewer**: Anonymous independent security audit  
**Date**: November 14, 2025  
**Quality**: Exceptional - found critical vulnerabilities, provided clear fixes

**Thank you!** This review prevented a serious security incident.

---

## Lessons Learned

1. **Never trust email as authentication**
   - Email = identifier, not authenticator
   - Always require signed tokens or passwords

2. **Secure by default**
   - Dangerous features (exec API) should be opt-in
   - Changed: exec API now disabled by default

3. **Schema vs implementation**
   - API schema promises (env/stdin) must match implementation
   - Add tests to catch drift

4. **Independent reviews are invaluable**
   - Fresh eyes catch what developers miss
   - Schedule regular security audits

5. **Act fast on critical issues**
   - Disabled vulnerable endpoints immediately
   - Deployed fixes within 15 minutes of report

---

## Status Summary

- 🔴 Critical (2): ✅ **FIXED** (deployed)
- 🟠 High (4): 📋 Planned for v2.1.7
- 🟡 Medium (3): 📋 Planned for v2.1.7-v2.1.8

**All critical vulnerabilities patched.** System is now secure by default.
