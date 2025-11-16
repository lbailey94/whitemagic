# Version Update Checklist - v2.2.1

**Purpose**: Systematic version update from mixed versions → 2.2.1  
**Date**: November 15, 2025

---

## Files Requiring Version Updates (11 files)

### Main Folder

1. **CHANGELOG.md**
   - Action: ADD v2.2.1 entry
   - Features to document:
     * Graph visualization (relationships)
     * Caching improvements
     * Backup enhancements
     * Archive API endpoints
     * SDK headers compatibility
     * Dockerfile
   - Status: ⏸️ TODO

2. **INSTALL.md**
   - Current: v2.1.6
   - Update to: v2.2.1
   - Lines to change: Installation examples, version pins
   - Status: ⏸️ TODO

3. **README.md** 🔴 MAJOR
   - Current: v2.2.0
   - Update to: v2.2.1
   - Changes needed:
     * Version badges
     * Feature list (add v2.2.1 features)
     * Remove aspirational features (Stripe, hosted service)
     * Roadmap section (NO monetization until AFTER v2.3.0)
     * Test count (verify actual number)
   - Status: ⏸️ TODO - MAJOR REWRITE

4. **SECURITY.md**
   - Current: "2.1.x current"
   - Update to: "2.2.x current"
   - Version table needs refresh
   - Status: ⏸️ TODO

### docs/ Folder

5. **ARCHITECTURE.md**
   - Current: v2.2.0 (line 3)
   - Update to: v2.2.1
   - Last updated: November 15, 2025
   - Status: ⏸️ TODO

6. **CHEATSHEET.md**
   - Current: v2.2.0 (lines 11, 14, 523)
   - Update to: v2.2.1
   - Also note Whop integration as "future" not current (line 373)
   - Status: ⏸️ TODO

7. **DEPRECATION_POLICY.md**
   - Current: v2.1.1 (line 3, lines 24-25)
   - Update to: v2.2.1
   - Refresh version table (lines 118-122)
   - Status: ⏸️ TODO

8. **MCP_CLI_SETUP.md**
   - Current: v2.1.4 (line 339)
   - Update to: v2.2.1
   - Status: ⏸️ TODO

9. **TROUBLESHOOTING.md**
   - Current: v2.1.5 in examples
   - Update to: v2.2.1
   - Search for "2.1.5" and replace with "2.2.1"
   - Status: ⏸️ TODO

10. **USER_GUIDE.md**
    - Current: v2.1.5 throughout
    - Update to: v2.2.1
    - Lines 42, 47, 60 and others
    - Status: ⏸️ TODO

11. **TERMINAL_TOOL_DESIGN.md** (optional)
    - Status marked "Design Phase"
    - Action: Update status if implemented, or archive if obsolete
    - Status: ⏸️ TODO - VERIFY IMPLEMENTATION STATUS

---

## Version File

12. **VERSION**
    - Current: (need to check)
    - Update to: 2.2.1
    - Status: ⏸️ TODO

---

## Additional Files to Check

### Python Package
- `pyproject.toml` - version field
- `setup.py` - version field
- `whitemagic/__init__.py` - __version__ constant

### NPM Packages
- `whitemagic-mcp/package.json` - version field
- `clients/typescript/package.json` - version field

### Verification Script
- `verify_fixes.py` - Update version checks to 2.2.1

---

## Quick Reference: v2.2.1 Features

**New in v2.2.1** (to document in CHANGELOG/README):
1. Graph visualization for memory relationships
2. Semantic search caching (10-100x faster)
3. Enhanced backup system with verification
4. Archive API endpoints (list, restore, permanent delete)
5. SDK header compatibility (X-API-Key + Authorization)
6. Dockerfile for compose deployment
7. Optimized memory retrieval (tiered context, direct reads)

**Fixed in v2.2.1**:
1. SDK/API contract alignment (partial)
2. Archive operations via API
3. Docker compose configuration
4. Documentation version consistency

---

## Replacement Strategy

### Global Search & Replace
```bash
# In docs/ folder
grep -r "v2\.2\.0" docs/ --files-with-matches
grep -r "2\.1\.[0-9]" docs/ --files-with-matches

# Replace examples:
# v2.2.0 → v2.2.1
# 2.1.5 → 2.2.1
# 2.1.4 → 2.2.1
```

### Manual Updates Required
- README.md (feature list, roadmap)
- CHANGELOG.md (new entry)
- SECURITY.md (version table)
- DEPRECATION_POLICY.md (version history)

---

## Verification

**After updates**:
1. Run grep to find remaining old versions
2. Check VERSION file matches package.json/pyproject.toml
3. Run verify_fixes.py
4. Build test: `python3 -m build`
5. Verify all links in updated docs still work

---

**Status**: Ready for execution  
**Estimated time**: 1-2 hours for all updates  
**Priority**: Before v2.2.1 release
