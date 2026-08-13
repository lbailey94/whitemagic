//! System tools — health, config, flush.

#![forbid(unsafe_code)]

use async_trait::async_trait;

use serde_json::{Value, json};
use std::sync::Arc;
use wm_core::{Context, EffectRow, Galaxy, Gana, Resource, Tool, ToolStats};
use wm_memory::{MemoryStore, SearchEngine};

pub struct SystemHealthTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl SystemHealthTool {
    pub fn new(store: Arc<MemoryStore>) -> Self {
        Self {
            store,
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
        "Overall system health check — galaxy counts, store path"
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
        Ok(json!({
            "status": "success",
            "healthy": failed_galaxies.is_empty(),
            "store_path": self.store.path().display().to_string(),
            "total_memories": total,
            "galaxies_with_data": galaxies_with_data,
            "failed_galaxies": failed_galaxies,
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
                writes: vec![Resource::Galaxy("universal".into())],
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
        "Flush low-importance memories across all galaxies (gentle GC)"
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let threshold = args
            .get("threshold")
            .and_then(serde_json::Value::as_f64)
            .unwrap_or(0.05) as f32;
        let mut flushed = 0u32;
        for galaxy in Galaxy::all() {
            let memories = self.store.scan(galaxy, 10_000)?;
            for mem in &memories {
                if mem.metadata.importance < threshold
                    && !mem.metadata.tags.contains(&"system".to_string())
                {
                    self.store.delete(galaxy, mem.metadata.id)?;
                    super::common::deindex(self.search.as_deref(), &mem.metadata.id.to_string());
                    flushed += 1;
                }
            }
        }
        Ok(json!({
            "status": "success",
            "threshold": threshold,
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
        let tool = SystemHealthTool::new(store);

        let v = tool.call(&mut Context::default(), json!({})).await.unwrap();
        assert_eq!(v["status"], "success");
        assert_eq!(v["healthy"], true);
        assert!(v.get("failed_galaxies").is_some());
        assert_eq!(v["failed_galaxies"].as_array().unwrap().len(), 0);
    }
}
