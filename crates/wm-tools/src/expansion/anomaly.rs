//! Anomaly & state tools — anomaly.detect, state.snapshot, state.revert.
//!
//! Gana::Heart — "Anomaly detection, state management"
//!
//! Anomaly detection scans for outliers in memory importance, access patterns,
//! and content length. State management captures and restores system state
//! snapshots stored in the Journals galaxy.

#![forbid(unsafe_code)]

use async_trait::async_trait;

use serde_json::{Value, json};
use std::collections::HashMap;
use std::sync::Arc;
use wm_core::{Context, EffectRow, Galaxy, Gana, Resource, Tool, ToolStats};
use wm_memory::{Memory, MemoryStore};

use super::common::galaxy_name;

// ── anomaly.detect ───────────────────────────────────────────────────

/// Detect anomalies in memory patterns across galaxies.
///
/// Identifies outliers in:
/// - Importance scores (unusually high or low)
/// - Access counts (rarely or excessively accessed)
/// - Content length (abnormally long or short memories)
/// - Tag frequency (rare tags that may indicate noise)
pub struct AnomalyDetectTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl AnomalyDetectTool {
    pub fn new(store: Arc<MemoryStore>) -> Self {
        Self {
            store,
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![Resource::Galaxy("universal".into())]),
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for AnomalyDetectTool {
    fn name(&self) -> &str {
        "anomaly.detect"
    }
    fn gana(&self) -> Gana {
        Gana::Heart
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Detect anomalies in memory importance, access patterns, and content"
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let galaxy_str = args.get("galaxy").and_then(|v| v.as_str());
        let sensitivity = args
            .get("sensitivity")
            .and_then(|v| v.as_str())
            .unwrap_or("medium");
        let threshold = match sensitivity {
            "low" => 2.5,  // fewer anomalies
            "high" => 1.5, // more anomalies
            _ => 2.0,      // medium (z-score threshold)
        };

        let galaxies: Vec<Galaxy> = match galaxy_str {
            Some(g) => vec![super::common::parse_galaxy(g)?],
            None => Galaxy::memory_galaxies().to_vec(),
        };

        // Collect all memories with metrics
        let mut all_mems: Vec<(Galaxy, Memory)> = Vec::new();
        for galaxy in &galaxies {
            let mems = self.store.scan(*galaxy, 1000)?;
            all_mems.extend(mems.into_iter().map(|m| (*galaxy, m)));
        }

        if all_mems.is_empty() {
            return Ok(json!({
                "status": "success",
                "total_memories": 0,
                "anomalies": [],
            }));
        }

        // Compute statistics
        let n = all_mems.len() as f64;
        let mean_importance: f64 = all_mems
            .iter()
            .map(|(_, m)| f64::from(m.metadata.importance))
            .sum::<f64>()
            / n;
        let std_importance: f64 = {
            let variance: f64 = all_mems
                .iter()
                .map(|(_, m)| (f64::from(m.metadata.importance) - mean_importance).powi(2))
                .sum::<f64>()
                / n;
            variance.sqrt()
        };

        let mean_access: f64 = all_mems
            .iter()
            .map(|(_, m)| m.metadata.access_count as f64)
            .sum::<f64>()
            / n;
        let std_access: f64 = {
            let variance: f64 = all_mems
                .iter()
                .map(|(_, m)| (m.metadata.access_count as f64 - mean_access).powi(2))
                .sum::<f64>()
                / n;
            variance.sqrt()
        };

        let mean_length: f64 = all_mems
            .iter()
            .map(|(_, m)| m.content.len() as f64)
            .sum::<f64>()
            / n;
        let std_length: f64 = {
            let variance: f64 = all_mems
                .iter()
                .map(|(_, m)| (m.content.len() as f64 - mean_length).powi(2))
                .sum::<f64>()
                / n;
            variance.sqrt()
        };

        // Detect anomalies using z-score
        let mut anomalies: Vec<Value> = Vec::new();
        for (galaxy, mem) in &all_mems {
            // Importance anomaly
            if std_importance > 0.0 {
                let z =
                    ((f64::from(mem.metadata.importance) - mean_importance) / std_importance).abs();
                if z > threshold {
                    anomalies.push(json!({
                        "type": "importance_outlier",
                        "galaxy": galaxy_name(*galaxy),
                        "memory_id": mem.metadata.id,
                        "z_score": (z * 100.0).round() / 100.0,
                        "value": mem.metadata.importance,
                        "mean": (mean_importance * 100.0).round() / 100.0,
                        "direction": if f64::from(mem.metadata.importance) > mean_importance { "high" } else { "low" },
                    }));
                }
            }

            // Access count anomaly
            if std_access > 0.0 {
                let z = ((mem.metadata.access_count as f64 - mean_access) / std_access).abs();
                if z > threshold {
                    anomalies.push(json!({
                        "type": "access_outlier",
                        "galaxy": galaxy_name(*galaxy),
                        "memory_id": mem.metadata.id,
                        "z_score": (z * 100.0).round() / 100.0,
                        "value": mem.metadata.access_count,
                        "mean": (mean_access * 100.0).round() / 100.0,
                        "direction": if mem.metadata.access_count as f64 > mean_access { "high" } else { "low" },
                    }));
                }
            }

            // Content length anomaly
            if std_length > 0.0 {
                let z = ((mem.content.len() as f64 - mean_length) / std_length).abs();
                if z > threshold {
                    anomalies.push(json!({
                        "type": "length_outlier",
                        "galaxy": galaxy_name(*galaxy),
                        "memory_id": mem.metadata.id,
                        "z_score": (z * 100.0).round() / 100.0,
                        "value": mem.content.len(),
                        "mean": (mean_length * 100.0).round() / 100.0,
                        "direction": if mem.content.len() as f64 > mean_length { "long" } else { "short" },
                    }));
                }
            }
        }

        // Tag frequency anomalies (rare tags)
        let mut tag_freq: HashMap<String, u32> = HashMap::new();
        for (_, mem) in &all_mems {
            for tag in &mem.metadata.tags {
                *tag_freq.entry(tag.clone()).or_default() += 1;
            }
        }
        let mean_tag_freq: f64 =
            tag_freq.values().map(|&c| f64::from(c)).sum::<f64>() / tag_freq.len().max(1) as f64;
        for (tag, count) in &tag_freq {
            if (f64::from(*count)) < mean_tag_freq * 0.3 && *count <= 1 {
                anomalies.push(json!({
                    "type": "rare_tag",
                    "tag": tag,
                    "frequency": count,
                    "mean_frequency": (mean_tag_freq * 100.0).round() / 100.0,
                }));
            }
        }

        Ok(json!({
            "status": "success",
            "total_memories": all_mems.len(),
            "sensitivity": sensitivity,
            "stats": {
                "mean_importance": (mean_importance * 100.0).round() / 100.0,
                "std_importance": (std_importance * 100.0).round() / 100.0,
                "mean_access": (mean_access * 100.0).round() / 100.0,
                "std_access": (std_access * 100.0).round() / 100.0,
                "mean_length": (mean_length * 100.0).round() / 100.0,
                "std_length": (std_length * 100.0).round() / 100.0,
            },
            "anomaly_count": anomalies.len(),
            "anomalies": anomalies,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── state.snapshot ───────────────────────────────────────────────────

/// Capture a snapshot of the current system state.
///
/// Collects galaxy counts, tag distributions, and importance statistics
/// into a JSON snapshot stored in the Journals galaxy.
pub struct StateSnapshotTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl StateSnapshotTool {
    pub fn new(store: Arc<MemoryStore>) -> Self {
        Self {
            store,
            stats: ToolStats::default(),
            effects: EffectRow {
                writes: vec![Resource::Galaxy("journals".into())],
                reads: vec![Resource::Galaxy("universal".into())],
                ..Default::default()
            },
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for StateSnapshotTool {
    fn name(&self) -> &str {
        "state.snapshot"
    }
    fn gana(&self) -> Gana {
        Gana::Heart
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Capture a snapshot of current system state into Journals galaxy"
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let label = args
            .get("label")
            .and_then(|v| v.as_str())
            .unwrap_or("system-state");

        let mut galaxy_stats: Vec<Value> = Vec::new();
        let mut total_memories = 0u64;

        for galaxy in Galaxy::memory_galaxies() {
            let mems = self.store.scan(galaxy, 10000)?;
            let count = mems.len();
            total_memories += count as u64;
            if count > 0 {
                let avg_importance: f32 =
                    mems.iter().map(|m| m.metadata.importance).sum::<f32>() / count as f32;
                let total_access: u64 = mems.iter().map(|m| m.metadata.access_count).sum();
                let mut tags: HashMap<String, u32> = HashMap::new();
                for mem in &mems {
                    for tag in &mem.metadata.tags {
                        *tags.entry(tag.clone()).or_default() += 1;
                    }
                }
                galaxy_stats.push(json!({
                    "galaxy": galaxy_name(galaxy),
                    "count": count,
                    "avg_importance": (avg_importance * 100.0).round() / 100.0,
                    "total_access": total_access,
                    "unique_tags": tags.len(),
                }));
            }
        }

        let snapshot = json!({
            "label": label,
            "captured_at": chrono::Utc::now().to_rfc3339(),
            "total_memories": total_memories,
            "galaxies_with_data": galaxy_stats.len(),
            "galaxy_stats": galaxy_stats,
        });

        let mut mem = Memory::new(Galaxy::Journals, snapshot.to_string());
        mem.metadata.tags = vec!["state-snapshot".into(), label.into()];
        mem.metadata.importance = 0.8;
        let id = mem.metadata.id;
        self.store.put(Galaxy::Journals, &mem)?;

        Ok(json!({
            "status": "success",
            "snapshot_id": id.to_string(),
            "label": label,
            "total_memories": total_memories,
            "galaxies_with_data": galaxy_stats.len(),
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── state.revert ─────────────────────────────────────────────────────

/// Revert to a previous state snapshot.
///
/// Reads a state snapshot from the Journals galaxy and returns the
/// system state at that point. This is a read-only operation — it does
/// not delete memories created after the snapshot. Instead, it provides
/// a comparison view for understanding system evolution.
pub struct StateRevertTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl StateRevertTool {
    pub fn new(store: Arc<MemoryStore>) -> Self {
        Self {
            store,
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![Resource::Galaxy("journals".into())]),
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for StateRevertTool {
    fn name(&self) -> &str {
        "state.revert"
    }
    fn gana(&self) -> Gana {
        Gana::Heart
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Read a previous state snapshot for system comparison"
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let label = args.get("label").and_then(|v| v.as_str());
        let snapshot_id = args.get("snapshot_id").and_then(|v| v.as_str());

        if label.is_none() && snapshot_id.is_none() {
            return Err(wm_core::CoreError::InvalidArgs(
                "Either label (string) or snapshot_id (string) required".into(),
            ));
        }

        // Fast path: direct lookup by UUID
        let snapshot: Option<wm_memory::Memory> = if let Some(sid) = snapshot_id {
            let uuid = uuid::Uuid::parse_str(sid).map_err(|e| {
                wm_core::CoreError::InvalidArgs(format!("Invalid snapshot_id UUID: {e}"))
            })?;
            self.store.get(Galaxy::Journals, uuid)?
        } else {
            // Fallback: scan by label
            let mems = self.store.scan(Galaxy::Journals, 500)?;
            mems.into_iter().find(|m| {
                m.metadata.tags.iter().any(|t| t == "state-snapshot")
                    && label.is_some_and(|l| m.metadata.tags.contains(&l.to_string()))
            })
        };

        match snapshot {
            Some(m) => {
                let state: Value = serde_json::from_str(&m.content).unwrap_or(Value::Null);

                // Compare with current state
                let mut current_total = 0u64;
                for galaxy in Galaxy::memory_galaxies() {
                    let count = self.store.scan(galaxy, 10000)?.len();
                    current_total += count as u64;
                }

                let snapshot_total = state
                    .get("total_memories")
                    .and_then(Value::as_u64)
                    .unwrap_or(0);

                Ok(json!({
                    "status": "success",
                    "snapshot_id": m.metadata.id,
                    "snapshot": state,
                    "current_total_memories": current_total,
                    "snapshot_total_memories": snapshot_total,
                    "delta": i64::try_from(current_total).unwrap_or(i64::MAX) - i64::try_from(snapshot_total).unwrap_or(i64::MAX),
                    "captured_at": m.metadata.created_at.to_rfc3339(),
                }))
            }
            None => Err(wm_core::CoreError::NotFound(
                "State snapshot not found".into(),
            )),
        }
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn open_store() -> (tempfile::TempDir, Arc<MemoryStore>) {
        let tmp = tempfile::tempdir().unwrap();
        let store = MemoryStore::open_default(tmp.path()).unwrap();
        (tmp, Arc::new(store))
    }

    fn seed_memories(store: &Arc<MemoryStore>) {
        // Normal memories
        for i in 0..5 {
            let mut mem = Memory::new(Galaxy::Codex, format!("Normal memory number {i}"));
            mem.metadata.importance = 0.5;
            mem.metadata.access_count = 5;
            mem.metadata.tags = vec!["common".into()];
            store.put(Galaxy::Codex, &mem).unwrap();
        }
        // Anomalous: very high importance
        let mut high = Memory::new(Galaxy::Codex, "Very important anomaly".into());
        high.metadata.importance = 1.0;
        high.metadata.access_count = 5;
        high.metadata.tags = vec!["common".into()];
        store.put(Galaxy::Codex, &high).unwrap();
        // Anomalous: very long content
        let mut long_mem = Memory::new(
            Galaxy::Codex,
            "A".repeat(500) + " very long anomaly content",
        );
        long_mem.metadata.importance = 0.5;
        long_mem.metadata.access_count = 5;
        long_mem.metadata.tags = vec!["rare-tag".into()];
        store.put(Galaxy::Codex, &long_mem).unwrap();
    }

    #[tokio::test]
    async fn anomaly_detect_finds_outliers() {
        let (_tmp, store) = open_store();
        seed_memories(&store);

        let tool = AnomalyDetectTool::new(store);
        let result = tool
            .call(&mut Context::default(), json!({"sensitivity": "high"}))
            .await
            .unwrap();
        let obj = result.as_object().unwrap();
        assert_eq!(obj["status"], "success");
        assert!(obj["total_memories"].as_u64().unwrap() >= 7);
        let anomalies = obj["anomalies"].as_array().unwrap();
        assert!(!anomalies.is_empty(), "Should detect anomalies");
    }

    #[tokio::test]
    async fn anomaly_detect_empty_store() {
        let (_tmp, store) = open_store();
        let tool = AnomalyDetectTool::new(store);
        let result = tool.call(&mut Context::default(), json!({})).await.unwrap();
        let obj = result.as_object().unwrap();
        assert_eq!(obj["total_memories"], 0);
        assert_eq!(obj["anomalies"].as_array().unwrap().len(), 0);
    }

    #[tokio::test]
    async fn anomaly_detect_low_sensitivity() {
        let (_tmp, store) = open_store();
        seed_memories(&store);

        let tool = AnomalyDetectTool::new(store);
        let result = tool
            .call(&mut Context::default(), json!({"sensitivity": "low"}))
            .await
            .unwrap();
        let obj = result.as_object().unwrap();
        assert_eq!(obj["sensitivity"], "low");
    }

    #[tokio::test]
    async fn state_snapshot_captures_state() {
        let (_tmp, store) = open_store();
        seed_memories(&store);

        let tool = StateSnapshotTool::new(store);
        let result = tool
            .call(&mut Context::default(), json!({"label": "test-snapshot"}))
            .await
            .unwrap();
        let obj = result.as_object().unwrap();
        assert_eq!(obj["status"], "success");
        assert_eq!(obj["label"], "test-snapshot");
        assert!(obj["total_memories"].as_u64().unwrap() >= 7);
        assert!(obj["galaxies_with_data"].as_u64().unwrap() >= 1);
    }

    #[tokio::test]
    async fn state_snapshot_default_label() {
        let (_tmp, store) = open_store();
        let tool = StateSnapshotTool::new(store);
        let result = tool.call(&mut Context::default(), json!({})).await.unwrap();
        let obj = result.as_object().unwrap();
        assert_eq!(obj["label"], "system-state");
    }

    #[tokio::test]
    async fn state_revert_finds_snapshot() {
        let (_tmp, store) = open_store();
        seed_memories(&store);

        // Create snapshot
        let snap_tool = StateSnapshotTool::new(store.clone());
        snap_tool
            .call(&mut Context::default(), json!({"label": "revert-test"}))
            .await
            .unwrap();

        // Add more memories after snapshot
        let mem = Memory::new(Galaxy::Codex, "Post-snapshot memory".into());
        store.put(Galaxy::Codex, &mem).unwrap();

        // Revert
        let revert_tool = StateRevertTool::new(store);
        let result = revert_tool
            .call(&mut Context::default(), json!({"label": "revert-test"}))
            .await
            .unwrap();
        let obj = result.as_object().unwrap();
        assert_eq!(obj["status"], "success");
        assert!(obj["snapshot"].is_object());
        let delta = obj["delta"].as_i64().unwrap();
        assert!(delta > 0, "Current should have more memories than snapshot");
    }

    #[tokio::test]
    async fn state_revert_not_found() {
        let (_tmp, store) = open_store();
        let tool = StateRevertTool::new(store);
        let result = tool
            .call(&mut Context::default(), json!({"label": "nonexistent"}))
            .await;
        assert!(result.is_err());
    }

    #[tokio::test]
    async fn state_revert_missing_args() {
        let (_tmp, store) = open_store();
        let tool = StateRevertTool::new(store);
        let result = tool.call(&mut Context::default(), json!({})).await;
        assert!(result.is_err());
    }
}
