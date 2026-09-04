//! System tools — health, config, flush.

#![forbid(unsafe_code)]

use async_trait::async_trait;

use serde_json::{Value, json};
use std::sync::Arc;
use wm_core::{Context, EffectRow, Galaxy, Gana, Tool, ToolStats};
use wm_memory::{MemoryStore, SearchEngine};

pub struct SystemHealthTool {
    store: Arc<MemoryStore>,
    search: Option<Arc<SearchEngine>>,
    stats: ToolStats,
    effects: EffectRow,
}

impl SystemHealthTool {
    pub fn new(store: Arc<MemoryStore>) -> Self {
        Self {
            store,
            search: None,
            stats: ToolStats::default(),
            effects: EffectRow::pure(),
        }
    }

    /// Create with a search engine for index health reporting.
    #[must_use]
    pub fn with_search(store: Arc<MemoryStore>, search: Arc<SearchEngine>) -> Self {
        Self {
            store,
            search: Some(search),
            stats: ToolStats::default(),
            effects: EffectRow::pure(),
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for SystemHealthTool {
    fn name(&self) -> &str {
        "system.health"
    }
    fn gana(&self) -> Gana {
        Gana::Horn
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Overall system health check — galaxy counts, store path, index health"
    }
    async fn call(&self, _ctx: &mut Context, _args: Value) -> wm_core::Result<Value> {
        let mut total = 0usize;
        let mut galaxies_with_data = 0usize;
        let mut failed_galaxies: Vec<String> = Vec::new();
        for galaxy in Galaxy::all() {
            match self.store.count(galaxy) {
                Ok(count) => {
                    if count > 0 {
                        total += count;
                        galaxies_with_data += 1;
                    }
                }
                // Storage errors must not be silently converted to zero
                // counts — the old behavior reported healthy: true with no
                // signal that galaxy reads were failing.
                Err(e) => failed_galaxies.push(format!("{}: {e}", galaxy.db_name())),
            }
        }

        // Index health: report degraded state and consistency drift.
        // When no search engine is configured, report `unavailable` so
        // callers know search is not functional — not silently healthy.
        let (index_health, index_consistency) = match &self.search {
            Some(search) => {
                let health = search.health().snapshot();
                let consistency = wm_memory::check_consistency(&self.store, search);
                let consistency_json = serde_json::json!({
                    "has_drift": consistency.has_drift,
                    "total_lmdb": consistency.total_lmdb,
                    "total_tantivy": consistency.total_tantivy,
                    "drifted_galaxies": consistency
                        .galaxies
                        .iter()
                        .filter(|g| g.drift)
                        .map(|g| serde_json::json!({
                            "galaxy": g.galaxy,
                            "lmdb_count": g.lmdb_count,
                            "tantivy_count": g.tantivy_count,
                        }))
                        .collect::<Vec<_>>(),
                });
                (health, consistency_json)
            }
            None => (
                serde_json::json!({"status": "unavailable", "degraded": true}),
                serde_json::json!({"status": "unavailable"}),
            ),
        };

        let index_degraded = index_health
            .get("degraded")
            .and_then(serde_json::Value::as_bool)
            .unwrap_or(true);
        let index_drift = index_consistency
            .get("has_drift")
            .and_then(serde_json::Value::as_bool)
            .unwrap_or(false);

        Ok(json!({
            "status": "success",
            "healthy": failed_galaxies.is_empty() && !index_degraded && !index_drift,
            "store_path": self.store.path().display().to_string(),
            "total_memories": total,
            "galaxies_with_data": galaxies_with_data,
            "failed_galaxies": failed_galaxies,
            "index_health": index_health,
            "index_consistency": index_consistency,
            "version": env!("CARGO_PKG_VERSION"),
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// `system.config` — system configuration info.
pub struct SystemConfigTool {
    stats: ToolStats,
    effects: EffectRow,
}

impl SystemConfigTool {
    #[must_use]
    pub fn new() -> Self {
        Self {
            stats: ToolStats::default(),
            effects: EffectRow::pure(),
        }
    }
}

impl Default for SystemConfigTool {
    fn default() -> Self {
        Self::new()
    }
}

#[async_trait]
#[async_trait]
impl Tool for SystemConfigTool {
    fn name(&self) -> &str {
        "system.config"
    }
    fn gana(&self) -> Gana {
        Gana::Horn
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "System configuration info — brain-wave states, galaxies, ganas"
    }
    async fn call(&self, _ctx: &mut Context, _args: Value) -> wm_core::Result<Value> {
        Ok(json!({
            "status": "success",
            "version": env!("CARGO_PKG_VERSION"),
            "brain_waves": ["Gamma", "Beta", "Alpha", "Theta", "Delta"],
            "galaxies": Galaxy::COUNT,
            "ganas": Gana::COUNT,
            "coherence_threshold": 0.3,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// `system.flush` — flush/cleanup old memories (gentle GC).
pub struct SystemFlushTool {
    store: Arc<MemoryStore>,
    search: Option<Arc<SearchEngine>>,
    stats: ToolStats,
    effects: EffectRow,
}

impl SystemFlushTool {
    pub fn new(store: Arc<MemoryStore>, search: Option<Arc<SearchEngine>>) -> Self {
        Self {
            store,
            search,
            stats: ToolStats::default(),
            effects: EffectRow {
                // Flush deletes low-importance memories across all galaxies.
                writes: super::common::memory_galaxy_writes(),
                reads: super::common::memory_galaxy_reads(),
                destructive: true,
                cost: wm_core::CostEstimate {
                    expensive: true,
                    ..Default::default()
                },
                ..Default::default()
            },
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for SystemFlushTool {
    fn name(&self) -> &str {
        "system.flush"
    }
    fn gana(&self) -> Gana {
        Gana::Root
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Flush low-importance memories (gentle GC) — scoped: pass `galaxy` for one galaxy or `store_wide: true` to acknowledge a store-wide flush. Preview-only unless `dry_run: false`."
    }
    fn input_schema(&self) -> Value {
        super::common::schema(
            &json!({
                "threshold": {"type": "number", "description": "Flush memories below this importance (default 0.05)"},
                "galaxy": {"type": "string", "description": "Scope the flush to one galaxy (e.g. 'codex')"},
                "store_wide": {"type": "boolean", "description": "Acknowledge a store-wide flush across all galaxies"},
                "dry_run": {"type": "boolean", "description": "Preview only (default true) — count without deleting"},
            }),
            &[],
        )
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let threshold = args
            .get("threshold")
            .and_then(serde_json::Value::as_f64)
            .unwrap_or(0.05) as f32;
        // Scope is mandatory and value-checked (the firebreak seam only
        // checks presence): exactly one of a non-empty `galaxy` or an
        // explicit `store_wide: true`.
        let galaxy_arg = args.get("galaxy").and_then(serde_json::Value::as_str);
        let store_wide = args
            .get("store_wide")
            .and_then(serde_json::Value::as_bool)
            .unwrap_or(false);
        let targets: Vec<Galaxy> = match (galaxy_arg, store_wide) {
            (Some(name), false) if !name.is_empty() => {
                vec![super::common::parse_galaxy(name)?]
            }
            (None, true) => Galaxy::all().to_vec(),
            (Some(_), true) => {
                return Err(wm_core::CoreError::InvalidArgs(
                    "system.flush takes exactly one scope: `galaxy` or `store_wide: true`, not both"
                        .into(),
                ));
            }
            _ => {
                return Err(wm_core::CoreError::InvalidArgs(
                    "system.flush requires a scope: pass `galaxy` (e.g. {\"galaxy\": \"codex\"}) or acknowledge the blast radius with `store_wide: true`"
                        .into(),
                ));
            }
        };
        let dry_run = args
            .get("dry_run")
            .and_then(serde_json::Value::as_bool)
            .unwrap_or(true);
        let mut per_galaxy = Vec::new();
        let mut preview: Vec<Value> = Vec::new();
        let mut flushed = 0u32;
        for galaxy in &targets {
            let memories = self.store.scan(*galaxy, 10_000)?;
            let mut count = 0u32;
            for mem in &memories {
                if mem.metadata.importance < threshold
                    && !mem.metadata.tags.contains(&"system".to_string())
                {
                    count += 1;
                    if preview.len() < 50 {
                        preview.push(json!({
                            "id": mem.metadata.id,
                            "galaxy": galaxy.db_name(),
                            "importance": mem.metadata.importance,
                        }));
                    }
                    if !dry_run {
                        self.store.delete(*galaxy, mem.metadata.id)?;
                        super::common::deindex(
                            self.search.as_deref(),
                            &mem.metadata.id.to_string(),
                        );
                        flushed += 1;
                    }
                }
            }
            per_galaxy.push(json!({"galaxy": galaxy.db_name(), "candidates": count}));
        }
        Ok(json!({
            "status": "success",
            "threshold": threshold,
            "dry_run": dry_run,
            "scope": galaxy_arg.unwrap_or("store_wide"),
            "per_galaxy": per_galaxy,
            "preview": preview,
            "flushed": flushed,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use wm_memory::MemoryStore;

    #[tokio::test]
    async fn system_health_reports_failures_honestly() {
        let dir = tempfile::tempdir().unwrap();
        let store = Arc::new(MemoryStore::open_default(dir.path()).unwrap());
        // No search engine → index_health reports unavailable, degraded=true.
        let tool = SystemHealthTool::new(store);

        let v = tool.call(&mut Context::default(), json!({})).await.unwrap();
        assert_eq!(v["status"], "success");
        // healthy is false because index is unavailable (degraded).
        assert_eq!(v["healthy"], false);
        assert_eq!(v["index_health"]["status"], "unavailable");
        assert_eq!(v["index_health"]["degraded"], true);
        assert!(v.get("failed_galaxies").is_some());
        assert_eq!(v["failed_galaxies"].as_array().unwrap().len(), 0);
    }

    #[tokio::test]
    async fn system_health_with_search_reports_index_consistency() {
        let dir = tempfile::tempdir().unwrap();
        let store = Arc::new(MemoryStore::open_default(dir.path()).unwrap());
        let tantivy_path = dir.path().join("tantivy");
        std::fs::create_dir_all(&tantivy_path).unwrap();
        let search = Arc::new(SearchEngine::open(&tantivy_path).unwrap());
        let tool = SystemHealthTool::with_search(store.clone(), search.clone());

        let v = tool.call(&mut Context::default(), json!({})).await.unwrap();
        assert_eq!(v["status"], "success");
        // No memories, no drift → healthy.
        assert_eq!(v["healthy"], true);
        assert_eq!(v["index_health"]["degraded"], false);
        assert_eq!(v["index_health"]["failures"], 0);
        assert_eq!(v["index_consistency"]["has_drift"], false);
        assert_eq!(v["index_consistency"]["total_lmdb"], 0);
        assert_eq!(v["index_consistency"]["total_tantivy"], 0);
    }

    #[tokio::test]
    async fn system_health_detects_index_drift() {
        let dir = tempfile::tempdir().unwrap();
        let store = Arc::new(MemoryStore::open_default(dir.path()).unwrap());
        let tantivy_path = dir.path().join("tantivy");
        std::fs::create_dir_all(&tantivy_path).unwrap();
        let search = Arc::new(SearchEngine::open(&tantivy_path).unwrap());

        // Write a memory to LMDB without indexing it in Tantivy → drift.
        let mem = wm_memory::Memory::new(Galaxy::Codex, "unindexed content".into());
        store.put(Galaxy::Codex, &mem).unwrap();

        let tool = SystemHealthTool::with_search(store.clone(), search.clone());
        let v = tool.call(&mut Context::default(), json!({})).await.unwrap();
        assert_eq!(v["status"], "success");
        assert_eq!(v["healthy"], false);
        assert_eq!(v["index_consistency"]["has_drift"], true);
        assert_eq!(v["index_consistency"]["total_lmdb"], 1);
        assert_eq!(v["index_consistency"]["total_tantivy"], 0);
    }

    // ── system.flush scope + dry_run hardening ──────────────────────────

    fn flush_fixture() -> (tempfile::TempDir, Arc<MemoryStore>) {
        let dir = tempfile::tempdir().unwrap();
        let store = Arc::new(MemoryStore::open_default(dir.path()).unwrap());
        // Low-importance flushable in Codex + Sessions; high-importance kept.
        for (galaxy, importance) in [
            (Galaxy::Codex, 0.01),
            (Galaxy::Sessions, 0.02),
            (Galaxy::Codex, 0.9),
        ] {
            let mut mem = wm_memory::Memory::new(galaxy, "flush me".into());
            mem.metadata.importance = importance;
            store.put(galaxy, &mem).unwrap();
        }
        (dir, store)
    }

    #[tokio::test]
    async fn flush_requires_a_scope() {
        let (_dir, store) = flush_fixture();
        let tool = SystemFlushTool::new(store, None);
        let err = tool
            .call(&mut Context::default(), json!({"threshold": 0.05}))
            .await
            .unwrap_err();
        assert!(matches!(err, wm_core::CoreError::InvalidArgs(_)));
        // store_wide:false is not an acknowledgement either.
        let err = tool
            .call(
                &mut Context::default(),
                json!({"threshold": 0.05, "store_wide": false}),
            )
            .await
            .unwrap_err();
        assert!(matches!(err, wm_core::CoreError::InvalidArgs(_)));
    }

    #[tokio::test]
    async fn flush_dry_run_previews_without_deleting() {
        let (_dir, store) = flush_fixture();
        let tool = SystemFlushTool::new(store.clone(), None);
        // dry_run defaults true: 1 Codex candidate reported, nothing deleted.
        let v = tool
            .call(&mut Context::default(), json!({"galaxy": "codex"}))
            .await
            .unwrap();
        assert_eq!(v["status"], "success");
        assert_eq!(v["dry_run"], true);
        assert_eq!(v["flushed"], 0);
        assert_eq!(v["scope"], "codex");
        assert_eq!(v["per_galaxy"][0]["candidates"], 1);
        assert_eq!(store.count(Galaxy::Codex).unwrap(), 2);
        assert_eq!(store.count(Galaxy::Sessions).unwrap(), 1);
    }

    #[tokio::test]
    async fn flush_galaxy_scope_isolates() {
        let (_dir, store) = flush_fixture();
        let tool = SystemFlushTool::new(store.clone(), None);
        let v = tool
            .call(
                &mut Context::default(),
                json!({"galaxy": "codex", "dry_run": false}),
            )
            .await
            .unwrap();
        assert_eq!(v["flushed"], 1);
        // Sessions untouched by a Codex-scoped flush.
        assert_eq!(store.count(Galaxy::Codex).unwrap(), 1);
        assert_eq!(store.count(Galaxy::Sessions).unwrap(), 1);
    }

    #[tokio::test]
    async fn flush_store_wide_acknowledged() {
        let (_dir, store) = flush_fixture();
        let tool = SystemFlushTool::new(store.clone(), None);
        let v = tool
            .call(
                &mut Context::default(),
                json!({"store_wide": true, "dry_run": false}),
            )
            .await
            .unwrap();
        assert_eq!(v["flushed"], 2);
        assert_eq!(store.count(Galaxy::Codex).unwrap(), 1);
        assert_eq!(store.count(Galaxy::Sessions).unwrap(), 0);
    }
}
