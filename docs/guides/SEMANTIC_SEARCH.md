# Semantic Search Guide (v2.2.7)

WhiteMagic ships a hybrid search stack that combines classic keyword filters with embedding-powered semantic ranking. This guide shows how to set it up, run it from the CLI/API/MCP, and interpret the results.

## 1. Requirements

- Python 3.10+
- `pip install "whitemagic[api,dev]"` (installs local embedding dependencies)
- Optional: OpenAI API key (`OPENAI_API_KEY`) if you prefer remote embeddings over the bundled local model.

## 2. One-Time Setup

```bash
# inside your project workspace
whitemagic setup-embeddings
# Choose:
#   1) local (privacy-first, ~90 MB download)
#   2) openai (requires OPENAI_API_KEY)
```

The CLI downloads the SentenceTransformers checkpoint (for local mode) and builds a cache under `~/.whitemagic/embeddings/`.

## 3. Running Searches (CLI)

```bash
# Hybrid (keyword + semantic) – recommended
whitemagic search-semantic "debugging async race conditions"

# Pure semantic
whitemagic search-semantic --mode semantic "rate limit mitigation"

# Keyword-only (legacy)
whitemagic search-semantic --mode keyword --tags "heuristic" "api"

# Limit + JSON output for scripting
whitemagic search-semantic "postmortem" --limit 5 --json
```

Useful flags:

- `--type short_term|long_term`
- `--tags tag1 tag2`
- `--threshold 0.65` (semantic minimum score)
- `--cache-refresh` to rebuild embeddings if files changed.

## 4. API & MCP

### REST API

```bash
curl -X POST https://api.whitemagic.dev/api/v1/search/semantic \
  -H "Authorization: Bearer $WM_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
        "query": "How do I debug race conditions?",
        "mode": "hybrid",
        "k": 10,
        "threshold": 0.7
      }'
```

### MCP Tools

In Windsurf/Claude, call:

```
"Use the WhiteMagic semantic search tool for 'async debugging heuristics' (hybrid mode)."
```

This hits the `search_semantic` MCP tool which maps to the same engine.

## 5. Interpreting Scores

- Semantic scores range 0–1 (higher is closer).
- Hybrid mode fuses keyword ranks via Reciprocal Rank Fusion; the final score is normalized so results remain comparable.
- Use `--json` to view both the `score` and `match_type` fields for downstream ranking.

## 6. Embedding Cache Management

```bash
# Inspect cache
ls ~/.whitemagic/embeddings

# Clear cache (forces rebuild)
rm -rf ~/.whitemagic/embeddings/cache
```

The cache stores `{memory_filename}.{model}.npy` pairs alongside a manifest, so incremental updates remain fast.

## 7. Troubleshooting

| Symptom | Fix |
| --- | --- |
| `ImportError: sentence_transformers` | Install extras: `pip install "whitemagic[api,dev]"`. |
| CLI hangs on first search | Allow time for embedding model download/compile. Subsequent runs use cache. |
| "No embeddings provider configured" | Re-run `whitemagic setup-embeddings` or export `OPENAI_API_KEY`. |
| Results feel stale after edits | Run with `--cache-refresh` or delete cache directory. |

## 8. Programmatic Usage

```python
from whitemagic import MemoryManager
from whitemagic.search.semantic import SemanticSearcher

manager = MemoryManager()
searcher = SemanticSearcher(manager)
results = await searcher.hybrid_search("gitops postmortem", k=5)
for result in results:
    print(result.title, result.score, result.match_type)
```

## 9. Roadmap

- Tier-2 cached embeddings stored alongside memories
- Vector store adapters (pgvector, LanceDB)
- Query expansion via symbolic reasoning engine

Use this guide alongside `docs/guides/MEMORY_SYSTEM_README.md` to integrate semantic search into your workflow end-to-end.
