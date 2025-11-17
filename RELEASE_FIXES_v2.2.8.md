# Release Process Fixes for v2.2.8

**Based on**: v2.2.7 release session analysis  
**Date**: November 16, 2025  
**Priority**: MUST FIX before v2.2.8 release

---

## 🔴 HIGH PRIORITY FIXES

### 1. Fix License Deprecation Warning

**File**: `pyproject.toml`

**Change from**:
```toml
[project.license]
text = "MIT"

[project]
classifiers = [
    "License :: OSI Approved :: MIT License",
    ...
]
```

**Change to**:
```toml
[project]
license = "MIT"  # Simple SPDX expression

# Remove license classifier from classifiers list
classifiers = [
    "Development Status :: 5 - Production/Stable",
    "Intended Audience :: Developers",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Topic :: Software Development :: Libraries :: Python Modules",
    # DO NOT include: "License :: OSI Approved :: MIT License"
]
```

**Deadline**: Before Feb 18, 2026  
**Impact**: Builds will fail after deadline

---

### 2. Fix Package Discovery Warnings

**File**: `pyproject.toml`

**Add explicit package configuration**:
```toml
[tool.setuptools]
packages = [
    "whitemagic",
    "whitemagic.api",
    "whitemagic.api.routes",
    "whitemagic.cli",
    "whitemagic.config",
    "whitemagic.embeddings",
    "whitemagic.parallel",
    "whitemagic.scratchpad",
    "whitemagic.search",
    "whitemagic.sessions",
    "whitemagic.setup",
    "whitemagic.templates",
    "whitemagic.terminal",
]

# OR use find with explicit include:
[tool.setuptools.packages.find]
where = ["."]
include = ["whitemagic*"]
exclude = ["tests*", "docs*", "private*"]
namespaces = false
```

**Alternative**: Update `setup.py` to be more explicit.

---

## 🟡 MEDIUM PRIORITY FIXES

### 3. Configure TestPyPI Credentials

**File**: `~/.pypirc` (user home directory)

**Create**:
```ini
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
username = __token__
password = pypi-AgE...YOUR_PRODUCTION_TOKEN...

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = pypi-AgE...YOUR_TEST_TOKEN...
```

**Security**:
```bash
chmod 600 ~/.pypirc
```

**Generate tokens**:
- Production: https://pypi.org/manage/account/token/
- Test: https://test.pypi.org/manage/account/token/

**Usage**:
```bash
# Test upload:
python3 -m twine upload --repository testpypi dist/*

# Production upload:
python3 -m twine upload dist/*
```

---

### 4. Fix TypeScript Repository URL

**File**: `clients/typescript/package.json` AND `whitemagic-mcp/package.json`

**Change from**:
```json
"repository": {
  "type": "git",
  "url": "https://github.com/lbailey94/whitemagic.git"
}
```

**Change to**:
```json
"repository": {
  "type": "git",
  "url": "git+https://github.com/lbailey94/whitemagic.git"
}
```

---

## 🟢 LOW PRIORITY / BEST PRACTICES

### 5. Clean Build Artifacts Script

**File**: `scripts/clean_build.sh`

**Create**:
```bash
#!/bin/bash
# Clean all build artifacts before release

echo "🧹 Cleaning build artifacts..."

# Python main package
rm -rf dist/ build/ *.egg-info
rm -rf whitemagic.egg-info/

# Python client
rm -rf clients/python/dist/ clients/python/build/
rm -rf clients/python/*.egg-info

# TypeScript client
rm -rf clients/typescript/dist/

# MCP server
rm -rf whitemagic-mcp/dist/

echo "✅ Clean complete!"
echo ""
echo "Now run:"
echo "  python3 -m build"
echo "  cd clients/python && python3 -m build"
echo "  cd clients/typescript && npm run build"
echo "  cd whitemagic-mcp && npm run build"
```

**Usage**:
```bash
chmod +x scripts/clean_build.sh
./scripts/clean_build.sh
```

---

### 6. Automated Release Script

**File**: `scripts/release.sh`

**Create**:
```bash
#!/bin/bash
set -e  # Exit on error

VERSION=$1

if [ -z "$VERSION" ]; then
    echo "Usage: ./scripts/release.sh 2.2.8"
    exit 1
fi

echo "🚀 Releasing WhiteMagic v$VERSION"
echo ""

# 1. Clean
echo "1️⃣  Cleaning build artifacts..."
./scripts/clean_build.sh

# 2. Update versions
echo "2️⃣  Updating version numbers..."
echo "$VERSION" > VERSION
# TODO: Update other version files (will be automated in v2.2.8 CLI)

# 3. Run tests
echo "3️⃣  Running tests..."
pytest

# 4. Run audit
echo "4️⃣  Running security audit..."
python scripts/audit_for_release.py

# 5. Build packages
echo "5️⃣  Building packages..."
python3 -m build

cd clients/python
python3 -m build
cd ../..

cd clients/typescript
npm run build
cd ../..

cd whitemagic-mcp
npm run build
cd ..

# 6. Upload to TestPyPI first
echo "6️⃣  Uploading to TestPyPI..."
python3 -m twine upload --repository testpypi dist/*
cd clients/python
python3 -m twine upload --repository testpypi dist/*
cd ../..

# Wait for user confirmation
echo ""
echo "✅ TestPyPI upload complete!"
echo "   Check: https://test.pypi.org/project/whitemagic/"
echo ""
read -p "Proceed with production upload? [y/N] " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]
then
    echo "❌ Cancelled."
    exit 1
fi

# 7. Upload to production
echo "7️⃣  Uploading to production PyPI..."
python3 -m twine upload dist/*
cd clients/python
python3 -m twine upload dist/*
cd ../..

# 8. Publish npm packages
echo "8️⃣  Publishing npm packages..."
cd whitemagic-mcp
npm publish
cd ..

cd clients/typescript
npm publish
cd ../..

# 9. Tag and push
echo "9️⃣  Creating git tag..."
git tag "v$VERSION"
git push origin "v$VERSION"

echo ""
echo "🎉 Release v$VERSION complete!"
echo ""
echo "Next steps:"
echo "  1. Deploy to Railway: railway up"
echo "  2. Create GitHub release"
echo "  3. Announce on social media"
```

**Usage**:
```bash
chmod +x scripts/release.sh
./scripts/release.sh 2.2.8
```

---

### 7. Railway Deployment Verification

**File**: `scripts/verify_railway.sh`

**Create**:
```bash
#!/bin/bash
set -e

RAILWAY_URL=${1:-"https://imaginative-courage.railway.app"}
API_KEY=$2

if [ -z "$API_KEY" ]; then
    echo "Usage: ./scripts/verify_railway.sh https://your-app.railway.app YOUR_API_KEY"
    exit 1
fi

echo "🔍 Verifying Railway deployment: $RAILWAY_URL"
echo ""

# 1. Health check
echo "1️⃣  Health check..."
HEALTH=$(curl -s "$RAILWAY_URL/health")
echo "   Response: $HEALTH"

VERSION=$(echo $HEALTH | grep -oP '(?<="version":")[^"]*')
echo "   Version: $VERSION"
echo ""

# 2. Create memory test
echo "2️⃣  Testing memory creation..."
CREATE_RESPONSE=$(curl -s -X POST "$RAILWAY_URL/api/v1/memories" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"title":"Deployment Test","content":"Verifying v'$VERSION'"}')
echo "   Response: $CREATE_RESPONSE"
echo ""

# 3. Search test
echo "3️⃣  Testing search..."
SEARCH_RESPONSE=$(curl -s -X POST "$RAILWAY_URL/api/v1/search" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query":"test"}')
echo "   Found: $(echo $SEARCH_RESPONSE | grep -oP '(?<="total":)\d+')"
echo ""

# 4. Parallel search test (v2.2.7+)
echo "4️⃣  Testing parallel search..."
PARALLEL_RESPONSE=$(curl -s -X POST "$RAILWAY_URL/api/v1/parallel/search" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"queries":["test","deployment"]}')
echo "   Response: $PARALLEL_RESPONSE"
echo ""

echo "✅ Verification complete!"
```

**Usage**:
```bash
chmod +x scripts/verify_railway.sh
./scripts/verify_railway.sh https://imaginative-courage.railway.app YOUR_API_KEY
```

---

## 📋 Updated Release Checklist for v2.2.8

### Pre-Release (DO THESE FIRST)
- [ ] Fix pyproject.toml license format
- [ ] Fix package discovery configuration
- [ ] Configure TestPyPI credentials
- [ ] Fix TypeScript repository URLs
- [ ] Create clean_build.sh script
- [ ] Create release.sh script
- [ ] Create verify_railway.sh script

### Build
- [ ] Run `./scripts/clean_build.sh`
- [ ] Run `pytest` (all tests passing)
- [ ] Run `python scripts/audit_for_release.py` (no HIGH issues)
- [ ] Build all packages (Python, TypeScript, MCP)

### Test Upload
- [ ] Upload to TestPyPI
- [ ] Verify TestPyPI packages install
- [ ] Test TypeScript packages locally

### Production Upload
- [ ] Upload to PyPI
- [ ] Upload Python client to PyPI
- [ ] Publish MCP to npm
- [ ] Publish TypeScript client to npm

### Deployment
- [ ] Deploy to Railway: `railway up`
- [ ] Verify Railway: `./scripts/verify_railway.sh`
- [ ] Check health endpoint
- [ ] Test API endpoints

### Post-Release
- [ ] Create GitHub release
- [ ] Tag version: `git tag v2.2.8`
- [ ] Push tag: `git push origin v2.2.8`
- [ ] Update CHANGELOG.md
- [ ] Announce on social media

---

## 🎯 Estimated Time Savings with Fixes

**v2.2.7 release time**: ~30 minutes (with manual fixes)  
**v2.2.8 release time** (with automation): ~10 minutes  
**Savings**: 20 minutes (66% faster!)

---

## 📊 Success Metrics

**v2.2.7 Results**:
- ✅ 4/5 packages published successfully
- ⚠️  10+ setuptools warnings
- ❌ TestPyPI failed
- ⏱️  ~30 minutes manual work

**v2.2.8 Goals**:
- ✅ 5/5 packages published (including TestPyPI)
- ✅ Zero setuptools warnings
- ✅ Automated verification
- ⏱️  ~10 minutes with automation

---

**Status**: Ready to implement for v2.2.8! 🚀
