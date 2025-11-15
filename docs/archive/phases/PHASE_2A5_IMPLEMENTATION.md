# Phase 2A.5: Platform Hardening - Implementation Guide

**Status**: 🚧 Starting Now  
**Priority**: P0 - Critical Foundation  
**Timeline**: 5-7 days  
**Start Date**: November 10, 2025

---

## 📋 Day-by-Day Implementation Plan

### **Day 1: API Versioning & Headers**

#### Tasks
- [x] Create `VERSION` file
- [ ] Add version header middleware
- [ ] Publish `/openapi.json` endpoint
- [ ] Create deprecation policy document
- [ ] Separate `/health` vs `/ready` endpoints

#### Implementation Steps

```bash
# 1. VERSION file (already created)
cat VERSION
# Output: 2.1.1

# 2. Update pyproject.toml to read from VERSION
# 3. Update package.json to read from VERSION
# 4. Update Dockerfile to use VERSION
```

---

### **Day 2: Structured Logging**

#### Tasks
- [ ] Create JSON logging formatter
- [ ] Add correlation ID middleware
- [ ] Replace all `print()` with `logger.info()`
- [ ] Test log output format

---

### **Day 3: Docker Hardening**

#### Tasks
- [ ] Update Dockerfile (non-root user)
- [ ] Add read-only filesystem
- [ ] Drop all capabilities
- [ ] Update docker-compose.yml
- [ ] Test container security

---

### **Day 4: Backup/Restore CLI**

#### Tasks
- [ ] Create `wm backup create` command
- [ ] Create `wm backup restore` command
- [ ] Create `wm backup verify` command
- [ ] Add backup round-trip test
- [ ] Document backup procedures

---

### **Day 5: Security CI**

#### Tasks
- [ ] Add Trivy scanning workflow
- [ ] Generate SBOM (CycloneDX)
- [ ] Set up cosign signing
- [ ] Configure CI to block on criticals
- [ ] Test full CI pipeline

---

## 🚀 Ready to Start?

**Current Status**: Documentation updated ✅, VERSION file created ✅

**Next Steps**:
1. Implement version header middleware
2. Add structured logging
3. Harden Docker setup
4. Create backup/restore CLI
5. Add security scanning to CI

Let's begin with Day 1 implementation!
