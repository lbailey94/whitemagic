# CODEX Pipeline v0.2.0 — Specification

**Version:** 0.2.0
**Date:** 2026-05-15
**Status:** Specification — Phase 3 (Obj 12)

---

## 1. Overview

CODEX extracts, chunks, embeds, indexes, and exports knowledge from five source corpora into queryable, graphable artifacts. It bridges the raw content layer (SD card transcripts, LIBRARY documents, essay frameworks) to the interactive surface (Aria backend, semantic search, knowledge sphere).

### Source Corpora (5)

| Corpus | Location | Format | Est. Size |
|--------|----------|--------|-----------|
| SD Card Transcripts | `~/Desktop/whitemagic-aux/archive/` | Text, PDF | 2.2 GB |
| LIBRARY Documents | `~/Desktop/whitemagic-aux/library/` | MD, PDF, TXT | TBD |
| Essay Frameworks | `docs/essay_frameworks/` | MD | 9 files |
| Session Summaries | `docs/message_board/` | MD | ~30 files |
| Message Board Docs | `docs/message_board/` | MD | ~25 files |

---

## 2. Pipeline Stages

### Stage 1: `codex-extract`

**Input:** Raw source files (multiple formats)
**Output:** Normalized `Document` objects

```python
@dataclass
class Document:
    source: str          # Corpus identifier
    path: str            # Original file path
    format: str          # md, txt, pdf, json
    title: str
    body: str            # Full text, UTF-8 normalized
    metadata: dict       # Date, author, epistemic tag, language
    tokens: int          # Token count estimate
```

**Behavior:**
- Parses Markdown, plain text, PDF (via PyMuPDF), JSON
- Preserves frontmatter metadata
- Handles UTF-8 normalization
- Skips binary files and build artifacts
- Respects `.gitignore` patterns for exclusion

**Exit criteria:** All 5 corpora parsed; document count logged.

---

### Stage 2: `codex-chunk`

**Input:** `Document` objects
**Output:** `Chunk` objects (hierarchical)

```python
@dataclass
class Chunk:
    doc_id: str          # Parent document ID
    chunk_index: int     # Position in document
    level: int           # 0 = document, 1 = section, 2 = paragraph
    heading: str         # Section heading (if applicable)
    body: str            # Chunk text
    speaker: str         # Speaker label (transcripts only)
    tokens: int          # Token count
    prev_chunk_id: str   # Previous chunk (preserves narrative flow)
    next_chunk_id: str   # Next chunk
```

**Behavior:**
- Splits by markdown headings → sections → paragraphs
- Preserves speaker-turn attribution for transcripts
- Respects max chunk size (configurable, default 512 tokens)
- Maintains `prev_chunk_id` / `next_chunk_id` for narrative continuity

**Exit criteria:** All documents chunked; chunk count logged.

---

### Stage 3: `codex-embed`

**Input:** `Chunk` objects
**Output:** Vectors stored in queryable index

**Behavior:**
- Generates embeddings via `sentence-transformers` (all-MiniLM-L6-v2 default)
- Graceful fallback to `whitemagic.core.embeddings` if transformers missing
- Stores vectors in Annoy or FAISS index
- Chunk metadata stored in SQLite alongside vectors

**Exit criteria:** All chunks embedded; index file size logged.

---

### Stage 4: `codex-index`

**Input:** Vectors + chunk metadata
**Output:** Graph clusters + `sphere-nodes.json`

**Behavior:**
- Builds similarity graph from vector cosine distances
- Louvain community detection for clustering
- Labels clusters with top TF-IDF terms
- Exports `sphere-nodes.json`:
  ```json
  {
    "nodes": [
      {"id": "cluster_0", "label": "Agent Governance", "size": 42, "epistemic_tag": "Proven"},
      ...
    ],
    "edges": [
      {"source": "cluster_0", "target": "cluster_1", "weight": 0.85},
      ...
    ]
  }
  ```

**Exit criteria:** Graph built; cluster count logged; `sphere-nodes.json` written.

---

### Stage 5: `codex-export`

**Input:** Graph clusters + chunk data
**Output:** Manifest files for downstream consumers

**Outputs:**
- `sphere-nodes.json` — knowledge sphere nodes/edges (consumed by Obj 3, 3D visualization)
- `search-index/` — searchable indices (consumed by Obj 16, semantic search)
- `aria-manifest.json` — Aria backend ingestion manifest (consumed by Obj 18)
- `vaya-vida-manifest.json` — Vaya Vida site content manifest

**Exit criteria:** All artifacts written; manifest validated.

---

## 3. Module Structure

```
core/whitemagic/codex/
├── __init__.py       # Package docstring
├── extract/
│   ├── __init__.py
│   ├── parser.py     # Format-specific parsers (MD, TXT, PDF, JSON)
│   └── corpus.py     # Corpus discovery and enumeration
├── chunk/
│   ├── __init__.py
│   ├── splitter.py   # Hierarchical chunking logic
│   └── speaker.py    # Speaker-turn detection
├── embed/
│   ├── __init__.py
│   ├── encoder.py    # Embedding generation (sentence-transformers)
│   └── store.py      # Vector storage (Annoy / FAISS)
├── index/
│   ├── __init__.py
│   ├── graph.py      # Similarity graph construction
│   ├── cluster.py    # Louvain community detection
│   └── label.py      # Cluster labeling (TF-IDF)
└── export/
    ├── __init__.py
    ├── sphere.py     # sphere-nodes.json generation
    ├── search.py     # Search index export
    └── manifest.py   # Aria + Vaya Vida manifests
```

---

## 4. CLI Interface

```bash
# Full pipeline
codex run --corpora all

# Individual stages
codex extract --corpus sd_card --output /tmp/codex/
codex chunk --input /tmp/codex/documents.jsonl
codex embed --input /tmp/codex/chunks.jsonl --model all-MiniLM-L6-v2
codex index --input /tmp/codex/vectors.ann
codex export --input /tmp/codex/graph.json --output apps/site/public/
```

---

## 5. Epistemic Tag Propagation

Every document, chunk, and cluster carries the epistemic tag from its source. Tags propagate through the pipeline:

```
Document (epistemic_tag: "Proven")
  → Chunks (inherit "Proven")
    → Embeddings (tagged in metadata)
      → Clusters (majority-vote tag)
        → sphere-nodes (tagged)
```

This ensures the knowledge sphere never shows a `[Speculative]` essay as fact.

---

## 6. Dependencies

| Dependency | Purpose | Fallback |
|-----------|---------|----------|
| `sentence-transformers` | Embedding generation | `whitemagic.core.embeddings` (Python) |
| `PyMuPDF` (fitz) | PDF text extraction | Warn and skip |
| `annoy` or `faiss` | Vector similarity search | `scipy.spatial` brute-force |
| `networkx` | Graph construction | Manual adjacency dict |
| `sklearn` | TF-IDF cluster labeling | Simple word frequency |
| `python-louvain` | Community detection | Built-in greedy modularity |

All dependencies are optional. The pipeline degrades gracefully, logging what's missing.

---

## 7. Output Artifacts

| File | Consumer | Purpose |
|------|----------|---------|
| `sphere-nodes.json` | Obj 3 (3D sphere), Obj 6 (v5 migration) | Knowledge sphere visualization |
| `search-index/` | Obj 16 (semantic search) | Hybrid search backend |
| `aria-manifest.json` | Obj 18 (Aria backend) | Document corpus for `/ask`, `/oracle`, `/wander` |
| `vaya-vida-manifest.json` | Obj 5 (content triage) | Content migration manifest |
