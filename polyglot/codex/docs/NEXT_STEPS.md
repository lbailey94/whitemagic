# CODEX Project: Next Steps & Improvement Roadmap

**Date:** April 24, 2026 | **Status:** Phase 1 Complete | **Version:** 0.1.0

---

## Executive Summary

The CODEX pipeline is now fully functional end-to-end:
```
Extraction -> Chunking -> Embedding -> Indexing -> Export
```

Recent completed work:
- Code quality: all clippy warnings resolved
- Testing: 13+ unit and integration tests
- CLI tooling: `stats`, `check`, and `watch` commands added
- Benchmarks: Criterion suite for chunking performance

This document outlines the next phases of development.

---

## Phase 2: Production Hardening (High Priority)

### 2.1 Configuration System Integration

**Current State:** `config/codex.yaml` exists but is NOT loaded by the CLI. All paths and settings are hardcoded in `src/main.rs`.

**Required Work:**
- Load `codex.yaml` at startup using `serde_yaml`
- Wire all hardcoded values to config settings (base path, token targets, batch sizes, API models, source paths)
- Support `--config <path>` CLI flag
- Add environment variable overrides (`CODEX_BASE_PATH`, `CODEX_LOG_LEVEL`)
- Validate config on load with clear error messages

**Impact:** Eliminates rebuilds for parameter tuning; enables multiple project support.
**Files:** `src/main.rs`, `crates/codex-core/src/lib.rs`

### 2.2 Token-Accurate Chunking

**Current State:** Token counting uses `chars / 4` approximation in `codex-chunk/src/lib.rs:66`.

**Required Work:**
- Enable the `tiktoken` feature (already declared in `codex-chunk/Cargo.toml`)
- Replace approximation with real token counts
- Implement hierarchy levels from config (`paragraph_target_tokens: 250`, `section_target_tokens: 1000`, `document_target_tokens: 4000`)
- Add overlap support (`overlap_tokens: 50`)
- Implement markdown header-aware splitting

**Impact:** Critical for embedding quality and API cost control.
**Files:** `crates/codex-chunk/src/lib.rs`

### 2.3 Persistent Index Storage

**Current State:** Index is rebuilt from scratch on every run. SurrealDB is a dependency but unused.

**Required Work:**
- Implement incremental index updates via dirty-chunk manifest
- Add SurrealDB backend for persistent graph + vector storage
- Add index versioning to detect stale indices

**Impact:** Reduces rebuild time from minutes to seconds.
**Files:** `crates/codex-index/src/lib.rs`, `Cargo.toml`

---

## Phase 3: Missing Pipeline Stages (High Priority)

### 3.1 Image Processing Pipeline

**Current State:** The `images` feature exists but is not wired. RESEARCH contains ~8K Twitter media folders skipped by text-only extraction.

**Required Work:**
- Implement `extract_image()` using Tesseract OCR
- Add multimodal API client (Claude 3 Vision, GPT-4V)
- Resize images to `max_dimension: 2048`
- Cache extractions to avoid re-processing

**Impact:** Unlocks the 18GB RESEARCH corpus (mostly images).
**Files:** `crates/codex-extract/src/lib.rs`

### 3.2 PDF & Document Extraction

**Current State:** `SourceType::Pdf` exists but PDFs are skipped entirely.

**Required Work:**
- Add PDF text extraction using `pdf-extract` or `lopdf`
- Extract text, tables, and images
- Preserve document structure

**Impact:** LIBRARY and RESEARCH likely contain PDFs currently invisible.
**Files:** `crates/codex-extract/src/lib.rs`

### 3.3 Conversation-Aware Chunking

**Current State:** `ChunkStrategy::Conversation` variant exists but is unused.

**Required Work:**
- Detect conversation format from headers (`## User`, `## Grok`, `## Assistant`)
- Preserve speaker context across chunk boundaries
- Implement `chunk_by_turns` option from config

**Impact:** Prevents semantic breakage in conversation chunks.
**Files:** `crates/codex-chunk/src/lib.rs`

---

## Phase 4: Performance & Scalability (Medium Priority)

### 4.1 HNSW Vector Index

**Current State:** Flat O(n^2) k-NN with rayon. Bottleneck for >10K chunks.

**Required Work:**
- Integrate `instant-distance` or `hnsw` crate
- Benchmark flat vs HNSW for 10K, 50K, 100K vectors
- Add configurable index type in config (`flat | hnsw | faiss`)
- Serialize HNSW index to disk

**Impact:** Reduces query latency from seconds to milliseconds.
**Files:** `crates/codex-index/src/lib.rs`

### 4.2 Parallel Embedding

**Current State:** Embedding processes one file at a time sequentially.

**Required Work:**
- Parallelize across JSONL files using `rayon` or `tokio::spawn`
- Implement `rayon_threads` setting from config
- Add concurrency limit for API rate limits

**Impact:** 4-6x speedup on 8-core machines.
**Files:** `crates/codex-embed/src/lib.rs`

### 4.3 Streaming Pipeline

**Current State:** Each stage reads all JSONL into memory, causing spikes.

**Required Work:**
- Implement streaming extraction -> chunking via `tokio::sync::mpsc`
- Process documents as extracted rather than batching
- Add memory limit / backpressure

**Impact:** Enables processing of the full 18GB RESEARCH corpus without OOM.
**Files:** `src/main.rs`, `crates/codex-extract/src/lib.rs`, `crates/codex-chunk/src/lib.rs`

---

## Phase 5: Web UI & API (Medium Priority)

### 5.1 Dynamic Web Viewer

**Current State:** `viewer.html` is a static hand-written file.

**Required Work:**
- Generate `viewer.html` from Rust templates (`handlebars` already a dependency)
- Auto-inject sphere JSON data or serve via API
- Add dynamic search endpoint (`/api/search?q=...`)

**Impact:** Viewer becomes a live representation of the corpus.
**Files:** `crates/codex-export/src/lib.rs`, `src/main.rs`

### 5.2 Query API Enhancements

**Current State:** `serve` command starts Axum but only serves static files.

**Required Work:**
- Add `/api/query?q=...&k=10` endpoint (embed query -> vector search -> return chunks)
- Add `/api/stats` for live corpus statistics
- Add `/api/consolidate` for cluster summaries

**Impact:** Makes CODEX usable as a knowledge backend.
**Files:** `src/main.rs`, `crates/codex-index/src/lib.rs`

---

## Phase 6: Quality & Reliability (Medium Priority)

### 6.1 End-to-End Integration Tests

**Current State:** Tests exist per crate but no full pipeline test.

**Required Work:**
- Add `tests/pipeline_test.rs` running full pipeline on temp directory
- Verify JSONL output at each stage
- Assert sphere.json validity
- Test with/without optional features

**Impact:** Prevents regressions across crates.
**Files:** `tests/pipeline_test.rs`

### 6.2 Error Recovery & Resume

**Current State:** Only embedding has checkpoint/resume logic.

**Required Work:**
- Add SHA256 manifest tracking to extraction
- Add resume to chunking and indexing (incremental updates)
- Add `--force` flag to override resume

**Impact:** Small changes only trigger downstream stages.
**Files:** `src/main.rs`, all crate entry points

---

## Phase 7: Data Quality & Features (Low Priority)

### 7.1 Metadata Enrichment

**Current State:** Documents have minimal metadata.

**Required Work:**
- Extract dates from conversation filenames
- Parse markdown frontmatter for tags, author, title
- Detect language using `whatlang`
- Extract keywords using TF-IDF

**Impact:** Better clustering, filtering, and search relevance.
**Files:** `crates/codex-extract/src/lib.rs`

### 7.2 Fuzzy Deduplication

**Current State:** Deduplication is exact string match only.

**Required Work:**
- Add MinHash or SimHash for near-duplicate detection
- Merge similar chunks with source attribution

**Impact:** Reduces corpus size; identifies redundant content.
**Files:** `crates/codex-chunk/src/lib.rs`

### 7.3 Source Attribution in Viewer

**Current State:** Nodes are color-coded but not clickable to original files.

**Required Work:**
- Add `source_url` or `source_path` to SphereNode
- Make nodes clickable to view original document
- Add "highlight by source" filter

**Impact:** Users can trace insights back to origins.
**Files:** `crates/codex-export/src/lib.rs`, `50_export/viewer.html`

---

## Phase 8: Vaya Vida Integration (Future)

### 8.1 Live Sync Protocol

**Current State:** Export is a one-time JSON file write.

**Required Work:**
- Design sync protocol for incremental updates
- WebSocket or SSE stream for new nodes/edges
- Version negotiation for sphere format compatibility

**Impact:** CODEX becomes a live knowledge backend for Vaya Vida.
**Files:** `crates/codex-export/src/lib.rs`

### 8.2 Multi-Sphere Support

**Current State:** Single sphere export per run.

**Required Work:**
- Support multiple named spheres in config
- Cross-sphere linking and comparison
- Sphere-level access control

**Impact:** Enables multiple knowledge domains or users.
**Files:** `crates/codex-export/src/lib.rs`, `config/codex.yaml`

---

## Discovered Bugs & Gaps (Codebase Audit — April 24, 2026)

### 🔴 Bug: `embed_batch` scoping error in `codex-embed` (compile-fail with `api` feature)

`codex-embed/src/lib.rs:220-224` — `embed_batch()` references `dimensions` and `max_retries` as if they're in scope, but they're parameters of the *outer* `embed_directory()` function (prefixed `_` as unused). Enabling the `api` feature will produce a compile error.

**Fix:** Pass `dimensions` and `max_retries` as parameters to `embed_batch()`, and remove the `_` prefixes from `embed_directory()`.

### 🔴 Bug: `embed_query_text` only exists under `local` feature gate

`codex-embed/src/lib.rs:309` — `embed_query_text()` is `#[cfg(feature = "local")]`. The `cmd_query --semantic` path in `main.rs` calls it unconditionally. If only the `api` feature is enabled, this won't compile.

**Fix:** Add an `api` variant of `embed_query_text` that calls the OpenAI embeddings endpoint, or gate the semantic query path behind the `local` feature.

### 🟡 Gap: `CodexConfig` struct doesn't match YAML schema

`codex-core/src/lib.rs:64-173` — The `CodexConfig` struct exists but:
- No `load_config()` function anywhere in the codebase
- `ChunkingConfig` is missing `respect_headers`, `preserve_frontmatter`, and `conversation` sub-config
- `ImageProcessingConfig.multimodal_api` is `Option<String>` but YAML has a string value (not null)
- `IndexingConfig` is missing `tag_clustering` sub-config and `max_connections_per_node`
- `ExportConfig.formats` is `Vec<ExportFormat>` (enum) but YAML has `["jsonl", "json", "yaml"]` (strings) — deserialization will fail

**Fix:** Align struct fields with YAML, add `load_config(path) -> Result<CodexConfig>`, add missing sub-configs.

### 🟡 Gap: `infer_source` duplicated 3 times

Three separate `infer_source` functions exist:
- `src/main.rs:645-653` (used by CLI query output)
- `src/main.rs` `api_query` handler (inline logic)
- `crates/codex-export/src/lib.rs:114-122` (used by sphere export)

**Fix:** Move to `codex-core` as a public utility.

### 🟡 Gap: `consolidate` command not in pipeline stages

`src/main.rs` has a working `cmd_consolidate` and `Consolidate` CLI subcommand, but:
- It's not in the `stages` array used by `codex build` (`["extract", "chunk", "embed", "index", "export"]`)
- The `PHASE_2_SYNTHESIS_PLAN.md` references `codex-synthesize` crate which doesn't exist yet
- Consolidation output (`consolidate_output.jsonl`) is written to project root, not `40_index/`

**Fix:** Add `"consolidate"` between `"index"` and `"export"` in build stages. Create `codex-synthesize` crate as Phase 2 extension.

### 🟡 Gap: No error handling for missing API keys in query path

`cmd_query --semantic` calls `codex_embed::embed_query_text()` which initializes FastEmbed on every call (no caching). If the model download fails or local feature is disabled, the error message is opaque.

**Fix:** Cache the local model instance, add clear error messages, support API-based query embedding.

### 🟢 Note: Hardcoded base path in every command

Every `cmd_*` function starts with `let base_path = PathBuf::from("/home/lucas/Desktop/CODEX")`. This is the single most impactful fix — config loading eliminates all of these.

---

## Quick Wins (Prioritized by Impact)

1. **Load `config/codex.yaml`** in CLI main() and replace all hardcoded paths ← *highest impact*
2. **Fix `embed_batch` scoping bug** — pass dimensions/max_retries as params ← *unblocks api feature*
3. **Enable `tiktoken` feature** in `codex-chunk/Cargo.toml` and wire token counting ← *embedding quality*
4. **Add progress bars** to extraction and indexing stages (copy pattern from embedding)
5. **Add `/api/health` endpoint** to Axum server for monitoring
6. **Implement `--force` flag** for `codex build` to skip all resume checks
7. **Wire `dry_run` config setting** to skip all file writes when true
8. **Move `infer_source` to `codex-core`** — deduplicate 3 copies
9. **Add `consolidate` to build pipeline stages** between index and export
10. **Add `tests/pipeline_test.rs`** with a minimal 3-file temp directory
11. **Add source path to sphere export** so viewer can link back to originals
12. **Generate viewer.html from template** instead of static hand-written file
13. **Add image feature gate compilation** to CI / build verification
14. **Add API-based `embed_query_text`** for semantic query without local model

---

*End of report.*
