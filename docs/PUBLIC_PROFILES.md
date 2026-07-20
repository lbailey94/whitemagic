# WhiteMagic Public Profiles

**Version**: 25.0.1
**Updated**: 2026-07-19

WhiteMagic supports five installation profiles, each with different dependencies and capabilities. Profiles are selected via pip extras.

## Profile: Core

**Install**: `pip install whitemagic`

**Includes**:
- Memory system (14-galaxy taxonomy, FTS5 search, SQLite backend)
- Stable runtime (dispatch pipeline, middleware, 8-stage governance)
- Dharma governance (ethical reasoning, karma ledger, maturity gates)
- Session recording with progressive recall
- Citta consciousness stream
- Dream cycle (12-phase memory consolidation)
- 28 Gana meta-tools (PRAT router)

**Excludes**: MCP server, CLI, embeddings, local inference, research tools, security assessment

**Best for**: Embedding WhiteMagic memory into existing Python applications

---

## Profile: MCP

**Install**: `pip install whitemagic[mcp]`

**Includes everything in Core, plus**:
- MCP server (stdio + Streamable HTTP transport)
- 860 callable tools via 28 Gana meta-tools
- MCP annotation compliance (readOnlyHint, destructiveHint, idempotentHint, openWorldHint)
- Lazy imports for <1s handshake

**Excludes**: CLI, embeddings, local inference, research tools

**Best for**: Connecting AI agents (Claude, ChatGPT, etc.) to WhiteMagic via MCP

---

## Profile: Local AI

**Install**: `pip install whitemagic[mcp,ai]`

**Includes everything in MCP, plus**:
- FastEmbed embeddings (BAAI/bge-small-en-v1.5, 384 dims)
- HNSW vector index with disk persistence
- Semantic search (cosine similarity, cross-encoder reranking)
- Hybrid retrieval (BM25 + semantic + 5D spatial via RRF)
- Ollama integration (local LLM inference)
- LlamaCpp backend (Qwen3, BitNet, speculative decoding)

**Excludes**: Research tools, security assessment

**Best for**: Running fully local AI with semantic memory and inference

---

## Profile: Research

**Install**: `pip install whitemagic[mcp,ai,research]`

**Includes everything in Local AI, plus**:
- Monte Carlo simulation (PolyglotMCOrchestrator)
- Superforecaster pipeline
- Recursive improvement loop
- Emergence engine (novel insight detection)
- Causal reasoning
- Multi-spectral reasoning
- Polyglot bridges (Rust, Haskell, Elixir, Go, Zig, Julia, Koka)
- Browser research tools
- Knowledge graph v2

**Excludes**: Security assessment capabilities

**Best for**: Research and experimentation with cognitive architectures

---

## Profile: Violet/Security

**Install**: `pip install whitemagic[mcp,ai,violet]`

**Includes everything in Local AI, plus**:
- Security assessment tools (nmap, nikto, nuclei, pentest)
- Engagement token enforcement (ROE Gate pattern)
- PoC pipeline governance
- Model signing verification
- Transaction firewall
- Violet shelter template (purple-team operations)
- Hermit Crab sandbox
- Audit signing (Ed25519)

**Requires**: Explicit `WM_VIOLET_ENABLED=1` environment variable

**Best for**: Authorized security assessment and red-team operations

---

## Unavailable Feature Messages

When a profile lacks a dependency, tools return actionable messages:

```
{"status": "unavailable", "message": "Embeddings not installed. Install with: pip install whitemagic[ai]"}
```

## Security Boundaries

- **Default Dharma profile**: Permissive, allows all safe operations
- **Violet profile**: Requires engagement tokens for red-ops tools, enforces model signing
- **Sandbox profile**: No network, limited resources
- **Secure profile**: No network/filesystem, minimal resources
- **Production profile**: Read-only, secure Dharma
