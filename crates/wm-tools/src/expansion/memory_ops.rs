//! Memory operation tools — consolidate, decay, batch_read, update, tag, stats, hybrid_recall.

#![forbid(unsafe_code)]

use async_trait::async_trait;

use serde_json::{Value, json};
use std::collections::HashMap;
use std::fmt::Write;
use std::sync::Arc;
use wm_core::{Context, EffectRow, Galaxy, Gana, Resource, Tool, ToolStats};
use wm_memory::{
    AssociationStore, MemoryStore, RecallEngine, SearchEngine, episodic::detect_conflicts,
};

use super::common::{
    galaxy_name, int_prop, num_prop, parse_galaxy, parse_galaxy_or, schema, str_prop,
};

/// Resolve a memory id across all memory galaxies. Associations may point at
/// records in any galaxy; callers should not have to guess which one.
fn resolve_memory_across_galaxies(
    store: &MemoryStore,
    id: uuid::Uuid,
) -> Option<(wm_core::Galaxy, wm_memory::Memory)> {
    for galaxy in wm_core::Galaxy::memory_galaxies() {
        if let Ok(Some(mem)) = store.get(galaxy, id) {
            return Some((galaxy, mem));
        }
    }
    None
}

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
        // Full scan: research/sessions galaxies exceed the legacy 10k scan cap,
        // which silently left the tail un-consolidated (B5 heritage dedupe).
        let memories = self.store.scan_all(galaxy)?;
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
        "Update tags, importance, title/topic, or content of an existing memory"
    }
    async fn call(&self, ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
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
        let previous_hash = mem.metadata.content_hash.clone();
        let content_changed = args.get("content").and_then(|v| v.as_str()).is_some();
        if let Some(tags) = args.get("tags").and_then(|v| v.as_array()) {
            mem.metadata.tags = tags
                .iter()
                .filter_map(|t| t.as_str().map(String::from))
                .collect();
        }
        // V8 S11d: the create-path class policy governs update too — a
        // classed memory's importance stays inside its band regardless of
        // which edit path touches it (update cannot mutate tier; now it
        // cannot escape the importance ceiling either).
        let mut class_policy = None;
        if let Some(importance) = args.get("importance").and_then(serde_json::Value::as_f64) {
            let requested = importance as f32;
            let applied = mem.metadata.class.map_or(requested, |class| {
                wm_memory::typology::apply_class_policy(class, requested)
            });
            if (applied - requested).abs() > f32::EPSILON {
                // Round like the write-gate's jnum(): f32 artifacts
                // (0.4000000059604645) must not leak into responses.
                let clean = |v: f32| serde_json::json!((f64::from(v) * 1000.0).round() / 1000.0);
                class_policy = Some(serde_json::json!({
                    "class": mem.metadata.class.map(wm_memory::typology::MemoryClass::as_str),
                    "importance_before": clean(requested),
                    "importance_applied": clean(applied),
                }));
            }
            mem.metadata.importance = applied;
        }
        // Envelope v2 (S4): title/topic are settable and clearable
        // (explicit null clears; absent leaves untouched).
        if let Some(title) = args.get("title") {
            mem.metadata.title = title
                .as_str()
                .map(str::trim)
                .filter(|s| !s.is_empty())
                .map(String::from);
        }
        if let Some(topic) = args.get("topic") {
            mem.metadata.topic = topic
                .as_str()
                .map(str::trim)
                .filter(|s| !s.is_empty())
                .map(String::from);
        }
        if let Some(content) = args.get("content").and_then(|v| v.as_str()) {
            mem.content = content.to_string();
            // Content changes invalidate the hash — keep it in sync so
            // dedup and content-hash lookups stay truthful.
            mem.metadata.content_hash = wm_memory::content_hash(content);
            // V8 S11c: content changes bump the revision counter; the
            // chain entry itself is recorded after the row lands.
            mem.metadata.revision_count = mem.metadata.revision_count.saturating_add(1);
        }
        self.store.put(galaxy, &mem)?;

        // V8 S11c: append the revision entry — seq, hashes, and the
        // attributed actor from the dispatch context. A chain failure
        // degrades loud (warn + disclosure), never silently.
        let mut revision_disclosure = None;
        if content_changed {
            let actor = wm_memory::RevisionActor {
                session: ctx.session_id.map(|sid| sid.to_string()),
                user: ctx.user_id.clone(),
            };
            match self.store.record_revision(
                galaxy,
                id,
                &previous_hash,
                &mem.metadata.content_hash,
                actor,
            ) {
                Ok(rev) => {
                    revision_disclosure = Some(serde_json::json!({
                        "seq": rev.seq,
                        "old_hash": rev.old_hash,
                        "new_hash": rev.new_hash,
                    }));
                }
                Err(e) => {
                    tracing::warn!(error = %e, "revision chain record failed for {id_str}");
                    revision_disclosure = Some(serde_json::json!({"record_failed": e.to_string()}));
                }
            }
        }

        // Phase 3 secrets hygiene: an update that introduces credential-
        // shaped content gets the same boundary warning as memory.create.
        let cred_kinds = args
            .get("content")
            .and_then(serde_json::Value::as_str)
            .map(wm_memory::credential_shaped_content)
            .unwrap_or_default();

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

        let mut response = json!({
            "status": "success",
            "id": mem.metadata.id,
            "galaxy": galaxy_name(galaxy),
            "tags": mem.metadata.tags,
            "importance": mem.metadata.importance,
            // V8 S11a: the write-audit journal scrapes `content_hash` from
            // tool output (pipeline record_write_audit), so disclosing it
            // here gives every update a hash-timeline journal entry;
            // `prev_content_hash` is the agent/human-facing amendment trail.
            "content_hash": mem.metadata.content_hash,
        });
        if content_changed {
            response["prev_content_hash"] = json!(previous_hash);
        }
        if let Some(rev) = revision_disclosure {
            response["revision"] = rev;
        }
        if let Some(policy) = class_policy {
            response["class_policy"] = policy;
        }
        if !cred_kinds.is_empty() {
            response["warnings"] = json!(
                cred_kinds
                    .iter()
                    .map(|k| format!(
                        "content looks like a credential ({k}) — {}",
                        wm_memory::CREDENTIAL_ADVICE
                    ))
                    .collect::<Vec<String>>()
            );
        }
        Ok(response)
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// `memory.revisions` — list or verify a memory's content revision chain
/// (V8 S11c).
///
/// `action: "list"` returns the entries; `action: "verify"` grades the
/// chain against the memory's current content hash (seq continuity, hash
/// linkage, head match) — the tamper-evidence walk.
pub struct MemoryRevisionsTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl MemoryRevisionsTool {
    pub fn new(store: Arc<MemoryStore>) -> Self {
        Self {
            store,
            stats: ToolStats::default(),
            effects: EffectRow {
                reads: super::common::memory_galaxy_reads(),
                ..Default::default()
            },
        }
    }
}

#[async_trait]
impl Tool for MemoryRevisionsTool {
    fn name(&self) -> &str {
        "memory.revisions"
    }
    fn gana(&self) -> Gana {
        Gana::WinnowingBasket
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "List or verify a memory's content revision chain (tamper evidence)"
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let galaxy = parse_galaxy_or(args.get("galaxy").and_then(|v| v.as_str()), Galaxy::Codex)?;
        let id_str = args
            .get("id")
            .and_then(|v| v.as_str())
            .ok_or_else(|| wm_core::CoreError::InvalidArgs("Missing 'id'".into()))?;
        let id = uuid::Uuid::parse_str(id_str)
            .map_err(|e| wm_core::CoreError::InvalidArgs(format!("Invalid UUID: {e}")))?;
        let action = args
            .get("action")
            .and_then(|v| v.as_str())
            .unwrap_or("list");
        let revisions = self.store.revisions(galaxy, id)?;
        match action {
            "verify" => {
                let mem = self.store.get(galaxy, id)?.ok_or_else(|| {
                    wm_core::CoreError::NotFound(format!(
                        "Memory {id} not found in {}",
                        galaxy_name(galaxy)
                    ))
                })?;
                let report =
                    self.store
                        .verify_revision_chain(galaxy, id, &mem.metadata.content_hash)?;
                Ok(json!({
                    "status": "success",
                    "id": id,
                    "galaxy": galaxy_name(galaxy),
                    "action": "verify",
                    "valid": report.valid,
                    "entries": report.entries,
                    "matches_head": report.matches_head,
                    "breaks": report.breaks,
                    "note": if report.entries == 0 {
                        "no revisions recorded (never content-updated or pre-S11c)"
                    } else { "" },
                }))
            }
            "list" => Ok(json!({
                "status": "success",
                "id": id,
                "galaxy": galaxy_name(galaxy),
                "action": "list",
                "count": revisions.len(),
                "revisions": revisions,
            })),
            other => Err(wm_core::CoreError::InvalidArgs(format!(
                "Unknown action '{other}' (expected 'list' or 'verify')"
            ))),
        }
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
    associations: Option<Arc<AssociationStore>>,
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

    /// Attach the association graph for bounded spreading activation:
    /// top results seed a one-hop expansion over typed links, surfacing
    /// connected memories that lexical search alone cannot reach.
    #[must_use]
    pub fn with_associations(mut self, associations: Option<Arc<AssociationStore>>) -> Self {
        self.associations = associations;
        self
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
            associations: None,
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![Resource::Galaxy("codex".into())]),
            route_name,
        }
    }
}

/// Build the empty-result guidance message: name where the content actually
/// lives so callers do not hit the "silent zero" class of failure (e.g.
/// stores whose memories live in `sessions`/`research`, not the default
/// `codex`).
fn empty_result_hint(store: &MemoryStore, galaxy: Galaxy) -> String {
    let mut populated: Vec<String> = Vec::new();
    let mut requested_total = 0usize;
    for g in Galaxy::memory_galaxies() {
        if g == galaxy {
            requested_total = store.count(g).unwrap_or(0);
            continue;
        }
        let n = store.count(g).unwrap_or(0);
        if n > 0 {
            populated.push(format!("{} ({})", g.db_name(), n));
        }
    }
    let location = if requested_total == 0 {
        format!("galaxy '{}' contains no memories", galaxy_name(galaxy))
    } else {
        format!(
            "no matches for this query in '{}' ({} memories)",
            galaxy_name(galaxy),
            requested_total
        )
    };
    if populated.is_empty() {
        format!("{location}; the store is empty")
    } else {
        format!(
            "{}; other galaxies with content: {}. Pass an explicit \"galaxy\" to search there.",
            location,
            populated.join(", ")
        )
    }
}

/// Same guidance for the galaxy-unfiltered search (no `galaxy` argument):
/// the query ran everywhere, so the hint reports the overall corpus shape.
fn empty_result_hint_all(store: &MemoryStore) -> String {
    let mut populated: Vec<String> = Vec::new();
    let mut total = 0usize;
    for g in Galaxy::memory_galaxies() {
        let n = store.count(g).unwrap_or(0);
        total += n;
        if n > 0 {
            populated.push(format!("{} ({})", g.db_name(), n));
        }
    }
    if populated.is_empty() {
        "no matches for this query; the store is empty".to_string()
    } else {
        format!(
            "no matches for this query across all memory galaxies ({} total); populated: {}",
            total,
            populated.join(", ")
        )
    }
}

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
        "Search memories: hybrid BM25+vector fusion with a real embedder; otherwise the episodic deterministic route, falling back to BM25 full-text. Every result discloses recall_mode (hybrid|episodic|fts). memory.hybrid_recall is a compatibility alias."
    }
    fn input_schema(&self) -> Value {
        schema(
            &json!({
                "query": str_prop("Full-text query"),
                "galaxy": str_prop("Galaxy filter (optional; default: search all memory galaxies, results labeled)"),
                "limit": int_prop("Maximum results (default 10)"),
                "min_importance": num_prop("Minimum memory importance (0-1)"),
                "min_score": num_prop("Absolute BM25 score floor"),
                "min_score_ratio": num_prop("Relative floor: reject hits below this fraction of the top score"),
            }),
            &["query"],
        )
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let galaxy_explicit = args.get("galaxy").and_then(|v| v.as_str()).is_some();
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

        // V8.1 trust weighting (evidence-gated): 0.0 = off by default.
        // See wm_memory::trust_weighted_score — enable after the recall
        // benchmark re-run, once heritage source_trust stamps are corrected
        // (wm trust survey / wm trust correct).
        let trust_weight = std::env::var("WM_TRUST_WEIGHT")
            .ok()
            .and_then(|v| v.parse::<f32>().ok())
            .unwrap_or(0.0)
            .clamp(0.0, 1.0);
        // V8 S8 disclosures, populated by Phase 0 when applicable.
        let mut result_extra: Option<serde_json::Value> = None;
        let mut trust_disclosure: Option<serde_json::Value> = None;

        // Recall-mode honesty (V8 ship list #1/#6): which route answered
        // this query is disclosed on the result — hybrid | episodic | fts |
        // importance | none.
        let mut recall_mode = "none";
        // Hybrid fusion requires a REAL embedder: with the stub, vector
        // halves are noise, so a stub-wired engine must not claim the
        // hybrid route (the server already refuses to wire one; this gate
        // makes the tool honest even when constructed directly).
        let hybrid_available = self
            .recall
            .as_ref()
            .is_some_and(|recall| recall.embedder_is_real());

        // Phase 0: If RecallEngine with a real embedder is available, use
        // hybrid BM25 + vector search for fused ranking. Trust weighting
        // lives INSIDE the fusion since V8 S8 (single application point —
        // applying it again here would double-count); the per-result
        // trust_factor + conformal set disclosure come straight from the
        // engine.
        if hybrid_available {
            let recall = self.recall.as_ref().expect("hybrid_available checked");
            if !query.is_empty() {
                let (hybrid_results, conformal) = recall.hybrid_search_with_disclosure(
                    query,
                    limit * 2,
                    galaxy_explicit.then_some(galaxy),
                );
                for hr in hybrid_results {
                    if let Ok(Some(mem)) = self.store.get(hr.galaxy, hr.memory_id) {
                        if mem.metadata.importance >= min_importance
                            && crate::expansion::common::mcp_visible(&mem)
                        {
                            results.push(json!({
                                "id": mem.metadata.id,
                                "galaxy": mem.metadata.galaxy.db_name(),
                                "content": wm_memory::scrub_text(&mem.content),
                                "importance": mem.metadata.importance,
                                "score": hr.score,
                                "trust_factor": hr.trust_factor,
                                "in_conformal_set": hr.in_conformal_set,
                                "bm25_score": hr.bm25_score,
                                "vector_score": hr.vector_score,
                                "trust": mem.metadata.source_trust,
                                "source": "hybrid",
                            }));
                        }
                    }
                }
                // Set-level calibrated coverage disclosure (V8 S8) —
                // attached whenever conformal mode is configured, honest
                // about `uncalibrated` until feedback exists.
                if let Some(info) = conformal {
                    result_extra = serde_json::to_value(&info).ok();
                }
                if trust_weight > 0.0 {
                    trust_disclosure = Some(json!({
                        "wm_trust_weight": trust_weight,
                        "applied_in": "fuse_results",
                    }));
                }
                if !results.is_empty() {
                    recall_mode = "hybrid";
                }
            }
        }

        // Phase E: the episodic deterministic route (V8 ship list #1) —
        // preferred over plain FTS whenever the hybrid route is
        // unavailable. The episodic lane mirrors every v5 write
        // (capture_explicit_memory), its deterministic scorer measures
        // R@1 0.86 vs the BM25 fallback's 0.64 (LongMemEval-S 50q, S8
        // protocol 2026-09-01), and this wire is exactly the v26
        // "one fast brain" lesson: route to the best machinery by
        // default, disclose which one ran. Falls through to FTS only
        // when episodic yields nothing (legacy stores, empty lane,
        // genuine no-match). Pool 100 mirrors the acceptance protocol
        // (retrieve broad, truncate to `limit` below).
        if results.is_empty() && !query.is_empty() && !hybrid_available {
            const EPISODIC_RECALL_POOL: usize = 100;
            let pool = limit.max(EPISODIC_RECALL_POOL);
            // Degradation is never fatal: an episodic-lane error falls
            // through to the FTS phases like an empty lane would.
            let episodic_hits = match self
                .store
                .episodic()
                .search_with_limits(query, pool, pool, false)
            {
                Ok(hits) => hits,
                Err(error) => {
                    tracing::warn!("episodic default-route search failed: {error}");
                    Vec::new()
                }
            };
            for er in episodic_hits {
                // Record ids mirror the v5 memory id; resolve to carry
                // galaxy/importance/visibility from the source of truth.
                let Some((hit_galaxy, mem)) =
                    resolve_memory_across_galaxies(&self.store, er.record.id)
                else {
                    continue;
                };
                if galaxy_explicit && hit_galaxy != galaxy {
                    continue;
                }
                if mem.metadata.importance < min_importance
                    || !crate::expansion::common::mcp_visible(&mem)
                {
                    continue;
                }
                results.push(json!({
                    "id": mem.metadata.id,
                    "galaxy": hit_galaxy.db_name(),
                    "content": wm_memory::scrub_text(&mem.content),
                    "importance": mem.metadata.importance,
                    "score": er.score,
                    "matched_terms": er.matched_terms,
                    "trust": mem.metadata.source_trust,
                    "source": "episodic",
                }));
            }
            if !results.is_empty() {
                recall_mode = "episodic";
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
                        // Explicit galaxy filters at the index. Without one,
                        // the query runs across every memory galaxy — the
                        // Tantivy query was always galaxy-blind, but hits
                        // were resolved against the default galaxy only,
                        // which silently hid sessions/research/dreams
                        // content (found by the post-cutover federated
                        // verification, 2026-08-29).
                        galaxy: galaxy_explicit.then_some(galaxy),
                        ..wm_memory::SearchOptions::default()
                    };
                    let hits = search.search_opt(query, &opts)?;
                    for hit in hits {
                        if let Ok(id) = uuid::Uuid::parse_str(&hit.memory_id) {
                            // Resolve each hit in the galaxy its index
                            // document declares — with no explicit filter
                            // this is the only correct resolution.
                            let hit_galaxy = if galaxy_explicit {
                                Some(galaxy)
                            } else {
                                wm_core::Galaxy::all()
                                    .into_iter()
                                    .find(|g| g.db_name() == hit.galaxy)
                            };
                            let Some(hit_galaxy) = hit_galaxy else {
                                continue;
                            };
                            if let Ok(Some(mem)) = self.store.get(hit_galaxy, id) {
                                if mem.metadata.importance >= min_importance
                                    && crate::expansion::common::mcp_visible(&mem)
                                {
                                    results.push(json!({
                                            "id": mem.metadata.id,
                                            "galaxy": hit_galaxy.db_name(),
                                            "content": wm_memory::scrub_text(&mem.content),
                                            "importance": mem.metadata.importance,
                                            "score": wm_memory::trust_weighted_score(
                                                hit.score,
                                                mem.metadata.source_trust,
                                                trust_weight,
                                            ),
                                            "normalized_score": hit.normalized_score,
                                        "trust": mem.metadata.source_trust,
                                        "source": "fts",
                                    }));
                                    if recall_mode == "none" {
                                        recall_mode = "fts";
                                    }
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
                if recall_mode == "none" {
                    recall_mode = "importance";
                }
            }
        }
        // Phase 3: bounded spreading activation over the association graph.
        // Top seeds from Phases 0-2 activate their one-hop neighbors; neighbors
        // surface as discounted results marked source=association. Read-only:
        // no Hebbian writes, one hop, at most 5 expansions.
        if !results.is_empty() {
            if let Some(assoc_store) = &self.associations {
                let mut anchors: Vec<(uuid::Uuid, f32)> = results
                    .iter()
                    .filter_map(|r| {
                        let id = r.get("id")?.as_str()?;
                        uuid::Uuid::parse_str(id).ok().map(|u| {
                            (
                                u,
                                r.get("score")
                                    .and_then(serde_json::Value::as_f64)
                                    .unwrap_or(0.0) as f32,
                            )
                        })
                    })
                    .collect();
                anchors.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));
                anchors.dedup_by(|a, b| a.0 == b.0);
                anchors.truncate(5);

                let mut expansions: Vec<(uuid::Uuid, f32, f32, String, uuid::Uuid)> = Vec::new();
                for (seed_id, seed_score) in &anchors {
                    let mut links = Vec::new();
                    if let Ok(outgoing) = assoc_store.find_from(self.store.env(), *seed_id) {
                        links.extend(outgoing);
                    }
                    if let Ok(incoming) = assoc_store.find_to(self.store.env(), *seed_id) {
                        links.extend(incoming);
                    }
                    for assoc in links {
                        if assoc.weight < 0.05 {
                            continue;
                        }
                        let neighbor = if assoc.target == *seed_id {
                            assoc.source
                        } else {
                            assoc.target
                        };
                        let score = seed_score * assoc.weight * 0.5;
                        if score <= 0.0 {
                            continue;
                        }
                        expansions.push((
                            neighbor,
                            score,
                            assoc.weight,
                            assoc.link_type.as_str().to_string(),
                            *seed_id,
                        ));
                    }
                }
                expansions.sort_by(|a, b| {
                    b.1.partial_cmp(&a.1)
                        .unwrap_or(std::cmp::Ordering::Equal)
                        .then_with(|| a.0.cmp(&b.0))
                });
                expansions.dedup_by(|a, b| a.0 == b.0);
                expansions.truncate(5);

                let direct_ids: Vec<String> = results
                    .iter()
                    .filter_map(|r| {
                        r.get("id")
                            .and_then(serde_json::Value::as_str)
                            .map(String::from)
                    })
                    .collect();
                for (neighbor_id, score, weight, link_type, seed_id) in expansions {
                    if direct_ids.iter().any(|id| id == &neighbor_id.to_string()) {
                        continue;
                    }
                    let Some((_, mem)) = resolve_memory_across_galaxies(&self.store, neighbor_id)
                    else {
                        continue;
                    };
                    if mem.metadata.importance < min_importance
                        || !crate::expansion::common::mcp_visible(&mem)
                    {
                        continue;
                    }
                    results.push(json!({
                        "id": mem.metadata.id,
                        "content": wm_memory::scrub_text(&mem.content),
                        "importance": mem.metadata.importance,
                        "score": score,
                        "weight": weight,
                        "link_type": link_type,
                        "via": seed_id.to_string(),
                        "source": "association",
                    }));
                }
            }
        }
        // Trust weighting re-orders (Phase 1 pushed in Tantivy's
        // unweighted order); re-sort so the cut at `limit` is honest.
        if trust_weight > 0.0 {
            results.sort_by(|a, b| {
                b.get("score")
                    .and_then(serde_json::Value::as_f64)
                    .partial_cmp(&a.get("score").and_then(serde_json::Value::as_f64))
                    .unwrap_or(std::cmp::Ordering::Equal)
            });
        }
        results.truncate(limit);
        // Empty-result guidance: when a query matched nothing, tell the caller
        // where the content actually lives. Prevents the "silent zero" class
        // of failure (e.g. stores like the vault whose memories live in
        // `sessions`/`research`, not the default `codex`).
        let hint = if results.is_empty() && !query.is_empty() {
            Some(if galaxy_explicit {
                empty_result_hint(&self.store, galaxy)
            } else {
                empty_result_hint_all(&self.store)
            })
        } else {
            None
        };
        let mut out = json!({
            "status": "success",
            "galaxy": if galaxy_explicit {
                serde_json::Value::from(galaxy_name(galaxy))
            } else {
                serde_json::Value::from("all")
            },
            "count": results.len(),
            "recall_mode": recall_mode,
            "results": results,
            "hint": hint,
        });
        // V8 S8 disclosures: the conformal set claim (active/uncalibrated)
        // and, when the trust knob is on, where the weighting was applied.
        if let Some(extra) = result_extra {
            out["conformal_set"] = extra;
        }
        if let Some(td) = trust_disclosure {
            out["trust_weighting"] = td;
        }
        Ok(out)
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// `memory.recall_feedback` — record relevance feedback into the recall
/// engine's conformal calibrator (V8 S8).
///
/// This is how retrieval earns the right to claim coverage: explicit
/// labels (human feedback or a harness with ground truth) become
/// calibration samples; results then carry set membership against a
/// threshold with a real guarantee. Refuses honestly when
/// `WM_RECALL_CONFORMAL_ALPHA` is unset — there is no calibrated set to
/// feed.
pub struct MemoryRecallFeedbackTool {
    recall: Option<Arc<RecallEngine>>,
    stats: ToolStats,
    effects: EffectRow,
}

impl MemoryRecallFeedbackTool {
    #[must_use]
    pub fn new(recall: Option<Arc<RecallEngine>>) -> Self {
        Self {
            recall,
            stats: ToolStats::default(),
            // Persists the fitted classifier JSON to the store root when
            // the calibrator crosses its fit threshold — a filesystem
            // write outside LMDB, declared as a capability (usage is
            // conditional on WM_RECALL_CONFORMAL_ALPHA + fit state).
            effects: EffectRow {
                writes: vec![Resource::Filesystem],
                ..Default::default()
            },
        }
    }
}

#[async_trait]
impl Tool for MemoryRecallFeedbackTool {
    fn name(&self) -> &str {
        "memory.recall_feedback"
    }
    fn gana(&self) -> Gana {
        Gana::WinnowingBasket
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Record relevance feedback for conformal retrieval calibration (V8 S8). Args: samples (array of {score: number 0-1, relevant: bool}) or score+relevant for a single sample. Requires WM_RECALL_CONFORMAL_ALPHA."
    }
    fn input_schema(&self) -> Value {
        schema(
            &json!({
                "samples": {"type": "array", "description": "Feedback samples: [{score: 0-1 fused score, relevant: bool}]"},
                "score": num_prop("Single-sample fused score (0-1)"),
                "relevant": {"type": "boolean", "description": "Single-sample relevance label"},
            }),
            &[],
        )
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let Some(ref recall) = self.recall else {
            return Ok(json!({
                "status": "error",
                "message": "no recall engine on this server (hybrid search unavailable) — nothing to calibrate",
            }));
        };
        let mut samples: Vec<(f32, bool)> = Vec::new();
        if let Some(list) = args.get("samples").and_then(Value::as_array) {
            for s in list {
                let score = s.get("score").and_then(Value::as_f64).unwrap_or(-1.0);
                let relevant = s.get("relevant").and_then(Value::as_bool);
                if !(0.0..=1.0).contains(&score) || relevant.is_none() {
                    return Err(wm_core::CoreError::InvalidArgs(
                        "each sample needs score in [0,1] and a boolean 'relevant'".into(),
                    ));
                }
                samples.push((score as f32, relevant.unwrap_or(false)));
            }
        } else if let Some(score) = args.get("score").and_then(Value::as_f64) {
            let relevant = args
                .get("relevant")
                .and_then(Value::as_bool)
                .ok_or_else(|| {
                    wm_core::CoreError::InvalidArgs("'relevant' is required with 'score'".into())
                })?;
            if !(0.0..=1.0).contains(&score) {
                return Err(wm_core::CoreError::InvalidArgs(
                    "'score' must be within [0,1]".into(),
                ));
            }
            samples.push((score as f32, relevant));
        } else {
            return Err(wm_core::CoreError::InvalidArgs(
                "provide 'samples' (array of {score, relevant}) or a single 'score' + 'relevant'"
                    .into(),
            ));
        }

        let mut recorded = 0usize;
        let mut count = 0usize;
        for (score, relevant) in samples {
            count = recall.record_relevance_feedback(score, relevant)?;
            recorded += 1;
        }
        // Honest post-state disclosure so the caller can see whether the
        // calibrator crossed its fit threshold.
        let status = recall
            .conformal_disclosure(&mut Vec::new())?
            .map_or_else(|| "off".into(), |info| info.status);
        Ok(json!({
            "status": "success",
            "recorded": recorded,
            "calibration_samples": count,
            "conformal_status": status,
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
                    "description": "Rerank mode selector (default 0.7): <1.0 hybrid blend weight; >=1.0 near-tie cosine tiebreaker; >=2.0 protected top-K full cosine reorder (recall@limit preserved by construction)",
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
        let visible: Vec<_> = raw_results
            .into_iter()
            .filter(|hit| !hit.record.is_private && !hit.record.model_exclude)
            .filter(|hit| min_score.is_none_or(|ms| hit.score >= ms))
            .filter(|_| !abstain)
            .take(limit)
            .collect();
        // Read-time contradiction detection over the visible results only
        // (TANGLE semantics: surface both sides with provenance, never
        // silently resolve).
        let conflicts = detect_conflicts(&visible);
        let results = visible
            .into_iter()
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
            // Temporal resolution: true when the query asked for the
            // current/latest value and the topic cluster was reordered by
            // deterministic chronology (see episodic::resolve_current).
            "current_resolution": wm_memory::episodic::is_current_query(query),
            // Detected contradictions among the results, when any: both
            // statements with provenance; the caller decides (TANGLE).
            "conflicts": conflicts,
            "results": results,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// `memory.aggregate` — post-retrieval aggregation over matching memories.
///
/// Retrieves memories with a full-text query (same BM25 path as
/// `memory.search`) and computes an aggregate over the results. Session
/// metrics derive from `session_<n>` tags (a common client convention),
/// letting callers answer cross-session synthesis questions like "how long
/// from X to Y" without scanning raw results themselves.
///
/// For span metrics, the anchor set is narrowed to results matching the
/// rarest query term (fewest matches, ties broken by query order) so that
/// unrelated-but-similar turns (e.g. the same question about a different
/// skill) do not distort the span.
pub struct MemoryAggregateTool {
    search: Option<Arc<SearchEngine>>,
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl MemoryAggregateTool {
    pub fn new(search: Option<Arc<SearchEngine>>, store: Arc<MemoryStore>) -> Self {
        Self {
            search,
            store,
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![Resource::Galaxy("codex".into())]),
        }
    }
}

/// Extract a session ordinal from `session_<n>` tags.
fn session_ordinal(tags: &[String]) -> Option<u64> {
    tags.iter().find_map(|tag| {
        let rest = tag.strip_prefix("session_")?;
        rest.parse::<u64>().ok()
    })
}

/// Word-boundary match of a lowercase query term against content (with a
/// light suffix-stripped variant for morphological tolerance).
fn contains_term(content: &str, term: &str) -> bool {
    let lowered = content.to_ascii_lowercase();
    let variants = [term.to_string(), strip_suffix(term)];
    for variant in &variants {
        if variant.len() < 2 {
            continue;
        }
        let mut start = 0;
        while let Some(pos) = lowered[start..].find(variant.as_str()) {
            let before_ok = pos == 0
                || !lowered[start + pos - 1..start + pos]
                    .chars()
                    .next()
                    .is_some_and(char::is_alphanumeric);
            let end = start + pos + variant.len();
            let after_ok = end >= lowered.len()
                || !lowered[end..]
                    .chars()
                    .next()
                    .is_some_and(char::is_alphanumeric);
            if before_ok && after_ok {
                return true;
            }
            start += pos + variant.len();
        }
    }
    false
}

/// Strip a common English suffix for tolerant matching (mirrors the
/// simple stemmer used by the search tokenizer).
fn strip_suffix(term: &str) -> String {
    for suffix in ["ing", "ed", "es", "s"] {
        if let Some(stem) = term.strip_suffix(suffix) {
            if stem.len() >= 2 {
                return stem.to_string();
            }
        }
    }
    term.to_string()
}

#[async_trait]
impl Tool for MemoryAggregateTool {
    fn name(&self) -> &str {
        "memory.aggregate"
    }
    fn gana(&self) -> Gana {
        Gana::WinnowingBasket
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Aggregate over memories matching a query: count, distinct session count, or session span (cross-session synthesis)"
    }
    fn input_schema(&self) -> Value {
        schema(
            &json!({
                "query": str_prop("Full-text query selecting the memories to aggregate over"),
                "metric": str_prop("Aggregate metric: count | session_count | session_span"),
                "limit": int_prop("Maximum candidates considered (default 50)"),
            }),
            &["query", "metric"],
        )
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let query = args
            .get("query")
            .and_then(Value::as_str)
            .ok_or_else(|| wm_core::CoreError::InvalidArgs("query (string) required".into()))?;
        let metric = args
            .get("metric")
            .and_then(Value::as_str)
            .ok_or_else(|| wm_core::CoreError::InvalidArgs("metric (string) required".into()))?;
        let limit = args.get("limit").and_then(Value::as_u64).unwrap_or(50) as usize;
        let Some(search) = self.search.as_ref() else {
            return Err(wm_core::CoreError::Memory(
                "search engine unavailable for aggregation".into(),
            ));
        };

        let results = search.search(query, limit)?;
        // Load full memories (for tags) and drop non-visible ones.
        let mut memories = Vec::new();
        for r in &results {
            let Some(galaxy) = wm_core::Galaxy::from_db_name(&r.galaxy) else {
                continue;
            };
            let Ok(id) = uuid::Uuid::parse_str(&r.memory_id) else {
                continue;
            };
            let Ok(Some(mem)) = self.store.get(galaxy, id) else {
                continue;
            };
            if super::common::mcp_visible(&mem) {
                memories.push((r.score, mem));
            }
        }

        let evidence: Vec<Value> = memories
            .iter()
            .map(|(score, mem)| {
                json!({
                    "memory_id": mem.metadata.id.to_string(),
                    "score": score,
                    "content": wm_memory::scrub_text(&mem.content),
                    "tags": mem.metadata.tags,
                })
            })
            .collect();

        // Anchor narrowing for session metrics: keep only results matching
        // the rarest query term (fewest matches; ties by query order).
        let session_tagged: Vec<_> = memories
            .iter()
            .filter(|(_, mem)| session_ordinal(&mem.metadata.tags).is_some())
            .collect();
        let anchored: Vec<_> = if metric == "count" || session_tagged.len() < 2 {
            Vec::new()
        } else {
            let terms: Vec<String> = wm_memory::strip_stopwords(query)
                .split(|c: char| !c.is_alphanumeric())
                .filter(|t| t.len() > 1)
                .map(str::to_ascii_lowercase)
                .collect();
            let mut best: Option<(String, usize)> = None;
            for term in &terms {
                let count = session_tagged
                    .iter()
                    .filter(|(_, mem)| contains_term(&mem.content, term))
                    .count();
                if count == 0 {
                    continue;
                }
                let better = best
                    .as_ref()
                    .is_none_or(|(_, best_count)| count < *best_count);
                if better {
                    best = Some((term.clone(), count));
                }
            }
            match best {
                Some((term, _)) => session_tagged
                    .iter()
                    .filter(|(_, mem)| contains_term(&mem.content, &term))
                    .copied()
                    .collect(),
                None => Vec::new(),
            }
        };

        let aggregate = match metric {
            "count" => json!({
                "metric": "count",
                "value": memories.len(),
                "content": format!("{} memories", memories.len()),
            }),
            "session_count" => {
                let sessions: std::collections::HashSet<u64> = anchored
                    .iter()
                    .filter_map(|(_, mem)| session_ordinal(&mem.metadata.tags))
                    .collect();
                json!({
                    "metric": "session_count",
                    "value": sessions.len(),
                    "content": format!("{} distinct sessions", sessions.len()),
                })
            }
            "session_span" => {
                let ordinals: Vec<u64> = anchored
                    .iter()
                    .filter_map(|(_, mem)| session_ordinal(&mem.metadata.tags))
                    .collect();
                if ordinals.is_empty() {
                    json!({
                        "metric": "session_span",
                        "value": null,
                        "content": "no session-tagged evidence found",
                    })
                } else {
                    let span = ordinals.iter().max().unwrap() - ordinals.iter().min().unwrap();
                    json!({
                        "metric": "session_span",
                        "value": span,
                        "unit": "sessions",
                        "content": format!("{span} sessions"),
                    })
                }
            }
            other => {
                return Err(wm_core::CoreError::InvalidArgs(format!(
                    "unknown metric '{other}' (count | session_count | session_span)"
                )));
            }
        };

        Ok(json!({
            "status": "success",
            "query": query,
            "total": memories.len(),
            "aggregate": aggregate,
            "results": evidence,
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
            "recency" => memories.sort_by_key(|x| std::cmp::Reverse(x.metadata.created_at)),
            "accessed" => {
                memories.sort_by_key(|x| std::cmp::Reverse(x.metadata.accessed_at));
            }
            "access_count" => {
                memories.sort_by_key(|x| std::cmp::Reverse(x.metadata.access_count));
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
    fn input_schema(&self) -> Value {
        super::common::schema(
            &json!({
                "galaxy": super::common::str_prop("Galaxy to filter (default codex)"),
                "tags": super::common::str_array_prop("Filter: memories with all of these tags"),
                "exclude_tags": super::common::str_array_prop("Filter: drop memories carrying any of these tags"),
                "min_importance": super::common::num_prop("Filter: minimum importance (0-1)"),
                "max_importance": super::common::num_prop("Filter: maximum importance (0-1)"),
                "created_after": super::common::str_prop("Filter: only memories created at or after this RFC 3339 timestamp (e.g. 2026-08-01T00:00:00Z)"),
                "created_before": super::common::str_prop("Filter: only memories created at or before this RFC 3339 timestamp"),
                "limit": super::common::int_prop("Maximum entries (default 50)"),
                "offset": super::common::int_prop("Skip this many matching entries before returning (default 0)"),
            }),
            &[],
        )
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
        let exclude_tags: Vec<String> = args
            .get("exclude_tags")
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
        let offset = args
            .get("offset")
            .and_then(serde_json::Value::as_u64)
            .unwrap_or(0) as usize;
        // Date range — promised by the description, previously ignored.
        // Bounds are inclusive RFC 3339 timestamps (e.g. "2026-08-01T00:00:00Z").
        let parse_bound = |name: &str| -> wm_core::Result<Option<chrono::DateTime<chrono::Utc>>> {
            match args.get(name).and_then(|v| v.as_str()) {
                Some(s) if !s.trim().is_empty() => chrono::DateTime::parse_from_rfc3339(s.trim())
                    .map(|t| Some(t.with_timezone(&chrono::Utc)))
                    .map_err(|_| {
                        wm_core::CoreError::InvalidArgs(format!(
                            "{name} must be an RFC 3339 timestamp (e.g. \"2026-08-01T00:00:00Z\"), got: {s}"
                        ))
                    }),
                _ => Ok(None),
            }
        };
        let created_after = parse_bound("created_after")?;
        let created_before = parse_bound("created_before")?;

        let memories = self.store.scan(galaxy, 10_000)?;

        let matched: Vec<&wm_memory::Memory> = memories
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
                if !tags.is_empty() && !tags.iter().all(|t| m.metadata.tags.contains(t)) {
                    return false;
                }
                if exclude_tags
                    .iter()
                    .any(|t| m.metadata.tags.iter().any(|mt| mt == t))
                {
                    return false;
                }
                if let Some(after) = created_after {
                    if m.metadata.created_at < after {
                        return false;
                    }
                }
                if let Some(before) = created_before {
                    if m.metadata.created_at > before {
                        return false;
                    }
                }
                true
            })
            .collect();
        // Page AFTER filtering: offset/limit address the visible surface.
        let filtered: Vec<&&wm_memory::Memory> = matched.iter().skip(offset).take(limit).collect();

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
            "matched": matched.len(),
            "offset": offset,
            "returned": results.len(),
            "filters": {
                "tags": tags,
                "exclude_tags": exclude_tags,
                "min_importance": min_importance,
                "max_importance": max_importance,
                "created_after": created_after.map(|t| t.to_rfc3339()),
                "created_before": created_before.map(|t| t.to_rfc3339()),
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
    use wm_memory::{Association, AssociationStore, LinkType, Memory, MemoryStore};

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

    /// Mirror a v5 memory into the episodic lane exactly like the write
    /// path does (capture_explicit_memory): record id = memory id.
    fn mirror_memory(
        store: &Arc<MemoryStore>,
        mem: &Memory,
        session: Option<uuid::Uuid>,
        sequence: u64,
    ) {
        use wm_core::EpisodicCapturePolicy;
        let record = EpisodicRecord::new(
            session,
            sequence,
            EpisodicKind::Observation,
            mem.content.clone(),
            Provenance::new(ProvenanceSource::User),
        )
        .with_id(mem.metadata.id)
        .with_visibility(mem.metadata.is_private, mem.metadata.model_exclude);
        store
            .episodic()
            .append_explicit(&record, EpisodicCapturePolicy::explicit_only())
            .unwrap();
    }

    fn default_search_tool(
        store: Arc<MemoryStore>,
        search: Option<Arc<SearchEngine>>,
    ) -> MemoryHybridRecallTool {
        MemoryHybridRecallTool::as_search(store, search, None)
    }

    #[tokio::test]
    async fn default_route_prefers_episodic_and_discloses_mode() {
        // V8 ship list #1: with no real embedder, memory.search must route
        // through the episodic deterministic machinery by default and
        // disclose `recall_mode: episodic` + per-result `source`.
        let (_dir, store, search) = hybrid_fixture();
        let needle = Memory::new(
            Galaxy::Codex,
            "Kotlin coroutine budget meeting notes".into(),
        );
        let needle_id = needle.metadata.id;
        let other = Memory::new(Galaxy::Codex, "Grocery list eggs and flour".into());
        store.put(Galaxy::Codex, &needle).unwrap();
        store.put(Galaxy::Codex, &other).unwrap();
        mirror_memory(&store, &needle, None, 1);
        mirror_memory(&store, &other, None, 2);

        let tool = default_search_tool(store.clone(), Some(search));
        let mut ctx = Context::default();
        let v = tool
            .call(
                &mut ctx,
                json!({"query": "kotlin coroutine budget", "limit": 10}),
            )
            .await
            .unwrap();
        assert_eq!(v["recall_mode"], "episodic");
        assert_eq!(v["results"][0]["source"], "episodic");
        assert_eq!(v["results"][0]["id"], json!(needle_id.to_string()));
        assert!(v["results"][0]["score"].as_f64().unwrap() > 0.0);
    }

    #[tokio::test]
    async fn default_route_matches_the_episodic_machinery_ranking() {
        // The default route must BE the episodic machinery, not a lookalike:
        // same corpus, same query, first result identical to
        // memory.episodic_search's top hit.
        let (_dir, store, search) = hybrid_fixture();
        let contents = [
            "Deployed the telemetry agent on Tuesday",
            "Cancun trip booked for the twelfth",
            "Telemetry agent rollout postponed to Friday",
            "Deadline for the quarterly report moved",
        ];
        let mut memories: Vec<(uuid::Uuid, &str)> = Vec::new();
        for (i, content) in contents.iter().enumerate() {
            let mem = Memory::new(Galaxy::Codex, (*content).to_string());
            memories.push((mem.metadata.id, content));
            store.put(Galaxy::Codex, &mem).unwrap();
            mirror_memory(&store, &mem, None, i as u64 + 1);
        }
        let query = "when was the telemetry agent deployed";

        let default_tool = default_search_tool(store.clone(), Some(search.clone()));
        let mut ctx = Context::default();
        let default_v = default_tool
            .call(&mut ctx, json!({"query": query, "limit": 10}))
            .await
            .unwrap();
        let episodic_tool = MemoryEpisodicSearchTool::new(store);
        let episodic_v = episodic_tool
            .call(&mut ctx, json!({"query": query, "limit": 10}))
            .await
            .unwrap();
        assert_eq!(
            default_v["results"][0]["id"], episodic_v["results"][0]["id"],
            "default route must rank exactly like the episodic machinery"
        );
        let top = memories
            .iter()
            .find(|(id, _)| id.to_string() == default_v["results"][0]["id"])
            .map(|(_, c)| *c)
            .unwrap();
        assert_eq!(top, "Deployed the telemetry agent on Tuesday");
    }

    #[tokio::test]
    async fn default_route_falls_back_to_fts_when_episodic_yields_nothing() {
        // Legacy store shape: memories indexed but the episodic lane never
        // populated. The default route must disclose `fts` honestly.
        let (_dir, store, search) = hybrid_fixture();
        let mem = Memory::new(Galaxy::Codex, "Zebra quotas revised upward".into());
        let id = mem.metadata.id;
        store.put(Galaxy::Codex, &mem).unwrap();
        {
            let mut writer = search.writer().unwrap();
            search
                .add_document(
                    &mut writer,
                    &id.to_string(),
                    "codex",
                    "Zebra quotas revised upward",
                    &mem.metadata.tags,
                    mem.metadata.created_at.timestamp(),
                )
                .unwrap();
            search.commit(&mut writer).unwrap();
        }

        let tool = default_search_tool(store, Some(search));
        let mut ctx = Context::default();
        let v = tool
            .call(&mut ctx, json!({"query": "zebra quotas", "limit": 10}))
            .await
            .unwrap();
        assert_eq!(v["recall_mode"], "fts");
        assert_eq!(v["results"][0]["source"], "fts");
        assert_eq!(v["results"][0]["id"], json!(id.to_string()));
    }

    #[tokio::test]
    async fn episodic_default_route_respects_galaxy_filter() {
        let (_dir, store, search) = hybrid_fixture();
        let in_galaxy = Memory::new(Galaxy::Codex, "Marble fountain restoration plan".into());
        let other_galaxy =
            Memory::new(Galaxy::Sessions, "Marble fountain restoration notes".into());
        store.put(Galaxy::Codex, &in_galaxy).unwrap();
        store.put(Galaxy::Sessions, &other_galaxy).unwrap();
        mirror_memory(&store, &in_galaxy, None, 1);
        mirror_memory(&store, &other_galaxy, None, 2);

        let tool = default_search_tool(store, Some(search));
        let mut ctx = Context::default();
        let v = tool
            .call(
                &mut ctx,
                json!({"query": "marble fountain", "galaxy": "sessions", "limit": 10}),
            )
            .await
            .unwrap();
        assert_eq!(v["recall_mode"], "episodic");
        for r in v["results"].as_array().unwrap() {
            assert_eq!(r["galaxy"], "sessions", "galaxy filter must hold");
        }
        assert_eq!(
            v["results"][0]["id"],
            json!(other_galaxy.metadata.id.to_string())
        );
    }

    #[tokio::test]
    async fn episodic_default_route_filters_private_and_stale() {
        let (_dir, store, search) = hybrid_fixture();
        let public = Memory::new(
            Galaxy::Codex,
            "Lighthouse maintenance schedule confirmed".into(),
        );
        let mut private = Memory::new(Galaxy::Codex, "Lighthouse access code renewal".into());
        private.metadata.is_private = true;
        let stale = Memory::new(Galaxy::Codex, "Lighthouse inspection legacy draft".into());
        let stale_id = stale.metadata.id;
        store.put(Galaxy::Codex, &public).unwrap();
        store.put(Galaxy::Codex, &private).unwrap();
        store.put(Galaxy::Codex, &stale).unwrap();
        mirror_memory(&store, &public, None, 1);
        mirror_memory(&store, &private, None, 2);
        mirror_memory(&store, &stale, None, 3);
        // The stale record's v5 memory is gone — the mirror survived, the
        // source of truth did not.
        store.delete(Galaxy::Codex, stale_id).unwrap();

        let tool = default_search_tool(store, Some(search));
        let mut ctx = Context::default();
        let v = tool
            .call(&mut ctx, json!({"query": "lighthouse", "limit": 10}))
            .await
            .unwrap();
        assert_eq!(v["recall_mode"], "episodic");
        let ids: Vec<&str> = v["results"]
            .as_array()
            .unwrap()
            .iter()
            .filter_map(|r| r["id"].as_str())
            .collect();
        assert!(
            !ids.contains(&private.metadata.id.to_string().as_str()),
            "private memories must never surface on the default route"
        );
        assert!(
            !ids.contains(&stale_id.to_string().as_str()),
            "episodic records without a live v5 memory must be skipped"
        );
        assert!(!ids.is_empty(), "the public hit must still surface");
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
    async fn memory_update_cannot_mutate_tier() {
        // S5 phase 2: tier moves are dream-cycle-ONLY. The update tool
        // whitelists its fields — a `tier` argument in the payload must be
        // ignored, not applied.
        let store = test_store();
        let mem = Memory::new(Galaxy::Codex, "tier is not client-settable".into());
        let id = mem.metadata.id;
        store.put(Galaxy::Codex, &mem).unwrap();

        let tool = MemoryUpdateTool::new(store.clone(), None);
        let mut ctx = Context::default();
        let v = tool
            .call(
                &mut ctx,
                json!({"galaxy": "codex", "id": id.to_string(), "tier": "archival", "tags": ["x"]}),
            )
            .await
            .unwrap();
        assert_eq!(v["status"], "success");

        let after = store.get(Galaxy::Codex, id).unwrap().unwrap();
        assert_eq!(
            after.metadata.tier,
            wm_memory::Tier::Working,
            "memory.update must never move the tier"
        );
        assert_eq!(
            after.metadata.tags,
            vec!["x".to_string()],
            "whitelisted fields still apply"
        );
    }

    #[tokio::test]
    async fn empty_search_hints_at_populated_galaxies() {
        // Content lives in `sessions`, not `codex` (the vault-store shape).
        // The galaxy-unfiltered default (no `galaxy` arg) must FIND it and
        // label the result with its galaxy — that is the post-cutover fix
        // (2026-08-29): hits used to be resolved against `codex` only.
        let (_dir, store, search) = hybrid_fixture();
        index_memory(&store, &search, Galaxy::Sessions, "gate plan decision");
        let tool = MemoryHybridRecallTool::new(store.clone(), Some(search), None);
        let mut ctx = Context::default();
        let v = tool
            .call(&mut ctx, json!({"query": "gate plan"}))
            .await
            .unwrap();
        assert_eq!(
            v["count"], 1,
            "unfiltered search must find cross-galaxy content: {v}"
        );
        assert_eq!(v["galaxy"], "all");
        assert_eq!(v["results"][0]["galaxy"], "sessions");
        assert!(v["hint"].is_null());

        // An explicit galaxy still filters at the index and hints on a miss.
        let v2 = tool
            .call(
                &mut ctx,
                json!({"query": "zzz-no-match", "galaxy": "sessions"}),
            )
            .await
            .unwrap();
        assert_eq!(v2["count"], 0);
        let hint2 = v2["hint"].as_str().unwrap();
        assert!(hint2.contains("no matches for this query"), "{hint2}");

        // A no-match query WITHOUT a galaxy filter searches everywhere and
        // reports the overall corpus shape instead of a per-galaxy view.
        let v3 = tool
            .call(&mut ctx, json!({"query": "zzz-no-match"}))
            .await
            .unwrap();
        assert_eq!(v3["count"], 0);
        let hint3 = v3["hint"].as_str().expect("hint present on empty result");
        assert!(hint3.contains("across all memory galaxies"), "{hint3}");
    }

    #[tokio::test]
    async fn unfiltered_search_labels_hits_from_every_galaxy() {
        // Content spread across three galaxies; the default search (no
        // `galaxy` arg) must surface all of them, each labeled. This is the
        // federated-recall regression: every backing's rich content lived
        // outside `codex` and the old resolution path returned silent zeros.
        let (_dir, store, search) = hybrid_fixture();
        index_memory(
            &store,
            &search,
            Galaxy::Sessions,
            "lineage ledger phase four",
        );
        index_memory(
            &store,
            &search,
            Galaxy::Codex,
            "lineage ledger codex mirror note",
        );
        index_memory(&store, &search, Galaxy::Dreams, "lineage ledger dream echo");
        let tool = MemoryHybridRecallTool::new(store.clone(), Some(search), None);
        let mut ctx = Context::default();
        let v = tool
            .call(&mut ctx, json!({"query": "lineage ledger", "limit": 10}))
            .await
            .unwrap();
        assert_eq!(v["count"], 3, "got: {v}");
        let galaxies: Vec<&str> = v["results"]
            .as_array()
            .unwrap()
            .iter()
            .map(|r| r["galaxy"].as_str().unwrap())
            .collect();
        assert!(galaxies.contains(&"sessions"), "got: {galaxies:?}");
        assert!(galaxies.contains(&"codex"), "got: {galaxies:?}");
        assert!(galaxies.contains(&"dreams"), "got: {galaxies:?}");

        // Explicit galaxy filters to exactly that galaxy.
        let v2 = tool
            .call(
                &mut ctx,
                json!({"query": "lineage ledger", "galaxy": "dreams"}),
            )
            .await
            .unwrap();
        assert_eq!(v2["count"], 1, "got: {v2}");
        assert_eq!(v2["results"][0]["galaxy"], "dreams");
    }

    #[tokio::test]
    async fn successful_search_carries_no_hint() {
        let (_dir, store, search) = hybrid_fixture();
        index_memory(&store, &search, Galaxy::Sessions, "gate plan decision");
        let tool = MemoryHybridRecallTool::new(store, Some(search), None);
        let mut ctx = Context::default();
        let v = tool
            .call(
                &mut ctx,
                json!({"query": "gate plan", "galaxy": "sessions"}),
            )
            .await
            .unwrap();
        assert_eq!(v["count"], 1);
        assert!(v["hint"].is_null());
    }

    #[tokio::test]
    async fn associative_expansion_surfaces_linked_memory() {
        // The core spreading-activation contract: a direct hit on memory A
        // activates its one-hop neighbor B even though B shares no query
        // terms, and B is marked source=association with its link metadata.
        let dir = tempfile::tempdir().unwrap();
        let store = Arc::new(MemoryStore::open_default(dir.path()).unwrap());
        let tantivy_dir = dir.path().join("tantivy");
        std::fs::create_dir_all(&tantivy_dir).unwrap();
        let search = Arc::new(SearchEngine::open(&tantivy_dir).unwrap());
        index_memory(
            &store,
            &search,
            Galaxy::Codex,
            "gate plan for the v7 alpha release",
        );
        let mut linked = Memory::new(
            Galaxy::Codex,
            "backup automation runs nightly at 03:30".into(),
        );
        linked.metadata.importance = 0.7;
        let linked_id = linked.metadata.id;
        store.put(Galaxy::Codex, &linked).unwrap();
        search
            .writer()
            .and_then(|mut w| {
                search.add_document(
                    &mut w,
                    &linked_id.to_string(),
                    "codex",
                    &linked.content,
                    &linked.metadata.tags,
                    linked.metadata.created_at.timestamp(),
                )?;
                search.commit(&mut w)
            })
            .unwrap();

        // The association must NOT share vocabulary with the query.
        let assoc = Association::new(
            find_id(&store, "gate plan"),
            linked_id,
            LinkType::Extends,
            0.8,
        );
        let associations = Arc::new(AssociationStore::open(store.env()).unwrap());
        associations.put(store.env(), &assoc).unwrap();

        let tool = MemoryHybridRecallTool::as_search(store.clone(), Some(search), None)
            .with_associations(Some(associations));
        let mut ctx = Context::default();
        let v = tool
            .call(&mut ctx, json!({"query": "gate plan alpha release"}))
            .await
            .unwrap();
        assert_eq!(v["count"], 2, "direct hit + associated memory: {v}");
        let assoc_hit = v["results"]
            .as_array()
            .unwrap()
            .iter()
            .find(|r| r["source"] == "association")
            .expect("association-sourced result present");
        assert_eq!(assoc_hit["id"], json!(linked_id.to_string()));
        assert_eq!(assoc_hit["link_type"], "extends");
        assert!(assoc_hit["via"].is_string());
        assert!(assoc_hit["weight"].as_f64().unwrap() > 0.7);
    }

    fn find_id(store: &MemoryStore, needle: &str) -> uuid::Uuid {
        store
            .scan(Galaxy::Codex, 100)
            .unwrap()
            .into_iter()
            .find(|m| m.content.contains(needle))
            .map(|m| m.metadata.id)
            .unwrap()
    }

    #[tokio::test]
    async fn associative_expansion_skips_private_and_dedupes() {
        let dir = tempfile::tempdir().unwrap();
        let store = Arc::new(MemoryStore::open_default(dir.path()).unwrap());
        let mut a = Memory::new(Galaxy::Codex, "quarterly revenue planning notes".into());
        a.metadata.importance = 0.8;
        let a_id = a.metadata.id;
        store.put(Galaxy::Codex, &a).unwrap();
        // Private neighbor: must never surface through expansion.
        let mut private = Memory::new(Galaxy::Codex, "private salary bands".into());
        private.metadata.is_private = true;
        private.metadata.importance = 0.8;
        store.put(Galaxy::Codex, &private).unwrap();
        // Public neighbor linked twice (both directions) — must appear once.
        let mut b = Memory::new(Galaxy::Codex, "hiring plan for next quarter".into());
        b.metadata.importance = 0.7;
        let b_id = b.metadata.id;
        store.put(Galaxy::Codex, &b).unwrap();

        let associations = Arc::new(AssociationStore::open(store.env()).unwrap());
        associations
            .put(
                store.env(),
                &Association::new(a_id, private.metadata.id, LinkType::Related, 0.9),
            )
            .unwrap();
        associations
            .put(
                store.env(),
                &Association::new(a_id, b_id, LinkType::Related, 0.9),
            )
            .unwrap();
        associations
            .put(
                store.env(),
                &Association::new(b_id, a_id, LinkType::Related, 0.9),
            )
            .unwrap();

        let tool = MemoryHybridRecallTool::as_search(store.clone(), None, None)
            .with_associations(Some(associations.clone()));
        let mut ctx = Context::default();
        // No SearchEngine: scan-free importance path still seeds anchors? No —
        // with no query there is no seed; use a query but no FTS: results come
        // from Phase 1 only when search is present. So attach a search engine.
        let _ = &tool;
        let tantivy_dir = dir.path().join("tantivy");
        std::fs::create_dir_all(&tantivy_dir).unwrap();
        let search = Arc::new(SearchEngine::open(&tantivy_dir).unwrap());
        for (content, id) in [
            ("quarterly revenue planning notes", a_id),
            ("private salary bands", private.metadata.id),
            ("hiring plan for next quarter", b_id),
        ] {
            search
                .writer()
                .and_then(|mut w| {
                    search.add_document(&mut w, &id.to_string(), "codex", content, &[], 0)?;
                    search.commit(&mut w)
                })
                .unwrap();
        }
        let tool = MemoryHybridRecallTool::as_search(store.clone(), Some(search), None)
            .with_associations(Some(associations));
        let v = tool
            .call(&mut ctx, json!({"query": "quarterly revenue planning"}))
            .await
            .unwrap();
        let ids: Vec<&str> = v["results"]
            .as_array()
            .unwrap()
            .iter()
            .filter_map(|r| r["id"].as_str())
            .collect();
        assert!(
            !ids.iter().any(|id| *id == private.metadata.id.to_string()),
            "private memory must not surface via association: {ids:?}"
        );
        assert_eq!(
            ids.iter().filter(|id| **id == b_id.to_string()).count(),
            1,
            "neighbor linked both directions appears exactly once: {ids:?}"
        );
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
    async fn memory_update_discloses_hash_timeline() {
        // V8 S11a: every update response carries the (new) content_hash so
        // the write-audit journal records a hash timeline per memory; a
        // content-changing update additionally carries prev_content_hash.
        let store = test_store();
        let mem = Memory::new(Galaxy::Codex, "original text".into());
        store.put(Galaxy::Codex, &mem).unwrap();
        let id = mem.metadata.id;
        let original_hash = mem.metadata.content_hash.clone();
        let tool = MemoryUpdateTool::new(store.clone(), None);
        let mut ctx = Context::default();

        let v = tool
            .call(
                &mut ctx,
                json!({"galaxy": "codex", "id": id.to_string(), "content": "changed text"}),
            )
            .await
            .unwrap();
        assert_eq!(
            v["content_hash"],
            json!(wm_memory::content_hash("changed text"))
        );
        assert_eq!(v["prev_content_hash"], json!(original_hash));

        // A metadata-only update discloses the current hash and no prev.
        let v = tool
            .call(
                &mut ctx,
                json!({"galaxy": "codex", "id": id.to_string(), "tags": ["amended"]}),
            )
            .await
            .unwrap();
        assert_eq!(
            v["content_hash"],
            json!(wm_memory::content_hash("changed text"))
        );
        assert!(v.get("prev_content_hash").is_none());
    }

    #[tokio::test]
    async fn memory_update_appends_revision_chain() {
        // V8 S11c: content changes append hash-linked revision entries;
        // metadata-only edits do not; the actor rides in from the context.
        let store = test_store();
        let mem = Memory::new(Galaxy::Codex, "original text".into());
        store.put(Galaxy::Codex, &mem).unwrap();
        let id = mem.metadata.id;
        let tool = MemoryUpdateTool::new(store.clone(), None);
        let mut ctx = Context {
            user_id: Some("agent-b".to_string()),
            session_id: Some(uuid::Uuid::nil()),
            ..Default::default()
        };
        let v = tool
            .call(
                &mut ctx,
                json!({"galaxy": "codex", "id": id.to_string(), "content": "second text"}),
            )
            .await
            .unwrap();
        assert_eq!(v["revision"]["seq"], 0);
        assert_eq!(
            v["revision"]["old_hash"],
            json!(wm_memory::content_hash("original text"))
        );
        assert_eq!(
            v["revision"]["new_hash"],
            json!(wm_memory::content_hash("second text"))
        );

        let v = tool
            .call(
                &mut ctx,
                json!({"galaxy": "codex", "id": id.to_string(), "content": "third text"}),
            )
            .await
            .unwrap();
        assert_eq!(v["revision"]["seq"], 1);

        let revisions = store.revisions(Galaxy::Codex, id).unwrap();
        assert_eq!(revisions.len(), 2);
        assert_eq!(revisions[1].old_hash, revisions[0].new_hash, "chain links");
        assert_eq!(revisions[0].actor_user.as_deref(), Some("agent-b"));
        assert_eq!(
            revisions[0].actor_session.as_deref(),
            Some(uuid::Uuid::nil().to_string().as_str())
        );

        let stored = store.get(Galaxy::Codex, id).unwrap().unwrap();
        assert_eq!(stored.metadata.revision_count, 2);

        // The honest chain verifies clean against the live content hash.
        let report = store
            .verify_revision_chain(Galaxy::Codex, id, &stored.metadata.content_hash)
            .unwrap();
        assert!(report.valid, "{:?}", report.breaks);
        assert!(report.matches_head);
    }

    #[tokio::test]
    async fn memory_update_out_of_band_edit_breaks_chain() {
        // Content changed WITHOUT the update tool (the write path the
        // journal sees but cannot describe) must break the head match.
        let store = test_store();
        let mem = Memory::new(Galaxy::Codex, "original text".into());
        store.put(Galaxy::Codex, &mem).unwrap();
        let id = mem.metadata.id;
        let tool = MemoryUpdateTool::new(store.clone(), None);
        tool.call(
            &mut Context::default(),
            json!({"galaxy": "codex", "id": id.to_string(), "content": "second text"}),
        )
        .await
        .unwrap();

        // Out-of-band rewrite: hash moved, no revision appended.
        let mut row = store.get(Galaxy::Codex, id).unwrap().unwrap();
        row.content = "smuggled text".to_string();
        row.metadata.content_hash = wm_memory::content_hash("smuggled text");
        store.put(Galaxy::Codex, &row).unwrap();

        let report = store
            .verify_revision_chain(Galaxy::Codex, id, &row.metadata.content_hash)
            .unwrap();
        assert!(!report.valid);
        assert!(!report.matches_head);
        assert!(report.breaks.iter().any(|b| b.contains("head mismatch")));
    }

    #[tokio::test]
    async fn memory_revisions_tool_list_and_verify() {
        let store = test_store();
        let mem = Memory::new(Galaxy::Codex, "v1".into());
        store.put(Galaxy::Codex, &mem).unwrap();
        let id = mem.metadata.id;
        let update = MemoryUpdateTool::new(store.clone(), None);
        update
            .call(
                &mut Context::default(),
                json!({"galaxy": "codex", "id": id.to_string(), "content": "v2"}),
            )
            .await
            .unwrap();

        let tool = MemoryRevisionsTool::new(store.clone());
        let v = tool
            .call(&mut Context::default(), json!({"id": id.to_string()}))
            .await
            .unwrap();
        assert_eq!(v["action"], "list");
        assert_eq!(v["count"], 1);

        let v = tool
            .call(
                &mut Context::default(),
                json!({"id": id.to_string(), "action": "verify"}),
            )
            .await
            .unwrap();
        assert_eq!(v["valid"], true);
        assert_eq!(v["entries"], 1);

        // An injected splice is detectable: entry 1 claims an old_hash the
        // chain never produced.
        store
            .record_revision(
                Galaxy::Codex,
                id,
                "forged_old_hash",
                &wm_memory::content_hash("v2"),
                wm_memory::RevisionActor::default(),
            )
            .unwrap();
        let v = tool
            .call(
                &mut Context::default(),
                json!({"id": id.to_string(), "action": "verify"}),
            )
            .await
            .unwrap();
        assert_eq!(v["valid"], false);
        let breaks: Vec<String> = v["breaks"]
            .as_array()
            .unwrap()
            .iter()
            .map(|b| b.as_str().unwrap().to_string())
            .collect();
        assert!(
            breaks.iter().any(|b| b.contains("hash-linkage")),
            "{breaks:?}"
        );
    }

    #[tokio::test]
    async fn memory_update_class_policy_caps_telemetry_and_floors_dialogue() {
        // V8 S11d: update cannot push a classed memory outside its band.
        let store = test_store();

        // Telemetry by construction (template shape) → ceiling 0.40.
        let tel = Memory::new(
            Galaxy::Codex,
            "## Auto-logged Friction: dispatch error\n\nbody".into(),
        );
        store.put(Galaxy::Codex, &tel).unwrap();
        // Dialogue by construction (start tag + stamped class) → floor 0.75.
        let mut dlg = Memory::new(Galaxy::Codex, "session marker".into());
        dlg.metadata.tags.push("start".to_string());
        dlg.metadata.class = Some(wm_memory::typology::MemoryClass::Dialogue);
        store.put(Galaxy::Codex, &dlg).unwrap();

        let tool = MemoryUpdateTool::new(store.clone(), None);
        let mut ctx = Context::default();

        let v = tool
            .call(
                &mut ctx,
                json!({"galaxy": "codex", "id": tel.metadata.id.to_string(), "importance": 0.9}),
            )
            .await
            .unwrap();
        assert_eq!(v["class_policy"]["importance_applied"], 0.40);
        let stored = store.get(Galaxy::Codex, tel.metadata.id).unwrap().unwrap();
        assert!((stored.metadata.importance - 0.40).abs() < 1e-5);

        let v = tool
            .call(
                &mut ctx,
                json!({"galaxy": "codex", "id": dlg.metadata.id.to_string(), "importance": 0.2}),
            )
            .await
            .unwrap();
        assert_eq!(v["class_policy"]["importance_applied"], 0.75);
        let stored = store.get(Galaxy::Codex, dlg.metadata.id).unwrap().unwrap();
        assert!((stored.metadata.importance - 0.75).abs() < 1e-5);

        // Unstamped memories stay untouched by the policy.
        let plain = Memory::new(Galaxy::Codex, "a normal thought".into());
        store.put(Galaxy::Codex, &plain).unwrap();
        let v = tool
            .call(
                &mut ctx,
                json!({"galaxy": "codex", "id": plain.metadata.id.to_string(), "importance": 0.95}),
            )
            .await
            .unwrap();
        assert!(v.get("class_policy").is_none());
        let stored = store
            .get(Galaxy::Codex, plain.metadata.id)
            .unwrap()
            .unwrap();
        assert!((stored.metadata.importance - 0.95).abs() < 1e-5);
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

    /// API honesty (§8): `offset`, `exclude_tags`, and the date range the
    /// description always promised are real. Paging addresses the VISIBLE
    /// surface.
    #[tokio::test]
    async fn memory_filter_offset_exclude_tags_and_date_range() {
        let store = test_store();
        let tool = MemoryFilterTool::new(store.clone());
        let mut ctx = Context::default();

        let mut recent_a = Memory::new(Galaxy::Codex, "recent a".into());
        recent_a.metadata.created_at = chrono::Utc::now() - chrono::Duration::hours(2);
        let mut recent_b = Memory::new(Galaxy::Codex, "recent b".into());
        recent_b.metadata.created_at = chrono::Utc::now() - chrono::Duration::hours(1);
        recent_b.metadata.tags = vec!["noise".into()];
        let mut recent_priv = Memory::new(Galaxy::Codex, "recent private".into());
        recent_priv.metadata.created_at = chrono::Utc::now() - chrono::Duration::minutes(90);
        recent_priv.metadata.is_private = true;
        let mut old = Memory::new(Galaxy::Codex, "old relic".into());
        old.metadata.created_at = chrono::Utc::now() - chrono::Duration::days(60);
        for m in [&recent_a, &recent_b, &recent_priv, &old] {
            store.put(Galaxy::Codex, m).unwrap();
        }

        let cutoff = (chrono::Utc::now() - chrono::Duration::days(1))
            .to_rfc3339_opts(chrono::SecondsFormat::Millis, true);

        // Date range + exclude_tags + privacy all compose.
        let v = tool
            .call(
                &mut ctx,
                json!({
                    "galaxy": "codex",
                    "created_after": cutoff,
                    "exclude_tags": ["noise"],
                }),
            )
            .await
            .unwrap();
        assert_eq!(v["matched"], 1, "only recent-a is visible in range: {v}");
        assert_eq!(v["returned"], 1);
        assert_eq!(v["memories"][0]["content"], "recent a");
        assert_eq!(v["filters"]["exclude_tags"], json!(["noise"]));
        assert!(v["filters"]["created_after"].is_string());

        // Offset pages the matched surface (recent-a, recent-b, old —
        // the private memory is invisible and never counted).
        let page2 = tool
            .call(
                &mut ctx,
                json!({"galaxy": "codex", "offset": 3, "limit": 2}),
            )
            .await
            .unwrap();
        assert_eq!(
            page2["matched"], 3,
            "private memory must not count: {page2}"
        );
        assert_eq!(
            page2["returned"], 0,
            "offset past the match set is an honest empty page"
        );
        assert_eq!(page2["offset"], 3);

        // Malformed date bounds are a loud InvalidArgs.
        let bad = tool
            .call(
                &mut ctx,
                json!({"galaxy": "codex", "created_before": "yesterday"}),
            )
            .await;
        assert!(bad.is_err(), "non-RFC-3339 bound must be refused");
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

    fn index_tagged_memory(
        store: &Arc<MemoryStore>,
        search: &Arc<SearchEngine>,
        galaxy: Galaxy,
        content: &str,
        tags: &[&str],
    ) {
        let mut mem = Memory::new(galaxy, content.to_string());
        mem.metadata.tags = tags.iter().map(ToString::to_string).collect();
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

    fn aggregate_fixture() -> (tempfile::TempDir, Arc<MemoryStore>, Arc<SearchEngine>) {
        let (dir, store, search) = hybrid_fixture();
        // A Rust learning journey across sessions 2, 7, 12 …
        index_tagged_memory(
            &store,
            &search,
            Galaxy::Codex,
            "I started learning Rust.",
            &["user", "session_002"],
        );
        index_tagged_memory(
            &store,
            &search,
            Galaxy::Codex,
            "I finished my first Rust project, a CLI tool.",
            &["user", "session_007"],
        );
        index_tagged_memory(
            &store,
            &search,
            Galaxy::Codex,
            "I got a job as a systems engineer using Rust.",
            &["user", "session_012"],
        );
        // …and a Go journey that must not distort the Rust span (all its
        // turns also match the generic terms "started"/"job").
        index_tagged_memory(
            &store,
            &search,
            Galaxy::Codex,
            "I started learning Go.",
            &["user", "session_003"],
        );
        index_tagged_memory(
            &store,
            &search,
            Galaxy::Codex,
            "I got a job as a backend engineer using Go.",
            &["user", "session_015"],
        );
        (dir, store, search)
    }

    #[tokio::test]
    async fn aggregate_session_span_isolated_by_rarest_term() {
        let (_dir, store, search) = aggregate_fixture();
        let tool = MemoryAggregateTool::new(Some(search), store);
        let mut ctx = Context::default();
        let v = tool
            .call(
                &mut ctx,
                json!({
                    "query": "How long did it take from starting Rust to getting a job using it?",
                    "metric": "session_span",
                }),
            )
            .await
            .unwrap();
        assert_eq!(v["aggregate"]["value"], 10, "session_012 - session_002");
        assert_eq!(v["aggregate"]["unit"], "sessions");
        assert_eq!(v["aggregate"]["content"], "10 sessions");
    }

    #[tokio::test]
    async fn aggregate_session_count() {
        let (_dir, store, search) = aggregate_fixture();
        let tool = MemoryAggregateTool::new(Some(search), store);
        let mut ctx = Context::default();
        let v = tool
            .call(
                &mut ctx,
                json!({
                    "query": "How long did it take from starting Rust to getting a job using it?",
                    "metric": "session_count",
                }),
            )
            .await
            .unwrap();
        // The anchor cluster is the Rust turns; the middle turn ("finished
        // my first Rust project") matches only one query term and is held
        // back by the search engine's token-coverage floor, so the distinct
        // session count is 2 (start and end sessions) — span is unaffected
        // because min/max need only the endpoints.
        assert_eq!(v["aggregate"]["value"], 2);
    }

    #[tokio::test]
    async fn aggregate_count_needs_no_session_tags() {
        let (_dir, store, search) = aggregate_fixture();
        let tool = MemoryAggregateTool::new(Some(search), store);
        let mut ctx = Context::default();
        let v = tool
            .call(
                &mut ctx,
                json!({"query": "Rust project", "metric": "count"}),
            )
            .await
            .unwrap();
        // OR semantics: all three Rust turns match "rust".
        assert_eq!(v["aggregate"]["value"], 3);
    }

    #[tokio::test]
    async fn aggregate_rejects_unknown_metric() {
        let (_dir, store, search) = aggregate_fixture();
        let tool = MemoryAggregateTool::new(Some(search), store);
        let mut ctx = Context::default();
        let err = tool
            .call(&mut ctx, json!({"query": "x", "metric": "median"}))
            .await
            .unwrap_err();
        assert!(err.to_string().contains("unknown metric"));
    }
}
