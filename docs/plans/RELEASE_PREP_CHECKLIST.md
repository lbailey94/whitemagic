# 2.6.5 Public Release Preparation Checklist

**Date**: November 16, 2025  
**Strategy**: Two-repository approach (dev + public)

---

## ✅ Completed

- [x] Version bump to 2.6.5
- [x] CHANGELOG updated
- [x] Package built
- [x] .gitignore strengthened

---

## 📋 Before Public Release

### 1. Verify .gitignore Working
```bash
git status --short
# Should NOT show any memory/*.md files
# Should NOT show SESSION_*.md, PHASE_*.md, etc.
```

### 2. Clean Untracked Session Docs
**Move to private dev docs or delete**:
- [ ] PARALLEL_THREADING_TEST_RESULTS.md
- [ ] PHASE_1_REFLECTION.md  
- [ ] SESSION_COMPLETE_v2.2.2.md
- [ ] SESSION_v2.2.3_PROGRESS.md
- [ ] V2.2.3_COMPLETION_STATUS.md (or move to docs/releases/)
- [ ] V2.2.3_IMPLEMENTATION_PLAN.md (or move to docs/planning/)

### 3. Verify Example Memories Exist
- [ ] `memory/short_term/example_short_term.md` exists and is good
- [ ] `memory/long_term/example_long_term.md` exists and is good
- [ ] No personal info in examples

### 4. Create .gitkeep Files
```bash
touch memory/.gitkeep
touch memory/short_term/.gitkeep
touch memory/long_term/.gitkeep
touch memory/archive/.gitkeep
```

### 5. Documentation Review
**Docs that SHOULD be public** (in docs/):
- [x] COGNITIVE_CYCLES_THEORY.md ✅
- [x] COGNITIVE_DEVELOPMENT_COMPARISON.md ✅
- [x] PHILOSOPHICAL_FOUNDATIONS.md ✅
- [x] WORKFLOW_RULES_v3_UNIVERSAL.md ✅
- [x] TOKEN_OPTIMIZATION_STRATEGIES.md ✅
- [x] WINDSURF_WORKFLOW_RULES_v2.md ✅
- [ ] README.md (update for 2.6.5)
- [ ] CONTRIBUTING.md (if exists)

**Docs that should be PRIVATE/DEV**:
- SESSION_DISCUSSION_SUMMARY.md (too personal/internal?)

### 6. Test Clean Clone
```bash
cd /tmp
git clone /home/lucas/Desktop/whitemagic test-whitemagic
cd test-whitemagic
ls -la memory/
# Should see: .gitkeep files, example files, templates/
# Should NOT see: Our 88 personal memories
```

### 7. Size Check
```bash
du -sh .  # Should be much smaller without memory/
```

---

## 🎯 Alternative: Separate Public Repo

**If you prefer complete separation**:

### Option A: Git Filter-Branch (Clean History)
```bash
# Clone to new location
git clone whitemagic whitemagic-public
cd whitemagic-public

# Remove all memory commits from history
git filter-branch --tree-filter 'rm -rf memory/short_term/*.md memory/long_term/*.md memory/archive/*.md' HEAD

# Force push to new remote
```

### Option B: Fresh Start (Simplest)
```bash
# Create new repo with only current state
mkdir whitemagic-public
cd whitemagic-public
git init

# Copy only public files from dev repo
# Skip: memory/, session docs, dev artifacts
```

### Option C: Subtree (Maintain Both)
```bash
# Keep dev repo private
# Push specific branches/tags to public repo
# Gives you fine control
```

---

## 🌸 White Magic Alignment Check

### Principles to Uphold

**Empowerment**:
- ✅ Full source code available
- ✅ Examples and documentation
- ✅ No artificial limitations

**Transparency**:
- ✅ Clear licensing (MIT)
- ✅ Honest about capabilities
- ✅ Acknowledge limitations

**Privacy**:
- ✅ No personal memories in release
- ✅ No private development notes
- ✅ Clean, professional presentation

**Community**:
- ✅ Open to contributions
- ✅ Welcoming documentation
- ✅ Ethical guidelines

**Responsibility**:
- ✅ Clear usage instructions
- ✅ Warning about API costs
- ✅ Sustainable architecture

---

## 📊 Release Size Targets

**Current full repo**: ~150MB (with all memories)

**Target public release**:
- Source code: ~5-10MB
- Documentation: ~2MB
- Examples: ~100KB
- **Total: <15MB** ✅

This ensures:
- Fast clone times
- Easy distribution
- Professional appearance
- No bloat

---

## 🚀 Recommended Release Process

1. **Strengthen .gitignore** ✅ (done)
2. **Move session docs** to `docs/development/` (excluded in .gitignore)
3. **Create .gitkeep files** for empty memory dirs
4. **Verify clean status**: `git status` shows no memory files
5. **Commit**: `git add . && git commit -m "chore: release 2.6.5"`
6. **Tag**: `git tag 2.6.5`
7. **Create GitHub release** with notes
8. **Monitor**: Watch for issues, be responsive

---

## 🙏 Gratitude & Attribution

**To acknowledge in release**:
- Community contributors
- Philosophical inspirations (I Ching, Daoism)
- Open source projects we build on
- Early testers and feedback providers

**README should mention**:
- This is research/experimental
- Costs involved (API usage)
- Community-driven development
- Invitation to contribute

---

**Status**: Checklist created  
**Next**: Execute prep steps, then release  
**Alignment**: ✅ White magic principles upheld
