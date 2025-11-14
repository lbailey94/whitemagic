# SDK Publishing Guide

## ✅ Pre-Publishing Checklist Complete

Both SDKs have been tested and are ready to publish!

### TypeScript SDK Status
- ✅ Builds successfully (DOM types fixed)
- ✅ Test script created (`test-sdk.js`)
- ✅ Connects to API health endpoint
- ✅ LICENSE file included
- ✅ Package metadata verified
- ✅ Size: 12.5 kB unpacked

### Python SDK Status
- ✅ Builds successfully (hatchling)
- ✅ Test script created (`test_sdk.py`)
- ✅ Successfully tested against live API
- ✅ LICENSE file included
- ✅ Package metadata verified
- ✅ Wheel + source dist generated

---

## 📦 Publishing Instructions

### 1. Set Up Accounts (First Time Only)

#### npm Account
```bash
# Create account at https://www.npmjs.com/signup
# Enable 2FA: https://www.npmjs.com/settings/[username]/twofa

# Login locally
npm login
# Enter: username, password, email, OTP
```

#### PyPI Account
```bash
# Create account at https://pypi.org/account/register/
# Enable 2FA: https://pypi.org/manage/account/#two-factor

# Create API token at: https://pypi.org/manage/account/token/
# Scope: Entire account (or specific project later)

# Configure credentials
pip install twine
# Store token in ~/.pypirc:
cat > ~/.pypirc << 'EOF'
[pypi]
username = __token__
password = pypi-[your-token-here]
EOF
chmod 600 ~/.pypirc
```

---

### 2. Publish TypeScript SDK

```bash
cd clients/typescript

# Verify you're logged in
npm whoami

# Final build
npm run build

# Dry run to verify package contents
npm pack --dry-run

# Publish to npm (this is it!)
npm publish

# If using 2FA, you'll be prompted for OTP
```

**Expected output**:
```
+ @whitemagic/client@2.1.4
```

**Verify**: https://www.npmjs.com/package/@whitemagic/client

---

### 3. Publish Python SDK

```bash
cd clients/python

# Clean previous builds
rm -rf dist/ build/ *.egg-info

# Build distributions
python3 -m build

# Verify package contents
tar -tzf dist/whitemagic_client-2.1.4.tar.gz | head -20

# Upload to PyPI (this is it!)
python3 -m twine upload dist/*

# You may be prompted for OTP if 2FA is enabled
```

**Expected output**:
```
Uploading whitemagic_client-2.1.4-py3-none-any.whl
Uploading whitemagic_client-2.1.4.tar.gz
```

**Verify**: https://pypi.org/project/whitemagic-client/

---

### 4. Post-Publishing Verification

#### Test TypeScript Installation
```bash
# In a fresh directory
mkdir test-ts-sdk && cd test-ts-sdk
npm init -y
npm install @whitemagic/client

# Create test.js
cat > test.js << 'EOF'
import { WhiteMagicClient } from '@whitemagic/client';
console.log('✅ TypeScript SDK installed successfully!');
EOF

node test.js
```

#### Test Python Installation
```bash
# In a fresh virtualenv
python3 -m venv test-env
source test-env/bin/activate
pip install whitemagic-client

# Test import
python3 -c "from whitemagic_client import WhiteMagicClient; print('✅ Python SDK installed successfully!')"
```

---

### 5. Update Documentation

After successful publishing, update:

1. **README.md** - Change "(New in v2.1.4!)" to note packages are live
2. **docs/sdk/README.md** - Update status from "Ready" to "✅ Published"
3. **CHANGELOG.md** - Add entry for v2.1.4 SDK release

```bash
# Update SDK status in docs
sed -i 's/Status: ✅ Ready/Status: ✅ Published/g' docs/sdk/README.md

# Commit
git add -A
git commit -m "docs: mark SDKs as published"
git push origin v2.1.4-dev
```

---

## 🔄 Future Publishing (Updates)

### Versioning
When updating SDKs, sync versions:
1. Update `VERSION` file
2. Update `clients/typescript/package.json` version
3. Update `clients/python/pyproject.toml` version
4. Rebuild and republish both

### Automated Publishing (Future)
Set up GitHub Actions workflow:
```yaml
# .github/workflows/publish-sdks.yml
name: Publish SDKs
on:
  release:
    types: [published]
jobs:
  publish-npm:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
      - run: cd clients/typescript && npm publish
        env:
          NODE_AUTH_TOKEN: ${{ secrets.NPM_TOKEN }}
  
  publish-pypi:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
      - run: cd clients/python && python -m build && twine upload dist/*
        env:
          TWINE_USERNAME: __token__
          TWINE_PASSWORD: ${{ secrets.PYPI_TOKEN }}
```

---

## 🚨 Troubleshooting

### npm Publish Issues

**"403 Forbidden"**
- Check you're logged in: `npm whoami`
- Verify scope ownership: `@whitemagic` org must exist
- Alternative: Publish without scope as `whitemagic-client`

**"Package name too similar"**
- npm may flag similar names
- Contact support or use different name

**Fix: Publish without @scope**:
```bash
# Edit package.json
"name": "whitemagic-ts-client"

# Republish
npm publish
```

### PyPI Publish Issues

**"403 Forbidden"**
- Check token in ~/.pypirc
- Verify token hasn't expired
- Create new token if needed

**"Package name conflict"**
- Check if name exists: https://pypi.org/project/whitemagic-client/
- Use different name like `whitemagic-py-client`

**Fix: Use different name**:
```bash
# Edit pyproject.toml
name = "whitemagic-py-client"

# Rebuild and republish
python3 -m build
twine upload dist/*
```

---

## 📊 Success Metrics

After publishing, monitor:

### npm Stats
- https://www.npmjs.com/package/@whitemagic/client
- Downloads per week
- GitHub stars
- Issues opened

### PyPI Stats
- https://pypi.org/project/whitemagic-client/
- Downloads per day
- Versions
- Issues

### GitHub
- Watch Issue #2 for user feedback
- Monitor for SDK-related issues
- Check for installation problems

---

## 🎯 Next Steps After Publishing

1. ✅ Announce on social media
2. ✅ Update main README badges
3. ✅ Create example projects using SDKs
4. ✅ Write blog post about SDK release
5. ✅ Submit to package indexes/directories
6. ✅ Move on to MCP CLI Auto-Setup (Issue #1)

---

**Last Updated**: November 12, 2025  
**SDKs Version**: 2.1.4  
**Status**: Ready to publish 🚀
