//! World Model — LLM-based state prediction for the Imagination Engine.
//!
//! Following ITP (Imagine-then-Plan) and SimuRA, the bicameral LLM hemispheres
//! serve as a text-based world model. The left hemisphere (deterministic, low
//! temperature) predicts likely outcomes; the right hemisphere (creative, high
//! temperature) generates diverse alternative scenarios.
//!
//! This module implements the "System II" simulative reasoning layer from
//! SR²AM — it predicts "what happens if I take action X in state Y?"

#![allow(clippy::cast_precision_loss)]

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::hash::{Hash, Hasher};
use std::sync::{Arc, Mutex};
use std::time::Instant;

use crate::router::TierHandler;

/// A predicted outcome from the world model.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PredictedState {
    /// Natural language description of predicted outcome.
    pub description: String,
    /// Confidence in prediction (0.0–1.0).
    pub confidence: f32,
    /// Key changes from current state.
    pub changes: Vec<String>,
    /// Risk factors identified.
    pub risks: Vec<String>,
    /// Goal progress estimate (0.0–1.0).
    pub goal_progress: f32,
}

impl PredictedState {
    /// Create a minimal predicted state with just a description and confidence.
    #[must_use]
    pub const fn new(description: String, confidence: f32) -> Self {
        Self {
            description,
            confidence,
            changes: Vec::new(),
            risks: Vec::new(),
            goal_progress: 0.0,
        }
    }

    /// Whether this prediction is high-confidence (≥ 0.7).
    #[must_use]
    pub const fn is_confident(&self) -> bool {
        self.confidence >= 0.7
    }

    /// Whether this prediction has significant risk (any risk factor present).
    #[must_use]
    pub fn has_risk(&self) -> bool {
        !self.risks.is_empty()
    }
}

/// Which hemisphere produced a prediction.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum PredictionSource {
    /// Left hemisphere (deterministic, analytical).
    Left,
    /// Right hemisphere (creative, stochastic).
    Right,
    /// Consensus from both hemispheres.
    Consensus,
}

/// Result of a dual-mind prediction (DMWM-inspired).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DualPrediction {
    /// Left hemisphere prediction.
    pub left: PredictedState,
    /// Right hemisphere prediction (if available).
    pub right: Option<PredictedState>,
    /// Consensus prediction (if both agree sufficiently).
    pub consensus: Option<PredictedState>,
    /// Whether the hemispheres agree (consensus reached).
    pub agrees: bool,
    /// Source of the final prediction.
    pub source: PredictionSource,
}

impl DualPrediction {
    /// Get the best prediction from this dual prediction.
    ///
    /// Prefers consensus, then left, then right.
    #[must_use]
    pub fn best(&self) -> &PredictedState {
        self.consensus
            .as_ref()
            .or(Some(&self.left))
            .or(self.right.as_ref())
            .unwrap_or(&self.left)
    }

    /// Whether consensus was reached.
    #[must_use]
    pub const fn has_consensus(&self) -> bool {
        self.consensus.is_some()
    }
}

// ── L1 Prediction Cache ──────────────────────────────────────────────

/// Cache statistics for the L1 prediction cache.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct CacheStats {
    /// Total cache lookups.
    pub hits: u64,
    /// Total cache misses (triggered L2 call).
    pub misses: u64,
    /// Total entries currently in the cache.
    pub entries: usize,
}

impl CacheStats {
    /// Hit rate as a fraction (0.0–1.0).
    #[must_use]
    pub fn hit_rate(&self) -> f64 {
        let total = self.hits + self.misses;
        if total == 0 {
            0.0
        } else {
            self.hits as f64 / total as f64
        }
    }
}

/// L1 in-memory cache for world model predictions.
///
/// Avoids redundant LLM (L2) calls when the same (state, action, goal)
/// combination is predicted multiple times — common during rollouts,
/// scenario evaluation, and Monte Carlo simulation.
///
/// Entries expire after `ttl_secs` to prevent stale predictions when
/// the underlying state may have changed (e.g. after memory updates).
pub struct PredictionCache {
    entries: HashMap<u64, (DualPrediction, Instant)>,
    ttl_secs: u64,
    max_entries: usize,
    stats: CacheStats,
}

impl PredictionCache {
    /// Create a new prediction cache.
    ///
    /// - `ttl_secs`: Time-to-live for cache entries (0 = never expire).
    /// - `max_entries`: Maximum number of cached predictions (LRU eviction when full).
    #[must_use]
    pub fn new(ttl_secs: u64, max_entries: usize) -> Self {
        Self {
            entries: HashMap::new(),
            ttl_secs,
            max_entries,
            stats: CacheStats::default(),
        }
    }

    /// Compute a cache key from (state, action, goal).
    fn cache_key(state: &str, action: &str, goal: &str) -> u64 {
        let mut hasher = std::collections::hash_map::DefaultHasher::new();
        state.hash(&mut hasher);
        action.hash(&mut hasher);
        goal.hash(&mut hasher);
        hasher.finish()
    }

    /// Look up a cached prediction.
    fn get(&mut self, state: &str, action: &str, goal: &str) -> Option<DualPrediction> {
        let key = Self::cache_key(state, action, goal);
        let hit = self.entries.get(&key).and_then(|(pred, ts)| {
            if self.ttl_secs == 0 || ts.elapsed().as_secs() < self.ttl_secs {
                Some(pred.clone())
            } else {
                None
            }
        });
        if hit.is_some() {
            self.stats.hits += 1;
        } else {
            // Remove expired entry if present
            if self.entries.contains_key(&key) {
                self.entries.remove(&key);
            }
            self.stats.misses += 1;
        }
        hit
    }

    /// Store a prediction in the cache.
    fn put(&mut self, state: &str, action: &str, goal: &str, prediction: &DualPrediction) {
        // Evict oldest entries if at capacity (simple FIFO, not true LRU)
        if self.entries.len() >= self.max_entries {
            if let Some(&oldest_key) = self
                .entries
                .iter()
                .min_by_key(|(_, (_, ts))| *ts)
                .map(|(k, _)| k)
            {
                self.entries.remove(&oldest_key);
            }
        }
        let key = Self::cache_key(state, action, goal);
        self.entries
            .insert(key, (prediction.clone(), Instant::now()));
        self.stats.entries = self.entries.len();
    }

    /// Get cache statistics.
    #[must_use]
    pub fn stats(&self) -> CacheStats {
        self.stats.clone()
    }

    /// Clear all cached predictions.
    pub fn clear(&mut self) {
        self.entries.clear();
        self.stats.entries = 0;
    }
}

impl Default for PredictionCache {
    fn default() -> Self {
        Self::new(300, 512) // 5-minute TTL, 512 entries
    }
}

/// The LLM-based world model.
///
/// Uses the existing bicameral hemispheres to predict outcomes:
/// - Left hemisphere (SmolLM2, temp 0.2) for deterministic state prediction
/// - Right hemisphere (Llama 3.2, temp 0.7) for diverse alternative generation
///
/// Following DMWM (NeurIPS 2025), both hemispheres predict independently,
/// and a consensus gate checks for logical consistency.
pub struct WorldModel {
    /// Left hemisphere handler (deterministic prediction).
    left: Arc<dyn TierHandler>,
    /// Right hemisphere handler (creative alternatives).
    right: Option<Arc<dyn TierHandler>>,
    /// Consensus threshold — if left/right confidence difference exceeds this,
    /// we consider them in disagreement.
    consensus_threshold: f32,
    /// L1 prediction cache (avoids redundant LLM calls).
    cache: Mutex<PredictionCache>,
}

impl WorldModel {
    /// Create a new world model with explicit handlers.
    #[must_use]
    pub fn new(left: Arc<dyn TierHandler>, right: Option<Arc<dyn TierHandler>>) -> Self {
        Self {
            left,
            right,
            consensus_threshold: 0.3,
            cache: Mutex::new(PredictionCache::default()),
        }
    }

    /// Set the consensus threshold.
    #[must_use]
    pub const fn with_consensus_threshold(mut self, threshold: f32) -> Self {
        self.consensus_threshold = threshold;
        self
    }

    /// Configure the L1 cache (TTL in seconds, max entries).
    #[must_use]
    pub fn with_cache_config(mut self, ttl_secs: u64, max_entries: usize) -> Self {
        self.cache = Mutex::new(PredictionCache::new(ttl_secs, max_entries));
        self
    }

    /// Predict the outcome of taking `action` in `state`.
    ///
    /// Uses the left hemisphere for deterministic prediction.
    /// If a right hemisphere is available, also generates a creative alternative
    /// and checks for consensus (DMWM dual-mind consistency).
    #[must_use]
    pub fn predict(&self, state: &str, action: &str, goal: &str) -> DualPrediction {
        // L1 cache check — avoid redundant LLM calls
        if let Ok(mut cache) = self.cache.lock() {
            if let Some(cached) = cache.get(state, action, goal) {
                tracing::debug!("world model: L1 cache hit");
                return cached;
            }
        }

        // L2 — LLM prediction
        let prompt = build_predict_prompt(state, action, goal);

        let left_result = self.left.handle(&prompt, 256).unwrap_or_else(|e| {
            tracing::warn!(error = %e, "world model left hemisphere failed");
            (format!("Unable to predict: {e}"), 0.0_f32)
        });

        let left = parse_prediction(&left_result.0, left_result.1);

        let right_result = self.right.as_ref().map(|h| {
            h.handle(&prompt, 256).unwrap_or_else(|e| {
                tracing::warn!(error = %e, "world model right hemisphere failed");
                (format!("Unable to predict: {e}"), 0.0_f32)
            })
        });

        let right = right_result.map(|(text, conf)| parse_prediction(&text, conf));

        // Consensus check (DMWM-inspired)
        let (agrees, consensus, source) = if let Some(ref right_pred) = right {
            let conf_diff = (left.confidence - right_pred.confidence).abs();
            if conf_diff <= self.consensus_threshold {
                // Hemispheres agree — merge predictions
                let merged = merge_predictions(&left, right_pred);
                (true, Some(merged), PredictionSource::Consensus)
            } else {
                (false, None, PredictionSource::Left)
            }
        } else {
            // No right hemisphere — left-only
            (true, None, PredictionSource::Left)
        };

        let prediction = DualPrediction {
            left,
            right,
            consensus,
            agrees,
            source,
        };

        // Store in L1 cache
        if let Ok(mut cache) = self.cache.lock() {
            cache.put(state, action, goal, &prediction);
        }

        prediction
    }

    /// Roll out K steps of imagination.
    ///
    /// Starting from `initial_state`, applies each action in sequence,
    /// predicting the state after each step. Each prediction feeds into
    /// the next as the new current state.
    #[must_use]
    pub fn rollout(
        &self,
        initial_state: &str,
        actions: &[String],
        goal: &str,
    ) -> Vec<PredictedState> {
        let mut trajectory = Vec::with_capacity(actions.len());
        let mut current_state = initial_state.to_string();

        for action in actions {
            let prediction = self.predict(&current_state, action, goal);
            let best = prediction.best().clone();

            // Update state description for next step
            current_state.clone_from(&best.description);
            trajectory.push(best);
        }

        trajectory
    }

    /// Generate alternative actions for a given state and goal.
    ///
    /// Uses the right hemisphere (creative) to propose diverse candidate actions.
    /// Falls back to the left hemisphere if no right is available.
    #[must_use]
    pub fn generate_actions(&self, state: &str, goal: &str, n: usize) -> Vec<String> {
        let handler = self.right.as_ref().unwrap_or(&self.left);
        let prompt = build_generate_prompt(state, goal, n);

        match handler.handle(&prompt, 256) {
            Ok((text, _)) => parse_action_list(&text, n),
            Err(e) => {
                tracing::warn!(error = %e, "action generation failed");
                Vec::new()
            }
        }
    }

    /// Check if the right hemisphere is available.
    #[must_use]
    pub const fn has_right(&self) -> bool {
        self.right.is_some()
    }

    /// Get the name of the left hemisphere handler.
    #[must_use]
    pub fn left_name(&self) -> &'static str {
        self.left.name()
    }

    /// Get the name of the right hemisphere handler, if available.
    #[must_use]
    pub fn right_name(&self) -> Option<&'static str> {
        self.right.as_ref().map(|h| h.name())
    }

    /// Get L1 cache statistics.
    #[must_use]
    pub fn cache_stats(&self) -> CacheStats {
        self.cache.lock().map(|c| c.stats()).unwrap_or_default()
    }

    /// Clear the L1 prediction cache.
    pub fn clear_cache(&self) {
        if let Ok(mut cache) = self.cache.lock() {
            cache.clear();
        }
    }
}

// ── Prompt Construction ───────────────────────────────────────────────

fn build_predict_prompt(state: &str, action: &str, goal: &str) -> String {
    format!(
        "You are a world model simulator. Predict what happens if the following action is taken.\n\
         \n\
         Current state: {state}\n\
         Proposed action: {action}\n\
         Goal: {goal}\n\
         \n\
         Predict the outcome. Format your response as:\n\
         DESCRIPTION: <one paragraph describing the predicted outcome>\n\
         CHANGES: <comma-separated list of key changes>\n\
         RISKS: <comma-separated list of risk factors, or 'none'>\n\
         PROGRESS: <float 0.0-1.0 estimating goal progress after this action>\n\
         CONFIDENCE: <float 0.0-1.0>"
    )
}

fn build_generate_prompt(state: &str, goal: &str, n: usize) -> String {
    format!(
        "You are a creative action planner. Given the current state and goal, propose {n} distinct actions.\n\
         \n\
         Current state: {state}\n\
         Goal: {goal}\n\
         \n\
         List {n} different actions that could be taken. One per line, numbered."
    )
}

// ── Parsing ───────────────────────────────────────────────────────────

fn parse_prediction(text: &str, confidence: f32) -> PredictedState {
    let mut description = String::new();
    let mut changes = Vec::new();
    let mut risks = Vec::new();
    let mut goal_progress = 0.0_f32;
    let mut parsed_confidence = confidence;

    for line in text.lines() {
        let trimmed = line.trim();
        if let Some(rest) = trimmed.strip_prefix("DESCRIPTION:") {
            description = rest.trim().to_string();
        } else if let Some(rest) = trimmed.strip_prefix("CHANGES:") {
            changes = rest
                .trim()
                .split(',')
                .map(|s| s.trim().to_string())
                .filter(|s| !s.is_empty() && s != "none")
                .collect();
        } else if let Some(rest) = trimmed.strip_prefix("RISKS:") {
            risks = rest
                .trim()
                .split(',')
                .map(|s| s.trim().to_string())
                .filter(|s| !s.is_empty() && s.to_lowercase() != "none")
                .collect();
        } else if let Some(rest) = trimmed.strip_prefix("PROGRESS:") {
            goal_progress = rest.trim().parse::<f32>().unwrap_or(0.0).clamp(0.0, 1.0);
        } else if let Some(rest) = trimmed.strip_prefix("CONFIDENCE:") {
            parsed_confidence = rest
                .trim()
                .parse::<f32>()
                .unwrap_or(confidence)
                .clamp(0.0, 1.0);
        }
    }

    // If no description was parsed, use the raw text
    if description.is_empty() {
        description = text.trim().to_string();
    }

    PredictedState {
        description,
        confidence: parsed_confidence,
        changes,
        risks,
        goal_progress,
    }
}

fn parse_action_list(text: &str, n: usize) -> Vec<String> {
    text.lines()
        .filter_map(|line| {
            let trimmed = line.trim();
            // Skip empty lines
            if trimmed.is_empty() {
                return None;
            }
            // Strip numbering like "1. ", "2. ", etc.
            let action = if let Some(pos) = trimmed.find(". ") {
                if trimmed[..pos].chars().all(|c| c.is_ascii_digit()) {
                    trimmed[pos + 2..].to_string()
                } else {
                    trimmed.to_string()
                }
            } else {
                trimmed.to_string()
            };
            Some(action)
        })
        .take(n)
        .collect()
}

fn merge_predictions(left: &PredictedState, right: &PredictedState) -> PredictedState {
    // Merge: take the higher-confidence description, union changes and risks,
    // average goal progress, take max confidence.
    let (description, confidence) = if left.confidence >= right.confidence {
        (left.description.clone(), left.confidence)
    } else {
        (right.description.clone(), right.confidence)
    };

    let mut changes = left.changes.clone();
    for c in &right.changes {
        if !changes.contains(c) {
            changes.push(c.clone());
        }
    }

    let mut risks = left.risks.clone();
    for r in &right.risks {
        if !risks.contains(r) {
            risks.push(r.clone());
        }
    }

    PredictedState {
        description,
        confidence,
        changes,
        risks,
        goal_progress: f32::midpoint(left.goal_progress, right.goal_progress),
    }
}

// ── Stub Handler for Testing ──────────────────────────────────────────

/// A stub tier handler for testing the world model without real LLMs.
pub struct StubWorldModelHandler {
    name: &'static str,
    deterministic: bool,
}

impl StubWorldModelHandler {
    /// Create a left-style stub (deterministic).
    #[must_use]
    pub const fn left() -> Self {
        Self {
            name: "stub-left",
            deterministic: true,
        }
    }

    /// Create a right-style stub (creative).
    #[must_use]
    pub const fn right() -> Self {
        Self {
            name: "stub-right",
            deterministic: false,
        }
    }
}

impl TierHandler for StubWorldModelHandler {
    fn handle(&self, _prompt: &str, _max_tokens: usize) -> Result<(String, f32), String> {
        if self.deterministic {
            Ok((
                "DESCRIPTION: Based on the current state, the action will proceed as expected with predictable outcomes.\n\
                     CHANGES: state updated, resources consumed\n\
                     RISKS: none\n\
                     PROGRESS: 0.5\n\
                     CONFIDENCE: 0.8".to_string(),
                0.8,
            ))
        } else {
            Ok((
                "DESCRIPTION: An alternative creative approach yields unexpected but potentially valuable results.\n\
                     CHANGES: novel path discovered, new capability unlocked\n\
                     RISKS: uncertainty in outcome, resource overhead\n\
                     PROGRESS: 0.6\n\
                     CONFIDENCE: 0.6".to_string(),
                0.6,
            ))
        }
    }

    fn name(&self) -> &'static str {
        self.name
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn make_world_model() -> WorldModel {
        WorldModel::new(
            Arc::new(StubWorldModelHandler::left()),
            Some(Arc::new(StubWorldModelHandler::right())),
        )
    }

    fn make_left_only() -> WorldModel {
        WorldModel::new(Arc::new(StubWorldModelHandler::left()), None)
    }

    // ── PredictedState tests ───────────────────────────────────────────

    #[test]
    fn predicted_state_new_minimal() {
        let ps = PredictedState::new("test".into(), 0.5);
        assert_eq!(ps.description, "test");
        assert_eq!(ps.confidence, 0.5);
        assert!(ps.changes.is_empty());
        assert!(ps.risks.is_empty());
        assert_eq!(ps.goal_progress, 0.0);
    }

    #[test]
    fn predicted_state_is_confident() {
        assert!(PredictedState::new("x".into(), 0.7).is_confident());
        assert!(PredictedState::new("x".into(), 0.9).is_confident());
        assert!(!PredictedState::new("x".into(), 0.69).is_confident());
    }

    #[test]
    fn predicted_state_has_risk() {
        let mut ps = PredictedState::new("x".into(), 0.5);
        assert!(!ps.has_risk());
        ps.risks.push("data loss".into());
        assert!(ps.has_risk());
    }

    // ── DualPrediction tests ───────────────────────────────────────────

    #[test]
    fn dual_prediction_best_prefers_consensus() {
        let left = PredictedState::new("left".into(), 0.7);
        let right = PredictedState::new("right".into(), 0.6);
        let consensus = PredictedState::new("merged".into(), 0.8);
        let dp = DualPrediction {
            left,
            right: Some(right),
            consensus: Some(consensus),
            agrees: true,
            source: PredictionSource::Consensus,
        };
        assert_eq!(dp.best().description, "merged");
        assert!(dp.has_consensus());
    }

    #[test]
    fn dual_prediction_best_falls_to_left() {
        let left = PredictedState::new("left".into(), 0.7);
        let dp = DualPrediction {
            left,
            right: None,
            consensus: None,
            agrees: true,
            source: PredictionSource::Left,
        };
        assert_eq!(dp.best().description, "left");
        assert!(!dp.has_consensus());
    }

    // ── WorldModel predict tests ───────────────────────────────────────

    #[test]
    fn predict_with_both_hemispheres() {
        let wm = make_world_model();
        let result = wm.predict("idle", "run task", "complete task");
        assert!(!result.left.description.is_empty());
        assert!(result.right.is_some());
        // Stub confidences are 0.8 and 0.6, diff = 0.2 <= 0.3 threshold
        assert!(result.agrees);
        assert!(result.consensus.is_some());
        assert_eq!(result.source, PredictionSource::Consensus);
    }

    #[test]
    fn predict_left_only() {
        let wm = make_left_only();
        let result = wm.predict("idle", "run task", "complete task");
        assert!(!result.left.description.is_empty());
        assert!(result.right.is_none());
        assert!(result.agrees);
        assert!(result.consensus.is_none());
        assert_eq!(result.source, PredictionSource::Left);
    }

    #[test]
    fn predict_parses_structured_output() {
        let wm = make_left_only();
        let result = wm.predict("state", "action", "goal");
        let best = result.best();
        assert!(best.confidence > 0.0);
        assert!(best.goal_progress > 0.0);
    }

    // ── Rollout tests ──────────────────────────────────────────────────

    #[test]
    fn rollout_multi_step() {
        let wm = make_left_only();
        let actions = vec!["step1".into(), "step2".into(), "step3".into()];
        let trajectory = wm.rollout("initial", &actions, "goal");
        assert_eq!(trajectory.len(), 3);
        // Each step should have a non-empty description
        for ps in &trajectory {
            assert!(!ps.description.is_empty());
        }
    }

    #[test]
    fn rollout_empty_actions() {
        let wm = make_left_only();
        let trajectory = wm.rollout("initial", &[], "goal");
        assert!(trajectory.is_empty());
    }

    #[test]
    fn rollout_single_step() {
        let wm = make_left_only();
        let trajectory = wm.rollout("initial", &["act".into()], "goal");
        assert_eq!(trajectory.len(), 1);
    }

    // ── Action generation tests ────────────────────────────────────────

    #[test]
    fn generate_actions_with_right() {
        let wm = make_world_model();
        let actions = wm.generate_actions("state", "goal", 3);
        assert!(!actions.is_empty());
    }

    #[test]
    fn generate_actions_left_only() {
        let wm = make_left_only();
        let actions = wm.generate_actions("state", "goal", 2);
        assert!(!actions.is_empty());
    }

    // ── Consensus threshold tests ──────────────────────────────────────

    #[test]
    fn consensus_threshold_low_disagrees() {
        let wm = WorldModel::new(
            Arc::new(StubWorldModelHandler::left()),
            Some(Arc::new(StubWorldModelHandler::right())),
        )
        .with_consensus_threshold(0.1);
        // Stub confidences: 0.8 vs 0.6, diff = 0.2 > 0.1 threshold
        let result = wm.predict("state", "action", "goal");
        assert!(!result.agrees);
        assert!(result.consensus.is_none());
    }

    #[test]
    fn consensus_threshold_high_agrees() {
        let wm = WorldModel::new(
            Arc::new(StubWorldModelHandler::left()),
            Some(Arc::new(StubWorldModelHandler::right())),
        )
        .with_consensus_threshold(0.5);
        // diff = 0.2 <= 0.5
        let result = wm.predict("state", "action", "goal");
        assert!(result.agrees);
        assert!(result.consensus.is_some());
    }

    // ── Parsing tests ──────────────────────────────────────────────────

    #[test]
    fn parse_prediction_full_format() {
        let text = "DESCRIPTION: The task completes successfully.\n\
                    CHANGES: output generated, state updated\n\
                    RISKS: timeout, resource exhaustion\n\
                    PROGRESS: 0.75\n\
                    CONFIDENCE: 0.9";
        let ps = parse_prediction(text, 0.5);
        assert_eq!(ps.description, "The task completes successfully.");
        assert_eq!(ps.changes.len(), 2);
        assert_eq!(ps.risks.len(), 2);
        assert!((ps.goal_progress - 0.75).abs() < 0.01);
        assert!((ps.confidence - 0.9).abs() < 0.01);
    }

    #[test]
    fn parse_prediction_no_risks() {
        let text = "DESCRIPTION: Safe operation.\nCHANGES: state updated\nRISKS: none\nPROGRESS: 0.5\nCONFIDENCE: 0.7";
        let ps = parse_prediction(text, 0.5);
        assert!(ps.risks.is_empty());
    }

    #[test]
    fn parse_prediction_fallback_to_raw() {
        let text = "Just some raw text without structure.";
        let ps = parse_prediction(text, 0.6);
        assert_eq!(ps.description, "Just some raw text without structure.");
        assert!((ps.confidence - 0.6).abs() < 0.01);
    }

    #[test]
    fn parse_action_list_numbered() {
        let text = "1. First action\n2. Second action\n3. Third action";
        let actions = parse_action_list(text, 3);
        assert_eq!(actions.len(), 3);
        assert_eq!(actions[0], "First action");
        assert_eq!(actions[1], "Second action");
    }

    #[test]
    fn parse_action_list_unnumbered() {
        let text = "do thing A\ndo thing B\ndo thing C";
        let actions = parse_action_list(text, 2);
        assert_eq!(actions.len(), 2);
    }

    #[test]
    fn parse_action_list_skips_empty() {
        let text = "1. Action one\n\n2. Action two";
        let actions = parse_action_list(text, 5);
        assert_eq!(actions.len(), 2);
    }

    // ── Merge predictions tests ────────────────────────────────────────

    #[test]
    fn merge_takes_higher_confidence() {
        let left = PredictedState {
            description: "left desc".into(),
            confidence: 0.9,
            changes: vec!["a".into()],
            risks: vec!["r1".into()],
            goal_progress: 0.6,
        };
        let right = PredictedState {
            description: "right desc".into(),
            confidence: 0.7,
            changes: vec!["b".into()],
            risks: vec!["r2".into()],
            goal_progress: 0.4,
        };
        let merged = merge_predictions(&left, &right);
        assert_eq!(merged.description, "left desc");
        assert!((merged.confidence - 0.9).abs() < 0.01);
        assert_eq!(merged.changes.len(), 2);
        assert_eq!(merged.risks.len(), 2);
        assert!((merged.goal_progress - 0.5).abs() < 0.01);
    }

    #[test]
    fn merge_deduplicates_changes() {
        let left = PredictedState {
            description: "left".into(),
            confidence: 0.8,
            changes: vec!["a".into(), "b".into()],
            risks: vec![],
            goal_progress: 0.5,
        };
        let right = PredictedState {
            description: "right".into(),
            confidence: 0.6,
            changes: vec!["b".into(), "c".into()],
            risks: vec![],
            goal_progress: 0.5,
        };
        let merged = merge_predictions(&left, &right);
        assert_eq!(merged.changes, vec!["a", "b", "c"]);
    }

    // ── Stub handler tests ─────────────────────────────────────────────

    #[test]
    fn stub_left_returns_high_confidence() {
        let handler = StubWorldModelHandler::left();
        let (text, conf) = handler.handle("test", 100).unwrap();
        assert!(conf > 0.7);
        assert!(text.contains("DESCRIPTION:"));
    }

    #[test]
    fn stub_right_returns_lower_confidence() {
        let handler = StubWorldModelHandler::right();
        let (text, conf) = handler.handle("test", 100).unwrap();
        assert!(conf < 0.8);
        assert!(text.contains("DESCRIPTION:"));
    }

    #[test]
    fn stub_names() {
        assert_eq!(StubWorldModelHandler::left().name(), "stub-left");
        assert_eq!(StubWorldModelHandler::right().name(), "stub-right");
    }

    // ── WorldModel metadata tests ──────────────────────────────────────

    #[test]
    fn world_model_has_right() {
        assert!(make_world_model().has_right());
        assert!(!make_left_only().has_right());
    }

    #[test]
    fn world_model_names() {
        let wm = make_world_model();
        assert_eq!(wm.left_name(), "stub-left");
        assert_eq!(wm.right_name(), Some("stub-right"));
    }

    #[test]
    fn world_model_left_only_names() {
        let wm = make_left_only();
        assert_eq!(wm.left_name(), "stub-left");
        assert_eq!(wm.right_name(), None);
    }

    // ── L1 Cache tests ─────────────────────────────────────────────────

    #[test]
    fn cache_hit_on_repeat_prediction() {
        let wm = make_left_only();
        // First call: L2 miss
        let p1 = wm.predict("state-a", "action-b", "goal-c");
        let stats_after_first = wm.cache_stats();
        assert_eq!(stats_after_first.misses, 1);
        assert_eq!(stats_after_first.hits, 0);

        // Second call: L1 hit — same prediction
        let p2 = wm.predict("state-a", "action-b", "goal-c");
        let stats_after_second = wm.cache_stats();
        assert_eq!(stats_after_second.misses, 1);
        assert_eq!(stats_after_second.hits, 1);

        // Cached prediction should be identical
        assert_eq!(p1.left.description, p2.left.description);
    }

    #[test]
    fn cache_miss_on_different_inputs() {
        let wm = make_left_only();
        let _ = wm.predict("state-a", "action-b", "goal-c");
        let _ = wm.predict("state-x", "action-b", "goal-c");
        let stats = wm.cache_stats();
        assert_eq!(stats.misses, 2);
        assert_eq!(stats.hits, 0);
    }

    #[test]
    fn cache_hit_rate_calculation() {
        let wm = make_left_only();
        let _ = wm.predict("s", "a", "g"); // miss
        let _ = wm.predict("s", "a", "g"); // hit
        let _ = wm.predict("s", "a", "g"); // hit
        let stats = wm.cache_stats();
        assert_eq!(stats.hits, 2);
        assert_eq!(stats.misses, 1);
        assert!((stats.hit_rate() - 2.0 / 3.0).abs() < 0.01);
    }

    #[test]
    fn cache_clear_resets_entries() {
        let wm = make_left_only();
        let _ = wm.predict("s", "a", "g");
        assert_eq!(wm.cache_stats().entries, 1);
        wm.clear_cache();
        let stats = wm.cache_stats();
        assert_eq!(stats.entries, 0);
        // Stats (hits/misses) are not reset by clear
        assert_eq!(stats.misses, 1);
    }

    #[test]
    fn cache_eviction_when_full() {
        let wm = make_left_only().with_cache_config(0, 2); // no TTL, max 2 entries
        let _ = wm.predict("s1", "a", "g");
        let _ = wm.predict("s2", "a", "g");
        let _ = wm.predict("s3", "a", "g"); // should evict oldest
        let stats = wm.cache_stats();
        assert_eq!(stats.entries, 2);
    }

    #[test]
    fn cache_stats_empty_initially() {
        let wm = make_left_only();
        let stats = wm.cache_stats();
        assert_eq!(stats.hits, 0);
        assert_eq!(stats.misses, 0);
        assert_eq!(stats.entries, 0);
        assert_eq!(stats.hit_rate(), 0.0);
    }

    #[test]
    fn cache_with_custom_config() {
        let wm = make_left_only().with_cache_config(600, 128);
        let _ = wm.predict("s", "a", "g");
        let stats = wm.cache_stats();
        assert_eq!(stats.entries, 1);
        assert_eq!(stats.misses, 1);
    }

    #[test]
    fn cache_rollout_uses_cache() {
        // Rollout with repeated states should benefit from cache
        let wm = make_left_only();
        let actions = vec!["act".into(), "act".into(), "act".into()];
        let _ = wm.rollout("initial", &actions, "goal");
        // After rollout, we should have some cache entries
        let stats = wm.cache_stats();
        assert!(stats.entries > 0);
    }
}
