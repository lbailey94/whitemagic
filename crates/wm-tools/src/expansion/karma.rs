//! Karma tools — history, clear.

#![forbid(unsafe_code)]

use async_trait::async_trait;

use serde_json::{Value, json};
use std::sync::Arc;
use wm_core::{Context, EffectRow, Gana, Resource, Tool, ToolStats};
use wm_governance::KarmaLedger;

pub struct KarmaHistoryTool {
    ledger: Arc<KarmaLedger>,
    stats: ToolStats,
    effects: EffectRow,
}

impl KarmaHistoryTool {
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
impl Tool for KarmaHistoryTool {
    fn name(&self) -> &str {
        "karma.history"
    }
    fn gana(&self) -> Gana {
        Gana::Willow
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Recent karma entries from the Karma galaxy"
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let limit = args
            .get("limit")
            .and_then(serde_json::Value::as_u64)
            .unwrap_or(20) as usize;
        let entries = self.ledger.recent(limit)?;
        let history: Vec<Value> = entries
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
                    "timestamp": e.timestamp,
                })
            })
            .collect();
        Ok(json!({
            "status": "success",
            "count": history.len(),
            "history": history,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// `karma.clear` — clear old karma entries (keep recent).
pub struct KarmaClearTool {
    ledger: Arc<KarmaLedger>,
    stats: ToolStats,
    effects: EffectRow,
}

impl KarmaClearTool {
    pub fn new(ledger: Arc<KarmaLedger>) -> Self {
        Self {
            ledger,
            stats: ToolStats::default(),
            effects: EffectRow {
                writes: vec![Resource::Galaxy("karma".into())],
                destructive: true,
                ..Default::default()
            },
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for KarmaClearTool {
    fn name(&self) -> &str {
        "karma.clear"
    }
    fn gana(&self) -> Gana {
        Gana::Willow
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Clear old karma entries, keeping only the most recent N"
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let keep = args
            .get("keep")
            .and_then(serde_json::Value::as_u64)
            .unwrap_or(100) as usize;
        let cleared = self.ledger.clear_old(keep)?;
        Ok(json!({
            "status": "success",
            "kept": keep,
            "cleared": cleared,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}
