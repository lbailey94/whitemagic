# Automated Housekeeping System Design

**Date**: November 17, 2025  
**Version**: 1.0  
**Status**: Design Proposal  
**Goal**: Self-organizing, self-updating WhiteMagic project

---

## 🎯 Core Principle

**"WhiteMagic should maintain itself using WhiteMagic"**

Every checkpoint, every session end, every version release should trigger automated housekeeping that keeps the project organized, current, and consistent.

---

## 🏗️ System Architecture

### Three Layers of Automation

```
┌─────────────────────────────────────────────┐
│  Layer 1: Session-Level Housekeeping        │
│  (Every checkpoint, 5-10 times per session) │
└─────────────────────────────────────────────┘
           ↓
┌─────────────────────────────────────────────┐
│  Layer 2: Version-Level Housekeeping        │
│  (Every release, 1-2 times per week)        │
└─────────────────────────────────────────────┘
           ↓
┌─────────────────────────────────────────────┐
│  Layer 3: Project-Level Housekeeping        │
│  (Weekly/monthly deep cleaning)             │
└─────────────────────────────────────────────┘
```

---

## 📋 Layer 1: Session-Level Housekeeping

**Trigger**: Every session checkpoint (or manual `whitemagic checkpoint`)

**Actions**:

### 1. Memory Consolidation Check
```bash
# Check if consolidation needed
whitemagic stats --format json | jq '.short_term_count'
# If > 40, suggest consolidation
# If > 50, auto-consolidate with user confirmation
```

**Rules**:
- Short-term > 40 files → Suggest consolidation
- Short-term > 50 files → Auto-consolidate (with --force flag)
- Look for duplicate/similar memories (by title similarity)
- Merge "v2.2.x complete" memories into single timeline

### 2. Timestamp Verification
```bash
# Check memory timestamps are valid
find memory/ -name "*.md" -exec grep -H "^created:" {} \; | \
  awk -F: '{if ($3 < "2025-01-01") print $1}'
```

**Rules**:
- All memories should have valid ISO 8601 timestamps
- Flag memories with missing/invalid timestamps
- Auto-fix if possible (use file mtime)

### 3. Tag Normalization
```bash
whitemagic normalize-tags --dry-run
# Then apply if needed
```

**Rules**:
- Convert CamelCase → snake_case
- Remove duplicate tags
- Suggest common typos (2.6.5 vs v2_2_7)

### 4. Scratchpad Cleanup
```bash
# Finalize old scratchpads
whitemagic pad-list | grep "older than 24 hours" | \
  xargs -I {} whitemagic pad-close {}
```

**Rules**:
- Scratchpads older than 24 hours → Finalize or delete
- Abandoned scratchpads → Prompt user

### 5. Metrics Collection
```bash
whitemagic metrics-track --category housekeeping \
  --metric session_checkpoint --value 1
```

**Output**:
```
✓ Session Housekeeping Complete
  - Memories: 38 short-term, 37 long-term (OK)
  - Tags: 251 unique, 5 normalized
  - Scratchpads: 1 active, 2 finalized
  - Next: Consolidate in 2 more checkpoints
```

---

## 📦 Layer 2: Version-Level Housekeeping

**Trigger**: Every version release (`whitemagic version X.Y.Z`)

**Actions**:

### 1. Version Synchronization
```bash
#!/bin/bash
# Auto-run during version bump

VERSION=$1

# Update all version files
echo "$VERSION" > VERSION
sed -i "s/version = \".*\"/version = \"$VERSION\"/" pyproject.toml
sed -i "s/\"version\": \".*\"/\"version\": \"$VERSION\"/" package.json
sed -i "s/\"version\": \".*\"/\"version\": \"$VERSION\"/" clients/*/package.json

# Update documentation
sed -i "s/Version.*: .*/Version: $VERSION/" docs/ARCHITECTURE.md
sed -i "s/Current Version.*: .*/Current Version: $VERSION/" ROADMAP.md
sed -i "s/version-[0-9.]*/version-$VERSION/" README.md

# Update module __version__
find whitemagic/ -name "__init__.py" -exec \
  sed -i "s/__version__ = \".*\"/__version__ = \"$VERSION\"/" {} \;

# Run docs-check
whitemagic docs-check --fix --version $VERSION

echo "✓ Version synchronized to $VERSION across all files"
```

### 2. Documentation Drift Detection
```bash
whitemagic docs-check --report
```

**Output**:
```
Documentation Drift Report
==========================
Version References:
  ✓ README.md: 2.6.5
  ✓ ROADMAP.md: 2.6.5
  ✓ ARCHITECTURE.md: 2.6.5
  ⚠ 3 guides reference 2.6.5 → Updated

Outdated Sections:
  ⚠ docs/guides/QUICKSTART.md mentions removed feature
  ⚠ docs/OVERVIEW.md has 2.6.5 example
  → Run: whitemagic docs-check --fix
```

### 3. File Organization
```bash
#!/bin/bash
# Move misplaced files

# Planning docs to private/
mv V2.2.8_COMPLETE_PLAN.md private/plans/
mv v2.2.9_QUALITY_RELEASE_PLAN.md private/plans/

# Release notes to docs/releases/
mv RELEASE_FIXES_v2.2.8.md docs/releases/

# Checklists to private/
mv SHIPPING_CHECKLIST_v2.2.7.md private/checklists/

# Production notes to docs/production/
mv RAILWAY_FIX_NOTES.md docs/production/

echo "✓ Files organized into proper directories"
```

### 4. CHANGELOG Update
```bash
#!/bin/bash
# Auto-generate CHANGELOG entry

VERSION=$1
DATE=$(date +%Y-%m-%d)

# Get commits since last tag
git log $(git describe --tags --abbrev=0)..HEAD \
  --pretty=format:"- %s" > /tmp/changelog_new.txt

# Prepend to CHANGELOG.md
{
  echo "## [$VERSION] - $DATE"
  echo ""
  cat /tmp/changelog_new.txt
  echo ""
  echo "---"
  echo ""
  cat CHANGELOG.md
} > CHANGELOG.md.new

mv CHANGELOG.md.new CHANGELOG.md

echo "✓ CHANGELOG.md updated for v$VERSION"
```

### 5. Memory Archival
```bash
# Archive old version memories
whitemagic search --query "2.6.5 OR 2.6.5" --type short_term | \
  xargs -I {} whitemagic update {} --archive

echo "✓ Archived memories for old versions"
```

### 6. Release Checklist Verification
```bash
#!/bin/bash
# Verify release checklist

echo "Pre-Release Checklist:"
echo "======================"

# Version consistency
echo -n "Version sync: "
if whitemagic audit --quiet | grep -q "Version.*OK"; then
  echo "✓"
else
  echo "✗ FAILED"
  exit 1
fi

# Tests passing
echo -n "Tests: "
if pytest --quiet; then
  echo "✓"
else
  echo "✗ FAILED"
  exit 1
fi

# Import resolution
echo -n "Imports: "
python3 -c "import whitemagic; from whitemagic.api import app" && echo "✓" || echo "✗ FAILED"

# CLI commands
echo -n "CLI: "
whitemagic audit --version >/dev/null && echo "✓" || echo "✗ FAILED"

# Documentation
echo -n "Docs: "
whitemagic docs-check --quiet && echo "✓" || echo "✗ FAILED"

echo ""
echo "✓ Release checklist complete"
```

---

## 🌍 Layer 3: Project-Level Housekeeping

**Trigger**: Weekly or monthly (cron job or manual)

**Actions**:

### 1. Deep Memory Consolidation
```bash
#!/bin/bash
# Intelligent memory consolidation

# Find similar memories
whitemagic search --semantic --query "session complete" | \
  head -20 > /tmp/similar_memories.txt

# Suggest merges
echo "Consolidation Candidates:"
cat /tmp/similar_memories.txt | \
  awk '{print "  - Merge:", $0}'

# Auto-consolidate with AI
if [ "$AUTO_CONSOLIDATE" = "true" ]; then
  whitemagic exec "Consolidate these memories: $(cat /tmp/similar_memories.txt)"
fi
```

**Rules**:
- Sessions with same date → Merge
- "Complete" memories for same version → Merge
- Duplicate content (>80% similarity) → Merge
- Keep most recent, archive others

### 2. Documentation Reorganization
```bash
#!/bin/bash
# Ensure docs follow structure

# Create missing directories
mkdir -p docs/guides/{getting_started,core_concepts,advanced,integrations,automation}
mkdir -p docs/philosophy
mkdir -p docs/production
mkdir -p docs/releases
mkdir -p private/{plans,checklists,sessions}

# Move files to correct locations
# (Based on AUTOMATED_HOUSEKEEPING_DESIGN.md structure)

# Generate missing docs
if [ ! -f "docs/guides/TYPED_MEMORIES.md" ]; then
  echo "⚠️  Missing: docs/guides/TYPED_MEMORIES.md"
  echo "   Run: whitemagic exec 'Create TYPED_MEMORIES.md guide'"
fi

# Check for duplicates
find docs/ -name "*.md" -exec basename {} \; | \
  sort | uniq -d | \
  while read dup; do
    echo "⚠️  Duplicate: $dup"
    find docs/ -name "$dup"
  done
```

### 3. Dependency Updates
```bash
#!/bin/bash
# Check for outdated dependencies

# Python
pip list --outdated | grep -E "(security|critical)" && \
  echo "⚠️  Security updates available"

# npm
npm outdated | grep -E "(security|high)" && \
  echo "⚠️  Security updates available"

# Generate update PR if needed
if [ "$AUTO_UPDATE" = "true" ]; then
  whitemagic exec "Update dependencies and test"
fi
```

### 4. Code Quality Scan
```bash
#!/bin/bash
# Automated code quality checks

# Dead code detection
vulture whitemagic/ --min-confidence 80

# Complexity analysis
radon cc whitemagic/ -a -nb

# Security scan
bandit -r whitemagic/ -f json > security_report.json

# Type coverage
mypy whitemagic/ --html-report /tmp/mypy_report

echo "✓ Code quality scan complete"
```

### 5. Roadmap Sync with Vision
```bash
#!/bin/bash
# Ensure ROADMAP reflects vision

# Extract vision features
grep -E "^- ❌|^1\. ❌" COMPREHENSIVE_AUDIT_FINDINGS_NOV_17_2025.md | \
  sed 's/.*❌ //' > /tmp/vision_missing.txt

# Check if in roadmap
while read feature; do
  if ! grep -qi "$feature" ROADMAP.md; then
    echo "⚠️  Missing from ROADMAP: $feature"
  fi
done < /tmp/vision_missing.txt

# Suggest additions
echo ""
echo "Run: whitemagic exec 'Update ROADMAP.md with missing vision features'"
```

### 6. Backup Creation
```bash
#!/bin/bash
# Create weekly backup

DATE=$(date +%Y%m%d)
BACKUP_FILE="backups/backup_${DATE}.tar.gz"

# Create backup
whitemagic backup --output $BACKUP_FILE

# Verify backup
whitemagic verify-backup $BACKUP_FILE

# Cleanup old backups (keep last 4 weeks)
find backups/ -name "backup_*.tar.gz" -mtime +28 -delete

echo "✓ Backup created: $BACKUP_FILE"
```

---

## 🤖 Implementation Plan

### Phase 1: Core Scripts (2.6.5)

**Create**:
1. `scripts/housekeeping/session_checkpoint.sh`
2. `scripts/housekeeping/version_sync.sh`
3. `scripts/housekeeping/docs_organize.sh`

**Test**:
- Run manually first
- Verify output
- Add to git hooks

### Phase 2: Automation Integration (2.6.5)

**Add to**:
1. `.git/hooks/pre-commit` → Session checkpoint
2. `.git/hooks/post-merge` → Check for drift
3. `scripts/release.sh` → Version-level housekeeping
4. GitHub Actions → Weekly housekeeping

### Phase 3: AI-Powered Housekeeping (2.6.5+)

**Features**:
1. AI detects when consolidation needed
2. AI suggests file reorganization
3. AI generates missing documentation
4. AI reviews and updates roadmap

---

## 🔧 CLI Commands

### New Commands to Add

```bash
# Session housekeeping
whitemagic housekeep --level session
whitemagic checkpoint --with-housekeeping

# Version housekeeping
whitemagic housekeep --level version --version 2.6.5
whitemagic release 2.6.5  # Includes version housekeeping

# Project housekeeping
whitemagic housekeep --level project --deep
whitemagic organize --dry-run  # Show what would be reorganized

# Specific tasks
whitemagic consolidate-memories --auto
whitemagic sync-versions 2.6.5
whitemagic organize-docs --dry-run
whitemagic check-vision-gaps
```

### Examples

```bash
# At end of session
$ whitemagic checkpoint --with-housekeeping
✓ Session checkpoint created
✓ Housekeeping complete:
  - 38 short-term memories (OK, suggest consolidate in 2 checkpoints)
  - 5 tags normalized
  - 1 scratchpad finalized
  - Metrics recorded

# Before release
$ whitemagic release 2.6.5
✓ Version synced to 2.6.5 across all files
✓ Documentation drift fixed (3 files updated)
✓ CHANGELOG.md updated
✓ Old version memories archived
✓ Release checklist passed
✓ Ready to ship!

# Weekly maintenance
$ whitemagic housekeep --level project --deep
✓ 5 memories consolidated
✓ 12 files reorganized
✓ Dependencies checked (2 security updates available)
✓ Roadmap synced with vision
✓ Backup created: backups/backup_20251117.tar.gz
```

---

## 📊 Metrics to Track

### Housekeeping Effectiveness

```python
# Track in metrics.jsonl
{
  "category": "housekeeping",
  "metric": "session_checkpoint",
  "value": 1,
  "context": {
    "memories_before": 42,
    "memories_after": 38,
    "tags_normalized": 5,
    "scratchpads_finalized": 1,
    "duration_seconds": 12
  }
}

{
  "category": "housekeeping",
  "metric": "version_sync",
  "value": 1,
  "context": {
    "version": "2.6.5",
    "files_updated": 15,
    "docs_fixed": 3,
    "duration_seconds": 45
  }
}

{
  "category": "housekeeping",
  "metric": "project_cleanup",
  "value": 1,
  "context": {
    "memories_consolidated": 5,
    "files_reorganized": 12,
    "docs_generated": 2,
    "duration_seconds": 180
  }
}
```

### Success Metrics

- **Memory count stability**: Short-term stays 30-40
- **Version drift**: Zero files with wrong version
- **Documentation coverage**: 95%+
- **Roadmap alignment**: 90%+ vision features tracked
- **Organization score**: 95%+ files in correct location

---

## 🎯 Rules & Heuristics

### Memory Consolidation

**Merge if**:
- Same date + same version + similar title (>70% similarity)
- Both tagged "session-complete" and <24h apart
- Content is duplicate (>80% similarity)
- One is clearly superseded by the other

**Keep separate if**:
- Different perspectives (different AI agents)
- Different phases (yin vs yang)
- Strategic vs tactical
- Problem vs solution

### File Organization

**Root directory** (keep 7 files only):
- README.md
- ROADMAP.md
- CHANGELOG.md
- INSTALL.md
- CONTRIBUTING.md
- SECURITY.md
- LICENSE

**Move to private/**:
- Planning docs (V2.X.X_PLAN.md)
- Checklists (SHIPPING_CHECKLIST_*.md)
- Session notes
- Analysis docs

**Move to docs/**:
- User-facing guides
- Philosophy docs
- Production guides
- Release notes

### Version Sync

**Always update**:
- VERSION file (source of truth)
- pyproject.toml
- package.json files
- README.md badges
- ROADMAP.md header
- ARCHITECTURE.md header
- Module __version__ attributes

**Check and fix**:
- All docs/ markdown files
- All guides
- Release notes
- Examples

---

## 🚀 Quick Reference

### At Every Checkpoint

```bash
whitemagic checkpoint --with-housekeeping
```

### At Every Release

```bash
whitemagic release 2.2.X
# Or manually:
whitemagic version 2.2.X
scripts/housekeeping/version_sync.sh 2.2.X
whitemagic docs-check --fix
whitemagic audit
```

### Weekly Maintenance

```bash
whitemagic housekeep --level project
# Or manually:
scripts/housekeeping/deep_cleanup.sh
whitemagic consolidate-memories --auto
whitemagic organize-docs
whitemagic backup
```

---

## 💡 Future Enhancements

### 2.6.5: AI-Powered Housekeeping

- AI detects consolidation opportunities
- AI generates missing documentation
- AI suggests roadmap updates
- AI reviews code quality

### 2.6.5: Federated Housekeeping

- Team workspace cleanup
- Shared memory consolidation
- Cross-project organization

### 2.6.5: Self-Healing System

- Automatic error recovery
- Self-testing and validation
- Continuous optimization
- Zero-maintenance mode

---

**Design Complete**: November 17, 2025  
**Next**: Implement Phase 1 in 2.6.5  
**Status**: Ready for review and implementation
