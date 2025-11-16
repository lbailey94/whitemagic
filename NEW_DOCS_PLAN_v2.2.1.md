# New Documentation Plan - v2.2.1

**Purpose**: Document what new docs are needed for v2.2.1 release  
**Date**: November 15, 2025

---

## Priority 1: Release Documentation

### 1. RELEASE_NOTES_v2.2.1.md
**Location**: Root folder (then archive after next release)

**Sections needed**:
- Release date
- Version number (2.2.1)
- Overview (incremental feature release)
- New features (graph viz, caching, backups, archive API, Dockerfile)
- Bug fixes (SDK compat, docker compose)
- Breaking changes (none)
- Migration guide (none needed - backwards compatible)
- Known issues (reference INDEPENDENT_REVIEW for v2.3.0 items)
- Upgrade instructions

**Status**: ⏸️ TODO

---

### 2. Update CHANGELOG.md with v2.2.1 Entry
**Location**: Root folder

**Entry format**:
```markdown
## [2.2.1] - 2025-11-XX

### Added
- Graph visualization for memory relationships (CLI: `whitemagic graph`)
- Semantic search caching (10-100x performance improvement)
- Enhanced backup verification (SHA256 hashes)
- Archive API endpoints: list, restore, permanent delete
- SDK header compatibility (X-API-Key + Authorization)
- Dockerfile for docker-compose deployment
- Optimized memory retrieval (tiered context, direct file reads)
- WhiteMagic MCP integration for session optimization

### Fixed
- Docker compose configuration (missing Dockerfile)
- Archive operations now accessible via API
- SDK authentication header compatibility
- Version consistency across documentation

### Changed
- Documentation reorganization (26 files archived)
- Improved token efficiency in memory operations

### Documentation
- Created comprehensive documentation audit
- Archived historical plans and aspirational docs
- Organized archive structure by version and category

[2.2.1]: https://github.com/lbailey94/whitemagic/compare/v2.2.0...v2.2.1
```

**Status**: ⏸️ TODO

---

## Priority 2: User-Facing Documentation

### 3. Simple PRIVACY.md (Local Tool)
**Location**: Root folder

**Purpose**: Replace aspirational SaaS privacy policy with reality

**Content**:
- WhiteMagic is a LOCAL tool
- All data stored on YOUR filesystem
- No cloud sync (currently)
- No data collection by default
- Optional: OpenAI API for embeddings (user's own key)
- Optional: API server (self-hosted only)
- No third-party data sharing
- Git-friendly markdown files (YOU control versioning)

**Length**: Short, clear, honest (~50 lines max)

**Status**: ⏸️ TODO

---

### 4. Simple TERMS.md (Local Tool)
**Location**: Root folder

**Purpose**: Replace aspirational SaaS terms with reality

**Content**:
- Open source software (check LICENSE)
- MIT License applies
- No warranty (as-is)
- Local use only (current version)
- No account/subscription (current version)
- Community support via GitHub issues
- Contributions welcome (see CONTRIBUTING.md)

**Length**: Short, clear (~50 lines max)

**Status**: ⏸️ TODO

---

## Priority 3: Roadmap Documentation

### 5. ROADMAP.md (v2.2.2 → v2.3.0)
**Location**: Root folder

**Purpose**: Clear, realistic roadmap aligned with user directive

**Sections**:

#### Current State (v2.2.1)
- What's working now
- What's production-ready
- What's experimental

#### Short Term: v2.2.2 (Bugfix Release)
**Timeline**: 1-2 weeks  
**Focus**: Polish and fixes from INDEPENDENT_REVIEW
- Complete SDK realignment
- Dashboard login fix or removal
- Documentation accuracy pass
- Test coverage improvements

#### Medium Term: v2.3.0 (Feature Release)
**Timeline**: 4-6 weeks  
**Focus**: Complete features, prepare for growth
- All features from v2.2.1_PLAN.md
- Full SDK/API parity
- Enhanced testing
- Performance optimizations
- **NO MONETIZATION** (deferred to v2.4.0+)

#### Long Term: v2.4.0+ (Monetization Release)
**Timeline**: Q1 2026  
**Focus**: Cloud sync, team features, optional paid tiers
- Cloud sync (optional)
- Team workspaces
- Dashboard
- Stripe integration
- Hosted service option
- **Only after 1,000+ active local users**

#### Principles
- Local-first always
- No breaking changes without major version bump
- Backwards compatibility paramount
- User privacy and control first
- Monetization helps sustainability, not required

**Status**: ⏸️ TODO

---

## Priority 4: Technical Documentation

### 6. Update ARCHITECTURE.md (if needed)
**Location**: docs/

**Check if tmp_memory_architecture.md content should be merged**

**Current tmp_memory_architecture.md shows**:
- v2.1.5 content (outdated)
- Good architecture overview
- May have useful diagrams

**Action**: 
1. Compare tmp_memory_architecture.md with docs/ARCHITECTURE.md
2. If tmp has newer/better content, merge it
3. If docs/ARCHITECTURE.md is better, delete tmp (now archived)
4. Update to v2.2.1 in either case

**Status**: ⏸️ TODO - needs comparison

---

### 7. GRAPH_VISUALIZATION.md (Feature Doc)
**Location**: docs/

**Purpose**: Document new graph visualization feature

**Content**:
- What it does (visualize memory relationships)
- How to use it (`whitemagic graph <memory>`)
- Flags: `--depth N`, `--format mermaid`
- Example output (ASCII tree)
- Use cases (understanding memory structure)
- API endpoint (if exists)

**Status**: ⏸️ TODO - depends on feature implementation

---

### 8. CACHING.md (Technical Doc)
**Location**: docs/

**Purpose**: Document semantic search caching

**Content**:
- How caching works (file-based, hash + mtime)
- Cache location (`.whitemagic/cache/embeddings/`)
- Cache key format
- Invalidation strategy
- Performance gains (benchmarks)
- How to rebuild cache (`--rebuild-cache`)
- How to clear cache

**Status**: ⏸️ TODO - depends on feature implementation

---

## Priority 5: Archive Documentation

### 9. ARCHIVE_GUIDE.md
**Location**: docs/

**Purpose**: Explain new archive system

**Content**:
- What the archive is
- When to use vs delete
- Archive structure (by version, by category)
- How to find archived docs
- When archived docs are still relevant
- How to restore if needed

**Status**: ⏸️ TODO

---

## Optional Documentation

### 10. DOCUMENTATION_STANDARDS.md
**Location**: docs/development/

**Purpose**: Prevent future documentation debt

**Content**:
- Version references policy
- When to archive vs update
- Archive organization structure
- Documentation review process
- Checklist for new releases

**Status**: ⏸️ OPTIONAL

---

### 11. MEMORY_OPTIMIZATION_GUIDE.md
**Location**: docs/

**Purpose**: Document WhiteMagic's own optimization techniques

**Content**:
- Tiered context (Tier 0/1/2)
- Direct file reads vs MCP tools
- Targeted grep search
- Session continuity patterns
- Token budget management
- Resume protocols

**Status**: ⏸️ OPTIONAL - could be valuable reference

---

## Files to Verify/Update

### Existing Documentation Health Check

1. **README.md** - Needs feature list update, roadmap cleanup
2. **INSTALL.md** - Verify all instructions current
3. **CONTRIBUTING.md** - Already current ✅
4. **SECURITY.md** - Version table needs update
5. **INDEX.md** - Verify all links after archiving
6. **tmp_memory_architecture.md** - Archived, may need content merge

---

## Execution Priority

**Immediate (before v2.2.1 release)**:
1. RELEASE_NOTES_v2.2.1.md
2. CHANGELOG.md entry
3. PRIVACY.md (simple version)
4. TERMS.md (simple version)
5. ROADMAP.md

**Short term (with v2.2.1 features)**:
6. GRAPH_VISUALIZATION.md (if feature complete)
7. CACHING.md (if feature complete)

**Medium term (ongoing)**:
8. ARCHIVE_GUIDE.md
9. Update ARCHITECTURE.md
10. MEMORY_OPTIMIZATION_GUIDE.md (optional)
11. DOCUMENTATION_STANDARDS.md (optional)

---

## Estimated Work

**Token cost for creation**:
- Priority 1-2 docs: ~15-20K tokens
- Priority 3 docs: ~5-10K tokens
- Priority 4-5 docs: ~10-15K tokens
- **Total**: 30-45K tokens to create all

**Time estimate**:
- Priority 1-2: 2-3 hours
- Priority 3: 1-2 hours
- Priority 4-5: 2-3 hours
- **Total**: 5-8 hours for complete documentation

---

**Status**: Plan complete, ready for execution  
**Created**: November 15, 2025  
**Next**: Execute priority 1-2 docs before v2.2.1 release
