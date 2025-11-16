# Option B: Complete Implementation Plan

**Decision**: Build it right  
**Timeline**: 3-5 days  
**Next Review**: After all features implemented

## Tasks

### ✅ Phase 1: Dependencies (DONE)
- Added email-validator to pyproject.toml

### 🔨 Phase 2: Local Embeddings (Day 1)
- Add sentence-transformers dependency
- Implement LocalEmbeddingProvider
- Update config to default to "local"
- Test without API key

### 🔨 Phase 3: CLI Commands (Day 2)
- `wm exec <cmd>` - read-only
- `wm exec <cmd> --write` - with approval
- `wm search <query> --mode semantic`
- `wm search --setup-embeddings` wizard

### 🔨 Phase 4: Write Mode + Approval (Day 3)
- Approver class with CLI prompts
- Wire into TerminalMCPTools
- Update API endpoint (remove 501 error)
- Add confirmation header requirement

### 🔨 Phase 5: Flexible Allowlist (Day 3)
- Parse commands (not exact matches)
- Support "git log -5" style commands
- Wildcard patterns

### 📝 Phase 6: Documentation (Day 4)
- Update all version refs 2.1.3 → 2.2.1
- Match docs to implementation
- Fix broken links

### ✅ Phase 7: Testing (Day 5)
- Run full test suite
- Test all new features
- Clean install verification

### 🔍 Phase 8: Second Review
- Independent review of completed work
- Address findings
- Ship when ready

## Starting Now: Local Embeddings
