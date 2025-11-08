# Deprecated Documentation

**Last Updated**: November 8, 2025

The following documents are **deprecated** or **superseded** by more current documentation. They are kept for historical reference but should not be used for new deployments.

---

## 🚫 **Do Not Use These**

### **Deployment Documents** (Use NEXT_STEPS.md instead)

- ❌ **DEPLOYMENT_STATUS.md** - Outdated status (use COMPREHENSIVE_REVIEW_ASSESSMENT.md)
- ❌ **DEPLOYMENT_READY_v2.1.0.md** - Superseded by NEXT_STEPS.md
- ❌ **READY_TO_DEPLOY_v2.1.0.md** - Superseded by NEXT_STEPS.md
- ❌ **READY_FOR_DEPLOYMENT.md** - Superseded by DEPLOY_NOW.md
- ❌ **PRODUCTION_DEPLOYMENT_FIXED.md** - Outdated (fixes already in main docs)
- ❌ **DEPLOYMENT_COMPLETE_SUMMARY.md** - Superseded by COMPREHENSIVE_REVIEW_ASSESSMENT.md

### **Status Documents** (Use COMPREHENSIVE_REVIEW_ASSESSMENT.md)

- ❌ **FINAL_STATUS.md** - Outdated (Nov 5, 2025)
- ❌ **FIXES_SUMMARY.md** - Superseded by REVIEW_IMPLEMENTATION_SUMMARY.md
- ❌ **ISSUES_RESOLVED.md** - Superseded by COMPREHENSIVE_REVIEW_ASSESSMENT.md
- ❌ **SESSION_SUMMARY.md** - Historical only
- ❌ **CLEANUP_SUMMARY.md** - Historical only

### **Dashboard Documents** (Use dashboard/README.md or NEXT_STEPS.md)

- ❌ **MEMORY_BROWSER_COMPLETE.md** - Feature already shipped
- ❌ **READY_FOR_DASHBOARD_IMPROVEMENTS.md** - Outdated
- ❌ **DASHBOARD_QUICK_START.md** - Superseded by NEXT_STEPS.md

### **CI/CD Documents**

- ❌ **CI_CD_SETUP_SUMMARY.md** - Outdated (CI updated since then)

---

## ✅ **Use These Instead**

### **For Deployment**
1. **[NEXT_STEPS.md](NEXT_STEPS.md)** - Complete launch checklist (npm + registry + deploy) ⭐ **PRIMARY**
2. **[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)** - Comprehensive production guide
3. **[DEPLOY_NOW.md](DEPLOY_NOW.md)** - Quick 45-minute Docker deploy

### **For Project Status**
1. **[COMPREHENSIVE_REVIEW_ASSESSMENT.md](COMPREHENSIVE_REVIEW_ASSESSMENT.md)** - Latest review (Nov 8, 2025) ⭐ **PRIMARY**
2. **[TEST_COVERAGE_SUMMARY.md](TEST_COVERAGE_SUMMARY.md)** - Testing statistics
3. **[ROADMAP.md](ROADMAP.md)** - Development roadmap

### **For Documentation Navigation**
1. **[DOCUMENTATION_MAP.md](DOCUMENTATION_MAP.md)** - "Which doc should I read?" guide ⭐ **PRIMARY**
2. **[docs/INDEX.md](docs/INDEX.md)** - Complete documentation index
3. **[README.md](README.md)** - Project overview

---

## 📂 **Document Status Reference**

| Document | Status | Replacement | Notes |
|----------|--------|-------------|-------|
| NEXT_STEPS.md | ✅ **ACTIVE** | N/A | Current launch guide |
| COMPREHENSIVE_REVIEW_ASSESSMENT.md | ✅ **ACTIVE** | N/A | Latest review |
| DEPLOYMENT_GUIDE.md | ✅ **ACTIVE** | N/A | Updated Nov 8 |
| TEST_COVERAGE_SUMMARY.md | ✅ **ACTIVE** | N/A | New Nov 8 |
| DOCUMENTATION_MAP.md | ✅ **ACTIVE** | N/A | New Nov 8 |
| | | | |
| DEPLOYMENT_STATUS.md | ⚠️ **DEPRECATED** | COMPREHENSIVE_REVIEW_ASSESSMENT.md | Outdated |
| FINAL_STATUS.md | ⚠️ **DEPRECATED** | COMPREHENSIVE_REVIEW_ASSESSMENT.md | Outdated |
| DEPLOYMENT_READY_v2.1.0.md | ⚠️ **DEPRECATED** | NEXT_STEPS.md | Superseded |
| MEMORY_BROWSER_COMPLETE.md | ⚠️ **DEPRECATED** | NEXT_STEPS.md | Feature shipped |
| PRODUCTION_DEPLOYMENT_FIXED.md | ⚠️ **DEPRECATED** | DEPLOYMENT_GUIDE.md | Fixes integrated |

---

## 🗑️ **Cleanup Recommendations**

### **Can Be Archived** (move to `docs/archive/`)
- All deprecated deployment status docs
- Historical session summaries
- Completed milestone docs
- Old fix reports

### **Should Keep** (active documentation)
- README.md
- DEPLOYMENT_GUIDE.md
- NEXT_STEPS.md
- COMPREHENSIVE_REVIEW_ASSESSMENT.md
- TEST_COVERAGE_SUMMARY.md
- DOCUMENTATION_MAP.md
- All files in `docs/guides/` and `docs/production/`

---

## 📋 **Migration Guide**

If you're using an old document, here's what to do:

**Old**: DEPLOYMENT_STATUS.md  
**New**: COMPREHENSIVE_REVIEW_ASSESSMENT.md  
**Why**: More comprehensive, includes latest review findings

**Old**: READY_TO_DEPLOY_v2.1.0.md  
**New**: NEXT_STEPS.md  
**Why**: Includes npm publish, MCP registry, and hosting instructions

**Old**: FINAL_STATUS.md  
**New**: COMPREHENSIVE_REVIEW_ASSESSMENT.md  
**Why**: More recent (Nov 8 vs Nov 5)

**Old**: MEMORY_BROWSER_COMPLETE.md  
**New**: NEXT_STEPS.md or dashboard/README.md  
**Why**: Feature already shipped and documented

**Old**: DASHBOARD_QUICK_START.md  
**New**: NEXT_STEPS.md § Dashboard section  
**Why**: Consolidated into single launch guide

---

## ✅ **Verification**

To ensure you're using current docs:

```bash
# Check last modified date
ls -lt *.md | head -20

# Recent docs (Nov 8, 2025):
# - COMPREHENSIVE_REVIEW_ASSESSMENT.md
# - NEXT_STEPS.md
# - TEST_COVERAGE_SUMMARY.md
# - DOCUMENTATION_MAP.md
# - REVIEW_IMPLEMENTATION_SUMMARY.md
```

---

**Summary**: Use **NEXT_STEPS.md** for deployment, **COMPREHENSIVE_REVIEW_ASSESSMENT.md** for status, and **DOCUMENTATION_MAP.md** to find everything else.
