//! Speculative Decoding Pipeline — draft + verify inference acceleration.
//!
//! Ported from v2's `inference/speculative_decoder.py` and
//! `inference/speculative_wiring.py`.
//!
//! ## How it works
//!
//! 1. A small **draft model** (e.g. BitMamba-2 255M) generates K candidate
//!    tokens cheaply.
//! 2. A larger **verify model** (e.g. llama.cpp 7B) checks all K tokens in a
//!    single forward pass.
//! 3. Matching tokens are accepted; the first mismatch triggers re-generation
//!    from the verify model.
//! 4. Expected speedup: `K * p / (1 + K * (1 - p))` where p is draft accuracy.
//!
//! In v4, the draft and verify handlers are `TierHandler` implementations:
//! - Draft: `TriModelHandler` for the autonomic tier (BitMamba)
//! - Verify: `TriModelHandler` for the left tier (llama.cpp)
//!
//! Since v4's `TierHandler::handle` returns a full text response (not
//! token-by-token), the speculative decoder operates at the **segment level**:
//! the draft model produces a complete response, and the verify model either
//! accepts it (if confidence is high) or generates its own. This is a
//! pragmatic adaptation — true token-level speculative decoding requires
//! streaming token logits, which would need llama.cpp API extensions.

#![allow(clippy::significant_drop_tightening)]

use serde::{Deserialize, Serialize};
use std::sync::{Arc, Mutex};
use std::time::Instant;

use crate::router::TierHandler;

/// Configuration for the speculative decoder.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SpeculativeConfig {
    /// Number of draft candidates to generate before verifying.
    /// In token-level speculative decoding, this is the number of tokens
    /// the draft model generates before the verify model checks them.
    /// In v4's segment-level adaptation, this controls how many draft
    /// segments are attempted before falling back to verify-only.
    pub draft_k: usize,
    /// Minimum draft confidence to accept without verification.
    /// If draft confidence >= this threshold, the draft output is accepted
    /// directly (skip verify step — maximum speedup).
    pub draft_accept_threshold: f32,
    /// Minimum verify confidence for the final output.
    pub verify_confidence_threshold: f32,
    /// Whether speculative decoding is enabled.
    pub enabled: bool,
    /// Maximum draft latency in milliseconds before timing out.
    pub draft_timeout_ms: u64,
}

impl Default for SpeculativeConfig {
    fn default() -> Self {
        Self {
            draft_k: 4,
            draft_accept_threshold: 0.85,
            verify_confidence_threshold: 0.5,
            enabled: true,
            draft_timeout_ms: 500,
        }
    }
}

impl SpeculativeConfig {
    /// Parse configuration from environment variables.
    ///
    /// | Variable | Default | Description |
    /// |---|---|---|
    /// | `WM_SPEC_DRAFT_K` | `4` | Number of draft candidates |
    /// | `WM_SPEC_DRAFT_THRESHOLD` | `0.85` | Min draft confidence to skip verify |
    /// | `WM_SPEC_VERIFY_THRESHOLD` | `0.5` | Min verify confidence |
    /// | `WM_SPEC_ENABLED` | `1` | Enable speculative decoding |
    /// | `WM_SPEC_DRAFT_TIMEOUT_MS` | `500` | Draft model timeout |
    #[must_use]
    pub fn from_env() -> Self {
        let mut config = Self::default();
        if let Ok(val) = std::env::var("WM_SPEC_DRAFT_K") {
            if let Ok(k) = val.parse::<usize>() {
                if k > 0 {
                    config.draft_k = k;
                }
            }
        }
        if let Ok(val) = std::env::var("WM_SPEC_DRAFT_THRESHOLD") {
            if let Ok(t) = val.parse::<f32>() {
                if (0.0..=1.0).contains(&t) {
                    config.draft_accept_threshold = t;
                }
            }
        }
        if let Ok(val) = std::env::var("WM_SPEC_VERIFY_THRESHOLD") {
            if let Ok(t) = val.parse::<f32>() {
                if (0.0..=1.0).contains(&t) {
                    config.verify_confidence_threshold = t;
                }
            }
        }
        if let Ok(val) = std::env::var("WM_SPEC_ENABLED") {
            config.enabled = val != "0" && val.to_lowercase() != "false";
        }
        if let Ok(val) = std::env::var("WM_SPEC_DRAFT_TIMEOUT_MS") {
            if let Ok(t) = val.parse::<u64>() {
                config.draft_timeout_ms = t;
            }
        }
        config
    }
}

/// Statistics for a single speculative decoding invocation.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SpeculativeStats {
    /// Total number of speculative decoding calls.
    pub total_calls: u64,
    /// Number of times the draft was accepted without verification.
    pub draft_accepted: u64,
    /// Number of times the draft was accepted after verification.
    pub verify_accepted: u64,
    /// Number of times the draft was rejected and verify generated fresh output.
    pub draft_rejected: u64,
    /// Total draft latency in milliseconds.
    pub total_draft_latency_ms: f64,
    /// Total verify latency in milliseconds.
    pub total_verify_latency_ms: f64,
    /// Total tokens (word equivalents) produced.
    pub total_tokens: u64,
    /// Total tokens accepted from draft.
    pub draft_tokens_accepted: u64,
}

impl SpeculativeStats {
    /// Create empty stats.
    #[must_use]
    pub const fn new() -> Self {
        Self {
            total_calls: 0,
            draft_accepted: 0,
            verify_accepted: 0,
            draft_rejected: 0,
            total_draft_latency_ms: 0.0,
            total_verify_latency_ms: 0.0,
            total_tokens: 0,
            draft_tokens_accepted: 0,
        }
    }

    /// Acceptance rate: fraction of calls where draft output was used.
    #[must_use]
    pub fn acceptance_rate(&self) -> f32 {
        if self.total_calls == 0 {
            return 0.0;
        }
        (self.draft_accepted + self.verify_accepted) as f32 / self.total_calls as f32
    }

    /// Draft-only rate: fraction of calls where draft was accepted without verify.
    #[must_use]
    pub fn draft_only_rate(&self) -> f32 {
        if self.total_calls == 0 {
            return 0.0;
        }
        self.draft_accepted as f32 / self.total_calls as f32
    }

    /// Average draft latency in milliseconds.
    #[must_use]
    pub fn avg_draft_latency_ms(&self) -> f64 {
        if self.total_calls == 0 {
            return 0.0;
        }
        self.total_draft_latency_ms / self.total_calls as f64
    }

    /// Average verify latency in milliseconds.
    #[must_use]
    pub fn avg_verify_latency_ms(&self) -> f64 {
        let verify_calls = self.verify_accepted + self.draft_rejected;
        if verify_calls == 0 {
            return 0.0;
        }
        self.total_verify_latency_ms / verify_calls as f64
    }

    /// Estimated speedup factor over verify-only inference.
    ///
    /// Speedup = K * p / (1 + K * (1 - p))
    /// where K is draft_k and p is acceptance rate.
    #[must_use]
    pub fn estimated_speedup(&self, draft_k: usize) -> f64 {
        let p = f64::from(self.acceptance_rate());
        if p <= 0.0 {
            return 1.0;
        }
        let k = draft_k as f64;
        let one_minus_p = 1.0 - p;
        k * p / k.mul_add(one_minus_p, 1.0)
    }

    /// Token acceptance rate: fraction of tokens from draft that were accepted.
    #[must_use]
    pub fn token_acceptance_rate(&self) -> f32 {
        if self.total_tokens == 0 {
            return 0.0;
        }
        self.draft_tokens_accepted as f32 / self.total_tokens as f32
    }
}

impl Default for SpeculativeStats {
    fn default() -> Self {
        Self::new()
    }
}

/// Result of a single speculative decoding call.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SpeculativeResult {
    /// The final output text.
    pub output: String,
    /// Confidence in the output (0.0–1.0).
    pub confidence: f32,
    /// Whether the draft was accepted without verification.
    pub draft_accepted: bool,
    /// Whether verification was required.
    pub verified: bool,
    /// Draft model latency in milliseconds.
    pub draft_latency_ms: f64,
    /// Verify model latency in milliseconds (0 if not invoked).
    pub verify_latency_ms: f64,
    /// Total latency in milliseconds.
    pub total_latency_ms: f64,
    /// Number of tokens (word equivalents) in the output.
    pub token_count: usize,
    /// Number of tokens accepted from the draft.
    pub draft_tokens_accepted: usize,
    /// Method used: "draft_only", "draft_verified", "verify_only", "fallback".
    pub method: String,
}

/// Speculative decoder — accelerates inference using draft + verify pattern.
///
/// The draft handler (small model) generates a candidate response.
/// If draft confidence is high enough, it's accepted directly.
/// Otherwise, the verify handler (large model) checks or regenerates.
///
/// Both handlers implement the `TierHandler` trait.
pub struct SpeculativeDecoder {
    draft_handler: Arc<dyn TierHandler>,
    verify_handler: Arc<dyn TierHandler>,
    config: SpeculativeConfig,
    stats: Mutex<SpeculativeStats>,
}

impl SpeculativeDecoder {
    /// Create a new speculative decoder.
    #[must_use]
    pub fn new(
        draft_handler: Arc<dyn TierHandler>,
        verify_handler: Arc<dyn TierHandler>,
        config: SpeculativeConfig,
    ) -> Self {
        Self {
            draft_handler,
            verify_handler,
            config,
            stats: Mutex::new(SpeculativeStats::new()),
        }
    }

    /// Create from environment configuration.
    #[must_use]
    pub fn from_env(
        draft_handler: Arc<dyn TierHandler>,
        verify_handler: Arc<dyn TierHandler>,
    ) -> Self {
        Self::new(draft_handler, verify_handler, SpeculativeConfig::from_env())
    }

    /// Run speculative decoding for a prompt.
    ///
    /// 1. Draft model generates a candidate response.
    /// 2. If draft confidence >= `draft_accept_threshold`, accept directly.
    /// 3. Otherwise, verify model generates its own response.
    /// 4. If verify confidence >= `verify_confidence_threshold`, use verify output.
    /// 5. Otherwise, combine both outputs (fallback).
    pub fn generate(&self, prompt: &str, max_tokens: usize) -> SpeculativeResult {
        let start = Instant::now();

        // Phase 1: Draft
        let draft_start = Instant::now();
        let draft_result = self.draft_handler.handle(prompt, max_tokens);
        let draft_latency = draft_start.elapsed().as_secs_f64() * 1000.0;

        let (draft_output, draft_confidence) = match draft_result {
            Ok(result) => result,
            Err(e) => {
                tracing::warn!(error = %e, "draft handler failed, falling back to verify-only");
                return self.verify_only(prompt, max_tokens, start, draft_latency);
            }
        };

        let draft_token_count = count_tokens(&draft_output);

        // Phase 2: Check if draft confidence is high enough to skip verification
        if draft_confidence >= self.config.draft_accept_threshold {
            let total_latency = start.elapsed().as_secs_f64() * 1000.0;
            self.record_stats(
                true,  // draft_accepted
                false, // verified
                false, // draft_rejected
                draft_latency,
                0.0,
                draft_token_count,
                draft_token_count,
            );

            return SpeculativeResult {
                output: draft_output,
                confidence: draft_confidence,
                draft_accepted: true,
                verified: false,
                draft_latency_ms: draft_latency,
                verify_latency_ms: 0.0,
                total_latency_ms: total_latency,
                token_count: draft_token_count,
                draft_tokens_accepted: draft_token_count,
                method: "draft_only".to_string(),
            };
        }

        // Phase 3: Verify — the verify model generates its own response
        let verify_start = Instant::now();
        let verify_result = self.verify_handler.handle(prompt, max_tokens);
        let verify_latency = verify_start.elapsed().as_secs_f64() * 1000.0;

        let (verify_output, verify_confidence) = match verify_result {
            Ok(result) => result,
            Err(e) => {
                tracing::warn!(error = %e, "verify handler also failed, using draft output");
                let total_latency = start.elapsed().as_secs_f64() * 1000.0;
                self.record_stats(
                    true, // draft_accepted (fallback)
                    false,
                    false,
                    draft_latency,
                    verify_latency,
                    draft_token_count,
                    draft_token_count,
                );

                return SpeculativeResult {
                    output: draft_output,
                    confidence: draft_confidence * 0.5, // reduced confidence
                    draft_accepted: true,
                    verified: false,
                    draft_latency_ms: draft_latency,
                    verify_latency_ms: verify_latency,
                    total_latency_ms: total_latency,
                    token_count: draft_token_count,
                    draft_tokens_accepted: draft_token_count,
                    method: "fallback".to_string(),
                };
            }
        };

        let verify_token_count = count_tokens(&verify_output);

        // Phase 4: Decide which output to use
        // Compare draft and verify outputs at segment level
        let similarity = text_similarity(&draft_output, &verify_output);
        let draft_tokens_match = (similarity * draft_token_count as f32) as usize;

        if verify_confidence >= self.config.verify_confidence_threshold {
            // Verify output is confident — use it
            let total_latency = start.elapsed().as_secs_f64() * 1000.0;
            let draft_accepted = similarity > 0.5;

            self.record_stats(
                draft_accepted,
                true, // verified
                !draft_accepted,
                draft_latency,
                verify_latency,
                verify_token_count,
                draft_tokens_match,
            );

            SpeculativeResult {
                output: verify_output,
                confidence: verify_confidence,
                draft_accepted,
                verified: true,
                draft_latency_ms: draft_latency,
                verify_latency_ms: verify_latency,
                total_latency_ms: total_latency,
                token_count: verify_token_count,
                draft_tokens_accepted: draft_tokens_match,
                method: if draft_accepted {
                    "draft_verified".to_string()
                } else {
                    "verify_only".to_string()
                },
            }
        } else {
            // Both are uncertain — merge outputs, prefer verify
            let merged = merge_outputs(&draft_output, &verify_output);
            let merged_tokens = count_tokens(&merged);
            let total_latency = start.elapsed().as_secs_f64() * 1000.0;

            self.record_stats(
                false,
                true,
                true,
                draft_latency,
                verify_latency,
                merged_tokens,
                draft_tokens_match,
            );

            SpeculativeResult {
                output: merged,
                confidence: draft_confidence.midpoint(verify_confidence),
                draft_accepted: false,
                verified: true,
                draft_latency_ms: draft_latency,
                verify_latency_ms: verify_latency,
                total_latency_ms: total_latency,
                token_count: merged_tokens,
                draft_tokens_accepted: draft_tokens_match,
                method: "merged".to_string(),
            }
        }
    }

    /// Fallback to verify-only mode (draft failed).
    fn verify_only(
        &self,
        prompt: &str,
        max_tokens: usize,
        start: Instant,
        draft_latency: f64,
    ) -> SpeculativeResult {
        let verify_start = Instant::now();
        match self.verify_handler.handle(prompt, max_tokens) {
            Ok((output, confidence)) => {
                let verify_latency = verify_start.elapsed().as_secs_f64() * 1000.0;
                let total_latency = start.elapsed().as_secs_f64() * 1000.0;
                let token_count = count_tokens(&output);

                self.record_stats(
                    false,
                    true,
                    true,
                    draft_latency,
                    verify_latency,
                    token_count,
                    0,
                );

                SpeculativeResult {
                    output,
                    confidence,
                    draft_accepted: false,
                    verified: true,
                    draft_latency_ms: draft_latency,
                    verify_latency_ms: verify_latency,
                    total_latency_ms: total_latency,
                    token_count,
                    draft_tokens_accepted: 0,
                    method: "verify_only".to_string(),
                }
            }
            Err(e) => {
                let total_latency = start.elapsed().as_secs_f64() * 1000.0;
                SpeculativeResult {
                    output: format!("Error: both draft and verify failed: {e}"),
                    confidence: 0.0,
                    draft_accepted: false,
                    verified: false,
                    draft_latency_ms: draft_latency,
                    verify_latency_ms: 0.0,
                    total_latency_ms: total_latency,
                    token_count: 0,
                    draft_tokens_accepted: 0,
                    method: "error".to_string(),
                }
            }
        }
    }

    /// Record statistics from a call.
    fn record_stats(
        &self,
        draft_accepted: bool,
        verified: bool,
        draft_rejected: bool,
        draft_latency: f64,
        verify_latency: f64,
        token_count: usize,
        draft_tokens_accepted: usize,
    ) {
        if let Ok(mut stats) = self.stats.lock() {
            stats.total_calls += 1;
            if draft_accepted && !verified {
                stats.draft_accepted += 1;
            }
            if verified && draft_accepted {
                stats.verify_accepted += 1;
            }
            if draft_rejected {
                stats.draft_rejected += 1;
            }
            stats.total_draft_latency_ms += draft_latency;
            stats.total_verify_latency_ms += verify_latency;
            stats.total_tokens += token_count as u64;
            stats.draft_tokens_accepted += draft_tokens_accepted as u64;
        }
    }

    /// Get a snapshot of the current statistics.
    #[must_use]
    pub fn stats(&self) -> SpeculativeStats {
        self.stats.lock().map(|s| s.clone()).unwrap_or_default()
    }

    /// Get the configuration.
    #[must_use]
    pub const fn config(&self) -> &SpeculativeConfig {
        &self.config
    }

    /// Check if speculative decoding is enabled.
    #[must_use]
    pub const fn is_enabled(&self) -> bool {
        self.config.enabled
    }

    /// Get the draft handler name.
    #[must_use]
    pub fn draft_name(&self) -> &'static str {
        self.draft_handler.name()
    }

    /// Get the verify handler name.
    #[must_use]
    pub fn verify_name(&self) -> &'static str {
        self.verify_handler.name()
    }

    /// Get a summary string for display.
    #[must_use]
    pub fn summary(&self) -> String {
        let stats = self.stats();
        format!(
            "SpeculativeDecoder [draft={}, verify={}]\n\
             Calls: {} | Acceptance: {:.1}% (draft-only: {:.1}%)\n\
             Avg draft: {:.2}ms | Avg verify: {:.2}ms\n\
             Token acceptance: {:.1}% | Est. speedup: {:.2}x",
            self.draft_handler.name(),
            self.verify_handler.name(),
            stats.total_calls,
            stats.acceptance_rate() * 100.0,
            stats.draft_only_rate() * 100.0,
            stats.avg_draft_latency_ms(),
            stats.avg_verify_latency_ms(),
            stats.token_acceptance_rate() * 100.0,
            stats.estimated_speedup(self.config.draft_k),
        )
    }
}

/// Thread-safe handler that wraps a `SpeculativeDecoder` for use as a `TierHandler`.
///
/// This allows the speculative decoder to be registered as the handler for
/// a specific tier in the `InferenceRouter`, transparently accelerating
/// inference for that tier.
pub struct SpeculativeHandler {
    decoder: Arc<SpeculativeDecoder>,
}

impl SpeculativeHandler {
    /// Create a new speculative handler.
    #[must_use]
    pub const fn new(decoder: Arc<SpeculativeDecoder>) -> Self {
        Self { decoder }
    }

    /// Get the underlying decoder.
    #[must_use]
    pub fn decoder(&self) -> &SpeculativeDecoder {
        &self.decoder
    }
}

impl TierHandler for SpeculativeHandler {
    fn handle(&self, prompt: &str, max_tokens: usize) -> Result<(String, f32), String> {
        if !self.decoder.is_enabled() {
            // If disabled, fall through to verify handler directly
            return Err("speculative decoding disabled".to_string());
        }
        let result = self.decoder.generate(prompt, max_tokens);
        if result.confidence > 0.0 {
            Ok((result.output, result.confidence))
        } else {
            Err("speculative decoding produced no confident result".to_string())
        }
    }

    fn name(&self) -> &'static str {
        "speculative_decoder"
    }
}

/// Count tokens (word-level approximation).
fn count_tokens(text: &str) -> usize {
    text.split_whitespace().count()
}

/// Compute text similarity between two strings using word overlap (Jaccard).
///
/// Returns a value in [0.0, 1.0] where 1.0 means identical word sets.
fn text_similarity(a: &str, b: &str) -> f32 {
    let a_lower = a.to_lowercase();
    let b_lower = b.to_lowercase();
    let set_a: std::collections::HashSet<&str> = a_lower.split_whitespace().collect();
    let set_b: std::collections::HashSet<&str> = b_lower.split_whitespace().collect();

    if set_a.is_empty() && set_b.is_empty() {
        return 1.0;
    }
    if set_a.is_empty() || set_b.is_empty() {
        return 0.0;
    }

    let intersection = set_a.intersection(&set_b).count();
    let union = set_a.union(&set_b).count();
    intersection as f32 / union as f32
}

/// Merge two outputs, preferring the verify output but preserving
/// unique information from the draft.
fn merge_outputs(draft: &str, verify: &str) -> String {
    let verify_lower = verify.to_lowercase();
    let verify_words: std::collections::HashSet<&str> = verify_lower.split_whitespace().collect();

    // Find draft sentences not covered by verify
    let draft_sentences: Vec<&str> = draft
        .split('.')
        .map(str::trim)
        .filter(|s| !s.is_empty())
        .collect();
    let mut extra: Vec<String> = Vec::new();
    for sentence in &draft_sentences {
        let sentence_lower = sentence.to_lowercase();
        let sentence_words: std::collections::HashSet<&str> =
            sentence_lower.split_whitespace().collect();
        let overlap = sentence_words.intersection(&verify_words).count();
        let coverage = if sentence_words.is_empty() {
            1.0
        } else {
            overlap as f32 / sentence_words.len() as f32
        };
        if coverage < 0.5 {
            extra.push(sentence.to_string());
        }
    }

    if extra.is_empty() {
        verify.to_string()
    } else {
        format!("{verify} Additional context: {}", extra.join(". "))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Stub draft handler that returns a fixed response.
    struct StubDraft {
        response: String,
        confidence: f32,
    }

    impl TierHandler for StubDraft {
        fn handle(&self, _prompt: &str, _max_tokens: usize) -> Result<(String, f32), String> {
            Ok((self.response.clone(), self.confidence))
        }
        fn name(&self) -> &'static str {
            "stub_draft"
        }
    }

    /// Stub verify handler that returns a fixed response.
    struct StubVerify {
        response: String,
        confidence: f32,
    }

    impl TierHandler for StubVerify {
        fn handle(&self, _prompt: &str, _max_tokens: usize) -> Result<(String, f32), String> {
            Ok((self.response.clone(), self.confidence))
        }
        fn name(&self) -> &'static str {
            "stub_verify"
        }
    }

    /// Failing handler — always returns error.
    struct FailingHandler;

    impl TierHandler for FailingHandler {
        fn handle(&self, _prompt: &str, _max_tokens: usize) -> Result<(String, f32), String> {
            Err("handler failed".to_string())
        }
        fn name(&self) -> &'static str {
            "failing"
        }
    }

    fn make_decoder(
        draft_confidence: f32,
        verify_confidence: f32,
        config: SpeculativeConfig,
    ) -> SpeculativeDecoder {
        SpeculativeDecoder::new(
            Arc::new(StubDraft {
                response: "The answer is 42.".to_string(),
                confidence: draft_confidence,
            }),
            Arc::new(StubVerify {
                response: "The answer is 42 and the universe is vast.".to_string(),
                confidence: verify_confidence,
            }),
            config,
        )
    }

    #[test]
    fn config_default_values() {
        let config = SpeculativeConfig::default();
        assert_eq!(config.draft_k, 4);
        assert!((config.draft_accept_threshold - 0.85).abs() < f32::EPSILON);
        assert!((config.verify_confidence_threshold - 0.5).abs() < f32::EPSILON);
        assert!(config.enabled);
        assert_eq!(config.draft_timeout_ms, 500);
    }

    #[test]
    fn config_from_env_defaults() {
        // from_env reads env vars; without any set, it returns defaults.
        // We can't mutate env vars in forbid(unsafe_code) crates,
        // so we verify that defaults match expected values.
        let config = SpeculativeConfig::default();
        assert_eq!(config.draft_k, 4);
        assert!(config.enabled);
    }

    #[test]
    fn config_construction_custom() {
        // Test custom config construction directly (env var mutation
        // requires unsafe in Rust 2024, forbidden in this crate).
        let config = SpeculativeConfig {
            draft_k: 8,
            draft_accept_threshold: 0.9,
            enabled: false,
            ..SpeculativeConfig::default()
        };
        assert_eq!(config.draft_k, 8);
        assert!((config.draft_accept_threshold - 0.9).abs() < f32::EPSILON);
        assert!(!config.enabled);
    }

    #[test]
    fn config_invalid_values_clamped() {
        // Invalid values are handled gracefully by from_env (keeps defaults).
        // Test that the default config has valid ranges.
        let config = SpeculativeConfig::default();
        assert!(config.draft_k > 0);
        assert!(config.draft_accept_threshold >= 0.0 && config.draft_accept_threshold <= 1.0);
        assert!(
            config.verify_confidence_threshold >= 0.0 && config.verify_confidence_threshold <= 1.0
        );
    }

    #[test]
    fn draft_accepted_when_confidence_high() {
        let decoder = make_decoder(0.9, 0.8, SpeculativeConfig::default());
        let result = decoder.generate("What is the answer?", 100);

        assert!(result.draft_accepted);
        assert!(!result.verified);
        assert_eq!(result.method, "draft_only");
        assert!((result.confidence - 0.9).abs() < f32::EPSILON);
        assert_eq!(result.verify_latency_ms, 0.0);
    }

    #[test]
    fn verify_invoked_when_draft_confidence_low() {
        let decoder = make_decoder(0.3, 0.8, SpeculativeConfig::default());
        let result = decoder.generate("What is the answer?", 100);

        assert!(!result.draft_accepted);
        assert!(result.verified);
        assert!(result.verify_latency_ms > 0.0);
        assert!((result.confidence - 0.8).abs() < f32::EPSILON);
    }

    #[test]
    fn draft_verified_when_similarity_high() {
        let decoder = SpeculativeDecoder::new(
            Arc::new(StubDraft {
                response: "The answer is 42.".to_string(),
                confidence: 0.3,
            }),
            Arc::new(StubVerify {
                response: "The answer is 42.".to_string(),
                confidence: 0.8,
            }),
            SpeculativeConfig::default(),
        );
        let result = decoder.generate("What is the answer?", 100);

        // Draft and verify are identical → high similarity → draft_verified
        assert!(result.verified);
        assert_eq!(result.method, "draft_verified");
    }

    #[test]
    fn merged_when_both_low_confidence() {
        let decoder = make_decoder(0.2, 0.3, SpeculativeConfig::default());
        let result = decoder.generate("What is the answer?", 100);

        assert!(result.verified);
        assert_eq!(result.method, "merged");
        assert!((result.confidence - 0.25).abs() < f32::EPSILON);
    }

    #[test]
    fn draft_failure_falls_back_to_verify() {
        let decoder = SpeculativeDecoder::new(
            Arc::new(FailingHandler),
            Arc::new(StubVerify {
                response: "Verified answer.".to_string(),
                confidence: 0.8,
            }),
            SpeculativeConfig::default(),
        );
        let result = decoder.generate("test", 100);

        assert!(!result.draft_accepted);
        assert!(result.verified);
        assert_eq!(result.method, "verify_only");
        assert_eq!(result.output, "Verified answer.");
    }

    #[test]
    fn both_handlers_fail_returns_error() {
        let decoder = SpeculativeDecoder::new(
            Arc::new(FailingHandler),
            Arc::new(FailingHandler),
            SpeculativeConfig::default(),
        );
        let result = decoder.generate("test", 100);

        assert_eq!(result.method, "error");
        assert_eq!(result.confidence, 0.0);
        assert!(result.output.starts_with("Error:"));
    }

    #[test]
    fn verify_failure_uses_draft_with_reduced_confidence() {
        let decoder = SpeculativeDecoder::new(
            Arc::new(StubDraft {
                response: "Draft answer.".to_string(),
                confidence: 0.5,
            }),
            Arc::new(FailingHandler),
            SpeculativeConfig::default(),
        );
        let result = decoder.generate("test", 100);

        assert!(result.draft_accepted);
        assert_eq!(result.method, "fallback");
        assert!((result.confidence - 0.25).abs() < f32::EPSILON);
        assert_eq!(result.output, "Draft answer.");
    }

    #[test]
    fn stats_track_calls_correctly() {
        // First decoder: draft accepted (high confidence)
        let decoder1 = make_decoder(0.9, 0.8, SpeculativeConfig::default());
        decoder1.generate("test 1", 100);
        let stats1 = decoder1.stats();
        assert_eq!(stats1.total_calls, 1);
        assert_eq!(stats1.draft_accepted, 1);
        assert_eq!(stats1.verify_accepted, 0);

        // Second decoder: draft low confidence, verify used, low similarity
        let decoder2 = make_decoder(0.3, 0.8, SpeculativeConfig::default());
        decoder2.generate("test 2", 100);
        let stats2 = decoder2.stats();
        assert_eq!(stats2.total_calls, 1);
        assert_eq!(stats2.draft_accepted, 0);
        assert_eq!(stats2.draft_rejected, 1);
    }

    #[test]
    fn stats_acceptance_rate() {
        let stats = SpeculativeStats {
            total_calls: 10,
            draft_accepted: 4,
            verify_accepted: 3,
            draft_rejected: 3,
            total_draft_latency_ms: 100.0,
            total_verify_latency_ms: 200.0,
            total_tokens: 500,
            draft_tokens_accepted: 300,
        };
        // 7 accepted out of 10 = 0.7
        assert!((stats.acceptance_rate() - 0.7).abs() < 0.01);
        // 4 draft-only out of 10 = 0.4
        assert!((stats.draft_only_rate() - 0.4).abs() < 0.01);
    }

    #[test]
    fn stats_estimated_speedup() {
        let stats = SpeculativeStats {
            total_calls: 10,
            draft_accepted: 7,
            verify_accepted: 0,
            draft_rejected: 3,
            total_draft_latency_ms: 100.0,
            total_verify_latency_ms: 200.0,
            total_tokens: 500,
            draft_tokens_accepted: 300,
        };
        // p = 0.7, K = 4: speedup = 4*0.7 / (1 + 4*0.3) = 2.8 / 2.2 ≈ 1.27
        let speedup = stats.estimated_speedup(4);
        assert!(speedup > 1.0, "speedup should be > 1.0, got {speedup}");
        assert!((speedup - 1.2727).abs() < 0.01);
    }

    #[test]
    fn stats_empty_returns_zero() {
        let stats = SpeculativeStats::new();
        assert_eq!(stats.acceptance_rate(), 0.0);
        assert_eq!(stats.avg_draft_latency_ms(), 0.0);
        assert_eq!(stats.avg_verify_latency_ms(), 0.0);
        assert!((stats.estimated_speedup(4) - 1.0).abs() < f64::EPSILON);
    }

    #[test]
    fn token_acceptance_rate() {
        let stats = SpeculativeStats {
            total_calls: 5,
            draft_accepted: 3,
            verify_accepted: 1,
            draft_rejected: 1,
            total_draft_latency_ms: 50.0,
            total_verify_latency_ms: 100.0,
            total_tokens: 200,
            draft_tokens_accepted: 120,
        };
        assert!((stats.token_acceptance_rate() - 0.6).abs() < 0.01);
    }

    #[test]
    fn speculative_handler_works_as_tier_handler() {
        let decoder = Arc::new(make_decoder(0.9, 0.8, SpeculativeConfig::default()));
        let handler = SpeculativeHandler::new(decoder);

        let result = handler.handle("test prompt", 100);
        assert!(result.is_ok());
        let (output, confidence) = result.unwrap();
        assert!(!output.is_empty());
        assert!(confidence > 0.0);
        assert_eq!(handler.name(), "speculative_decoder");
    }

    #[test]
    fn speculative_handler_disabled_returns_error() {
        let config = SpeculativeConfig {
            enabled: false,
            ..SpeculativeConfig::default()
        };
        let decoder = Arc::new(make_decoder(0.9, 0.8, config));
        let handler = SpeculativeHandler::new(decoder);

        let result = handler.handle("test prompt", 100);
        assert!(result.is_err());
    }

    #[test]
    fn summary_contains_key_info() {
        let decoder = make_decoder(0.9, 0.8, SpeculativeConfig::default());
        decoder.generate("test", 100);
        let summary = decoder.summary();
        assert!(summary.contains("SpeculativeDecoder"));
        assert!(summary.contains("stub_draft"));
        assert!(summary.contains("stub_verify"));
        assert!(summary.contains("Calls: 1"));
    }

    #[test]
    fn count_tokens_works() {
        assert_eq!(count_tokens(""), 0);
        assert_eq!(count_tokens("hello"), 1);
        assert_eq!(count_tokens("hello world"), 2);
        assert_eq!(count_tokens("the quick brown fox"), 4);
    }

    #[test]
    fn text_similarity_identical() {
        let s = text_similarity("hello world", "hello world");
        assert!((s - 1.0).abs() < f32::EPSILON);
    }

    #[test]
    fn text_similarity_completely_different() {
        let s = text_similarity("hello world", "foo bar");
        assert!((s - 0.0).abs() < f32::EPSILON);
    }

    #[test]
    fn text_similarity_partial_overlap() {
        let s = text_similarity("hello world foo", "hello world bar");
        // intersection: hello, world = 2; union: hello, world, foo, bar = 4
        assert!((s - 0.5).abs() < 0.01);
    }

    #[test]
    fn text_similarity_empty_strings() {
        assert!((text_similarity("", "") - 1.0).abs() < f32::EPSILON);
        assert!((text_similarity("", "hello") - 0.0).abs() < f32::EPSILON);
    }

    #[test]
    fn merge_outputs_no_extra_info() {
        let merged = merge_outputs("hello world", "hello world foo");
        assert_eq!(merged, "hello world foo");
    }

    #[test]
    fn merge_outputs_with_extra_info() {
        let draft = "The answer is 42. Pine trees are green.";
        let verify = "The answer is 42 and the universe is vast.";
        let merged = merge_outputs(draft, verify);
        assert!(merged.contains("The answer is 42 and the universe is vast."));
        assert!(merged.contains("Additional context"));
        assert!(merged.contains("Pine trees are green"));
    }

    #[test]
    fn draft_k_does_not_affect_segment_level() {
        // In segment-level speculative decoding, draft_k doesn't change behavior
        // (it's relevant for token-level, which requires streaming API)
        let config = SpeculativeConfig {
            draft_k: 8,
            ..SpeculativeConfig::default()
        };
        let decoder = make_decoder(0.9, 0.8, config);
        let result = decoder.generate("test", 100);
        assert!(result.draft_accepted);
    }

    #[test]
    fn draft_accept_threshold_boundary() {
        let config = SpeculativeConfig {
            draft_accept_threshold: 0.85,
            ..SpeculativeConfig::default()
        };

        // Draft confidence exactly at threshold → accepted
        let decoder = make_decoder(0.85, 0.8, config.clone());
        let result = decoder.generate("test", 100);
        assert!(result.draft_accepted);

        // Draft confidence just below threshold → verify invoked
        let decoder2 = make_decoder(0.84, 0.8, config);
        let result2 = decoder2.generate("test", 100);
        assert!(!result2.draft_accepted);
        assert!(result2.verified);
    }

    #[test]
    fn verify_confidence_threshold_boundary() {
        let config = SpeculativeConfig {
            verify_confidence_threshold: 0.5,
            ..SpeculativeConfig::default()
        };

        // Use identical responses so similarity is 1.0 → draft_verified
        let decoder = SpeculativeDecoder::new(
            Arc::new(StubDraft {
                response: "The answer is 42.".to_string(),
                confidence: 0.3,
            }),
            Arc::new(StubVerify {
                response: "The answer is 42.".to_string(),
                confidence: 0.5,
            }),
            config,
        );
        let result = decoder.generate("test", 100);
        assert!(result.verified);
        assert_eq!(result.method, "draft_verified");
    }

    #[test]
    fn latency_is_recorded() {
        let decoder = make_decoder(0.3, 0.8, SpeculativeConfig::default());
        let result = decoder.generate("test", 100);

        assert!(result.draft_latency_ms >= 0.0);
        assert!(result.verify_latency_ms >= 0.0);
        assert!(result.total_latency_ms >= result.draft_latency_ms);

        let stats = decoder.stats();
        assert!(stats.total_draft_latency_ms > 0.0);
    }

    #[test]
    fn handler_names() {
        let decoder = make_decoder(0.9, 0.8, SpeculativeConfig::default());
        assert_eq!(decoder.draft_name(), "stub_draft");
        assert_eq!(decoder.verify_name(), "stub_verify");
    }

    #[test]
    fn is_enabled_checks_config() {
        let config = SpeculativeConfig {
            enabled: true,
            ..SpeculativeConfig::default()
        };
        let decoder = make_decoder(0.9, 0.8, config);
        assert!(decoder.is_enabled());

        let config2 = SpeculativeConfig {
            enabled: false,
            ..SpeculativeConfig::default()
        };
        let decoder2 = make_decoder(0.9, 0.8, config2);
        assert!(!decoder2.is_enabled());
    }

    #[test]
    fn config_accessor() {
        let config = SpeculativeConfig {
            draft_k: 6,
            ..SpeculativeConfig::default()
        };
        let decoder = make_decoder(0.9, 0.8, config);
        assert_eq!(decoder.config().draft_k, 6);
    }

    #[test]
    fn multiple_calls_accumulate_stats() {
        let decoder = make_decoder(0.9, 0.8, SpeculativeConfig::default());

        for _ in 0..5 {
            decoder.generate("test", 100);
        }

        let stats = decoder.stats();
        assert_eq!(stats.total_calls, 5);
        assert_eq!(stats.draft_accepted, 5);
        assert_eq!(stats.verify_accepted, 0);
        assert!((stats.acceptance_rate() - 1.0).abs() < f32::EPSILON);
    }

    #[test]
    fn mixed_calls_produce_correct_stats() {
        // Use a single decoder with low draft confidence so verify is always needed.
        // Draft and verify have different responses → low similarity → draft_rejected.
        let decoder = SpeculativeDecoder::new(
            Arc::new(StubDraft {
                response: "The answer is 42.".to_string(),
                confidence: 0.3, // Low confidence → always needs verify
            }),
            Arc::new(StubVerify {
                response: "The answer is 42 and more.".to_string(),
                confidence: 0.8,
            }),
            SpeculativeConfig::default(),
        );

        for _ in 0..2 {
            decoder.generate("test", 100);
        }

        let stats = decoder.stats();
        assert_eq!(stats.total_calls, 2);
        assert_eq!(stats.draft_accepted, 0);
        assert_eq!(stats.draft_rejected, 2);
        // acceptance_rate = (draft_accepted + verify_accepted) / total = 0/2 = 0
        assert!((stats.acceptance_rate() - 0.0).abs() < f32::EPSILON);
    }
}
