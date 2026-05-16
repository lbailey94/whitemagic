# CODEX Master Plan
## Semantic Knowledge Extraction & Vaya Vida Integration

**Version:** 0.1.0  
**Date:** April 20, 2026  
**Status:** Phase 0 - Foundation

---

## Executive Summary

This document outlines the complete architecture and implementation plan for **CODEX**: a Rust-based semantic knowledge extraction pipeline that consolidates three major research corpora (LIBRARY, OPENAI archives, RESEARCH) into a unified, queryable, and visualizable knowledge system integrated with the Vaya Vida technospiritual research portal.

### Scope
- **Input:** ~27,400 files, ~19 GB of research data
- **Processing:** Full semantic extraction, hierarchical chunking, multimodal image analysis, vector embeddings
- **Output:** Queryable knowledge graph, Vaya Vida sphere integration (~200 new nodes)

---

## Phase Overview

### Phase 0: Foundation (Current)
- [x] Master project folder structure
- [x] Rust workspace scaffolding
- [x] Configuration schema
- [ ] Symlink verification
- [ ] Initial crate implementations
- [ ] CLI command stubs

### Phase 1: Extraction Engine
- File system walker with async I/O
- Text normalization (encoding detection → UTF-8)
- Markdown frontmatter parsing
- Conversation thread reconstruction
- **Image pipeline:** OCR + multimodal API extraction

### Phase 2: Semantic Chunking
- Hierarchical chunking (paragraph/section/document levels)
- Token-accurate boundaries using tiktoken
- Conversation-aware splitting (preserve speaker context)
- Overlap handling for continuity

### Phase 3: Embedding Generation
- API-based: OpenAI `text-embedding-3-large` (3072D) or Anthropic
- Rate limiting and retry logic
- Batch processing with checkpointing
- Optional: Local ONNX/Candle fallback

### Phase 4: Index Construction
- In-memory graph (petgraph)
- Vector similarity index (HNSW or flat)
- Tag-based clustering (Louvain algorithm)
- Cross-reference edges (cosine similarity > 0.85)

### Phase 5: Vaya Vida Export
- Sphere node generation (Fibonacci coordinates)
- Category-based visual styling
- Connection thread calculation
- JSON manifest for direct integration

---

## Architecture

### Workspace Structure

```
codex/
├── Cargo.toml                    # Workspace manifest
├── src/main.rs                   # CLI entry point
├── crates/
│   ├── codex-core/              # Shared types, config, errors
│   ├── codex-extract/           # File ingestion
│   ├── codex-chunk/             # Semantic chunking
│   ├── codex-embed/             # Vector generation
│   ├── codex-index/             # Graph + vector index
│   └── codex-export/            # Output formatters
├── config/
│   ├── codex.yaml               # Production config
│   └── codex.example.yaml       # Template
├── 00_source/                   # Symlinks to source data
│   ├── library/ → ~/Desktop/LIBRARY
│   ├── conversations/ → ~/Desktop/OPENAI archives
│   └── research/ → ~/Desktop/RESEARCH
├── 10_extracted/                # Normalized JSONL
├── 20_chunks/                   # Semantic chunks
├── 30_embeddings/             # Vector arrays (.npy/.parquet)
├── 40_index/                    # Graph database + manifests
├── 50_export/                   # Final outputs
└── docs/
    └── PLAN.md                  # This document
```

### Data Flow

```
00_source/          →  10_extracted/        →  20_chunks/
[Raw files]            [Normalized JSONL]      [Chunked JSONL]
     ↓                       ↓                       ↓
  walker                 parser                  splitter
  encoding               frontmatter             tokenizer
  image OCR              text normalization      hierarchy builder

20_chunks/          →  30_embeddings/       →  40_index/
[Chunked JSONL]         [Vector arrays]          [Graph + Index]
     ↓                       ↓                       ↓
  batcher                embedder                similarity calc
  rate limiter           API client              edge builder
  checkpoint             local fallback          tag clusterer

40_index/           →  50_export/
[Graph + Index]          [Output formats]
     ↓                       ↓
  query engine           Vaya Vida JSON
  traversal              Markdown corpus
                         YAML manifest
```

---

## Source Analysis

### LIBRARY (33 MB, ~400 files)
**Structure:** 8 categorized domains + loose files

| Domain | Files | Focus |
|--------|-------|-------|
| 1_CONSCIOUSNESS | 15 | Meditation, cyberbrains, psi, brainwaves |
| 2_SPIRITUALITY | 19 | Sufism, bhakti, tathagata, mahamudra |
| 3_GOVERNANCE | 15 | Game theory, UBI, world constitution, geopolitics |
| 4_TECHNOLOGY | 17 | AI habitats, droids, datacenters, edge AI |
| 5_SPACE | 7 | Astra system, interstellar, habitats |
| 6_ECONOMICS | 4 | Currency, automation, fairness |
| 7_AI_EMERGENCE | 12 | Alignment, superintelligence, control |
| 8_PROJECTS | 10 | Modular designs, synapse suite |
| Loose files | ~300 | Cross-cutting research |

**Processing notes:**
- Many files have Tibetan/Japanese/Arabic characters → UTF-8 normalization critical
- Mix of `.txt` and `.md` formats
- Some files are large (~2MB for `---NewSpirit.txt`)

### OPENAI Archives (1.1 GB, ~650 files)
**Structure:** Already parsed to markdown

| Folder | Content |
|--------|---------|
| REORGANIZED_RESULTS/consolidated/ | Clean conversation data |
| SOURCE_DATA/_PARSED_MARKDOWN/2025/ | Chronological by month |
| ANALYSIS/ | Pre-generated reports |

**Stats:**
- 219 conversations (May-Dec 2025)
- Average: 42K chars per conversation
- Peak: June (92 convos), Longest: July (avg 69.5K chars)

**Processing notes:**
- Preserve conversation structure (speaker turns)
- Chronological clustering potential
- Concept genealogy already partially analyzed

### RESEARCH (18 GB, ~26K files)
**Structure:** Primarily images + `subjects/` folder

| Folder | Content |
|--------|---------|
| subjects/ | 20 research domains (markdown notes) |
| twitter-*/ | ~8K folders of tweet media (images) |
| twitter*.zip | 5.2 GB compressed archive |

**Processing notes:**
- **Challenge:** 18GB is mostly Twitter media
- **Strategy:** Sample/selective processing vs. full ingestion
- Image extraction via multimodal API (Claude/GPT-4V)
- OCR fallback for text-heavy images

---

## Implementation Details

### Crate: codex-core

**Responsibilities:**
- Central types (`Document`, `Chunk`, `EntityId`)
- Configuration structs (YAML → typed config)
- Error taxonomy
- Common utilities

**Key Types:**
```rust
pub struct Document {
    pub id: EntityId,
    pub source_path: PathBuf,
    pub source_type: SourceType,
    pub content: String,
    pub metadata: HashMap<String, Value>,
    pub word_count: usize,
    pub token_count: usize,
}

pub struct Chunk {
    pub id: EntityId,
    pub document_id: EntityId,
    pub content: String,
    pub level: ChunkLevel,  // Paragraph | Section | Document
    pub embedding: Option<Vec<f32>>,
}
```

### Crate: codex-extract

**Responsibilities:**
- Async file system walking (`tokio::fs`)
- Encoding detection (`chardetng`)
- Markdown parsing (`pulldown-cmark`)
- Image processing pipeline

**Image Pipeline:**
```rust
pub async fn extract_image(path: &Path) -> Result<ImageExtraction> {
    // 1. Load and resize
    let img = image::open(path)?;
    let resized = img.resize(2048, 2048, FilterType::Lanczos3);
    
    // 2. OCR pass
    let ocr_text = tesseract::ocr(&resized)?;
    
    // 3. Multimodal API
    let description = anthropic::describe(&resized, PROMPT).await?;
    
    Ok(ImageExtraction { ocr_text, description, concepts })
}
```

### Crate: codex-chunk

**Strategies:**

1. **Paragraph:** Split on `\n\n`, respect 250 token target
2. **Semantic:** Use sentence boundaries + coherence scoring
3. **Hierarchical:** Build tree (paragraphs → sections → documents)
4. **Conversation:** Preserve speaker turns, chunk by message count or token target

**Algorithm:**
```rust
pub fn chunk_hierarchical(doc: &Document) -> Vec<Chunk> {
    // Level 1: Paragraphs
    let paragraphs = split_paragraphs(&doc.content);
    let para_chunks = merge_small_paragraphs(paragraphs, 250);
    
    // Level 2: Sections (markdown headers)
    let sections = group_by_headers(&doc.content);
    let section_chunks = sections.into_iter()
        .map(|s| merge_paragraphs(s, 1000))
        .collect();
    
    // Level 3: Document (if > 4000 tokens, use sections as children)
    vec![para_chunks, section_chunks, doc_chunk]
}
```

### Crate: codex-embed

**Providers:**
- `anthropic`: Claude API for extraction + OpenAI for embeddings
- `openai`: Native text-embedding-3-large
- `local_onnx`: ONNX Runtime with all-MiniLM-L6-v2
- `local_candle`: Candle framework with local models

**Rate Limiting:**
```rust
pub struct RateLimiter {
    rps: f32,
    last_request: Instant,
}

impl RateLimiter {
    pub async fn acquire(&mut self) {
        let delay = Duration::from_secs_f32(1.0 / self.rps);
        let elapsed = self.last_request.elapsed();
        if elapsed < delay {
            sleep(delay - elapsed).await;
        }
        self.last_request = Instant::now();
    }
}
```

### Crate: codex-index

**Graph Structure:**
- Nodes: Documents, Chunks, Tags
- Edges: Contains (doc→chunk), Similar (cosine > 0.85), Tagged (doc→tag)

**Vector Index:**
- Flat index (exact search) for <100K vectors
- HNSW (approximate) for >100K vectors
- Cosine similarity metric

**Clustering:**
- Louvain algorithm for tag-based communities
- Visual coloring by cluster

### Crate: codex-export

**Vaya Vida Integration:**

Output: `40_index/sphere-nodes-v2.json`

```json
{
  "version": "v5.1.0",
  "nodes": [
    {
      "id": "lib-consciousness-exploration",
      "title": "Consciousness Exploration",
      "type": "library",
      "category": "1_CONSCIOUSNESS",
      "coordinates": {"x": 0.5, "y": -0.3, "z": 0.8},
      "color": "#8b5cf6",
      "char": "◆",
      "word_count": 18485,
      "tags": ["consciousness", "meditation", "cyberbrains"],
      "connections": ["lib-cyberbrains", "note-awareness"]
    }
  ]
}
```

**Coordinate Generation (Fibonacci Sphere):**
```rust
pub fn fibonacci_sphere(n: usize, index: usize, category_offset: f32) -> (f32, f32, f32) {
    let phi = (1.0 + 5.0_f32.sqrt()) / 2.0; // Golden ratio
    let y = 1.0 - (index as f32 / (n as f32 - 1.0)) * 2.0;
    let radius = (1.0 - y * y).sqrt();
    let theta = phi * index as f32 + category_offset;
    
    let x = theta.cos() * radius;
    let z = theta.sin() * radius;
    
    (x, y, z)
}
```

---

## CLI Commands

```bash
# Initialize project
codex init my-codex

# Extract all sources
codex extract --source all --force

# Chunk with hierarchical strategy
codex chunk --strategy hierarchical --level all

# Generate embeddings
codex embed --provider anthropic --resume

# Build indices
codex index --rebuild

# Export to Vaya Vida
codex export --format vaya-vida --output 50_export/

# Full pipeline
codex build --from extract --to export

# Query the corpus
codex query "consciousness and AI alignment" --semantic --limit 20

# Development server
codex serve --bind 127.0.0.1:8080
```

---

## Performance Targets

| Metric | Target | Rationale |
|--------|--------|-----------|
| Extraction throughput | 10K files/sec | `tokio` async I/O |
| Chunking throughput | 1M tokens/sec | `rayon` parallelism |
| Embedding rate | 100 req/sec | API rate limit ceiling |
| Index build | <5 min | In-memory graph |
| Total pipeline | <2 hours | ~19GB corpus |
| Memory usage | <8GB peak | Streaming processing |

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| API rate limits | Exponential backoff, checkpointing, local fallback |
| Image processing cost | Batch processing, selective sampling |
| Encoding issues | chardetng + manual override list |
| Memory exhaustion | Streaming JSONL, batched operations |
| Data loss | Immutable stages, checksums, git LFS |

---

## Vaya Vida Integration Plan

### New Sphere Categories

1. **Library Nodes** (Purple ◆)
   - 8 domains → 8 clusters on sphere
   - ~150-200 nodes from categorized folders
   - Loose files clustered by semantic similarity

2. **Conversation Nodes** (Cyan ◇)
   - Monthly clusters (May-Dec 2025)
   - Topic-based sub-clustering
   - ~50-100 representative nodes

3. **Research Nodes** (Amber ○)
   - `subjects/` folder → 20 nodes
   - Image extractions → visual knowledge nodes
   - Twitter insights (if sampled) → trend nodes

### Visual Design

```
Sphere v5.1.0:
├── Existing 40 nodes (maintained)
├── Library layer (150 nodes, violet)
│   └── 8 domain clusters (Fibonacci banding)
├── Conversation layer (50 nodes, cyan)
│   └── Chronological spiral
└── Research layer (30 nodes, amber)
    └── Image-derived concepts
```

### Connection Strategy

- **Within-category:** Geodesic proximity on sphere surface
- **Cross-category:** Semantic similarity edges (>0.90 cosine)
- **To existing 40:** Manual curation of key connections

---

## Next Steps

1. **Verify folder structure:**
   ```bash
   cd /home/lucas/Desktop/CODEX
   ls -la 00_source/
   ```

2. **Test Rust build:**
   ```bash
   cargo check
   cargo build --release
   ```

3. **Configure API keys:**
   ```bash
   export ANTHROPIC_API_KEY="..."
   export OPENAI_API_KEY="..."
   ```

4. **Dry run extraction:**
   ```bash
   codex extract --source library --dry-run
   ```

5. **Iterative development:**
   - Start with LIBRARY only (~400 files)
   - Add conversations
   - Handle RESEARCH images last

---

## Appendix: File Inventory

### LIBRARY Top Files by Size
| File | Size | Domain |
|------|------|--------|
| ---NewSpirit.txt | 2.0 MB | Spirituality |
| solarpunk.txt | 183 KB | Tech/Future |
| kali.txt | 148 KB | Spirituality |
| newsociety.txt | 364 KB | Governance |
| ---NewSociety.txt | 437 KB | Governance |

### OPENAI Archives Key Folders
- `REORGANIZED_RESULTS/consolidated/openai5/` (64 MB)
- `REORGANIZED_RESULTS/consolidated/openaiconvos/` (897 MB)
- `SOURCE_DATA/_PARSED_MARKDOWN/2025/` (9.5 MB)

### RESEARCH Subjects (Active)
- `sacred-geometry/` (4 items)
- `lostciv/` (3 items)
- `spirituality & healing/` (3 items)
- `earth/` (3 items)
- `magic & the occult/` (1 item)
- `philosophy/` (1 item)

---

**Document Version:** 0.1.0  
**Last Updated:** 2026-04-20  
**Author:** Lucas + Cascade
