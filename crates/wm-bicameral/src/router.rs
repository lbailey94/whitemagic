//! Inference Router — complexity-aware routing across edge/local/cloud tiers.
//!
//! Ported from v2's `router.py` (1071 lines) and `complexity.py` (361 lines).
//! Routes each inference request to the cheapest sufficient tier:
//!
//! ```text
//! Prompt → ComplexityClassifier → Route Decision
//!                                     ├─ Tier 0: Heuristic (evidence tally, <1ms)
//!                                     ├─ Tier 1: llama.cpp small (1.5B-7B, 50-500ms)
//!                                     ├─ Tier 2: llama.cpp large / BitNet (8B+, 1-10s)
//!                                     └─ Tier 3: Cloud API (frontier model, 2-30s)
//! ```
//!
//! With confidence cascading: if Tier N output confidence < threshold,
//! escalate to Tier N+1. Sensitive data never routes to cloud.

#![allow(clippy::cast_sign_loss)]

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::Arc;
use std::time::Instant;

/// Inference capability tiers, ordered by cost/latency.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
#[repr(u8)]
pub enum InferenceTier {
    /// Pattern matching, heuristic — sub-millisecond.
    EdgeRules = 0,
    /// llama.cpp small model (continuous) — 10-100ms.
    LocalLlamaCpp = 1,
    /// llama.cpp 1.5B-7B quantized — 50-500ms.
    LocalSmall = 2,
    /// BitNet/llama.cpp 8B+ — 1-10s.
    LocalLarge = 3,
    /// Frontier model via API — 2-30s.
    Cloud = 4,
}

impl InferenceTier {
    /// Human-readable name.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::EdgeRules => "edge_rules",
            Self::LocalLlamaCpp => "local_llama_cpp",
            Self::LocalSmall => "local_small",
            Self::LocalLarge => "local_large",
            Self::Cloud => "cloud",
        }
    }

    /// Next higher tier (more expensive), or `None` if already at top.
    #[must_use]
    pub const fn escalate(self) -> Option<Self> {
        match self {
            Self::EdgeRules => Some(Self::LocalLlamaCpp),
            Self::LocalLlamaCpp => Some(Self::LocalSmall),
            Self::LocalSmall => Some(Self::LocalLarge),
            Self::LocalLarge => Some(Self::Cloud),
            Self::Cloud => None,
        }
    }

    /// All tiers in ascending order.
    #[must_use]
    pub const fn all() -> [Self; 5] {
        [
            Self::EdgeRules,
            Self::LocalLlamaCpp,
            Self::LocalSmall,
            Self::LocalLarge,
            Self::Cloud,
        ]
    }
}

impl std::fmt::Display for InferenceTier {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(self.as_str())
    }
}

/// Task type patterns — ordered from simplest to most complex.
/// Each entry: (regex pattern, tier, task label).
struct TaskPattern {
    re: regex::Regex,
    tier: InferenceTier,
    label: &'static str,
}

static TASK_PATTERNS: &[(&str, InferenceTier, &str)] = &[
    // Tier 0: Edge rules — pattern matching only, no model needed
    (
        r"^(hi|hello|hey|greetings|bye|goodbye|thanks)\b",
        InferenceTier::EdgeRules,
        "greeting",
    ),
    (
        r"\b(version|what version|status|health)\b",
        InferenceTier::EdgeRules,
        "status_query",
    ),
    (
        r"\b(yes|no|true|false)\b",
        InferenceTier::EdgeRules,
        "boolean",
    ),
    // Tier 1: LocalLlamaCpp — small model (0.5B), fast for simple Q&A and lookup
    (
        r"\b(what is|what.s the|who is|who was|where is|when did|how many)\b",
        InferenceTier::LocalLlamaCpp,
        "factual_qa",
    ),
    (
        r"\b(define|definition of|meaning of|what does .+ mean)\b",
        InferenceTier::LocalLlamaCpp,
        "definition",
    ),
    (
        r"\b(list|enumerate|name the|name some)\b",
        InferenceTier::LocalLlamaCpp,
        "listing",
    ),
    (
        r"\b(convert|calculate|compute|solve)\b",
        InferenceTier::LocalLlamaCpp,
        "computation",
    ),
    // Tier 2: LocalSmall — small/medium model (0.5B-1.5B), classification & extraction
    (
        r"\b(classify|categor|label|tag)\b",
        InferenceTier::LocalSmall,
        "classification",
    ),
    (
        r"\b(extract|pull out|find the|identify)\b",
        InferenceTier::LocalSmall,
        "extraction",
    ),
    (
        r"\b(summariz|tl;?dr|brief|condense)\b",
        InferenceTier::LocalSmall,
        "summarization",
    ),
    (
        r"\b(translat|paraphrase|rewrite|rephrase)\b",
        InferenceTier::LocalSmall,
        "reformulation",
    ),
    (
        r"\b(format|template|structure)\b",
        InferenceTier::LocalSmall,
        "formatting",
    ),
    // Tier 3: LocalLarge — large model (3B), reasoning & code generation
    (
        r"\b(analyz|evaluat|assess|investigat)\b",
        InferenceTier::LocalLarge,
        "analysis",
    ),
    (
        r"\b(code|function|implement|debug|refactor)\b",
        InferenceTier::LocalLarge,
        "coding",
    ),
    (
        r"\b(reason|deduce|infer|conclude)\b",
        InferenceTier::LocalLarge,
        "reasoning",
    ),
    (
        r"\b(compare|contrast|versus|vs\.?)\b",
        InferenceTier::LocalLarge,
        "comparison",
    ),
    (
        r"\b(plan|design|architect|strategy)\b",
        InferenceTier::LocalLarge,
        "planning",
    ),
    // Tier 4: Cloud — multi-step, creative, research
    (
        r"\b(multi.?step|chain|pipeline|workflow)\b",
        InferenceTier::Cloud,
        "multi_step",
    ),
    (
        r"\b(creative|story|poem|novel|screenplay)\b",
        InferenceTier::Cloud,
        "creative",
    ),
    (
        r"\b(research|literature|survey|systematic)\b",
        InferenceTier::Cloud,
        "research",
    ),
    (
        r"\b(legal|medical|financial advis|compliance)\b",
        InferenceTier::Cloud,
        "expert_domain",
    ),
];

static SENSITIVITY_PATTERNS: &[&str] = &[
    r"\b(ssn|social security|passport|national id)\b",
    r"\b(credit card|bank account|routing number|iban)\b",
    r"\b(diagnosis|prescription|medical record|patient)\b",
    r"\b(password|api key|secret|token|credential)\b",
    r"\b(confidential|proprietary|internal only|classified)\b",
];

static TOOL_CALL_PATTERNS: &[&str] = &[
    r"\b(call|invoke|execute|run)\s+(the\s+)?(tool|function|api|command)\b",
    r"\b(search|find|lookup|query)\s+(the\s+)?(memor\w*|database|knowledge)\b",
    r"\b(use|with|via)\s+(tool|function|mcp)\b",
];

static MULTI_TURN_PATTERNS: &[&str] = &[
    r"\b(then|after that|next|subsequently|finally)\b",
    r"\b(step \d|phase \d|stage \d)\b",
    r"\b(first.*second.*third|1\..*2\..*3\.)\b",
];

/// Result of complexity classification.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ComplexityAssessment {
    /// Recommended inference tier.
    pub tier: InferenceTier,
    /// Detected task type label.
    pub task_type: String,
    /// Classification confidence (0.0–1.0).
    pub confidence: f32,
    /// Estimated output token count.
    pub estimated_output_tokens: usize,
    /// Whether the prompt contains sensitive data.
    pub is_sensitive: bool,
    /// Whether the prompt likely needs tool/function calling.
    pub needs_tool_calls: bool,
    /// Whether the prompt is multi-turn/sequential.
    pub is_multi_turn: bool,
    /// Additional routing signals.
    pub signals: HashMap<String, String>,
}

impl ComplexityAssessment {
    /// Whether this assessment mandates cloud tier.
    #[must_use]
    pub fn requires_cloud(&self) -> bool {
        self.tier == InferenceTier::Cloud && !self.is_sensitive
    }

    /// Maximum tier allowed if cloud is unavailable.
    #[must_use]
    pub const fn max_local_tier(&self) -> InferenceTier {
        if self.is_sensitive {
            InferenceTier::LocalLarge
        } else {
            self.tier
        }
    }
}

/// Lightweight prompt complexity classifier for inference routing.
///
/// Uses pattern matching and heuristics — no model inference needed.
/// Runs in <100µs, suitable for the routing hot path.
pub struct ComplexityClassifier {
    default_tier: InferenceTier,
    sensitivity_override: bool,
    task_patterns: Vec<TaskPattern>,
    sensitivity_patterns: Vec<regex::Regex>,
    tool_call_patterns: Vec<regex::Regex>,
    multi_turn_patterns: Vec<regex::Regex>,
}

impl ComplexityClassifier {
    /// Create a new classifier with default settings.
    /// Defaults to `LocalLlamaCpp` (smallest HTTP model) for unknown prompts,
    /// which is the cheapest tier that still produces real LLM output.
    #[must_use]
    pub fn new() -> Self {
        Self::with_defaults(InferenceTier::LocalLlamaCpp, true)
    }

    /// Create a classifier with custom defaults.
    #[must_use]
    pub fn with_defaults(default_tier: InferenceTier, sensitivity_override: bool) -> Self {
        let task_patterns = TASK_PATTERNS
            .iter()
            .filter_map(|(pat, tier, label)| {
                regex::Regex::new(pat).ok().map(|re| TaskPattern {
                    re,
                    tier: *tier,
                    label,
                })
            })
            .collect();

        let sensitivity_patterns = SENSITIVITY_PATTERNS
            .iter()
            .filter_map(|p| regex::Regex::new(p).ok())
            .collect();

        let tool_call_patterns = TOOL_CALL_PATTERNS
            .iter()
            .filter_map(|p| regex::Regex::new(p).ok())
            .collect();

        let multi_turn_patterns = MULTI_TURN_PATTERNS
            .iter()
            .filter_map(|p| regex::Regex::new(p).ok())
            .collect();

        Self {
            default_tier,
            sensitivity_override,
            task_patterns,
            sensitivity_patterns,
            tool_call_patterns,
            multi_turn_patterns,
        }
    }

    /// Classify a prompt to determine the appropriate inference tier.
    ///
    /// # Parameters
    /// - `prompt`: The user prompt to classify.
    /// - `max_output_tokens`: Expected output length (if known).
    /// - `latency_budget_ms`: Maximum acceptable latency (if known).
    /// - `is_background`: Whether this is a background task (not user-facing).
    #[must_use]
    pub fn classify(
        &self,
        prompt: &str,
        max_output_tokens: Option<usize>,
        latency_budget_ms: Option<f64>,
        is_background: bool,
    ) -> ComplexityAssessment {
        let mut signals = HashMap::new();

        // 1. Task type classification via pattern matching
        let mut task_type = "unknown".to_string();
        let mut best_tier = self.default_tier;
        let mut best_confidence = 0.0_f32;

        for tp in &self.task_patterns {
            if tp.re.is_match(prompt) {
                task_type = tp.label.to_string();
                best_tier = tp.tier;
                best_confidence = if tp.tier == InferenceTier::EdgeRules {
                    0.9
                } else {
                    0.75
                };
                break; // First match wins (patterns are ordered)
            }
        }

        if best_confidence == 0.0 {
            // No pattern matched — estimate by length and structure
            let word_count = prompt.split_whitespace().count();
            if word_count < 10 {
                best_tier = InferenceTier::LocalLlamaCpp;
                best_confidence = 0.5;
                task_type = "short_query".into();
            } else if word_count < 50 {
                best_tier = InferenceTier::LocalLlamaCpp;
                best_confidence = 0.4;
                task_type = "medium_query".into();
            } else {
                best_tier = InferenceTier::LocalSmall;
                best_confidence = 0.4;
                task_type = "long_query".into();
            }
        }

        signals.insert("task_type".into(), task_type.clone());
        signals.insert("pattern_confidence".into(), format!("{best_confidence:.2}"));

        // 2. Token budget estimation
        // Detect prompt padding: if the prompt has very high repetition
        // (low unique-to-total word ratio), cap the effective word count
        // to prevent artificial tier escalation.
        let raw_word_count = prompt.split_whitespace().count();
        let unique_words: std::collections::HashSet<&str> = prompt.split_whitespace().collect();
        let unique_ratio = if raw_word_count > 0 {
            unique_words.len() as f32 / raw_word_count as f32
        } else {
            1.0
        };
        let word_count = if raw_word_count > 50 && unique_ratio < 0.1 {
            // Severe padding — cap effective word count
            signals.insert("padding_detected".into(), "true".into());
            unique_words.len().min(50)
        } else {
            raw_word_count
        };
        let est_tokens = if let Some(max_tok) = max_output_tokens {
            max_tok
        } else {
            // Heuristic: output ~ 1.5x input for generative, ~0.3x for extraction
            match task_type.as_str() {
                "extraction" | "classification" | "boolean" => {
                    (word_count as f32).mul_add(0.3, 50.0) as usize
                }
                "summarization" | "reformulation" => {
                    (word_count as f32).mul_add(0.5, 100.0) as usize
                }
                "creative" | "research" | "multi_step" => {
                    (word_count as f32).mul_add(2.0, 500.0) as usize
                }
                _ => (128.0 + word_count as f32) as usize,
            }
        };

        signals.insert("estimated_output_tokens".into(), est_tokens.to_string());

        // Token budget escalation (skip if padding was detected)
        let padding_detected = signals.contains_key("padding_detected");
        if !padding_detected && est_tokens > 2048 && best_tier < InferenceTier::Cloud {
            best_tier = InferenceTier::Cloud;
            signals.insert("escalation_reason".into(), "high_token_budget".into());
        } else if !padding_detected && est_tokens > 512 && best_tier < InferenceTier::LocalLarge {
            best_tier = InferenceTier::LocalLarge;
            signals.insert("escalation_reason".into(), "moderate_token_budget".into());
        }

        // 3. Data sensitivity detection
        let is_sensitive = self.sensitivity_patterns.iter().any(|p| p.is_match(prompt));
        signals.insert("is_sensitive".into(), is_sensitive.to_string());

        if is_sensitive && self.sensitivity_override && best_tier > InferenceTier::LocalLarge {
            best_tier = InferenceTier::LocalLarge;
            signals.insert("sensitivity_override".into(), "true".into());
        }

        // 4. Tool-call requirement detection
        let needs_tool_calls = self.tool_call_patterns.iter().any(|p| p.is_match(prompt));
        signals.insert("needs_tool_calls".into(), needs_tool_calls.to_string());

        if needs_tool_calls && best_tier < InferenceTier::LocalSmall {
            best_tier = InferenceTier::LocalSmall;
            signals.insert("tool_call_escalation".into(), "true".into());
        }

        // 5. Multi-turn detection
        let is_multi_turn = self.multi_turn_patterns.iter().any(|p| p.is_match(prompt));
        signals.insert("is_multi_turn".into(), is_multi_turn.to_string());

        if is_multi_turn && best_tier < InferenceTier::LocalSmall {
            best_tier = InferenceTier::LocalSmall;
            signals.insert("multi_turn_escalation".into(), "true".into());
        }

        // 6. Latency budget awareness
        if let Some(budget_ms) = latency_budget_ms {
            if budget_ms < 100.0 && best_tier > InferenceTier::EdgeRules {
                best_tier = InferenceTier::EdgeRules;
                signals.insert("latency_budget_override".into(), "true".into());
            } else if budget_ms < 500.0 && best_tier > InferenceTier::LocalSmall {
                best_tier = InferenceTier::LocalSmall;
                signals.insert("latency_budget_override".into(), "true".into());
            }
        }

        // Background tasks can use higher quality
        if is_background && best_tier < InferenceTier::LocalLarge {
            signals.insert("background_quality_boost".into(), "true".into());
        }

        ComplexityAssessment {
            tier: best_tier,
            task_type,
            confidence: best_confidence,
            estimated_output_tokens: est_tokens,
            is_sensitive,
            needs_tool_calls,
            is_multi_turn,
            signals,
        }
    }
}

impl Default for ComplexityClassifier {
    fn default() -> Self {
        Self::new()
    }
}

/// Tracks token budget across routing calls in a session.
///
/// Maintains a rolling EMA of token usage to predict whether the next
/// request will fit within budget.
#[derive(Debug, Clone)]
pub struct TokenBudgetTracker {
    total_budget: usize,
    used_tokens: usize,
    warning_threshold: f32,
    critical_threshold: f32,
    request_count: usize,
    ema_usage: f32,
    alpha: f32,
}

impl TokenBudgetTracker {
    /// Create a new budget tracker.
    #[must_use]
    pub const fn new(total_budget: usize) -> Self {
        Self {
            total_budget,
            used_tokens: 0,
            warning_threshold: 0.7,
            critical_threshold: 0.9,
            request_count: 0,
            ema_usage: 0.0,
            alpha: 0.3,
        }
    }

    /// Remaining tokens.
    #[must_use]
    pub const fn remaining(&self) -> usize {
        self.total_budget.saturating_sub(self.used_tokens)
    }

    /// Usage ratio (0.0–1.0+).
    #[must_use]
    pub fn usage_ratio(&self) -> f32 {
        if self.total_budget == 0 {
            return 1.0;
        }
        self.used_tokens as f32 / self.total_budget as f32
    }

    /// Whether usage is at warning level.
    #[must_use]
    pub fn is_warning(&self) -> bool {
        self.usage_ratio() >= self.warning_threshold
    }

    /// Whether usage is at critical level.
    #[must_use]
    pub fn is_critical(&self) -> bool {
        self.usage_ratio() >= self.critical_threshold
    }

    /// Record token usage from a completed request.
    pub fn record_usage(&mut self, input_tokens: usize, output_tokens: usize) {
        let total = input_tokens + output_tokens;
        self.used_tokens = self.used_tokens.saturating_add(total);
        self.request_count += 1;
        self.ema_usage = (total as f32).mul_add(self.alpha, (1.0 - self.alpha) * self.ema_usage);
    }

    /// Recommend a lower tier if token budget is running low.
    ///
    /// Returns the downgraded tier, or `None` if the requested tier is fine.
    #[must_use]
    pub fn recommend_downgrade(&self, requested_tier: InferenceTier) -> Option<InferenceTier> {
        if !self.is_warning() || requested_tier == InferenceTier::EdgeRules {
            return None;
        }

        if self.is_critical() {
            return if requested_tier > InferenceTier::EdgeRules {
                Some(InferenceTier::EdgeRules)
            } else {
                None
            };
        }

        // Warning: downgrade by one tier
        match requested_tier {
            InferenceTier::Cloud => Some(InferenceTier::LocalLarge),
            InferenceTier::LocalLarge => Some(InferenceTier::LocalSmall),
            InferenceTier::LocalSmall => Some(InferenceTier::LocalLlamaCpp),
            InferenceTier::LocalLlamaCpp => Some(InferenceTier::EdgeRules),
            InferenceTier::EdgeRules => None,
        }
    }

    /// Reset the tracker, optionally with a new budget.
    pub const fn reset(&mut self, new_budget: Option<usize>) {
        self.used_tokens = 0;
        self.request_count = 0;
        self.ema_usage = 0.0;
        if let Some(budget) = new_budget {
            self.total_budget = budget;
        }
    }

    /// Get a summary of the budget tracker state.
    #[must_use]
    pub fn summary(&self) -> BudgetSummary {
        BudgetSummary {
            total_budget: self.total_budget,
            used_tokens: self.used_tokens,
            remaining: self.remaining(),
            usage_ratio: self.usage_ratio(),
            is_warning: self.is_warning(),
            is_critical: self.is_critical(),
            request_count: self.request_count,
            avg_tokens_per_request: if self.request_count > 0 {
                self.ema_usage
            } else {
                0.0
            },
        }
    }
}

/// Budget tracker summary snapshot.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BudgetSummary {
    pub total_budget: usize,
    pub used_tokens: usize,
    pub remaining: usize,
    pub usage_ratio: f32,
    pub is_warning: bool,
    pub is_critical: bool,
    pub request_count: usize,
    pub avg_tokens_per_request: f32,
}

/// Result of a routing decision.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RoutingDecision {
    /// Chosen tier.
    pub tier: InferenceTier,
    /// Complexity assessment.
    pub assessment: ComplexityAssessment,
    /// Human-readable reason for the routing choice.
    pub reason: String,
    /// Latency budget (if specified).
    pub latency_budget_ms: Option<f64>,
}

/// Response from a routed inference call.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct InferenceResponse {
    /// The answer text.
    pub answer: String,
    /// Confidence in the answer (0.0–1.0).
    pub confidence: f32,
    /// Which tier produced this response.
    pub tier: InferenceTier,
    /// Total latency in milliseconds.
    pub latency_ms: f64,
    /// Whether the response was escalated from a lower tier.
    pub escalated: bool,
    /// Chain of tiers tried before reaching the final tier.
    pub escalation_chain: Vec<InferenceTier>,
    /// Additional metadata.
    pub metadata: HashMap<String, String>,
}

/// Trait for a tier handler — produces inference responses for a specific tier.
pub trait TierHandler: Send + Sync {
    /// Handle an inference request.
    ///
    /// Returns `(answer, confidence)` on success, or an error string on failure.
    fn handle(&self, prompt: &str, max_tokens: usize) -> Result<(String, f32), String>;

    /// Name of this handler (for logging).
    fn name(&self) -> &'static str;
}

/// Configuration for the inference router.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RouterConfig {
    /// Confidence threshold below which to escalate to a higher tier.
    pub confidence_threshold: f32,
    /// Maximum number of escalations before giving up.
    pub max_escalations: usize,
    /// Whether cloud tier is available.
    pub cloud_available: bool,
    /// Total token budget for the session.
    pub token_budget: usize,
}

impl Default for RouterConfig {
    fn default() -> Self {
        Self {
            confidence_threshold: 0.5,
            max_escalations: 2,
            cloud_available: true,
            token_budget: 100_000,
        }
    }
}

impl RouterConfig {
    /// Create config from environment variables.
    ///
    /// Env vars:
    /// - `WM_ROUTER_CONFIDENCE_THRESHOLD` (default 0.5)
    /// - `WM_ROUTER_MAX_ESCALATIONS` (default 2)
    /// - `WM_ROUTER_CLOUD_AVAILABLE` (default 1)
    /// - `WM_ROUTER_TOKEN_BUDGET` (default 100000)
    #[must_use]
    pub fn from_env() -> Self {
        let mut config = Self::default();

        if let Ok(val) = std::env::var("WM_ROUTER_CONFIDENCE_THRESHOLD") {
            if let Ok(parsed) = val.parse::<f32>() {
                config.confidence_threshold = parsed;
            }
        }

        if let Ok(val) = std::env::var("WM_ROUTER_MAX_ESCALATIONS") {
            if let Ok(parsed) = val.parse::<usize>() {
                config.max_escalations = parsed;
            }
        }

        if let Ok(val) = std::env::var("WM_ROUTER_CLOUD_AVAILABLE") {
            config.cloud_available = val != "0" && val.to_lowercase() != "false";
        }

        if let Ok(val) = std::env::var("WM_ROUTER_TOKEN_BUDGET") {
            if let Ok(parsed) = val.parse::<usize>() {
                config.token_budget = parsed;
            }
        }

        config
    }
}

/// Complexity-aware inference router with confidence cascading.
///
/// Routes prompts to the appropriate inference tier based on complexity
/// classification, then cascades to higher tiers if confidence is low.
///
/// # Example
/// ```no_run
/// use wm_bicameral::router::*;
///
/// let router = InferenceRouter::new(RouterConfig::default());
/// // Register handlers for each tier...
/// // let response = router.route("What is the capital of France?", None, None, false);
/// ```
pub struct InferenceRouter {
    classifier: ComplexityClassifier,
    config: RouterConfig,
    budget_tracker: TokenBudgetTracker,
    handlers: HashMap<InferenceTier, Arc<dyn TierHandler>>,
    calibrator: ConformalCalibrator,
    /// Collects (prompt, response, label) triples for LoRA fine-tuning
    training_data: TrainingDataCollector,
}

impl InferenceRouter {
    /// Create a new inference router with the given config.
    #[must_use]
    pub fn new(config: RouterConfig) -> Self {
        let budget = config.token_budget;
        let mut calibrator = ConformalCalibrator::new(config.confidence_threshold);
        calibrator.warm_start();
        Self {
            classifier: ComplexityClassifier::new(),
            budget_tracker: TokenBudgetTracker::new(budget),
            handlers: HashMap::new(),
            calibrator,
            training_data: TrainingDataCollector::default_capacity(),
            config,
        }
    }

    /// Create a router from environment variables.
    #[must_use]
    pub fn from_env() -> Self {
        Self::new(RouterConfig::from_env())
    }

    /// Register a handler for a specific tier.
    pub fn register_handler(&mut self, tier: InferenceTier, handler: Arc<dyn TierHandler>) {
        self.handlers.insert(tier, handler);
    }

    /// Check if a handler is registered for the given tier.
    #[must_use]
    pub fn has_handler(&self, tier: InferenceTier) -> bool {
        self.handlers.contains_key(&tier)
    }

    /// Add a calibration sample to the conformal calibrator.
    ///
    /// Call this after verifying whether a response was correct:
    /// `router.add_calibration_sample(raw_confidence, was_correct)`.
    /// After collecting enough samples (≥10), call `fit_calibrator()`.
    pub fn add_calibration_sample(&mut self, raw_confidence: f32, correct: bool) {
        self.calibrator.add_sample(raw_confidence, correct);
    }

    /// Fit the conformal calibrator using collected samples.
    ///
    /// After fitting, the router will use the calibrated threshold
    /// for cascade escalation decisions instead of the fixed threshold.
    pub fn fit_calibrator(&mut self) {
        self.calibrator.fit();
    }

    /// Whether the conformal calibrator has been fitted.
    #[must_use]
    pub const fn is_calibrated(&self) -> bool {
        self.calibrator.is_fitted()
    }

    /// Get the number of collected training samples.
    #[must_use]
    pub fn training_sample_count(&self) -> usize {
        self.training_data.len()
    }

    /// Get the number of positive (verified correct) training samples.
    #[must_use]
    pub fn training_positive_count(&self) -> usize {
        self.training_data.positive_count()
    }

    /// Export training data to JSONL format.
    ///
    /// Only positive (verified correct) samples are exported by default.
    /// Set `include_negative=true` to also export failed verifications.
    #[must_use]
    pub fn export_training_data(&self, include_negative: bool) -> String {
        self.training_data.export_jsonl(include_negative)
    }

    /// Export training data in llama.cpp fine-tuning format.
    #[must_use]
    pub fn export_training_data_llama_cpp(&self) -> String {
        self.training_data.export_llama_cpp()
    }

    /// Export training data in OpenAI chat format.
    #[must_use]
    pub fn export_training_data_chat(&self) -> String {
        self.training_data.export_chat()
    }

    /// Clear all collected training data.
    pub fn clear_training_data(&mut self) {
        self.training_data.clear();
    }

    /// Route a prompt to the appropriate inference tier.
    ///
    /// This classifies the prompt, selects a starting tier, and cascades
    /// to higher tiers if the response confidence is below threshold.
    ///
    /// # Parameters
    /// - `prompt`: The user prompt.
    /// - `max_output_tokens`: Expected output length (if known).
    /// - `latency_budget_ms`: Maximum acceptable latency.
    /// - `is_background`: Whether this is a background task.
    /// - `force_tier`: Override routing and force a specific tier.
    #[must_use]
    pub fn route(
        &mut self,
        prompt: &str,
        max_output_tokens: Option<usize>,
        latency_budget_ms: Option<f64>,
        is_background: bool,
        force_tier: Option<InferenceTier>,
    ) -> InferenceResponse {
        let start = Instant::now();

        let assessment =
            self.classifier
                .classify(prompt, max_output_tokens, latency_budget_ms, is_background);

        let (mut tier, reason) = if let Some(forced) = force_tier {
            (forced, "forced".to_string())
        } else {
            (assessment.tier, assessment.task_type.clone())
        };

        // Token budget downgrade
        if let Some(downgraded) = self.budget_tracker.recommend_downgrade(tier) {
            tier = downgraded;
        }

        // Cloud availability check
        if tier == InferenceTier::Cloud && !self.config.cloud_available {
            tier = InferenceTier::LocalLarge;
        }

        // Confidence cascading loop
        let mut escalation_chain = Vec::new();
        let mut escalations = 0;
        let mut current_tier = tier;
        let mut last_answer = String::new();
        let mut last_confidence = 0.0_f32;

        while current_tier <= InferenceTier::Cloud {
            let handler = if let Some(h) = self.handlers.get(&current_tier) {
                Arc::clone(h)
            } else {
                // No handler for this tier — escalate
                if let Some(next) = current_tier.escalate() {
                    escalation_chain.push(current_tier);
                    current_tier = next;
                    escalations += 1;
                    continue;
                }
                // No higher tier — return fallback
                return InferenceResponse {
                    answer: "No inference handler available for any tier.".into(),
                    confidence: 0.0,
                    tier: current_tier,
                    latency_ms: start.elapsed().as_secs_f64() * 1000.0,
                    escalated: !escalation_chain.is_empty(),
                    escalation_chain,
                    metadata: self.build_metadata(&assessment, &reason),
                };
            };

            let max_tokens = max_output_tokens.unwrap_or(assessment.estimated_output_tokens);

            match handler.handle(prompt, max_tokens) {
                Ok((answer, confidence)) => {
                    last_answer = answer;
                    // Calibrate raw confidence using conformal calibration
                    let calibrated = self.calibrator.calibrate(confidence);
                    last_confidence = calibrated;

                    // Use calibrated threshold if available, else fixed threshold
                    let threshold = if self.calibrator.is_fitted() {
                        self.calibrator.threshold()
                    } else {
                        self.config.confidence_threshold
                    };

                    // Check if we should escalate
                    if calibrated < threshold
                        && escalations < self.config.max_escalations
                        && !assessment.is_sensitive
                    {
                        // Self-verification: ask the same model to verify its answer.
                        // This is the AutoMix (NeurIPS 2024) pattern — cheaper than
                        // immediately escalating to a larger model.
                        let verified = self.self_verify(
                            &handler,
                            prompt,
                            &last_answer,
                            &assessment.task_type,
                            current_tier,
                        );
                        if verified {
                            // Model verified its own answer — boost confidence
                            last_confidence = last_confidence.max(0.6);
                        } else if let Some(next) = current_tier.escalate() {
                            escalation_chain.push(current_tier);
                            current_tier = next;
                            escalations += 1;
                            continue;
                        }
                    }

                    // Success — record token usage
                    let input_tokens = prompt.split_whitespace().count() * 2;
                    let output_tokens = last_answer.split_whitespace().count() * 2;
                    self.budget_tracker
                        .record_usage(input_tokens, output_tokens);

                    return InferenceResponse {
                        answer: last_answer,
                        confidence: last_confidence,
                        tier: current_tier,
                        latency_ms: start.elapsed().as_secs_f64() * 1000.0,
                        escalated: !escalation_chain.is_empty(),
                        escalation_chain,
                        metadata: self.build_metadata(&assessment, &reason),
                    };
                }
                Err(e) => {
                    tracing::warn!(
                        tier = %current_tier,
                        error = %e,
                        "tier handler failed, escalating"
                    );

                    if let Some(next) = current_tier.escalate() {
                        if escalations < self.config.max_escalations {
                            escalation_chain.push(current_tier);
                            current_tier = next;
                            escalations += 1;
                            continue;
                        }
                    }

                    // Can't escalate further
                    return InferenceResponse {
                        answer: format!("Error: {e}"),
                        confidence: 0.0,
                        tier: current_tier,
                        latency_ms: start.elapsed().as_secs_f64() * 1000.0,
                        escalated: !escalation_chain.is_empty(),
                        escalation_chain,
                        metadata: self.build_metadata(&assessment, &reason),
                    };
                }
            }
        }

        // Exhausted all escalations
        InferenceResponse {
            answer: last_answer,
            confidence: last_confidence,
            tier: current_tier,
            latency_ms: start.elapsed().as_secs_f64() * 1000.0,
            escalated: true,
            escalation_chain,
            metadata: self.build_metadata(&assessment, &reason),
        }
    }

    /// Self-verification: ask the same model to verify its own answer.
    ///
    /// Uses the AutoMix (NeurIPS 2024) pattern — the model checks its own
    /// output with a verification prompt. If the model says the answer is
    /// correct and complete, we trust it and avoid escalating to a larger
    /// model. This saves the cost of running the verify model on every
    /// low-confidence response.
    ///
    /// The verification prompt is tailored to the task type for more
    /// accurate verification.
    fn self_verify(
        &mut self,
        handler: &Arc<dyn TierHandler>,
        original_prompt: &str,
        answer: &str,
        task_type: &str,
        tier: InferenceTier,
    ) -> bool {
        let verify_prompt = self::build_verify_prompt(original_prompt, answer, task_type);

        match handler.handle(&verify_prompt, 32) {
            Ok((response, verify_confidence)) => {
                let lower = response.to_lowercase();
                let starts_with_yes = lower.trim_start().starts_with("yes");
                let result = starts_with_yes && verify_confidence >= 0.5;

                // Auto-collect calibration sample: use verification result
                // as a proxy label. This is noisy but provides a starting
                // point for conformal calibration until external feedback
                // is available.
                self.calibrator.add_sample(verify_confidence, result);

                // Collect training data for LoRA fine-tuning
                self.training_data.add(TrainingSample {
                    prompt: original_prompt.to_string(),
                    response: answer.to_string(),
                    raw_confidence: verify_confidence,
                    verified_correct: result,
                    tier: format!("{tier:?}"),
                    task_type: task_type.to_string(),
                    timestamp: std::time::SystemTime::now()
                        .duration_since(std::time::UNIX_EPOCH)
                        .unwrap_or_default()
                        .as_secs(),
                });

                // Re-fit periodically as real samples accumulate
                // (warm_start pre-seeds ~22 samples, so 50 = ~28 real samples)
                if self.calibrator.sample_count() % 50 == 0 {
                    self.calibrator.fit();
                    tracing::info!(
                        samples = self.calibrator.sample_count(),
                        threshold = self.calibrator.threshold(),
                        training_samples = self.training_data.len(),
                        "conformal calibrator re-fitted"
                    );
                }

                result
            }
            Err(_) => {
                // Verification failed — don't block escalation
                false
            }
        }
    }

    /// Build the metadata map from an assessment.
    fn build_metadata(
        &self,
        assessment: &ComplexityAssessment,
        reason: &str,
    ) -> HashMap<String, String> {
        let mut meta = assessment.signals.clone();
        meta.insert("task_type".into(), assessment.task_type.clone());
        meta.insert("reason".into(), reason.to_string());
        meta.insert(
            "estimated_output_tokens".into(),
            assessment.estimated_output_tokens.to_string(),
        );
        meta.insert(
            "token_budget_remaining".into(),
            self.budget_tracker.remaining().to_string(),
        );
        meta
    }

    /// Get the budget tracker summary.
    #[must_use]
    pub fn budget_summary(&self) -> BudgetSummary {
        self.budget_tracker.summary()
    }

    /// Classify a prompt's complexity without routing.
    ///
    /// Returns the complexity assessment including recommended tier.
    #[must_use]
    pub fn classify(
        &self,
        prompt: &str,
        max_output_tokens: Option<usize>,
        latency_budget_ms: Option<f64>,
        is_background: bool,
    ) -> ComplexityAssessment {
        self.classifier
            .classify(prompt, max_output_tokens, latency_budget_ms, is_background)
    }

    /// Get the router configuration.
    #[must_use]
    pub const fn config(&self) -> &RouterConfig {
        &self.config
    }

    /// Reset the token budget tracker.
    pub const fn reset_budget(&mut self, new_budget: Option<usize>) {
        self.budget_tracker.reset(new_budget);
    }
}

/// Build a task-specific verification prompt for self-verification.
///
/// Different task types have different correctness criteria:
/// - Factual Q&A: check if the answer is accurate and directly answers the question
/// - Coding: check if the code is syntactically valid and addresses the requirement
/// - Summarization: check if the summary captures key points without hallucination
/// - Classification: check if the category is appropriate
/// - Default: generic correctness check
fn build_verify_prompt(question: &str, answer: &str, task_type: &str) -> String {
    let criteria = match task_type {
        "factual_qa" | "definition" => {
            "Is this answer factually accurate and does it directly answer the question?"
        }
        "computation" => "Is this calculation correct? Verify each step.",
        "coding" => "Is this code syntactically valid and does it solve the stated problem?",
        "summarization" => {
            "Does this summary capture the key points without adding fabricated information?"
        }
        "classification" => "Is this classification correct and appropriate for the input?",
        "extraction" => "Did the extraction correctly identify all requested information?",
        "listing" => "Does this list contain all relevant items and are they accurate?",
        "analysis" | "reasoning" => {
            "Is the reasoning sound and are the conclusions supported by evidence?"
        }
        "comparison" => {
            "Does this comparison fairly represent both sides and cover the key differences?"
        }
        _ => "Is this answer correct, accurate, and complete?",
    };

    format!(
        "Question: {question}\n\
         Answer: {answer}\n\
         {criteria} \
         Respond with only 'YES' or 'NO' followed by a brief reason."
    )
}

#[cfg(test)]
mod tests {
    use super::*;

    // --- InferenceTier tests ---

    #[test]
    fn tier_ordering() {
        assert!(InferenceTier::EdgeRules < InferenceTier::LocalLlamaCpp);
        assert!(InferenceTier::LocalSmall < InferenceTier::LocalLarge);
        assert!(InferenceTier::LocalLarge < InferenceTier::Cloud);
    }

    #[test]
    fn tier_escalate() {
        assert_eq!(
            InferenceTier::EdgeRules.escalate(),
            Some(InferenceTier::LocalLlamaCpp)
        );
        assert_eq!(
            InferenceTier::LocalLarge.escalate(),
            Some(InferenceTier::Cloud)
        );
        assert_eq!(InferenceTier::Cloud.escalate(), None);
    }

    #[test]
    fn tier_as_str() {
        assert_eq!(InferenceTier::EdgeRules.as_str(), "edge_rules");
        assert_eq!(InferenceTier::Cloud.as_str(), "cloud");
    }

    #[test]
    fn tier_all() {
        let all = InferenceTier::all();
        assert_eq!(all.len(), 5);
        assert_eq!(all[0], InferenceTier::EdgeRules);
        assert_eq!(all[4], InferenceTier::Cloud);
    }

    // --- ComplexityClassifier tests ---

    #[test]
    fn classify_greeting() {
        let classifier = ComplexityClassifier::new();
        let result = classifier.classify("hello there", None, None, false);
        assert_eq!(result.tier, InferenceTier::EdgeRules);
        assert_eq!(result.task_type, "greeting");
        assert!(!result.is_sensitive);
    }

    #[test]
    fn classify_status_query() {
        let classifier = ComplexityClassifier::new();
        let result = classifier.classify("what version is this?", None, None, false);
        assert_eq!(result.tier, InferenceTier::EdgeRules);
        assert_eq!(result.task_type, "status_query");
    }

    #[test]
    fn classify_classification_task() {
        let classifier = ComplexityClassifier::new();
        let result =
            classifier.classify("classify this document into categories", None, None, false);
        assert_eq!(result.tier, InferenceTier::LocalSmall);
        assert_eq!(result.task_type, "classification");
    }

    #[test]
    fn classify_coding_task() {
        let classifier = ComplexityClassifier::new();
        let result =
            classifier.classify("implement a function to sort an array", None, None, false);
        assert_eq!(result.tier, InferenceTier::LocalLarge);
        assert_eq!(result.task_type, "coding");
    }

    #[test]
    fn classify_creative_task() {
        let classifier = ComplexityClassifier::new();
        let result =
            classifier.classify("write a creative story about a dragon", None, None, false);
        assert_eq!(result.tier, InferenceTier::Cloud);
        assert_eq!(result.task_type, "creative");
    }

    #[test]
    fn classify_sensitive_data() {
        let classifier = ComplexityClassifier::new();
        let result = classifier.classify(
            "my credit card number is 1234-5678-9012-3456",
            None,
            None,
            false,
        );
        assert!(result.is_sensitive);
        // Sensitive data should not route to cloud
        assert!(result.tier <= InferenceTier::LocalLarge);
    }

    #[test]
    fn classify_sensitive_password() {
        let classifier = ComplexityClassifier::new();
        let result = classifier.classify("the password is hunter2", None, None, false);
        assert!(result.is_sensitive);
    }

    #[test]
    fn classify_sensitive_medical() {
        let classifier = ComplexityClassifier::new();
        let result = classifier.classify("patient diagnosis: type 2 diabetes", None, None, false);
        assert!(result.is_sensitive);
    }

    #[test]
    fn classify_tool_call_requirement() {
        let classifier = ComplexityClassifier::new();
        let result = classifier.classify("search the memory for recent entries", None, None, false);
        assert!(result.needs_tool_calls);
        // Tool calls should escalate to at least LocalSmall
        assert!(result.tier >= InferenceTier::LocalSmall);
    }

    #[test]
    fn classify_multi_turn() {
        let classifier = ComplexityClassifier::new();
        let result =
            classifier.classify("first do X, then do Y, and finally do Z", None, None, false);
        assert!(result.is_multi_turn);
        assert!(result.tier >= InferenceTier::LocalSmall);
    }

    #[test]
    fn classify_short_query_no_pattern() {
        let classifier = ComplexityClassifier::new();
        let result = classifier.classify("what is rust?", None, None, false);
        // "what is" matches factual_qa pattern → LocalLlamaCpp
        assert_eq!(result.tier, InferenceTier::LocalLlamaCpp);
        assert_eq!(result.task_type, "factual_qa");
    }

    #[test]
    fn classify_long_query_no_pattern() {
        let classifier = ComplexityClassifier::new();
        let long_prompt = "word ".repeat(60);
        let result = classifier.classify(&long_prompt, None, None, false);
        // Long queries without pattern match default to LocalSmall (not LocalLarge)
        assert_eq!(result.tier, InferenceTier::LocalSmall);
        assert_eq!(result.task_type, "long_query");
    }

    #[test]
    fn classify_latency_budget_override() {
        let classifier = ComplexityClassifier::new();
        let result =
            classifier.classify("analyze the code and refactor it", None, Some(50.0), false);
        // Latency budget < 100ms should force EdgeRules
        assert_eq!(result.tier, InferenceTier::EdgeRules);
    }

    #[test]
    fn classify_latency_budget_moderate() {
        let classifier = ComplexityClassifier::new();
        let result =
            classifier.classify("analyze the code and refactor it", None, Some(300.0), false);
        // Latency budget < 500ms should cap at LocalSmall
        assert!(result.tier <= InferenceTier::LocalSmall);
    }

    #[test]
    fn classify_token_budget_escalation() {
        let classifier = ComplexityClassifier::new();
        // Force high token estimate
        let result = classifier.classify("summarize this", Some(3000), None, false);
        assert_eq!(result.tier, InferenceTier::Cloud);
    }

    #[test]
    fn classify_background_task() {
        let classifier = ComplexityClassifier::new();
        let result = classifier.classify("hello", None, None, true);
        assert!(result.signals.contains_key("background_quality_boost"));
    }

    #[test]
    fn classify_max_local_tier_sensitive() {
        let classifier = ComplexityClassifier::new();
        let result = classifier.classify(
            "research the patient medical record literature",
            None,
            None,
            false,
        );
        // "research" matches Cloud tier, but "patient"/"medical record" triggers sensitivity
        assert!(result.is_sensitive);
        assert_eq!(result.max_local_tier(), InferenceTier::LocalLarge);
    }

    #[test]
    fn classify_padding_does_not_force_cloud() {
        let classifier = ComplexityClassifier::new();
        // Pad a simple prompt with repeated tokens
        let padded = "simple question ".repeat(500);
        let result = classifier.classify(&padded, None, None, false);
        // Should not escalate to cloud despite high raw word count
        assert!(
            !result.requires_cloud(),
            "padded prompt should not force cloud tier"
        );
        assert!(
            result.signals.contains_key("padding_detected"),
            "padding_detected signal should be set"
        );
    }

    #[test]
    fn classify_padding_capped_to_local() {
        let classifier = ComplexityClassifier::new();
        // 500 repetitions of 2 words = 1000 words, but only 2 unique
        let padded = "hello world ".repeat(500);
        let result = classifier.classify(&padded, None, None, false);
        // Should stay at LocalSmall or LocalLarge, not Cloud
        assert!(
            result.tier <= InferenceTier::LocalLarge,
            "padded prompt should not exceed LocalLarge, got {:?}",
            result.tier
        );
    }

    #[test]
    fn classify_no_padding_for_diverse_prompt() {
        let classifier = ComplexityClassifier::new();
        // A genuinely long prompt with diverse vocabulary
        let diverse: String = (0..100).fold(String::new(), |mut s, i| {
            s.push_str("word");
            s.push_str(&i.to_string());
            s.push(' ');
            s
        });
        let result = classifier.classify(&diverse, None, None, false);
        // Should not trigger padding detection
        assert!(
            !result.signals.contains_key("padding_detected"),
            "diverse prompt should not trigger padding detection"
        );
    }

    // --- TokenBudgetTracker tests ---

    #[test]
    fn budget_tracker_initial_state() {
        let tracker = TokenBudgetTracker::new(100_000);
        assert_eq!(tracker.remaining(), 100_000);
        assert!((tracker.usage_ratio() - 0.0).abs() < 0.01);
        assert!(!tracker.is_warning());
        assert!(!tracker.is_critical());
    }

    #[test]
    fn budget_tracker_record_usage() {
        let mut tracker = TokenBudgetTracker::new(100_000);
        tracker.record_usage(500, 200);
        assert_eq!(tracker.remaining(), 99_300);
        assert!((tracker.usage_ratio() - 0.007).abs() < 0.01);
        assert_eq!(tracker.request_count, 1);
    }

    #[test]
    fn budget_tracker_warning_threshold() {
        let mut tracker = TokenBudgetTracker::new(1000);
        tracker.record_usage(700, 0);
        assert!(tracker.is_warning());
        assert!(!tracker.is_critical());
    }

    #[test]
    fn budget_tracker_critical_threshold() {
        let mut tracker = TokenBudgetTracker::new(1000);
        tracker.record_usage(900, 0);
        assert!(tracker.is_critical());
    }

    #[test]
    fn budget_tracker_recommend_downgrade_normal() {
        let tracker = TokenBudgetTracker::new(100_000);
        assert_eq!(tracker.recommend_downgrade(InferenceTier::Cloud), None);
    }

    #[test]
    fn budget_tracker_recommend_downgrade_warning() {
        let mut tracker = TokenBudgetTracker::new(1000);
        tracker.record_usage(700, 0);
        // Warning level: downgrade by one tier
        assert_eq!(
            tracker.recommend_downgrade(InferenceTier::Cloud),
            Some(InferenceTier::LocalLarge)
        );
    }

    #[test]
    fn budget_tracker_recommend_downgrade_critical() {
        let mut tracker = TokenBudgetTracker::new(1000);
        tracker.record_usage(900, 0);
        // Critical: downgrade to cheapest
        assert_eq!(
            tracker.recommend_downgrade(InferenceTier::Cloud),
            Some(InferenceTier::EdgeRules)
        );
    }

    #[test]
    fn budget_tracker_reset() {
        let mut tracker = TokenBudgetTracker::new(1000);
        tracker.record_usage(500, 0);
        tracker.reset(None);
        assert_eq!(tracker.remaining(), 1000);
        assert_eq!(tracker.request_count, 0);
    }

    #[test]
    fn budget_tracker_reset_with_new_budget() {
        let mut tracker = TokenBudgetTracker::new(1000);
        tracker.reset(Some(2000));
        assert_eq!(tracker.remaining(), 2000);
    }

    #[test]
    fn budget_tracker_ema_updates() {
        let mut tracker = TokenBudgetTracker::new(100_000);
        tracker.record_usage(100, 100);
        let ema1 = tracker.ema_usage;
        tracker.record_usage(200, 200);
        let ema2 = tracker.ema_usage;
        // EMA should increase but be between the two values
        assert!(ema2 > ema1);
        assert!(ema2 < 400.0);
    }

    // --- InferenceRouter tests ---

    /// A simple test handler that returns a fixed response.
    struct StubHandler {
        response: String,
        confidence: f32,
        should_fail: bool,
    }

    impl TierHandler for StubHandler {
        fn handle(&self, _prompt: &str, _max_tokens: usize) -> Result<(String, f32), String> {
            if self.should_fail {
                return Err("stub handler error".into());
            }
            Ok((self.response.clone(), self.confidence))
        }

        fn name(&self) -> &'static str {
            "stub"
        }
    }

    #[test]
    fn router_no_handlers_returns_fallback() {
        let mut router = InferenceRouter::new(RouterConfig::default());
        let response = router.route("hello", None, None, false, None);
        assert_eq!(response.confidence, 0.0);
        assert!(response.answer.contains("No inference handler"));
    }

    #[test]
    fn router_edge_handler_success() {
        let mut router = InferenceRouter::new(RouterConfig::default());
        router.register_handler(
            InferenceTier::EdgeRules,
            Arc::new(StubHandler {
                response: "Hi there!".into(),
                confidence: 0.95,
                should_fail: false,
            }),
        );

        let response = router.route("hello", None, None, false, None);
        assert_eq!(response.tier, InferenceTier::EdgeRules);
        // Warm-started calibrator maps 0.95 → ~1.0 (all high-confidence samples are correct)
        assert!(
            response.confidence > 0.9,
            "confidence should be high, got {}",
            response.confidence
        );
        assert_eq!(response.answer, "Hi there!");
        assert!(!response.escalated);
    }

    #[test]
    fn router_confidence_cascade() {
        let config = RouterConfig {
            confidence_threshold: 0.8,
            ..Default::default()
        };
        let mut router = InferenceRouter::new(config);

        // Edge handler with low confidence → should cascade
        router.register_handler(
            InferenceTier::EdgeRules,
            Arc::new(StubHandler {
                response: "low confidence response".into(),
                confidence: 0.3,
                should_fail: false,
            }),
        );
        // LocalLlamaCpp handler with high confidence → should stop here
        router.register_handler(
            InferenceTier::LocalLlamaCpp,
            Arc::new(StubHandler {
                response: "high confidence response".into(),
                confidence: 0.9,
                should_fail: false,
            }),
        );

        let response = router.route("hello", None, None, false, None);
        assert_eq!(response.tier, InferenceTier::LocalLlamaCpp);
        assert!(response.escalated);
        assert_eq!(response.escalation_chain, vec![InferenceTier::EdgeRules]);
    }

    #[test]
    fn router_handler_error_cascades() {
        let mut router = InferenceRouter::new(RouterConfig::default());

        router.register_handler(
            InferenceTier::EdgeRules,
            Arc::new(StubHandler {
                response: String::new(),
                confidence: 0.0,
                should_fail: true,
            }),
        );
        router.register_handler(
            InferenceTier::LocalLlamaCpp,
            Arc::new(StubHandler {
                response: "recovered".into(),
                confidence: 0.9,
                should_fail: false,
            }),
        );

        let response = router.route("hello", None, None, false, None);
        assert_eq!(response.tier, InferenceTier::LocalLlamaCpp);
        assert!(response.escalated);
    }

    #[test]
    fn router_sensitive_data_no_cloud() {
        let config = RouterConfig {
            confidence_threshold: 0.1, // Low threshold to prevent cascading
            cloud_available: true,
            ..Default::default()
        };
        let mut router = InferenceRouter::new(config);

        // Register all tiers
        for tier in InferenceTier::all() {
            router.register_handler(
                tier,
                Arc::new(StubHandler {
                    response: format!("response from {tier}"),
                    confidence: 0.95,
                    should_fail: false,
                }),
            );
        }

        let response = router.route("my credit card number is 1234", None, None, false, None);
        // Sensitive data should never reach cloud
        assert!(response.tier <= InferenceTier::LocalLarge);
    }

    #[test]
    fn router_force_tier() {
        let mut router = InferenceRouter::new(RouterConfig::default());
        router.register_handler(
            InferenceTier::Cloud,
            Arc::new(StubHandler {
                response: "cloud response".into(),
                confidence: 0.9,
                should_fail: false,
            }),
        );

        let response = router.route("hello", None, None, false, Some(InferenceTier::Cloud));
        assert_eq!(response.tier, InferenceTier::Cloud);
        assert_eq!(response.answer, "cloud response");
    }

    #[test]
    fn router_cloud_unavailable_fallback() {
        let config = RouterConfig {
            cloud_available: false,
            ..Default::default()
        };
        let mut router = InferenceRouter::new(config);
        router.register_handler(
            InferenceTier::LocalLarge,
            Arc::new(StubHandler {
                response: "local response".into(),
                confidence: 0.9,
                should_fail: false,
            }),
        );

        // "research" would normally route to Cloud
        let response = router.route(
            "research the literature on quantum computing",
            None,
            None,
            false,
            None,
        );
        assert_ne!(response.tier, InferenceTier::Cloud);
    }

    #[test]
    fn router_max_escalations_limit() {
        let config = RouterConfig {
            confidence_threshold: 0.99, // Always cascade
            max_escalations: 1,
            ..Default::default()
        };
        let mut router = InferenceRouter::new(config);

        // Register handlers that always return low confidence
        for tier in InferenceTier::all() {
            router.register_handler(
                tier,
                Arc::new(StubHandler {
                    response: format!("response from {tier}"),
                    confidence: 0.1,
                    should_fail: false,
                }),
            );
        }

        let response = router.route("hello", None, None, false, None);
        // Should stop after 1 escalation
        assert!(response.escalation_chain.len() <= 1);
    }

    #[test]
    fn router_budget_tracking() {
        let mut router = InferenceRouter::new(RouterConfig::default());
        router.register_handler(
            InferenceTier::EdgeRules,
            Arc::new(StubHandler {
                response: "hi".into(),
                confidence: 0.9,
                should_fail: false,
            }),
        );

        let _ = router.route("hello", None, None, false, None);
        let summary = router.budget_summary();
        assert_eq!(summary.request_count, 1);
        assert!(summary.used_tokens > 0);
    }

    #[test]
    fn router_reset_budget() {
        let mut router = InferenceRouter::new(RouterConfig::default());
        router.register_handler(
            InferenceTier::EdgeRules,
            Arc::new(StubHandler {
                response: "hi".into(),
                confidence: 0.9,
                should_fail: false,
            }),
        );

        let _ = router.route("hello", None, None, false, None);
        router.reset_budget(Some(50_000));
        let summary = router.budget_summary();
        assert_eq!(summary.total_budget, 50_000);
        assert_eq!(summary.used_tokens, 0);
    }

    #[test]
    fn router_config_default_values() {
        let config = RouterConfig::default();
        assert!((config.confidence_threshold - 0.5).abs() < 0.01);
        assert_eq!(config.max_escalations, 2);
        assert!(config.cloud_available);
        assert_eq!(config.token_budget, 100_000);
    }

    #[test]
    fn routing_decision_serialization() {
        let assessment = ComplexityAssessment {
            tier: InferenceTier::LocalSmall,
            task_type: "classification".into(),
            confidence: 0.75,
            estimated_output_tokens: 128,
            is_sensitive: false,
            needs_tool_calls: false,
            is_multi_turn: false,
            signals: HashMap::new(),
        };
        let decision = RoutingDecision {
            tier: InferenceTier::LocalSmall,
            assessment,
            reason: "classification".into(),
            latency_budget_ms: None,
        };
        let json = serde_json::to_string(&decision).unwrap();
        let decoded: RoutingDecision = serde_json::from_str(&json).unwrap();
        assert_eq!(decoded.tier, InferenceTier::LocalSmall);
    }

    #[test]
    fn inference_response_serialization() {
        let response = InferenceResponse {
            answer: "test answer".into(),
            confidence: 0.8,
            tier: InferenceTier::LocalLarge,
            latency_ms: 42.0,
            escalated: true,
            escalation_chain: vec![InferenceTier::EdgeRules, InferenceTier::LocalLlamaCpp],
            metadata: HashMap::new(),
        };
        let json = serde_json::to_string(&response).unwrap();
        let decoded: InferenceResponse = serde_json::from_str(&json).unwrap();
        assert_eq!(decoded.answer, "test answer");
        assert!(decoded.escalated);
        assert_eq!(decoded.escalation_chain.len(), 2);
    }

    #[test]
    fn budget_summary_serialization() {
        let summary = BudgetSummary {
            total_budget: 100_000,
            used_tokens: 30_000,
            remaining: 70_000,
            usage_ratio: 0.3,
            is_warning: false,
            is_critical: false,
            request_count: 5,
            avg_tokens_per_request: 6000.0,
        };
        let json = serde_json::to_string(&summary).unwrap();
        let decoded: BudgetSummary = serde_json::from_str(&json).unwrap();
        assert_eq!(decoded.total_budget, 100_000);
        assert_eq!(decoded.request_count, 5);
    }
}

// ── LoRA Training Data Collection ─────────────────────────────────────

/// A training sample for LoRA fine-tuning: (prompt, response, label).
///
/// Collected during self-verification — when the model verifies its own
/// answer as correct, we store the (prompt, response) pair as a positive
/// training example. When verification fails, we store it as a negative
/// example (useful for DPO/RLHF but not for SFT).
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct TrainingSample {
    /// The original user prompt
    pub prompt: String,
    /// The model's response
    pub response: String,
    /// Raw model confidence (pre-calibration)
    pub raw_confidence: f32,
    /// Whether self-verification passed
    pub verified_correct: bool,
    /// Which inference tier produced this response
    pub tier: String,
    /// Task type classification
    pub task_type: String,
    /// Unix timestamp of collection
    pub timestamp: u64,
}

/// Collects training samples during inference for LoRA fine-tuning.
///
/// The collector stores (prompt, response, verified_correct) triples
/// whenever self-verification runs. These can be exported to JSONL
/// format for use with llama.cpp's LoRA training pipeline.
///
/// Only samples where `verified_correct=true` should be used for
/// supervised fine-tuning (SFT). Samples where `verified_correct=false`
/// are useful for DPO/RLHF preference learning.
pub struct TrainingDataCollector {
    samples: Vec<TrainingSample>,
    /// Maximum samples to retain (ring buffer)
    max_samples: usize,
}

impl TrainingDataCollector {
    /// Create a new collector with the given capacity.
    #[must_use]
    pub fn new(max_samples: usize) -> Self {
        Self {
            samples: Vec::with_capacity(max_samples.min(10_000)),
            max_samples,
        }
    }

    /// Create a collector with default capacity (10,000 samples).
    #[must_use]
    pub fn default_capacity() -> Self {
        Self::new(10_000)
    }

    /// Add a training sample.
    pub fn add(&mut self, sample: TrainingSample) {
        if self.samples.len() >= self.max_samples {
            self.samples.remove(0); // Ring buffer: drop oldest
        }
        self.samples.push(sample);
    }

    /// Number of collected samples.
    #[must_use]
    pub fn len(&self) -> usize {
        self.samples.len()
    }

    /// Whether the collector is empty.
    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.samples.is_empty()
    }

    /// Number of positive (verified correct) samples.
    #[must_use]
    pub fn positive_count(&self) -> usize {
        self.samples.iter().filter(|s| s.verified_correct).count()
    }

    /// Number of negative (verification failed) samples.
    #[must_use]
    pub fn negative_count(&self) -> usize {
        self.samples.iter().filter(|s| !s.verified_correct).count()
    }

    /// Export samples to JSONL format (one JSON object per line).
    ///
    /// Only positive samples (verified_correct=true) are exported by
    /// default, as these are suitable for supervised fine-tuning.
    /// Set `include_negative=true` to also export failed verifications
    /// (useful for DPO/RLHF).
    #[must_use]
    pub fn export_jsonl(&self, include_negative: bool) -> String {
        self.samples
            .iter()
            .filter(|s| include_negative || s.verified_correct)
            .map(|s| serde_json::to_string(s).unwrap_or_default())
            .collect::<Vec<_>>()
            .join("\n")
    }

    /// Export positive samples to llama.cpp training format.
    ///
    /// Format: `{ "prompt": "...", "completion": "..." }` per line.
    /// This is the format expected by llama.cpp's `--finetune` command
    /// with `--train-data` flag.
    #[must_use]
    pub fn export_llama_cpp(&self) -> String {
        self.samples
            .iter()
            .filter(|s| s.verified_correct)
            .map(|s| {
                serde_json::json!({
                    "prompt": s.prompt,
                    "completion": s.response,
                })
                .to_string()
            })
            .collect::<Vec<_>>()
            .join("\n")
    }

    /// Export to OpenAI chat format for general fine-tuning.
    ///
    /// Format: `{ "messages": [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}] }` per line.
    #[must_use]
    pub fn export_chat(&self) -> String {
        self.samples
            .iter()
            .filter(|s| s.verified_correct)
            .map(|s| {
                serde_json::json!({
                    "messages": [
                        {"role": "user", "content": s.prompt},
                        {"role": "assistant", "content": s.response},
                    ]
                })
                .to_string()
            })
            .collect::<Vec<_>>()
            .join("\n")
    }

    /// Clear all collected samples.
    pub fn clear(&mut self) {
        self.samples.clear();
    }
}

// ── Conformal Calibration ─────────────────────────────────────────────

/// A calibration sample: (raw confidence, was the answer correct?).
#[derive(Debug, Clone)]
struct CalibrationSample {
    raw_confidence: f32,
    correct: bool,
}

/// Lightweight conformal calibration for cascade threshold tuning.
///
/// Implements isotonic regression on (confidence, correctness) pairs to
/// map raw model confidence to a calibrated error probability. The
/// calibrated threshold is cost-optimal under the UCCI framework.
///
/// In practice, calibration samples are collected by running the small
/// model on a held-out set and recording whether each answer was correct.
/// The calibrator then produces a threshold that bounds the error rate.
pub struct ConformalCalibrator {
    samples: Vec<CalibrationSample>,
    /// Calibrated threshold — escalate when calibrated confidence < threshold.
    threshold: f32,
    /// Whether calibration has been fitted.
    fitted: bool,
}

impl ConformalCalibrator {
    /// Create a new calibrator with a default threshold.
    #[must_use]
    pub const fn new(default_threshold: f32) -> Self {
        Self {
            samples: Vec::new(),
            threshold: default_threshold,
            fitted: false,
        }
    }

    /// Pre-seed the calibrator with known confidence patterns from Qwen 2.5
    /// logprobs data. This allows the calibrator to be useful from the first
    /// call instead of requiring 50 real samples before fitting.
    ///
    /// Patterns observed in benchmarks:
    /// - High confidence (>0.9) → almost always correct (factual QA, simple math)
    /// - Medium confidence (0.7-0.9) → usually correct but some hallucination
    /// - Low confidence (<0.7) → often incorrect or incomplete
    pub fn warm_start(&mut self) {
        // High confidence — correct
        for conf in [0.94, 0.92, 0.91, 0.90, 0.88, 0.86, 0.85] {
            self.add_sample(conf, true);
        }
        // Medium-high confidence — mostly correct
        for conf in [0.82, 0.80, 0.78, 0.76, 0.75] {
            self.add_sample(conf, true);
        }
        // Medium confidence — mixed
        self.add_sample(0.72, true);
        self.add_sample(0.70, false);
        self.add_sample(0.68, true);
        self.add_sample(0.66, false);
        // Low confidence — mostly incorrect
        for conf in [0.60, 0.55, 0.50, 0.45, 0.40] {
            self.add_sample(conf, false);
        }
        // Very low confidence — incorrect
        for conf in [0.35, 0.30, 0.25] {
            self.add_sample(conf, false);
        }
        self.fit();
    }

    /// Add a calibration sample.
    pub fn add_sample(&mut self, raw_confidence: f32, correct: bool) {
        self.samples.push(CalibrationSample {
            raw_confidence,
            correct,
        });
    }

    /// Fit the calibrator using isotonic regression on collected samples.
    ///
    /// Computes the calibrated threshold as the confidence value that
    /// separates correct from incorrect answers with minimum error.
    /// Uses a simple sorted-split approach (O(n log n)).
    pub fn fit(&mut self) {
        if self.samples.len() < 10 {
            // Not enough data — keep default threshold
            return;
        }

        // Sort by raw confidence
        self.samples.sort_by(|a, b| {
            a.raw_confidence
                .partial_cmp(&b.raw_confidence)
                .unwrap_or(std::cmp::Ordering::Equal)
        });

        // Find the threshold that minimizes misclassification
        // (incorrect answers above threshold + correct answers below)
        let n = self.samples.len();
        let mut best_threshold = self.threshold;
        let mut best_error = usize::MAX;

        for i in 0..n {
            let threshold = self.samples[i].raw_confidence;
            let mut errors = 0;
            for sample in &self.samples {
                if sample.raw_confidence >= threshold && !sample.correct {
                    errors += 1; // False accept
                }
                if sample.raw_confidence < threshold && sample.correct {
                    errors += 1; // False reject
                }
            }
            if errors < best_error {
                best_error = errors;
                best_threshold = threshold;
            }
        }

        self.threshold = best_threshold;
        self.fitted = true;
    }

    /// Get the calibrated threshold for cascade escalation.
    #[must_use]
    pub const fn threshold(&self) -> f32 {
        self.threshold
    }

    /// Whether the calibrator has been fitted with enough data.
    #[must_use]
    pub const fn is_fitted(&self) -> bool {
        self.fitted
    }

    /// Calibrate a raw confidence score using isotonic regression.
    ///
    /// Returns the calibrated probability of correctness.
    #[must_use]
    pub fn calibrate(&self, raw_confidence: f32) -> f32 {
        if !self.fitted || self.samples.is_empty() {
            return raw_confidence;
        }

        // Binary search for the position in sorted samples
        let pos = self
            .samples
            .partition_point(|s| s.raw_confidence < raw_confidence);

        // Compute empirical correctness rate around this confidence level
        let window = 5.min(self.samples.len());
        let start = pos.saturating_sub(window / 2);
        let end = (start + window).min(self.samples.len());

        let correct_in_window: usize = self.samples[start..end]
            .iter()
            .filter(|s| s.correct)
            .count();
        correct_in_window as f32 / (end - start) as f32
    }

    /// Number of calibration samples collected.
    #[must_use]
    pub fn sample_count(&self) -> usize {
        self.samples.len()
    }
}

impl Default for ConformalCalibrator {
    fn default() -> Self {
        Self::new(0.5)
    }
}

#[cfg(test)]
mod conformal_tests {
    use super::*;

    #[test]
    fn calibrator_default_threshold() {
        let cal = ConformalCalibrator::new(0.6);
        assert!((cal.threshold() - 0.6).abs() < 0.01);
        assert!(!cal.is_fitted());
    }

    #[test]
    fn calibrator_fit_with_samples() {
        let mut cal = ConformalCalibrator::new(0.5);
        // Low confidence → mostly incorrect
        for i in 0..20 {
            cal.add_sample((i as f32).mul_add(0.01, 0.1), i < 3);
        }
        // High confidence → mostly correct
        for i in 0..20 {
            cal.add_sample((i as f32).mul_add(0.01, 0.7), i >= 2);
        }
        cal.fit();
        assert!(cal.is_fitted());
        // Threshold should be somewhere between 0.3 and 0.7
        assert!(cal.threshold() > 0.2 && cal.threshold() < 0.8);
    }

    #[test]
    fn calibrator_insufficient_samples() {
        let mut cal = ConformalCalibrator::new(0.5);
        cal.add_sample(0.3, false);
        cal.add_sample(0.8, true);
        cal.fit();
        // Should not fit with < 10 samples
        assert!(!cal.is_fitted());
        assert!((cal.threshold() - 0.5).abs() < 0.01);
    }

    #[test]
    fn calibrator_calibrate_returns_raw_when_unfitted() {
        let cal = ConformalCalibrator::new(0.5);
        let calibrated = cal.calibrate(0.7);
        assert!((calibrated - 0.7).abs() < 0.01);
    }

    #[test]
    fn calibrator_sample_count() {
        let mut cal = ConformalCalibrator::new(0.5);
        assert_eq!(cal.sample_count(), 0);
        cal.add_sample(0.3, true);
        cal.add_sample(0.7, false);
        assert_eq!(cal.sample_count(), 2);
    }

    #[test]
    fn calibrator_warm_start_fits() {
        let mut cal = ConformalCalibrator::new(0.5);
        assert!(!cal.is_fitted());
        assert_eq!(cal.sample_count(), 0);
        cal.warm_start();
        assert!(cal.is_fitted());
        assert!(cal.sample_count() >= 20);
    }

    #[test]
    fn calibrator_warm_start_high_confidence() {
        let mut cal = ConformalCalibrator::new(0.5);
        cal.warm_start();
        // High confidence should calibrate to high probability
        let calibrated = cal.calibrate(0.95);
        assert!(
            calibrated > 0.8,
            "high confidence should stay high, got {calibrated}"
        );
    }

    #[test]
    fn calibrator_warm_start_low_confidence() {
        let mut cal = ConformalCalibrator::new(0.5);
        cal.warm_start();
        // Low confidence should calibrate to low probability
        let calibrated = cal.calibrate(0.30);
        assert!(
            calibrated < 0.3,
            "low confidence should stay low, got {calibrated}"
        );
    }
}

#[cfg(test)]
mod verify_prompt_tests {
    use super::*;

    #[test]
    fn verify_prompt_factual_qa() {
        let p = build_verify_prompt("What is 2+2?", "4", "factual_qa");
        assert!(p.contains("factually accurate"));
        assert!(p.contains("YES"));
    }

    #[test]
    fn verify_prompt_coding() {
        let p = build_verify_prompt("Write a sort function", "fn sort() {}", "coding");
        assert!(p.contains("syntactically valid"));
    }

    #[test]
    fn verify_prompt_default() {
        let p = build_verify_prompt("Tell me about Rust", "Rust is...", "unknown_type");
        assert!(p.contains("correct, accurate, and complete"));
    }

    #[test]
    fn verify_prompt_summarization() {
        let p = build_verify_prompt("Summarize this", "Short summary", "summarization");
        assert!(p.contains("key points"));
        assert!(p.contains("fabricated"));
    }

    // ── Training Data Collector tests ──

    #[test]
    fn training_collector_default_capacity() {
        let collector = TrainingDataCollector::default_capacity();
        assert!(collector.is_empty());
        assert_eq!(collector.len(), 0);
    }

    #[test]
    fn training_collector_add_and_count() {
        let mut collector = TrainingDataCollector::new(100);
        collector.add(TrainingSample {
            prompt: "What is 2+2?".into(),
            response: "4".into(),
            raw_confidence: 0.95,
            verified_correct: true,
            tier: "EdgeRules".into(),
            task_type: "math".into(),
            timestamp: 0,
        });
        collector.add(TrainingSample {
            prompt: "What is the capital of France?".into(),
            response: "London".into(),
            raw_confidence: 0.4,
            verified_correct: false,
            tier: "LocalSmall".into(),
            task_type: "factual_qa".into(),
            timestamp: 0,
        });
        assert_eq!(collector.len(), 2);
        assert_eq!(collector.positive_count(), 1);
        assert_eq!(collector.negative_count(), 1);
    }

    #[test]
    fn training_collector_export_jsonl_positive_only() {
        let mut collector = TrainingDataCollector::new(100);
        collector.add(TrainingSample {
            prompt: "What is 2+2?".into(),
            response: "4".into(),
            raw_confidence: 0.95,
            verified_correct: true,
            tier: "EdgeRules".into(),
            task_type: "math".into(),
            timestamp: 100,
        });
        collector.add(TrainingSample {
            prompt: "Capital of France?".into(),
            response: "London".into(),
            raw_confidence: 0.4,
            verified_correct: false,
            tier: "LocalSmall".into(),
            task_type: "factual_qa".into(),
            timestamp: 200,
        });
        let jsonl = collector.export_jsonl(false);
        let lines: Vec<&str> = jsonl.lines().collect();
        assert_eq!(lines.len(), 1); // Only positive
        assert!(lines[0].contains("What is 2+2?"));
    }

    #[test]
    fn training_collector_export_jsonl_with_negative() {
        let mut collector = TrainingDataCollector::new(100);
        collector.add(TrainingSample {
            prompt: "test1".into(),
            response: "resp1".into(),
            raw_confidence: 0.9,
            verified_correct: true,
            tier: "EdgeRules".into(),
            task_type: "test".into(),
            timestamp: 0,
        });
        collector.add(TrainingSample {
            prompt: "test2".into(),
            response: "resp2".into(),
            raw_confidence: 0.3,
            verified_correct: false,
            tier: "LocalSmall".into(),
            task_type: "test".into(),
            timestamp: 0,
        });
        let jsonl = collector.export_jsonl(true);
        assert_eq!(jsonl.lines().count(), 2); // Both
    }

    #[test]
    fn training_collector_export_llama_cpp() {
        let mut collector = TrainingDataCollector::new(100);
        collector.add(TrainingSample {
            prompt: "What is Rust?".into(),
            response: "A systems programming language.".into(),
            raw_confidence: 0.9,
            verified_correct: true,
            tier: "LocalSmall".into(),
            task_type: "factual_qa".into(),
            timestamp: 0,
        });
        collector.add(TrainingSample {
            prompt: "Wrong answer".into(),
            response: "Bad response".into(),
            raw_confidence: 0.2,
            verified_correct: false,
            tier: "LocalSmall".into(),
            task_type: "test".into(),
            timestamp: 0,
        });
        let exported = collector.export_llama_cpp();
        let lines: Vec<&str> = exported.lines().collect();
        assert_eq!(lines.len(), 1); // Only positive
        assert!(lines[0].contains("prompt"));
        assert!(lines[0].contains("completion"));
    }

    #[test]
    fn training_collector_export_chat_format() {
        let mut collector = TrainingDataCollector::new(100);
        collector.add(TrainingSample {
            prompt: "Hello".into(),
            response: "Hi there!".into(),
            raw_confidence: 0.95,
            verified_correct: true,
            tier: "EdgeRules".into(),
            task_type: "greeting".into(),
            timestamp: 0,
        });
        let exported = collector.export_chat();
        assert!(exported.contains("messages"));
        assert!(exported.contains("user"));
        assert!(exported.contains("assistant"));
    }

    #[test]
    fn training_collector_ring_buffer() {
        let mut collector = TrainingDataCollector::new(3);
        for i in 0..5 {
            collector.add(TrainingSample {
                prompt: format!("prompt{i}"),
                response: format!("resp{i}"),
                raw_confidence: 0.9,
                verified_correct: true,
                tier: "EdgeRules".into(),
                task_type: "test".into(),
                timestamp: i,
            });
        }
        assert_eq!(collector.len(), 3); // Capped at max
        let jsonl = collector.export_jsonl(false);
        assert!(jsonl.contains("prompt2"));
        assert!(jsonl.contains("prompt3"));
        assert!(jsonl.contains("prompt4"));
        assert!(!jsonl.contains("prompt0"));
        assert!(!jsonl.contains("prompt1"));
    }

    #[test]
    fn training_collector_clear() {
        let mut collector = TrainingDataCollector::new(100);
        collector.add(TrainingSample {
            prompt: "test".into(),
            response: "resp".into(),
            raw_confidence: 0.9,
            verified_correct: true,
            tier: "EdgeRules".into(),
            task_type: "test".into(),
            timestamp: 0,
        });
        assert!(!collector.is_empty());
        collector.clear();
        assert!(collector.is_empty());
    }

    #[test]
    fn router_has_training_data_collector() {
        let router = InferenceRouter::new(RouterConfig::default());
        assert_eq!(router.training_sample_count(), 0);
    }

    #[test]
    fn router_export_empty_training_data() {
        let router = InferenceRouter::new(RouterConfig::default());
        let exported = router.export_training_data(false);
        assert!(exported.is_empty());
    }
}
