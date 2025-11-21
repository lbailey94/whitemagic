# Release Checklist - v2.1.3

**Date**: November 12, 2025  
**Status**: Ready for final smoke tests

---

## ✅ Pre-Release Verification (COMPLETE)

- [x] All 196 Python tests passing
- [x] Semantic search tests re-enabled (14 tests)
- [x] Documentation links verified
- [x] Version references updated to 2.1.3
- [x] Code fixes validated (version hardcoding, exec API security)
- [x] create_demo_user.py script verified
- [x] Independent review findings addressed

---

## 🔄 Step 1: Final Smoke Tests (MANUAL)

### Docker Compose Test (~5 minutes)

Run the automated smoke test script:

```bash
cd /home/lucas/Desktop/whitemagic
./scripts/docker_smoke_test.sh
```

**Expected Output**:
```
✅ Version check passed: 2.1.3 detected
✅ Health status: healthy
✅ API docs accessible
✅ No critical errors detected
```

**If test fails**:
- Check `docker-compose logs api` for errors
- Verify DATABASE_URL and REDIS_URL in .env
- Ensure ports 8000, 3000, 5432, 6379 are available

**When done**: `docker-compose down`

---

### MCP Test Suite (~2 minutes)

Run the MCP test script:

```bash
cd /home/lucas/Desktop/whitemagic
./scripts/mcp_smoke_test.sh
```

**Expected Output**:
```
✅ Node.js: v18.x.x (or higher)
✅ npm: 9.x.x (or higher)
🧪 Running MCP test suite...
  27 passing
```

**If test fails**:
- Ensure Node.js 18+ is installed
- Check `whitemagic-mcp/src/` for TypeScript errors
- Run `npm install` in whitemagic-mcp/ directory

---

## 📦 Step 2: Commit & Tag Release

### Add all changes
```bash
cd /home/lucas/Desktop/whitemagic
git add -A
```

### Commit with release message
```bash
git commit -m "Release v2.1.3 - Independent review remediation

Code Fixes:
- Fix version hardcoding in middleware.py and backup.py (now dynamic)
- Harden exec API with Profile.PROD for read endpoint (security fix)
- Fix import path in middleware.py (from .version not ..version)
- Update test_backup.py to use VERSION constant

Documentation Fixes:
- Remove broken links to archived docs (NEXT_STEPS, DEPLOY_NOW, etc)
- Update all version references from 2.1.2 → 2.1.3
- Add working API key creation with scripts/create_demo_user.py
- Clean up DEPLOYMENT_GUIDE, START_HERE, QUICKSTART

Testing Improvements:
- Re-enable semantic search tests with mock provider (14 tests)
- Replace skipped stub with full test suite
- All 196 Python tests passing

Release Documentation:
- INDEPENDENT_REVIEW_FIXES_v2.1.3.md (AI fixes)
- REVIEW_FIXES_SUMMARY_v2.1.3.md (combined fixes)
- VERIFICATION_REPORT_v2.1.3.md (test verification)

Verification Status:
- 196/196 Python tests passing
- 27/27 MCP tests passing
- Docker compose smoke test passing
- Security hardening verified
- Documentation links validated

Ready for production deployment."
```

### Create annotated tag
```bash
git tag -a v2.1.3 -m "Release v2.1.3 - Independent review fixes

Major improvements:
- Security hardening (exec API now truly read-only)
- Dynamic version management (no more hardcoded versions)
- Documentation cleanup (removed broken links)
- Semantic search tests re-enabled (14 tests)
- Complete test coverage verification (196 tests)

See INDEPENDENT_REVIEW_FIXES_v2.1.3.md for details."
```

### Push to GitHub
```bash
# Push commits
git push origin main  # or your branch name

# Push tag (triggers CI/CD)
git push origin v2.1.3
```

---

## 🤖 Step 3: Monitor CI/CD

### GitHub Actions
Watch the build progress:
```
https://github.com/lbailey94/whitemagic/actions
```

**Expected Workflows**:
1. ✅ Python Tests (pytest)
2. ✅ MCP Tests (npm test)
3. ✅ PyPI Package Build & Upload
4. ✅ Docker Image Build & Push
5. ✅ GitHub Pages Deploy (optional)

**Typical Duration**: 5-10 minutes

**What to Watch For**:
- All tests passing in CI environment
- PyPI upload successful: `https://pypi.org/project/whitemagic/2.1.3/`
- Docker image available: `lbailey94/whitemagic:2.1.3`

**If CI fails**:
- Check workflow logs on GitHub Actions
- Most common issues:
  - Test failures (check test output)
  - PyPI credentials (check repository secrets)
  - Docker Hub credentials (check repository secrets)

---

## 🚀 Step 4: Production Deployment

### Option A: Railway Deployment

```bash
# SSH to Railway or use Railway CLI
railway up
```

### Option B: Manual Server Deployment

```bash
# SSH to production server
ssh user@your-server.com

# Pull latest code
cd /path/to/whitemagic
git fetch --tags
git checkout v2.1.3

# Rebuild and restart
docker-compose pull
docker-compose up -d --build

# Watch logs
docker-compose logs -f api
```

### Option C: Install from PyPI

```bash
pip install --upgrade whitemagic==2.1.3

# Or in production
pip install whitemagic==2.1.3 --no-cache-dir
```

---

## ✅ Step 5: Post-Deployment Verification

### Test Production Health Endpoint

```bash
# Replace with your production URL
curl https://your-api.com/health

# Expected response:
# {"status":"healthy","version":"2.1.3"}
```

### Verify Version

```bash
curl https://your-api.com/health | jq -r '.version'
# Expected: 2.1.3
```

### Test API Docs

```bash
curl -I https://your-api.com/docs
# Expected: HTTP 200 OK
```

### Check Production Logs

```bash
# Docker Compose
docker-compose logs api | tail -50

# Or via Railway CLI
railway logs

# Look for:
# - Startup success messages
# - No error/exception traces
# - Database connection success
# - Redis connection success (if enabled)
```

---

## 📋 Step 6: Create GitHub Release

### Navigate to Releases
```
https://github.com/lbailey94/whitemagic/releases/new
```

### Release Details
- **Tag**: v2.1.3 (auto-populated)
- **Title**: WhiteMagic v2.1.3 - Independent Review Fixes

### Release Notes Template

```markdown
# WhiteMagic v2.1.3 - Independent Review Fixes

**Release Date**: November 12, 2025  
**Status**: Production Ready

## 🎯 Highlights

- **Security Hardening**: Exec API read endpoint now enforces strict read-only access
- **Version Management**: Dynamic version references eliminate manual updates
- **Documentation Cleanup**: Removed all broken links and outdated references
- **Test Coverage**: Re-enabled semantic search tests (14 tests), 196 total tests passing

## 🔒 Security Improvements

- Fixed exec API to use `Profile.PROD` for read-only endpoint (was using `Profile.AGENT` which allowed write operations)
- Updated all version headers to use dynamic version detection
- Verified all security configurations current

## 🐛 Bug Fixes

- Fixed hardcoded API version in middleware (X-API-Version now shows current version)
- Fixed hardcoded version in backup manifests (now uses VERSION constant)
- Fixed import path in middleware.py (corrected relative import)
- Updated test assertions to use dynamic VERSION constant

## 📚 Documentation Updates

- Removed references to archived files (NEXT_STEPS.md, DEPLOY_NOW.md, PROJECT_STATUS.md)
- Updated all version references from 2.1.2 → 2.1.3
- Added working API key creation workflow with scripts/create_demo_user.py
- Cleaned up DEPLOYMENT_GUIDE, START_HERE, QUICKSTART

## 🧪 Testing Improvements

- Re-enabled semantic search test suite with mock provider (14 tests)
- All 196 Python tests passing
- All 27 MCP tests passing
- Docker compose smoke test passing

## 📦 Installation

### PyPI
```bash
pip install whitemagic==2.1.3
```

### Docker
```bash
docker pull lbailey94/whitemagic:2.1.3
```

### From Source
```bash
git clone https://github.com/lbailey94/whitemagic.git
cd whitemagic
git checkout v2.1.3
pip install -e .
```

## 📖 Full Details

See attached release documentation:
- [INDEPENDENT_REVIEW_FIXES_v2.1.3.md](INDEPENDENT_REVIEW_FIXES_v2.1.3.md) - Detailed fixes
- [VERIFICATION_REPORT_v2.1.3.md](VERIFICATION_REPORT_v2.1.3.md) - Test verification

## 🔗 Links

- **Documentation**: https://lbailey94.github.io/whitemagic
- **PyPI Package**: https://pypi.org/project/whitemagic/2.1.3/
- **Docker Image**: https://hub.docker.com/r/lbailey94/whitemagic

## 🙏 Acknowledgments

Special thanks to the independent reviewer who identified these issues and provided specific, actionable feedback with line-number precision.

---

**Full Changelog**: https://github.com/lbailey94/whitemagic/compare/v2.1.2...v2.1.3
```

### Attach Documentation Files
- `INDEPENDENT_REVIEW_FIXES_v2.1.3.md`
- `VERIFICATION_REPORT_v2.1.3.md`
- `REVIEW_FIXES_SUMMARY_v2.1.3.md`

---

## 📢 Step 7: Announce Release (Optional)

### Update README Badge
If you have a version badge in README.md, ensure it reflects 2.1.3.

### Social/Community
- Post to project discussions
- Update any status pages
- Notify integration partners

---

## ✅ Final Checklist

Before marking complete, verify:

- [ ] Docker smoke test passed
- [ ] MCP test suite passed (27/27)
- [ ] Git commit created
- [ ] Git tag v2.1.3 created
- [ ] Changes pushed to GitHub
- [ ] Tag pushed to GitHub
- [ ] CI/CD pipeline completed successfully
- [ ] PyPI package available: https://pypi.org/project/whitemagic/2.1.3/
- [ ] Docker image available: lbailey94/whitemagic:2.1.3
- [ ] Production deployment completed
- [ ] Production health check shows version 2.1.3
- [ ] GitHub release created with documentation
- [ ] Release announced (if applicable)

---

## 🆘 Troubleshooting

### Docker Smoke Test Fails
**Issue**: Health endpoint returns wrong version  
**Fix**: Rebuild image with `docker-compose build --no-cache api`

**Issue**: Services won't start  
**Fix**: Check `docker-compose logs` for port conflicts or config errors

### CI/CD Fails
**Issue**: Tests fail in CI but pass locally  
**Fix**: Check for environment differences (Python version, dependencies)

**Issue**: PyPI upload fails  
**Fix**: Verify PYPI_API_TOKEN secret is set correctly

**Issue**: Docker build fails  
**Fix**: Verify DOCKER_USERNAME and DOCKER_PASSWORD secrets

### Production Issues
**Issue**: Version shows old number  
**Fix**: Ensure code was pulled from v2.1.3 tag, not old branch

**Issue**: Database migration errors  
**Fix**: Run `alembic upgrade head` manually

---

## 📞 Need Help?

- **Issues**: https://github.com/lbailey94/whitemagic/issues
- **Discussions**: https://github.com/lbailey94/whitemagic/discussions

---

**Prepared**: November 12, 2025  
**Next Action**: Run Docker and MCP smoke tests
