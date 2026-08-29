//! Mindful forgetting — multi-signal memory retention scoring.
//!
//! Ported from v2's `mindful_forgetting.py`. A memory's retention score
//! is computed from several independent signals:
//!   1. Semantic importance (the memory's own importance field)
//!   2. Recency & recall (hippocampal access patterns)
//!   3. Connection density (how many associations link to it)
//!   4. Pattern relevance (tag density — does it participate in patterns?)
//!   5. Protection (high-importance memories are hard-protected)
//!
//! If the composite retention score drops below a threshold, the memory's
//! importance is decayed (never deleted — mindful forgetting is gentle).

use chrono::Utc;
use serde::{Deserialize, Serialize};
use std::collections::HashSet;
use wm_core::{Galaxy, Result};
use wm_memory::{AssociationStore, Memory, MemoryStore};

/// One subsystem's vote on whether a memory should be retained.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RetentionSignal {
    /// Signal name (e.g. "semantic", "recency", "connection")
    pub name: String,
    /// 0.0 (forget) to 1.0 (absolutely keep)
    pub score: f32,
    /// How much this signal matters
    pub weight: f32,
    /// Human-readable explanation
    pub reason: String,
}

/// Final retention decision for a single memory.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RetentionVerdict {
    /// Memory UUID (as string for serialization)
    pub memory_id: String,
    /// Whether to retain the memory
    pub retain: bool,
    /// Composite retention score 0.0-1.0
    pub score: f32,
    /// Individual signal breakdown
    pub signals: Vec<RetentionSignal>,
    /// Recommended action: "keep", "decay", "protect"
    pub recommended_action: String,
}

/// Configuration for the retention engine.
#[derive(Debug, Clone)]
pub struct RetentionConfig {
    /// Composite score below which memories are decayed
    pub retain_threshold: f32,
    /// Score below which memories are aggressively decayed
    pub decay_threshold: f32,
    /// Recency half-life in days
    pub recency_half_life_days: f32,
    /// Frequency bonus cap
    pub freq_bonus_cap: f32,
    /// Importance level for hard protection
    pub protection_importance: f32,
    /// Maximum connection links to consider for density
    pub max_connection_links: f32,
    /// Weight for the emotional salience signal
    pub emotional_weight: f32,
    /// Weight for the neuro_score signal
    pub neuro_weight: f32,
}

impl Default for RetentionConfig {
    fn default() -> Self {
        Self {
            retain_threshold: 0.35,
            decay_threshold: 0.15,
            recency_half_life_days: 30.0,
            freq_bonus_cap: 0.3,
            protection_importance: 0.9,
            max_connection_links: 10.0,
            emotional_weight: 0.6,
            neuro_weight: 0.8,
        }
    }
}

/// Multi-signal retention engine.
///
/// Evaluates each memory against independent signals and produces a
/// composite retention verdict. Used by the dream cycle's Decay phase.
pub struct RetentionEngine {
    config: RetentionConfig,
}

impl RetentionEngine {
    /// Create a new retention engine with the given config.
    #[must_use]
    pub const fn new(config: RetentionConfig) -> Self {
        Self { config }
    }

    /// Create with default config.
    #[must_use]
    pub fn default_config() -> Self {
        Self::new(RetentionConfig::default())
    }

    /// Evaluate a single memory for retention.
    ///
    /// `association_count` is the number of associations linking to/from
    /// this memory (computed externally via `AssociationStore`).
    #[must_use]
    pub fn evaluate(&self, mem: &Memory, association_count: usize) -> RetentionVerdict {
        let signals = vec![
            self.semantic_signal(mem),
            self.recency_signal(mem),
            self.connection_signal(mem, association_count),
            self.pattern_signal(mem),
            self.protection_signal(mem),
            self.emotional_signal(mem),
            self.neuro_signal(mem),
        ];

        // Compute weighted average (excluding zero-weight signals)
        let total_weight: f32 = signals
            .iter()
            .filter(|s| s.weight > 0.0)
            .map(|s| s.weight)
            .sum();
        let composite = if total_weight == 0.0 {
            0.5
        } else {
            let raw: f32 = signals.iter().map(|s| s.score * s.weight).sum();
            (raw / total_weight).clamp(0.0, 1.0)
        };

        // Determine action — explicit is_protected flag or high-importance protection
        let is_protected = mem.metadata.is_protected
            || signals
                .iter()
                .any(|s| s.name == "protection" && s.score >= 1.0);
        let (retain, action) = if is_protected {
            (true, "protect")
        } else if composite >= self.config.retain_threshold {
            (true, "keep")
        } else if composite >= self.config.decay_threshold {
            (true, "decay")
        } else {
            (false, "decay")
        };

        RetentionVerdict {
            memory_id: mem.metadata.id.to_string(),
            retain,
            score: composite,
            signals,
            recommended_action: action.to_string(),
        }
    }

    /// Semantic importance — the memory's own importance field.
    fn semantic_signal(&self, mem: &Memory) -> RetentionSignal {
        let score = mem.metadata.importance;
        RetentionSignal {
            name: "semantic".into(),
            score,
            weight: 1.0,
            reason: format!("importance={score:.2}"),
        }
    }

    /// Recency & recall — exponential decay based on time since last access.
    fn recency_signal(&self, mem: &Memory) -> RetentionSignal {
        let now = Utc::now();
        let days_since = (now - mem.metadata.accessed_at).num_days() as f32;
        let half_life = self.config.recency_half_life_days;

        // Exponential recency decay
        let recency = 0.5_f32.powf(days_since / half_life.max(1.0));

        // Frequency bonus (log scale, capped)
        let freq_bonus =
            (self.config.freq_bonus_cap).min((mem.metadata.access_count as f32).ln_1p() * 0.05);

        let score = (recency + freq_bonus).min(1.0);
        RetentionSignal {
            name: "recency".into(),
            score,
            weight: 0.9,
            reason: format!(
                "days_since={:.1}, recalls={}, half_life={}",
                days_since, mem.metadata.access_count, half_life
            ),
        }
    }

    /// Connection density — memories with many associations are harder to forget.
    fn connection_signal(&self, _mem: &Memory, link_count: usize) -> RetentionSignal {
        if link_count == 0 {
            return RetentionSignal {
                name: "connection".into(),
                score: 0.1,
                weight: 0.7,
                reason: "no links".into(),
            };
        }

        let n = link_count as f32;
        let density = (n / self.config.max_connection_links).min(1.0);
        RetentionSignal {
            name: "connection".into(),
            score: density,
            weight: 0.7,
            reason: format!("links={link_count}"),
        }
    }

    /// Pattern relevance — memories with more tags participate in more patterns.
    fn pattern_signal(&self, mem: &Memory) -> RetentionSignal {
        let tag_count = mem.metadata.tags.len() as f32;
        // 5+ tags = full pattern participation
        let density = (tag_count / 5.0).min(1.0);
        RetentionSignal {
            name: "pattern".into(),
            score: density,
            weight: 0.5,
            reason: format!("tags={}", mem.metadata.tags.len()),
        }
    }

    /// Protection — high-importance memories or explicitly protected memories are hard-protected.
    fn protection_signal(&self, mem: &Memory) -> RetentionSignal {
        if mem.metadata.is_protected {
            return RetentionSignal {
                name: "protection".into(),
                score: 1.0,
                weight: 100.0,
                reason: "hard_protect: is_protected flag".into(),
            };
        }
        if mem.metadata.importance >= self.config.protection_importance {
            RetentionSignal {
                name: "protection".into(),
                score: 1.0,
                weight: 100.0,
                reason: format!(
                    "hard_protect: importance={:.2} >= {:.2}",
                    mem.metadata.importance, self.config.protection_importance
                ),
            }
        } else {
            RetentionSignal {
                name: "protection".into(),
                score: 0.0,
                weight: 0.0,
                reason: "not protected".into(),
            }
        }
    }

    /// Emotional salience — memories with high emotional weight are harder to forget.
    fn emotional_signal(&self, mem: &Memory) -> RetentionSignal {
        let weight = mem.metadata.emotional_weight;
        let valence = mem.metadata.emotional_valence.abs();
        // Score combines weight and valence intensity
        let score = f32::midpoint(weight, valence).clamp(0.0, 1.0);
        RetentionSignal {
            name: "emotional".into(),
            score,
            weight: self.config.emotional_weight,
            reason: format!(
                "valence={:.2}, weight={:.2}",
                mem.metadata.emotional_valence, weight
            ),
        }
    }

    /// Neuro score — dynamic neural strength from Hebbian recall dynamics.
    fn neuro_signal(&self, mem: &Memory) -> RetentionSignal {
        let score = mem.metadata.neuro_score;
        RetentionSignal {
            name: "neuro".into(),
            score,
            weight: self.config.neuro_weight,
            reason: format!(
                "neuro_score={:.2}, recall_count={}",
                score, mem.metadata.recall_count
            ),
        }
    }

    /// Run a retention sweep across a galaxy.
    ///
    /// Evaluates each memory and applies decay to low-scoring ones.
    /// **Never deletes** — only lowers importance for memories that
    /// score below the retain threshold.
    pub fn sweep(
        &self,
        store: &MemoryStore,
        assoc_store: &AssociationStore,
        galaxy: Galaxy,
    ) -> Result<SweepReport> {
        let memories = store.scan(galaxy, 10_000)?;
        let mut report = SweepReport::new();
        let mut to_decay: Vec<Memory> = Vec::new();

        for mem in &memories {
            // Count associations for this memory
            let from_count = assoc_store
                .find_from(store.env(), mem.metadata.id)
                .map_or(0, |v| v.len());
            let to_count = assoc_store
                .find_to(store.env(), mem.metadata.id)
                .map_or(0, |v| v.len());
            let link_count = from_count + to_count;

            let verdict = self.evaluate(mem, link_count);
            report.total_evaluated += 1;

            match verdict.recommended_action.as_str() {
                "protect" => report.protected += 1,
                "keep" => report.retained += 1,
                "decay" => {
                    report.decayed += 1;
                    // Apply decay: lower importance proportionally to how
                    // far below the retain threshold the score is
                    let decay_factor = if verdict.score < self.config.decay_threshold {
                        0.5 // Aggressive decay for very low scores
                    } else {
                        0.8 // Gentle decay for borderline scores
                    };
                    let mut updated = mem.clone();
                    updated.decay_importance(decay_factor);
                    to_decay.push(updated);
                }
                _ => {}
            }
            report.verdicts.push(verdict);
        }

        // Batch write all decayed memories in a single transaction
        if !to_decay.is_empty() {
            store.put_batch(galaxy, &to_decay)?;
        }

        Ok(report)
    }
}

/// Results from a retention sweep.
#[derive(Debug, Clone)]
pub struct SweepReport {
    /// Total memories evaluated
    pub total_evaluated: usize,
    /// Memories retained at full importance
    pub retained: usize,
    /// Memories that had importance decayed
    pub decayed: usize,
    /// Memories that are hard-protected
    pub protected: usize,
    /// Individual verdicts
    pub verdicts: Vec<RetentionVerdict>,
}

impl SweepReport {
    /// Create a new empty report.
    #[must_use]
    pub const fn new() -> Self {
        Self {
            total_evaluated: 0,
            retained: 0,
            decayed: 0,
            protected: 0,
            verdicts: Vec::new(),
        }
    }

    /// Convert to JSON for status reporting.
    #[must_use]
    pub fn to_json(&self) -> serde_json::Value {
        serde_json::json!({
            "total_evaluated": self.total_evaluated,
            "retained": self.retained,
            "decayed": self.decayed,
            "protected": self.protected,
        })
    }
}

impl Default for SweepReport {
    fn default() -> Self {
        Self::new()
    }
}

/// Extract unique tags from a set of memories (used by pattern signal).
#[must_use]
pub fn collect_tags(memories: &[Memory]) -> HashSet<String> {
    let mut tags = HashSet::new();
    for mem in memories {
        for tag in &mem.metadata.tags {
            tags.insert(tag.clone());
        }
    }
    tags
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::tempdir;
    use wm_memory::Memory;

    #[test]
    fn retention_signal_serializes() {
        let sig = RetentionSignal {
            name: "test".into(),
            score: 0.5,
            weight: 1.0,
            reason: "testing".into(),
        };
        let json = serde_json::to_string(&sig).unwrap();
        let back: RetentionSignal = serde_json::from_str(&json).unwrap();
        assert_eq!(back.name, "test");
        assert!((back.score - 0.5).abs() < f32::EPSILON);
    }

    #[test]
    fn evaluate_high_importance_memory() {
        let engine = RetentionEngine::default_config();
        let mem = Memory::new(Galaxy::Codex, "important".into()).with_importance(0.95);
        let verdict = engine.evaluate(&mem, 3);
        assert!(verdict.retain);
        assert_eq!(verdict.recommended_action, "protect");
        assert!(verdict.score >= 0.9);
    }

    #[test]
    fn evaluate_low_importance_memory() {
        let engine = RetentionEngine::default_config();
        let mem = Memory::new(Galaxy::Codex, "trivial".into()).with_importance(0.05);
        let verdict = engine.evaluate(&mem, 0);
        assert!(!verdict.retain || verdict.recommended_action == "decay");
        assert!(verdict.score < 0.35);
    }

    #[test]
    fn evaluate_connected_memory_gets_boost() {
        let engine = RetentionEngine::default_config();
        let mem = Memory::new(Galaxy::Codex, "connected".into()).with_importance(0.3);
        let verdict_low = engine.evaluate(&mem, 0);
        let verdict_high = engine.evaluate(&mem, 10);
        assert!(verdict_high.score > verdict_low.score);
    }

    #[test]
    fn evaluate_tagged_memory_gets_pattern_boost() {
        let engine = RetentionEngine::default_config();
        let mem_no_tags = Memory::new(Galaxy::Codex, "no tags".into()).with_importance(0.3);
        let mem_tags = Memory::new(Galaxy::Codex, "tagged".into()).with_tags(vec![
            "rust".into(),
            "memory".into(),
            "dream".into(),
            "cycle".into(),
            "test".into(),
        ]);
        let v1 = engine.evaluate(&mem_no_tags, 0);
        let v2 = engine.evaluate(&mem_tags, 0);
        assert!(v2.score > v1.score);
    }

    #[test]
    fn sweep_decays_low_importance() {
        let tmp = tempdir().unwrap();
        let store = MemoryStore::open_default(tmp.path()).unwrap();
        let assoc_store = AssociationStore::open(store.env()).unwrap();

        // Low importance memory
        let low = Memory::new(Galaxy::Codex, "unimportant".into()).with_importance(0.05);
        store.put(Galaxy::Codex, &low).unwrap();

        // High importance memory
        let high = Memory::new(Galaxy::Codex, "important".into()).with_importance(0.95);
        store.put(Galaxy::Codex, &high).unwrap();

        let engine = RetentionEngine::default_config();
        let report = engine.sweep(&store, &assoc_store, Galaxy::Codex).unwrap();

        assert_eq!(report.total_evaluated, 2);
        assert_eq!(report.protected, 1);
        assert_eq!(report.decayed, 1);

        // Verify the low-importance memory was decayed further
        let updated = store.get(Galaxy::Codex, low.metadata.id).unwrap().unwrap();
        assert!(updated.metadata.importance < 0.05);
    }

    #[test]
    fn sweep_never_deletes() {
        let tmp = tempdir().unwrap();
        let store = MemoryStore::open_default(tmp.path()).unwrap();
        let assoc_store = AssociationStore::open(store.env()).unwrap();

        let mem = Memory::new(Galaxy::Codex, "trivial".into()).with_importance(0.01);
        store.put(Galaxy::Codex, &mem).unwrap();

        let engine = RetentionEngine::default_config();
        let _report = engine.sweep(&store, &assoc_store, Galaxy::Codex).unwrap();

        // Memory should still exist, just with lower importance
        let still_there = store.get(Galaxy::Codex, mem.metadata.id).unwrap();
        assert!(still_there.is_some());
    }

    #[test]
    fn sweep_report_to_json() {
        let report = SweepReport {
            total_evaluated: 10,
            retained: 7,
            decayed: 2,
            protected: 1,
            verdicts: vec![],
        };
        let json = report.to_json();
        assert_eq!(json["total_evaluated"], 10);
        assert_eq!(json["retained"], 7);
        assert_eq!(json["decayed"], 2);
        assert_eq!(json["protected"], 1);
    }

    #[test]
    fn collect_tags_extracts_unique() {
        let mems = vec![
            Memory::new(Galaxy::Codex, "a".into()).with_tags(vec!["rust".into(), "memory".into()]),
            Memory::new(Galaxy::Codex, "b".into()).with_tags(vec!["rust".into(), "dream".into()]),
        ];
        let tags = collect_tags(&mems);
        assert_eq!(tags.len(), 3);
        assert!(tags.contains("rust"));
        assert!(tags.contains("memory"));
        assert!(tags.contains("dream"));
    }

    // ── Phase 6.1: Enriched signal tests ───────────────────────────────

    #[test]
    fn emotional_signal_boosts_retention() {
        let engine = RetentionEngine::default_config();
        let mem_plain = Memory::new(Galaxy::Codex, "plain".into()).with_importance(0.3);
        let mem_emotional = Memory::new(Galaxy::Codex, "emotional".into())
            .with_importance(0.3)
            .with_emotional_valence(0.9, 0.8);

        let v_plain = engine.evaluate(&mem_plain, 0);
        let v_emotional = engine.evaluate(&mem_emotional, 0);
        assert!(v_emotional.score > v_plain.score);
    }

    #[test]
    fn neuro_signal_boosts_retention() {
        let engine = RetentionEngine::default_config();
        let mem_low = Memory::new(Galaxy::Codex, "low neuro".into())
            .with_importance(0.3)
            .with_neuro_score(0.1);
        let mem_high = Memory::new(Galaxy::Codex, "high neuro".into())
            .with_importance(0.3)
            .with_neuro_score(0.9);

        let v_low = engine.evaluate(&mem_low, 0);
        let v_high = engine.evaluate(&mem_high, 0);
        assert!(v_high.score > v_low.score);
    }

    #[test]
    fn is_protected_flag_overrides_low_importance() {
        let engine = RetentionEngine::default_config();
        let mem = Memory::new(Galaxy::Codex, "protected".into())
            .with_importance(0.01)
            .with_protection(true);

        let verdict = engine.evaluate(&mem, 0);
        assert!(verdict.retain);
        assert_eq!(verdict.recommended_action, "protect");
    }

    #[test]
    fn sweep_respects_is_protected_flag() {
        let tmp = tempdir().unwrap();
        let store = MemoryStore::open_default(tmp.path()).unwrap();
        let assoc_store = AssociationStore::open(store.env()).unwrap();

        let low_protected = Memory::new(Galaxy::Codex, "protected".into())
            .with_importance(0.01)
            .with_protection(true);
        store.put(Galaxy::Codex, &low_protected).unwrap();

        let engine = RetentionEngine::default_config();
        let report = engine.sweep(&store, &assoc_store, Galaxy::Codex).unwrap();

        assert_eq!(report.protected, 1);
        assert_eq!(report.decayed, 0);

        // Importance should be unchanged
        let back = store
            .get(Galaxy::Codex, low_protected.metadata.id)
            .unwrap()
            .unwrap();
        assert!((back.metadata.importance - 0.01).abs() < f32::EPSILON);
    }

    #[test]
    fn evaluate_has_seven_signals() {
        let engine = RetentionEngine::default_config();
        let mem = Memory::new(Galaxy::Codex, "test".into());
        let verdict = engine.evaluate(&mem, 0);
        assert_eq!(verdict.signals.len(), 7);
        let names: Vec<_> = verdict.signals.iter().map(|s| s.name.as_str()).collect();
        assert!(names.contains(&"semantic"));
        assert!(names.contains(&"recency"));
        assert!(names.contains(&"connection"));
        assert!(names.contains(&"pattern"));
        assert!(names.contains(&"protection"));
        assert!(names.contains(&"emotional"));
        assert!(names.contains(&"neuro"));
    }
}
