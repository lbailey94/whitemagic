# WhiteMagic Release Readiness Review Checklist

**Version**: 25.1.0
**Date**: 2026-07-20

This checklist must be completed before any major or minor release. All items must be checked or explicitly waived with justification.

## 1. Contract Integrity

- [ ] **Tool registry complete**: `scripts/check_stubs.py` passes with zero structural stubs
- [ ] **Dispatch table complete**: `unmapped_dispatch = 0` in generated facts
- [ ] **Unauthored tools = 0**: All tools have authored definitions
- [ ] **PRAT mappings complete**: All 860 tools mapped to 28 Ganas (830 PRAT entries)
- [ ] **Safety classification**: Every tool has READ/WRITE/DELETE classification
- [ ] **Stability classification**: Every tool has STABLE/OPTIONAL/EXPERIMENTAL
- [ ] **MCP annotations**: Every tool has readOnlyHint, destructiveHint, idempotentHint, openWorldHint, title

## 2. Memory System

- [ ] **Galaxy taxonomy**: 14 canonical galaxies, 5 deprecated aliases mapped
- [ ] **Holographic coordinates**: All memories have 6D coordinates
- [ ] **Content hashes**: All memories have content_hash
- [ ] **FTS5 index**: Search returns correct results (benchmark: 100% recall@10)
- [ ] **HNSW index**: Semantic search functional (if embeddings installed)
- [ ] **Session recording**: Progressive recall works across sessions
- [ ] **Dream cycle**: 12-phase consolidation runs without errors
- [ ] **Cross-galaxy associations**: Association graph builds without crashes

## 3. Governance and Security

- [ ] **Dharma profiles**: default, violet, sandbox, production, secure all functional
- [ ] **Karma ledger**: Effect recording works for every tool call
- [ ] **Engagement tokens**: Red-ops tools blocked without valid token (violet profile) — 238 tokens issued, defense-in-depth at middleware + handler level
- [ ] **Model signing**: Unsigned models blocked under violet profile — 4 registered models (2 verified, 1 unverified, 1 blocked)
- [ ] **Transaction firewall**: Spend limits enforced, per-agent rate limiting
- [ ] **WASM verification**: Checksum verification passes (if WM_WASM_VERIFY=1)
- [ ] **Audit signing**: Ed25519 key generation and verification functional
- [ ] **MCP integrity**: Tool definitions match between registry and dispatch — baseline 860 tools, 0 drift events
- [ ] **STRATA→MITRE mapping**: 47 security checker categories mapped to ATT&CK TTPs
- [ ] **Dharma violet rules**: 6 governance rules (token requirement, blue-ops logging, model load, exfiltration block, recon throttle, jailbreak block)
- [ ] **Semantic defense**: Ensemble voting operational
- [ ] **Canary tokens**: Active canaries for exfiltration detection
- [ ] **Hermit Crab**: Withdrawal-based access control with ledger
- [ ] **Adaptive defense**: Attack variant generation + defense loop

## 4. CI and Testing

- [ ] **Lane A (PR fast)**: All blocking jobs pass
- [ ] **Lane B (PR integration)**: Full test suite passes
- [ ] **Lane C (Nightly)**: Coverage report generated, reproducible build verified
- [ ] **False-green gates**: No new `continue-on-error` on blocking jobs
- [ ] **Test count**: 8,244+ test functions, 0 new failures
- [ ] **Flaky tests**: Zero flaky tests (all tests pass with random ordering)
- [ ] **Coverage**: Critical packages ≥75% branch, high-risk ≥65% branch

## 5. Performance

- [ ] **Cold bootstrap**: <5s to MCP handshake (lazy imports)
- [ ] **Memory search**: <100ms for 100-memory benchmark
- [ ] **Dispatch latency**: <50ms p99 for READ tools
- [ ] **Rust acceleration**: SIMD operations functional (if compiled)
- [ ] **Polyglot bridges**: At least Rust bridge functional (others optional)

## 6. Documentation

- [ ] **README.md**: Version, tool count, quick start all accurate
- [ ] **PROJECT_STATE.md**: Generated facts match actual codebase
- [ ] **CHANGELOG.md**: Release entry with all changes documented
- [ ] **AGENTS.md**: Version and changelog updated
- [ ] **PUBLIC_PROFILES.md**: All 5 profiles documented
- [ ] **COMPATIBILITY_POLICY.md**: Stable list, semver, deprecation, MCP checklist
- [ ] **CONTRIBUTING.md**: CI lanes, test tiers, add-tool steps
- [ ] **MODEL_GUIDE.md**: Quick start, safety, stability, best practices
- [ ] **Doc drift**: `scripts/check_doc_drift.py` passes

## 7. Packaging and Distribution

- [ ] **Version consistency**: `scripts/check_versions.py` passes
- [ ] **Wheel build**: `uv build` produces clean wheel
- [ ] **Clean install**: Wheel installs in fresh venv, `wm --json status` works
- [ ] **Reproducible build**: SHA-256 matches across builds from same commit
- [ ] **SBOM**: CycloneDX SBOM generated
- [ ] **Sigstore**: All artifacts signed
- [ ] **Docker image**: Builds and pushes to GHCR
- [ ] **PyPI**: Package uploads successfully

## 8. Polyglot

- [ ] **Rust**: `cargo test` passes, `cargo clippy` clean
- [ ] **WASM**: `wasm-pack build` succeeds for web and nodejs targets
- [ ] **Seed binary**: Cross-platform builds succeed (Linux, macOS, Windows)
- [ ] **Python fallback**: All polyglot features work without native bridges

## 9. Website

- [ ] **TypeScript**: `tsc --noEmit` passes
- [ ] **ESLint**: `npm run lint` passes
- [ ] **Next.js build**: `npm run build` succeeds
- [ ] **Catalog consistency**: `check_catalog_impl_consistency.mjs` passes
- [ ] **Site facts**: `sync_facts.py --check` passes
- [ ] **Smoke test**: 32 routes return 200 (main branch only)

## 10. Strategy Completion

- [ ] **Phase 0-7**: All completed and documented in strategy doc
- [ ] **Phase 8**: CI lanes defined, false-green gates eliminated, coverage by risk
- [ ] **Phase 9**: Documentation hierarchy, public profiles, compatibility policy, guides
- [ ] **Phase 10**: This checklist completed

## Sign-off

- **Reviewer**: _________________
- **Date**: _________________
- **Version**: _________________
- **Git SHA**: _________________
- **Test count**: _________________
- **Waivers**: _________________
