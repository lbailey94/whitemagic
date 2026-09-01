//! Karma tools — history, clear.

#![forbid(unsafe_code)]

use async_trait::async_trait;

use serde_json::{Value, json};
use std::sync::Arc;
use wm_core::{Context, EffectRow, Gana, Resource, Tool, ToolStats};
use wm_governance::KarmaLedger;

/// Append a chained anchor record to an external JSONL log.
///
/// Each record contains the anchor (root, entry_count, chain_head) plus a
/// `prev_hash` — the SHA-256 of the previous record — so the log is itself
/// a tamper-evident chain. When the log lives in a versioned repository
/// (git), the commit history provides out-of-band verifiability the
/// runtime cannot rewrite.
///
/// Returns the JSON record on success, `None` on failure (logged).
fn append_external_anchor(
    path: &str,
    checkpoint: &wm_governance::MerkleCheckpoint,
) -> Option<Value> {
    use sha2::{Digest, Sha256};

    // Previous record hash: the hash of the last line's record.
    let prev_hash = std::fs::read_to_string(path)
        .ok()
        .and_then(|contents| {
            contents.lines().last().map(|line| {
                const HEX: &[u8; 16] = b"0123456789abcdef";
                let digest = Sha256::digest(line.as_bytes());
                digest.iter().fold(String::with_capacity(64), |mut s, b| {
                    s.push(HEX[(b >> 4) as usize] as char);
                    s.push(HEX[(b & 0x0f) as usize] as char);
                    s
                })
            })
        })
        .unwrap_or_else(|| "genesis".to_string());

    let entry = json!({
        "root": checkpoint.root,
        "entry_count": checkpoint.entry_count,
        "chain_head": checkpoint.chain_head,
        "timestamp": checkpoint.timestamp,
        "prev_hash": prev_hash,
    });

    let mut line = serde_json::to_string(&entry).ok()?;
    line.push('\n');
    // Append-only: never truncate, use OpenOptions append mode.
    use std::io::Write;
    let result = std::fs::OpenOptions::new()
        .create(true)
        .append(true)
        .open(path)
        .and_then(|mut f| f.write_all(line.as_bytes()))
        .map_or_else(
            |e| {
                tracing::warn!(path = %path, error = %e, "external anchor append failed");
                false
            },
            |()| true,
        );
    result.then_some(entry)
}

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
        "Publish a Merkle anchor of the karma chain (actions: anchor, status). anchor: compute + persist the Merkle root, optionally append to an external anchor log (publish_path) for out-of-band verifiability; status: list published anchors"
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let action = args
            .get("action")
            .and_then(Value::as_str)
            .unwrap_or("anchor");
        match action {
            "anchor" => {
                let checkpoint = self.ledger.anchor()?;
                let mut result = json!({
                    "status": "success",
                    "action": "anchor",
                    "root": checkpoint.root,
                    "entry_count": checkpoint.entry_count,
                    "chain_head": checkpoint.chain_head,
                    "timestamp": checkpoint.timestamp,
                });
                // External anchor log: append a chained record to a
                // versioned file (e.g. in a git repo), so the anchor is
                // verifiable out-of-band and the runtime cannot rewrite it.
                if let Some(path) = args.get("publish_path").and_then(Value::as_str) {
                    if let Some(entry) = append_external_anchor(path, &checkpoint) {
                        result["external"] = json!({
                            "path": path,
                            "entry": entry,
                        });
                    } else {
                        result["external"] =
                            json!({"path": path, "error": "append failed (see logs)"});
                    }
                }
                Ok(result)
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

#[cfg(test)]
mod tests {
    use super::*;
    use sha2::{Digest, Sha256};

    fn checkpoint(root: &str, count: u64, head: &str, ts: u64) -> wm_governance::MerkleCheckpoint {
        wm_governance::MerkleCheckpoint {
            root: root.to_string(),
            entry_count: count,
            timestamp: ts,
            chain_head: head.to_string(),
        }
    }

    #[test]
    fn external_anchor_log_is_chained_and_append_only() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("anchors.jsonl");
        let path = path.to_str().unwrap();

        // First anchor: prev_hash is genesis.
        let e1 = append_external_anchor(path, &checkpoint("r1", 10, "h1", 100)).unwrap();
        assert_eq!(e1["prev_hash"], "genesis");

        // Second anchor: prev_hash is the SHA-256 of the first record.
        let e2 = append_external_anchor(path, &checkpoint("r2", 20, "h2", 200)).unwrap();
        let first_line = std::fs::read_to_string(path)
            .unwrap()
            .lines()
            .next()
            .unwrap()
            .to_string();
        const HEX: &[u8; 16] = b"0123456789abcdef";
        let digest = Sha256::digest(first_line.as_bytes());
        let expected = digest.iter().fold(String::with_capacity(64), |mut s, b| {
            s.push(HEX[(b >> 4) as usize] as char);
            s.push(HEX[(b & 0x0f) as usize] as char);
            s
        });
        assert_eq!(e2["prev_hash"], expected);

        // The file is append-only JSONL with exactly 2 records.
        let contents = std::fs::read_to_string(path).unwrap();
        assert_eq!(contents.lines().count(), 2);
    }

    #[test]
    fn external_anchor_handles_missing_file_as_genesis() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("missing.jsonl");
        let e =
            append_external_anchor(path.to_str().unwrap(), &checkpoint("r1", 1, "h1", 1)).unwrap();
        assert_eq!(e["prev_hash"], "genesis");
    }
}
