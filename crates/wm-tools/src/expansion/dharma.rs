//! Dharma tools — rules, audit, profiles.

#![forbid(unsafe_code)]

use async_trait::async_trait;

use serde_json::{Value, json};
use std::sync::Arc;
use wm_core::{Context, EffectRow, Galaxy, Gana, Resource, Tool, ToolStats};
use wm_memory::MemoryStore;

pub struct DharmaRulesTool {
    stats: ToolStats,
    effects: EffectRow,
}

impl DharmaRulesTool {
    #[must_use]
    pub fn new() -> Self {
        Self {
            stats: ToolStats::default(),
            effects: EffectRow::pure(),
        }
    }
}

impl Default for DharmaRulesTool {
    fn default() -> Self {
        Self::new()
    }
}

#[async_trait]
#[async_trait]
impl Tool for DharmaRulesTool {
    fn name(&self) -> &str {
        "dharma.rules"
    }
    fn gana(&self) -> Gana {
        Gana::ExtendedNet
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "List active dharma rules and governance policies"
    }
    async fn call(&self, _ctx: &mut Context, _args: Value) -> wm_core::Result<Value> {
        Ok(json!({
            "status": "success",
            "rules": [
                { "name": "brain_wave_filter", "description": "Tools filtered by brain-wave state" },
                { "name": "coherence_gate", "description": "Writes blocked when citta coherence < 0.3" },
                { "name": "dharma_eval", "description": "Ethical governance verdict on every dispatch" },
                { "name": "rate_limit", "description": "Sliding window per-tool + global rate limiting" },
                { "name": "circuit_breaker", "description": "Fast-fail on repeated tool failures" },
            ],
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// `dharma.audit` — audit recent dispatches for governance violations.
pub struct DharmaAuditTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl DharmaAuditTool {
    pub fn new(store: Arc<MemoryStore>) -> Self {
        Self {
            store,
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![Resource::Galaxy("dharma".into())]),
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for DharmaAuditTool {
    fn name(&self) -> &str {
        "dharma.audit"
    }
    fn gana(&self) -> Gana {
        Gana::ExtendedNet
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Audit recent dispatches for governance violations"
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let limit = args
            .get("limit")
            .and_then(serde_json::Value::as_u64)
            .unwrap_or(50) as usize;
        let memories = self.store.scan(Galaxy::Dharma, limit)?;
        let audits: Vec<Value> = memories
            .iter()
            .map(|m| {
                json!({
                    "id": m.metadata.id,
                    "content": m.content,
                    "importance": m.metadata.importance,
                })
            })
            .collect();
        Ok(json!({
            "status": "success",
            "audited": audits.len(),
            "entries": audits,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}
