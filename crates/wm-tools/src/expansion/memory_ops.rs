//! Memory operation tools — consolidate, decay, batch_read, update, tag, stats, hybrid_recall.

#![forbid(unsafe_code)]

use async_trait::async_trait;

use serde_json::{Value, json};
use std::collections::HashMap;
use std::fmt::Write;
use std::sync::Arc;
use wm_core::{Context, EffectRow, Galaxy, Gana, Resource, Tool, ToolStats};
use wm_memory::{MemoryStore, RecallEngine, SearchEngine};

use super::common::{
    galaxy_name, int_prop, num_prop, parse_galaxy, parse_galaxy_or, schema, str_prop,
};

/// `memory.consolidate` — deduplicate memories by content_hash within a galaxy.
pub struct MemoryConsolidateTool {
    store: Arc<MemoryStore>,
    search: Option<Arc<SearchEngine>>,
    stats: ToolStats,
    effects: EffectRow,
}

impl MemoryConsolidateTool {
    pub fn new(store: Arc<MemoryStore>, search: Option<Arc<SearchEngine>>) -> Self {
        Self {
            store,
            search,
            stats: ToolStats::default(),
            effects: EffectRow {
                writes: super::common::memory_galaxy_writes(),
                reads: super::common::memory_galaxy_reads(),
                destructive: true,
                ..Default::default()
            },
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for MemoryConsolidateTool {
    fn name(&self) -> &str {
        "memory.consolidate"
    }
    fn gana(&self) -> Gana {
        Gana::Encampment
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Deduplicate memories by content_hash within a galaxy"
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let galaxy = args
            .get("galaxy")
            .and_then(|v| v.as_str())
            .unwrap_or("codex");
        let galaxy = parse_galaxy(galaxy)?;
        let memories = self.store.scan(galaxy, 10_000)?;
        let mut seen_hashes: HashMap<String, uuid::Uuid> = HashMap::new();
        let mut duplicates = 0u32;
        for mem in &memories {
            let hash = &mem.metadata.content_hash;
            if let Some(existing_id) = seen_hashes.get(hash) {
                if *existing_id != mem.metadata.id {
                    self.store.delete(galaxy, mem.metadata.id)?;
                    super::common::deindex(self.search.as_deref(), &mem.metadata.id.to_string());
                    duplicates += 1;
                }
            } else {
                seen_hashes.insert(hash.clone(), mem.metadata.id);
            }
        }
        Ok(json!({
            "status": "success",
            "galaxy": galaxy_name(galaxy),
            "scanned": memories.len(),
            "duplicates_removed": duplicates,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// `memory.decay` — lower importance of old, low-access memories.
pub struct MemoryDecayTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl MemoryDecayTool {
    pub fn new(store: Arc<MemoryStore>) -> Self {
        Self {
            store,
            stats: ToolStats::default(),
            effects: EffectRow {
                writes: super::common::memory_galaxy_writes(),
                reads: super::common::memory_galaxy_reads(),
                ..Default::default()
            },
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for MemoryDecayTool {
    fn name(&self) -> &str {
        "memory.decay"
    }
    fn gana(&self) -> Gana {
        Gana::WinnowingBasket
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Lower importance of old, low-access memories (never deletes)"
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let galaxy = args
            .get("galaxy")
            .and_then(|v| v.as_str())
            .unwrap_or("codex");
        let galaxy = parse_galaxy(galaxy)?;
        let threshold = args
            .get("importance_threshold")
            .and_then(serde_json::Value::as_f64)
            .unwrap_or(0.3) as f32;
        let decay_factor = args
            .get("decay_factor")
            .and_then(serde_json::Value::as_f64)
            .unwrap_or(0.9) as f32;
        let memories = self.store.scan(galaxy, 10_000)?;
        let mut decayed = 0u32;
        for mem in &memories {
            if mem.metadata.importance < threshold {
                let mut updated = mem.clone();
                updated.metadata.importance =
                    (updated.metadata.importance * decay_factor).clamp(0.0, 1.0);
                if (updated.metadata.importance - mem.metadata.importance).abs() > 0.001 {
                    self.store.put(galaxy, &updated)?;
                    decayed += 1;
                }
            }
        }
        Ok(json!({
            "status": "success",
            "galaxy": galaxy_name(galaxy),
            "scanned": memories.len(),
            "decayed": decayed,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// `memory.batch_read` — read multiple memories by ID.
pub struct MemoryBatchReadTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl MemoryBatchReadTool {
    pub fn new(store: Arc<MemoryStore>) -> Self {
        Self {
            store,
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![Resource::Galaxy("codex".into())]),
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for MemoryBatchReadTool {
    fn name(&self) -> &str {
        "memory.batch_read"
    }
    fn gana(&self) -> Gana {
        Gana::WinnowingBasket
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Read multiple memories by ID from a galaxy"
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let galaxy = args
            .get("galaxy")
            .and_then(|v| v.as_str())
            .unwrap_or("codex");
        let galaxy = parse_galaxy(galaxy)?;
        let ids = args
            .get("ids")
            .and_then(|v| v.as_array())
            .ok_or_else(|| wm_core::CoreError::InvalidArgs("Missing 'ids' array".into()))?;
        let mut results = Vec::new();
        let mut misses = 0u32;
        for id_val in ids {
            if let Some(id_str) = id_val.as_str() {
                if let Ok(id) = uuid::Uuid::parse_str(id_str) {
                    match self.store.get(galaxy, id)? {
                        Some(mem) if crate::expansion::common::mcp_visible(&mem) => {
                            results.push(json!({
                                "id": mem.metadata.id,
                                "content": mem.content,
                                "tags": mem.metadata.tags,
                                "importance": mem.metadata.importance,
                            }));
                        }
                        // Private memories are treated like misses — they never
                        // appear in MCP responses.
                        Some(_) => {
                            misses += 1;
                        }
                        None => {
                            misses += 1;
                        }
                    }
                }
            }
        }
        Ok(json!({
            "status": "success",
            "galaxy": galaxy_name(galaxy),
            "found": results.len(),
            "misses": misses,
            "memories": results,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// `memory.update` — update tags or importance of a memory.
///
/// If a `SearchEngine` is provided, the updated memory is re-indexed into
/// Tantivy (delete old doc, add new doc, commit).
pub struct MemoryUpdateTool {
    store: Arc<MemoryStore>,
    search: Option<Arc<SearchEngine>>,
    stats: ToolStats,
    effects: EffectRow,
}

impl MemoryUpdateTool {
    pub fn new(store: Arc<MemoryStore>, search: Option<Arc<SearchEngine>>) -> Self {
        Self {
            store,
            search,
            stats: ToolStats::default(),
            effects: EffectRow {
                writes: super::common::memory_galaxy_writes(),
                reads: super::common::memory_galaxy_reads(),
                ..Default::default()
            },
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for MemoryUpdateTool {
    fn name(&self) -> &str {
        "memory.update"
    }
    fn gana(&self) -> Gana {
        Gana::Encampment
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Update tags or importance of an existing memory"
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let galaxy = parse_galaxy_or(args.get("galaxy").and_then(|v| v.as_str()), Galaxy::Codex)?;
        let id_str = args
            .get("id")
            .and_then(|v| v.as_str())
            .ok_or_else(|| wm_core::CoreError::InvalidArgs("Missing 'id'".into()))?;
        let id = uuid::Uuid::parse_str(id_str)
            .map_err(|e| wm_core::CoreError::InvalidArgs(format!("Invalid UUID: {e}")))?;
        if let Some(search) = &self.search {
            if search.is_readonly() {
                return Err(wm_core::CoreError::InvalidArgs(
                    "read-only mode: memory.update disabled (another process owns the index)"
                        .into(),
                ));
            }
        }
        let mut mem = self.store.get(galaxy, id)?.ok_or_else(|| {
            wm_core::CoreError::NotFound(format!(
                "Memory {id} not found in {}",
                galaxy_name(galaxy)
            ))
        })?;
        if let Some(tags) = args.get("tags").and_then(|v| v.as_array()) {
            mem.metadata.tags = tags
                .iter()
                .filter_map(|t| t.as_str().map(String::from))
                .collect();
        }
        if let Some(importance) = args.get("importance").and_then(serde_json::Value::as_f64) {
            mem.metadata.importance = importance as f32;
        }
        if let Some(content) = args.get("content").and_then(|v| v.as_str()) {
            mem.content = content.to_string();
            // Content changes invalidate the hash — keep it in sync so
            // dedup and content-hash lookups stay truthful.
            mem.metadata.content_hash = wm_memory::content_hash(content);
        }
        self.store.put(galaxy, &mem)?;

        // Re-index in Tantivy if search engine is available (non-fatal)
        if let Some(search) = &self.search {
            if let Err(e) = (|| {
                let mut writer = search.writer()?;
                search.delete_document(&mut writer, id_str)?;
                search.add_document(
                    &mut writer,
                    id_str,
                    galaxy_name(galaxy),
                    &mem.content,
                    &mem.metadata.tags,
                    mem.metadata.created_at.timestamp(),
                )?;
                search.commit(&mut writer)?;
                Ok::<(), wm_core::CoreError>(())
            })() {
                tracing::warn!("Tantivy re-indexing failed for memory {id_str}: {e}");
            }
        }

        Ok(json!({
            "status": "success",
            "id": mem.metadata.id,
            "galaxy": galaxy_name(galaxy),
            "tags": mem.metadata.tags,
            "importance": mem.metadata.importance,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// `memory.tag` — add or remove tags from a memory.
pub struct MemoryTagTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl MemoryTagTool {
    pub fn new(store: Arc<MemoryStore>) -> Self {
        Self {
            store,
            stats: ToolStats::default(),
            effects: EffectRow {
                writes: super::common::memory_galaxy_writes(),
                reads: super::common::memory_galaxy_reads(),
                ..Default::default()
            },
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for MemoryTagTool {
    fn name(&self) -> &str {
        "memory.tag"
    }
    fn gana(&self) -> Gana {
        Gana::Net
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Add or remove tags from a memory"
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let galaxy = parse_galaxy_or(args.get("galaxy").and_then(|v| v.as_str()), Galaxy::Codex)?;
        let id_str = args
            .get("id")
            .and_then(|v| v.as_str())
            .ok_or_else(|| wm_core::CoreError::InvalidArgs("Missing 'id'".into()))?;
        let id = uuid::Uuid::parse_str(id_str)
            .map_err(|e| wm_core::CoreError::InvalidArgs(format!("Invalid UUID: {e}")))?;
        let mut mem = self
            .store
            .get(galaxy, id)?
            .ok_or_else(|| wm_core::CoreError::NotFound(format!("Memory {id} not found")))?;
        let action = args.get("action").and_then(|v| v.as_str()).unwrap_or("add");
        let tags = args
            .get("tags")
            .and_then(|v| v.as_array())
            .ok_or_else(|| wm_core::CoreError::InvalidArgs("Missing 'tags' array".into()))?;
        let tag_list: Vec<String> = tags
            .iter()
            .filter_map(|t| t.as_str().map(String::from))
            .collect();
        match action {
            "remove" => {
                mem.metadata.tags.retain(|t| !tag_list.contains(t));
            }
            _ => {
                for t in &tag_list {
                    if !mem.metadata.tags.contains(t) {
                        mem.metadata.tags.push(t.clone());
                    }
                }
            }
        }
        self.store.put(galaxy, &mem)?;
        Ok(json!({
            "status": "success",
            "id": mem.metadata.id,
            "action": action,
            "tags": mem.metadata.tags,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// `memory.stats` — statistics for a galaxy.
pub struct MemoryStatsTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl MemoryStatsTool {
    pub fn new(store: Arc<MemoryStore>) -> Self {
        Self {
            store,
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![Resource::Galaxy("codex".into())]),
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for MemoryStatsTool {
    fn name(&self) -> &str {
        "memory.stats"
    }
    fn gana(&self) -> Gana {
        Gana::WinnowingBasket
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Statistics for a galaxy (count, avg importance, tag frequency)"
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let galaxy = parse_galaxy_or(args.get("galaxy").and_then(|v| v.as_str()), Galaxy::Codex)?;
        let memories = self.store.scan(galaxy, 10_000)?;
        let total = memories.len();
        let avg_importance = if total > 0 {
            memories.iter().map(|m| m.metadata.importance).sum::<f32>() / total as f32
        } else {
            0.0
        };
        let mut tag_freq: HashMap<String, u32> = HashMap::new();
        for mem in &memories {
            for tag in &mem.metadata.tags {
                *tag_freq.entry(tag.clone()).or_insert(0) += 1;
            }
        }
        let top_tags: Vec<(String, u32)> = tag_freq.into_iter().filter(|(_, c)| *c >= 2).collect();
        Ok(json!({
            "status": "success",
            "galaxy": galaxy_name(galaxy),
            "count": total,
            "avg_importance": (avg_importance * 100.0).round() / 100.0,
            "tag_clusters": top_tags.len(),
            "top_tags": top_tags.into_iter().take(10).collect::<Vec<_>>(),
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// Shared retrieval implementation used by `memory.search` (public verb)
/// and `memory.hybrid_recall` (compatibility alias).
pub struct MemoryHybridRecallTool {
    store: Arc<MemoryStore>,
    search: Option<Arc<SearchEngine>>,
    recall: Option<Arc<RecallEngine>>,
    stats: ToolStats,
    effects: EffectRow,
    route_name: &'static str,
}

impl MemoryHybridRecallTool {
    pub fn new(
        store: Arc<MemoryStore>,
        search: Option<Arc<SearchEngine>>,
        recall: Option<Arc<RecallEngine>>,
    ) -> Self {
        Self::named("memory.hybrid_recall", store, search, recall)
    }

    /// Public retrieval verb. Same implementation as `memory.hybrid_recall`.
    pub fn as_search(
        store: Arc<MemoryStore>,
        search: Option<Arc<SearchEngine>>,
        recall: Option<Arc<RecallEngine>>,
    ) -> Self {
        Self::named("memory.search", store, search, recall)
    }

    fn named(
        route_name: &'static str,
        store: Arc<MemoryStore>,
        search: Option<Arc<SearchEngine>>,
        recall: Option<Arc<RecallEngine>>,
    ) -> Self {
        Self {
            store,
            search,
            recall,
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![Resource::Galaxy("codex".into())]),
            route_name,
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for MemoryHybridRecallTool {
    fn name(&self) -> &str {
        self.route_name
    }
    fn gana(&self) -> Gana {
        Gana::WinnowingBasket
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Search memories (BM25 by default; BM25 + vector fusion when WM_EMBEDDER_ENDPOINT is set). memory.hybrid_recall is a compatibility alias."
    }
    fn input_schema(&self) -> Value {
        schema(
            &json!({
                "query": str_prop("Full-text query"),
                "galaxy": str_prop("Galaxy filter (default: codex)"),
                "limit": int_prop("Maximum results (default 10)"),
                "min_importance": num_prop("Minimum memory importance (0-1)"),
                "min_score": num_prop("Absolute BM25 score floor"),
                "min_score_ratio": num_prop("Relative floor: reject hits below this fraction of the top score"),
            }),
            &["query"],
        )
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let galaxy = parse_galaxy_or(args.get("galaxy").and_then(|v| v.as_str()), Galaxy::Codex)?;
        let query = args.get("query").and_then(|v| v.as_str()).unwrap_or("");
        let limit = args
            .get("limit")
            .and_then(serde_json::Value::as_u64)
            .unwrap_or(10) as usize;
        let min_importance = args
            .get("min_importance")
            .and_then(serde_json::Value::as_f64)
            .unwrap_or(0.0) as f32;
        // Absolute BM25 floor (0 / absent = disabled). Clients that set a
        // meaningful `minScore` finally get what they asked for.
        let min_score = args
            .get("min_score")
            .and_then(serde_json::Value::as_f64)
            .map(|v| v as f32)
            .filter(|v| *v > 0.0);
        // Relative floor: reject hits below `ratio * top_score`.
        // 0.0 or absent → use default 5%. Explicitly passing a value in
        // (0, 1) overrides; passing 0.0 disables the floor entirely.
        let min_score_ratio = args
            .get("min_score_ratio")
            .and_then(serde_json::Value::as_f64)
            .map(|v| v as f32)
            .filter(|v| *v >= 0.0 && *v < 1.0)
            .map_or(Some(0.05), Some);
        let mut results = Vec::new();

        // Phase 0: If RecallEngine with a real embedder is available, use
        // hybrid BM25 + vector search for fused ranking.
        if let Some(ref recall) = self.recall {
            if !query.is_empty() {
                let hybrid_results = recall.hybrid_search(query, limit * 2, Some(galaxy));
                for hr in hybrid_results {
                    if let Ok(Some(mem)) = self.store.get(hr.galaxy, hr.memory_id) {
                        if mem.metadata.importance >= min_importance
                            && crate::expansion::common::mcp_visible(&mem)
                        {
                            results.push(json!({
                                "id": mem.metadata.id,
                                "content": wm_memory::scrub_text(&mem.content),
                                "importance": mem.metadata.importance,
                                "score": hr.score,
                                "bm25_score": hr.bm25_score,
                                "vector_score": hr.vector_score,
                                "source": "hybrid",
                            }));
                        }
                    }
                }
            }
        }

        // Phase 1: full-text search (OR + token-coverage + score floors)
        // Only run if hybrid search didn't produce results or no RecallEngine
        if results.is_empty() {
            if let Some(ref search) = self.search {
                if !query.is_empty() {
                    let opts = wm_memory::SearchOptions {
                        limit: limit * 2,
                        min_score,
                        relative_floor: min_score_ratio,
                        ..wm_memory::SearchOptions::default()
                    };
                    let hits = search.search_opt(query, &opts)?;
                    for hit in hits {
                        if let Ok(id) = uuid::Uuid::parse_str(&hit.memory_id) {
                            if let Ok(Some(mem)) = self.store.get(galaxy, id) {
                                if mem.metadata.importance >= min_importance
                                    && crate::expansion::common::mcp_visible(&mem)
                                {
                                    results.push(json!({
                                        "id": mem.metadata.id,
                                        "content": wm_memory::scrub_text(&mem.content),
                                        "importance": mem.metadata.importance,
                                        "score": hit.score,
                                        "normalized_score": hit.normalized_score,
                                        "source": "fts",
                                    }));
                                }
                            }
                        }
                    }
                }
            }
        }
        // Phase 2: only when NO query was given, return by importance.
        // (With a query, empty results are final — a score threshold must
        // not be bypassed by a scan-based fallback.)
        if results.is_empty() && query.is_empty() {
            let mut memories = self.store.scan(galaxy, 100)?;
            memories.sort_by(|a, b| {
                b.metadata
                    .importance
                    .partial_cmp(&a.metadata.importance)
                    .unwrap_or(std::cmp::Ordering::Equal)
            });
            for mem in memories
                .iter()
                .filter(|m| {
                    m.metadata.importance >= min_importance
                        && crate::expansion::common::mcp_visible(m)
                })
                .take(limit)
            {
                results.push(json!({
                    "id": mem.metadata.id,
                    "content": &mem.content,
                    "importance": mem.metadata.importance,
                    "score": mem.metadata.importance,
                    "source": "importance",
                }));
            }
        }
        results.truncate(limit);
        Ok(json!({
            "status": "success",
            "galaxy": galaxy_name(galaxy),
            "count": results.len(),
            "results": results,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// `memory.episodic_search` — v6 raw episodic search for controlled evaluation.
///
/// This route is explicit-only and is not part of the curated v5 surface.
pub struct MemoryEpisodicSearchTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl MemoryEpisodicSearchTool {
    pub fn new(store: Arc<MemoryStore>) -> Self {
        Self {
            store,
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![Resource::Galaxy("episodic_records".into())]),
        }
    }
}

#[async_trait]
impl Tool for MemoryEpisodicSearchTool {
    fn name(&self) -> &str {
        "memory.episodic_search"
    }
    fn gana(&self) -> Gana {
        Gana::WinnowingBasket
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "[V6 Experimental] Search explicit episodic records with provenance and lifecycle filtering"
    }
    fn input_schema(&self) -> Value {
        schema(
            &json!({
                "query": str_prop("Full-text query"),
                "limit": int_prop("Maximum results (default 10)"),
                "candidate_limit": int_prop("Maximum candidates to score (default 2x limit)"),
                "include_historical": {
                    "type": "boolean",
                    "description": "Include superseded, revoked, and archived records",
                },
                "rerank": {
                    "type": "boolean",
                    "description": "Enable vector reranking (requires embedder, default false)",
                },
                "rerank_alpha": {
                    "type": "number",
                    "description": "Deterministic weight in hybrid score (0.0-1.0, default 0.7)",
                },
                "min_score": {
                    "type": "number",
                    "description": "Minimum score threshold; results below this are dropped (abstention). Default 0.0 (no threshold)",
                },
                "min_coverage": {
                    "type": "number",
                    "description": "Minimum query-term coverage ratio (0.0-1.0); results with lower coverage are dropped. E.g. 0.5 requires at least half the query terms to match. Default 0.0 (no threshold)",
                },
            }),
            &["query"],
        )
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let query = args.get("query").and_then(Value::as_str).unwrap_or("");
        let limit = args.get("limit").and_then(Value::as_u64).unwrap_or(10) as usize;
        let candidate_limit =
            args.get("candidate_limit")
                .and_then(Value::as_u64)
                .unwrap_or_else(|| limit.saturating_mul(2) as u64) as usize;
        let include_historical = args
            .get("include_historical")
            .and_then(Value::as_bool)
            .unwrap_or(false);
        let rerank = args.get("rerank").and_then(Value::as_bool).unwrap_or(false);
        let rerank_alpha = args
            .get("rerank_alpha")
            .and_then(Value::as_f64)
            .unwrap_or(0.7) as f32;
        let min_score = args
            .get("min_score")
            .and_then(Value::as_f64)
            .map(|v| v as f32);
        let min_coverage = args
            .get("min_coverage")
            .and_then(Value::as_f64)
            .map(|v| v as f32);
        // Compute query content-term count for coverage ratio.
        // We use a simple split on non-alphanumeric after removing common
        // stopwords, matching the episodic search tokenization.
        let query_term_count: usize = {
            const STOPWORDS: &[&str] = &[
                "the", "a", "an", "is", "are", "was", "were", "be", "been", "being", "have", "has",
                "had", "do", "does", "did", "will", "would", "could", "should", "may", "might",
                "must", "can", "shall", "to", "of", "in", "on", "at", "by", "for", "with", "about",
                "as", "into", "like", "through", "after", "over", "between", "out", "against",
                "during", "without", "before", "under", "around", "among", "i", "me", "my", "we",
                "us", "our", "you", "your", "he", "him", "his", "she", "her", "it", "its", "they",
                "them", "their", "what", "whats", "who", "when", "where", "why", "how", "and",
                "or", "but", "not", "no", "nor", "so", "yet", "both", "either", "neither", "this",
                "that", "these", "those", "there", "here", "now", "then", "than",
            ];
            query
                .split(|c: char| !c.is_alphanumeric())
                .filter(|t| t.len() > 1)
                .map(str::to_ascii_lowercase)
                .filter(|t| !STOPWORDS.contains(&t.as_str()))
                .collect::<std::collections::HashSet<_>>()
                .len()
        };
        let raw_results = if rerank {
            self.store.episodic().search_with_rerank(
                query,
                limit,
                candidate_limit,
                include_historical,
                rerank_alpha,
            )?
        } else {
            self.store.episodic().search_with_limits(
                query,
                limit,
                candidate_limit,
                include_historical,
            )?
        };
        // Coverage-based abstention: if the query has 3+ content terms and
        // NO result matches 2+ terms, all matches are likely on a single
        // generic term (e.g. "favorite") rather than the actual topic.
        // In that case, abstain entirely. If even one result matches 2+
        // terms, keep all results (the query has real matches in the haystack).
        // Skip abstention for count-style queries ("how many") since they
        // need all candidates for count verification.
        let is_count_query = query.to_ascii_lowercase().contains("how many");
        let abstain = min_coverage.is_some()
            && !is_count_query
            && query_term_count >= 3
            && !raw_results.iter().any(|hit| hit.matched_terms >= 2);
        let results = raw_results
            .into_iter()
            .filter(|hit| !hit.record.is_private && !hit.record.model_exclude)
            .filter(|hit| min_score.is_none_or(|ms| hit.score >= ms))
            .filter(|_| !abstain)
            .take(limit)
            .map(|hit| {
                json!({
                    "id": hit.record.id,
                    "content": wm_memory::scrub_text(&hit.record.content),
                    "score": hit.score,
                    "matched_terms": hit.matched_terms,
                    "session_id": hit.record.session_id,
                    "sequence": hit.record.sequence,
                    "created_at": hit.record.created_at,
                    "validity": hit.record.validity,
                    "provenance": hit.record.provenance,
                    "source": "episodic",
                })
            })
            .collect::<Vec<_>>();
        Ok(json!({
            "status": "success",
            "count": results.len(),
            "results": results,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// `memory.sort` — sort memories by importance, recency, or access count.
pub struct MemorySortTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl MemorySortTool {
    pub fn new(store: Arc<MemoryStore>) -> Self {
        Self {
            store,
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![Resource::Galaxy("codex".into())]),
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for MemorySortTool {
    fn name(&self) -> &str {
        "memory.sort"
    }
    fn gana(&self) -> Gana {
        Gana::WinnowingBasket
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Sort memories by importance, recency, or access count"
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let galaxy = parse_galaxy_or(args.get("galaxy").and_then(|v| v.as_str()), Galaxy::Codex)?;
        let sort_by = args
            .get("sort_by")
            .and_then(|v| v.as_str())
            .unwrap_or("importance");
        let order = args.get("order").and_then(|v| v.as_str()).unwrap_or("desc");
        let limit = args
            .get("limit")
            .and_then(serde_json::Value::as_u64)
            .unwrap_or(50) as usize;

        let mut memories = self.store.scan(galaxy, 10_000)?;
        // Private memories never appear in MCP responses.
        memories.retain(crate::expansion::common::mcp_visible);

        match sort_by {
            "importance" => memories.sort_by(|a, b| {
                b.metadata
                    .importance
                    .partial_cmp(&a.metadata.importance)
                    .unwrap_or(std::cmp::Ordering::Equal)
            }),
            "recency" => memories.sort_by(|a, b| b.metadata.created_at.cmp(&a.metadata.created_at)),
            "accessed" => {
                memories.sort_by(|a, b| b.metadata.accessed_at.cmp(&a.metadata.accessed_at));
            }
            "access_count" => {
                memories.sort_by(|a, b| b.metadata.access_count.cmp(&a.metadata.access_count));
            }
            _ => {
                return Err(wm_core::CoreError::InvalidArgs(format!(
                    "Unknown sort_by: '{sort_by}'. Use importance, recency, accessed, or access_count"
                )));
            }
        }

        if order == "asc" {
            memories.reverse();
        }

        let total = memories.len();
        memories.truncate(limit);

        let results: Vec<Value> = memories
            .iter()
            .map(|m| {
                json!({
                    "id": m.metadata.id,
                    "content": &m.content,
                    "importance": m.metadata.importance,
                    "created_at": m.metadata.created_at.to_rfc3339(),
                    "accessed_at": m.metadata.accessed_at.to_rfc3339(),
                    "access_count": m.metadata.access_count,
                    "tags": &m.metadata.tags,
                })
            })
            .collect();

        Ok(json!({
            "status": "success",
            "galaxy": galaxy_name(galaxy),
            "sort_by": sort_by,
            "order": order,
            "total": total,
            "returned": results.len(),
            "memories": results,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// `memory.filter` — filter memories by tags, date range, importance.
pub struct MemoryFilterTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl MemoryFilterTool {
    pub fn new(store: Arc<MemoryStore>) -> Self {
        Self {
            store,
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![Resource::Galaxy("codex".into())]),
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for MemoryFilterTool {
    fn name(&self) -> &str {
        "memory.filter"
    }
    fn gana(&self) -> Gana {
        Gana::WinnowingBasket
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Filter memories by tags, date range, and importance thresholds"
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let galaxy = parse_galaxy_or(args.get("galaxy").and_then(|v| v.as_str()), Galaxy::Codex)?;
        let tags: Vec<String> = args
            .get("tags")
            .and_then(|v| v.as_array())
            .map(|arr| {
                arr.iter()
                    .filter_map(|t| t.as_str().map(String::from))
                    .collect()
            })
            .unwrap_or_default();
        let min_importance = args
            .get("min_importance")
            .and_then(serde_json::Value::as_f64)
            .unwrap_or(0.0) as f32;
        let max_importance = args
            .get("max_importance")
            .and_then(serde_json::Value::as_f64)
            .unwrap_or(1.0) as f32;
        let limit = args
            .get("limit")
            .and_then(serde_json::Value::as_u64)
            .unwrap_or(50) as usize;

        let memories = self.store.scan(galaxy, 10_000)?;

        let filtered: Vec<&wm_memory::Memory> = memories
            .iter()
            .filter(|m| {
                // Private memories never appear in MCP responses.
                if !crate::expansion::common::mcp_visible(m) {
                    return false;
                }
                if m.metadata.importance < min_importance || m.metadata.importance > max_importance
                {
                    return false;
                }
                if !tags.is_empty() {
                    return tags.iter().all(|t| m.metadata.tags.contains(t));
                }
                true
            })
            .take(limit)
            .collect();

        let total_scanned = memories.len();
        let results: Vec<Value> = filtered
            .iter()
            .map(|m| {
                json!({
                    "id": m.metadata.id,
                    "content": &m.content,
                    "importance": m.metadata.importance,
                    "tags": &m.metadata.tags,
                    "created_at": m.metadata.created_at.to_rfc3339(),
                })
            })
            .collect();

        Ok(json!({
            "status": "success",
            "galaxy": galaxy_name(galaxy),
            "scanned": total_scanned,
            "matched": results.len(),
            "filters": {
                "tags": tags,
                "min_importance": min_importance,
                "max_importance": max_importance,
            },
            "memories": results,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// `memory.deduplicate` — find and merge duplicate memories by content similarity.
pub struct MemoryDeduplicateTool {
    store: Arc<MemoryStore>,
    search: Option<Arc<SearchEngine>>,
    stats: ToolStats,
    effects: EffectRow,
}

impl MemoryDeduplicateTool {
    pub fn new(store: Arc<MemoryStore>, search: Option<Arc<SearchEngine>>) -> Self {
        Self {
            store,
            search,
            stats: ToolStats::default(),
            effects: EffectRow {
                writes: super::common::memory_galaxy_writes(),
                reads: super::common::memory_galaxy_reads(),
                destructive: true,
                ..Default::default()
            },
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for MemoryDeduplicateTool {
    fn name(&self) -> &str {
        "memory.deduplicate"
    }
    fn gana(&self) -> Gana {
        Gana::WinnowingBasket
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Find and merge duplicate memories by content hash or similarity"
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let galaxy = parse_galaxy_or(args.get("galaxy").and_then(|v| v.as_str()), Galaxy::Codex)?;
        let mode = args.get("mode").and_then(|v| v.as_str()).unwrap_or("hash");
        let dry_run = args
            .get("dry_run")
            .and_then(serde_json::Value::as_bool)
            .unwrap_or(true);
        let limit = args
            .get("limit")
            .and_then(serde_json::Value::as_u64)
            .unwrap_or(10_000) as usize;

        let memories = self.store.scan(galaxy, limit)?;

        match mode {
            "hash" => {
                let mut seen_hashes: HashMap<String, uuid::Uuid> = HashMap::new();
                let mut duplicates: Vec<Value> = Vec::new();

                for mem in &memories {
                    let hash = &mem.metadata.content_hash;
                    if let Some(existing_id) = seen_hashes.get(hash) {
                        if *existing_id != mem.metadata.id {
                            duplicates.push(json!({
                                "id": mem.metadata.id,
                                "duplicate_of": existing_id,
                                "content_preview": mem.content.chars().take(100).collect::<String>(),
                                "importance": mem.metadata.importance,
                            }));
                            if !dry_run {
                                self.store.delete(galaxy, mem.metadata.id)?;
                                super::common::deindex(
                                    self.search.as_deref(),
                                    &mem.metadata.id.to_string(),
                                );
                            }
                        }
                    } else {
                        seen_hashes.insert(hash.clone(), mem.metadata.id);
                    }
                }

                let removed = if dry_run { 0 } else { duplicates.len() };

                Ok(json!({
                    "status": "success",
                    "galaxy": galaxy_name(galaxy),
                    "mode": mode,
                    "dry_run": dry_run,
                    "scanned": memories.len(),
                    "duplicates_found": duplicates.len(),
                    "removed": removed,
                    "duplicates": duplicates,
                }))
            }
            "content" => {
                let mut duplicates: Vec<Value> = Vec::new();
                let mut removed_count = 0u32;

                for i in 0..memories.len() {
                    for j in (i + 1)..memories.len() {
                        if memories[i].content == memories[j].content {
                            duplicates.push(json!({
                                "id": memories[j].metadata.id,
                                "duplicate_of": memories[i].metadata.id,
                                "content_preview": memories[j].content.chars().take(100).collect::<String>(),
                            }));
                            if !dry_run {
                                self.store.delete(galaxy, memories[j].metadata.id)?;
                                super::common::deindex(
                                    self.search.as_deref(),
                                    &memories[j].metadata.id.to_string(),
                                );
                                removed_count += 1;
                            }
                            break;
                        }
                    }
                }

                Ok(json!({
                    "status": "success",
                    "galaxy": galaxy_name(galaxy),
                    "mode": mode,
                    "dry_run": dry_run,
                    "scanned": memories.len(),
                    "duplicates_found": duplicates.len(),
                    "removed": removed_count,
                    "duplicates": duplicates,
                }))
            }
            _ => Err(wm_core::CoreError::InvalidArgs(format!(
                "Unknown mode: '{mode}'. Use 'hash' or 'content'"
            ))),
        }
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// `memory.export` — export memories in JSON, CSV, or Markdown format.
pub struct MemoryExportTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl MemoryExportTool {
    pub fn new(store: Arc<MemoryStore>) -> Self {
        Self {
            store,
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![Resource::Galaxy("codex".into())]),
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for MemoryExportTool {
    fn name(&self) -> &str {
        "memory.export"
    }
    fn gana(&self) -> Gana {
        Gana::WinnowingBasket
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Export memories in JSON, CSV, or Markdown format"
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let galaxy = parse_galaxy_or(args.get("galaxy").and_then(|v| v.as_str()), Galaxy::Codex)?;
        let format = args
            .get("format")
            .and_then(|v| v.as_str())
            .unwrap_or("json");
        let limit = args
            .get("limit")
            .and_then(serde_json::Value::as_u64)
            .unwrap_or(1000) as usize;

        let memories = self.store.scan(galaxy, limit)?;

        let exported = match format {
            "json" => {
                let entries: Vec<Value> = memories
                    .iter()
                    .map(|m| {
                        json!({
                            "id": m.metadata.id,
                            "content": &m.content,
                            "tags": &m.metadata.tags,
                            "importance": m.metadata.importance,
                            "created_at": m.metadata.created_at.to_rfc3339(),
                            "access_count": m.metadata.access_count,
                        })
                    })
                    .collect();
                serde_json::to_string_pretty(&entries).unwrap_or_default()
            }
            "csv" => {
                let mut csv = String::from("id,content,tags,importance,created_at,access_count\n");
                for m in &memories {
                    let tags = m.metadata.tags.join(";");
                    let content = m.content.replace('\n', " ").replace('"', "'");
                    let _ = writeln!(
                        csv,
                        "{},{},{},{:.3},{},{}",
                        m.metadata.id,
                        content,
                        tags,
                        m.metadata.importance,
                        m.metadata.created_at.to_rfc3339(),
                        m.metadata.access_count,
                    );
                }
                csv
            }
            "markdown" => {
                let mut md = format!("# Memory Export: {}\n\n", galaxy_name(galaxy));
                let _ = write!(md, "Total memories: {}\n\n", memories.len());
                for m in &memories {
                    let _ = write!(
                        md,
                        "## {}\n\n- **Importance**: {:.2}\n- **Tags**: {}\n- **Created**: {}\n- **Access Count**: {}\n\n{}\n\n---\n\n",
                        m.metadata.id,
                        m.metadata.importance,
                        m.metadata.tags.join(", "),
                        m.metadata.created_at.to_rfc3339(),
                        m.metadata.access_count,
                        m.content,
                    );
                }
                md
            }
            _ => {
                return Err(wm_core::CoreError::InvalidArgs(format!(
                    "Unknown format: '{format}'. Use json, csv, or markdown"
                )));
            }
        };

        Ok(json!({
            "status": "success",
            "galaxy": galaxy_name(galaxy),
            "format": format,
            "count": memories.len(),
            "export": exported,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use wm_core::{EpisodicKind, EpisodicRecord, Galaxy, Provenance, ProvenanceSource};
    use wm_memory::{Memory, MemoryStore};

    fn test_store() -> Arc<MemoryStore> {
        let dir = tempfile::tempdir().unwrap();
        Arc::new(MemoryStore::open_default(dir.path()).unwrap())
    }

    fn populate_memories(store: &Arc<MemoryStore>, galaxy: Galaxy) {
        let mut m1 = Memory::new(galaxy, "First memory about rust".into());
        m1.metadata.importance = 0.9;
        m1.metadata.tags = vec!["rust".into(), "programming".into()];
        let _ = store.put(galaxy, &m1);

        let mut m2 = Memory::new(galaxy, "Second memory about python".into());
        m2.metadata.importance = 0.5;
        m2.metadata.tags = vec!["python".into()];
        let _ = store.put(galaxy, &m2);

        let mut m3 = Memory::new(galaxy, "Third memory about rust".into());
        m3.metadata.importance = 0.3;
        m3.metadata.tags = vec!["rust".into(), "tutorial".into()];
        let _ = store.put(galaxy, &m3);
    }

    #[tokio::test]
    async fn episodic_search_filters_private_records() {
        let store = test_store();
        let public = EpisodicRecord::new(
            None,
            1,
            EpisodicKind::Observation,
            "public retrieval evidence",
            Provenance::new(ProvenanceSource::User),
        );
        let private = EpisodicRecord::new(
            None,
            2,
            EpisodicKind::Observation,
            "private retrieval evidence",
            Provenance::new(ProvenanceSource::User),
        )
        .with_visibility(true, false);
        store.episodic().append(&public).unwrap();
        store.episodic().append(&private).unwrap();

        let tool = MemoryEpisodicSearchTool::new(store);
        let mut ctx = Context::default();
        let result = tool
            .call(
                &mut ctx,
                json!({"query": "retrieval evidence", "limit": 10}),
            )
            .await
            .unwrap();
        assert_eq!(result["count"], 1);
        assert_eq!(result["results"][0]["id"], json!(public.id));
    }

    #[tokio::test]
    async fn memory_sort_by_importance_desc() {
        let store = test_store();
        populate_memories(&store, Galaxy::Codex);
        let tool = MemorySortTool::new(store);
        let mut ctx = Context::default();
        let v = tool
            .call(&mut ctx, json!({"sort_by": "importance", "order": "desc"}))
            .await
            .unwrap();
        assert_eq!(v["status"], "success");
        assert_eq!(v["returned"], 3);
        let mems = v["memories"].as_array().unwrap();
        assert!(mems[0]["importance"].as_f64().unwrap() >= mems[1]["importance"].as_f64().unwrap());
    }

    #[tokio::test]
    async fn memory_update_content_recomputes_hash() {
        let store = test_store();
        let mem = Memory::new(Galaxy::Codex, "original text".into());
        store.put(Galaxy::Codex, &mem).unwrap();
        let id = mem.metadata.id;
        let original_hash = mem.metadata.content_hash.clone();

        let tool = MemoryUpdateTool::new(store.clone(), None);
        let v = tool
            .call(
                &mut Context::default(),
                json!({"galaxy": "codex", "id": id.to_string(), "content": "changed text"}),
            )
            .await
            .unwrap();
        assert_eq!(v["status"], "success");

        // Regression: content updates used to keep the old content hash,
        // leaving dedup and hash lookups pointing at stale content.
        let stored = store.get(Galaxy::Codex, id).unwrap().unwrap();
        assert_eq!(stored.content, "changed text");
        assert_eq!(
            stored.metadata.content_hash,
            wm_memory::content_hash("changed text")
        );
        assert_ne!(stored.metadata.content_hash, original_hash);
    }

    #[tokio::test]
    async fn memory_sort_by_importance_asc() {
        let store = test_store();
        populate_memories(&store, Galaxy::Codex);
        let tool = MemorySortTool::new(store);
        let mut ctx = Context::default();
        let v = tool
            .call(&mut ctx, json!({"sort_by": "importance", "order": "asc"}))
            .await
            .unwrap();
        let mems = v["memories"].as_array().unwrap();
        assert!(mems[0]["importance"].as_f64().unwrap() <= mems[1]["importance"].as_f64().unwrap());
    }

    #[tokio::test]
    async fn memory_sort_by_recency() {
        let store = test_store();
        populate_memories(&store, Galaxy::Codex);
        let tool = MemorySortTool::new(store);
        let mut ctx = Context::default();
        let v = tool
            .call(&mut ctx, json!({"sort_by": "recency"}))
            .await
            .unwrap();
        assert_eq!(v["returned"], 3);
    }

    #[tokio::test]
    async fn memory_sort_invalid_field() {
        let store = test_store();
        let tool = MemorySortTool::new(store);
        let mut ctx = Context::default();
        let result = tool.call(&mut ctx, json!({"sort_by": "invalid"})).await;
        assert!(result.is_err());
    }

    #[tokio::test]
    async fn memory_sort_with_limit() {
        let store = test_store();
        populate_memories(&store, Galaxy::Codex);
        let tool = MemorySortTool::new(store);
        let mut ctx = Context::default();
        let v = tool.call(&mut ctx, json!({"limit": 2})).await.unwrap();
        assert_eq!(v["returned"], 2);
        assert_eq!(v["total"], 3);
    }

    #[tokio::test]
    async fn memory_filter_by_tag() {
        let store = test_store();
        populate_memories(&store, Galaxy::Codex);
        let tool = MemoryFilterTool::new(store);
        let mut ctx = Context::default();
        let v = tool
            .call(&mut ctx, json!({"tags": ["rust"]}))
            .await
            .unwrap();
        assert_eq!(v["matched"], 2);
    }

    #[tokio::test]
    async fn memory_filter_by_importance_range() {
        let store = test_store();
        populate_memories(&store, Galaxy::Codex);
        let tool = MemoryFilterTool::new(store);
        let mut ctx = Context::default();
        let v = tool
            .call(
                &mut ctx,
                json!({"min_importance": 0.4, "max_importance": 0.6}),
            )
            .await
            .unwrap();
        assert_eq!(v["matched"], 1);
    }

    #[tokio::test]
    async fn memory_filter_no_matches() {
        let store = test_store();
        populate_memories(&store, Galaxy::Codex);
        let tool = MemoryFilterTool::new(store);
        let mut ctx = Context::default();
        let v = tool
            .call(&mut ctx, json!({"tags": ["nonexistent"]}))
            .await
            .unwrap();
        assert_eq!(v["matched"], 0);
    }

    #[tokio::test]
    async fn memory_filter_combined_tags_and_importance() {
        let store = test_store();
        populate_memories(&store, Galaxy::Codex);
        let tool = MemoryFilterTool::new(store);
        let mut ctx = Context::default();
        let v = tool
            .call(&mut ctx, json!({"tags": ["rust"], "min_importance": 0.5}))
            .await
            .unwrap();
        assert_eq!(v["matched"], 1);
    }

    #[tokio::test]
    async fn memory_deduplicate_hash_dry_run() {
        let store = test_store();
        let m1 = Memory::new(Galaxy::Codex, "duplicate content".into());
        let m2 = Memory::new(Galaxy::Codex, "duplicate content".into());
        let _ = store.put(Galaxy::Codex, &m1);
        let _ = store.put(Galaxy::Codex, &m2);
        let _ = store.put(
            Galaxy::Codex,
            &Memory::new(Galaxy::Codex, "unique content".into()),
        );

        let tool = MemoryDeduplicateTool::new(store.clone(), None);
        let mut ctx = Context::default();
        let v = tool
            .call(&mut ctx, json!({"mode": "hash", "dry_run": true}))
            .await
            .unwrap();
        assert_eq!(v["duplicates_found"], 1);
        assert_eq!(v["removed"], 0);

        let memories = store.scan(Galaxy::Codex, 100).unwrap();
        assert_eq!(memories.len(), 3);
    }

    #[tokio::test]
    async fn memory_deduplicate_hash_execute() {
        let store = test_store();
        let m1 = Memory::new(Galaxy::Codex, "duplicate content".into());
        let m2 = Memory::new(Galaxy::Codex, "duplicate content".into());
        let _ = store.put(Galaxy::Codex, &m1);
        let _ = store.put(Galaxy::Codex, &m2);
        let _ = store.put(
            Galaxy::Codex,
            &Memory::new(Galaxy::Codex, "unique content".into()),
        );

        let tool = MemoryDeduplicateTool::new(store.clone(), None);
        let mut ctx = Context::default();
        let v = tool
            .call(&mut ctx, json!({"mode": "hash", "dry_run": false}))
            .await
            .unwrap();
        assert_eq!(v["duplicates_found"], 1);
        assert_eq!(v["removed"], 1);

        let memories = store.scan(Galaxy::Codex, 100).unwrap();
        assert_eq!(memories.len(), 2);
    }

    #[tokio::test]
    async fn memory_deduplicate_deindexes_removed_memories() {
        // Regression: deduplicate used to delete from LMDB without de-indexing,
        // so full-text search kept returning the removed duplicate.
        let (_dir, store, search) = hybrid_fixture();

        let m1 = Memory::new(Galaxy::Codex, "index drift duplicate".into());
        let m2 = Memory::new(Galaxy::Codex, "index drift duplicate".into());
        let id1 = m1.metadata.id;
        let id2 = m2.metadata.id;
        let _ = store.put(Galaxy::Codex, &m1);
        let _ = store.put(Galaxy::Codex, &m2);
        for mem in [&m1, &m2] {
            let mut writer = search.writer().unwrap();
            search
                .add_document(
                    &mut writer,
                    &mem.metadata.id.to_string(),
                    mem.metadata.galaxy.db_name(),
                    &mem.content,
                    &mem.metadata.tags,
                    mem.metadata.created_at.timestamp(),
                )
                .unwrap();
            search.commit(&mut writer).unwrap();
        }

        // Precondition: both duplicates are searchable.
        let before = search.search_ids("index drift", 100).unwrap();
        assert_eq!(before.len(), 2);

        let tool = MemoryDeduplicateTool::new(store.clone(), Some(search.clone()));
        let mut ctx = Context::default();
        let v = tool
            .call(&mut ctx, json!({"mode": "hash", "dry_run": false}))
            .await
            .unwrap();
        assert_eq!(v["removed"], 1);

        // The surviving memory is still searchable; the removed one is gone.
        // (LMDB scan order is by UUID, so either duplicate may be the keeper.)
        let after = search.search_ids("index drift", 100).unwrap();
        assert_eq!(after.len(), 1, "search index should only contain survivors");
        assert!(
            after.contains(&id1) || after.contains(&id2),
            "survivor should be one of the original memories"
        );
    }

    #[tokio::test]
    async fn memory_deduplicate_content_mode() {
        let store = test_store();
        let m1 = Memory::new(Galaxy::Codex, "same text".into());
        let m2 = Memory::new(Galaxy::Codex, "same text".into());
        let _ = store.put(Galaxy::Codex, &m1);
        let _ = store.put(Galaxy::Codex, &m2);

        let tool = MemoryDeduplicateTool::new(store, None);
        let mut ctx = Context::default();
        let v = tool
            .call(&mut ctx, json!({"mode": "content", "dry_run": true}))
            .await
            .unwrap();
        assert_eq!(v["duplicates_found"], 1);
    }

    #[tokio::test]
    async fn memory_deduplicate_no_duplicates() {
        let store = test_store();
        let _ = store.put(
            Galaxy::Codex,
            &Memory::new(Galaxy::Codex, "content a".into()),
        );
        let _ = store.put(
            Galaxy::Codex,
            &Memory::new(Galaxy::Codex, "content b".into()),
        );

        let tool = MemoryDeduplicateTool::new(store, None);
        let mut ctx = Context::default();
        let v = tool.call(&mut ctx, json!({})).await.unwrap();
        assert_eq!(v["duplicates_found"], 0);
    }

    #[tokio::test]
    async fn memory_deduplicate_invalid_mode() {
        let store = test_store();
        let tool = MemoryDeduplicateTool::new(store, None);
        let mut ctx = Context::default();
        let result = tool.call(&mut ctx, json!({"mode": "invalid"})).await;
        assert!(result.is_err());
    }

    #[tokio::test]
    async fn memory_export_json() {
        let store = test_store();
        populate_memories(&store, Galaxy::Codex);
        let tool = MemoryExportTool::new(store);
        let mut ctx = Context::default();
        let v = tool
            .call(&mut ctx, json!({"format": "json"}))
            .await
            .unwrap();
        assert_eq!(v["format"], "json");
        assert_eq!(v["count"], 3);
        assert!(v["export"].as_str().unwrap().contains("First memory"));
    }

    #[tokio::test]
    async fn memory_export_csv() {
        let store = test_store();
        populate_memories(&store, Galaxy::Codex);
        let tool = MemoryExportTool::new(store);
        let mut ctx = Context::default();
        let v = tool.call(&mut ctx, json!({"format": "csv"})).await.unwrap();
        let csv = v["export"].as_str().unwrap();
        assert!(csv.contains("id,content,tags"));
        assert!(csv.contains("First memory"));
    }

    #[tokio::test]
    async fn memory_export_markdown() {
        let store = test_store();
        populate_memories(&store, Galaxy::Codex);
        let tool = MemoryExportTool::new(store);
        let mut ctx = Context::default();
        let v = tool
            .call(&mut ctx, json!({"format": "markdown"}))
            .await
            .unwrap();
        let md = v["export"].as_str().unwrap();
        assert!(md.contains("# Memory Export"));
        assert!(md.contains("First memory"));
    }

    #[tokio::test]
    async fn memory_export_invalid_format() {
        let store = test_store();
        let tool = MemoryExportTool::new(store);
        let mut ctx = Context::default();
        let result = tool.call(&mut ctx, json!({"format": "xml"})).await;
        assert!(result.is_err());
    }

    #[tokio::test]
    async fn memory_export_empty_galaxy() {
        let store = test_store();
        let tool = MemoryExportTool::new(store);
        let mut ctx = Context::default();
        let v = tool
            .call(&mut ctx, json!({"format": "json"}))
            .await
            .unwrap();
        assert_eq!(v["count"], 0);
    }

    #[tokio::test]
    async fn memory_sort_and_filter_are_winnowing_basket_gana() {
        let store = test_store();
        assert_eq!(
            MemorySortTool::new(store.clone()).gana(),
            Gana::WinnowingBasket
        );
        assert_eq!(
            MemoryFilterTool::new(store.clone()).gana(),
            Gana::WinnowingBasket
        );
        assert_eq!(
            MemoryDeduplicateTool::new(store.clone(), None).gana(),
            Gana::WinnowingBasket
        );
        assert_eq!(MemoryExportTool::new(store).gana(), Gana::WinnowingBasket);
    }

    // ── hybrid_recall incident regression tests ─────────────────────────
    //
    // Mirrors the 2026-08-11 incident: `memory.hybrid_recall` with query
    // "smoke test from wmClient" and limit 20 returned 20 unrelated memories
    // at BM25 scores 0.5–1.0 with zero query-token overlap. The fix uses
    // OR semantics with a token-coverage floor and score floors, replacing
    // the old `scan(galaxy, 100)` lottery.

    #[test]
    fn hybrid_recall_routes_expose_query_schema() {
        let dir = tempfile::tempdir().unwrap();
        let store = Arc::new(MemoryStore::open_default(dir.path()).unwrap());
        for tool in [
            MemoryHybridRecallTool::new(store.clone(), None, None),
            MemoryHybridRecallTool::as_search(store, None, None),
        ] {
            let schema = tool.input_schema();
            assert_eq!(schema["type"], "object");
            assert!(schema["properties"].get("query").is_some());
            assert_eq!(schema["required"], json!(["query"]));
        }
    }

    /// Build a store + tantivy index pair where the memory and its index
    /// document are kept in sync (as the write path does).
    fn hybrid_fixture() -> (tempfile::TempDir, Arc<MemoryStore>, Arc<SearchEngine>) {
        let dir = tempfile::tempdir().unwrap();
        let store = Arc::new(MemoryStore::open_default(dir.path()).unwrap());
        let tantivy_dir = dir.path().join("tantivy");
        std::fs::create_dir_all(&tantivy_dir).unwrap();
        let search = Arc::new(SearchEngine::open(&tantivy_dir).unwrap());
        (dir, store, search)
    }

    fn index_memory(
        store: &Arc<MemoryStore>,
        search: &Arc<SearchEngine>,
        galaxy: Galaxy,
        content: &str,
    ) {
        let mem = Memory::new(galaxy, content.to_string());
        let id = mem.metadata.id;
        store.put(galaxy, &mem).unwrap();
        let mut writer = search.writer().unwrap();
        search
            .add_document(
                &mut writer,
                &id.to_string(),
                galaxy.db_name(),
                content,
                &mem.metadata.tags,
                mem.metadata.created_at.timestamp(),
            )
            .unwrap();
        search.commit(&mut writer).unwrap();
    }

    #[tokio::test]
    async fn hybrid_recall_excludes_private_memories() {
        let (_dir, store, search) = hybrid_fixture();

        // Private memory, indexed exactly like the write path.
        let mut priv_mem = Memory::new(Galaxy::Codex, "private secret plan alpha".to_string());
        priv_mem.metadata.is_private = true;
        let id = priv_mem.metadata.id;
        store.put(Galaxy::Codex, &priv_mem).unwrap();
        {
            let mut writer = search.writer().unwrap();
            search
                .add_document(
                    &mut writer,
                    &id.to_string(),
                    "codex",
                    "private secret plan alpha",
                    &[],
                    priv_mem.metadata.created_at.timestamp(),
                )
                .unwrap();
            search.commit(&mut writer).unwrap();
        }

        // Public memory with overlapping terms.
        index_memory(
            &store,
            &search,
            Galaxy::Codex,
            "public plan alpha documentation",
        );

        let tool = MemoryHybridRecallTool::new(store.clone(), Some(search.clone()), None);
        let v = tool
            .call(
                &mut Context::default(),
                json!({"query": "plan alpha", "galaxy": "codex"}),
            )
            .await
            .unwrap();
        let results = v["results"].as_array().unwrap();
        let contents: Vec<&str> = results
            .iter()
            .filter_map(|r| r["content"].as_str())
            .collect();
        assert!(
            !contents.iter().any(|c| c.contains("private")),
            "private memory leaked through hybrid recall: {results:?}"
        );
        assert!(
            contents.iter().any(|c| c.contains("public")),
            "public memory missing from hybrid recall: {results:?}"
        );
    }

    #[tokio::test]
    async fn batch_read_treats_private_as_miss() {
        let store = test_store();
        let mut priv_mem = Memory::new(Galaxy::Codex, "private batch note".into());
        priv_mem.metadata.is_private = true;
        let priv_id = priv_mem.metadata.id;
        store.put(Galaxy::Codex, &priv_mem).unwrap();
        let pub_mem = Memory::new(Galaxy::Codex, "public batch note".into());
        let pub_id = pub_mem.metadata.id;
        store.put(Galaxy::Codex, &pub_mem).unwrap();

        let tool = MemoryBatchReadTool::new(store);
        let v = tool
            .call(
                &mut Context::default(),
                json!({"galaxy": "codex", "ids": [priv_id.to_string(), pub_id.to_string()]}),
            )
            .await
            .unwrap();
        assert_eq!(v["found"], 1);
        assert_eq!(v["misses"], 1);
        assert!(
            !v["memories"]
                .as_array()
                .unwrap()
                .iter()
                .any(|m| m["content"].as_str().unwrap_or("").contains("private")),
            "private memory leaked through batch_read: {v}"
        );
    }

    #[tokio::test]
    async fn hybrid_recall_incident_query_returns_only_relevant() {
        let (_dir, store, search) = hybrid_fixture();
        index_memory(
            &store,
            &search,
            Galaxy::Codex,
            "smoke test from wmClient: verify recall",
        );
        index_memory(
            &store,
            &search,
            Galaxy::Codex,
            "NES Evolution and Impact: a history of the console wars",
        );
        index_memory(
            &store,
            &search,
            Galaxy::Codex,
            "Insights on The Gateless Gate: koans and zen practice",
        );
        let tool = MemoryHybridRecallTool::new(store, Some(search), None);
        let mut ctx = Context::default();
        let v = tool
            .call(
                &mut ctx,
                json!({"query": "smoke test", "galaxy": "codex", "limit": 5}),
            )
            .await
            .unwrap();
        let results = v["results"].as_array().unwrap();
        assert_eq!(
            results.len(),
            1,
            "incident query must not return unrelated memories: {results:?}"
        );
        let hit = &results[0];
        assert_eq!(hit["source"], "fts");
        assert!(
            hit["content"]
                .as_str()
                .unwrap()
                .contains("smoke test from wmClient")
        );
        assert!(hit["normalized_score"].as_f64().unwrap() > 0.0);
        assert_eq!(v["count"], 1);
    }

    #[tokio::test]
    async fn hybrid_recall_filters_stale_index_entries() {
        // A document indexed in tantivy but absent from LMDB must not be
        // returned (the old code wasted top-K slots on these).
        let (_dir, store, search) = hybrid_fixture();
        index_memory(
            &store,
            &search,
            Galaxy::Codex,
            "rust memory about ownership",
        );
        {
            let mut writer = search.writer().unwrap();
            search
                .add_document(
                    &mut writer,
                    "99999999-9999-9999-9999-999999999999",
                    "codex",
                    "rust ghost memory",
                    &[],
                    1700000000,
                )
                .unwrap();
            search.commit(&mut writer).unwrap();
        }

        let tool = MemoryHybridRecallTool::new(store, Some(search), None);
        let mut ctx = Context::default();
        let v = tool
            .call(&mut ctx, json!({"query": "rust", "limit": 10}))
            .await
            .unwrap();
        let results = v["results"].as_array().unwrap();
        assert_eq!(results.len(), 1);
        assert_ne!(
            results[0]["id"].as_str().unwrap(),
            "99999999-9999-9999-9999-999999999999"
        );
    }

    #[tokio::test]
    async fn hybrid_recall_respects_min_score_arg() {
        let (_dir, store, search) = hybrid_fixture();
        index_memory(&store, &search, Galaxy::Codex, "alpha");
        let filler = format!("alpha {}", "zzz ".repeat(400));
        index_memory(&store, &search, Galaxy::Codex, &filler);

        // No threshold: both match.
        let tool = MemoryHybridRecallTool::new(store.clone(), Some(search.clone()), None);
        let mut ctx = Context::default();
        let v = tool
            .call(&mut ctx, json!({"query": "alpha", "limit": 10}))
            .await
            .unwrap();
        assert_eq!(v["count"], 2);

        // min_score between the two scores: only the strong match remains.
        let scores: Vec<f64> = v["results"]
            .as_array()
            .unwrap()
            .iter()
            .map(|r| r["score"].as_f64().unwrap())
            .collect();
        let lo = scores.iter().copied().fold(f64::MAX, f64::min);
        let hi = scores.iter().copied().fold(0.0, f64::max);
        let mid = f64::midpoint(hi, lo);

        let v = tool
            .call(
                &mut ctx,
                json!({"query": "alpha", "limit": 10, "min_score": mid}),
            )
            .await
            .unwrap();
        assert_eq!(v["count"], 1);
        assert!((v["results"][0]["score"].as_f64().unwrap() - hi).abs() < 1e-3);
    }

    #[tokio::test]
    async fn hybrid_recall_or_coverage_finds_partial_matches() {
        // OR + token-coverage finds partial matches without a separate
        // fallback phase.  The doc covering 3/4 query terms survives the
        // 2/4 coverage floor; the 1/4 doc is filtered out.
        let (_dir, store, search) = hybrid_fixture();
        index_memory(&store, &search, Galaxy::Codex, "alpha only here");
        index_memory(&store, &search, Galaxy::Codex, "alpha beta gamma delta");

        let tool = MemoryHybridRecallTool::new(store, Some(search), None);
        let mut ctx = Context::default();
        let v = tool
            .call(&mut ctx, json!({"query": "alpha beta gamma", "limit": 10}))
            .await
            .unwrap();
        let results = v["results"].as_array().unwrap();
        // 3-term query: 2/3 coverage floor.  "alpha beta gamma delta" covers
        // 3/3, "alpha only here" covers 1/3 → filtered.
        assert_eq!(results.len(), 1);
        assert!(
            results[0]["content"]
                .as_str()
                .unwrap()
                .contains("alpha beta gamma")
        );

        // 4-term query: 2/4 coverage floor.  "alpha beta gamma delta" covers
        // 3/4, "alpha only here" covers 1/4 → filtered.
        let v = tool
            .call(
                &mut ctx,
                json!({"query": "alpha beta gamma zeta", "limit": 10}),
            )
            .await
            .unwrap();
        let results = v["results"].as_array().unwrap();
        assert_eq!(
            results.len(),
            1,
            "OR + coverage must require 2/4 token coverage: {results:?}"
        );
        assert!(
            results[0]["content"]
                .as_str()
                .unwrap()
                .contains("alpha beta gamma")
        );
        for r in results {
            assert!(
                matches!(r["source"].as_str(), Some("fts")),
                "results should be tagged fts"
            );
        }
    }
}
