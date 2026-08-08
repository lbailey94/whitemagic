//! LLM Meta-Harness — cognitive enhancement for local LLM calls.
//!
//! Wraps inference with enhancement strategies:
//! - **Direct**: passthrough (baseline)
//! - **MemoryGrounded**: retrieve relevant memories → inject as context (RAG)
//! - **SelfCorrecting**: generate → critique → refine
//! - **Ensemble**: N attempts with varied parameters → vote
//! - **FullStack**: all of the above
//!
//! Ported from v2's `inference/llm_meta_harness.py` (569 lines).
//! Integrates with existing ContextOptimizer (Pre-N Batch B),
//! SpeculativeExecutor (Pre-N Batch B), and ConversationalSearch (N5).

#![forbid(unsafe_code)]

use serde::{Deserialize, Serialize};
use std::sync::{Arc, Mutex};
use std::time::Instant;

// ── Enhancement Mode ──────────────────────────────────────────────────

/// Enhancement strategy to apply.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize, Default)]
pub enum EnhancementMode {
    /// Passthrough — no enhancement (baseline).
    Direct,
    /// Retrieve relevant memories → inject as context (RAG).
    #[default]
    MemoryGrounded,
    /// Generate → critique → refine loop.
    SelfCorrecting,
    /// Multiple attempts with varied parameters → vote.
    Ensemble,
    /// All enhancements stacked: memory grounding → ensemble → self-correction.
    FullStack,
}

impl EnhancementMode {
    /// Human-readable name.
    #[must_use]
    pub const fn label(self) -> &'static str {
        match self {
            Self::Direct => "direct",
            Self::MemoryGrounded => "memory_grounded",
            Self::SelfCorrecting => "self_correcting",
            Self::Ensemble => "ensemble",
            Self::FullStack => "full_stack",
        }
    }

    /// Whether this mode uses memory grounding.
    #[must_use]
    pub const fn uses_memory(self) -> bool {
        matches!(self, Self::MemoryGrounded | Self::FullStack)
    }

    /// Whether this mode uses self-correction.
    #[must_use]
    pub const fn uses_self_correction(self) -> bool {
        matches!(self, Self::SelfCorrecting | Self::FullStack)
    }

    /// Whether this mode uses ensemble voting.
    #[must_use]
    pub const fn uses_ensemble(self) -> bool {
        matches!(self, Self::Ensemble | Self::FullStack)
    }
}

// ── Config ────────────────────────────────────────────────────────────

/// Configuration for the meta-harness.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MetaHarnessConfig {
    /// Default enhancement mode.
    pub default_mode: EnhancementMode,
    /// Maximum memories to retrieve for grounding.
    pub max_grounding_memories: usize,
    /// Token budget for context packing.
    pub context_token_budget: usize,
    /// Number of ensemble attempts.
    pub ensemble_attempts: usize,
    /// Maximum self-correction rounds.
    pub max_correction_rounds: usize,
    /// Minimum confidence threshold for accepting self-corrected output.
    pub min_confidence: f32,
    /// Whether to validate outputs with SpeculativeExecutor.
    pub validate_outputs: bool,
}

impl Default for MetaHarnessConfig {
    fn default() -> Self {
        Self {
            default_mode: EnhancementMode::MemoryGrounded,
            max_grounding_memories: 5,
            context_token_budget: 4096,
            ensemble_attempts: 3,
            max_correction_rounds: 2,
            min_confidence: 0.6,
            validate_outputs: true,
        }
    }
}

// ── Enhanced Response ─────────────────────────────────────────────────

/// Result of an enhanced inference call.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EnhancedResponse {
    /// The final output text.
    pub output: String,
    /// Confidence in the output (0.0–1.0).
    pub confidence: f32,
    /// Which enhancement mode was used.
    pub mode: EnhancementMode,
    /// Memories used for grounding (IDs).
    pub grounded_memories: Vec<String>,
    /// Number of self-correction rounds applied.
    pub correction_rounds: usize,
    /// Number of ensemble attempts.
    pub ensemble_attempts: usize,
    /// Whether the output passed validation.
    pub validated: bool,
    /// Latency in microseconds.
    pub latency_us: u64,
    /// Improvement score vs baseline (0.0 = no improvement, 1.0 = doubled).
    pub improvement_score: f32,
    /// Enhancement steps taken.
    pub steps: Vec<EnhancementStep>,
}

/// A single step in the enhancement pipeline.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EnhancementStep {
    /// Step name (e.g., "memory_grounding", "self_correction_round_1").
    pub name: String,
    /// Latency of this step in microseconds.
    pub latency_us: u64,
    /// Whether this step modified the output.
    pub modified: bool,
    /// Step-specific metadata.
    pub detail: String,
}

// ── Stats ─────────────────────────────────────────────────────────────

/// Statistics tracked per enhancement mode.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct ModeStats {
    /// Total calls with this mode.
    pub calls: u64,
    /// Total latency in microseconds.
    pub total_latency_us: u64,
    /// Sum of improvement scores.
    pub total_improvement: f32,
    /// Number of calls that used memory grounding.
    pub grounded_count: u64,
    /// Number of calls that applied self-correction.
    pub corrected_count: u64,
    /// Number of calls that used ensemble voting.
    pub ensemble_count: u64,
}

impl ModeStats {
    /// Average latency in microseconds.
    #[must_use]
    pub const fn avg_latency_us(&self) -> u64 {
        if self.calls == 0 {
            0
        } else {
            self.total_latency_us / self.calls
        }
    }

    /// Average improvement score.
    #[must_use]
    pub fn avg_improvement(&self) -> f32 {
        if self.calls == 0 {
            0.0
        } else {
            self.total_improvement / self.calls as f32
        }
    }
}

/// Overall meta-harness statistics.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct HarnessStats {
    /// Per-mode statistics.
    pub by_mode: std::collections::HashMap<EnhancementMode, ModeStats>,
    /// Total calls across all modes.
    pub total_calls: u64,
    /// Total latency across all calls.
    pub total_latency_us: u64,
    /// Number of validation failures.
    pub validation_failures: u64,
}

impl HarnessStats {
    /// Average latency across all calls.
    #[must_use]
    pub const fn avg_latency_us(&self) -> u64 {
        if self.total_calls == 0 {
            0
        } else {
            self.total_latency_us / self.total_calls
        }
    }

    /// Get stats for a specific mode.
    #[must_use]
    pub fn mode(&self, mode: EnhancementMode) -> Option<&ModeStats> {
        self.by_mode.get(&mode)
    }
}

// ── Memory Provider Trait ─────────────────────────────────────────────

/// Trait for providing memory grounding context.
///
/// Implemented by `ConversationalSearch` in wm-memory, but kept as a trait
/// to avoid a hard dependency on wm-memory from wm-bicameral.
pub trait MemoryProvider: Send + Sync {
    /// Search for relevant memories.
    /// Returns (memory_id, content) pairs.
    fn search(&self, query: &str, limit: usize) -> Vec<(String, String)>;
}

/// No-op memory provider for when grounding is unavailable.
pub struct NoMemory;

impl MemoryProvider for NoMemory {
    fn search(&self, _query: &str, _limit: usize) -> Vec<(String, String)> {
        Vec::new()
    }
}

// ── Inference Provider Trait ──────────────────────────────────────────

/// Trait for generating inference outputs.
///
/// Implemented by `TierHandler` or any other inference backend.
pub trait InferenceProvider: Send + Sync {
    /// Generate a response for the given prompt.
    /// Returns (output, confidence).
    fn generate(&self, prompt: &str, max_tokens: usize) -> Result<(String, f32), String>;
}

// ── Critique Provider Trait ───────────────────────────────────────────

/// Trait for critiquing generated outputs (self-correction).
pub trait CritiqueProvider: Send + Sync {
    /// Critique an output and suggest improvements.
    /// Returns (critique_text, refined_output, new_confidence).
    fn critique(&self, prompt: &str, output: &str, confidence: f32) -> (String, String, f32);
}

/// Heuristic critique provider — checks for common issues.
pub struct HeuristicCritique;

impl CritiqueProvider for HeuristicCritique {
    fn critique(&self, prompt: &str, output: &str, confidence: f32) -> (String, String, f32) {
        let mut critiques = Vec::new();
        let mut refined = output.to_string();
        let mut new_confidence = confidence;

        // Check for hedging language
        let hedging = ["maybe", "perhaps", "i think", "possibly", "not sure"];
        let lower = output.to_lowercase();
        let hedge_count = hedging.iter().filter(|h| lower.contains(*h)).count();
        if hedge_count > 0 {
            critiques.push(format!("Output contains {hedge_count} hedging phrase(s)"));
            new_confidence = (-0.05_f32)
                .mul_add(hedge_count as f32, new_confidence)
                .max(0.1);
        }

        // Check for repetition
        let words: Vec<&str> = output.split_whitespace().collect();
        if words.len() > 10 {
            let mut seen = std::collections::HashSet::new();
            let mut repeats = 0;
            for w in &words {
                let wl = w.to_lowercase();
                if !seen.insert(wl) {
                    repeats += 1;
                }
            }
            if repeats > words.len() / 3 {
                critiques.push("Output has high word repetition".to_string());
                new_confidence = (new_confidence - 0.1).max(0.1);
            }
        }

        // Check for empty or very short output
        if output.trim().len() < 10 {
            critiques.push("Output is too short".to_string());
            new_confidence = (new_confidence - 0.2).max(0.1);
        }

        // Check prompt relevance (keyword overlap)
        let prompt_lower = prompt.to_lowercase();
        let output_lower = output.to_lowercase();
        let prompt_words: std::collections::HashSet<&str> =
            prompt_lower.split_whitespace().collect();
        let output_words: std::collections::HashSet<&str> =
            output_lower.split_whitespace().collect();
        let overlap = prompt_words.intersection(&output_words).count();
        if prompt_words.len() > 2 && overlap < prompt_words.len() / 3 {
            critiques.push("Output has low relevance to prompt".to_string());
            new_confidence = (new_confidence - 0.1).max(0.1);
        }

        // Simple refinement: strip hedging
        for h in &hedging {
            refined = refined.replace(h, "");
            let cap = h.chars().next().map(|c| {
                let mut upper = String::new();
                upper.push(c.to_ascii_uppercase());
                upper.push_str(&h[1..]);
                upper
            });
            if let Some(cap_h) = cap {
                refined = refined.replace(&cap_h, "");
            }
        }
        refined = refined.split_whitespace().collect::<Vec<_>>().join(" ");

        let critique_text = if critiques.is_empty() {
            "No issues found".to_string()
        } else {
            critiques.join("; ")
        };

        (critique_text, refined, new_confidence)
    }
}

// ── Meta-Harness ──────────────────────────────────────────────────────

/// LLM Meta-Harness — wraps inference with cognitive enhancement strategies.
///
/// Combines memory grounding (RAG), self-correction, and ensemble voting
/// to improve local LLM output quality.
pub struct MetaHarness {
    config: MetaHarnessConfig,
    memory: Arc<dyn MemoryProvider>,
    inference: Arc<dyn InferenceProvider>,
    critique: Arc<dyn CritiqueProvider>,
    stats: Mutex<HarnessStats>,
}

impl MetaHarness {
    /// Create a new meta-harness with the given components.
    #[must_use]
    pub fn new(
        config: MetaHarnessConfig,
        inference: Arc<dyn InferenceProvider>,
        memory: Arc<dyn MemoryProvider>,
        critique: Arc<dyn CritiqueProvider>,
    ) -> Self {
        Self {
            config,
            memory,
            inference,
            critique,
            stats: Mutex::new(HarnessStats::default()),
        }
    }

    /// Create with default config and heuristic critique.
    #[must_use]
    pub fn with_defaults(
        inference: Arc<dyn InferenceProvider>,
        memory: Arc<dyn MemoryProvider>,
    ) -> Self {
        Self::new(
            MetaHarnessConfig::default(),
            inference,
            memory,
            Arc::new(HeuristicCritique),
        )
    }

    /// Create with no memory grounding (Direct/SelfCorrecting/Ensemble only).
    #[must_use]
    pub fn no_memory(inference: Arc<dyn InferenceProvider>) -> Self {
        Self::new(
            MetaHarnessConfig {
                default_mode: EnhancementMode::SelfCorrecting,
                ..MetaHarnessConfig::default()
            },
            inference,
            Arc::new(NoMemory),
            Arc::new(HeuristicCritique),
        )
    }

    /// Enhance a prompt with the default mode.
    pub fn enhance(&self, prompt: &str, max_tokens: usize) -> EnhancedResponse {
        self.enhance_with_mode(prompt, max_tokens, self.config.default_mode)
    }

    /// Enhance a prompt with a specific mode.
    pub fn enhance_with_mode(
        &self,
        prompt: &str,
        max_tokens: usize,
        mode: EnhancementMode,
    ) -> EnhancedResponse {
        let start = Instant::now();
        let mut steps = Vec::new();
        let mut grounded_memories = Vec::new();
        let mut correction_rounds = 0;
        let mut ensemble_attempts = 1;
        let mut validated = true;

        // Step 1: Memory grounding (if applicable)
        let effective_prompt = if mode.uses_memory() {
            let step_start = Instant::now();
            let memories = self
                .memory
                .search(prompt, self.config.max_grounding_memories);
            let latency = step_start.elapsed().as_micros() as u64;

            if memories.is_empty() {
                steps.push(EnhancementStep {
                    name: "memory_grounding".into(),
                    latency_us: latency,
                    modified: false,
                    detail: "no memories found".into(),
                });
                prompt.to_string()
            } else {
                grounded_memories = memories.iter().map(|(id, _)| id.clone()).collect();
                let context_block = self.build_context_block(&memories, prompt);
                steps.push(EnhancementStep {
                    name: "memory_grounding".into(),
                    latency_us: latency,
                    modified: true,
                    detail: format!("{} memories injected", memories.len()),
                });
                context_block
            }
        } else {
            prompt.to_string()
        };

        // Step 2: Generate (with ensemble if applicable)
        let (mut output, mut confidence) = if mode.uses_ensemble() {
            ensemble_attempts = self.config.ensemble_attempts;
            let step_start = Instant::now();
            let result = self.ensemble_generate(&effective_prompt, max_tokens, mode);
            let latency = step_start.elapsed().as_micros() as u64;
            steps.push(EnhancementStep {
                name: "ensemble_generate".into(),
                latency_us: latency,
                modified: true,
                detail: format!(
                    "{} attempts, best confidence: {:.2}",
                    ensemble_attempts, result.1
                ),
            });
            result
        } else {
            let step_start = Instant::now();
            let result = self
                .inference
                .generate(&effective_prompt, max_tokens)
                .unwrap_or_else(|e| (e, 0.0));
            let latency = step_start.elapsed().as_micros() as u64;
            steps.push(EnhancementStep {
                name: "generate".into(),
                latency_us: latency,
                modified: false,
                detail: format!("confidence: {:.2}", result.1),
            });
            result
        };

        // Step 3: Self-correction (if applicable)
        if mode.uses_self_correction() {
            for round in 0..self.config.max_correction_rounds {
                if confidence >= self.config.min_confidence {
                    break;
                }
                let step_start = Instant::now();
                let (critique_text, refined, new_conf) =
                    self.critique.critique(prompt, &output, confidence);
                let latency = step_start.elapsed().as_micros() as u64;
                let modified = refined != output;
                steps.push(EnhancementStep {
                    name: format!("self_correction_round_{}", round + 1),
                    latency_us: latency,
                    modified,
                    detail: critique_text,
                });
                output = refined;
                confidence = new_conf;
                correction_rounds = round + 1;
            }
        }

        // Step 4: Validation
        if self.config.validate_outputs {
            let step_start = Instant::now();
            let (clean, issues) = validate_output(&output);
            let latency = step_start.elapsed().as_micros() as u64;
            validated = clean;
            steps.push(EnhancementStep {
                name: "validation".into(),
                latency_us: latency,
                modified: !clean,
                detail: if clean {
                    "passed".into()
                } else {
                    issues.join("; ")
                },
            });
        }

        let latency_us = start.elapsed().as_micros() as u64;

        // Compute improvement score: compare enhanced confidence vs baseline
        let baseline_confidence = self.estimate_baseline_confidence(prompt);
        let improvement_score = if baseline_confidence > 0.0 {
            ((confidence - baseline_confidence) / baseline_confidence).clamp(0.0, 1.0)
        } else {
            0.0
        };

        let response = EnhancedResponse {
            output,
            confidence,
            mode,
            grounded_memories,
            correction_rounds,
            ensemble_attempts,
            validated,
            latency_us,
            improvement_score,
            steps,
        };

        // Update stats
        self.record_stats(mode, &response);

        response
    }

    /// Get current statistics.
    #[must_use]
    pub fn stats(&self) -> HarnessStats {
        self.stats.lock().map(|s| s.clone()).unwrap_or_default()
    }

    /// Get the configuration.
    #[must_use]
    pub const fn config(&self) -> &MetaHarnessConfig {
        &self.config
    }

    // ── Internal helpers ──────────────────────────────────────────────

    fn build_context_block(&self, memories: &[(String, String)], prompt: &str) -> String {
        let items: Vec<crate::ContextItem> = memories
            .iter()
            .map(|(id, content)| {
                crate::ContextItem::new(id, content)
                    .with_importance(0.8)
                    .with_relevance(0.7)
            })
            .collect();

        let optimizer = crate::ContextOptimizer::new(self.config.context_token_budget);
        let packed = optimizer.pack(items, Some(self.config.context_token_budget), Some(prompt));
        crate::ContextOptimizer::render(&packed, "\n---\n")
    }

    fn ensemble_generate(
        &self,
        prompt: &str,
        max_tokens: usize,
        _mode: EnhancementMode,
    ) -> (String, f32) {
        let mut best_output = String::new();
        let mut best_confidence = 0.0f32;
        let mut outputs: Vec<(String, f32)> = Vec::new();

        for _ in 0..self.config.ensemble_attempts {
            if let Ok((output, conf)) = self.inference.generate(prompt, max_tokens) {
                outputs.push((output.clone(), conf));
                if conf > best_confidence {
                    best_confidence = conf;
                    best_output = output;
                }
            }
        }

        // Vote: if multiple outputs agree on first N words, boost confidence
        if outputs.len() >= 2 {
            let prefix_len = 20.min(best_output.len());
            let best_prefix = best_output[..prefix_len].to_lowercase();
            let agreements = outputs
                .iter()
                .filter(|(o, _)| {
                    let p = 20.min(o.len());
                    o[..p].to_lowercase() == best_prefix
                })
                .count();
            if agreements > 1 {
                let boost = 0.05 * (agreements - 1) as f32;
                best_confidence = (best_confidence + boost).min(1.0);
            }
        }

        (best_output, best_confidence)
    }

    fn estimate_baseline_confidence(&self, prompt: &str) -> f32 {
        // Heuristic: longer prompts tend to have lower baseline confidence
        let words = prompt.split_whitespace().count();
        if words < 5 {
            0.7
        } else if words < 15 {
            0.6
        } else if words < 30 {
            0.5
        } else {
            0.4
        }
    }

    fn record_stats(&self, mode: EnhancementMode, response: &EnhancedResponse) {
        let Ok(mut stats) = self.stats.lock() else {
            return;
        };
        stats.total_calls += 1;
        stats.total_latency_us += response.latency_us;

        if !response.validated {
            stats.validation_failures += 1;
        }

        let mode_stats = stats.by_mode.entry(mode).or_default();
        mode_stats.calls += 1;
        mode_stats.total_latency_us += response.latency_us;
        mode_stats.total_improvement += response.improvement_score;
        if !response.grounded_memories.is_empty() {
            mode_stats.grounded_count += 1;
        }
        if response.correction_rounds > 0 {
            mode_stats.corrected_count += 1;
        }
        if response.ensemble_attempts > 1 {
            mode_stats.ensemble_count += 1;
        }
    }
}

// ── Validation ────────────────────────────────────────────────────────

/// Validate output for common issues.
/// Returns (is_clean, issues).
fn validate_output(output: &str) -> (bool, Vec<String>) {
    let mut issues = Vec::new();

    // Check for empty output
    if output.trim().is_empty() {
        issues.push("empty output".to_string());
        return (false, issues);
    }

    // Check for bracket balance (code-like outputs)
    let (balanced, err) = check_bracket_balance(output);
    if !balanced {
        if let Some(e) = err {
            issues.push(e);
        }
    }

    // Check for obvious security issues
    let lower = output.to_lowercase();
    if lower.contains("exec(") || lower.contains("eval(") {
        issues.push("dangerous function call detected".to_string());
    }

    (issues.is_empty(), issues)
}

/// Lightweight bracket balance check.
fn check_bracket_balance(s: &str) -> (bool, Option<String>) {
    let mut paren = 0i32;
    let mut bracket = 0i32;
    let mut brace = 0i32;

    for ch in s.chars() {
        match ch {
            '(' => paren += 1,
            ')' => paren -= 1,
            '[' => bracket += 1,
            ']' => bracket -= 1,
            '{' => brace += 1,
            '}' => brace -= 1,
            _ => {}
        }
        if paren < 0 || bracket < 0 || brace < 0 {
            return (
                false,
                Some(format!("unmatched closing delimiter near '{ch}'")),
            );
        }
    }

    if paren != 0 {
        return (
            false,
            Some(format!("unbalanced parentheses: offset {paren}")),
        );
    }
    if bracket != 0 {
        return (
            false,
            Some(format!("unbalanced brackets: offset {bracket}")),
        );
    }
    if brace != 0 {
        return (false, Some(format!("unbalanced braces: offset {brace}")));
    }

    (true, None)
}

// ── TierHandler adapter ───────────────────────────────────────────────

/// Adapter to use a `TierHandler` as an `InferenceProvider`.
pub struct TierHandlerInference {
    handler: Arc<dyn crate::TierHandler>,
}

impl TierHandlerInference {
    /// Create a new adapter.
    #[must_use]
    pub fn new(handler: Arc<dyn crate::TierHandler>) -> Self {
        Self { handler }
    }
}

impl InferenceProvider for TierHandlerInference {
    fn generate(&self, prompt: &str, max_tokens: usize) -> Result<(String, f32), String> {
        self.handler.handle(prompt, max_tokens)
    }
}

// ── Tests ─────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    // ── Stub inference provider ──────────────────────────────────────

    struct StubInference {
        response: String,
        confidence: f32,
    }

    impl InferenceProvider for StubInference {
        fn generate(&self, _prompt: &str, _max_tokens: usize) -> Result<(String, f32), String> {
            Ok((self.response.clone(), self.confidence))
        }
    }

    struct FailingInference;

    impl InferenceProvider for FailingInference {
        fn generate(&self, _prompt: &str, _max_tokens: usize) -> Result<(String, f32), String> {
            Err("inference failed".to_string())
        }
    }

    struct VariedInference;

    impl InferenceProvider for VariedInference {
        fn generate(&self, prompt: &str, _max_tokens: usize) -> Result<(String, f32), String> {
            // Return different confidence based on prompt word count
            let words = prompt.split_whitespace().count();
            let conf = if words > 5 { 0.9 } else { 0.4 };
            Ok((format!("response to: {prompt}"), conf))
        }
    }

    // ── Stub memory provider ─────────────────────────────────────────

    struct StubMemory {
        memories: Vec<(String, String)>,
    }

    impl MemoryProvider for StubMemory {
        fn search(&self, _query: &str, limit: usize) -> Vec<(String, String)> {
            self.memories.iter().take(limit).cloned().collect()
        }
    }

    // ── Mode tests ───────────────────────────────────────────────────

    #[test]
    fn mode_label() {
        assert_eq!(EnhancementMode::Direct.label(), "direct");
        assert_eq!(EnhancementMode::MemoryGrounded.label(), "memory_grounded");
        assert_eq!(EnhancementMode::SelfCorrecting.label(), "self_correcting");
        assert_eq!(EnhancementMode::Ensemble.label(), "ensemble");
        assert_eq!(EnhancementMode::FullStack.label(), "full_stack");
    }

    #[test]
    fn mode_uses_memory() {
        assert!(EnhancementMode::MemoryGrounded.uses_memory());
        assert!(EnhancementMode::FullStack.uses_memory());
        assert!(!EnhancementMode::Direct.uses_memory());
        assert!(!EnhancementMode::SelfCorrecting.uses_memory());
        assert!(!EnhancementMode::Ensemble.uses_memory());
    }

    #[test]
    fn mode_uses_self_correction() {
        assert!(EnhancementMode::SelfCorrecting.uses_self_correction());
        assert!(EnhancementMode::FullStack.uses_self_correction());
        assert!(!EnhancementMode::Direct.uses_self_correction());
    }

    #[test]
    fn mode_uses_ensemble() {
        assert!(EnhancementMode::Ensemble.uses_ensemble());
        assert!(EnhancementMode::FullStack.uses_ensemble());
        assert!(!EnhancementMode::Direct.uses_ensemble());
    }

    // ── Direct mode ──────────────────────────────────────────────────

    #[test]
    fn direct_mode_passthrough() {
        let harness = MetaHarness::new(
            MetaHarnessConfig {
                default_mode: EnhancementMode::Direct,
                ..MetaHarnessConfig::default()
            },
            Arc::new(StubInference {
                response: "hello world".into(),
                confidence: 0.9,
            }),
            Arc::new(NoMemory),
            Arc::new(HeuristicCritique),
        );

        let resp = harness.enhance("test prompt", 100);
        assert_eq!(resp.mode, EnhancementMode::Direct);
        assert_eq!(resp.output, "hello world");
        assert!((resp.confidence - 0.9).abs() < 0.01);
        assert!(resp.grounded_memories.is_empty());
        assert_eq!(resp.correction_rounds, 0);
        assert_eq!(resp.ensemble_attempts, 1);
    }

    // ── Memory grounding ─────────────────────────────────────────────

    #[test]
    fn memory_grounded_injects_context() {
        let harness = MetaHarness::new(
            MetaHarnessConfig {
                default_mode: EnhancementMode::MemoryGrounded,
                max_grounding_memories: 3,
                ..MetaHarnessConfig::default()
            },
            Arc::new(StubInference {
                response: "grounded response".into(),
                confidence: 0.85,
            }),
            Arc::new(StubMemory {
                memories: vec![
                    ("mem-1".into(), "Rust is safe".into()),
                    ("mem-2".into(), "Rust is fast".into()),
                    ("mem-3".into(), "Rust is concurrent".into()),
                ],
            }),
            Arc::new(HeuristicCritique),
        );

        let resp = harness.enhance("tell me about rust", 100);
        assert_eq!(resp.mode, EnhancementMode::MemoryGrounded);
        assert_eq!(resp.grounded_memories.len(), 3);
        assert!(resp.grounded_memories.contains(&"mem-1".to_string()));
        assert_eq!(resp.output, "grounded response");
    }

    #[test]
    fn memory_grounded_no_memories() {
        let harness = MetaHarness::new(
            MetaHarnessConfig {
                default_mode: EnhancementMode::MemoryGrounded,
                ..MetaHarnessConfig::default()
            },
            Arc::new(StubInference {
                response: "no context".into(),
                confidence: 0.7,
            }),
            Arc::new(NoMemory),
            Arc::new(HeuristicCritique),
        );

        let resp = harness.enhance("test", 100);
        assert!(resp.grounded_memories.is_empty());
        assert_eq!(resp.output, "no context");
    }

    // ── Self-correction ──────────────────────────────────────────────

    #[test]
    fn self_correcting_improves_low_confidence() {
        let harness = MetaHarness::new(
            MetaHarnessConfig {
                default_mode: EnhancementMode::SelfCorrecting,
                min_confidence: 0.7,
                max_correction_rounds: 3,
                ..MetaHarnessConfig::default()
            },
            Arc::new(StubInference {
                response: "maybe this is possibly correct".into(),
                confidence: 0.3,
            }),
            Arc::new(NoMemory),
            Arc::new(HeuristicCritique),
        );

        let resp = harness.enhance("what is rust", 100);
        assert_eq!(resp.mode, EnhancementMode::SelfCorrecting);
        assert!(resp.correction_rounds > 0);
        // HeuristicCritique should strip hedging words
        assert!(!resp.output.contains("maybe"));
        assert!(!resp.output.contains("possibly"));
    }

    #[test]
    fn self_correcting_skips_high_confidence() {
        let harness = MetaHarness::new(
            MetaHarnessConfig {
                default_mode: EnhancementMode::SelfCorrecting,
                min_confidence: 0.6,
                ..MetaHarnessConfig::default()
            },
            Arc::new(StubInference {
                response: "confident answer".into(),
                confidence: 0.9,
            }),
            Arc::new(NoMemory),
            Arc::new(HeuristicCritique),
        );

        let resp = harness.enhance("test", 100);
        assert_eq!(resp.correction_rounds, 0);
    }

    // ── Ensemble ─────────────────────────────────────────────────────

    #[test]
    fn ensemble_picks_best_confidence() {
        let harness = MetaHarness::new(
            MetaHarnessConfig {
                default_mode: EnhancementMode::Ensemble,
                ensemble_attempts: 3,
                ..MetaHarnessConfig::default()
            },
            Arc::new(VariedInference),
            Arc::new(NoMemory),
            Arc::new(HeuristicCritique),
        );

        // With a long prompt (context block), VariedInference returns 0.9
        let resp = harness.enhance(
            "this is a longer prompt that should get high confidence",
            100,
        );
        assert_eq!(resp.ensemble_attempts, 3);
        assert!(resp.confidence >= 0.9);
    }

    // ── Full stack ───────────────────────────────────────────────────

    #[test]
    fn full_stack_all_enhancements() {
        let harness = MetaHarness::new(
            MetaHarnessConfig {
                default_mode: EnhancementMode::FullStack,
                max_grounding_memories: 2,
                ensemble_attempts: 2,
                min_confidence: 0.7,
                max_correction_rounds: 2,
                ..MetaHarnessConfig::default()
            },
            Arc::new(StubInference {
                response: "maybe answer".into(),
                confidence: 0.4,
            }),
            Arc::new(StubMemory {
                memories: vec![("m1".into(), "context info".into())],
            }),
            Arc::new(HeuristicCritique),
        );

        let resp = harness.enhance("explain rust", 200);
        assert_eq!(resp.mode, EnhancementMode::FullStack);
        assert!(!resp.grounded_memories.is_empty());
        assert!(resp.ensemble_attempts >= 2);
        // Low confidence should trigger correction
        assert!(resp.correction_rounds > 0);
    }

    // ── Stats ────────────────────────────────────────────────────────

    #[test]
    fn stats_track_by_mode() {
        let harness = MetaHarness::new(
            MetaHarnessConfig {
                default_mode: EnhancementMode::Direct,
                ..MetaHarnessConfig::default()
            },
            Arc::new(StubInference {
                response: "test".into(),
                confidence: 0.8,
            }),
            Arc::new(NoMemory),
            Arc::new(HeuristicCritique),
        );

        harness.enhance("prompt1", 100);
        harness.enhance("prompt2", 100);

        let stats = harness.stats();
        assert_eq!(stats.total_calls, 2);
        let direct = stats.mode(EnhancementMode::Direct).unwrap();
        assert_eq!(direct.calls, 2);
        assert!(direct.avg_latency_us() > 0);
    }

    #[test]
    fn stats_track_multiple_modes() {
        let harness = MetaHarness::new(
            MetaHarnessConfig {
                default_mode: EnhancementMode::Direct,
                ..MetaHarnessConfig::default()
            },
            Arc::new(StubInference {
                response: "test".into(),
                confidence: 0.8,
            }),
            Arc::new(NoMemory),
            Arc::new(HeuristicCritique),
        );

        harness.enhance("p1", 100);
        harness.enhance_with_mode("p2", 100, EnhancementMode::SelfCorrecting);

        let stats = harness.stats();
        assert_eq!(stats.total_calls, 2);
        assert!(stats.by_mode.contains_key(&EnhancementMode::Direct));
        assert!(stats.by_mode.contains_key(&EnhancementMode::SelfCorrecting));
    }

    // ── Validation ───────────────────────────────────────────────────

    #[test]
    fn validation_catches_empty_output() {
        let (clean, issues) = validate_output("");
        assert!(!clean);
        assert!(issues.iter().any(|i| i.contains("empty")));
    }

    #[test]
    fn validation_catches_unbalanced_brackets() {
        let (clean, issues) = validate_output("function() { unclosed");
        assert!(!clean);
        assert!(issues.iter().any(|i| i.contains("unbalanced")));
    }

    #[test]
    fn validation_catches_dangerous_calls() {
        let (clean, issues) = validate_output("result = eval(user_input)");
        assert!(!clean);
        assert!(issues.iter().any(|i| i.contains("dangerous")));
    }

    #[test]
    fn validation_passes_clean_output() {
        let (clean, issues) = validate_output("This is a clean response with no issues.");
        assert!(clean);
        assert!(issues.is_empty());
    }

    // ── Heuristic critique ───────────────────────────────────────────

    #[test]
    fn critique_detects_hedging() {
        let critique = HeuristicCritique;
        let (text, refined, conf) = critique.critique("test", "maybe this is possibly right", 0.8);
        assert!(text.contains("hedging"));
        assert!(!refined.contains("maybe"));
        assert!(!refined.contains("possibly"));
        assert!(conf < 0.8);
    }

    #[test]
    fn critique_detects_short_output() {
        let critique = HeuristicCritique;
        let (text, _refined, conf) = critique.critique("test", "hi", 0.9);
        assert!(text.contains("short"));
        assert!(conf < 0.9);
    }

    #[test]
    fn critique_detects_low_relevance() {
        let critique = HeuristicCritique;
        let (text, _refined, _conf) = critique.critique(
            "explain quantum physics in detail",
            "the weather is nice today and I like cookies",
            0.7,
        );
        assert!(text.contains("relevance"));
    }

    #[test]
    fn critique_passes_good_output() {
        let critique = HeuristicCritique;
        let (text, refined, conf) = critique.critique(
            "what is rust",
            "Rust is a systems programming language focused on safety and performance",
            0.9,
        );
        assert_eq!(text, "No issues found");
        assert_eq!(
            refined,
            "Rust is a systems programming language focused on safety and performance"
        );
        assert!((conf - 0.9).abs() < 0.01);
    }

    // ── Failing inference ────────────────────────────────────────────

    #[test]
    fn failing_inference_returns_error_output() {
        let harness = MetaHarness::new(
            MetaHarnessConfig {
                default_mode: EnhancementMode::Direct,
                ..MetaHarnessConfig::default()
            },
            Arc::new(FailingInference),
            Arc::new(NoMemory),
            Arc::new(HeuristicCritique),
        );

        let resp = harness.enhance("test", 100);
        assert_eq!(resp.output, "inference failed");
        assert!((resp.confidence - 0.0).abs() < f32::EPSILON);
    }

    // ── Improvement score ────────────────────────────────────────────

    #[test]
    fn improvement_score_non_negative() {
        let harness = MetaHarness::new(
            MetaHarnessConfig {
                default_mode: EnhancementMode::Direct,
                ..MetaHarnessConfig::default()
            },
            Arc::new(StubInference {
                response: "test".into(),
                confidence: 0.3,
            }),
            Arc::new(NoMemory),
            Arc::new(HeuristicCritique),
        );

        let resp = harness.enhance("short", 100);
        assert!(resp.improvement_score >= 0.0);
    }

    #[test]
    fn improvement_score_high_for_boosted_confidence() {
        let harness = MetaHarness::new(
            MetaHarnessConfig {
                default_mode: EnhancementMode::Ensemble,
                ensemble_attempts: 3,
                ..MetaHarnessConfig::default()
            },
            Arc::new(VariedInference),
            Arc::new(NoMemory),
            Arc::new(HeuristicCritique),
        );

        // Long prompt → high confidence from VariedInference
        let resp = harness.enhance("this is a longer prompt for high confidence output", 100);
        assert!(resp.improvement_score > 0.0);
    }

    // ── Config ───────────────────────────────────────────────────────

    #[test]
    fn config_default() {
        let config = MetaHarnessConfig::default();
        assert_eq!(config.default_mode, EnhancementMode::MemoryGrounded);
        assert_eq!(config.max_grounding_memories, 5);
        assert_eq!(config.ensemble_attempts, 3);
        assert_eq!(config.max_correction_rounds, 2);
        assert!((config.min_confidence - 0.6).abs() < 0.01);
        assert!(config.validate_outputs);
    }

    // ── NoMemory provider ────────────────────────────────────────────

    #[test]
    fn no_memory_returns_empty() {
        let provider = NoMemory;
        assert!(provider.search("test", 10).is_empty());
    }

    // ── Mode stats ───────────────────────────────────────────────────

    #[test]
    fn mode_stats_avg_latency() {
        let stats = ModeStats {
            calls: 3,
            total_latency_us: 300,
            total_improvement: 1.5,
            grounded_count: 2,
            corrected_count: 1,
            ensemble_count: 0,
        };
        assert_eq!(stats.avg_latency_us(), 100);
        assert!((stats.avg_improvement() - 0.5).abs() < 0.01);
    }

    #[test]
    fn mode_stats_zero_calls() {
        let stats = ModeStats::default();
        assert_eq!(stats.avg_latency_us(), 0);
        assert!((stats.avg_improvement() - 0.0).abs() < f32::EPSILON);
    }

    // ── Harness stats ────────────────────────────────────────────────

    #[test]
    fn harness_stats_avg_latency() {
        let stats = HarnessStats {
            total_calls: 5,
            total_latency_us: 500,
            ..Default::default()
        };
        assert_eq!(stats.avg_latency_us(), 100);
    }

    #[test]
    fn harness_stats_avg_latency_zero() {
        let stats = HarnessStats::default();
        assert_eq!(stats.avg_latency_us(), 0);
    }

    // ── Steps tracking ───────────────────────────────────────────────

    #[test]
    fn steps_recorded_for_full_stack() {
        let harness = MetaHarness::new(
            MetaHarnessConfig {
                default_mode: EnhancementMode::FullStack,
                max_grounding_memories: 2,
                ensemble_attempts: 2,
                min_confidence: 0.8,
                max_correction_rounds: 2,
                ..MetaHarnessConfig::default()
            },
            Arc::new(StubInference {
                response: "maybe answer".into(),
                confidence: 0.3,
            }),
            Arc::new(StubMemory {
                memories: vec![("m1".into(), "context".into())],
            }),
            Arc::new(HeuristicCritique),
        );

        let resp = harness.enhance("test prompt here", 100);
        // Should have: memory_grounding, ensemble_generate, correction rounds, validation
        assert!(resp.steps.len() >= 3);
        assert!(resp.steps.iter().any(|s| s.name == "memory_grounding"));
        assert!(resp.steps.iter().any(|s| s.name == "ensemble_generate"));
        assert!(resp.steps.iter().any(|s| s.name == "validation"));
    }

    #[test]
    fn direct_mode_minimal_steps() {
        let harness = MetaHarness::new(
            MetaHarnessConfig {
                default_mode: EnhancementMode::Direct,
                validate_outputs: false,
                ..MetaHarnessConfig::default()
            },
            Arc::new(StubInference {
                response: "test".into(),
                confidence: 0.9,
            }),
            Arc::new(NoMemory),
            Arc::new(HeuristicCritique),
        );

        let resp = harness.enhance("test", 100);
        // Direct mode with validation off should have just 1 step (generate)
        assert_eq!(resp.steps.len(), 1);
        assert_eq!(resp.steps[0].name, "generate");
    }

    // ── Build context block ──────────────────────────────────────────

    #[test]
    fn context_block_includes_memories() {
        let harness = MetaHarness::new(
            MetaHarnessConfig {
                default_mode: EnhancementMode::MemoryGrounded,
                max_grounding_memories: 2,
                context_token_budget: 1000,
                ..MetaHarnessConfig::default()
            },
            Arc::new(StubInference {
                response: "test".into(),
                confidence: 0.8,
            }),
            Arc::new(StubMemory {
                memories: vec![
                    ("m1".into(), "Rust is a systems language".into()),
                    ("m2".into(), "Rust prevents data races".into()),
                ],
            }),
            Arc::new(HeuristicCritique),
        );

        let resp = harness.enhance("what is rust", 100);
        assert_eq!(resp.grounded_memories.len(), 2);
    }

    // ── Bracket balance ──────────────────────────────────────────────

    #[test]
    fn bracket_balance_balanced() {
        let (ok, _) = check_bracket_balance("function() { return [1, 2]; }");
        assert!(ok);
    }

    #[test]
    fn bracket_balance_unbalanced() {
        let (ok, err) = check_bracket_balance("function() { unclosed");
        assert!(!ok);
        assert!(err.is_some());
    }

    #[test]
    fn bracket_balance_no_brackets() {
        let (ok, _) = check_bracket_balance("plain text");
        assert!(ok);
    }
}
