# Development Process Documentation

This folder contains internal development process documentation, session notes, and release preparation materials.

## Purpose

These documents track the **how** of WhiteMagic's development rather than the **what** (which is in user-facing docs).

## Contents

### Release Preparation
- `*_v2.1.X_*.md` - Version-specific preparation, testing, and completion notes
- `RELEASE_*.md` - Release summaries and status reports
- `READY_FOR_*.md` - Pre-release review documents

### Development Process
- `IMPLEMENTATION_*.md` - Feature implementation tracking
- `DOCUMENTATION_AUDIT_*.md` - Documentation review results
- `ROADMAP_COMPARISON_*.md` - Roadmap planning and analysis
- `OPTION_*_IMPLEMENTATION.md` - Technical decision documents

### Testing
- `TEST_*.md` - Test results and reports
- `test_output*.txt` - Raw test output logs

### Utility Scripts
- `*.sh` - Development and debugging scripts
- `.commit-message-*.txt` - Prepared commit messages

### Historical
- `ARCHIVAL_*.md` - Completed milestone summaries
- `START_HERE.md` - Original development orientation (deprecated)

## Why Separate?

**User-facing docs** (in root and `docs/guides/`):
- Installation guides
- API references  
- Usage tutorials
- Security policies

**Development docs** (this folder):
- Sprint planning
- Bug tracking
- Testing notes
- Release checklists

## Distribution

These files are **not included in releases** (via `.gitignore`) to keep distributions clean and professional.

However, they are:
- ✅ Available in the GitHub repository
- ✅ Published as blog posts on whitemagic.dev
- ✅ Referenced in release notes for transparency

## For New Contributors

If you're contributing to WhiteMagic:
1. Check recent `IMPLEMENTATION_*.md` files to see current work
2. Review `ROADMAP_COMPARISON_*.md` for strategic direction
3. Read `TEST_*.md` to understand testing practices

For usage documentation, see:
- `/README.md` - Project overview
- `/INSTALL.md` - Installation guide
- `/docs/guides/` - User guides
