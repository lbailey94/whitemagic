#!/bin/bash
# C4: Git filter-repo execution script for WhiteMagic v22.0.0
# WARNING: This rewrites Git history. All collaborators must re-clone after.

set -euo pipefail

echo "=========================================="
echo "C4: Git History Cleanup (filter-repo)"
echo "=========================================="
echo ""
echo "This will remove the following from Git history:"
echo "  - .restructure_backups/       (11 MB tar.gz)"
echo "  - docs/ci-logs/               (28 MB logs)"
echo "  - docs/reports/auxiliary_reports/ (16 MB JSON)"
echo "  - polyglot/BitNet/            (41 MB llama.cpp clone)"
echo "  - projects/                   (7.6 MB, GPG test fixtures trigger secret scanners)"
echo "  - core/scripts/archaeology_results/ (24 KB)"
echo ""
echo "Estimated reduction: 1.1 GB -> ~50-100 MB"
echo ""
echo "REQUIREMENTS:"
echo "  1. All work committed (git status should be clean)"
echo "  2. git-filter-repo installed: sudo apt install git-filter-repo"
echo "  3. Remote access to force-push after"
echo "  4. Team coordination: everyone must re-clone"
echo ""
read -p "Proceed? (type 'yes' to continue): " CONFIRM
if [[ "$CONFIRM" != "yes" ]]; then
    echo "Aborted."
    exit 1
fi

# Verify clean state
if [[ -n $(git status --porcelain) ]]; then
    echo "ERROR: Uncommitted changes detected. Commit first:"
    git status --short
    exit 1
fi

# Verify git-filter-repo
if ! command -v git-filter-repo &> /dev/null; then
    echo "ERROR: git-filter-repo not found. Install: sudo apt install git-filter-repo"
    exit 1
fi

BACKUP_BRANCH="pre-filter-repo-backup-$(date +%Y%m%d-%H%M%S)"
echo ""
echo "Creating backup branch: $BACKUP_BRANCH"
git branch "$BACKUP_BRANCH"

echo ""
echo "Step 1: Removing directories from history..."
git filter-repo \
  --invert-paths \
  --path .restructure_backups/ \
  --path docs/ci-logs/ \
  --path docs/reports/auxiliary_reports/ \
  --path polyglot/BitNet/ \
  --path projects/ \
  --path core/scripts/archaeology_results/ \
  --force

echo ""
echo "Step 2: Garbage collection..."
git reflog expire --expire=now --all
git gc --aggressive --prune=now

echo ""
echo "Step 3: Verification..."
echo "New repo size:"
du -sh .git/

echo ""
echo "Largest remaining blobs (should be < 5 MB each):"
git rev-list --all --objects | \
  git cat-file --batch-check='%(objecttype) %(objectsize) %(objectname) %(rest)' | \
  awk '$1=="blob" && $2>1000000' | sort -k2 -n -r | head -10

echo ""
echo "=========================================="
echo "C4 COMPLETE"
echo "=========================================="
echo ""
echo "NEXT STEPS (manual):"
echo "  1. Verify tests still pass: PYTHONPATH=core pytest core/tests/unit/ -q"
echo "  2. Force-push to origin: git push --force-with-lease origin main"
echo "  3. Notify team to re-clone (history changed)"
echo "  4. Update .gitignore to prevent re-adding these paths"
echo ""
echo "Backup branch created: $BACKUP_BRANCH"
echo "To restore if needed: git checkout $BACKUP_BRANCH"
