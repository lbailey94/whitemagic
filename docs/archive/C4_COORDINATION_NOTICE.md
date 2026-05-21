# C4 Coordination Notice: Git History Rewrite Required

**Date**: 2026-04-16  
**Action Required**: Repository history rewrite using `git filter-repo`  
**Impact**: All collaborators must re-clone after execution  
**Backup**: Branch `pre-filter-repo-backup-YYYYMMDD-HHMMSS` will be created

---

## Why

The repository is **1.1 GB** due to accidentally committed artifacts:
- 11 MB `.restructure_backups/docs_pre_restructure.tar.gz`
- 28 MB `docs/ci-logs/` (committed log files)
- 16 MB `docs/reports/auxiliary_reports/deep_scan_results.json`
- 41 MB `polyglot/BitNet/3rdparty/llama.cpp/` (full llama.cpp clone)
- 7.6 MB `projects/` (includes 5 GPG test fixture `.key` files that trigger secret scanners)

Target size after cleanup: **~50-100 MB**

---

## Pre-Flight Checklist

- [x] All critical work committed (verified: 0 uncommitted changes)
- [x] Round 1 and 2 fixes complete
- [x] Regression tests passing (34/34)
- [x] `git-filter-repo` install command ready

---

## Execution Steps (Run These)

```bash
# 1. Navigate to repo
cd /home/lucas/Desktop/WHITEMAGIC

# 2. Install git-filter-repo (if not already)
sudo apt update && sudo apt install -y git-filter-repo

# 3. Run the prepared script
chmod +x C4_GIT_FILTER_REPO_SCRIPT.sh
./C4_GIT_FILTER_REPO_SCRIPT.sh

# 4. Or run filter-repo directly:
git filter-repo \
  --invert-paths \
  --path .restructure_backups/ \
  --path docs/ci-logs/ \
  --path docs/reports/auxiliary_reports/ \
  --path polyglot/BitNet/ \
  --path projects/ \
  --path core/scripts/archaeology_results/ \
  --force

# 5. Garbage collect
git reflog expire --expire=now --all
git gc --aggressive --prune=now

# 6. Verify size
du -sh .git/
# Expect: ~50-100 MB (was 1.1 GB)

# 7. Verify tests still pass
PYTHONPATH=core pytest core/tests/unit/regression/ -v

# 8. Force-push (requires maintainer access)
git push --force-with-lease origin main
```

---

## Post-Execution: Team Notice

After force-push, post this to your team channel:

```
🚨 Git history rewritten for WhiteMagic repo

We've cleaned accidentally committed large files using git filter-repo.
The repo went from 1.1 GB -> ~50 MB.

ACTION REQUIRED for all collaborators:
  1. Save any uncommitted work (stashes won't transfer)
  2. Delete your local clone
  3. Re-clone: git clone https://github.com/whitemagic-ai/whitemagic.git
  4. Re-install: pip install -e core/.[dev,mcp,cli]

DO NOT pull -- the history is incompatible. Re-clone is required.
Backup branch exists if we need to recover anything: pre-filter-repo-backup-*
```

---

## What's Removed vs. Preserved

**Removed from history**:
- `.restructure_backups/` (11 MB tarball)
- `docs/ci-logs/` (28 MB logs)
- `docs/reports/auxiliary_reports/` (16 MB JSON)
- `polyglot/BitNet/` (41 MB vendored llama.cpp)
- `projects/` (7.6 MB — includes GPG test keys that trigger scanners)
- `core/scripts/archaeology_results/` (24 KB)

**Preserved**:
- All source code
- All documentation
- All test files
- All legitimate configuration
- GitHub metadata (CODEOWNERS, workflows, issue templates)

---

## Rollback Plan

If something goes wrong:

```bash
# The script creates a backup branch
git checkout pre-filter-repo-backup-YYYYMMDD-HHMMSS

# Or restore from GitHub (if force-push hasn't happened)
git fetch origin
git reset --hard origin/main
```

---

## Verification Commands

After filter-repo, verify:

```bash
# No more large blobs
git rev-list --all --objects | \
  git cat-file --batch-check='%(objecttype) %(objectsize) %(objectname) %(rest)' | \
  awk '$1=="blob" && $2>5000000'
# Should return nothing

# No secret-like files
git log --all --full-history --name-only | sort -u | grep -E '\.key$|\.pem$' | head
# Should return nothing (or only intentional paths)

# Tests pass
PYTHONPATH=core pytest core/tests/unit/regression/ -q
# Should be 34 passed
```

---

## Questions?

See `RELEASE_READINESS_PLAN.md` Section 5 (C4) for full technical details.
