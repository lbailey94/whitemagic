# CODEX

**Semantic Knowledge Extraction Pipeline for the Vaya Vida Research Portal**

A high-performance Rust-based system for consolidating, chunking, embedding, and visualizing large research corpora.

---

## Quick Start

```bash
# Build the project
cargo build --release

# Set API keys (for multimodal/embedding)
export ANTHROPIC_API_KEY="your-key"
export OPENAI_API_KEY="your-key"

# Run full pipeline
cargo run --release -- build

# Or step by step
codex extract --source library
codex chunk --strategy hierarchical
codex embed --provider anthropic
codex index
codex export --format vaya-vida
```

---

## Project Structure

```
codex/
├── 00_source/          # Symlinks to source data (LIBRARY, OPENAI, RESEARCH)
├── 10_extracted/       # Normalized JSONL
├── 20_chunks/          # Semantic chunks
├── 30_embeddings/      # Vector arrays
├── 40_index/           # Graph database + manifests
├── 50_export/          # Final outputs for Vaya Vida
├── crates/             # Rust workspace
│   ├── codex-core/     # Types, config, errors
│   ├── codex-extract/  # File ingestion
│   ├── codex-chunk/    # Semantic chunking
│   ├── codex-embed/    # Vector generation
│   ├── codex-index/    # Graph + vector index
│   └── codex-export/   # Output formatters
├── config/
│   └── codex.yaml      # Pipeline configuration
└── docs/
    └── PLAN.md         # Comprehensive architecture plan
```

---

## Data Sources

| Source | Files | Size | Status |
|--------|-------|------|--------|
| LIBRARY | ~723 | 33 MB | ✅ Ready |
| OPENAI Archives | ~649 | 1.1 GB | ✅ Parsed to markdown |
| RESEARCH | ~26,000 | 18 GB | ⚠️ Mostly images (selective processing) |

---

## Features

- **Async I/O:** Process 10K+ files/second with Tokio
- **Semantic Chunking:** Hierarchical (paragraph/section/document) or conversation-aware
- **Multimodal Extraction:** OCR + Claude/GPT-4V for image analysis
- **Vector Embeddings:** OpenAI, Anthropic, or local ONNX/Candle
- **Graph Index:** In-memory or SurrealDB with similarity-based edges
- **Vaya Vida Export:** Direct sphere node generation with Fibonacci coordinates

---

## Configuration

Edit `config/codex.yaml`:

```yaml
project:
  name: "Lucas Research Codex"

extraction:
  image_processing:
    enabled: true
    multimodal_api: "anthropic"

chunking:
  strategy: hierarchical
  paragraph_target_tokens: 250

embedding:
  provider: anthropic
  dimensions: 3072

export:
  vaya_vida:
    enabled: true
    max_nodes: 200
```

---

## Documentation

- [Master Plan](docs/PLAN.md) - Full architecture and phase breakdown
- `cargo run -- --help` - CLI reference

---

## Performance

| Stage | Throughput |
|-------|------------|
| Extraction | 10K files/sec |
| Chunking | 1M tokens/sec |
| Embedding | 100 req/sec (API-limited) |
| Full Pipeline | <2 hours for 19GB corpus |

---

## License

Personal research project. See [docs/PLAN.md](docs/PLAN.md) for full details.
