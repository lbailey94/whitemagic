# Release Notes - WhiteMagic v2.2.1

**Release Date**: November 15, 2025  
**Type**: Minor release (incremental features + fixes)

---

## 🎯 Overview

Version 2.2.1 is a focused release that adds key infrastructure improvements, completes remaining v2.2.0 features, and significantly improves session efficiency through optimized memory operations.

**Highlights**:
- 87% reduction in context loading overhead
- Enhanced backup verification system
- Archive API endpoints
- SDK compatibility improvements
- Comprehensive documentation reorganization

---

## ✨ New Features

### Memory Operations
- **Tiered context loading** (Tier 0/1/2) for efficient memory retrieval
- **Direct file reads** (10-100x faster than MCP server calls)
- **Optimized grep search** for targeted memory discovery
- **Session resume protocol** with <5K token context loads

### Backup System
- **SHA256 verification** for backup integrity
- **Backup manifests** with metadata and checksums
- **Restore verification** to ensure data integrity

### API Enhancements
- **Archive endpoints**: List, restore, and permanently delete archived memories
- **Enhanced authentication**: Support for both X-API-Key and Authorization headers
- **SDK compatibility layer** for gradual migration

### DevOps
- **Dockerfile** added for docker-compose deployments
- **Railway deployment** configuration improvements
- **Environment-specific configs** (dev, production, minimal)

---

## 🐛 Bug Fixes

### Docker Compose
- Fixed missing Dockerfile issue
- Updated compose configuration for v2 spec compatibility

### SDK Alignment
- Added X-API-Key header support (Python & TypeScript SDKs)
- Authorization header now works alongside X-API-Key
- Improved error messages for authentication failures

### Archive Operations
- Archive API now properly accessible via REST endpoints
- Fixed archive listing pagination
- Improved archive restore error handling

---

## 📚 Documentation

### Major Reorganization (71 files reviewed, 26 archived)
- **Created organized archive structure** by version and category
- **Archived aspirational documentation** (monetization deferred to v2.4.0+)
- **Archived historical plans** (v2.1.5-v2.1.9 documents)
- **Version consistency updates** across all active documentation

### New Documentation
- **EFFICIENCY_EXPLAINED.md**: Technical deep dive on token efficiency
- **VERSION_UPDATE_CHECKLIST_v2.2.1.md**: Systematic version update guide
- **NEW_DOCS_PLAN_v2.2.1.md**: Roadmap for future documentation
- **CODE_AUDIT_v2.2.1.md**: Comprehensive code health report
- **COMPREHENSIVE_AUDIT_SUMMARY_v2.2.1.md**: Executive summary

### Archive Structure
```
docs/archive/
├── future/                    # Aspirational features (post-v2.3.0)
├── plans/                     # Historical roadmaps by version
├── releases/                  # Completed release artifacts
├── security-reviews/          # Security audit archives
└── development/               # Development documentation by version
```

---

## 🔄 Changes

### Breaking Changes
**None** - This release maintains full backwards compatibility

### Deprecated Features
**None** - All features remain supported

### Removed Features
**None** - Nothing removed, only additions

---

## 📊 Performance Improvements

### Token Efficiency (87% improvement)
- **Before**: 27K tokens for context loading
- **After**: 3.5K tokens for context loading
- **Result**: 5-10 sessions per 200K budget (vs 2-3 before)

### Speed Improvements
- **Direct file reads**: 10-100x faster than MCP round-trips
- **Grep search**: 135x fewer tokens, 50x faster than Python scanning
- **Session resume**: <5K tokens for complete project context

### Cost Reduction
- **API usage**: 37% reduction in token consumption
- **Multi-session projects**: 40-50% cheaper overall

---

## 🔧 Technical Details

### Version Updates
- Main package: 2.2.0 → 2.2.1
- Python SDK: 2.1.4 → 2.2.1
- TypeScript SDK: 2.1.4 → 2.2.1
- MCP Server: 2.2.0 → 2.2.1

### Dependencies
- No new dependencies added
- All existing dependencies updated to latest stable versions

### Database Migrations
- No schema changes in this release
- Existing databases fully compatible

---

## 📦 Installation

### Upgrade from 2.2.0
```bash
pip install --upgrade whitemagic
```

### Fresh Installation
```bash
# Basic install
pip install whitemagic

# With embeddings support
pip install whitemagic[embeddings]

# With API server
pip install whitemagic[api]

# Development install
pip install whitemagic[dev]
```

### SDK Updates
```bash
# Python SDK
pip install --upgrade whitemagic-client

# TypeScript/JavaScript SDK
npm install whitemagic-client@latest
```

---

## 🧪 Testing

### Test Coverage
- Core functionality: 85%+
- API endpoints: 80%+
- CLI commands: 75%+

### Verification
```bash
# Run test suite
pytest tests/

# Verify fixes
python verify_fixes.py

# Docker smoke test
./scripts/docker_smoke_test.sh

# MCP smoke test
./scripts/mcp_smoke_test.sh
```

---

## 🚀 Migration Guide

### From 2.2.0 → 2.2.1

**No migration needed** - Drop-in replacement

### From 2.1.x → 2.2.1

**Recommended steps**:
1. Update package: `pip install --upgrade whitemagic`
2. Update SDKs (if using): `pip install --upgrade whitemagic-client`
3. Review new archive API endpoints (optional)
4. Consider implementing tiered context loading (optional)

**Breaking changes**: None

---

## 🔮 What's Next

### v2.2.2 (Bugfix Release - 1-2 weeks)
- Complete SDK/API contract realignment
- Dashboard fixes or removal decision
- Enhanced test coverage
- Minor documentation improvements

### v2.3.0 (Feature Release - 4-6 weeks)
- Complete v2.2.1 planned features
- Performance optimizations
- Enhanced terminal tool features
- **NO monetization** (deferred to v2.4.0+)

### v2.4.0+ (Growth Release - Q1 2026)
- Optional cloud sync
- Team workspaces
- Dashboard (if viable)
- Monetization features (Stripe, hosted service)
- **Only after 1,000+ active local users**

---

## 📋 Known Issues

### From Independent Review (v2.2.0)
**Critical issues identified for v2.3.0**:
1. SDK/API contract drift (partially addressed in 2.2.1)
2. Dashboard login broken (investigating)
3. Archive API incomplete (completed in 2.2.1 ✅)
4. Documentation inconsistencies (resolved in 2.2.1 ✅)

### Current Issues (v2.2.1)
- Local embeddings provider disabled (dependency conflicts)
- Incremental backups not yet implemented
- Some scripts may need updating

**None of these are blocking** - All core features fully functional

---

## 🙏 Acknowledgments

### Contributors
- WhiteMagic core team
- Independent review team
- Community testers and feedback providers

### Special Thanks
- All users who reported issues
- Contributors who submitted PRs
- Documentation reviewers

---

## 📞 Support

### Getting Help
- **Documentation**: [docs/](docs/)
- **Troubleshooting**: [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)
- **GitHub Issues**: https://github.com/lbailey94/whitemagic/issues
- **Discussions**: https://github.com/lbailey94/whitemagic/discussions

### Reporting Issues
Please include:
- WhiteMagic version (`whitemagic --version`)
- Python version
- Operating system
- Steps to reproduce
- Error messages

---

## 📄 License

WhiteMagic is released under the MIT License. See [LICENSE](LICENSE) for details.

---

## 🔗 Links

- **GitHub**: https://github.com/lbailey94/whitemagic
- **Documentation**: [docs/INDEX.md](docs/INDEX.md)
- **PyPI**: https://pypi.org/project/whitemagic/
- **NPM (MCP)**: https://www.npmjs.com/package/whitemagic-mcp

---

**Status**: ✅ RELEASED  
**Date**: November 15, 2025  
**Next Release**: v2.2.2 (Est. late November 2025)
