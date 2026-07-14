# Category: memory

**59 tools** in this category.

| Tool | Safety | Description |
|------|--------|-------------|
| [activation.spread](../tools/activation.spread.md) | write | Spread activation from seed memories through the association graph, priming rela |
| [activation.stats](../tools/activation.stats.md) | read | Get spreading activation engine statistics. |
| [codebase.recall](../tools/codebase.recall.md) | read | Semantic recall from the codex galaxy. Searches file and chunk content memories  |
| [consolidation.run](../tools/consolidation.run.md) | write | Run a sleep consolidation cycle — transfer, strengthen, and prune memories acros |
| [consolidation.stats](../tools/consolidation.stats.md) | read | Get sleep consolidation engine statistics. |
| [entity_resolve](../tools/entity_resolve.md) | write | Run embedding-based entity resolution (dedup) on the memory store. Finds near-du |
| [fast_write.append](../tools/fast_write.append.md) | write | Append content to an existing file with optional syntax validation. |
| [fast_write.batch](../tools/fast_write.batch.md) | write | Write multiple files in one operation with syntax validation. |
| [fast_write.validate](../tools/fast_write.validate.md) | read | Validate syntax of a file without writing. Checks Python (ast.parse) or basic en |
| [fast_write.write](../tools/fast_write.write.md) | write | Write content to a file atomically with syntax validation. Overwrites if file ex |
| [fragment.index](../tools/fragment.index.md) | write | Build or update a Fragment index for a codebase. Supports quick (BM25 only) and  |
| [fragment.query](../tools/fragment.query.md) | read | Alias for fragment.search — query a Fragment index for relevant code chunks. |
| [fragment.search](../tools/fragment.search.md) | read | Search a codebase index for relevant code chunks using Fragment (Rust). 100x fas |
| [fragment.status](../tools/fragment.status.md) | read | Show Fragment index statistics for a project — file count, chunk count, index si |
| [galaxy.search_multi](../tools/galaxy.search_multi.md) | read | Search across multiple galaxies in parallel. Executes FTS5 queries against each  |
| [gating.detect](../tools/gating.detect.md) | read | Auto-detect cognitive context from a query string using keyword matching. |
| [gating.list](../tools/gating.list.md) | read | List all available galaxy gating contexts with descriptions and current context. |
| [gating.mask](../tools/gating.mask.md) | read | Get the galaxy activation mask (weight multipliers per galaxy) for a given conte |
| [gating.set_context](../tools/gating.set_context.md) | read | Set the current cognitive context for galaxy gating (introspection, coding, rese |
| [gating.stats](../tools/gating.stats.md) | read | Get galaxy gating system statistics. |
| [graph_walk](../tools/graph_walk.md) | read | Execute a multi-hop weighted random walk from seed memory IDs. Returns traversal |
| [hybrid_recall](../tools/hybrid_recall.md) | read | Multi-hop graph-aware memory recall. Combines BM25 + embedding anchor search wit |
| [jit_research](../tools/jit_research.md) | read | Iterative plan-search-reflect research across the memory store. Decomposes a que |
| [jit_research.stats](../tools/jit_research.stats.md) | read | Get JIT Memory Researcher statistics — total sessions, evidence found, configura |
| [kg.extract](../tools/kg.extract.md) | write | Extract entities and relations from text into the knowledge graph (spaCy NER + r |
| [kg.query](../tools/kg.query.md) | read | Query an entity and its connections in the knowledge graph |
| [kg2.batch](../tools/kg2.batch.md) | write | Batch extract entities from multiple unextracted memories |
| [kg2.entity](../tools/kg2.entity.md) | read | Query entity graph with typed edges (KG v2 with LightNER) |
| [kg2.extract](../tools/kg2.extract.md) | write | Extract entities and relations using LightNER (fast pattern-based extraction) |
| [metaplasticity.apply](../tools/metaplasticity.apply.md) | write | Apply a strength modification to a memory, gated by its metaplasticity threshold |
| [metaplasticity.batch](../tools/metaplasticity.batch.md) | write | Batch apply multiple metaplasticity-gated modifications. |
| [metaplasticity.decay](../tools/metaplasticity.decay.md) | write | Decay all metaplasticity activity counters (e.g., during sleep homeostasis). |
| [metaplasticity.plasticity](../tools/metaplasticity.plasticity.md) | read | Get plasticity score for a memory (0=stable, 1=plastic) and its current threshol |
| [metaplasticity.stats](../tools/metaplasticity.stats.md) | read | Get metaplasticity system statistics. |
| [narrative.compress](../tools/narrative.compress.md) | write | Compress clusters of episodic memories into coherent narrative summaries. Runs a |
| [narrative.stats](../tools/narrative.stats.md) | read | Get narrative compressor statistics — total compressions, narratives created. |
| [neuro.modulate](../tools/neuro.modulate.md) | write | Apply neuromodulation to a list of memories, adjusting their neuro_score based o |
| [neuro.reset](../tools/neuro.reset.md) | write | Reset neuromodulator levels to baseline. |
| [polyglot.memory_query](../tools/polyglot.memory_query.md) | read | Execute a holographic memory query through an available polyglot backend (Julia, |
| [polyglot.search](../tools/polyglot.search.md) | read | Convenience tool: encode a query text and find its nearest neighbors among a poo |
| [recall](../tools/recall.md) | read | Shorthand: search memories. Equivalent to gana_winnowing_basket → hybrid_recall. |
| [reconsolidation.mark](../tools/reconsolidation.mark.md) | write | Mark a retrieved memory as labile (modifiable). Within the 5-minute window, it c |
| [reconsolidation.status](../tools/reconsolidation.status.md) | read | Get reconsolidation engine status: labile count, stats, pending updates. |
| [reconsolidation.update](../tools/reconsolidation.update.md) | write | Update a labile memory with new context before reconsolidation. |
| [remember](../tools/remember.md) | write | Shorthand: create a memory. Equivalent to gana_neck → create_memory. |
| [replay.batch](../tools/replay.batch.md) | write | Batch replay multiple memory sequences for parallel consolidation. |
| [replay.run](../tools/replay.run.md) | write | Replay a memory sequence with STDP strengthening and trajectory detection. |
| [replay.stats](../tools/replay.stats.md) | read | Get replay simulation system statistics. |
| [ripple.decay](../tools/ripple.decay.md) | write | Decay all ripple tags (e.g., after a consolidation cycle has consumed them). |
| [ripple.stats](../tools/ripple.stats.md) | read | Get ripple tagging system statistics. |
| [ripple.tag](../tools/ripple.tag.md) | write | Tag memories that co-activate within a ripple window for consolidation during sl |
| [ripple.tags](../tools/ripple.tags.md) | read | Get ripple tags for specified memories. |
| [wm_read](../tools/wm_read.md) | read | Unified read interface — auto-selects best strategy or uses explicit mode. Modes |
| [wm_read.status](../tools/wm_read.status.md) | read | Get wm_read system status: available modes, backend availability, and stats. |
| [wm_write](../tools/wm_write.md) | write | Unified write interface — auto-selects best strategy or uses explicit mode. Mode |
| [wm_write.status](../tools/wm_write.status.md) | read | Get wm_write system status: available modes and backend availability. |
| [working_memory.attend](../tools/working_memory.attend.md) | write | Bring a memory into working memory focus. LRU eviction when at capacity (7±2 chu |
| [working_memory.context](../tools/working_memory.context.md) | read | Get current working memory contents sorted by activation, for prompt injection. |
| [working_memory.status](../tools/working_memory.status.md) | read | Get working memory status: capacity, used slots, chunks, eviction stats. |
