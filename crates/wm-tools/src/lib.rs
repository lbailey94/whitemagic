//! WhiteMagic v5 Tools — 229 tools + fractal meta-tool
//!
//! Tools: memory.create, memory.read, memory.list, memory.delete,
//! memory.query, memory.search, memory.associate, memory.associations,
//! gnosis, tools.list, karma.report, dharma.status, and the `wm` meta-tool.

#![forbid(unsafe_code)]
#![allow(clippy::significant_drop_tightening)]

pub mod embedding_router;
pub mod expansion;
pub mod nlu;
pub mod profiles;

use async_trait::async_trait;

use std::sync::Arc;

use serde_json::{Value, json};
use wm_cognitive::GanYingBus;
use wm_core::{Capability, Context, EffectRow, Galaxy, Gana, Resource, Tool, ToolStats};
use wm_dispatch::{DispatchPipeline, ToolRegistry, ToolRegistryBuilder};
use wm_governance::{DharmaGate, KarmaLedger, ResourceRules};
use wm_memory::{
    Association, AssociationStore, ConversationalSearch, Memory, MemoryQuery, MemoryStore,
    SearchEngine, VectorStore,
};
use wm_substrate::SubstrateMonitor;
use wm_substrate::anomaly::AnomalyDetector;
use wm_substrate::homeostatic::HomeostaticLoop;
use wm_substrate::sensorimotor::{ReflexLoop, SensorimotorBus};

use crate::expansion::common::{
    bool_prop, fresh_write_galaxies, int_prop, memory_galaxy_reads, memory_galaxy_writes, num_prop,
    schema, str_array_prop, str_prop,
};

// ── Tool: memory.create ──────────────────────────────────────────────

/// Create a memory in a galaxy.
///
/// If a `SearchEngine` is provided, the memory is also indexed into Tantivy
/// for full-text search immediately after the LMDB write.
pub struct MemoryCreateTool {
    store: Arc<MemoryStore>,
    search: Option<Arc<SearchEngine>>,
    stats: ToolStats,
    effects: EffectRow,
}

impl MemoryCreateTool {
    pub fn new(store: Arc<MemoryStore>, search: Option<Arc<SearchEngine>>) -> Self {
        Self {
            store,
            search,
            stats: ToolStats::default(),
            effects: EffectRow {
                // Writes whichever galaxy the caller selects at runtime.
                // Citta is excluded: a fresh write into the consciousness
                // stream is refused by the pipeline's runtime Satya check.
                writes: fresh_write_galaxies(),
                invokes: vec![Capability::MemoryWrite],
                ..Default::default()
            },
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for MemoryCreateTool {
    fn name(&self) -> &str {
        "memory.create"
    }
    fn gana(&self) -> Gana {
        Gana::Encampment
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn input_schema(&self) -> Value {
        schema(
            &json!({
                "content": str_prop("Memory content (text)"),
                "galaxy": str_prop("Target galaxy (default codex)"),
                "tags": str_array_prop("Optional tags"),
            }),
            &["content"],
        )
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let content = args
            .get("content")
            .and_then(|v| v.as_str())
            .ok_or_else(|| wm_core::CoreError::InvalidArgs("content (string) required".into()))?;
        let galaxy_str = args
            .get("galaxy")
            .and_then(|v| v.as_str())
            .unwrap_or("codex");
        let galaxy = parse_galaxy(galaxy_str)?;
        let tags: Vec<String> = args
            .get("tags")
            .and_then(|v| v.as_array())
            .map(|a| {
                a.iter()
                    .filter_map(|v| v.as_str().map(String::from))
                    .collect()
            })
            .unwrap_or_default();

        if let Some(search) = &self.search {
            if search.is_readonly() {
                return Err(wm_core::CoreError::InvalidArgs(
                    "read-only mode: memory.create disabled (another process owns the index)"
                        .into(),
                ));
            }
        }
        let mut memory = Memory::new(galaxy, content.to_string());
        memory.metadata.tags = tags;
        let id = memory.metadata.id;
        self.store.put(galaxy, &memory)?;

        // Index into Tantivy if search engine is available (non-fatal)
        if let Some(search) = &self.search {
            if let Err(e) = (|| {
                let mut writer = search.writer()?;
                search.add_document(
                    &mut writer,
                    &id.to_string(),
                    galaxy.db_name(),
                    content,
                    &memory.metadata.tags,
                    memory.metadata.created_at.timestamp(),
                )?;
                search.commit(&mut writer)?;
                Ok::<(), wm_core::CoreError>(())
            })() {
                tracing::warn!("Tantivy indexing failed for memory {id}: {e}");
            }
        }

        Ok(json!({
            "status": "success",
            "id": id.to_string(),
            "galaxy": galaxy.db_name(),
            "content_hash": memory.metadata.content_hash,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── Tool: memory.read ────────────────────────────────────────────────

/// Read a memory by ID from a galaxy.
pub struct MemoryReadTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl MemoryReadTool {
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
impl Tool for MemoryReadTool {
    fn name(&self) -> &str {
        "memory.read"
    }
    fn gana(&self) -> Gana {
        Gana::WinnowingBasket
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn input_schema(&self) -> Value {
        schema(
            &json!({
                "id": str_prop("Memory UUID"),
                "galaxy": str_prop("Galaxy containing the memory (default codex)"),
            }),
            &["id"],
        )
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let id_str = args
            .get("id")
            .and_then(|v| v.as_str())
            .ok_or_else(|| wm_core::CoreError::InvalidArgs("id (string) required".into()))?;
        let id = uuid::Uuid::parse_str(id_str)
            .map_err(|e| wm_core::CoreError::InvalidArgs(format!("invalid UUID: {e}")))?;
        let galaxy_str = args
            .get("galaxy")
            .and_then(|v| v.as_str())
            .unwrap_or("codex");
        let galaxy = parse_galaxy(galaxy_str)?;

        match self.store.get(galaxy, id)? {
            Some(memory) => {
                if memory.metadata.is_private {
                    // Private memories never appear in MCP responses —
                    // treat them as not found rather than leaking content.
                    return Ok(json!({
                        "status": "not_found",
                        "id": id_str,
                        "galaxy": galaxy.db_name(),
                    }));
                }
                Ok(json!({
                    "status": "success",
                    "id": memory.metadata.id.to_string(),
                    "galaxy": memory.metadata.galaxy.db_name(),
                    "content": memory.content,
                    "tags": memory.metadata.tags,
                    "created_at": memory.metadata.created_at.to_rfc3339(),
                }))
            }
            None => Ok(json!({
                "status": "not_found",
                "id": id_str,
                "galaxy": galaxy.db_name(),
            })),
        }
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── Tool: memory.list ────────────────────────────────────────────────

/// List memories from a galaxy (up to limit).
pub struct MemoryListTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl MemoryListTool {
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
impl Tool for MemoryListTool {
    fn name(&self) -> &str {
        "memory.list"
    }
    fn gana(&self) -> Gana {
        Gana::WinnowingBasket
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn input_schema(&self) -> Value {
        schema(
            &json!({
                "galaxy": str_prop("Galaxy to list (default codex)"),
                "limit": int_prop("Maximum entries (default 20)"),
            }),
            &[],
        )
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let galaxy_str = args
            .get("galaxy")
            .and_then(|v| v.as_str())
            .unwrap_or("codex");
        let limit = args
            .get("limit")
            .and_then(serde_json::Value::as_u64)
            .unwrap_or(20) as usize;
        let galaxy = parse_galaxy(galaxy_str)?;

        let memories = self.store.scan(galaxy, limit)?;
        let total = self.store.count(galaxy)?;

        let entries: Vec<Value> = memories
            .iter()
            .filter(|m| crate::expansion::common::mcp_visible(m))
            .map(|m| {
                json!({
                    "id": m.metadata.id.to_string(),
                    "content_preview": m.content.chars().take(80).collect::<String>(),
                    "tags": m.metadata.tags,
                    "created_at": m.metadata.created_at.to_rfc3339(),
                })
            })
            .collect();

        Ok(json!({
            "status": "success",
            "galaxy": galaxy.db_name(),
            "total": total,
            "returned": entries.len(),
            "memories": entries,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── Tool: gnosis ─────────────────────────────────────────────────────

/// System introspection — returns basic system state.
pub struct GnosisTool {
    store: Arc<MemoryStore>,
    tool_count: usize,
    stats: ToolStats,
    effects: EffectRow,
}

impl GnosisTool {
    pub fn new(store: Arc<MemoryStore>) -> Self {
        Self {
            store,
            tool_count: 0,
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![Resource::Galaxy("substrate".into())]),
        }
    }

    /// Create with a known tool count (computed at registration time).
    pub fn with_tool_count(store: Arc<MemoryStore>, tool_count: usize) -> Self {
        Self {
            store,
            tool_count,
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![Resource::Galaxy("substrate".into())]),
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for GnosisTool {
    fn name(&self) -> &str {
        "gnosis"
    }
    fn gana(&self) -> Gana {
        Gana::Root
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    async fn call(&self, ctx: &mut Context, _args: Value) -> wm_core::Result<Value> {
        let mut galaxy_stats = serde_json::Map::new();
        for galaxy in Galaxy::all() {
            let count = self.store.count(galaxy).unwrap_or(0);
            if count > 0 {
                galaxy_stats.insert(galaxy.db_name().to_string(), json!(count));
            }
        }

        Ok(json!({
            "status": "success",
            "version": env!("CARGO_PKG_VERSION"),
            "store_path": self.store.path().display().to_string(),
            "brain_wave": format!("{:?}", ctx.brain_wave),
            "available_tools": self.tool_count,
            "galaxies_with_data": galaxy_stats.len(),
            "galaxy_counts": galaxy_stats,
            "ganas": Gana::COUNT,
            "galaxies": Galaxy::COUNT,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── Tool: tools.list ─────────────────────────────────────────────────

/// List all registered tools.
pub struct ToolsListTool {
    registry: Arc<ToolRegistry>,
    stats: ToolStats,
    effects: EffectRow,
}

impl ToolsListTool {
    #[must_use]
    pub fn new(registry: Arc<ToolRegistry>) -> Self {
        Self {
            registry,
            stats: ToolStats::default(),
            effects: EffectRow::pure(),
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for ToolsListTool {
    fn name(&self) -> &str {
        "tools.list"
    }
    fn gana(&self) -> Gana {
        Gana::Ghost
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    async fn call(&self, ctx: &mut Context, _args: Value) -> wm_core::Result<Value> {
        let available = self.registry.available_in(ctx.brain_wave);
        let tools: Vec<Value> = available
            .iter()
            .map(|t| {
                // MCP tool annotations derived from the declared effects —
                // clients and registries use these for safety decisions.
                let effects = t.effects();
                json!({
                    "name": t.name(),
                    "gana": format!("{:?}", t.gana()),
                    "description": t.description(),
                    "input_schema": t.input_schema(),
                    "annotations": {
                        "readOnlyHint": effects.writes.is_empty(),
                        "destructiveHint": effects.destructive,
                    },
                })
            })
            .collect();
        Ok(json!({
            "status": "success",
            "brain_wave": format!("{:?}", ctx.brain_wave),
            "total": tools.len(),
            "tools": tools,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── Tool: memory.delete ──────────────────────────────────────────────

/// Delete a memory by ID from a galaxy.
///
/// If a `SearchEngine` is provided, the document is also removed from the
/// Tantivy index after the LMDB delete.
pub struct MemoryDeleteTool {
    store: Arc<MemoryStore>,
    search: Option<Arc<SearchEngine>>,
    stats: ToolStats,
    effects: EffectRow,
}

impl MemoryDeleteTool {
    pub fn new(store: Arc<MemoryStore>, search: Option<Arc<SearchEngine>>) -> Self {
        Self {
            store,
            search,
            stats: ToolStats::default(),
            effects: EffectRow {
                // Delete reads the record it removes (index cleanup), so the
                // read-modify-write declaration covers the runtime galaxy.
                writes: memory_galaxy_writes(),
                reads: memory_galaxy_reads(),
                invokes: vec![Capability::MemoryWrite],
                destructive: true,
                ..Default::default()
            },
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for MemoryDeleteTool {
    fn name(&self) -> &str {
        "memory.delete"
    }
    fn gana(&self) -> Gana {
        Gana::Encampment
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn input_schema(&self) -> Value {
        schema(
            &json!({
                "id": str_prop("Memory UUID"),
                "galaxy": str_prop("Galaxy containing the memory (default codex)"),
                "confirm": bool_prop("Required — memory.delete is destructive"),
            }),
            &["id", "confirm"],
        )
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let id_str = args
            .get("id")
            .and_then(|v| v.as_str())
            .ok_or_else(|| wm_core::CoreError::InvalidArgs("id (string) required".into()))?;
        let id = uuid::Uuid::parse_str(id_str)
            .map_err(|e| wm_core::CoreError::InvalidArgs(format!("invalid UUID: {e}")))?;
        let galaxy_str = args
            .get("galaxy")
            .and_then(|v| v.as_str())
            .unwrap_or("codex");
        let galaxy = parse_galaxy(galaxy_str)?;

        if let Some(search) = &self.search {
            if search.is_readonly() {
                return Err(wm_core::CoreError::InvalidArgs(
                    "read-only mode: memory.delete disabled (another process owns the index)"
                        .into(),
                ));
            }
        }
        let deleted = self.store.delete(galaxy, id)?;

        // Remove from Tantivy index if search engine is available (non-fatal)
        if deleted {
            if let Some(search) = &self.search {
                if let Err(e) = (|| {
                    let mut writer = search.writer()?;
                    search.delete_document(&mut writer, id_str)?;
                    search.commit(&mut writer)?;
                    Ok::<(), wm_core::CoreError>(())
                })() {
                    tracing::warn!("Tantivy de-indexing failed for memory {id_str}: {e}");
                }
            }
        }

        Ok(json!({
            "status": if deleted { "success" } else { "not_found" },
            "id": id_str,
            "galaxy": galaxy.db_name(),
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── Tool: memory.query ───────────────────────────────────────────────

/// Query memories with filters (tags, importance, temporal range).
pub struct MemoryQueryTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl MemoryQueryTool {
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
impl Tool for MemoryQueryTool {
    fn name(&self) -> &str {
        "memory.query"
    }
    fn gana(&self) -> Gana {
        Gana::WinnowingBasket
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn input_schema(&self) -> Value {
        schema(
            &json!({
                "query": str_prop("Query text (used by the meta-tool's routing validation)"),
                "galaxy": str_prop("Galaxy to query (default codex)"),
                "tags": str_array_prop("Filter: memories with all of these tags"),
                "min_importance": num_prop("Filter: minimum importance (0-1)"),
                "max_importance": num_prop("Filter: maximum importance (0-1)"),
                "limit": int_prop("Maximum entries (default 50)"),
            }),
            &[],
        )
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let galaxy_str = args
            .get("galaxy")
            .and_then(|v| v.as_str())
            .unwrap_or("codex");
        let galaxy = parse_galaxy(galaxy_str)?;
        let limit = args
            .get("limit")
            .and_then(serde_json::Value::as_u64)
            .unwrap_or(50) as usize;
        let mut query = MemoryQuery::new().with_limit(limit);

        if let Some(tags) = args.get("tags").and_then(|v| v.as_array()) {
            let tag_list: Vec<String> = tags
                .iter()
                .filter_map(|v| v.as_str().map(String::from))
                .collect();
            if !tag_list.is_empty() {
                query = query.with_tags(tag_list);
            }
        }

        let min_imp = args
            .get("min_importance")
            .and_then(serde_json::Value::as_f64);
        let max_imp = args
            .get("max_importance")
            .and_then(serde_json::Value::as_f64);
        if let (Some(min), Some(max)) = (min_imp, max_imp) {
            query = query.with_importance_range(min as f32, max as f32);
        } else if let Some(min) = min_imp {
            query = query.with_importance_range(min as f32, 1.0);
        }

        let memories = self.store.query(galaxy, &query)?;

        let entries: Vec<Value> = memories
            .iter()
            .filter(|m| crate::expansion::common::mcp_visible(m))
            .map(|m| {
                json!({
                    "id": m.metadata.id.to_string(),
                    "content_preview": m.content.chars().take(80).collect::<String>(),
                    "tags": m.metadata.tags,
                    "importance": m.metadata.importance,
                    "created_at": m.metadata.created_at.to_rfc3339(),
                })
            })
            .collect();

        Ok(json!({
            "status": "success",
            "galaxy": galaxy.db_name(),
            "total": entries.len(),
            "memories": entries,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── Tool: memory.search ──────────────────────────────────────────────

/// Full-text search via Tantivy (BM25 scoring).
pub struct MemorySearchTool {
    search: Arc<SearchEngine>,
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl MemorySearchTool {
    #[must_use]
    pub fn new(search: Arc<SearchEngine>, store: Arc<MemoryStore>) -> Self {
        Self {
            search,
            store,
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![Resource::Galaxy("codex".into())]),
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for MemorySearchTool {
    fn name(&self) -> &str {
        "memory.search"
    }
    fn gana(&self) -> Gana {
        Gana::WinnowingBasket
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn input_schema(&self) -> Value {
        schema(
            &json!({
                "query": str_prop("Full-text query"),
                "galaxy": str_prop("Galaxy filter (default: all galaxies)"),
                "limit": int_prop("Maximum results (default 20)"),
                "min_score": num_prop("Absolute BM25 score floor"),
                "min_score_ratio": num_prop("Relative floor: reject hits below this fraction of the top score"),
            }),
            &["query"],
        )
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let query = args
            .get("query")
            .and_then(|v| v.as_str())
            .ok_or_else(|| wm_core::CoreError::InvalidArgs("query (string) required".into()))?;
        let limit = args
            .get("limit")
            .and_then(serde_json::Value::as_u64)
            .unwrap_or(20) as usize;
        let min_score = args
            .get("min_score")
            .and_then(serde_json::Value::as_f64)
            .map(|v| v as f32)
            .filter(|v| *v > 0.0);
        let min_score_ratio = args
            .get("min_score_ratio")
            .and_then(serde_json::Value::as_f64)
            .map(|v| v as f32)
            .filter(|v| *v > 0.0 && *v < 1.0);
        let galaxy_str = args.get("galaxy").and_then(|v| v.as_str());

        let mut opts = wm_memory::SearchOptions {
            limit,
            min_score,
            relative_floor: min_score_ratio,
            ..wm_memory::SearchOptions::default()
        };
        if let Some(g) = galaxy_str {
            opts.galaxy = Some(parse_galaxy(g)?);
        }
        let results = self.search.search_opt(query, &opts)?;

        // Stale verification: index entries whose memory no longer exists in
        // LMDB are dropped, and the preview comes from the verified LMDB copy.
        // Private memories are dropped here too — they never appear in MCP
        // search responses.
        let entries: Vec<Value> = results
            .iter()
            .filter_map(|r| {
                let galaxy = wm_core::Galaxy::from_db_name(&r.galaxy)?;
                let id = uuid::Uuid::parse_str(&r.memory_id).ok()?;
                let mem = self.store.get(galaxy, id).ok().flatten()?;
                if !crate::expansion::common::mcp_visible(&mem) {
                    return None;
                }
                Some(json!({
                    "memory_id": r.memory_id,
                    "galaxy": r.galaxy,
                    "score": r.score,
                    "normalized_score": r.normalized_score,
                    "content_preview": wm_memory::scrub_text(&mem.content).chars().take(120).collect::<String>(),
                }))
            })
            .collect();

        Ok(json!({
            "status": "success",
            "query": query,
            "total": entries.len(),
            "results": entries,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── Tool: memory.chat (conversational search) ─────────────────────

/// Conversational memory search with LRU caching and query classification.
///
/// Wraps `ConversationalSearch` (Phase N5) for sub-50ms hybrid search.
pub struct MemoryChatTool {
    search: std::sync::Mutex<ConversationalSearch>,
    stats: ToolStats,
    effects: EffectRow,
}

impl MemoryChatTool {
    #[must_use]
    pub fn new(search: ConversationalSearch) -> Self {
        Self {
            search: std::sync::Mutex::new(search),
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![Resource::Galaxy("codex".into())]),
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for MemoryChatTool {
    fn name(&self) -> &str {
        "memory.chat"
    }
    fn gana(&self) -> Gana {
        Gana::WinnowingBasket
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn input_schema(&self) -> Value {
        schema(
            &json!({
                "query": str_prop("Conversational query"),
                "galaxy": str_prop("Optional galaxy filter"),
                "limit": int_prop("Maximum results"),
            }),
            &["query"],
        )
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let query = args
            .get("query")
            .and_then(|v| v.as_str())
            .ok_or_else(|| wm_core::CoreError::InvalidArgs("query (string) required".into()))?;
        let limit = args
            .get("limit")
            .and_then(serde_json::Value::as_u64)
            .map(|n| n as usize);
        let galaxy_str = args.get("galaxy").and_then(|v| v.as_str());

        let galaxy = match galaxy_str {
            Some(g) => Some(parse_galaxy(g)?),
            None => None,
        };

        let (results, metrics) = {
            let search = self
                .search
                .lock()
                .map_err(|e| wm_core::CoreError::Tool(format!("search lock: {e}")))?;
            let results = search.search_in_galaxy(query, limit, galaxy);
            let metrics = search.metrics();
            (results, metrics)
        };

        let entries: Vec<Value> = results
            .iter()
            .map(|r| {
                json!({
                    "memory_id": r.memory_id,
                    "galaxy": format!("{:?}", r.galaxy),
                    "score": r.score,
                    "snippet": r.snippet,
                    "from_cache": r.from_cache,
                    "latency_us": r.latency_us,
                })
            })
            .collect();

        Ok(json!({
            "status": "success",
            "query": query,
            "total": entries.len(),
            "results": entries,
            "metrics": {
                "total_queries": metrics.total_queries,
                "cache_hits": metrics.cache_hits,
                "cache_misses": metrics.cache_misses,
                "cache_hit_rate": metrics.cache_hit_rate(),
                "avg_latency_ms": metrics.avg_latency_ms(),
                "meets_latency_target": metrics.meets_latency_target(),
            },
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── Tool: memory.vector.search ───────────────────────────────────────

/// Vector similarity search over memory embeddings.
///
/// Searches for memories by embedding vector similarity (cosine similarity).
/// Accepts either a raw embedding vector or a memory ID to find similar memories.
/// Optionally filters by galaxy.
pub struct MemoryVectorSearchTool {
    store: Arc<MemoryStore>,
    vector_store: Arc<std::sync::Mutex<VectorStore>>,
    stats: ToolStats,
    effects: EffectRow,
}

impl MemoryVectorSearchTool {
    /// Create a new vector search tool.
    ///
    /// The `VectorStore` is lazily loaded from LMDB on first search.
    #[must_use]
    pub fn new(store: Arc<MemoryStore>, vector_store: Arc<std::sync::Mutex<VectorStore>>) -> Self {
        Self {
            store,
            vector_store,
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![Resource::VectorStore]),
        }
    }

    /// Ensure the vector store is loaded from LMDB.
    fn ensure_loaded(&self) -> wm_core::Result<()> {
        let mut vs = self
            .vector_store
            .lock()
            .map_err(|e| wm_core::CoreError::Tool(format!("vector store lock: {e}")))?;
        if !vs.is_loaded() {
            vs.load(&self.store)?;
        }
        drop(vs);
        Ok(())
    }
}

#[async_trait]
#[async_trait]
impl Tool for MemoryVectorSearchTool {
    fn name(&self) -> &str {
        "memory.vector.search"
    }
    fn gana(&self) -> Gana {
        Gana::WinnowingBasket
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        self.ensure_loaded()?;

        let limit = args
            .get("limit")
            .and_then(serde_json::Value::as_u64)
            .unwrap_or(10) as usize;
        let galaxy_str = args.get("galaxy").and_then(|v| v.as_str());
        let galaxy_filter = match galaxy_str {
            Some(g) => Some(parse_galaxy(g)?),
            None => None,
        };

        // Two modes: search by embedding vector, or search by memory ID
        let results = if let Some(id_str) = args.get("memory_id").and_then(|v| v.as_str()) {
            // Search similar to a given memory ID
            let memory_id = uuid::Uuid::parse_str(id_str).map_err(|e| {
                wm_core::CoreError::InvalidArgs(format!("Invalid memory_id UUID: {e}"))
            })?;

            let vs = self
                .vector_store
                .lock()
                .map_err(|e| wm_core::CoreError::Tool(format!("vector store lock: {e}")))?;
            vs.search_similar_to(memory_id, limit)
        } else if let Some(embedding_arr) = args.get("embedding").and_then(|v| v.as_array()) {
            // Search by raw embedding vector
            let embedding: Vec<f32> = embedding_arr
                .iter()
                .filter_map(|v| v.as_f64().map(|f| f as f32))
                .collect();

            if embedding.is_empty() {
                return Err(wm_core::CoreError::InvalidArgs(
                    "embedding (array of numbers) or memory_id (string) required".into(),
                ));
            }

            let vs = self
                .vector_store
                .lock()
                .map_err(|e| wm_core::CoreError::Tool(format!("vector store lock: {e}")))?;
            vs.search(&embedding, limit, galaxy_filter)
        } else {
            return Err(wm_core::CoreError::InvalidArgs(
                "Either 'embedding' (array of floats) or 'memory_id' (UUID string) is required"
                    .into(),
            ));
        };

        let entries: Vec<Value> = results
            .iter()
            .filter_map(|r| {
                // Fetch content preview from the verified LMDB copy. Private
                // memories never appear in MCP vector search responses.
                // Vector-store entries without a backing memory keep their
                // slot with an empty preview (unverifiable, no content leak).
                let stored = self.store.get(r.galaxy, r.memory_id).ok().flatten();
                if let Some(mem) = &stored {
                    if !crate::expansion::common::mcp_visible(mem) {
                        return None;
                    }
                }
                let preview = stored
                    .map(|m| m.content.chars().take(120).collect::<String>())
                    .unwrap_or_default();
                Some(json!({
                    "memory_id": r.memory_id.to_string(),
                    "galaxy": r.galaxy.db_name(),
                    "score": r.score,
                    "content_preview": preview,
                }))
            })
            .collect();

        Ok(json!({
            "status": "success",
            "total": entries.len(),
            "results": entries,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── Tool: memory.associate ───────────────────────────────────────────

/// Create a cross-galaxy association between two memories.
pub struct MemoryAssociateTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl MemoryAssociateTool {
    pub fn new(store: Arc<MemoryStore>) -> Self {
        Self {
            store,
            stats: ToolStats::default(),
            effects: EffectRow {
                writes: vec![Resource::Galaxy("associations".into())],
                invokes: vec![Capability::MemoryWrite],
                ..Default::default()
            },
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for MemoryAssociateTool {
    fn name(&self) -> &str {
        "memory.associate"
    }
    fn gana(&self) -> Gana {
        Gana::Net
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let source_str = args.get("source").and_then(|v| v.as_str()).ok_or_else(|| {
            wm_core::CoreError::InvalidArgs("source (UUID string) required".into())
        })?;
        let target_str = args.get("target").and_then(|v| v.as_str()).ok_or_else(|| {
            wm_core::CoreError::InvalidArgs("target (UUID string) required".into())
        })?;
        let source = uuid::Uuid::parse_str(source_str)
            .map_err(|e| wm_core::CoreError::InvalidArgs(format!("invalid source UUID: {e}")))?;
        let target = uuid::Uuid::parse_str(target_str)
            .map_err(|e| wm_core::CoreError::InvalidArgs(format!("invalid target UUID: {e}")))?;
        let weight = args
            .get("weight")
            .and_then(serde_json::Value::as_f64)
            .unwrap_or(1.0) as f32;
        let assoc_type = args
            .get("type")
            .and_then(|v| v.as_str())
            .unwrap_or("related");
        let link_type = wm_memory::LinkType::from_str_lossy(assoc_type);

        let assoc = Association::new(source, target, link_type, weight);
        let assoc_store = AssociationStore::open(self.store.env())?;
        assoc_store.put(self.store.env(), &assoc)?;

        Ok(json!({
            "status": "success",
            "source": source_str,
            "target": target_str,
            "weight": weight,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── Tool: memory.associations ────────────────────────────────────────

/// Find associations for a memory (incoming or outgoing).
pub struct MemoryAssociationsTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl MemoryAssociationsTool {
    pub fn new(store: Arc<MemoryStore>) -> Self {
        Self {
            store,
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![Resource::Galaxy("associations".into())]),
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for MemoryAssociationsTool {
    fn name(&self) -> &str {
        "memory.associations"
    }
    fn gana(&self) -> Gana {
        Gana::Net
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let id_str = args
            .get("id")
            .and_then(|v| v.as_str())
            .ok_or_else(|| wm_core::CoreError::InvalidArgs("id (UUID string) required".into()))?;
        let id = uuid::Uuid::parse_str(id_str)
            .map_err(|e| wm_core::CoreError::InvalidArgs(format!("invalid UUID: {e}")))?;
        let direction = args
            .get("direction")
            .and_then(|v| v.as_str())
            .unwrap_or("both");

        let assoc_store = AssociationStore::open(self.store.env())?;

        let mut entries = Vec::new();

        if direction == "from" || direction == "both" {
            for a in assoc_store.find_from(self.store.env(), id)? {
                entries.push(json!({
                    "source": a.source.to_string(),
                    "target": a.target.to_string(),
                    "weight": a.weight,
                    "link_type": a.link_type.as_str(),
                    "co_activation_count": a.co_activation_count,
                    "direction": "outgoing",
                }));
            }
        }
        if direction == "to" || direction == "both" {
            for a in assoc_store.find_to(self.store.env(), id)? {
                entries.push(json!({
                    "source": a.source.to_string(),
                    "target": a.target.to_string(),
                    "weight": a.weight,
                    "link_type": a.link_type.as_str(),
                    "co_activation_count": a.co_activation_count,
                    "direction": "incoming",
                }));
            }
        }

        let total = assoc_store.count(self.store.env())?;

        Ok(json!({
            "status": "success",
            "id": id_str,
            "direction": direction,
            "associations": entries,
            "returned": entries.len(),
            "total_in_store": total,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── Tool: karma.report ───────────────────────────────────────────────

/// Report karma ledger status: total debt, recent entries, per-tool breakdown.
pub struct KarmaReportTool {
    ledger: Arc<KarmaLedger>,
    stats: ToolStats,
    effects: EffectRow,
}

impl KarmaReportTool {
    pub fn new(ledger: Arc<KarmaLedger>) -> Self {
        Self {
            ledger,
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![Resource::Galaxy("karma".into())]),
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for KarmaReportTool {
    fn name(&self) -> &str {
        "karma.report"
    }
    fn gana(&self) -> Gana {
        Gana::Willow
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let recent_count = args
            .get("limit")
            .and_then(serde_json::Value::as_u64)
            .unwrap_or(10) as usize;

        let recent = self.ledger.recent(recent_count)?;
        let tool_debt = self.ledger.tool_debt()?;

        let recent_entries: Vec<Value> = recent
            .iter()
            .map(|e| {
                json!({
                    "id": e.id,
                    "tool": e.tool,
                    "success": e.success,
                    "mismatch": e.mismatch,
                    "debt_delta": e.debt_delta,
                    "guna": format!("{:?}", e.guna),
                    "total_debt": e.total_debt,
                })
            })
            .collect();

        let tool_debt_entries: Vec<Value> = tool_debt
            .iter()
            .map(|(tool, debt)| {
                json!({
                    "tool": tool,
                    "debt": debt,
                })
            })
            .collect();

        Ok(json!({
            "status": "success",
            "total_debt": self.ledger.total_debt(),
            "chain_head": self.ledger.chain_head(),
            "entry_count": self.ledger.next_id(),
            "recent_entries": recent_entries,
            "per_tool_debt": tool_debt_entries,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── Tool: dharma.status ──────────────────────────────────────────────

/// Report Dharma gate state: homeostasis, health score, strict mode.
pub struct DharmaStatusTool {
    gate: Arc<DharmaGate>,
    stats: ToolStats,
    effects: EffectRow,
}

impl DharmaStatusTool {
    pub fn new(gate: Arc<DharmaGate>) -> Self {
        Self {
            gate,
            stats: ToolStats::default(),
            effects: EffectRow::pure(),
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for DharmaStatusTool {
    fn name(&self) -> &str {
        "dharma.status"
    }
    fn gana(&self) -> Gana {
        Gana::ExtendedNet
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    async fn call(&self, _ctx: &mut Context, _args: Value) -> wm_core::Result<Value> {
        let homeostasis = self.gate.homeostasis();
        let health = homeostasis.health_score();

        Ok(json!({
            "status": "success",
            "homeostasis": {
                "cpu_load": homeostasis.cpu_load,
                "memory_pressure": homeostasis.memory_pressure,
                "active": homeostasis.active,
                "health_score": health,
                "stressed": homeostasis.is_stressed(),
            },
            "sutras": {
                "ahimsa": "Non-harm — destructive actions blocked in strict mode",
                "satya": "Truth — memory fabrication always forbidden",
            },
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── Tool: harmony.vector ─────────────────────────────────────────────

/// Report current Harmony Vector — real-time hardware state (Lakshmi).
pub struct HarmonyVectorTool {
    monitor: Arc<SubstrateMonitor>,
    stats: ToolStats,
    effects: EffectRow,
}

impl HarmonyVectorTool {
    pub fn new(monitor: Arc<SubstrateMonitor>) -> Self {
        Self {
            monitor,
            stats: ToolStats::default(),
            effects: EffectRow::pure(),
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for HarmonyVectorTool {
    fn name(&self) -> &str {
        "harmony.vector"
    }
    fn gana(&self) -> Gana {
        Gana::Dipper
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    async fn call(&self, _ctx: &mut Context, _args: Value) -> wm_core::Result<Value> {
        let hv = self.monitor.sample();
        Ok(json!({
            "status": "success",
            "harmony_vector": hv.to_json(),
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── Tool: harmony.history ────────────────────────────────────────────

/// Report historical Harmony Vector samples.
pub struct HarmonyHistoryTool {
    monitor: Arc<SubstrateMonitor>,
    stats: ToolStats,
    effects: EffectRow,
}

impl HarmonyHistoryTool {
    pub fn new(monitor: Arc<SubstrateMonitor>) -> Self {
        Self {
            monitor,
            stats: ToolStats::default(),
            effects: EffectRow::pure(),
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for HarmonyHistoryTool {
    fn name(&self) -> &str {
        "harmony.history"
    }
    fn gana(&self) -> Gana {
        Gana::Dipper
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let limit = args.get("limit").and_then(Value::as_u64).unwrap_or(20) as usize;
        let samples: Vec<Value> = self
            .monitor
            .history(limit)
            .iter()
            .map(wm_substrate::HarmonyVector::to_json)
            .collect();
        Ok(json!({
            "status": "success",
            "count": samples.len(),
            "samples": samples,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── Tool: gnosis.status ──────────────────────────────────────────────

/// Full governance transparency — homeostasis, resource rules, brain-wave.
///
/// The Gnosis Portal exposes the complete governance state for human
/// inspection. This is the transparency layer — every autonomous
/// action's governance context is visible here.
pub struct GnosisStatusTool {
    dharma_gate: Arc<DharmaGate>,
    resource_rules: Arc<ResourceRules>,
    substrate: Arc<SubstrateMonitor>,
    stats: ToolStats,
    effects: EffectRow,
}

impl GnosisStatusTool {
    pub fn new(
        dharma_gate: Arc<DharmaGate>,
        resource_rules: Arc<ResourceRules>,
        substrate: Arc<SubstrateMonitor>,
    ) -> Self {
        Self {
            dharma_gate,
            resource_rules,
            substrate,
            stats: ToolStats::default(),
            effects: EffectRow::pure(),
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for GnosisStatusTool {
    fn name(&self) -> &str {
        "gnosis.status"
    }
    fn gana(&self) -> Gana {
        Gana::ThreeStars
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    async fn call(&self, ctx: &mut Context, _args: Value) -> wm_core::Result<Value> {
        let homeostasis = self.dharma_gate.homeostasis();
        let health = homeostasis.health_score();
        let budget_usage = self.resource_rules.budget_usage();
        let human_approved = self.resource_rules.human_approved();
        let last_hv = self.substrate.last_sample();

        Ok(json!({
            "status": "success",
            "brain_wave": format!("{:?}", ctx.brain_wave),
            "homeostasis": {
                "cpu_load": homeostasis.cpu_load,
                "memory_pressure": homeostasis.memory_pressure,
                "active": homeostasis.active,
                "health_score": health,
                "stressed": homeostasis.is_stressed(),
            },
            "resource_rules": {
                "writes_last_minute": budget_usage.writes_last_minute,
                "spawns_last_minute": budget_usage.spawns_last_minute,
                "network_last_minute": budget_usage.network_last_minute,
                "novelty_entries": budget_usage.novelty_entries,
                "human_approved": human_approved,
                "require_human_review": true,
            },
            "substrate": last_hv.as_ref().map(wm_substrate::HarmonyVector::to_json),
            "governance_layers": {
                "lakshmi": "Harmony Vector — hardware awareness (active)",
                "tiferet": "Resource Gating — brain-wave transitions gated by health (active)",
                "yama": "Dharma Resource Rules — budgets, novelty, purpose, human review (active)",
                "gnosis": "Transparency Portals — this tool (active)",
            },
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── Tool: gnosis.history ─────────────────────────────────────────────

/// Historical governance data — harmony vector history and budget trends.
pub struct GnosisHistoryTool {
    substrate: Arc<SubstrateMonitor>,
    stats: ToolStats,
    effects: EffectRow,
}

impl GnosisHistoryTool {
    pub fn new(substrate: Arc<SubstrateMonitor>) -> Self {
        Self {
            substrate,
            stats: ToolStats::default(),
            effects: EffectRow::pure(),
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for GnosisHistoryTool {
    fn name(&self) -> &str {
        "gnosis.history"
    }
    fn gana(&self) -> Gana {
        Gana::ThreeStars
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let limit = args.get("limit").and_then(Value::as_u64).unwrap_or(20) as usize;
        let history = self.substrate.history(limit);
        let samples: Vec<Value> = history
            .iter()
            .map(wm_substrate::HarmonyVector::to_json)
            .collect();

        // Compute summary stats
        let avg_cpu = if samples.is_empty() {
            0.0
        } else {
            samples
                .iter()
                .filter_map(|s| s["cpu_load"].as_f64())
                .sum::<f64>()
                / samples.len() as f64
        };
        let avg_mem = if samples.is_empty() {
            0.0
        } else {
            samples
                .iter()
                .filter_map(|s| s["memory_pressure"].as_f64())
                .sum::<f64>()
                / samples.len() as f64
        };
        let avg_health = if samples.is_empty() {
            0.0
        } else {
            samples
                .iter()
                .filter_map(|s| s["health_score"].as_f64())
                .sum::<f64>()
                / samples.len() as f64
        };

        Ok(json!({
            "status": "success",
            "count": samples.len(),
            "summary": {
                "avg_cpu_load": avg_cpu,
                "avg_memory_pressure": avg_mem,
                "avg_health_score": avg_health,
            },
            "samples": samples,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── Tool: gnosis.explain ─────────────────────────────────────────────

/// Explain governance decisions — why an action was allowed or blocked.
///
/// Given a tool name and its effects, returns the governance verdict
/// from each layer (Dharma gate, resource rules) so humans can
/// understand exactly why the system made its decision.
pub struct GnosisExplainTool {
    dharma_gate: Arc<DharmaGate>,
    resource_rules: Arc<ResourceRules>,
    stats: ToolStats,
    effects: EffectRow,
}

impl GnosisExplainTool {
    pub fn new(dharma_gate: Arc<DharmaGate>, resource_rules: Arc<ResourceRules>) -> Self {
        Self {
            dharma_gate,
            resource_rules,
            stats: ToolStats::default(),
            effects: EffectRow::pure(),
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for GnosisExplainTool {
    fn name(&self) -> &str {
        "gnosis.explain"
    }
    fn gana(&self) -> Gana {
        Gana::ThreeStars
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    async fn call(&self, ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let tool_name = args
            .get("tool_name")
            .and_then(Value::as_str)
            .unwrap_or("unknown");
        let is_write = args
            .get("is_write")
            .and_then(Value::as_bool)
            .unwrap_or(false);
        let is_spawn = args
            .get("is_spawn")
            .and_then(Value::as_bool)
            .unwrap_or(false);
        let is_network = args
            .get("is_network")
            .and_then(Value::as_bool)
            .unwrap_or(false);
        let has_purpose = args
            .get("has_purpose")
            .and_then(Value::as_bool)
            .unwrap_or(true);
        let args_hash = args.get("args_hash").and_then(Value::as_u64).unwrap_or(0);

        let homeostasis = self.dharma_gate.homeostasis();

        // Get Dharma gate verdict
        let dummy_effects = if is_write {
            EffectRow {
                writes: vec![Resource::Filesystem],
                ..Default::default()
            }
        } else {
            EffectRow::pure()
        };
        let dharma_verdict = self.dharma_gate.evaluate(&dummy_effects, ctx);

        // Get resource rules verdict
        let resource_verdict = self.resource_rules.evaluate(
            tool_name,
            args_hash,
            is_write,
            is_spawn,
            is_network,
            has_purpose,
            &homeostasis,
            ctx.brain_wave,
        );

        Ok(json!({
            "status": "success",
            "tool_name": tool_name,
            "brain_wave": format!("{:?}", ctx.brain_wave),
            "homeostasis": {
                "cpu_load": homeostasis.cpu_load,
                "memory_pressure": homeostasis.memory_pressure,
                "health_score": homeostasis.health_score(),
                "stressed": homeostasis.is_stressed(),
            },
            "dharma_verdict": {
                "verdict": format!("{:?}", dharma_verdict),
                "blocks": dharma_verdict.blocks(),
                "reason": dharma_verdict.reason(),
            },
            "resource_verdict": {
                "verdict": format!("{:?}", resource_verdict),
                "blocks": resource_verdict.blocks(),
                "reason": resource_verdict.reason(),
            },
            "would_block": dharma_verdict.blocks() || resource_verdict.blocks(),
            "explanation": format!(
                "Tool '{}' under {:?} brain-wave with health {:.2}: Dharma says '{}', Resources say '{}'. {}",
                tool_name,
                ctx.brain_wave,
                homeostasis.health_score(),
                dharma_verdict.reason(),
                resource_verdict.reason(),
                if dharma_verdict.blocks() || resource_verdict.blocks() {
                    "Action would be BLOCKED."
                } else {
                    "Action would be ALLOWED."
                }
            ),
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── Fractal Meta-Tool: wm ────────────────────────────────────────────

/// The fractal meta-tool — routes natural language or explicit route to tools.
pub struct WmMetaTool {
    registry: Arc<ToolRegistry>,
    stats: ToolStats,
    effects: EffectRow,
    /// Optional embedding-based NLU router. When present, used as primary router
    /// with TF-IDF as fallback (shadow mode). When `None`, TF-IDF is used directly.
    embedding_router: Option<Arc<embedding_router::EmbeddingRouter>>,
    /// Shadow mode disagreement stats (shared for observability).
    shadow_stats: Arc<std::sync::RwLock<embedding_router::ShadowModeStats>>,
    /// Optional dispatch pipeline. When present, inner tool calls are dispatched
    /// through the full governance chain (effect check, destructive confirmation,
    /// dharma gate, rate limit, circuit breaker, karma record, stats). When
    /// `None` (e.g. in unit tests), inner calls bypass the pipeline.
    pipeline: Option<Arc<DispatchPipeline>>,
}

impl WmMetaTool {
    #[must_use]
    pub fn new(registry: Arc<ToolRegistry>) -> Self {
        Self {
            registry,
            stats: ToolStats::default(),
            effects: EffectRow::pure(),
            embedding_router: None,
            shadow_stats: Arc::new(std::sync::RwLock::new(
                embedding_router::ShadowModeStats::default(),
            )),
            pipeline: None,
        }
    }

    /// Create a new meta-tool with an embedding router.
    ///
    /// If the embedder is a stub, the embedding router will be `None` and the
    /// TF-IDF router is used as fallback.
    #[must_use]
    pub fn with_embedder(
        registry: Arc<ToolRegistry>,
        embedder: Box<dyn wm_memory::Embedder>,
    ) -> Self {
        let embedding_router = Self::build_embedding_router(&registry, embedder).map(Arc::new);
        Self {
            registry,
            stats: ToolStats::default(),
            effects: EffectRow::pure(),
            embedding_router,
            shadow_stats: Arc::new(std::sync::RwLock::new(
                embedding_router::ShadowModeStats::default(),
            )),
            pipeline: None,
        }
    }

    /// Create a new meta-tool with an embedding router and shared shadow stats.
    ///
    /// Allows the caller to hold a reference to the shadow stats for
    /// observability and persistence.
    #[must_use]
    pub fn with_embedder_and_shadow_stats(
        registry: Arc<ToolRegistry>,
        embedder: Box<dyn wm_memory::Embedder>,
        shadow_stats: Arc<std::sync::RwLock<embedding_router::ShadowModeStats>>,
    ) -> Self {
        let embedding_router = Self::build_embedding_router(&registry, embedder).map(Arc::new);
        Self {
            registry,
            stats: ToolStats::default(),
            effects: EffectRow::pure(),
            embedding_router,
            shadow_stats,
            pipeline: None,
        }
    }

    /// Create a new meta-tool with an embedding router, shared shadow stats,
    /// and a dispatch pipeline for governance-gated inner dispatch.
    #[must_use]
    pub fn with_router_shadow_stats_and_pipeline(
        registry: Arc<ToolRegistry>,
        embedder: Box<dyn wm_memory::Embedder>,
        shadow_stats: Arc<std::sync::RwLock<embedding_router::ShadowModeStats>>,
        pipeline: Option<Arc<DispatchPipeline>>,
    ) -> Self {
        let embedding_router = Self::build_embedding_router(&registry, embedder).map(Arc::new);
        Self {
            registry,
            stats: ToolStats::default(),
            effects: EffectRow::pure(),
            embedding_router,
            shadow_stats,
            pipeline,
        }
    }

    /// Build an embedding router from the live registry's tool descriptions.
    ///
    /// Uses prose descriptions from the registered tools (name + description)
    /// augmented with intent anchors (natural query phrasings per tool), which
    /// embed far better than the static keyword-mashup profiles. Only falls
    /// back to the static profiles when the registry has no tools (e.g. in
    /// unit tests that call `with_embedder` directly).
    fn build_embedding_router(
        registry: &ToolRegistry,
        embedder: Box<dyn wm_memory::Embedder>,
    ) -> Option<embedding_router::EmbeddingRouter> {
        let tools = registry.all_ref();
        if tools.is_empty() {
            return embedding_router::EmbeddingRouter::new(embedder);
        }
        let descriptions = embedding_router::anchored_descriptions(tools);
        embedding_router::EmbeddingRouter::with_descriptions(embedder, descriptions)
    }

    /// Classify natural language input into (tool_name, confidence).
    ///
    /// When an embedding router is available, uses it as primary. Falls back to
    /// the TF-IDF router (`nlu::classify`) when no embedding router is configured
    /// or as a shadow-mode comparison.
    fn classify(text: &str) -> (&'static str, f64) {
        nlu::classify(text)
    }

    /// Classification core shared by the async wrapper. Runs the embedding
    /// router (and shadow TF-IDF comparison) synchronously — callers place it
    /// on the blocking pool because the HTTP embedder does synchronous
    /// network I/O (ureq), which must not run on the tokio worker thread.
    ///
    /// Returns the query embedding alongside the routing decision when the
    /// embedding router computed one, so the caller can reuse it for OATS
    /// outcome recording (one embedder round-trip instead of two).
    fn classify_with_router_inner(
        router: &embedding_router::EmbeddingRouter,
        shadow_stats: &std::sync::RwLock<embedding_router::ShadowModeStats>,
        text: &str,
    ) -> (String, f64, Option<Vec<f32>>) {
        let (emb_tool, emb_conf, margin, query_emb) =
            match router.route_with_margin_and_embedding(text) {
                Some(t) => t,
                None => ("gnosis".into(), 0.0, 0.0, Vec::new()),
            };

        // Shadow mode: run TF-IDF in parallel and track disagreements
        let (tfidf_tool, tfidf_conf) = nlu::classify(text);
        if emb_tool != tfidf_tool {
            tracing::debug!(
                query = text.chars().take(100).collect::<String>(),
                embedding_tool = %emb_tool,
                embedding_conf = emb_conf,
                margin = margin,
                tfidf_tool = %tfidf_tool,
                tfidf_conf = tfidf_conf,
                "shadow mode disagreement: embedding vs TF-IDF"
            );
        }

        // Record in shadow stats tracker
        if let Ok(mut stats) = shadow_stats.write() {
            stats.record(text, &emb_tool, emb_conf, tfidf_tool, tfidf_conf);
        }

        // Margin fallback: defer to TF-IDF when the embedding router
        // cannot separate the top candidates. TF-IDF's keyword-driven
        // picks stay reliable even at low confidence (2026-08-11 data:
        // a confidence floor on this fallback caused net regressions).
        let selected = if margin < embedding_router::MIN_MARGIN {
            (tfidf_tool.to_string(), tfidf_conf)
        } else {
            (emb_tool, emb_conf)
        };
        let query_emb = (!query_emb.is_empty()).then_some(query_emb);
        (selected.0, selected.1, query_emb)
    }

    /// Classify a thought off the async worker thread.
    ///
    /// The embedding router performs synchronous HTTP against the embedder
    /// endpoint (`ureq`); running it inline on the tokio worker would block
    /// every other dispatch on that worker for the duration of the embedder
    /// round-trip. Falls back to TF-IDF on the current thread when no
    /// embedding router is configured or the blocking task fails to join.
    async fn classify_async(&self, text: &str) -> (String, f64, Option<Vec<f32>>) {
        let Some(router) = self.embedding_router.clone() else {
            let (tool, conf) = Self::classify(text);
            return (tool.to_string(), conf, None);
        };
        let shadow_stats = Arc::clone(&self.shadow_stats);
        let text_owned = text.to_string();
        let fallback_text = text_owned.clone();
        match tokio::task::spawn_blocking(move || {
            Self::classify_with_router_inner(&router, &shadow_stats, &text_owned)
        })
        .await
        {
            Ok(result) => result,
            Err(join_err) => {
                tracing::warn!(
                    error = %join_err,
                    "NLU blocking classifier task failed — falling back to TF-IDF"
                );
                let (tool, conf) = Self::classify(&fallback_text);
                (tool.to_string(), conf, None)
            }
        }
    }

    /// Get a reference to the shadow mode stats for observability.
    #[must_use]
    pub const fn shadow_stats(&self) -> &Arc<std::sync::RwLock<embedding_router::ShadowModeStats>> {
        &self.shadow_stats
    }

    /// Get a reference to the embedding router, if present.
    #[must_use]
    pub const fn embedding_router(&self) -> Option<&Arc<embedding_router::EmbeddingRouter>> {
        self.embedding_router.as_ref()
    }

    /// Returns the required parameter for a tool, if any.
    /// Tools not listed here either have no required args or accept passthrough.
    fn required_arg(tool_name: &str) -> Option<&'static str> {
        match tool_name {
            "memory.create" => Some("content"),
            "memory.read" => Some("id"),
            "memory.delete" => Some("id"),
            "memory.search" => Some("query"),
            "memory.query" => Some("query"),
            "memory.associate" => Some("source"),
            "memory.associations" => Some("id"),
            "memory.update" => Some("id"),
            "memory.tag" => Some("id"),
            "memory.batch_read" => Some("ids"),
            "memory.nearby" => Some("query"),
            "session.end" => Some("session_id"),
            "agent.register" => Some("name"),
            "agent.trust" => Some("agent_id"),
            "agent.descriptions" => Some("agent_id"),
            "agent.capabilities" => Some("agent_id"),
            "agent.heartbeat.history" => Some("agent_id"),
            "agent.deregister" => Some("agent_id"),
            "galaxy.purge" => Some("galaxy"),
            "memory.deduplicate" => Some("galaxy"),
            "task.distribute" => Some("task"),
            _ => None,
        }
    }

    /// Build a helpful hint message for a missing required argument.
    fn missing_arg_hint(tool_name: &str, missing: &str) -> String {
        match (tool_name, missing) {
            ("memory.create", "content") => "Provide the content to store, e.g. wm(thought='remember that rust is fast')".into(),
            ("memory.read", "id") => "Provide a memory UUID, e.g. wm(thought='recall <uuid>') or wm(route='memory.read', args={\"id\": \"<uuid>\"}). To list memories instead, use wm(route='memory.list', args={\"galaxy\": \"codex\", \"limit\": 10})".into(),
            ("memory.delete", "id") => "Provide a memory UUID, e.g. wm(thought='delete memory <uuid>')".into(),
            ("memory.search", "query") => "Provide a search query, e.g. wm(thought='search for rust')".into(),
            ("memory.query", "query") => "Provide a query string, e.g. wm(route='memory.query', args={\"query\": \"tag:rust\"})".into(),
            ("memory.vector.search", "memory_id") => "Provide a memory UUID for similarity search, e.g. wm(thought='find similar to <uuid>')".into(),
            ("memory.update", "id") => "Provide a memory UUID to update, e.g. wm(route='memory.update', args={\"id\": \"<uuid>\", \"tags\": [\"new\"]})".into(),
            ("memory.tag", "id") => "Provide a memory UUID to tag, e.g. wm(route='memory.tag', args={\"id\": \"<uuid>\", \"tags\": [\"rust\"]})".into(),
            _ => format!("Missing required argument: '{missing}' for tool '{tool_name}'"),
        }
    }

    /// Extract payload from thought text by stripping routing keywords.
    fn extract_payload(thought: &str, tool_name: &str) -> Option<(String, String)> {
        let lower = thought.to_lowercase();
        match tool_name {
            "memory.create" => {
                for prefix in &[
                    "remember that ",
                    "remember ",
                    "store ",
                    "save ",
                    "note that ",
                    "note ",
                ] {
                    if lower.starts_with(prefix) {
                        let content = thought[prefix.len()..].to_string();
                        if !content.is_empty() {
                            return Some(("content".into(), content));
                        }
                    }
                }
                if !thought.is_empty() {
                    return Some(("content".into(), thought.to_string()));
                }
            }
            "memory.read" => {
                for prefix in &["recall ", "read memory ", "fetch memory ", "get memory "] {
                    if lower.starts_with(prefix) {
                        let id = thought[prefix.len()..].trim().to_string();
                        if !id.is_empty() {
                            return Some(("id".into(), id));
                        }
                    }
                }
            }
            "memory.list" => {
                for prefix in &[
                    "list memories",
                    "show memories",
                    "search memories",
                    "search for",
                ] {
                    if lower.contains(prefix) {
                        let after = &thought[lower.find(prefix).unwrap() + prefix.len()..];
                        let query = after.trim().trim_start_matches("in ").trim();
                        if !query.is_empty() {
                            return Some(("galaxy".into(), query.to_string()));
                        }
                    }
                }
            }
            "memory.delete" => {
                for prefix in &["delete memory ", "remove memory ", "forget memory "] {
                    if lower.starts_with(prefix) {
                        let id = thought[prefix.len()..].trim().to_string();
                        if !id.is_empty() {
                            return Some(("id".into(), id));
                        }
                    }
                }
            }
            "memory.search" => {
                for prefix in &["search for ", "search "] {
                    if lower.starts_with(prefix) {
                        let query = thought[prefix.len()..].trim().to_string();
                        if !query.is_empty() {
                            return Some(("query".into(), query));
                        }
                    }
                }
            }
            "memory.chat" => {
                for prefix in &[
                    "chat about ",
                    "chat ",
                    "ask about ",
                    "ask ",
                    "discuss ",
                    "explore ",
                    "converse about ",
                ] {
                    if lower.starts_with(prefix) {
                        let query = thought[prefix.len()..].trim().to_string();
                        if !query.is_empty() {
                            return Some(("query".into(), query));
                        }
                    }
                }
                if !thought.is_empty() {
                    return Some(("query".into(), thought.to_string()));
                }
            }
            "memory.vector.search" => {
                for prefix in &[
                    "find similar to ",
                    "similar to memory ",
                    "vector search ",
                    "semantic search ",
                    "embedding search ",
                ] {
                    if lower.starts_with(prefix) {
                        let id = thought[prefix.len()..].trim().to_string();
                        if !id.is_empty() {
                            return Some(("memory_id".into(), id));
                        }
                    }
                }
            }
            "memory.count" => {
                for prefix in &[
                    "count memories in ",
                    "how many memories in ",
                    "memory count ",
                ] {
                    if lower.starts_with(prefix) {
                        let galaxy = thought[prefix.len()..].trim().to_string();
                        if !galaxy.is_empty() {
                            return Some(("galaxy".into(), galaxy));
                        }
                    }
                }
            }
            "session.start" => {
                for prefix in &["start session ", "new session ", "begin session "] {
                    if lower.starts_with(prefix) {
                        let title = thought[prefix.len()..].trim().to_string();
                        if !title.is_empty() {
                            // `title` is the argument the session tool reads;
                            // the old payload key was "name", which silently
                            // created "Untitled Session" entries.
                            return Some(("title".into(), title));
                        }
                    }
                }
            }
            "session.end" => {
                for prefix in &["end session ", "close session ", "stop session "] {
                    if lower.starts_with(prefix) {
                        let id = thought[prefix.len()..].trim().to_string();
                        if !id.is_empty() {
                            return Some(("session_id".into(), id));
                        }
                    }
                }
            }
            "agent.register" => {
                for prefix in &[
                    "register agent ",
                    "new agent ",
                    "create agent ",
                    "add agent ",
                ] {
                    if lower.starts_with(prefix) {
                        let name = thought[prefix.len()..].trim().to_string();
                        if !name.is_empty() {
                            return Some(("name".into(), name));
                        }
                    }
                }
            }
            "agent.trust"
            | "agent.descriptions"
            | "agent.capabilities"
            | "agent.heartbeat.history"
            | "agent.deregister" => {
                for prefix in &[
                    "trust agent ",
                    "describe agent ",
                    "capabilities agent ",
                    "heartbeat history agent ",
                    "deregister agent ",
                    "unregister agent ",
                    "remove agent ",
                ] {
                    if lower.starts_with(prefix) {
                        let id = thought[prefix.len()..].trim().to_string();
                        if !id.is_empty() {
                            return Some(("agent_id".into(), id));
                        }
                    }
                }
            }
            "galaxy.purge" => {
                for prefix in &["purge galaxy ", "wipe galaxy ", "clear galaxy "] {
                    if lower.starts_with(prefix) {
                        let galaxy = thought[prefix.len()..].trim().to_string();
                        if !galaxy.is_empty() {
                            return Some(("galaxy".into(), galaxy));
                        }
                    }
                }
            }
            "task.distribute" => {
                for prefix in &["distribute task ", "assign task ", "dispatch task "] {
                    if lower.starts_with(prefix) {
                        let task = thought[prefix.len()..].trim().to_string();
                        if !task.is_empty() {
                            return Some(("task".into(), task));
                        }
                    }
                }
            }
            "memory.sort" => {
                for prefix in &["sort memories ", "sort memory ", "order memories "] {
                    if lower.starts_with(prefix) {
                        let galaxy = thought[prefix.len()..].trim().to_string();
                        if !galaxy.is_empty() {
                            return Some(("galaxy".into(), galaxy));
                        }
                    }
                }
            }
            "memory.filter" => {
                for prefix in &["filter memories ", "filter memory "] {
                    if lower.starts_with(prefix) {
                        let galaxy = thought[prefix.len()..].trim().to_string();
                        if !galaxy.is_empty() {
                            return Some(("galaxy".into(), galaxy));
                        }
                    }
                }
            }
            "memory.deduplicate" => {
                for prefix in &[
                    "deduplicate memories ",
                    "deduplicate memory ",
                    "dedup memories ",
                ] {
                    if lower.starts_with(prefix) {
                        let galaxy = thought[prefix.len()..].trim().to_string();
                        if !galaxy.is_empty() {
                            return Some(("galaxy".into(), galaxy));
                        }
                    }
                }
            }
            "memory.export" => {
                for prefix in &["export memories ", "export memory "] {
                    if lower.starts_with(prefix) {
                        let galaxy = thought[prefix.len()..].trim().to_string();
                        if !galaxy.is_empty() {
                            return Some(("galaxy".into(), galaxy));
                        }
                    }
                }
            }
            "speculative.decode" => {
                for prefix in &[
                    "speculative decode ",
                    "speculative ",
                    "decode ",
                    "draft and verify ",
                    "accelerate inference ",
                ] {
                    if lower.starts_with(prefix) {
                        let prompt = thought[prefix.len()..].trim().to_string();
                        if !prompt.is_empty() {
                            return Some(("prompt".into(), prompt));
                        }
                    }
                }
            }
            "meta.enhance" => {
                for prefix in &[
                    "enhance ",
                    "enhance prompt ",
                    "grounded inference ",
                    "self-correct ",
                    "meta enhance ",
                    "cognitive enhance ",
                    "augment ",
                ] {
                    if lower.starts_with(prefix) {
                        let prompt = thought[prefix.len()..].trim().to_string();
                        if !prompt.is_empty() {
                            return Some(("prompt".into(), prompt));
                        }
                    }
                }
            }
            "dense.encode" => {
                for prefix in &["dense encode ", "compress ", "encode ", "compact "] {
                    if lower.starts_with(prefix) {
                        let text = thought[prefix.len()..].trim().to_string();
                        if !text.is_empty() {
                            return Some(("text".into(), text));
                        }
                    }
                }
            }
            "dream.trigger" => {
                for prefix in &[
                    "dream trigger ",
                    "trigger dream ",
                    "start dream ",
                    "force dream ",
                    "initiate dream ",
                ] {
                    if lower.starts_with(prefix) {
                        let rest = thought[prefix.len()..].trim();
                        if !rest.is_empty() {
                            return Some(("force".into(), rest.to_string()));
                        }
                    }
                }
            }
            _ => {}
        }
        None
    }
}

#[async_trait]
#[async_trait]
impl Tool for WmMetaTool {
    fn name(&self) -> &str {
        "wm"
    }
    fn gana(&self) -> Gana {
        Gana::Horn
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    async fn call(&self, ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let thought = args.get("thought").and_then(|v| v.as_str()).unwrap_or("");
        let route = args.get("route").and_then(|v| v.as_str());
        let passthrough_args = args.get("args").cloned().unwrap_or(Value::Null);

        if thought.is_empty() && route.is_none() {
            return Ok(json!({
                "status": "error",
                "message": "Either 'thought' (natural language) or 'route' (explicit) is required",
                "hint": "wm(thought='remember that X is Y') or wm(route='memory.create', args={\"content\": \"...\"})"
            }));
        }

        // Explicit routing
        let (tool_name, confidence, query_emb) = if let Some(r) = route {
            (r.to_string(), 1.0, None)
        } else {
            self.classify_async(thought).await
        };

        // Build args for the target tool
        let mut tool_args = if passthrough_args.is_object() {
            passthrough_args
        } else {
            Value::Null
        };

        // Auto-extract payload from thought when auto-routing
        if route.is_none() && !thought.is_empty() && tool_args.is_null() {
            if let Some((param, value)) = Self::extract_payload(thought, &tool_name) {
                tool_args = json!({ param: value });
            }
        }

        // Check for missing required args before dispatching
        if let Some(required) = Self::required_arg(&tool_name) {
            let has_arg = tool_args.is_object()
                && tool_args.get(required).is_some()
                && !tool_args
                    .get(required)
                    .is_some_and(serde_json::Value::is_null);
            if !has_arg {
                return Ok(json!({
                    "status": "error",
                    "message": format!("Missing required argument: '{required}' for tool '{tool_name}'"),
                    "hint": Self::missing_arg_hint(&tool_name, required),
                    "_wm_route": { "tool": tool_name, "confidence": confidence },
                }));
            }
        }

        // Dispatch to target tool
        let tool = self.registry.get(&tool_name);
        match tool {
            Some(t) => {
                // Hard gate: destructive tools are unreachable via natural-language
                // routing — they require an explicit route= plus `confirm: true`,
                // which the dispatch pipeline enforces below. This makes it
                // structurally impossible for fuzzy NLU to destroy data.
                if route.is_none() && t.effects().destructive {
                    return Ok(json!({
                        "status": "error",
                        "message": format!(
                            "tool '{tool_name}' is destructive and cannot be reached via natural language — use wm(route='{tool_name}', args={{...}}) with \"confirm\": true"
                        ),
                        "_wm_route": { "tool": tool_name, "confidence": confidence },
                    }));
                }
                // Route through the full governance pipeline when attached:
                // destructive confirmation, dharma gate, rate limit, circuit
                // breaker, karma record, and per-tool stats all apply to the
                // inner tool. Falls back to a direct call when no pipeline is
                // attached (e.g. unit tests).
                let result = match &self.pipeline {
                    Some(p) => p.dispatch(t.as_ref(), ctx, tool_args).await,
                    None => t.call(ctx, tool_args).await,
                };
                // OATS: record routing outcome for embedding router refinement.
                // Reuse the query embedding computed during routing so the
                // embedder is called once per NLU request, not twice. When no
                // embedding is available (explicit route= or router fallback),
                // the re-embed does synchronous HTTP — run it on the blocking
                // pool instead of the tokio worker.
                if let Some(ref router) = self.embedding_router {
                    let success = result.is_ok();
                    if let Some(emb) = &query_emb {
                        router.record_outcome_with_embedding(&tool_name, thought, success, emb);
                    } else {
                        let router = Arc::clone(router);
                        let tool_name_owned = tool_name.clone();
                        let thought_owned = thought.to_string();
                        tokio::task::spawn_blocking(move || {
                            router.record_outcome(&tool_name_owned, &thought_owned, success);
                        });
                    }
                }
                match result {
                    Ok(mut output) => {
                        // Augment with routing metadata
                        if let Value::Object(ref mut map) = output {
                            map.insert(
                                "_wm_route".into(),
                                json!({
                                    "input": thought.chars().take(200).collect::<String>(),
                                    "tool": tool_name,
                                    "confidence": confidence,
                                }),
                            );
                        }
                        Ok(output)
                    }
                    Err(e) => Ok(json!({
                        "status": "error",
                        "error": e.to_string(),
                        "_wm_route": { "tool": tool_name, "confidence": confidence },
                    })),
                }
            }
            None => Ok(json!({
                "status": "error",
                "message": format!("Unknown tool: '{tool_name}'"),
                "_wm_route": { "tool": tool_name, "confidence": confidence },
            })),
        }
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── Helpers ──────────────────────────────────────────────────────────

/// Parse a galaxy name string into a Galaxy enum.
fn parse_galaxy(s: &str) -> wm_core::Result<Galaxy> {
    expansion::common::parse_galaxy(s)
}

/// Register all base tools into a registry.
///
/// `search`, `karma`, and `dharma` are optional — pass `None` if those
/// subsystems aren't available (e.g., no Tantivy index, no karma ledger).
/// `vector_store` is the in-memory vector index for embedding similarity search.
/// `conversational` is the optional N5 conversational search engine.
#[allow(clippy::too_many_arguments)]
pub fn register_all(
    registry: &ToolRegistry,
    store: &Arc<MemoryStore>,
    search: Option<Arc<SearchEngine>>,
    karma: Option<Arc<KarmaLedger>>,
    dharma: &Option<Arc<DharmaGate>>,
    substrate: Option<Arc<SubstrateMonitor>>,
    resource_rules: &Option<Arc<ResourceRules>>,
    associations: Arc<AssociationStore>,
    spiral_tracker: Arc<std::sync::Mutex<wm_cognitive::SpiralTracker>>,
    vector_store: Arc<std::sync::Mutex<VectorStore>>,
    conversational: Option<ConversationalSearch>,
    homeostatic_loop: Option<Arc<std::sync::Mutex<HomeostaticLoop>>>,
    anomaly_detector: Option<Arc<std::sync::Mutex<AnomalyDetector>>>,
    sensorimotor_bus: Option<Arc<std::sync::Mutex<SensorimotorBus>>>,
    reflex_loop: Option<Arc<std::sync::Mutex<ReflexLoop>>>,
    gan_ying_bus: Option<&Arc<std::sync::Mutex<GanYingBus>>>,
    transaction_state: expansion::TransactionState,
    escalation_queue: Option<&Arc<std::sync::Mutex<wm_governance::EscalationQueue>>>,
    firewall: Option<&Arc<expansion::firewall::TxFirewall>>,
    code_graph: Option<&Arc<std::sync::Mutex<expansion::code::CodeGraph>>>,
) -> ToolRegistry {
    let mut reg = registry
        .register(Arc::new(MemoryCreateTool::new(
            store.clone(),
            search.clone(),
        )))
        .register(Arc::new(MemoryReadTool::new(store.clone())))
        .register(Arc::new(MemoryListTool::new(store.clone())))
        .register(Arc::new(MemoryDeleteTool::new(
            store.clone(),
            search.clone(),
        )))
        .register(Arc::new(MemoryQueryTool::new(store.clone())))
        .register(Arc::new(MemoryAssociateTool::new(store.clone())))
        .register(Arc::new(MemoryAssociationsTool::new(store.clone())))
        .register(Arc::new(MemoryVectorSearchTool::new(
            store.clone(),
            vector_store,
        )))
        .register(Arc::new(GnosisTool::new(store.clone())));

    if let Some(conv) = conversational {
        reg = reg.register(Arc::new(MemoryChatTool::new(conv)));
    }

    if let Some(s) = search {
        reg = reg.register(Arc::new(MemorySearchTool::new(s.clone(), store.clone())));
        // Pass search to expansion tools
        reg = expansion::register_expansion(
            &reg,
            store,
            Some(s),
            associations,
            spiral_tracker,
            karma.clone(),
            substrate.clone(),
            homeostatic_loop,
            anomaly_detector,
            sensorimotor_bus,
            reflex_loop,
            gan_ying_bus,
            transaction_state,
            resource_rules.as_ref(),
            escalation_queue,
            dharma.as_ref(),
            firewall,
            code_graph,
        );
    } else {
        reg = expansion::register_expansion(
            &reg,
            store,
            None,
            associations,
            spiral_tracker,
            karma.clone(),
            substrate.clone(),
            homeostatic_loop,
            anomaly_detector,
            sensorimotor_bus,
            reflex_loop,
            gan_ying_bus,
            transaction_state,
            resource_rules.as_ref(),
            escalation_queue,
            dharma.as_ref(),
            firewall,
            code_graph,
        );
    }
    if let Some(k) = karma {
        reg = reg.register(Arc::new(KarmaReportTool::new(k)));
    }
    if let Some(d) = dharma {
        reg = reg.register(Arc::new(DharmaStatusTool::new(d.clone())));
    }
    if let Some(s) = substrate {
        reg = reg
            .register(Arc::new(HarmonyVectorTool::new(s.clone())))
            .register(Arc::new(HarmonyHistoryTool::new(s.clone())));
        if let Some(d) = dharma {
            if let Some(r) = resource_rules {
                reg = reg
                    .register(Arc::new(GnosisStatusTool::new(
                        d.clone(),
                        r.clone(),
                        s.clone(),
                    )))
                    .register(Arc::new(GnosisHistoryTool::new(s)))
                    .register(Arc::new(GnosisExplainTool::new(d.clone(), r.clone())));
            }
        }
    }

    reg
}

/// Register tools.list and wm meta-tool after the base tools are registered.
///
/// This requires a two-phase approach because tools.list needs the registry.
/// Also creates GnosisTool with registry access for brain-wave-aware tool counting.
/// The `shadow_stats` Arc is shared between the `WmMetaTool` and `NluShadowReportTool`.
pub fn register_meta_tools(
    registry: &ToolRegistry,
    store: &Arc<MemoryStore>,
    shadow_stats: Arc<std::sync::RwLock<embedding_router::ShadowModeStats>>,
) -> ToolRegistry {
    register_meta_tools_with_router(registry, store, shadow_stats, None).0
}

/// Register the meta-tools and return the embedding router alongside.
///
/// The router is returned so the caller can persist/restore OATS outcome
/// stats (`save_oats` / `load_oats`) across restarts — the outcome-aware
/// refinement that makes NLU routing learn from dispatch outcomes.
///
/// When `pipeline` is `Some`, the `wm` meta-tool dispatches inner tools through
/// the full governance pipeline (destructive confirmation, dharma gate, rate
/// limit, circuit breaker, karma record, per-tool stats).
#[must_use]
pub fn register_meta_tools_with_router(
    registry: &ToolRegistry,
    store: &Arc<MemoryStore>,
    shadow_stats: Arc<std::sync::RwLock<embedding_router::ShadowModeStats>>,
    pipeline: Option<Arc<DispatchPipeline>>,
) -> (ToolRegistry, Option<Arc<embedding_router::EmbeddingRouter>>) {
    let base_snapshot: Vec<Arc<dyn Tool>> = registry.all();
    // Count includes old gnosis (which will be replaced with tool-count-aware version)
    let tool_count = base_snapshot.len();

    let non_gnosis: Vec<Arc<dyn Tool>> = base_snapshot
        .iter()
        .filter(|t| t.name() != "gnosis")
        .cloned()
        .collect();

    // Build tools.list with snapshot of non-gnosis tools
    let mut list_builder = ToolRegistryBuilder::new();
    for tool in &non_gnosis {
        list_builder.register(tool.clone());
    }
    let tools_list = Arc::new(ToolsListTool::new(Arc::new(list_builder.build())));

    // Build wm with all base tools (non-gnosis) + tools.list + new gnosis
    let gnosis = Arc::new(GnosisTool::with_tool_count(Arc::clone(store), tool_count));
    let mut wm_builder = ToolRegistryBuilder::new();
    for tool in &non_gnosis {
        wm_builder.register(tool.clone());
    }
    wm_builder.register(tools_list.clone());
    wm_builder.register(gnosis.clone());

    // Create NLU shadow report tool sharing the same shadow stats.
    // Registered inside the wm meta-tool's routing registry so
    // `wm(route="nlu.shadow_report")` is reachable — the MCP boundary only
    // exposes the `wm` meta-tool, so top-level-only registration was unreachable.
    let shadow_report = Arc::new(expansion::NluShadowReportTool::new(Arc::clone(
        &shadow_stats,
    )));
    wm_builder.register(shadow_report.clone());
    let wm = Arc::new(WmMetaTool::with_router_shadow_stats_and_pipeline(
        Arc::new(wm_builder.build()),
        wm_memory::create_embedder(),
        shadow_stats,
        pipeline,
    ));
    let router = wm.embedding_router().cloned();

    // Build the final registry: non-gnosis + tools.list + wm + gnosis + shadow report
    let mut final_builder = ToolRegistryBuilder::new();
    for tool in non_gnosis {
        final_builder.register(tool);
    }
    final_builder.register(tools_list);
    final_builder.register(wm);
    final_builder.register(gnosis);
    final_builder.register(shadow_report);
    (final_builder.build(), router)
}

#[cfg(test)]
mod tests {
    use super::*;
    use wm_core::BrainWave;

    fn test_store() -> Arc<MemoryStore> {
        let tmp = tempfile::tempdir().unwrap();
        Arc::new(MemoryStore::open_default(tmp.path()).unwrap())
    }

    fn test_registry_with(store: &Arc<MemoryStore>) -> ToolRegistry {
        let registry = ToolRegistry::new();
        let associations = Arc::new(AssociationStore::open(store.env()).unwrap());
        let spiral_tracker =
            Arc::new(std::sync::Mutex::new(wm_cognitive::SpiralTracker::default()));
        let vector_store = Arc::new(std::sync::Mutex::new(wm_memory::VectorStore::new()));
        register_all(
            &registry,
            store,
            None,
            None,
            &None,
            None,
            &None,
            associations,
            spiral_tracker,
            vector_store,
            None,
            None,
            None,
            None,
            None,
            None,
            std::sync::Arc::new(std::sync::Mutex::new(None)),
            None,
            None,
            None,
        )
    }

    #[tokio::test]
    async fn memory_create_and_read() {
        let store = test_store();
        let tool = MemoryCreateTool::new(store.clone(), None);
        let mut ctx = Context::new(BrainWave::Gamma);

        let args = json!({"content": "test memory content", "galaxy": "codex"});
        let result = tool.call(&mut ctx, args).await.unwrap();
        assert_eq!(result["status"], "success");
        let id = result["id"].as_str().unwrap();

        let read_tool = MemoryReadTool::new(store);
        let result = read_tool.call(&mut ctx, json!({"id": id})).await.unwrap();
        assert_eq!(result["status"], "success");
        assert_eq!(result["content"], "test memory content");
    }

    #[tokio::test]
    async fn memory_list_returns_entries() {
        let store = test_store();
        let create = MemoryCreateTool::new(store.clone(), None);
        let mut ctx = Context::new(BrainWave::Gamma);

        for i in 0..3 {
            create
                .call(&mut ctx, json!({"content": format!("item-{i}")}))
                .await
                .unwrap();
        }

        let list = MemoryListTool::new(store);
        let result = list.call(&mut ctx, json!({"limit": 10})).await.unwrap();
        assert_eq!(result["status"], "success");
        assert_eq!(result["total"], 3);
        assert_eq!(result["returned"], 3);
    }

    #[tokio::test]
    async fn gnosis_returns_system_info() {
        let store = test_store();
        let tool = GnosisTool::new(store);
        let mut ctx = Context::new(BrainWave::Gamma);
        let result = tool.call(&mut ctx, json!({})).await.unwrap();
        assert_eq!(result["status"], "success");
        assert!(result["version"].is_string());
    }

    #[tokio::test]
    async fn memory_delete_removes_entry() {
        let store = test_store();
        let create = MemoryCreateTool::new(store.clone(), None);
        let mut ctx = Context::new(BrainWave::Gamma);

        let result = create
            .call(&mut ctx, json!({"content": "to be deleted"}))
            .await
            .unwrap();
        let id = result["id"].as_str().unwrap();

        let delete = MemoryDeleteTool::new(store.clone(), None);
        let result = delete.call(&mut ctx, json!({"id": id})).await.unwrap();
        assert_eq!(result["status"], "success");

        let read = MemoryReadTool::new(store);
        let result = read.call(&mut ctx, json!({"id": id})).await.unwrap();
        assert_eq!(result["status"], "not_found");
    }

    #[tokio::test]
    async fn memory_query_filters_by_tags() {
        let store = test_store();
        let create = MemoryCreateTool::new(store.clone(), None);
        let mut ctx = Context::new(BrainWave::Gamma);

        create
            .call(&mut ctx, json!({"content": "tagged", "tags": ["rust"]}))
            .await
            .unwrap();
        create
            .call(&mut ctx, json!({"content": "untagged"}))
            .await
            .unwrap();

        let query = MemoryQueryTool::new(store);
        let result = query
            .call(&mut ctx, json!({"tags": ["rust"]}))
            .await
            .unwrap();
        assert_eq!(result["status"], "success");
        assert_eq!(result["total"], 1);
    }

    #[tokio::test]
    async fn memory_vector_search_by_embedding() {
        let store = test_store();
        let vector_store = Arc::new(std::sync::Mutex::new(wm_memory::VectorStore::new()));

        // Add some vectors directly
        {
            let mut vs = vector_store.lock().unwrap();
            vs.add(uuid::Uuid::new_v4(), Galaxy::Codex, vec![1.0, 0.0, 0.0]);
            vs.add(uuid::Uuid::new_v4(), Galaxy::Codex, vec![0.9, 0.1, 0.0]);
            vs.add(uuid::Uuid::new_v4(), Galaxy::Research, vec![0.0, 1.0, 0.0]);
        }

        let tool = MemoryVectorSearchTool::new(store, vector_store);
        let mut ctx = Context::new(BrainWave::Gamma);

        // Search for vectors similar to [1, 0, 0]
        let result = tool
            .call(&mut ctx, json!({"embedding": [1.0, 0.0, 0.0], "limit": 2}))
            .await
            .unwrap();
        assert_eq!(result["status"], "success");
        assert_eq!(result["total"], 2);
    }

    #[tokio::test]
    async fn memory_vector_search_missing_args() {
        let store = test_store();
        let vector_store = Arc::new(std::sync::Mutex::new(wm_memory::VectorStore::new()));

        let tool = MemoryVectorSearchTool::new(store, vector_store);
        let mut ctx = Context::new(BrainWave::Gamma);

        let result = tool.call(&mut ctx, json!({"limit": 5})).await;
        assert!(result.is_err());
    }

    #[tokio::test]
    async fn wm_routes_vector_search_to_memory_vector_search() {
        let store = test_store();
        let registry = test_registry_with(&store);
        let registry = register_meta_tools(
            &registry,
            &store,
            std::sync::Arc::new(std::sync::RwLock::new(
                embedding_router::ShadowModeStats::default(),
            )),
        );

        let wm = registry.get("wm").unwrap();
        let mut ctx = Context::new(BrainWave::Gamma);
        let result = wm
            .call(
                &mut ctx,
                json!({"route": "memory.vector.search", "args": {"embedding": [1.0, 0.0, 0.0]}}),
            )
            .await
            .unwrap();

        assert_eq!(result["status"], "success");
        assert_eq!(result["_wm_route"]["tool"], "memory.vector.search");
    }

    #[tokio::test]
    async fn wm_routes_shadow_report_inside_meta_tool() {
        // The MCP boundary only exposes the `wm` meta-tool, so observability
        // tools must be reachable through it. Regression test: `nlu.shadow_report`
        // was top-level-only and returned "Unknown tool" via wm(route=...).
        let store = test_store();
        let registry = test_registry_with(&store);
        let registry = register_meta_tools(
            &registry,
            &store,
            std::sync::Arc::new(std::sync::RwLock::new(
                embedding_router::ShadowModeStats::default(),
            )),
        );

        let wm = registry.get("wm").unwrap();
        let mut ctx = Context::new(BrainWave::Gamma);
        let result = wm
            .call(&mut ctx, json!({"route": "nlu.shadow_report"}))
            .await
            .unwrap();

        assert_eq!(result["_wm_route"]["tool"], "nlu.shadow_report");
        assert!(
            result.get("total_queries").is_some(),
            "expected shadow report payload"
        );
    }

    #[tokio::test]
    async fn memory_associate_and_find() {
        let store = test_store();
        let create = MemoryCreateTool::new(store.clone(), None);
        let mut ctx = Context::new(BrainWave::Gamma);

        let r1 = create
            .call(&mut ctx, json!({"content": "source mem"}))
            .await
            .unwrap();
        let r2 = create
            .call(&mut ctx, json!({"content": "target mem"}))
            .await
            .unwrap();
        let id1 = r1["id"].as_str().unwrap();
        let id2 = r2["id"].as_str().unwrap();

        let assoc = MemoryAssociateTool::new(store.clone());
        let result = assoc
            .call(
                &mut ctx,
                json!({"source": id1, "target": id2, "weight": 0.8}),
            )
            .await
            .unwrap();
        assert_eq!(result["status"], "success");

        let find = MemoryAssociationsTool::new(store);
        let result = find
            .call(&mut ctx, json!({"id": id1, "direction": "from"}))
            .await
            .unwrap();
        assert_eq!(result["status"], "success");
        assert_eq!(result["returned"], 1);
    }

    #[tokio::test]
    async fn karma_report_shows_entries() {
        let tmp = tempfile::tempdir().unwrap();
        let store = Arc::new(MemoryStore::open_default(tmp.path()).unwrap());
        let ledger = Arc::new(KarmaLedger::new(store).unwrap());

        // Record a few entries
        ledger.record("test_tool", false, 0, true).unwrap();
        ledger.record("wasteful_tool", true, 0, true).unwrap();

        let tool = KarmaReportTool::new(ledger);
        let mut ctx = Context::new(BrainWave::Gamma);
        let result = tool.call(&mut ctx, json!({"limit": 5})).await.unwrap();
        assert_eq!(result["status"], "success");
        assert_eq!(result["entry_count"], 2);
        assert_eq!(result["recent_entries"].as_array().unwrap().len(), 2);
    }

    #[tokio::test]
    async fn dharma_status_returns_homeostasis() {
        let gate = Arc::new(DharmaGate::default());
        let tool = DharmaStatusTool::new(gate);
        let mut ctx = Context::new(BrainWave::Gamma);
        let result = tool.call(&mut ctx, json!({})).await.unwrap();
        assert_eq!(result["status"], "success");
        assert!(result["homeostasis"]["health_score"].is_f64());
        assert!(result["sutras"]["ahimsa"].is_string());
    }

    #[tokio::test]
    async fn wm_routes_remember_to_memory_create() {
        let store = test_store();
        let registry = test_registry_with(&store);
        let registry = register_meta_tools(
            &registry,
            &store,
            std::sync::Arc::new(std::sync::RwLock::new(
                embedding_router::ShadowModeStats::default(),
            )),
        );

        let wm = registry.get("wm").unwrap();
        let mut ctx = Context::new(BrainWave::Gamma);
        let result = wm
            .call(
                &mut ctx,
                json!({"thought": "remember that the API uses X-User-Id headers"}),
            )
            .await
            .unwrap();

        assert_eq!(result["status"], "success");
        assert_eq!(result["_wm_route"]["tool"], "memory.create");
        assert!(result["id"].is_string());
    }

    #[tokio::test]
    async fn wm_explicit_route() {
        let store = test_store();
        let registry = test_registry_with(&store);
        let registry = register_meta_tools(
            &registry,
            &store,
            std::sync::Arc::new(std::sync::RwLock::new(
                embedding_router::ShadowModeStats::default(),
            )),
        );

        let wm = registry.get("wm").unwrap();
        let mut ctx = Context::new(BrainWave::Gamma);
        let result = wm
            .call(
                &mut ctx,
                json!({
                    "route": "gnosis"
                }),
            )
            .await
            .unwrap();

        assert_eq!(result["status"], "success");
        assert_eq!(result["_wm_route"]["tool"], "gnosis");
    }

    #[tokio::test]
    async fn wm_no_input_returns_error() {
        let store = test_store();
        let registry = test_registry_with(&store);
        let registry = register_meta_tools(
            &registry,
            &store,
            std::sync::Arc::new(std::sync::RwLock::new(
                embedding_router::ShadowModeStats::default(),
            )),
        );

        let wm = registry.get("wm").unwrap();
        let mut ctx = Context::new(BrainWave::Gamma);
        let result = wm.call(&mut ctx, json!({})).await.unwrap();

        assert_eq!(result["status"], "error");
    }

    #[tokio::test]
    async fn wm_unknown_tool_returns_error() {
        let store = test_store();
        let registry = test_registry_with(&store);
        let registry = register_meta_tools(
            &registry,
            &store,
            std::sync::Arc::new(std::sync::RwLock::new(
                embedding_router::ShadowModeStats::default(),
            )),
        );

        let wm = registry.get("wm").unwrap();
        let mut ctx = Context::new(BrainWave::Gamma);
        let result = wm
            .call(&mut ctx, json!({"route": "nonexistent.tool"}))
            .await
            .unwrap();

        assert_eq!(result["status"], "error");
        assert!(result["message"].as_str().unwrap().contains("Unknown tool"));
    }

    #[tokio::test]
    async fn wm_missing_arg_returns_hint() {
        let store = test_store();
        let registry = test_registry_with(&store);
        let registry = register_meta_tools(
            &registry,
            &store,
            std::sync::Arc::new(std::sync::RwLock::new(
                embedding_router::ShadowModeStats::default(),
            )),
        );

        let wm = registry.get("wm").unwrap();
        let mut ctx = Context::new(BrainWave::Gamma);

        // Route to memory.read without providing id
        let result = wm
            .call(&mut ctx, json!({"route": "memory.read"}))
            .await
            .unwrap();

        assert_eq!(result["status"], "error");
        assert!(
            result["message"]
                .as_str()
                .unwrap()
                .contains("Missing required argument")
        );
        assert!(result["hint"].as_str().unwrap().contains("uuid"));
    }

    #[tokio::test]
    async fn wm_auto_route_missing_arg_returns_hint() {
        let store = test_store();
        let registry = test_registry_with(&store);
        let registry = register_meta_tools(
            &registry,
            &store,
            std::sync::Arc::new(std::sync::RwLock::new(
                embedding_router::ShadowModeStats::default(),
            )),
        );

        let wm = registry.get("wm").unwrap();
        let mut ctx = Context::new(BrainWave::Gamma);

        // "recall" routes to memory.read but no UUID provided
        let result = wm
            .call(&mut ctx, json!({"thought": "recall"}))
            .await
            .unwrap();

        assert_eq!(result["status"], "error");
        assert!(result["hint"].as_str().unwrap().contains("uuid"));
    }

    #[tokio::test]
    async fn wm_routes_karma_to_karma_report() {
        let tmp = tempfile::tempdir().unwrap();
        let store = Arc::new(MemoryStore::open_default(tmp.path()).unwrap());
        let ledger = Arc::new(KarmaLedger::new(store.clone()).unwrap());
        let gate = Arc::new(DharmaGate::default());

        let registry = ToolRegistry::new();
        let associations = Arc::new(AssociationStore::open(store.env()).unwrap());
        let spiral_tracker =
            Arc::new(std::sync::Mutex::new(wm_cognitive::SpiralTracker::default()));
        let vector_store = Arc::new(std::sync::Mutex::new(wm_memory::VectorStore::new()));
        let registry = register_all(
            &registry,
            &store,
            None,
            Some(ledger),
            &Some(gate),
            None,
            &None,
            associations,
            spiral_tracker,
            vector_store,
            None,
            None,
            None,
            None,
            None,
            None,
            std::sync::Arc::new(std::sync::Mutex::new(None)),
            None,
            None,
            None,
        );
        let registry = register_meta_tools(
            &registry,
            &store,
            std::sync::Arc::new(std::sync::RwLock::new(
                embedding_router::ShadowModeStats::default(),
            )),
        );

        let wm = registry.get("wm").unwrap();
        let mut ctx = Context::new(BrainWave::Gamma);
        let result = wm
            .call(&mut ctx, json!({"thought": "show me the karma report"}))
            .await
            .unwrap();

        assert_eq!(result["status"], "success");
        assert_eq!(result["_wm_route"]["tool"], "karma.report");
    }

    /// Build a registry with the wm meta-tool wired to a real DispatchPipeline,
    /// so inner tool calls are governance-gated (destructive confirm, etc.).
    fn test_registry_with_pipeline(
        store: &Arc<MemoryStore>,
    ) -> (ToolRegistry, Arc<DispatchPipeline>) {
        let registry = test_registry_with(store);
        let pipeline = Arc::new(DispatchPipeline::with_defaults());
        let (registry, _router) = register_meta_tools_with_router(
            &registry,
            store,
            std::sync::Arc::new(std::sync::RwLock::new(
                embedding_router::ShadowModeStats::default(),
            )),
            Some(pipeline.clone()),
        );
        (registry, pipeline)
    }

    #[tokio::test]
    async fn wm_route_destructive_without_confirm_blocked_by_pipeline() {
        let store = test_store();
        let (registry, _pipeline) = test_registry_with_pipeline(&store);

        let wm = registry.get("wm").unwrap();
        let mut ctx = Context::new(BrainWave::Gamma);
        let result = wm
            .call(
                &mut ctx,
                json!({"route": "memory.delete", "args": {"id": "00000000-0000-0000-0000-000000000001"}}),
            )
            .await
            .unwrap();

        assert_eq!(result["status"], "error");
        assert!(
            result["error"].as_str().unwrap().contains("destructive"),
            "expected destructive-gate message, got: {result}"
        );
        assert!(result["error"].as_str().unwrap().contains("confirm"));
    }

    #[tokio::test]
    async fn wm_route_destructive_with_confirm_proceeds() {
        let store = test_store();
        let (registry, _pipeline) = test_registry_with_pipeline(&store);

        // Create a real memory to delete.
        let memory = Memory::new(Galaxy::Codex, "delete me via wm route".into());
        let id = memory.metadata.id;
        store.put(Galaxy::Codex, &memory).unwrap();

        let wm = registry.get("wm").unwrap();
        let mut ctx = Context::new(BrainWave::Gamma);
        let result = wm
            .call(
                &mut ctx,
                json!({"route": "memory.delete", "args": {"id": id.to_string(), "galaxy": "codex", "confirm": true}}),
            )
            .await
            .unwrap();

        assert_eq!(result["status"], "success");
        assert_eq!(result["_wm_route"]["tool"], "memory.delete");
        assert!(store.get(Galaxy::Codex, id).unwrap().is_none());
    }

    #[tokio::test]
    async fn wm_thought_cannot_reach_destructive_tool() {
        let store = test_store();
        let (registry, _pipeline) = test_registry_with_pipeline(&store);

        let wm = registry.get("wm").unwrap();
        let mut ctx = Context::new(BrainWave::Gamma);
        // "delete memory <uuid>" routes to memory.delete via NLU — must be
        // structurally blocked even with confirm present in extracted payload.
        let result = wm
            .call(
                &mut ctx,
                json!({"thought": "delete memory 00000000-0000-0000-0000-000000000001"}),
            )
            .await
            .unwrap();

        assert_eq!(result["status"], "error");
        assert!(
            result["message"]
                .as_str()
                .unwrap()
                .contains("cannot be reached via natural language"),
            "expected NLU hard-block message, got: {result}"
        );
    }

    #[tokio::test]
    async fn wm_thought_cannot_reach_destructive_tool_even_with_confirm() {
        let store = test_store();
        let (registry, _pipeline) = test_registry_with_pipeline(&store);

        let wm = registry.get("wm").unwrap();
        let mut ctx = Context::new(BrainWave::Gamma);
        // An LLM that guesses the confirm requirement (and supplies the id)
        // must still be blocked — NLU routing is structurally barred from
        // destructive tools.
        let result = wm
            .call(
                &mut ctx,
                json!({"thought": "delete memory 00000000-0000-0000-0000-000000000001", "args": {"confirm": true, "id": "00000000-0000-0000-0000-000000000001"}}),
            )
            .await
            .unwrap();

        assert_eq!(result["status"], "error");
        assert!(
            result["message"]
                .as_str()
                .unwrap()
                .contains("cannot be reached via natural language")
        );
    }

    /// Deterministic fake embedder — exercises the embedding router path
    /// without the stub auto-detect kicking in (backend name != "stub").
    struct FakeVecEmbedder;

    impl wm_memory::Embedder for FakeVecEmbedder {
        fn embed_batch(&self, texts: &[&str]) -> wm_core::Result<Vec<Vec<f32>>> {
            Ok(texts
                .iter()
                .map(|t| {
                    let mut v = vec![0.0_f32; 16];
                    for (i, b) in t.bytes().take(16).enumerate() {
                        v[i] = f32::from(b) / 255.0;
                    }
                    v
                })
                .collect())
        }
        fn dimension(&self) -> usize {
            16
        }
        fn is_available(&self) -> bool {
            true
        }
        fn backend_name(&self) -> &'static str {
            "fake"
        }
    }

    #[tokio::test]
    async fn wm_classify_async_routes_off_thread_with_embedding_router() {
        let store = test_store();
        let registry = test_registry_with(&store);
        let shadow = std::sync::Arc::new(std::sync::RwLock::new(
            embedding_router::ShadowModeStats::default(),
        ));
        let router = embedding_router::EmbeddingRouter::with_descriptions(
            Box::new(FakeVecEmbedder),
            embedding_router::tool_descriptions(),
        )
        .expect("fake-embedder router should build");
        let mut meta = WmMetaTool::with_router_shadow_stats_and_pipeline(
            std::sync::Arc::new(registry),
            wm_memory::create_embedder(),
            shadow,
            None,
        );
        meta.embedding_router = Some(std::sync::Arc::new(router));

        // Runs through spawn_blocking; on the current-thread test runtime this
        // proves the classification path is runtime-agnostic and completes.
        let (tool, conf, emb) = meta.classify_async("remember the meeting notes").await;
        assert!(!tool.is_empty());
        assert!(conf >= 0.0);
        assert!(
            emb.is_some(),
            "query embedding should be returned for OATS reuse"
        );
    }

    #[tokio::test]
    async fn tools_list_shows_all() {
        let store = test_store();
        let registry = test_registry_with(&store);
        let registry = register_meta_tools(
            &registry,
            &store,
            std::sync::Arc::new(std::sync::RwLock::new(
                embedding_router::ShadowModeStats::default(),
            )),
        );

        let list = registry.get("tools.list").unwrap();
        let mut ctx = Context::new(BrainWave::Gamma);
        let result = list.call(&mut ctx, json!({})).await.unwrap();

        assert_eq!(result["status"], "success");
        assert!(result["total"].as_u64().unwrap() >= 7);
    }

    #[tokio::test]
    async fn tools_list_exposes_curated_argument_schemas() {
        let store = test_store();
        let registry = test_registry_with(&store);
        let registry = register_meta_tools(
            &registry,
            &store,
            std::sync::Arc::new(std::sync::RwLock::new(
                embedding_router::ShadowModeStats::default(),
            )),
        );

        let list = registry.get("tools.list").unwrap();
        let mut ctx = Context::new(BrainWave::Gamma);
        let result = list.call(&mut ctx, json!({})).await.unwrap();

        let tools = result["tools"].as_array().unwrap();
        let create = tools
            .iter()
            .find(|t| t["name"] == "memory.create")
            .expect("tools.list must include memory.create");
        let schema = &create["input_schema"];
        assert_eq!(schema["type"], "object");
        assert!(
            schema["properties"].get("content").is_some(),
            "memory.create schema must describe content, got: {schema}"
        );
        assert!(
            schema["required"]
                .as_array()
                .unwrap()
                .iter()
                .any(|r| r == "content"),
            "memory.create schema must require content"
        );

        let rollback = tools
            .iter()
            .find(|t| t["name"] == "transaction.rollback")
            .expect("tools.list must include transaction.rollback");
        assert!(
            rollback["input_schema"]["required"]
                .as_array()
                .unwrap()
                .iter()
                .any(|r| r == "confirm"),
            "transaction.rollback schema must require confirm"
        );

        // MCP annotations derived from EffectRow.
        let annotations = &create["annotations"];
        assert_eq!(annotations["readOnlyHint"], false, "memory.create writes");
        assert_eq!(annotations["destructiveHint"], false);
        assert_eq!(
            rollback["annotations"]["destructiveHint"], true,
            "transaction.rollback is destructive"
        );
        let list_tool = tools
            .iter()
            .find(|t| t["name"] == "memory.list")
            .expect("tools.list must include memory.list");
        assert_eq!(
            list_tool["annotations"]["readOnlyHint"], true,
            "memory.list is read-only"
        );
    }

    #[tokio::test]
    async fn tools_list_filters_by_brain_wave() {
        let store = test_store();
        let registry = test_registry_with(&store);
        let registry = register_meta_tools(
            &registry,
            &store,
            std::sync::Arc::new(std::sync::RwLock::new(
                embedding_router::ShadowModeStats::default(),
            )),
        );

        let list = registry.get("tools.list").unwrap();

        // Gamma: all tools available
        let mut ctx_gamma = Context::new(BrainWave::Gamma);
        let result_gamma = list.call(&mut ctx_gamma, json!({})).await.unwrap();
        let gamma_count = result_gamma["total"].as_u64().unwrap();
        assert!(gamma_count >= 7);

        // Alpha: only read-only tools (no writes, no expensive)
        let mut ctx_alpha = Context::new(BrainWave::Alpha);
        let result_alpha = list.call(&mut ctx_alpha, json!({})).await.unwrap();
        let alpha_count = result_alpha["total"].as_u64().unwrap();
        assert!(alpha_count < gamma_count);
        assert!(alpha_count > 0);

        // Delta: no tools available
        let mut ctx_delta = Context::new(BrainWave::Delta);
        let result_delta = list.call(&mut ctx_delta, json!({})).await.unwrap();
        assert_eq!(result_delta["total"], 0);
    }

    #[tokio::test]
    async fn gnosis_includes_brain_wave_and_tool_count() {
        let store = test_store();
        let registry = test_registry_with(&store);
        let registry = register_meta_tools(
            &registry,
            &store,
            std::sync::Arc::new(std::sync::RwLock::new(
                embedding_router::ShadowModeStats::default(),
            )),
        );

        let gnosis = registry.get("gnosis").unwrap();
        let mut ctx = Context::new(BrainWave::Gamma);
        let result = gnosis.call(&mut ctx, json!({})).await.unwrap();

        assert_eq!(result["status"], "success");
        assert_eq!(result["brain_wave"], "Gamma");
        assert!(result["available_tools"].as_u64().unwrap() >= 9);
    }

    #[tokio::test]
    async fn gnosis_available_tools_is_total_registered() {
        let store = test_store();
        let registry = test_registry_with(&store);
        let registry = register_meta_tools(
            &registry,
            &store,
            std::sync::Arc::new(std::sync::RwLock::new(
                embedding_router::ShadowModeStats::default(),
            )),
        );

        let gnosis = registry.get("gnosis").unwrap();

        // available_tools is now a static count of registered tools,
        // not brain-wave-dependent. It should be the same in all states.
        let mut ctx_gamma = Context::new(BrainWave::Gamma);
        let result_gamma = gnosis.call(&mut ctx_gamma, json!({})).await.unwrap();
        let gamma_tools = result_gamma["available_tools"].as_u64().unwrap();

        let mut ctx_delta = Context::new(BrainWave::Delta);
        let result_delta = gnosis.call(&mut ctx_delta, json!({})).await.unwrap();
        let delta_tools = result_delta["available_tools"].as_u64().unwrap();

        assert_eq!(gamma_tools, delta_tools);
        assert!(
            gamma_tools >= 9,
            "expected at least 9 registered tools, got {gamma_tools}"
        );
    }

    #[tokio::test]
    async fn expansion_brings_tool_count_to_50() {
        let store = test_store();
        let registry = test_registry_with(&store);
        let registry = register_meta_tools(
            &registry,
            &store,
            std::sync::Arc::new(std::sync::RwLock::new(
                embedding_router::ShadowModeStats::default(),
            )),
        );

        let list = registry.get("tools.list").unwrap();
        let mut ctx = Context::new(BrainWave::Gamma);
        let result = list.call(&mut ctx, json!({})).await.unwrap();

        let total = result["total"].as_u64().unwrap();
        assert!(
            total >= 50,
            "Expected 50+ tools after expansion, got {total}"
        );
    }

    // ── NLU Router Expansion Tests ─────────────────────────────────────

    #[tokio::test]
    async fn nlu_routes_consolidate() {
        let (tool, conf) = WmMetaTool::classify("consolidate memories in codex");
        assert_eq!(tool, "memory.consolidate");
        assert!(conf > 0.0);
    }

    #[tokio::test]
    async fn nlu_routes_decay() {
        let (tool, conf) = WmMetaTool::classify("decay old memories");
        assert_eq!(tool, "memory.decay");
        assert!(conf > 0.0);
    }

    #[tokio::test]
    async fn nlu_routes_batch_read() {
        let (tool, conf) = WmMetaTool::classify("batch read these memories");
        assert_eq!(tool, "memory.batch_read");
        assert!(conf > 0.0);
    }

    #[tokio::test]
    async fn nlu_routes_update() {
        let (tool, conf) = WmMetaTool::classify("update memory tags");
        assert_eq!(tool, "memory.update");
        assert!(conf > 0.0);
    }

    #[tokio::test]
    async fn nlu_routes_tag() {
        let (tool, conf) = WmMetaTool::classify("add tag to memory");
        assert_eq!(tool, "memory.tag");
        assert!(conf > 0.0);
    }

    #[tokio::test]
    async fn nlu_routes_memory_stats() {
        let (tool, conf) = WmMetaTool::classify("memory stats for codex");
        assert_eq!(tool, "memory.stats");
        assert!(conf > 0.0);
    }

    #[tokio::test]
    async fn nlu_routes_hybrid_recall() {
        let (tool, conf) = WmMetaTool::classify("hybrid recall for rust");
        assert_eq!(tool, "memory.hybrid_recall");
        assert!(conf > 0.0);
    }

    #[tokio::test]
    async fn nlu_routes_count() {
        let (tool, conf) = WmMetaTool::classify("count memories in codex");
        assert_eq!(tool, "memory.count");
        assert!(conf > 0.0);
    }

    #[tokio::test]
    async fn nlu_routes_tags() {
        let (tool, conf) = WmMetaTool::classify("list tags in codex");
        assert_eq!(tool, "memory.tags");
        assert!(conf > 0.0);
    }

    #[tokio::test]
    async fn nlu_routes_associate_mine() {
        let (tool, conf) = WmMetaTool::classify("mine associations in codex");
        assert_eq!(tool, "memory.associate_mine");
        assert!(conf > 0.0);
    }

    #[tokio::test]
    async fn nlu_routes_session_start() {
        let (tool, conf) = WmMetaTool::classify("start session research");
        assert_eq!(tool, "session.start");
        assert!(conf > 0.0);
    }

    #[tokio::test]
    async fn nlu_routes_session_end() {
        let (tool, conf) = WmMetaTool::classify("end session 12345");
        assert_eq!(tool, "session.end");
        assert!(conf > 0.0);
    }

    #[tokio::test]
    async fn nlu_routes_session_list() {
        let (tool, conf) = WmMetaTool::classify("list sessions");
        assert_eq!(tool, "session.list");
        assert!(conf > 0.0);
    }

    #[tokio::test]
    async fn nlu_routes_citta_status() {
        let (tool, conf) = WmMetaTool::classify("citta status");
        assert_eq!(tool, "citta.status");
        assert!(conf > 0.0);
    }

    #[tokio::test]
    async fn nlu_routes_citta_reflect() {
        let (tool, conf) = WmMetaTool::classify("reflect on recent events");
        assert_eq!(tool, "citta.reflect");
        assert!(conf > 0.0);
    }

    #[tokio::test]
    async fn nlu_routes_coherence() {
        let (tool, conf) = WmMetaTool::classify("check coherence");
        assert_eq!(tool, "citta.coherence");
        assert!(conf > 0.0);
    }

    #[tokio::test]
    async fn nlu_routes_dream_status() {
        let (tool, conf) = WmMetaTool::classify("dream cycle status");
        assert_eq!(tool, "dream.status");
        assert!(conf > 0.0);
    }

    #[tokio::test]
    async fn nlu_routes_dream_trigger() {
        let (tool, conf) = WmMetaTool::classify("trigger dream cycle");
        assert_eq!(tool, "dream.trigger");
        assert!(conf > 0.0);
    }

    #[tokio::test]
    async fn nlu_routes_effectiveness() {
        let (tool, conf) = WmMetaTool::classify("tool effectiveness report");
        assert_eq!(tool, "tools.effectiveness_report");
        assert!(conf > 0.0);
    }

    #[tokio::test]
    async fn nlu_routes_retire() {
        let (tool, conf) = WmMetaTool::classify("retire tool memory.old");
        assert_eq!(tool, "tools.retire");
        assert!(conf > 0.0);
    }

    #[tokio::test]
    async fn nlu_routes_pattern_search() {
        let (tool, conf) = WmMetaTool::classify("pattern search for rust");
        assert_eq!(tool, "pattern.search");
        assert!(conf > 0.0);
    }

    #[tokio::test]
    async fn nlu_routes_salience() {
        let (tool, conf) = WmMetaTool::classify("salience spotlight");
        assert_eq!(tool, "salience.spotlight");
        assert!(conf > 0.0);
    }

    #[tokio::test]
    async fn nlu_routes_serendipity() {
        let (tool, conf) = WmMetaTool::classify("serendipity surface");
        assert_eq!(tool, "serendipity.surface");
        assert!(conf > 0.0);
    }

    #[tokio::test]
    async fn nlu_routes_constellation_detect() {
        let (tool, conf) = WmMetaTool::classify("detect clusters");
        assert_eq!(tool, "constellation.detect");
        assert!(conf > 0.0);
    }

    #[tokio::test]
    async fn nlu_routes_constellation_list() {
        let (tool, conf) = WmMetaTool::classify("list constellations");
        assert_eq!(tool, "constellation.list");
        assert!(conf > 0.0);
    }

    #[tokio::test]
    async fn nlu_routes_galaxy_stats() {
        let (tool, conf) = WmMetaTool::classify("galaxy stats");
        assert_eq!(tool, "galaxy.stats");
        assert!(conf > 0.0);
    }

    #[tokio::test]
    async fn nlu_routes_galaxy_export() {
        let (tool, conf) = WmMetaTool::classify("export galaxy codex");
        assert_eq!(tool, "galaxy.export");
        assert!(conf > 0.0);
    }

    #[tokio::test]
    async fn nlu_routes_galaxy_import() {
        let (tool, conf) = WmMetaTool::classify("import galaxy codex");
        assert_eq!(tool, "galaxy.import");
        assert!(conf > 0.0);
    }

    #[tokio::test]
    async fn nlu_routes_karma_history() {
        let (tool, conf) = WmMetaTool::classify("karma history");
        assert_eq!(tool, "karma.history");
        assert!(conf > 0.0);
    }

    #[tokio::test]
    async fn nlu_routes_karma_clear() {
        let (tool, conf) = WmMetaTool::classify("clear karma");
        assert_eq!(tool, "karma.clear");
        assert!(conf > 0.0);
    }

    #[tokio::test]
    async fn nlu_routes_dharma_rules() {
        let (tool, conf) = WmMetaTool::classify("dharma rules");
        assert_eq!(tool, "dharma.rules");
        assert!(conf > 0.0);
    }

    #[tokio::test]
    async fn nlu_routes_dharma_audit() {
        let (tool, conf) = WmMetaTool::classify("dharma audit");
        assert_eq!(tool, "dharma.audit");
        assert!(conf > 0.0);
    }

    #[tokio::test]
    async fn nlu_routes_dharma_profiles() {
        let (tool, conf) = WmMetaTool::classify("dharma profiles");
        assert_eq!(tool, "dharma.profiles");
        assert!(conf > 0.0);
    }

    #[tokio::test]
    async fn nlu_routes_agent_register() {
        let (tool, conf) = WmMetaTool::classify("register agent worker-1");
        assert_eq!(tool, "agent.register");
        assert!(conf > 0.0);
    }

    #[tokio::test]
    async fn nlu_routes_agent_list() {
        let (tool, conf) = WmMetaTool::classify("list agents");
        assert_eq!(tool, "agent.list");
        assert!(conf > 0.0);
    }

    #[tokio::test]
    async fn nlu_routes_agent_heartbeat() {
        let (tool, conf) = WmMetaTool::classify("heartbeat for agent");
        assert_eq!(tool, "agent.heartbeat");
        assert!(conf > 0.0);
    }

    #[tokio::test]
    async fn nlu_routes_task_distribute() {
        let (tool, conf) = WmMetaTool::classify("distribute task analyze data");
        assert_eq!(tool, "task.distribute");
        assert!(conf > 0.0);
    }

    #[tokio::test]
    async fn nlu_routes_task_status() {
        let (tool, conf) = WmMetaTool::classify("task status");
        assert_eq!(tool, "task.status");
        assert!(conf > 0.0);
    }

    #[tokio::test]
    async fn nlu_routes_system_health() {
        let (tool, conf) = WmMetaTool::classify("system health check");
        assert_eq!(tool, "system.health");
        assert!(conf > 0.0);
    }

    #[tokio::test]
    async fn nlu_routes_system_config() {
        let (tool, conf) = WmMetaTool::classify("system config");
        assert_eq!(tool, "system.config");
        assert!(conf > 0.0);
    }

    #[tokio::test]
    async fn nlu_routes_system_flush() {
        let (tool, conf) = WmMetaTool::classify("flush old memories");
        assert_eq!(tool, "system.flush");
        assert!(conf > 0.0);
    }

    #[tokio::test]
    async fn nlu_routes_memory_nearby() {
        let (tool, conf) = WmMetaTool::classify("nearby memories in codex");
        assert_eq!(tool, "memory.nearby");
        assert!(conf > 0.0);
    }

    #[tokio::test]
    async fn nlu_routes_empty_to_gnosis() {
        let (tool, conf) = WmMetaTool::classify("");
        assert_eq!(tool, "gnosis");
        assert_eq!(conf, 0.0);
    }

    #[tokio::test]
    async fn nlu_routes_unknown_to_gnosis() {
        let (tool, conf) = WmMetaTool::classify("xyzzy frobnicate");
        assert_eq!(tool, "gnosis");
        assert_eq!(conf, 0.0);
    }

    #[tokio::test]
    async fn nlu_extract_payload_memory_search() {
        let (param, value) =
            WmMetaTool::extract_payload("search for rust patterns", "memory.search").unwrap();
        assert_eq!(param, "query");
        assert_eq!(value, "rust patterns");
    }

    #[tokio::test]
    async fn nlu_extract_payload_session_start() {
        // Regression: the payload key was "name", which session.start never
        // reads — natural-language session starts silently created
        // "Untitled Session" entries.
        let (param, value) =
            WmMetaTool::extract_payload("start session research", "session.start").unwrap();
        assert_eq!(param, "title");
        assert_eq!(value, "research");
    }

    #[tokio::test]
    async fn nlu_extract_payload_agent_register() {
        let (param, value) =
            WmMetaTool::extract_payload("register agent worker-1", "agent.register").unwrap();
        assert_eq!(param, "name");
        assert_eq!(value, "worker-1");
    }

    #[tokio::test]
    async fn nlu_extract_payload_task_distribute() {
        let (param, value) =
            WmMetaTool::extract_payload("distribute task analyze data", "task.distribute").unwrap();
        assert_eq!(param, "task");
        assert_eq!(value, "analyze data");
    }

    #[tokio::test]
    async fn nlu_count_unique_patterns() {
        // Verify we have 30+ unique routing targets
        let inputs = [
            "remember",
            "recall",
            "list memories",
            "delete memory",
            "search",
            "query",
            "associate",
            "associations",
            "consolidate",
            "decay",
            "batch read",
            "update memory",
            "tag memory",
            "memory stats",
            "hybrid recall",
            "count memories",
            "list tags",
            "mine associations",
            "start session",
            "checkpoint",
            "recall session",
            "end session",
            "list sessions",
            "citta status",
            "reflect",
            "coherence",
            "dream status",
            "trigger dream",
            "effectiveness",
            "retire tool",
            "pattern search",
            "salience",
            "serendipity",
            "detect clusters",
            "list constellations",
            "galaxy stats",
            "export galaxy",
            "import galaxy",
            "karma",
            "karma history",
            "clear karma",
            "dharma rules",
            "dharma audit",
            "dharma profiles",
            "dharma",
            "register agent",
            "list agents",
            "heartbeat",
            "distribute task",
            "task status",
            "system health",
            "system config",
            "flush",
            "tools",
            "nearby memories",
        ];
        let mut tools: std::collections::HashSet<&str> = std::collections::HashSet::new();
        for input in &inputs {
            let (tool, _) = WmMetaTool::classify(input);
            tools.insert(tool);
        }
        // Should have 30+ unique tool targets
        assert!(
            tools.len() >= 30,
            "Expected 30+ unique NLU targets, got {}",
            tools.len()
        );
    }

    #[tokio::test]
    async fn nlu_routes_shadow_report() {
        let (tool, conf) = WmMetaTool::classify("shadow mode disagreement report");
        assert_eq!(tool, "nlu.shadow_report");
        assert!(conf > 0.0);
    }

    #[tokio::test]
    async fn nlu_routes_oats_report() {
        let (tool, conf) = WmMetaTool::classify("oats disagreement nlu router");
        assert_eq!(tool, "nlu.shadow_report");
        assert!(conf > 0.0);
    }
}
