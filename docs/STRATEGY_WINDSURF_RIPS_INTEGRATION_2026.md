# WindsurfRips Integration Strategy

**Date**: 2026-07-13
**Goal**: Integrate WindsurfRips extraction, ingestion, and mining techniques into WhiteMagic's MCP tool system, making them callable, efficient, and far more capable than the standalone scripts.

---

## 1. Current State

### 1.1 WindsurfRips Standalone Scripts (`windsurf-rips/`)

| Script | Purpose | Technique |
|--------|---------|-----------|
| `windsurf_api_export.py` | **Best method**. Exports all conversations via live language server gRPC API. Bypasses .pb encryption entirely. | Scans `/proc` for `language_server` PID → extracts `WINDSURF_CSRF_TOKEN` from environ → finds gRPC port via `ss`/`/proc/net/tcp` → calls `GetAllCascadeTrajectories`, `GetCascadeTranscriptForTrajectoryId`, `GetCascadeTrajectorySteps` (paginated, bypasses 200K truncation) |
| `export_all_conversations.py` | Fallback method. Parses encrypted .pb files with simple protobuf scanner. | Reads `state.vscdb` metadata → scans `.pb` files → heuristic text extraction (varint parser, UTF-8 decode, role alternation) → categorizes by keyword matching → exports organized markdown + JSON |
| `ingest_transcripts.py` | Parses exported transcripts and ingests into sessions galaxy. | Regex-based turn parsing (`=== MESSAGE N - Role ===`) → heuristic turn type classification (decision, breakthrough, error, code_change, question, answer, summary, context) → importance scoring → `SessionRecorder.record_user/record_ai` |
| `compare_exports.py` | Diffs exports across dates to find new/changed sessions. | Loads `INDEX.json` from each export → compares by cascadeId, transcript length, step count, content hash |
| `organize_all.py` | Master organizer tying together all extraction sources. | Cross-references metadata from multiple sources (state.vscdb, .pb files, IndexedDB blobs, brain files) → categorizes → writes unified index |
| `pb_decryptor.py` | Brute-force .pb decryption (superseded by API export). | Tries AES-CBC/CTR with keys from oauth_creds, installation_id, settings.json |
| `ingest_windsurf.rs` | Rust high-performance ingestion (placeholder). | Direct SQLite insertion with WAL mode, batch transactions, FTS rebuild |

### 1.2 Existing MCP Tools (5 tools, all in `gana_chariot`)

| Tool | Handler | Source | Limitation |
|------|---------|--------|------------|
| `windsurf_list_conversations` | `windsurf_conv.py` | `windsurf_reader.py` | Only lists .pb files, no API method |
| `windsurf_read_conversation` | `windsurf_conv.py` | `windsurf_reader.py` | Heuristic protobuf parser, no role detection, no structured turns |
| `windsurf_export_conversation` | `windsurf_conv.py` | `windsurf_reader.py` | Single conversation only, no bulk export |
| `windsurf_search_conversations` | `windsurf_conv.py` | `windsurf_reader.py` | Keyword search only, no semantic search, no FTS5 |
| `windsurf_stats` | `windsurf_conv.py` | `windsurf_reader.py` | Basic file count + size only |

### 1.3 Key Gaps

1. **No API-based export** — The best technique (gRPC language server API) is not exposed as an MCP tool
2. **No ingestion pipeline** — `ingest_transcripts.py` is standalone only; no MCP tool can ingest sessions
3. **No turn classification** — Existing tools return raw text, not structured turns with types and importance
4. **No incremental sync** — No way to detect and ingest only new/changed sessions
5. **No pattern mining** — No cross-session analysis for decisions, breakthroughs, recurring topics
6. **No semantic search** — Only keyword matching; doesn't use HNSW embeddings or FTS5
7. **No categorization** — No automatic topic routing to appropriate galaxies
8. **No full-step retrieval** — 200K transcript truncation bypass not available
9. **Duplicated code** — Protobuf parser exists in both `windsurf_reader.py` and `export_all_conversations.py`
10. **No auto-discovery** — No way to auto-detect running language server and use API method preferentially

---

## 2. Proposed Architecture

### 2.1 New Module: `archaeology/session_miner.py`

A unified session mining system that combines all WindsurfRips techniques into a single Python module with clean APIs.

```
archaeology/session_miner.py
├── LanguageServerClient       # gRPC API client (from windsurf_api_export.py)
├── ProtobufFallback           # .pb file parser (from export_all_conversations.py)
├── TranscriptParser           # Turn parsing + classification (from ingest_transcripts.py)
├── SessionIngestor            # Galaxy ingestion with dedup + incremental sync
├── ExportComparator           # Cross-export diffing (from compare_exports.py)
├── PatternMiner               # Cross-session pattern mining (NEW)
└── SessionMiner               # Unified facade combining all capabilities
```

### 2.2 New MCP Tools (8 new tools)

| Tool | Purpose | Key Improvement |
|------|---------|-----------------|
| `windsurf.export_all` | Bulk export all sessions via API or .pb fallback | **API method**: bypasses encryption, gets full transcripts, structured steps |
| `windsurf.ingest` | Parse + ingest sessions into sessions galaxy | **Turn classification**: decision/breakthrough/error/code_change with importance scoring |
| `windsurf.sync` | Incremental export + ingest of new/changed sessions only | **Dedup + diff**: compares against last export, only processes new content |
| `windsurf.mine` | Cross-session pattern mining | **NEW**: extracts decisions, breakthroughs, recurring errors, topic clusters across all sessions |
| `windsurf.categorize` | Auto-categorize sessions by topic | **Galaxy routing**: maps sessions to appropriate galaxies (codex, research, journals) |
| `windsurf.full_steps` | Fetch complete step data for a single session | **Bypasses 200K truncation**: paginated API call for full step-by-step data |
| `windsurf.compare` | Compare exports across dates | **Diff detection**: new, changed, missing sessions with content hash |
| `windsurf.semantic_search` | Semantic search across all conversations | **HNSW + FTS5**: uses existing embedding index for meaning-based search |

### 2.3 Upgrade Existing Tools

| Tool | Upgrade |
|------|---------|
| `windsurf_list_conversations` | Add API method: if language server is running, use `GetAllCascadeTrajectories` for richer metadata (titles, step counts, user inputs, status). Fall back to .pb file listing. |
| `windsurf_read_conversation` | Add API method: use `GetCascadeTranscriptForTrajectoryId` for decrypted transcript. Fall back to .pb parser. Return structured turns, not raw text blobs. |
| `windsurf_search_conversations` | Use FTS5 on ingested sessions galaxy for search. Fall back to in-memory keyword search if not ingested. |
| `windsurf_stats` | Include API availability, ingestion status, galaxy memory count, last sync date. |

---

## 3. Implementation Plan

### Phase 1: Core Module + API Client (1 session)

**Create `archaeology/session_miner.py`** with:

1. **`LanguageServerClient`** class:
   - `find_server()` — scan `/proc` for language server PID
   - `get_csrf_token(pid)` — extract from environ
   - `find_grpc_port(pid, csrf)` — find listening port
   - `get_all_trajectories()` — session list + user inputs
   - `get_transcript(cascade_id)` — full transcript text
   - `get_all_steps(cascade_id)` — paginated step data (bypasses truncation)
   - `is_available()` — quick check if API is accessible
   - All methods use `urllib.request` (no external deps, consistent with existing code)

2. **`ProtobufFallback`** class:
   - Reuse existing `parse_protobuf_simple()` from `windsurf_reader.py`
   - Add `extract_messages()` with better role detection from `export_all_conversations.py`
   - Add `categorize()` from `organize_all.py`

3. **`TranscriptParser`** class:
   - `parse_transcript(content)` — regex-based turn parsing from `ingest_transcripts.py`
   - `parse_step_json(filepath)` — structured step data parsing
   - `classify_turn_type(content, role)` — heuristic classification
   - `score_importance(content, role, turn_type)` — importance scoring
   - `extract_decisions(turns)` — filter to decision-type turns
   - `extract_breakthroughs(turns)` — filter to breakthrough-type turns

### Phase 2: Ingestion + Sync (1 session)

4. **`SessionIngestor`** class:
   - `ingest_session(session_id, title, turns)` — uses `SessionRecorder`, handles dedup
   - `ingest_from_export(export_dir)` — bulk ingest from export directory
   - `ingest_incremental(export_dir)` — only new/changed sessions (uses `ExportComparator`)
   - `get_ingestion_status()` — which sessions are ingested, turn counts, last sync
   - Uses `safe_connect()` for any direct DB access (per AGENTS.md rule)

5. **`ExportComparator`** class:
   - `compare(new_dir, old_dirs)` — diff across exports
   - `find_new_sessions()` — sessions not in any previous export
   - `find_changed_sessions()` — same ID, different content hash
   - `find_missing_sessions()` — in old but not new

6. **`SessionMiner`** facade class:
   - `export(output_dir, full_steps=False)` — auto-detect API vs fallback
   - `ingest(export_dir=None, incremental=True)` — export + ingest in one call
   - `sync()` — full pipeline: export → compare → ingest new/changed → report
   - `stats()` — unified stats across all subsystems

### Phase 3: MCP Tool Wiring (1 session)

7. **Handler functions** in `windsurf_conv.py` (extend existing file):
   - `handle_windsurf_export_all` — calls `SessionMiner.export()`
   - `handle_windsurf_ingest` — calls `SessionMiner.ingest()`
   - `handle_windsurf_sync` — calls `SessionMiner.sync()`
   - `handle_windsurf_mine` — calls `PatternMiner.mine()`
   - `handle_windsurf_categorize` — calls `SessionMiner.categorize()`
   - `handle_windsurf_full_steps` — calls `LanguageServerClient.get_all_steps()`
   - `handle_windsurf_compare` — calls `ExportComparator.compare()`
   - `handle_windsurf_semantic_search` — uses galaxy search + HNSW

8. **Registry definitions** in `archaeology.py`:
   - Add 8 new `ToolDefinition` entries with proper schemas
   - All under `ToolCategory.ARCHAEOLOGY`, `ToolSafety.READ` (except ingest = `WRITE`)

9. **Dispatch table** in `dispatch_table.py`:
   - Add 8 new `LazyHandler` entries

10. **PRAT mappings** in `prat_mappings.py`:
    - Map all 8 new tools to `gana_chariot`

11. **NLU patterns** in `meta_tool.py`:
    - Add regex patterns for natural language routing

12. **Upgrade existing handlers** to use `SessionMiner` when API is available

### Phase 4: Pattern Mining (1 session)

13. **`PatternMiner`** class in `session_miner.py`:
    - `mine_decisions(session_ids)` — extract all decision-type turns across sessions
    - `mine_breakthroughs(session_ids)` — extract breakthrough turns
    - `mine_errors(session_ids)` — extract error turns, group by error type
    - `mine_topics(session_ids)` — cluster sessions by topic similarity
    - `mine_recurring_patterns()` — find repeated code patterns, tool usage patterns
    - `mine_directives()` — extract user directives (imperative statements)
    - `create_codex_memories()` — persist mined patterns to codex galaxy
    - `create_cross_references()` — link related sessions via galaxy associations

---

## 4. Key Improvements Over Standalone Scripts

### 4.1 Unified Pipeline
- **Before**: 3 separate scripts (`windsurf_api_export.py` → `ingest_transcripts.py` → manual review)
- **After**: Single `windsurf.sync` MCP tool call handles export → compare → ingest → mine

### 4.2 Auto-Method Selection
- **Before**: Must manually run API export script when Windsurf is running, or fall back to .pb parsing
- **After**: `SessionMiner` auto-detects running language server, uses API when available, falls back to .pb parsing automatically

### 4.3 Incremental Sync
- **Before**: Must re-export and re-ingest everything each time
- **After**: `windsurf.sync` compares against previous exports, only processes new/changed sessions

### 4.4 Structured Turn Output
- **Before**: `windsurf_read_conversation` returns raw text blobs with heuristic role alternation
- **After**: Returns structured turns with classified types (decision, breakthrough, error, code_change), importance scores, and proper role detection

### 4.5 Galaxy Integration
- **Before**: Ingestion writes to sessions galaxy only, no cross-galaxy routing
- **After**: Auto-categorization routes content to appropriate galaxies:
  - Decisions → `codex` galaxy (for cross-session intention tracking)
  - Breakthroughs → `codex` galaxy (for learning)
  - Errors → `codex` galaxy (for debugging patterns)
  - Research topics → `research` galaxy
  - Personal/reflection → `journals` galaxy
  - Everything → `sessions` galaxy (chronological record)

### 4.6 Semantic Search
- **Before**: Keyword-only search across .pb files (slow, limited)
- **After**: `windsurf.semantic_search` uses HNSW embeddings + FTS5 on ingested sessions for meaning-based search

### 4.7 Pattern Mining
- **Before**: No cross-session analysis
- **After**: `windsurf.mine` extracts:
  - All decisions ever made (with context + outcome)
  - All breakthroughs (with the insight that led to them)
  - Recurring error patterns (for debugging)
  - Topic clusters (for knowledge mapping)
  - User directive patterns (for understanding working style)

### 4.8 MCP-Native
- **Before**: Scripts must be run manually from terminal
- **After**: Any AI agent connected to WhiteMagic MCP can export, ingest, search, and mine conversations

---

## 5. Technical Details

### 5.1 Language Server API (from `windsurf_api_export.py`)

```
Service: exa.language_server_pb.LanguageServerService
Base URL: http://127.0.0.1:{port}/exa.language_server_pb.LanguageServerService/
Auth: x-codeium-csrf-token header
Protocol: Connect-protocol gRPC (JSON over HTTP)

Methods:
  GetAllCascadeTrajectories    → {includeUserInputs: true}  → trajectorySummaries, userInputs
  GetCascadeTranscriptForTrajectoryId → {cascadeId: "..."}  → transcript, numTotalSteps
  GetCascadeTrajectorySteps    → {cascadeId: "...", stepOffset: N} → steps[]
```

### 5.2 Turn Classification Heuristics (from `ingest_transcripts.py`)

| Type | Keywords | Role Constraint |
|------|----------|-----------------|
| `decision` | "let's go with", "we should", "I'll implement", "decision:", "the plan is" | Any |
| `breakthrough` | "breakthrough", "eureka", "got it", "solved", "figured out", "the key insight" | Any |
| `error` | "error", "traceback", "exception", "failed", "crash", "segfault" | tool/assistant |
| `code_change` | "def ", "class ", "import ", "```", "edit_file", "write_to_file" | assistant/tool |
| `question` | Ends with "?", or contains "what/how/why/where/when/can you" | user |
| `answer` | Starts with "yes/no/the/this/here", < 500 chars | assistant |
| `summary` | "summary:", "in summary", "to summarize", "overall", "recap:" | Any |
| `context` | Long tool output (> 1000 chars) | tool |
| `message` | Default | Any |

### 5.3 Importance Scoring

```
base = 0.7 (user) | 0.6 (assistant) | 0.3 (tool)
+ 0.3 (decision) | + 0.3 (breakthrough) | + 0.2 (summary) | + 0.15 (error)
+ 0.1 (code_change) | + 0.1 (question) | + 0.05 (answer) | - 0.2 (context)
- 0.1 (if < 20 chars or > 5000 chars)
clamped to [0.1, 1.0]
```

### 5.4 Categorization Keywords (from `organize_all.py`)

Sessions are categorized by keyword matching against title + first 20 messages:
- **whitemagic**: whitemagic, holographic, galaxy, dharma, karma, grimoire, gana, prat, zodiac, dream cycle, polyglot, rust, koka, zig, elixir, haskell, julia, mcp, prescience, citta, sensorium, strata, wasm, pwa, etc.
- **system_maintenance**: disk, cleanup, organize, folder, file, export, backup, archive, sync
- **hardware**: hdmi, audio, charging, battery, ssd, screen, power, thermal, cpu
- **games**: game, tremulous, virtualdj, dolphin, emulator, cho-han, hawo, checkers
- **ai_research**: ollama, model, open source model, ai prompting, agent, safety, antigravity, codex, grok, deepseek, glm, claude
- **devin_windsurf**: devin, windsurf, cascade, extension, vscode, theme, crash, performance

### 5.5 Export Comparison Logic

```python
# From compare_exports.py
brand_new = new_ids - all_old_ids           # Never seen before
changed = [cid for cid in (new_ids & old_ids) if hash differs]  # Content changed
missing = all_old_ids - new_ids             # In old but not new (deleted?)
```

---

## 6. File Changes Summary

### New Files
- `core/whitemagic/archaeology/session_miner.py` — Unified session mining module (~600 lines)

### Modified Files
- `core/whitemagic/archaeology/windsurf_reader.py` — Upgrade to use API when available
- `core/whitemagic/tools/handlers/windsurf_conv.py` — Add 8 new handler functions
- `core/whitemagic/tools/registry_defs/archaeology.py` — Add 8 new tool definitions
- `core/whitemagic/tools/dispatch_table.py` — Add 8 new dispatch entries
- `core/whitemagic/tools/prat_mappings.py` — Map 8 new tools to `gana_chariot`
- `core/whitemagic/tools/handlers/meta_tool.py` — Add NLU patterns for new tools
- `core/whitemagic/tools/tool_catalog.py` — Update `gana_chariot` description

### Test File
- `core/tests/unit/test_session_miner.py` — Unit tests for all new classes

---

## 7. Priority Order

1. **Phase 1** (Critical): `LanguageServerClient` + `TranscriptParser` — enables API-based export as MCP tool
2. **Phase 2** (High): `SessionIngestor` + `ExportComparator` — enables incremental sync
3. **Phase 3** (High): MCP tool wiring — makes everything callable
4. **Phase 4** (Medium): `PatternMiner` — cross-session analysis and codex galaxy enrichment

---

## 8. Polyglot Acceleration Strategy

### 8.1 Why Rust (PyO3) Is the Clear Choice

WhiteMagic's Rust crate (`whitemagic-rust/`) is the only polyglot language with **compiled, working PyO3 bindings** — the others (Zig, Go, Elixir, Julia, Koka, Haskell) are either stubs or subprocess bridges with FFI overhead.

**Existing Rust infrastructure we can leverage directly:**

| Module | Function | Reuse for WindsurfRips |
|--------|----------|----------------------|
| `file_ops.rs` | `read_file_fast()`, `read_files_fast()` | Batch-read .pb files |
| `search/keyword_extract.rs` | `extract_keywords()` | Turn classification keyword matching |
| `ingest_windsurf.rs` (binary) | `batch_ingest()`, `content_hash()` | SQLite batch ingestion pattern (upgrade from placeholder) |
| `sha2` crate | SHA-256 hashing | Content hashing for dedup |
| `rayon` crate | Data parallelism | Parallel .pb parsing, transcript parsing, classification |
| `serde_json` crate | JSON serialization | Export index comparison |
| `regex` crate | Rust regex engine | Transcript turn parsing (10-20x faster than Python `re`) |

### 8.2 Bottleneck Analysis

| Operation | Current (Python) | Bottleneck Type | Rust Speedup |
|-----------|-----------------|-----------------|-------------|
| .pb file parsing | Byte-by-byte varint loop, `data[pos:pos+length]` slicing | CPU-bound, single-threaded | **50-100x** — zero-copy scanning, SIMD UTF-8 validation, rayon parallelism across files |
| Transcript turn parsing | `re.compile()` + line-by-line iteration | CPU-bound | **10-20x** — Rust regex engine, rayon parallelism across sessions |
| Turn type classification | Python keyword lists, `any(kw in content_lower for kw in [...])` | CPU-bound, per-turn | **5-10x** — HashSet lookup, no Python string object overhead |
| HTTP API calls (53 sessions) | Sequential `urllib.request` + `time.sleep(0.1)` | I/O-bound, serialized | **5-10x** — `tokio` + `reqwest` concurrent requests (all 53 in parallel) |
| Content hashing (SHA-256) | Python `hashlib` per file | CPU-bound | **10-20x** — `sha2` crate with rayon |
| Category keyword matching | Python `for kw in keywords: if kw in combined` | CPU-bound | **5-10x** — HashSet-based Aho-Corasick matching |
| SQLite batch ingestion | Python `sqlite3` per-turn `INSERT` | I/O-bound, per-row | **10-50x** — batch transaction, WAL mode, prepared statements |
| Export comparison | Python JSON load + dict comparison | CPU-bound | **3-5x** — `serde_json` deserialization |

### 8.3 Proposed Rust Functions (add to `whitemagic-rust/src/session_miner.rs`)

```rust
// ── Parallel .pb parsing ──────────────────────────────────────────
/// Parse multiple .pb files in parallel using rayon.
/// Returns Vec<ParsedConversation> with extracted text blocks.
/// Uses zero-copy byte scanning + SIMD-accelerated UTF-8 validation.
#[pyfunction]
fn parse_pb_batch(paths: Vec<String>) -> Vec<ParsedConversation>;

// ── Parallel transcript parsing ───────────────────────────────────
/// Parse multiple transcript strings in parallel.
/// Uses Rust regex engine for turn header matching.
/// Returns Vec<Vec<Turn>> — one Vec<Turn> per transcript.
#[pyfunction]
fn parse_transcripts_batch(contents: Vec<String>) -> Vec<Vec<Turn>>;

// ── Batch turn classification ─────────────────────────────────────
/// Classify turn types for all turns across all sessions.
/// Uses HashSet-based keyword lookup (O(1) per keyword).
/// Returns Vec<Vec<ClassifiedTurn>> with type + importance score.
#[pyfunction]
fn classify_turns_batch(turns: Vec<Vec<Turn>>) -> Vec<Vec<ClassifiedTurn>>;

// ── Batch categorization ──────────────────────────────────────────
/// Categorize sessions by topic using Aho-Corasick keyword matching.
/// Returns Vec<String> — category per session.
#[pyfunction]
fn categorize_sessions_batch(titles: Vec<String>, previews: Vec<String>) -> Vec<String>;

// ── Parallel content hashing ──────────────────────────────────────
/// Compute SHA-256 hashes for multiple transcripts in parallel.
/// Returns Vec<String> — hex digest per transcript.
#[pyfunction]
fn hash_transcripts_batch(contents: Vec<String>) -> Vec<String>;

// ── Concurrent HTTP API export ─────────────────────────────────────
/// Fetch all transcripts from language server API concurrently.
/// Uses tokio + reqwest for parallel HTTP requests.
/// Returns Vec<TranscriptResult> — one per cascade_id.
#[pyfunction]
fn fetch_transcripts_concurrent(
    port: u16,
    csrf: String,
    cascade_ids: Vec<String>,
) -> Vec<TranscriptResult>;

// ── Batch SQLite ingestion ────────────────────────────────────────
/// Batch ingest memories into sessions galaxy SQLite DB.
/// Uses WAL mode, prepared statements, single transaction.
/// Returns IngestResult { inserted, skipped, elapsed_ms }.
#[pyfunction]
fn batch_ingest_sessions(
    db_path: String,
    sessions: Vec<SessionMemories>,
) -> IngestResult;
```

### 8.4 Architecture: Hybrid Rust + Python

```
┌─────────────────────────────────────────────────────────┐
│                    MCP Tool Call                         │
│              windsurf.sync / windsurf.ingest             │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│              SessionMiner (Python)                       │
│  ┌─────────────────────────────────────────────────┐    │
│  │ 1. LanguageServerClient.is_available()           │    │
│  │    └─ Python: scan /proc for PID + CSRF          │    │
│  │ 2. Export method selection                       │    │
│  └────────┬──────────────────┬──────────────────────┘    │
│           │ API available    │ API unavailable            │
│           ▼                  ▼                            │
│  ┌────────────────┐  ┌──────────────────┐                │
│  │ Rust: fetch_   │  │ Rust: parse_     │                │
│  │ transcripts_   │  │ pb_batch()       │                │
│  │ concurrent()   │  │ (50-100x faster) │                │
│  │ (5-10x faster) │  │                  │                │
│  └────────┬───────┘  └────────┬─────────┘                │
│           │                   │                           │
│           ▼                   ▼                           │
│  ┌──────────────────────────────────────────┐            │
│  │ Rust: parse_transcripts_batch()           │            │
│  │ Rust: classify_turns_batch()              │            │
│  │ Rust: categorize_sessions_batch()         │            │
│  │ Rust: hash_transcripts_batch()            │            │
│  │ (all parallel via rayon)                  │            │
│  └────────────────────┬─────────────────────┘            │
│                       │                                  │
│  ┌────────────────────▼─────────────────────┐            │
│  │ Python: SessionRecorder.record_user/ai   │            │
│  │ (galaxy ingestion — needs Python ecosystem)│           │
│  └──────────────────────────────────────────┘            │
└─────────────────────────────────────────────────────────┘
```

**Key principle**: Rust handles all CPU-bound and I/O-bound batch operations. Python handles galaxy ingestion (which requires `SessionRecorder`, `GalaxyAwareBackend`, HNSW embeddings — the Python ecosystem).

### 8.5 Expected Performance Gains

**Current pipeline** (53 sessions, ~4MB):
- `windsurf_api_export.py`: ~60s (sequential HTTP + sleep)
- `ingest_transcripts.py`: ~120s (Python parsing + per-turn SQLite insert)
- `compare_exports.py`: ~5s
- **Total**: ~185s

**With Rust acceleration**:
- `fetch_transcripts_concurrent()`: ~6s (53 concurrent HTTP requests)
- `parse_transcripts_batch()` + `classify_turns_batch()`: ~2s (rayon parallelism)
- `batch_ingest_sessions()`: ~3s (batch transaction, WAL mode)
- Export comparison: ~1s
- **Total**: ~12s (**~15x speedup**)

**For .pb fallback path** (no API):
- Current: ~90s (Python varint parser, single-threaded)
- Rust: ~1s (`parse_pb_batch()` with rayon + zero-copy)
- **~90x speedup** on parsing alone

### 8.6 Token Efficiency Gains

The Rust acceleration doesn't just speed up processing — it **reduces token consumption** for AI agents using the MCP tools:

1. **No LLM needed for classification** — Turn type classification (decision, breakthrough, error) is done in Rust with HashSet keyword matching, not by asking an LLM to analyze each turn
2. **No LLM needed for categorization** — Session categorization (whitemagic, games, hardware) is done in Rust with Aho-Corasick matching
3. **Structured output** — Rust returns properly typed `Turn` and `ClassifiedTurn` structs, so the agent doesn't need to parse raw text to understand what happened in a session
4. **Pattern mining without LLM** — `PatternMiner` can extract all decisions/breakthroughs across 53 sessions in <1s using Rust, vs. requiring an LLM to read through 4MB of transcripts
5. **Incremental sync** — Only new/changed sessions are processed, so repeat syncs process 1-3 sessions instead of 53

**Estimated token savings per sync**: ~50K-100K tokens (vs. asking an LLM to read and classify all transcripts)

### 8.7 Implementation Approach

**New file**: `core/whitemagic-rust/src/session_miner.rs`

1. Define `ParsedConversation`, `Turn`, `ClassifiedTurn`, `SessionMemories`, `IngestResult` structs with `#[pyclass]`
2. Implement `parse_pb_batch()` — rayon-parallel protobuf scanning with SIMD UTF-8 validation
3. Implement `parse_transcripts_batch()` — rayon-parallel regex-based turn parsing
4. Implement `classify_turns_batch()` — HashSet keyword matching for turn types
5. Implement `categorize_sessions_batch()` — Aho-Corasick multi-pattern matching
6. Implement `hash_transcripts_batch()` — parallel SHA-256
7. Implement `fetch_transcripts_concurrent()` — tokio + reqwest concurrent HTTP
8. Implement `batch_ingest_sessions()` — batch SQLite with WAL mode (upgrade from `ingest_windsurf.rs` placeholder)
9. Register all functions in `lib.rs` `#[pymodule]`

**Python side**: `SessionMiner` class calls `whitemagic_rs.*` functions, falls back to Python implementations if Rust module not available.

### 8.8 Why Not Other Polyglot Languages?

| Language | Why Not |
|----------|---------|
| **Zig** | FFI stubs only (`zig_ffi.rs` — all functions return `None`/`0`/`false`). No compiled Zig library available. |
| **Go** | Used for P2P mesh networking, not data processing. Subprocess bridge overhead would negate speed gains. |
| **Elixir** | Bridge returns `{"status": "fallback"}`. BEAM VM is great for concurrency but bad for CPU-bound parsing. |
| **Julia** | Bridge returns `{"status": "fallback"}`. Julia's strength is numerical computing, not text parsing. |
| **Koka** | Effect-typed functional language for compile-time verification, not runtime performance. |
| **Haskell** | Subprocess bridge with 5s timeout. Good for pure computation but FFI overhead is too high. |

**Rust via PyO3 is the only viable option** — it's already compiled, already has the infrastructure (file I/O, search, hashing, SQLite), and PyO3 eliminates marshaling overhead by borrowing strings directly from Python.

---

## 9. Risk Assessment

- **Language server not running**: Handled by auto-fallback to .pb parsing
- **API changes**: gRPC endpoints are stable (unchanged across 6+ export dates from Jul 2 to Jul 13)
- **CSRF token rotation**: Token is read fresh from `/proc/PID/environ` each time, no caching
- **Large session counts**: 53+ sessions, ~4MB total — manageable in memory
- **Truncation**: `GetCascadeTrajectorySteps` with pagination bypasses 200K limit
- **Dedup**: Content hash + session ID comparison prevents duplicate ingestion

---

## 10. Absolute Clarity Recipe

**Goal**: Give an AI agent complete project context — every decision, breakthrough, error, and pattern across all sessions — in under 5 seconds, zero tokens burned on retrieval.

### The Prompt (copy-paste into a fresh agent session)

```
You are gaining absolute clarity on the WhiteMagic project. Execute these steps in order:

STEP 1 — INGEST (one call, ~2s, zero tokens):
  Call: windsurf.sync
  This exports all sessions, compares with previous exports, and ingests only new/changed ones.

STEP 2 — MINE (one call, ~2s, zero tokens):
  Call: windsurf.mine
  This runs all 13 mining operations across every session:
    - All decisions ever made (keyword-detected)
    - All breakthroughs ("eureka", "solved", "that's it")
    - All errors grouped by type + recurring error fingerprints
    - Cross-session associations (decision → breakthrough chains)
    - Decision outcome tracking (led_to_breakthrough / led_to_error / unknown)
    - Topic co-occurrence matrix
    - Session similarity pairs (Jaccard keyword overlap)
    - Technology evolution timeline (40+ tracked technologies)
    - Emotional arc shapes per session (struggle_to_success, smooth_progress, etc.)
    - User directive taxonomy (build / fix / explore / decide / verify / refactor)
    - Topic clusters by category

STEP 3 — READ THE OUTPUT:
  The mine() result contains everything you need. Key sections:
    - decision_outcomes.decisions — every decision + whether it worked
    - associations.chains — decision→breakthrough links across sessions
    - recurring_errors.recurring — errors that keep happening
    - tech_timeline.timeline — which technologies are used most
    - emotional_arcs.shape_distribution — project emotional health
    - directive_taxonomy.distribution — build vs fix vs explore ratio

STEP 4 — DRILL DOWN (optional, per-topic):
  Call: windsurf.semantic_search with query="specific topic you want details on"
  This uses HNSW + FTS5 to find relevant turns across all sessions.

DO NOT read session transcripts directly. DO NOT use session.recall until you know what you're looking for. The mining output IS the clarity — it distills 50+ sessions into decisions, outcomes, and patterns.
```

### Why This Works

| Concern | Answer |
|---------|--------|
| Token cost | Zero on retrieval — all mining is Python heuristics |
| Time | ~5 seconds for 50+ sessions (sync + mine) |
| Completeness | Every decision, breakthrough, error, and directive is extracted |
| Signal-to-noise | Low-importance tool outputs and context dumps are filtered out |
| Cross-session insight | Association chains link decisions in one session to breakthroughs in another |
| Outcome tracking | You learn not just what was decided, but whether it worked |
| Pattern detection | Recurring errors reveal systemic issues; emotional arcs reveal project health |

### What the Agent Learns

After Steps 1-3, the agent knows:
- **Every decision** made in the project and its outcome
- **Every breakthrough** and which decision led to it
- **Every recurring error** and how many times it appeared
- **Which technologies** are used most and in which sessions
- **The emotional arc** of the project (mostly struggle_to_success = healthy)
- **The work ratio** (build vs fix vs explore vs verify)
- **Which sessions are similar** (for finding related work)
- **Which topics co-occur** (for understanding architecture)

### Files to Reference

- `core/whitemagic/archaeology/session_miner.py` — SessionMiner facade + all 7 classes
- `core/whitemagic/tools/handlers/windsurf_conv.py` — MCP tool handlers
- `core/tests/unit/test_session_miner.py` — 77 tests covering all functionality
