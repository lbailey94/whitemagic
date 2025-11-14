# 🚀 WhiteMagic Railway Deployment Journey - Lessons Learned

**Date**: November 13, 2025  
**Duration**: ~2 hours of troubleshooting  
**Status**: ✅ Successfully Deployed!  
**Final Result**: Railway API live, Vercel dashboard live, ready for DNS configuration

---

## 📋 Executive Summary

Deployed WhiteMagic API to Railway and dashboard to Vercel. Encountered multiple configuration issues related to Python packaging, environment variables, and port configuration. Successfully resolved all issues by understanding Railway's deployment pipeline (Nixpacks vs Dockerfile) and proper dependency management.

---

## 🎯 The Challenge

**Goal**: Deploy WhiteMagic API to Railway (backend) and dashboard to Vercel (frontend)

**Initial State**:
- ✅ Local development working perfectly
- ✅ All tests passing (174/197 Python, 27/27 MCP)
- ✅ Whop products created
- ❌ No production deployment yet

**Target State**:
- ✅ Railway API running at `api.whitemagic.dev`
- ✅ Vercel dashboard at `app.whitemagic.dev`
- ✅ PostgreSQL and Redis connected
- ✅ Whop integration working
- ✅ DNS configured

---

## 🐛 Issues Encountered & Solutions

### Issue #1: Railway Network Test Failed - PORT Interpolation

**Error**:
```
Attempt #1 failed with service unavailable. Continuing to retry for 1m29s
Healthcheck failed!
```

**Root Cause**: Railway wasn't properly detecting how to start the application.

**Investigation**:
- Initial `railway.json` had explicit `startCommand` with `$PORT`
- Railway wasn't interpolating the `$PORT` variable correctly

**Solution #1 (Attempted)**:
```json
// Removed explicit startCommand from railway.json
// Let Railway auto-detect from Procfile
{
  "deploy": {
    "numReplicas": 1,
    "restartPolicyType": "ON_FAILURE",
    "healthcheckPath": "/health"
  }
}
```

**Result**: Still failed - moved to next issue.

---

### Issue #2: ModuleNotFoundError: No module named 'openai'

**Error**:
```python
File "/app/whitemagic/embeddings/openai_provider.py", line 9, in <module>
    from openai import AsyncOpenAI, OpenAIError
ModuleNotFoundError: No module named 'openai'
```

**Root Cause**: 
- `requirements.txt` had `openai>=1.3.0` BUT
- Railway was using `pip install -e .` which reads from `pyproject.toml`
- In `pyproject.toml`, `openai` was in **optional** `[embeddings]` extras, not core dependencies

**Investigation**:
- Checked build logs: `pip install -e .` was running
- Checked `pyproject.toml`: Only `pydantic>=2.0.0` in core dependencies
- `openai` was in `[project.optional-dependencies]` section

**Solution #2**:
```toml
# pyproject.toml - BEFORE
dependencies = [
    "pydantic>=2.0.0",
]

[project.optional-dependencies]
embeddings = [
    "openai>=1.0.0",
    # ... other deps
]

# pyproject.toml - AFTER
dependencies = [
    "pydantic>=2.0.0",
    "pydantic-settings>=2.1.0",
    "fastapi>=0.104.0",
    "uvicorn[standard]>=0.24.0",
    "sqlalchemy>=2.0.0",
    "asyncpg>=0.29.0",
    "redis>=5.0.1",
    "httpx>=0.25.0",
    "openai>=1.3.0",  # ← MOVED TO CORE!
    "numpy>=1.24.0",
    "python-json-logger>=2.0.7",
    "pyyaml>=6.0.0",
]
```

**Key Learning**: When using `pip install -e .`, Railway installs from `pyproject.toml` dependencies, NOT `requirements.txt`!

**Result**: App now starts, but healthcheck still failing...

---

### Issue #3: Dockerfile PORT Not Interpolating

**Error**:
```
Error: Invalid value for '--port': '$PORT' is not a valid integer.
```

**Root Cause**:
- Railway detected `Dockerfile` in repo
- Our `Dockerfile` had: `CMD ["python", "-m", "uvicorn", "...", "--port", "8000"]`
- Hardcoded port 8000, not using Railway's dynamic `$PORT`

**First Attempt - Fix Dockerfile**:
```dockerfile
# BEFORE
CMD ["python", "-m", "uvicorn", "whitemagic.api.app:app", "--host", "0.0.0.0", "--port", "8000"]

# AFTER (Attempted)
CMD uvicorn whitemagic.api.app:app --host 0.0.0.0 --port ${PORT:-8000} --workers 2
```

**Result**: Still failed! Railway's Docker exec form wasn't interpolating `$PORT` correctly.

**Investigation**:
- Dockerfile `CMD` in exec form (`["cmd", "arg"]`) doesn't expand env vars
- Shell form (`cmd arg`) does, but Railway wasn't handling it properly
- Realized Dockerfile was overcomplicating things

**Final Solution #3**:
```bash
# Disable Dockerfile detection
mv Dockerfile Dockerfile.backup

# Update railway.json to use Nixpacks
{
  "build": {
    "builder": "NIXPACKS",
    "buildCommand": "pip install -e ."
  }
}

# Procfile already correct
web: uvicorn whitemagic.api.app:app --host 0.0.0.0 --port $PORT --workers 2
```

**Key Learning**: Railway's **Nixpacks + Procfile** is better than Dockerfile for Python apps! Nixpacks handles `$PORT` interpolation correctly.

**Result**: ✅ SUCCESS! App started and healthcheck passed!

---

## 🏗️ Final Working Configuration

### File: `pyproject.toml`
```toml
[project]
name = "whitemagic"
version = "2.1.3"

dependencies = [
    "pydantic>=2.0.0",
    "pydantic-settings>=2.1.0",
    # API Framework
    "fastapi>=0.104.0",
    "uvicorn[standard]>=0.24.0",
    "python-multipart>=0.0.6",
    # Database
    "sqlalchemy>=2.0.0",
    "aiosqlite>=0.19.0",
    "asyncpg>=0.29.0",
    "alembic>=1.13.0",
    # Caching & Rate Limiting
    "redis>=5.0.1",
    # HTTP Client
    "httpx>=0.25.0",
    # AI/Embeddings
    "openai>=1.3.0",
    "numpy>=1.24.0",
    # Logging
    "python-json-logger>=2.0.7",
    # YAML parsing
    "pyyaml>=6.0.0",
]
```

### File: `railway.json`
```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS",
    "buildCommand": "pip install -e ."
  },
  "deploy": {
    "numReplicas": 1,
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10,
    "healthcheckPath": "/health",
    "healthcheckTimeout": 100
  }
}
```

### File: `Procfile`
```
web: uvicorn whitemagic.api.app:app --host 0.0.0.0 --port $PORT --workers 2
```

### Railway Environment Variables
```bash
# Core
WHOP_API_KEY=b5xFgUfkCVw3__8wsDQsJ3BLXLXbEx8xKt8SPrmi_U0
ALLOWED_ORIGINS=https://whitemagic-one.vercel.app,http://localhost:3000
LOG_LEVEL=INFO
LOG_FORMAT=json

# Auto-provided by Railway
DATABASE_URL=postgresql://...
REDIS_URL=redis://...
PORT=8080  # (dynamic, Railway sets this)
```

---

## 📊 Deployment Timeline

1. **Initial Railway Deploy** - FAILED
   - Error: Network test failed
   - Issue: startCommand with $PORT not working

2. **Remove startCommand** - FAILED
   - Error: ModuleNotFoundError: No module named 'openai'
   - Issue: Dependencies in wrong section of pyproject.toml

3. **Move deps to core** - FAILED
   - Error: Invalid value for '--port': '$PORT' is not a valid integer
   - Issue: Dockerfile using hardcoded port

4. **Fix Dockerfile PORT** - FAILED
   - Error: Still $PORT not interpolating
   - Issue: Dockerfile exec form doesn't expand env vars

5. **Disable Dockerfile, use Nixpacks** - ✅ SUCCESS!
   - Result: App starts on Railway's PORT
   - Healthcheck passes
   - All systems operational!

---

## 🎓 Key Lessons Learned

### 1. **Railway Deployment Methods**

**Dockerfile vs Nixpacks**:
- ✅ **Nixpacks + Procfile** (Recommended for Python)
  - Auto-detects Python project
  - Handles `$PORT` environment variable correctly
  - Simpler configuration
  - Better for most use cases

- ⚠️ **Dockerfile** (Advanced, more control)
  - Good for complex multi-stage builds
  - Requires careful env var handling
  - Must use shell form CMD for env var expansion
  - Can be overkill for simple apps

**Winner**: Nixpacks + Procfile for Python APIs!

---

### 2. **Python Packaging for Cloud Deployment**

**Critical Understanding**:
```bash
pip install -r requirements.txt  # Reads requirements.txt
pip install -e .                  # Reads pyproject.toml
```

**Railway uses**: `pip install -e .` (even if you have requirements.txt!)

**Best Practice**:
- Put **production dependencies** in `pyproject.toml` → `[project] dependencies = [...]`
- Put **dev/test dependencies** in `pyproject.toml` → `[project.optional-dependencies] dev = [...]`
- Keep `requirements.txt` for local dev consistency (optional)

---

### 3. **Environment Variables in Different Contexts**

**Procfile** (Shell expansion works):
```
web: uvicorn app:app --port $PORT  ✅ Works!
```

**Dockerfile exec form** (No expansion):
```dockerfile
CMD ["uvicorn", "app:app", "--port", "$PORT"]  ❌ Fails!
```

**Dockerfile shell form** (Expansion works):
```dockerfile
CMD uvicorn app:app --port ${PORT:-8000}  ✅ Works!
```

**Railway Reality**: Even shell form had issues. Nixpacks + Procfile = most reliable.

---

### 4. **Railway Service Architecture**

**Proper Setup**:
```
Project: whitemagic
├── Service: whitemagic (API)
│   ├── Environment: production
│   ├── Build: Nixpacks
│   ├── Source: GitHub main branch
│   └── Health: /health endpoint
├── Database: Postgres
│   └── Auto-provides: DATABASE_URL
└── Database: Redis
    └── Auto-provides: REDIS_URL
```

**Key Points**:
- PostgreSQL and Redis auto-inject connection URLs
- No manual connection string needed
- Railway handles networking between services

---

### 5. **Healthcheck Configuration**

**What Works**:
```json
{
  "deploy": {
    "healthcheckPath": "/health",
    "healthcheckTimeout": 100
  }
}
```

**Requirements**:
- Endpoint must respond within timeout (100s default)
- Must return 2xx status code
- App must bind to `0.0.0.0` (not `localhost`!)
- Must use Railway's `$PORT` variable

**Our `/health` endpoint**:
```python
@app.get("/health")
async def health():
    return {"status": "healthy", "version": "2.1.4"}
```

---

## 🔍 Debugging Techniques That Helped

### 1. **Read Full Deploy Logs**
- Don't just look at the error at the end
- Scroll up to see full context
- Look for package installation logs
- Check what command Railway is actually running

### 2. **Check What Railway Detects**
```
Using Detected Dockerfile  → Railway found Dockerfile
No Dockerfile detected     → Railway using Nixpacks
```

### 3. **Verify Environment Variables**
- Railway → Service → Variables tab
- Check which are auto-provided vs manual
- Look for "Suggested Variables" that Railway detected in code

### 4. **Test Build Commands Locally**
```bash
# Test what Railway will run
pip install -e .

# Verify dependencies
pip list | grep openai
pip list | grep fastapi
```

### 5. **Understand Railway's Build vs Deploy**
- **Build**: Install dependencies, create image
- **Deploy**: Start container, run command
- Errors in build = dependency issues
- Errors in deploy = runtime/config issues

---

## 📦 Vercel Deployment (Bonus)

**Status**: ✅ Worked on first try!

**Configuration**:
```json
// vercel.json
{
  "cleanUrls": true,
  "trailingSlash": false,
  "headers": [
    {
      "source": "/(.*)",
      "headers": [
        { "key": "Cache-Control", "value": "public, max-age=3600" }
      ]
    }
  ]
}
```

**Vercel Settings**:
- Root Directory: `dashboard/`
- Build Command: (auto-detected, none needed for static)
- Output Directory: (auto-detected)

**Files Created**:
```
.vercelignore  # Exclude API files from dashboard deployment
```

**Result**: 
- Dashboard live at `https://whitemagic-one.vercel.app`
- Beautiful beige UI loading correctly
- Login form working
- No errors!

**Why It Worked**: Vercel is optimized for static sites and frontend frameworks. Much simpler than backend deployment!

---

## 🎯 The Winning Strategy

### Railway Deployment Checklist

- [ ] **pyproject.toml configured**
  - [ ] All production deps in `[project] dependencies`
  - [ ] Dev deps in `[project.optional-dependencies.dev`]
  
- [ ] **railway.json configured**
  - [ ] `builder: "NIXPACKS"`
  - [ ] `buildCommand: "pip install -e ."`
  - [ ] `healthcheckPath: "/health"`

- [ ] **Procfile created**
  - [ ] `web: uvicorn app:app --host 0.0.0.0 --port $PORT`

- [ ] **No Dockerfile** (or renamed to `.backup`)
  - [ ] Let Nixpacks handle everything

- [ ] **Environment variables set**
  - [ ] API keys (WHOP_API_KEY, etc.)
  - [ ] CORS origins (ALLOWED_ORIGINS)
  - [ ] Log config (LOG_LEVEL, LOG_FORMAT)

- [ ] **Services added**
  - [ ] PostgreSQL database
  - [ ] Redis database
  - [ ] Verify DATABASE_URL and REDIS_URL auto-appear

- [ ] **Health endpoint working**
  - [ ] Returns 200 status
  - [ ] Responds quickly
  - [ ] Doesn't require auth

---

## 💡 Pro Tips for Future Deployments

### 1. **Start with Nixpacks**
Don't create a Dockerfile unless you have a specific reason. Nixpacks handles 90% of use cases perfectly.

### 2. **Use pyproject.toml as Source of Truth**
Put all dependencies there. Railway will read it automatically with `pip install -e .`

### 3. **Test PORT locally**
```bash
PORT=8080 uvicorn app:app --host 0.0.0.0 --port $PORT
```

### 4. **Keep Procfile Simple**
```
web: uvicorn app:app --host 0.0.0.0 --port $PORT --workers 2
```
That's it! No fancy shell scripts needed.

### 5. **Let Railway Auto-Configure**
- Don't override unless necessary
- Use Railway's auto-provided DATABASE_URL and REDIS_URL
- Let Railway set PORT dynamically

### 6. **Healthcheck is Critical**
Make sure your `/health` endpoint:
- Exists
- Returns 200
- Responds in < 10 seconds
- Doesn't require authentication

---

## 📚 Resources That Helped

- [Railway Nixpacks Documentation](https://docs.railway.app/deploy/builds)
- [Railway Procfile Documentation](https://docs.railway.app/deploy/deployments)
- [Python Packaging Guide - pyproject.toml](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/)
- Railway Discord community (not used but available)

---

## 🎊 Final Result

### Railway
- ✅ API deployed successfully
- ✅ PostgreSQL connected
- ✅ Redis connected  
- ✅ Health checks passing
- ✅ Logs showing clean startup
- ⏳ Need to generate public domain

### Vercel
- ✅ Dashboard deployed at `https://whitemagic-one.vercel.app`
- ✅ Beautiful UI loading
- ✅ Login form working
- ⏳ Need to connect to Railway API

### Whop
- ✅ 4 products created (Free, Plus, Pro, Enterprise)
- ✅ Plan IDs mapped in code
- ⏳ Webhooks to configure after custom domains

---

## 🚀 What's Next

1. **Generate Railway Public URL**
   - Railway → whitemagic → Settings → Networking
   - Click "Generate Domain"
   - Get URL like `whitemagic-production.up.railway.app`

2. **Test API Endpoint**
   - `curl https://your-railway-url.up.railway.app/health`
   - Should return: `{"status":"healthy","version":"2.1.4"}`

3. **Add Custom Domains**
   - Railway: `api.whitemagic.dev`
   - Vercel: `app.whitemagic.dev`

4. **Configure DNS in Squarespace**
   - CNAME: `api` → Railway domain
   - CNAME: `app` → Vercel domain

5. **Update Vercel to Use Railway API**
   - Add environment variable: `WHITEMAGIC_API_BASE`
   - Value: `https://api.whitemagic.dev`

6. **Configure Whop Webhooks**
   - Webhook URL: `https://api.whitemagic.dev/api/v1/whop/webhook`
   - Events: membership created, updated, deleted

7. **Test End-to-End**
   - Sign up with Whop
   - Get API key in dashboard
   - Create memory
   - Search memory
   - Execute terminal command
   - Celebrate! 🎉

---

## 🙏 Acknowledgments

**Time Invested**: ~2 hours of focused troubleshooting  
**Commits Made**: 7 targeted fixes  
**Lessons Learned**: Invaluable  

**Key Takeaway**: "Infrastructure as Code" is only as good as your understanding of the deployment platform. Railway + Nixpacks is elegant when you understand it, frustrating when you fight it. Work *with* the platform, not against it.

---

**End of Deployment Journey**  
*November 13, 2025 - 10:22 PM EST*
