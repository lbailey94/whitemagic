# Gana: gana_winnowing_basket

**35 tools** routed through this Gana.

| Tool | Category | Safety | Description |
|------|----------|--------|-------------|
| [activation.spread](../tools/activation.spread.md) | memory | write | Spread activation from seed memories through the association graph, priming rela |
| [activation.stats](../tools/activation.stats.md) | memory | read | Get spreading activation engine statistics. |
| [batch_read_memories](../tools/batch_read_memories.md) | system | read | Dispatch-routable WhiteMagic tool 'batch_read_memories'. |
| [fast_read_memory](../tools/fast_read_memory.md) | system | read | Dispatch-routable WhiteMagic tool 'fast_read_memory'. |
| [fragment.index](../tools/fragment.index.md) | memory | write | Build or update a Fragment index for a codebase. Supports quick (BM25 only) and  |
| [fragment.query](../tools/fragment.query.md) | memory | read | Alias for fragment.search — query a Fragment index for relevant code chunks. |
| [fragment.search](../tools/fragment.search.md) | memory | read | Search a codebase index for relevant code chunks using Fragment (Rust). 100x fas |
| [fragment.status](../tools/fragment.status.md) | memory | read | Show Fragment index statistics for a project — file count, chunk count, index si |
| [graph_walk](../tools/graph_walk.md) | memory | read | Execute a multi-hop weighted random walk from seed memory IDs. Returns traversal |
| [hybrid_recall](../tools/hybrid_recall.md) | memory | read | Multi-hop graph-aware memory recall. Combines BM25 + embedding anchor search wit |
| [jit_research](../tools/jit_research.md) | memory | read | Iterative plan-search-reflect research across the memory store. Decomposes a que |
| [jit_research.stats](../tools/jit_research.stats.md) | memory | read | Get JIT Memory Researcher statistics — total sessions, evidence found, configura |
| [list_memories](../tools/list_memories.md) | system | read | Dispatch-routable WhiteMagic tool 'list_memories'. |
| [memory_read](../tools/memory_read.md) | system | read | Dispatch-routable WhiteMagic tool 'memory_read'. |
| [memory_search](../tools/memory_search.md) | system | read | Dispatch-routable WhiteMagic tool 'memory_search'. |
| [polyglot.search](../tools/polyglot.search.md) | memory | read | Convenience tool: encode a query text and find its nearest neighbors among a poo |
| [read_memory](../tools/read_memory.md) | system | read | Dispatch-routable WhiteMagic tool 'read_memory'. |
| [recall](../tools/recall.md) | memory | read | Shorthand: search memories. Equivalent to gana_winnowing_basket → hybrid_recall. |
| [rerank](../tools/rerank.md) | synthesis | read | Rerank search results using cross-encoder model or BM25 lexical fallback for hig |
| [rerank.status](../tools/rerank.status.md) | synthesis | read | Get reranker status (cross-encoder availability, fallback mode). |
| [research.dag.breakthroughs](../tools/research.dag.breakthroughs.md) | synthesis | read | List top breakthroughs, optionally filtered by domain |
| [research.dag.experiments](../tools/research.dag.experiments.md) | synthesis | read | Query experiments with optional domain and stage filters |
| [research.dag.leaderboard](../tools/research.dag.leaderboard.md) | synthesis | read | Get domain leaderboard (top experiments by fitness) |
| [research.dag.lineage](../tools/research.dag.lineage.md) | synthesis | read | Get lineage tree for an experiment (ancestors + descendants) |
| [research.dag.result](../tools/research.dag.result.md) | synthesis | write | Record an experiment result with fitness score |
| [research.dag.stats](../tools/research.dag.stats.md) | synthesis | read | Get research DAG statistics (total experiments, breakthroughs, etc.) |
| [research.dag.submit](../tools/research.dag.submit.md) | synthesis | write | Submit a hypothesis to the research DAG |
| [search.telemetry](../tools/search.telemetry.md) | system | read | Dispatch-routable WhiteMagic tool 'search.telemetry'. |
| [search_memories](../tools/search_memories.md) | system | read | Dispatch-routable WhiteMagic tool 'search_memories'. |
| [search_query](../tools/search_query.md) | system | read | Dispatch-routable WhiteMagic tool 'search_query'. |
| [vector.index](../tools/vector.index.md) | system | read | Dispatch-routable WhiteMagic tool 'vector.index'. |
| [vector.search](../tools/vector.search.md) | system | read | Dispatch-routable WhiteMagic tool 'vector.search'. |
| [vector.status](../tools/vector.status.md) | system | read | Dispatch-routable WhiteMagic tool 'vector.status'. |
| [wm_read](../tools/wm_read.md) | memory | read | Unified read interface — auto-selects best strategy or uses explicit mode. Modes |
| [wm_read.status](../tools/wm_read.status.md) | memory | read | Get wm_read system status: available modes, backend availability, and stats. |
