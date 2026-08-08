//! Pattern-Dream Bridge — Connect pattern discovery to dream cycle.
//!
//! When patterns are discovered during active operation, they're queued
//! for processing during the next dream cycle, enabling subconscious
//! synthesis of patterns into higher-order insights.
//!
//! Ported from v2 `synergies/pattern_dream_bridge.py` (108 lines).
//! In v4, the queue is in-memory (no file I/O) — patterns are queued
//! during active operation and drained during dream cycle processing.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// A discovered pattern queued for dream cycle processing.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct QueuedPattern {
    /// Pattern type (e.g., "association", "constellation", "anomaly").
    pub pattern_type: String,
    /// Pattern description or summary.
    pub description: String,
    /// Optional metadata (tags, source galaxy, confidence, etc.).
    pub metadata: HashMap<String, String>,
    /// When the pattern was queued (epoch seconds).
    pub queued_at: f64,
}

impl QueuedPattern {
    /// Create a new queued pattern.
    #[must_use]
    pub fn new(pattern_type: impl Into<String>, description: impl Into<String>) -> Self {
        Self {
            pattern_type: pattern_type.into(),
            description: description.into(),
            metadata: HashMap::new(),
            queued_at: 0.0,
        }
    }

    /// Add metadata to the pattern.
    #[must_use]
    pub fn with_metadata(mut self, key: impl Into<String>, value: impl Into<String>) -> Self {
        self.metadata.insert(key.into(), value.into());
        self
    }
}

/// A synthesis produced from grouped patterns during dream cycle.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DreamSynthesis {
    /// Pattern type that was synthesized.
    pub pattern_type: String,
    /// Number of source patterns combined.
    pub source_count: usize,
    /// Synthesized insight description.
    pub synthesis: String,
    /// When the synthesis was produced (epoch seconds).
    pub produced_at: f64,
}

/// Summary of the bridge state.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BridgeSummary {
    /// Patterns currently queued for dream processing.
    pub pending_patterns: usize,
    /// Total syntheses produced across all dream cycles.
    pub total_syntheses: usize,
}

/// Pattern-Dream Bridge — queues patterns for dream cycle synthesis.
///
/// During active operation, pattern discovery (constellation detection,
/// association mining, anomaly detection, etc.) calls `queue_pattern()`.
/// During the dream cycle's Oracle phase, `process_queue()` drains the
/// queue, groups patterns by type, and synthesizes higher-order insights
/// from groups with 2+ patterns.
/// Maximum pending patterns before the bridge starts dropping new ones.
const MAX_PENDING_PATTERNS: usize = 1024;

pub struct PatternDreamBridge {
    /// Pending patterns awaiting dream cycle processing.
    pending: Vec<QueuedPattern>,
    /// Syntheses produced across all dream cycles.
    syntheses: Vec<DreamSynthesis>,
    /// Maximum pending patterns (DoS prevention).
    max_pending: usize,
}

impl PatternDreamBridge {
    /// Create a new empty bridge.
    #[must_use]
    pub const fn new() -> Self {
        Self {
            pending: Vec::new(),
            syntheses: Vec::new(),
            max_pending: MAX_PENDING_PATTERNS,
        }
    }

    /// Create a new bridge with a custom max pending limit.
    #[must_use]
    pub const fn with_max_pending(max_pending: usize) -> Self {
        Self {
            pending: Vec::new(),
            syntheses: Vec::new(),
            max_pending,
        }
    }

    /// Queue a pattern for dream cycle processing.
    ///
    /// Returns `false` if the queue is full and the pattern was dropped.
    pub fn queue_pattern(&mut self, pattern: QueuedPattern) -> bool {
        if self.pending.len() >= self.max_pending {
            tracing::warn!(
                pending = self.pending.len(),
                max = self.max_pending,
                "PatternDreamBridge queue full, dropping pattern"
            );
            return false;
        }
        self.pending.push(pattern);
        true
    }

    /// Queue a simple pattern with just type and description.
    pub fn queue(&mut self, pattern_type: impl Into<String>, description: impl Into<String>) {
        self.queue_pattern(QueuedPattern::new(pattern_type, description));
    }

    /// Number of patterns currently queued.
    #[must_use]
    pub fn pending_count(&self) -> usize {
        self.pending.len()
    }

    /// Number of syntheses produced.
    #[must_use]
    pub fn synthesis_count(&self) -> usize {
        self.syntheses.len()
    }

    /// Process queued patterns (called during dream cycle).
    ///
    /// Groups patterns by type, synthesizes higher-order insights
    /// from groups with 2+ patterns. Drains the queue after processing.
    /// Returns the syntheses produced.
    pub fn process_queue(&mut self) -> Vec<DreamSynthesis> {
        if self.pending.len() < 2 {
            self.pending.clear();
            return Vec::new();
        }

        // Group patterns by type
        let mut by_type: HashMap<String, Vec<&QueuedPattern>> = HashMap::new();
        for pattern in &self.pending {
            by_type
                .entry(pattern.pattern_type.clone())
                .or_default()
                .push(pattern);
        }

        // Synthesize within each type group
        let mut new_syntheses = Vec::new();
        for (ptype, patterns) in by_type {
            if patterns.len() >= 2 {
                let synthesis = DreamSynthesis {
                    pattern_type: ptype.clone(),
                    source_count: patterns.len(),
                    synthesis: format!(
                        "Combined {} {} patterns: {}",
                        patterns.len(),
                        ptype,
                        patterns
                            .iter()
                            .map(|p| p.description.as_str())
                            .collect::<Vec<_>>()
                            .join("; ")
                    ),
                    produced_at: 0.0,
                };
                new_syntheses.push(synthesis);
            }
        }

        // Record syntheses and drain queue
        self.syntheses.extend(new_syntheses.clone());
        self.pending.clear();

        new_syntheses
    }

    /// Get all syntheses ever produced.
    #[must_use]
    pub fn syntheses(&self) -> &[DreamSynthesis] {
        &self.syntheses
    }

    /// Get pending patterns (without draining).
    #[must_use]
    pub fn pending(&self) -> &[QueuedPattern] {
        &self.pending
    }

    /// Get a summary of the bridge state.
    #[must_use]
    pub fn summary(&self) -> BridgeSummary {
        BridgeSummary {
            pending_patterns: self.pending.len(),
            total_syntheses: self.syntheses.len(),
        }
    }

    /// Clear all state (pending + syntheses).
    pub fn clear(&mut self) {
        self.pending.clear();
        self.syntheses.clear();
    }
}

impl Default for PatternDreamBridge {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn new_bridge_is_empty() {
        let bridge = PatternDreamBridge::new();
        assert_eq!(bridge.pending_count(), 0);
        assert_eq!(bridge.synthesis_count(), 0);
    }

    #[test]
    fn queue_pattern_increases_count() {
        let mut bridge = PatternDreamBridge::new();
        bridge.queue("association", "found link between codex and research");
        assert_eq!(bridge.pending_count(), 1);
    }

    #[test]
    fn queue_pattern_with_metadata() {
        let mut bridge = PatternDreamBridge::new();
        let pattern = QueuedPattern::new("anomaly", "unusual memory spike")
            .with_metadata("galaxy", "codex")
            .with_metadata("confidence", "0.85");
        bridge.queue_pattern(pattern);
        assert_eq!(bridge.pending_count(), 1);
        assert_eq!(bridge.pending()[0].metadata.len(), 2);
    }

    #[test]
    fn process_queue_with_less_than_two_returns_empty() {
        let mut bridge = PatternDreamBridge::new();
        bridge.queue("association", "single pattern");
        let result = bridge.process_queue();
        assert!(result.is_empty());
        assert_eq!(bridge.pending_count(), 0); // queue drained
    }

    #[test]
    fn process_queue_groups_by_type() {
        let mut bridge = PatternDreamBridge::new();
        bridge.queue("association", "link A");
        bridge.queue("association", "link B");
        bridge.queue("constellation", "cluster X");
        bridge.queue("constellation", "cluster Y");
        bridge.queue("anomaly", "spike Z");

        let result = bridge.process_queue();
        // Only groups with 2+ patterns produce syntheses
        assert_eq!(result.len(), 2); // "association" and "constellation"
        assert_eq!(bridge.synthesis_count(), 2);
        assert_eq!(bridge.pending_count(), 0); // queue drained
    }

    #[test]
    fn process_queue_synthesis_contains_pattern_count() {
        let mut bridge = PatternDreamBridge::new();
        bridge.queue("association", "link A");
        bridge.queue("association", "link B");
        bridge.queue("association", "link C");

        let result = bridge.process_queue();
        assert_eq!(result.len(), 1);
        assert_eq!(result[0].source_count, 3);
        assert_eq!(result[0].pattern_type, "association");
        assert!(result[0].synthesis.contains('3'));
    }

    #[test]
    fn process_queue_drains_even_when_no_syntheses() {
        let mut bridge = PatternDreamBridge::new();
        bridge.queue("type_a", "pattern 1");
        bridge.queue("type_b", "pattern 2");
        // Different types, each with only 1 pattern → no syntheses
        let result = bridge.process_queue();
        assert!(result.is_empty());
        assert_eq!(bridge.pending_count(), 0);
    }

    #[test]
    fn syntheses_accumulate_across_cycles() {
        let mut bridge = PatternDreamBridge::new();

        // First cycle
        bridge.queue("association", "link A");
        bridge.queue("association", "link B");
        bridge.process_queue();
        assert_eq!(bridge.synthesis_count(), 1);

        // Second cycle
        bridge.queue("constellation", "cluster X");
        bridge.queue("constellation", "cluster Y");
        bridge.process_queue();
        assert_eq!(bridge.synthesis_count(), 2);
    }

    #[test]
    fn summary_reflects_state() {
        let mut bridge = PatternDreamBridge::new();
        bridge.queue("association", "link A");
        bridge.queue("association", "link B");

        let summary = bridge.summary();
        assert_eq!(summary.pending_patterns, 2);
        assert_eq!(summary.total_syntheses, 0);

        bridge.process_queue();

        let summary = bridge.summary();
        assert_eq!(summary.pending_patterns, 0);
        assert_eq!(summary.total_syntheses, 1);
    }

    #[test]
    fn clear_resets_all_state() {
        let mut bridge = PatternDreamBridge::new();
        bridge.queue("association", "link A");
        bridge.queue("association", "link B");
        bridge.process_queue();

        assert!(bridge.pending_count() > 0 || bridge.synthesis_count() > 0);

        bridge.clear();
        assert_eq!(bridge.pending_count(), 0);
        assert_eq!(bridge.synthesis_count(), 0);
    }

    #[test]
    fn pending_returns_queued_patterns() {
        let mut bridge = PatternDreamBridge::new();
        bridge.queue("anomaly", "spike in codex");
        let pending = bridge.pending();
        assert_eq!(pending.len(), 1);
        assert_eq!(pending[0].pattern_type, "anomaly");
        assert_eq!(pending[0].description, "spike in codex");
    }

    #[test]
    fn syntheses_returns_all_produced() {
        let mut bridge = PatternDreamBridge::new();
        bridge.queue("type_a", "p1");
        bridge.queue("type_a", "p2");
        bridge.queue("type_b", "p3");
        bridge.queue("type_b", "p4");
        bridge.process_queue();

        let all = bridge.syntheses();
        assert_eq!(all.len(), 2);
    }

    #[test]
    fn queued_pattern_new_with_metadata_chaining() {
        let pattern = QueuedPattern::new("test", "desc")
            .with_metadata("a", "1")
            .with_metadata("b", "2")
            .with_metadata("c", "3");
        assert_eq!(pattern.metadata.len(), 3);
        assert_eq!(pattern.metadata.get("a"), Some(&"1".to_string()));
    }

    #[test]
    fn queue_cap_drops_excess_patterns() {
        let mut bridge = PatternDreamBridge::with_max_pending(3);
        assert!(bridge.queue_pattern(QueuedPattern::new("a", "p1")));
        assert!(bridge.queue_pattern(QueuedPattern::new("a", "p2")));
        assert!(bridge.queue_pattern(QueuedPattern::new("a", "p3")));
        assert!(
            !bridge.queue_pattern(QueuedPattern::new("a", "p4")),
            "Queue full, should drop"
        );
        assert_eq!(bridge.pending_count(), 3);
    }
}
