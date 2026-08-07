//! System tools — health, config, flush.

#![forbid(unsafe_code)]

use serde_json::{Value, json};
use std::sync::Arc;
use wm_core::{Context, EffectRow, Galaxy, Gana, Resource, Tool, ToolStats};
use wm_memory::MemoryStore;

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
    fn call(&self, _ctx: &mut Context, _args: Value) -> wm_core::Result<Value> {
        let mut total = 0usize;
        let mut galaxies_with_data = 0usize;
        for galaxy in Galaxy::all() {
            let count = self.store.count(galaxy).unwrap_or(0);
            if count > 0 {
                total += count;
                galaxies_with_data += 1;
            }
        }
        Ok(json!({
            "status": "success",
            "healthy": true,
            "store_path": self.store.path().display().to_string(),
            "total_memories": total,
            "galaxies_with_data": galaxies_with_data,
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
    fn call(&self, _ctx: &mut Context, _args: Value) -> wm_core::Result<Value> {
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
    stats: ToolStats,
    effects: EffectRow,
}

impl SystemFlushTool {
    pub fn new(store: Arc<MemoryStore>) -> Self {
        Self {
            store,
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
    fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
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
