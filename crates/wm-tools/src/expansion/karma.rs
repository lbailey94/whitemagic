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

/// `karma.verify_chain` — verify the SHA-256 hash-chain integrity.
pub struct KarmaVerifyChainTool {
    ledger: Arc<KarmaLedger>,
    stats: ToolStats,
    effects: EffectRow,
}

impl KarmaVerifyChainTool {
    pub fn new(ledger: Arc<KarmaLedger>) -> Self {
        Self {
            ledger,
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![Resource::Galaxy("karma".into())]),
        }
    }
}

#[async_trait]
impl Tool for KarmaVerifyChainTool {
    fn name(&self) -> &str {
        "karma.verify_chain"
    }
    fn gana(&self) -> Gana {
        Gana::Willow
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Verify karma chain integrity — checks every link hash and the chain head (tamper detection)"
    }
    async fn call(&self, _ctx: &mut Context, _args: Value) -> wm_core::Result<Value> {
        let result = self.ledger.verify_integrity()?;
        Ok(json!({
            "status": if result.valid { "success" } else { "error" },
            "valid": result.valid,
            "entries_verified": result.entries_verified,
            "broken_at": result.broken_at,
            "violation": result.violation,
            "chain_head": result.chain_head,
            "last_merkle_root": result.last_merkle_root,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// `karma.anchor` — publish a Merkle checkpoint (anchor) of the whole chain.
pub struct KarmaAnchorTool {
    ledger: Arc<KarmaLedger>,
    stats: ToolStats,
    effects: EffectRow,
}

impl KarmaAnchorTool {
    pub fn new(ledger: Arc<KarmaLedger>) -> Self {
        Self {
            ledger,
            stats: ToolStats::default(),
            effects: EffectRow {
                writes: vec![Resource::Galaxy("karma".into())],
                ..Default::default()
            },
        }
    }
}

#[async_trait]
impl Tool for KarmaAnchorTool {
    fn name(&self) -> &str {
        "karma.anchor"
    }
    fn gana(&self) -> Gana {
        Gana::Willow
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Publish a Merkle anchor of the karma chain (actions: anchor, status). anchor: compute + persist the Merkle root; status: list published anchors"
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let action = args
            .get("action")
            .and_then(Value::as_str)
            .unwrap_or("anchor");
        match action {
            "anchor" => {
                let checkpoint = self.ledger.anchor()?;
                Ok(json!({
                    "status": "success",
                    "action": "anchor",
                    "root": checkpoint.root,
                    "entry_count": checkpoint.entry_count,
                    "chain_head": checkpoint.chain_head,
                    "timestamp": checkpoint.timestamp,
                }))
            }
            "status" => {
                let anchors: Vec<Value> = self
                    .ledger
                    .anchors()?
                    .into_iter()
                    .map(|a| {
                        json!({
                            "root": a.root,
                            "entry_count": a.entry_count,
                            "chain_head": a.chain_head,
                            "timestamp": a.timestamp,
                        })
                    })
                    .collect();
                Ok(json!({
                    "status": "success",
                    "action": "status",
                    "anchors_count": anchors.len(),
                    "anchors": anchors,
                }))
            }
            other => Err(wm_core::CoreError::InvalidArgs(format!(
                "unknown karma.anchor action: {other}"
            ))),
        }
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}
