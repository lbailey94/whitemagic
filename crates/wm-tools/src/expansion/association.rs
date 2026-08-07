//! Association tools — associate_mine.

#![forbid(unsafe_code)]

use serde_json::{Value, json};
use std::sync::Arc;
use wm_core::{Context, EffectRow, Gana, Resource, Tool, ToolStats};
use wm_memory::{Association, AssociationStore, LinkType, MemoryStore};

use super::common::parse_galaxy;

pub struct MemoryAssociateMineTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl MemoryAssociateMineTool {
    pub fn new(store: Arc<MemoryStore>) -> Self {
        Self {
            store,
            stats: ToolStats::default(),
            effects: EffectRow {
                writes: vec![Resource::Galaxy("associations".into())],
                ..Default::default()
            },
        }
    }
}

impl Tool for MemoryAssociateMineTool {
    fn name(&self) -> &str {
        "memory.associate_mine"
    }
    fn gana(&self) -> Gana {
        Gana::Net
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Mine associations across galaxies using keyword overlap"
    }
    fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let galaxy_name_str = args
            .get("galaxy")
            .and_then(|v| v.as_str())
            .unwrap_or("codex");
        let galaxy = parse_galaxy(galaxy_name_str)?;
        let limit = args
            .get("limit")
            .and_then(serde_json::Value::as_u64)
            .unwrap_or(50) as usize;
        let memories = self.store.scan(galaxy, limit)?;
        let env = self.store.env();
        let assoc_store = AssociationStore::open(env)?;
        let mut proposed = 0u32;
        for i in 0..memories.len() {
            for j in (i + 1)..memories.len() {
                let a = &memories[i];
                let b = &memories[j];
                let a_words: std::collections::HashSet<&str> =
                    a.content.split_whitespace().collect();
                let b_words: std::collections::HashSet<&str> =
                    b.content.split_whitespace().collect();
                let intersection = a_words.intersection(&b_words).count();
                let union = a_words.union(&b_words).count();
                if union > 0 && intersection > 2 {
                    let strength = intersection as f32 / union as f32;
                    if strength > 0.3 {
                        let assoc = Association::new(
                            a.metadata.id,
                            b.metadata.id,
                            LinkType::Related,
                            strength,
                        );
                        let _ = assoc_store.put(env, &assoc);
                        proposed += 1;
                    }
                }
            }
        }
        Ok(json!({
            "status": "success",
            "galaxy": galaxy_name_str,
            "scanned": memories.len(),
            "proposed_associations": proposed,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}
