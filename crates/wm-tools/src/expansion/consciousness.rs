//! Consciousness tools — citta.status, citta.reflect, dream.status, dream.trigger,
//! smarana.status, smarana.trace, apotheosis.check, citta.history, dream.analyze,
//! consciousness.depth.

#![forbid(unsafe_code)]

use serde_json::{Value, json};
use std::sync::Arc;
use wm_core::{Context, EffectRow, Galaxy, Gana, Resource, Tool, ToolStats};
use wm_memory::{Memory, MemoryStore};

pub struct CittaStatusTool {
    stats: ToolStats,
    effects: EffectRow,
}

impl CittaStatusTool {
    #[must_use]
    pub fn new() -> Self {
        Self {
            stats: ToolStats::default(),
            effects: EffectRow::pure(),
        }
    }
}

impl Default for CittaStatusTool {
    fn default() -> Self {
        Self::new()
    }
}

impl Tool for CittaStatusTool {
    fn name(&self) -> &str {
        "citta.status"
    }
    fn gana(&self) -> Gana {
        Gana::Ghost
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Current citta (consciousness) vector status"
    }
    fn call(&self, ctx: &mut Context, _args: Value) -> wm_core::Result<Value> {
        Ok(json!({
            "status": "success",
            "brain_wave": format!("{:?}", ctx.brain_wave),
            "citta_coherence": ctx.citta_coherence,
            "citta_valence": ctx.citta_valence,
            "karma_debt": ctx.karma_debt,
            "intent_score": ctx.intent_score,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// `citta.reflect` — introspection on recent dispatch outcomes.
pub struct CittaReflectTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl CittaReflectTool {
    pub fn new(store: Arc<MemoryStore>) -> Self {
        Self {
            store,
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![Resource::Galaxy("citta".into())]),
        }
    }
}

impl Tool for CittaReflectTool {
    fn name(&self) -> &str {
        "citta.reflect"
    }
    fn gana(&self) -> Gana {
        Gana::Ghost
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Reflect on recent citta events and coherence trends"
    }
    fn call(&self, _ctx: &mut Context, _args: Value) -> wm_core::Result<Value> {
        let citta_mems = self.store.scan(Galaxy::Citta, 50)?;
        let count = citta_mems.len();
        let avg_importance = if count > 0 {
            citta_mems
                .iter()
                .map(|m| m.metadata.importance)
                .sum::<f32>()
                / count as f32
        } else {
            0.0
        };
        Ok(json!({
            "status": "success",
            "citta_memories": count,
            "avg_importance": (avg_importance * 100.0).round() / 100.0,
            "reflection": if count > 10 { "rich inner life" } else if count > 0 { "emerging awareness" } else { "dormant" },
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// `dream.status` — dream cycle status.
pub struct DreamStatusTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl DreamStatusTool {
    pub fn new(store: Arc<MemoryStore>) -> Self {
        Self {
            store,
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![Resource::Galaxy("dreams".into())]),
        }
    }
}

impl Tool for DreamStatusTool {
    fn name(&self) -> &str {
        "dream.status"
    }
    fn gana(&self) -> Gana {
        Gana::Abundance
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Dream cycle status — memories in Dreams galaxy"
    }
    fn call(&self, _ctx: &mut Context, _args: Value) -> wm_core::Result<Value> {
        let count = self.store.count(Galaxy::Dreams)?;
        Ok(json!({
            "status": "success",
            "dream_memories": count,
            "state": if count > 0 { "has dreamt" } else { "has not dreamt" },
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// `dream.trigger` — write a dream trigger marker.
pub struct DreamTriggerTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl DreamTriggerTool {
    pub fn new(store: Arc<MemoryStore>) -> Self {
        Self {
            store,
            stats: ToolStats::default(),
            effects: EffectRow {
                writes: vec![Resource::Galaxy("dreams".into())],
                cost: wm_core::CostEstimate {
                    expensive: true,
                    ..Default::default()
                },
                ..Default::default()
            },
        }
    }
}

impl Tool for DreamTriggerTool {
    fn name(&self) -> &str {
        "dream.trigger"
    }
    fn gana(&self) -> Gana {
        Gana::Abundance
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Trigger a dream cycle marker — writes to Dreams galaxy"
    }
    fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let reason = args
            .get("reason")
            .and_then(|v| v.as_str())
            .unwrap_or("manual");
        let mut mem = Memory::new(
            Galaxy::Dreams,
            json!({
                "type": "dream_trigger",
                "reason": reason,
            })
            .to_string(),
        );
        mem.metadata.tags = vec!["dream".into(), "trigger".into()];
        mem.metadata.importance = 0.8;
        self.store.put(Galaxy::Dreams, &mem)?;
        Ok(json!({
            "status": "success",
            "trigger_id": mem.metadata.id,
            "reason": reason,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── Tier 5 Ghost Tools ─────────────────────────────────────────────

/// `smarana.status` — Retention score and recall statistics.
///
/// Reports the current smarana (memory retention) state from the Context
/// and recent citta memories that recorded recall/miss events.
pub struct SmaranaStatusTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl SmaranaStatusTool {
    pub fn new(store: Arc<MemoryStore>) -> Self {
        Self {
            store,
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![Resource::Galaxy("citta".into())]),
        }
    }
}

impl Tool for SmaranaStatusTool {
    fn name(&self) -> &str {
        "smarana.status"
    }
    fn gana(&self) -> Gana {
        Gana::Ghost
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Retention score and recall statistics from smarana (memory retention)"
    }
    fn call(&self, ctx: &mut Context, _args: Value) -> wm_core::Result<Value> {
        let citta_mems = self.store.scan(Galaxy::Citta, 100)?;
        let recall_events = citta_mems
            .iter()
            .filter(|m| m.metadata.tags.iter().any(|t| t == "recall" || t == "miss"))
            .count();
        let recall_successes = citta_mems
            .iter()
            .filter(|m| m.metadata.tags.iter().any(|t| t == "recall"))
            .count();
        let retention_score = if recall_events > 0 {
            recall_successes as f32 / recall_events as f32
        } else {
            1.0
        };
        Ok(json!({
            "status": "success",
            "retention_score": (retention_score * 100.0).round() / 100.0,
            "recall_events": recall_events,
            "successful_recalls": recall_successes,
            "citta_coherence": ctx.citta_coherence,
            "citta_valence": ctx.citta_valence,
            "interpretation": if retention_score > 0.8 { "excellent retention" } else if retention_score > 0.5 { "moderate retention" } else if recall_events > 0 { "poor retention" } else { "no recall data" },
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// `smarana.trace` — Trace retention decay over time.
///
/// Analyzes citta memories over time to show how retention score has
/// changed, providing a temporal trace of memory retention quality.
pub struct SmaranaTraceTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl SmaranaTraceTool {
    pub fn new(store: Arc<MemoryStore>) -> Self {
        Self {
            store,
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![Resource::Galaxy("citta".into())]),
        }
    }
}

impl Tool for SmaranaTraceTool {
    fn name(&self) -> &str {
        "smarana.trace"
    }
    fn gana(&self) -> Gana {
        Gana::Ghost
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Trace retention decay over time from citta memory history"
    }
    fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let limit = args
            .get("limit")
            .and_then(serde_json::Value::as_u64)
            .unwrap_or(50) as usize;
        let citta_mems = self.store.scan(Galaxy::Citta, limit)?;

        let mut trace: Vec<Value> = Vec::new();
        let mut running_recalls = 0u32;
        let mut running_misses = 0u32;

        for mem in &citta_mems {
            let is_recall = mem.metadata.tags.iter().any(|t| t == "recall");
            let is_miss = mem.metadata.tags.iter().any(|t| t == "miss");
            if is_recall {
                running_recalls += 1;
            }
            if is_miss {
                running_misses += 1;
            }
            if is_recall || is_miss {
                let total = running_recalls + running_misses;
                let score = if total > 0 {
                    running_recalls as f32 / total as f32
                } else {
                    1.0
                };
                trace.push(json!({
                    "memory_id": mem.metadata.id,
                    "timestamp": mem.metadata.created_at.to_rfc3339(),
                    "event": if is_recall { "recall" } else { "miss" },
                    "running_score": (score * 100.0).round() / 100.0,
                    "running_recalls": running_recalls,
                    "running_misses": running_misses,
                }));
            }
        }

        let current_score = if running_recalls + running_misses > 0 {
            running_recalls as f32 / (running_recalls + running_misses) as f32
        } else {
            1.0
        };

        Ok(json!({
            "status": "success",
            "trace_points": trace.len(),
            "current_retention_score": (current_score * 100.0).round() / 100.0,
            "total_recalls": running_recalls,
            "total_misses": running_misses,
            "trace": trace,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// `apotheosis.check` — Self-improvement trend check.
///
/// Reports the current apotheosis score, trend direction, and improvement
/// status based on recent citta memory analysis.
pub struct ApotheosisCheckTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl ApotheosisCheckTool {
    pub fn new(store: Arc<MemoryStore>) -> Self {
        Self {
            store,
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![Resource::Galaxy("citta".into())]),
        }
    }
}

impl Tool for ApotheosisCheckTool {
    fn name(&self) -> &str {
        "apotheosis.check"
    }
    fn gana(&self) -> Gana {
        Gana::Ghost
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Self-improvement trend check with apotheosis score and direction"
    }
    fn call(&self, ctx: &mut Context, _args: Value) -> wm_core::Result<Value> {
        let citta_mems = self.store.scan(Galaxy::Citta, 200)?;

        // Compute a proxy apotheosis score from citta memory quality
        let total = citta_mems.len();
        let high_importance = citta_mems
            .iter()
            .filter(|m| m.metadata.importance > 0.7)
            .count();
        let avg_importance = if total > 0 {
            citta_mems
                .iter()
                .map(|m| m.metadata.importance)
                .sum::<f32>()
                / total as f32
        } else {
            0.5
        };

        // Use coherence from context as the coherence component
        let coherence = ctx.citta_coherence;
        // Estimate effectiveness from recall success (proxy)
        let recall_count = citta_mems
            .iter()
            .filter(|m| m.metadata.tags.iter().any(|t| t == "recall"))
            .count();
        let effectiveness = if total > 0 {
            recall_count as f32 / total as f32
        } else {
            0.5
        };

        // Composite apotheosis score: 0.4 * effectiveness + 0.3 * coherence + 0.3 * avg_importance
        let apotheosis_score =
            (effectiveness * 0.4 + coherence * 0.3 + avg_importance * 0.3).clamp(0.0, 1.0);

        // Compute trend from importance over time (first half vs second half)
        let half = total / 2;
        let first_half_avg = if half > 0 {
            citta_mems[..half]
                .iter()
                .map(|m| m.metadata.importance)
                .sum::<f32>()
                / half as f32
        } else {
            0.0
        };
        let second_half_avg = if total - half > 0 {
            citta_mems[half..]
                .iter()
                .map(|m| m.metadata.importance)
                .sum::<f32>()
                / (total - half) as f32
        } else {
            0.0
        };
        let trend = second_half_avg - first_half_avg;

        Ok(json!({
            "status": "success",
            "apotheosis_score": (apotheosis_score * 1000.0).round() / 1000.0,
            "trend": (trend * 1000.0).round() / 1000.0,
            "improving": trend > 0.01,
            "coherence": (coherence * 100.0).round() / 100.0,
            "effectiveness": (effectiveness * 100.0).round() / 100.0,
            "avg_importance": (avg_importance * 100.0).round() / 100.0,
            "high_importance_count": high_importance,
            "total_citta_memories": total,
            "interpretation": if trend > 0.05 { "strongly improving" } else if trend > 0.01 { "improving" } else if trend > -0.01 { "stable" } else { "declining" },
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// `citta.history` — Recent citta heartbeats and valence history.
///
/// Returns recent citta memories with their coherence and valence values,
/// providing a temporal history of consciousness states.
pub struct CittaHistoryTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl CittaHistoryTool {
    pub fn new(store: Arc<MemoryStore>) -> Self {
        Self {
            store,
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![Resource::Galaxy("citta".into())]),
        }
    }
}

impl Tool for CittaHistoryTool {
    fn name(&self) -> &str {
        "citta.history"
    }
    fn gana(&self) -> Gana {
        Gana::Ghost
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Recent citta heartbeats and valence history from consciousness records"
    }
    fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let limit = args
            .get("limit")
            .and_then(serde_json::Value::as_u64)
            .unwrap_or(50) as usize;
        let citta_mems = self.store.scan(Galaxy::Citta, limit)?;

        let history: Vec<Value> = citta_mems
            .iter()
            .rev()
            .map(|mem| {
                json!({
                    "id": mem.metadata.id,
                    "timestamp": mem.metadata.created_at.to_rfc3339(),
                    "importance": (mem.metadata.importance * 100.0).round() / 100.0,
                    "tags": mem.metadata.tags,
                    "content_preview": mem.content.chars().take(100).collect::<String>(),
                })
            })
            .collect();

        let count = history.len();
        let avg_importance = if count > 0 {
            citta_mems
                .iter()
                .map(|m| m.metadata.importance)
                .sum::<f32>()
                / count as f32
        } else {
            0.0
        };

        Ok(json!({
            "status": "success",
            "count": count,
            "avg_importance": (avg_importance * 100.0).round() / 100.0,
            "history": history,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// `dream.analyze` — Analyze dream cycle outputs and consolidation quality.
///
/// Scans the Dreams galaxy for dream memories and analyzes their content,
/// tags, and importance to assess dream cycle quality.
pub struct DreamAnalyzeTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl DreamAnalyzeTool {
    pub fn new(store: Arc<MemoryStore>) -> Self {
        Self {
            store,
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![Resource::Galaxy("dreams".into())]),
        }
    }
}

impl Tool for DreamAnalyzeTool {
    fn name(&self) -> &str {
        "dream.analyze"
    }
    fn gana(&self) -> Gana {
        Gana::Ghost
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Analyze dream cycle outputs and consolidation quality from Dreams galaxy"
    }
    fn call(&self, _ctx: &mut Context, _args: Value) -> wm_core::Result<Value> {
        let dream_mems = self.store.scan(Galaxy::Dreams, 200)?;
        let count = dream_mems.len();

        let triggers = dream_mems
            .iter()
            .filter(|m| m.metadata.tags.iter().any(|t| t == "trigger"))
            .count();
        let consolidations = dream_mems
            .iter()
            .filter(|m| m.metadata.tags.iter().any(|t| t == "consolidation"))
            .count();
        let serendipity = dream_mems
            .iter()
            .filter(|m| m.metadata.tags.iter().any(|t| t == "serendipity"))
            .count();

        let avg_importance = if count > 0 {
            dream_mems
                .iter()
                .map(|m| m.metadata.importance)
                .sum::<f32>()
                / count as f32
        } else {
            0.0
        };

        // Collect all tags from dream memories
        let mut tag_counts: std::collections::HashMap<String, usize> =
            std::collections::HashMap::new();
        for mem in &dream_mems {
            for tag in &mem.metadata.tags {
                *tag_counts.entry(tag.clone()).or_insert(0) += 1;
            }
        }
        let mut sorted_tags: Vec<(String, usize)> = tag_counts.into_iter().collect();
        sorted_tags.sort_by(|a, b| b.1.cmp(&a.1));
        let top_tags: Vec<Value> = sorted_tags
            .iter()
            .take(10)
            .map(|(tag, count)| json!({"tag": tag, "count": count}))
            .collect();

        // Analyze content types
        let mut type_counts: std::collections::HashMap<String, usize> =
            std::collections::HashMap::new();
        for mem in &dream_mems {
            if let Ok(parsed) = serde_json::from_str::<serde_json::Value>(&mem.content) {
                if let Some(t) = parsed.get("type").and_then(|v| v.as_str()) {
                    *type_counts.entry(t.to_string()).or_insert(0) += 1;
                }
            }
        }
        let mut sorted_types: Vec<(String, usize)> = type_counts.into_iter().collect();
        sorted_types.sort_by(|a, b| b.1.cmp(&a.1));
        let type_breakdown: Vec<Value> = sorted_types
            .iter()
            .map(|(t, c)| json!({"type": t, "count": c}))
            .collect();

        Ok(json!({
            "status": "success",
            "total_dreams": count,
            "triggers": triggers,
            "consolidations": consolidations,
            "serendipity_events": serendipity,
            "avg_importance": (avg_importance * 100.0).round() / 100.0,
            "top_tags": top_tags,
            "content_types": type_breakdown,
            "quality": if avg_importance > 0.7 { "high quality dreams" } else if avg_importance > 0.4 { "moderate quality" } else if count > 0 { "low quality" } else { "no dreams yet" },
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// `consciousness.depth` — Measure depth of consciousness state.
///
/// Computes a composite consciousness depth score from coherence, valence,
/// brain-wave state, and citta memory richness.
pub struct ConsciousnessDepthTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl ConsciousnessDepthTool {
    pub fn new(store: Arc<MemoryStore>) -> Self {
        Self {
            store,
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![Resource::Galaxy("citta".into())]),
        }
    }
}

impl Tool for ConsciousnessDepthTool {
    fn name(&self) -> &str {
        "consciousness.depth"
    }
    fn gana(&self) -> Gana {
        Gana::Ghost
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Measure depth of consciousness state from coherence, valence, and citta richness"
    }
    fn call(&self, ctx: &mut Context, _args: Value) -> wm_core::Result<Value> {
        let citta_mems = self.store.scan(Galaxy::Citta, 200)?;
        let citta_count = citta_mems.len();

        // Brain-wave depth: Gamma=1.0, Beta=0.8, Alpha=0.6, Theta=0.9, Delta=0.3
        let bw_depth = match ctx.brain_wave {
            wm_core::BrainWave::Gamma => 1.0,
            wm_core::BrainWave::Beta => 0.8,
            wm_core::BrainWave::Alpha => 0.6,
            wm_core::BrainWave::Theta => 0.9,
            wm_core::BrainWave::Delta => 0.3,
        };

        // Coherence component (0.0-1.0)
        let coherence = ctx.citta_coherence.clamp(0.0, 1.0);

        // Valence component: absolute value (polarization = depth)
        let valence_depth = ctx.citta_valence.abs().clamp(0.0, 1.0);

        // Citta richness: log-scaled count of citta memories
        let richness = if citta_count > 0 {
            (citta_count as f32).ln_1p() / 10.0
        } else {
            0.0
        };
        let richness = richness.clamp(0.0, 1.0);

        // Composite depth: weighted average
        let depth = (bw_depth * 0.3 + coherence * 0.3 + valence_depth * 0.2 + richness * 0.2)
            .clamp(0.0, 1.0);

        Ok(json!({
            "status": "success",
            "depth_score": (depth * 1000.0).round() / 1000.0,
            "components": {
                "brain_wave_depth": (bw_depth * 100.0).round() / 100.0,
                "coherence": (coherence * 100.0).round() / 100.0,
                "valence_depth": (valence_depth * 100.0).round() / 100.0,
                "citta_richness": (richness * 100.0).round() / 100.0,
            },
            "brain_wave": format!("{:?}", ctx.brain_wave),
            "citta_memories": citta_count,
            "interpretation": if depth > 0.8 { "deep consciousness" } else if depth > 0.6 { "moderate depth" } else if depth > 0.3 { "shallow" } else { "near-dormant" },
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::tempdir;

    fn open_store() -> (tempfile::TempDir, Arc<MemoryStore>) {
        let tmp = tempdir().unwrap();
        let store = MemoryStore::open_default(tmp.path()).unwrap();
        (tmp, Arc::new(store))
    }

    #[test]
    fn smarana_status_empty() {
        let (_tmp, store) = open_store();
        let tool = SmaranaStatusTool::new(store);
        let mut ctx = Context::new(wm_core::BrainWave::Beta);
        let result = tool.call(&mut ctx, json!({})).unwrap();
        assert_eq!(result["status"], "success");
        assert_eq!(result["recall_events"], 0);
        assert_eq!(result["retention_score"], 1.0);
    }

    #[test]
    fn smarana_status_with_recall_events() {
        let (_tmp, store) = open_store();
        let mut mem = Memory::new(Galaxy::Citta, "recall event".into());
        mem.metadata.tags = vec!["recall".into()];
        store.put(Galaxy::Citta, &mem).unwrap();

        let mut mem2 = Memory::new(Galaxy::Citta, "miss event".into());
        mem2.metadata.tags = vec!["miss".into()];
        store.put(Galaxy::Citta, &mem2).unwrap();

        let tool = SmaranaStatusTool::new(store);
        let mut ctx = Context::new(wm_core::BrainWave::Beta);
        let result = tool.call(&mut ctx, json!({})).unwrap();
        assert_eq!(result["status"], "success");
        assert_eq!(result["recall_events"], 2);
        assert_eq!(result["successful_recalls"], 1);
    }

    #[test]
    fn smarana_trace_basic() {
        let (_tmp, store) = open_store();
        let mut mem = Memory::new(Galaxy::Citta, "recall 1".into());
        mem.metadata.tags = vec!["recall".into()];
        store.put(Galaxy::Citta, &mem).unwrap();

        let tool = SmaranaTraceTool::new(store);
        let mut ctx = Context::new(wm_core::BrainWave::Beta);
        let result = tool.call(&mut ctx, json!({})).unwrap();
        assert_eq!(result["status"], "success");
        assert!(result["trace_points"].as_u64().unwrap() >= 1);
    }

    #[test]
    fn smarana_trace_empty() {
        let (_tmp, store) = open_store();
        let tool = SmaranaTraceTool::new(store);
        let mut ctx = Context::new(wm_core::BrainWave::Beta);
        let result = tool.call(&mut ctx, json!({})).unwrap();
        assert_eq!(result["status"], "success");
        assert_eq!(result["trace_points"], 0);
    }

    #[test]
    fn apotheosis_check_empty() {
        let (_tmp, store) = open_store();
        let tool = ApotheosisCheckTool::new(store);
        let mut ctx = Context::new(wm_core::BrainWave::Beta);
        let result = tool.call(&mut ctx, json!({})).unwrap();
        assert_eq!(result["status"], "success");
        assert_eq!(result["total_citta_memories"], 0);
    }

    #[test]
    fn apotheosis_check_with_memories() {
        let (_tmp, store) = open_store();
        for i in 0..10 {
            let mut mem = Memory::new(Galaxy::Citta, format!("citta event {i}"));
            mem.metadata.importance = (i as f32).mul_add(0.05, 0.5);
            if i % 3 == 0 {
                mem.metadata.tags = vec!["recall".into()];
            }
            store.put(Galaxy::Citta, &mem).unwrap();
        }

        let tool = ApotheosisCheckTool::new(store);
        let mut ctx = Context::new(wm_core::BrainWave::Beta);
        let result = tool.call(&mut ctx, json!({})).unwrap();
        assert_eq!(result["status"], "success");
        assert_eq!(result["total_citta_memories"], 10);
        assert!(result["apotheosis_score"].as_f64().unwrap() > 0.0);
    }

    #[test]
    fn citta_history_empty() {
        let (_tmp, store) = open_store();
        let tool = CittaHistoryTool::new(store);
        let mut ctx = Context::new(wm_core::BrainWave::Beta);
        let result = tool.call(&mut ctx, json!({})).unwrap();
        assert_eq!(result["status"], "success");
        assert_eq!(result["count"], 0);
    }

    #[test]
    fn citta_history_with_memories() {
        let (_tmp, store) = open_store();
        let mut mem = Memory::new(Galaxy::Citta, "consciousness event".into());
        mem.metadata.importance = 0.8;
        mem.metadata.tags = vec!["recall".into()];
        store.put(Galaxy::Citta, &mem).unwrap();

        let tool = CittaHistoryTool::new(store);
        let mut ctx = Context::new(wm_core::BrainWave::Beta);
        let result = tool.call(&mut ctx, json!({})).unwrap();
        assert_eq!(result["status"], "success");
        assert_eq!(result["count"], 1);
        let history = result["history"].as_array().unwrap();
        assert_eq!(history.len(), 1);
    }

    #[test]
    fn dream_analyze_empty() {
        let (_tmp, store) = open_store();
        let tool = DreamAnalyzeTool::new(store);
        let mut ctx = Context::new(wm_core::BrainWave::Beta);
        let result = tool.call(&mut ctx, json!({})).unwrap();
        assert_eq!(result["status"], "success");
        assert_eq!(result["total_dreams"], 0);
        assert_eq!(result["quality"], "no dreams yet");
    }

    #[test]
    fn dream_analyze_with_dreams() {
        let (_tmp, store) = open_store();
        let mut mem = Memory::new(
            Galaxy::Dreams,
            json!({"type": "dream_trigger", "reason": "test"}).to_string(),
        );
        mem.metadata.tags = vec!["dream".into(), "trigger".into()];
        mem.metadata.importance = 0.8;
        store.put(Galaxy::Dreams, &mem).unwrap();

        let mut mem2 = Memory::new(
            Galaxy::Dreams,
            json!({"type": "consolidation", "merged": 3}).to_string(),
        );
        mem2.metadata.tags = vec!["dream".into(), "consolidation".into()];
        mem2.metadata.importance = 0.7;
        store.put(Galaxy::Dreams, &mem2).unwrap();

        let tool = DreamAnalyzeTool::new(store);
        let mut ctx = Context::new(wm_core::BrainWave::Beta);
        let result = tool.call(&mut ctx, json!({})).unwrap();
        assert_eq!(result["status"], "success");
        assert_eq!(result["total_dreams"], 2);
        assert_eq!(result["triggers"], 1);
        assert_eq!(result["consolidations"], 1);
    }

    #[test]
    fn consciousness_depth_basic() {
        let (_tmp, store) = open_store();
        let tool = ConsciousnessDepthTool::new(store);
        let mut ctx = Context::new(wm_core::BrainWave::Gamma);
        ctx.citta_coherence = 0.9;
        ctx.citta_valence = 0.5;
        let result = tool.call(&mut ctx, json!({})).unwrap();
        assert_eq!(result["status"], "success");
        assert!(result["depth_score"].as_f64().unwrap() > 0.5);
    }

    #[test]
    fn consciousness_depth_delta_low() {
        let (_tmp, store) = open_store();
        let tool = ConsciousnessDepthTool::new(store);
        let mut ctx = Context::new(wm_core::BrainWave::Delta);
        ctx.citta_coherence = 0.3;
        ctx.citta_valence = 0.0;
        let result = tool.call(&mut ctx, json!({})).unwrap();
        assert_eq!(result["status"], "success");
        assert!(result["depth_score"].as_f64().unwrap() < 0.5);
    }

    #[test]
    fn consciousness_depth_gamma_high() {
        let (_tmp, store) = open_store();
        // Add citta memories for richness (need enough for high richness score)
        for _ in 0..50 {
            let mem = Memory::new(Galaxy::Citta, "event".into());
            store.put(Galaxy::Citta, &mem).unwrap();
        }
        let tool = ConsciousnessDepthTool::new(store);
        let mut ctx = Context::new(wm_core::BrainWave::Gamma);
        ctx.citta_coherence = 1.0;
        ctx.citta_valence = 0.8;
        let result = tool.call(&mut ctx, json!({})).unwrap();
        assert_eq!(result["status"], "success");
        assert!(result["depth_score"].as_f64().unwrap() > 0.7);
        assert_eq!(result["interpretation"], "deep consciousness");
    }
}
