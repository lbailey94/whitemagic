# v2.1.4 Shipping Checklist

**Release Date**: November 13, 2025  
**Version**: 2.1.4  
**Codename**: Developer Experience Edition

---

## ✅ Pre-Release Checklist

### Version Updates
- [x] VERSION file updated to 2.1.4
- [x] CHANGELOG.md updated with v2.1.4 entry
- [x] whitemagic-mcp/package.json → 2.1.4
- [x] clients/typescript/package.json → 2.1.4
- [x] clients/python/pyproject.toml → 2.1.4

### Code & Features
- [x] TypeScript SDK complete and tested
- [x] Python SDK complete and tested
- [x] MCP CLI complete and tested
- [x] All tests passing (223 tests)
- [x] Documentation complete

### Published Packages (Already Done!)
- [x] TypeScript SDK published to npm
- [x] Python SDK published to PyPI

### Documentation
- [x] RELEASE_NOTES_v2.1.4.md created
- [x] README.md updated with SDK showcase
- [x] docs/sdk/ documentation complete
- [x] docs/MCP_CLI_SETUP.md created
- [x] CHANGELOG.md updated

---

## 🚀 Release Steps

### 1. Final Commit & Tag
```bash
# Commit final changes
git add -A
git commit -m "release: v2.1.4 - Developer Experience Edition

Major features:
- Official TypeScript & Python SDKs (published)
- One-command MCP CLI setup
- 13x faster onboarding

Full changelog: CHANGELOG.md
Release notes: RELEASE_NOTES_v2.1.4.md"

# Tag the release
git tag -a v2.1.4 -m "v2.1.4 - Developer Experience Edition"

# Push to main and dev branches
git push origin v2.1.4-dev
git checkout main
git merge v2.1.4-dev
git push origin main
git push origin v2.1.4
```

### 2. Publish whitemagic-mcp to npm
```bash
cd whitemagic-mcp
npm run build
npm publish
```

### 3. Create GitHub Release
1. Go to: https://github.com/lbailey94/whitemagic/releases/new
2. Tag: `v2.1.4`
3. Title: `v2.1.4 - Developer Experience Edition`
4. Description: Copy from `RELEASE_NOTES_v2.1.4.md`
5. Attach: None needed (packages on npm/PyPI)
6. Mark as latest release ✅
7. Publish!

### 4. Verify Published Packages
```bash
# Check npm
npm view whitemagic-client version
npm view whitemagic-mcp version

# Check PyPI
pip index versions whitemagic-client

# Test installations
npm install whitemagic-client
pip install whitemagic-client
npx whitemagic-mcp-setup
```

---

## 📢 Announcement Checklist

### Social Media
- [ ] Twitter/X announcement
- [ ] LinkedIn post
- [ ] Reddit r/programming (if allowed)
- [ ] Hacker News "Show HN" (optional)

### Developer Communities
- [ ] MCP Discord/Community
- [ ] Dev.to article (optional)
- [ ] Medium post (optional)

### Documentation Updates
- [ ] Update website (whitemagic.dev) if exists
- [ ] Update any external documentation
- [ ] Announce in GitHub Discussions

---

## 📋 Post-Release Checklist

### Monitoring
- [ ] Watch npm download stats
- [ ] Watch PyPI download stats
- [ ] Monitor GitHub issues for bugs
- [ ] Check social media feedback

### Follow-up
- [ ] Respond to issues within 24h
- [ ] Document any problems in GitHub
- [ ] Plan v2.2.1 based on feedback

---

## 🎯 Success Metrics

### Downloads (1 week)
- Target: 100+ npm downloads
- Target: 50+ PyPI downloads
- Target: 10+ GitHub stars

### Feedback
- Target: < 5 bug reports
- Target: Positive feedback on ease of use
- Target: At least 1 success story

---

## 🔄 Rollback Plan

If critical issues found:

1. **Immediately**: Document the issue
2. **Quick fix possible?** 
   - Yes → Patch release (v2.2.1)
   - No → Deprecate v2.1.4, advise v2.1.3
3. **Update documentation** with workarounds
4. **Communicate** via GitHub release notes

---

## 📝 Sample Announcement

### Twitter/X
```
🎉 WhiteMagic v2.1.4 is here!

New:
✅ Official TypeScript & Python SDKs
✅ One-command IDE setup (npx whitemagic-mcp-setup)
✅ 13x faster onboarding

Get started in < 3 minutes instead of 30+

📦 npm install whitemagic-client
📦 pip install whitemagic-client

Docs: https://github.com/lbailey94/whitemagic

#AI #DevTools #Memory
```

### GitHub Release Description
```markdown
# v2.1.4 - Developer Experience Edition

Making WhiteMagic 10x easier to use! 🚀

## 🎉 What's New

### Official SDKs
- **TypeScript/JavaScript**: `npm install whitemagic-client`
- **Python**: `pip install whitemagic-client`

Full type safety, auto-retry, error handling - all built-in.

### One-Command IDE Setup
```bash
npx whitemagic-mcp-setup
```

Auto-configures Cursor, Windsurf, Claude Desktop, or VS Code in < 2 minutes.

## 📈 Impact
- **13x faster onboarding** (from 40 min → 3 min)
- **7x simpler code** (3 lines instead of 20+)
- **Professional DX** on par with major APIs

## 📚 Documentation
- [TypeScript SDK](docs/sdk/typescript.md)
- [Python SDK](docs/sdk/python.md)
- [MCP CLI Setup](docs/MCP_CLI_SETUP.md)
- [Full Release Notes](RELEASE_NOTES_v2.1.4.md)

## 🔗 Links
- npm: https://www.npmjs.com/package/whitemagic-client
- PyPI: https://pypi.org/project/whitemagic-client/
- Changelog: [CHANGELOG.md](CHANGELOG.md)

No breaking changes - all v2.1.3 functionality preserved!
```

---

## ✅ Ready to Ship!

All checks passed. Version 2.1.4 is ready for release!

**Estimated time**: 30 minutes
**Risk level**: Low (no breaking changes)
**Impact**: High (major UX improvement)

---

**Prepared by**: Development Team  
**Date**: November 12-13, 2025  
**Status**: 🟢 Ready to Ship
