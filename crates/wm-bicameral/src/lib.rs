//! wm-bicameral — Bicameral reasoning for WhiteMagic v4 (Phase R5).
//!
//! Dual-hemisphere reasoning system:
//! - **Left hemisphere**: deterministic Rust logic (evidence-based analysis)
//! - **Right hemisphere**: pluggable inference (LLM, heuristic, or embedded model)
//! - **Corpus callosum**: bounded bidirectional critique channel
//! - **Consensus gate**: both hemispheres must agree, up to N debate rounds
//!
//! When the right hemisphere is unavailable or times out, the left hemisphere
//! result is used as fallback (left-only mode).

#![forbid(unsafe_code)]
#![allow(clippy::significant_drop_tightening)]

pub mod bitnet;
pub mod callosum;
pub mod configurator;
pub mod consensus;
pub mod context_optimizer;
pub mod dense_encoding;
pub mod edge_rules;
pub mod evaluator;
pub mod gated;
pub mod grammar_schemas;
pub mod hemisphere;
pub mod inference_tuner;
pub mod llm;
pub mod local_llm;
pub mod meta_harness;
pub mod resource_governor;
pub mod router;
pub mod routing_metrics;
pub mod scenario;
pub mod simulation_bridge;
pub mod speculative;
pub mod tri_model;
pub mod world_model;
pub mod world_model_handlers;

pub use bitnet::{BitNetConfig, BitNetRightHemisphere};
pub use callosum::{CallosumConfig, CorpusCallosum, Message, MessageKind};
pub use configurator::{ConfiguratorConfig, DeliberationMode, ImaginationConfigurator};
pub use consensus::{ConsensusGate, ConsensusResult, RoutingInfo, Verdict};
pub use context_optimizer::{ContextItem, ContextOptimizer, PackedContext, estimate_tokens};
pub use dense_encoding::{DenseEncoder, DenseEncodingConfig};
pub use edge_rules::{CompiledRule, EdgeRuleEngine, EdgeRuleHandler, EdgeStats, InferenceResult};
pub use evaluator::{EvaluatorConfig, ScenarioEvaluator, ScoreBreakdown};
pub use gated::{GateDecision, GatedEngine, RouterGate, TierHandlerRegistry};
pub use grammar_schemas::{
    GrammarName, SchemaName, ValidationError, ValidationResult, extract_and_validate, extract_json,
    get_grammar, get_schema, grammar_map, schema_map, validate_json,
};
pub use hemisphere::{
    Hemisphere, HemisphereInput, HemisphereOutput, LeftHemisphere, RightHemisphere,
    RightHemisphereFn, RightHemisphereStub,
};
pub use inference_tuner::{
    BenchmarkResult, CacheType, HardwareProfile, InferenceTuner, SimdLevel, SpecMethod,
    TunedConfig, TuningDecision, apply_idle_timeout, apply_to_llama_config, detect_hardware,
    profile_to_governor_mode, profile_to_hardware_metrics, recommend_config,
};
pub use llm::{LlmConfig, LlmRightHemisphere};
pub use local_llm::{LlamaConfig, LlamaLeftHemisphere};
pub use meta_harness::{
    CritiqueProvider, EnhancedResponse, EnhancementMode, EnhancementStep, HarnessStats,
    HeuristicCritique, InferenceProvider, MemoryProvider, MetaHarness, MetaHarnessConfig,
    ModeStats, NoMemory, TierHandlerInference,
};
pub use resource_governor::{
    GovernorMode, GovernorTransition, HardwareMetrics, ModeProfile, ResourceGovernor,
};
pub use router::{
    BudgetSummary, ComplexityAssessment, ComplexityClassifier, InferenceResponse, InferenceRouter,
    InferenceTier, RouterConfig, RoutingDecision, TierHandler, TokenBudgetTracker,
    TrainingDataCollector, TrainingSample,
};
pub use routing_metrics::{
    DriftRecommendation, DriftReport, DriftStatus, RoutingMetrics, TierStats,
};
pub use scenario::{ReflectionResult, Scenario, ScenarioConfig, ScenarioEngine};
pub use simulation_bridge::{
    EnrichedScenario, ForecastPrior, ProbabilisticRollout, SimulationBridge, SimulationBridgeConfig,
};
pub use speculative::{
    SpeculativeConfig, SpeculativeDecoder, SpeculativeHandler, SpeculativeResult, SpeculativeStats,
};
pub use tri_model::{
    IdleMode, LifecycleEvent, LifecycleEventType, ModelComponent, ModelKind, ModelState,
    TriModelConfig, TriModelHandler, TriModelManager,
};
pub use world_model::{
    DualPrediction, PredictedState, PredictionSource, StubWorldModelHandler, WorldModel,
};
pub use world_model_handlers::{LlmTierHandler, world_model_from_env};

use serde::{Deserialize, Serialize};
use std::sync::Arc;
use std::time::Duration;

/// Configuration for the bicameral reasoning system.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BicameralConfig {
    /// Maximum debate rounds before forcing consensus.
    pub max_rounds: usize,
    /// Timeout for each hemisphere response.
    pub timeout: Duration,
    /// Maximum message size through the corpus callosum (bytes).
    pub callosum_bandwidth: usize,
    /// Whether the right hemisphere is enabled.
    pub right_enabled: bool,
}

impl Default for BicameralConfig {
    fn default() -> Self {
        Self {
            max_rounds: 3,
            timeout: Duration::from_secs(5),
            callosum_bandwidth: 1024,
            right_enabled: true,
        }
    }
}

/// Bicameral reasoning engine — orchestrates left + right hemispheres
/// through the corpus callosum and consensus gate.
///
/// When an [`InferenceRouter`] is attached, the engine classifies each
/// prompt by complexity and routes it to the appropriate inference tier
/// before running the hemisphere debate. The routing decision is recorded
/// in the [`ConsensusResult`] metadata.
pub struct BicameralEngine {
    left: Box<dyn Hemisphere>,
    right: Option<Arc<dyn RightHemisphere>>,
    config: BicameralConfig,
    router: Option<InferenceRouter>,
}

impl BicameralEngine {
    /// Create a new bicameral engine with the given config and optional right hemisphere.
    ///
    /// The left hemisphere is selected from environment variables:
    /// - If `WM_LLAMA_ENDPOINT` is set, uses `LlamaLeftHemisphere` (llama.cpp-backed).
    /// - Otherwise, uses the heuristic `LeftHemisphere`.
    #[must_use]
    pub fn new(config: BicameralConfig, right: Option<Arc<dyn RightHemisphere>>) -> Self {
        let left: Box<dyn Hemisphere> = if let Some(llama) = LlamaLeftHemisphere::from_env() {
            tracing::info!("llama left hemisphere configured");
            Box::new(llama)
        } else {
            Box::new(LeftHemisphere::new())
        };
        Self {
            left,
            right: if config.right_enabled { right } else { None },
            config,
            router: None,
        }
    }

    /// Create a bicameral engine with explicit left and right hemispheres.
    #[must_use]
    pub fn with_hemispheres(
        config: BicameralConfig,
        left: Box<dyn Hemisphere>,
        right: Option<Arc<dyn RightHemisphere>>,
    ) -> Self {
        Self {
            left,
            right: if config.right_enabled { right } else { None },
            config,
            router: None,
        }
    }

    /// Create a left-only engine (no right hemisphere).
    #[must_use]
    pub fn left_only(config: BicameralConfig) -> Self {
        let left: Box<dyn Hemisphere> = if let Some(llama) = LlamaLeftHemisphere::from_env() {
            tracing::info!("llama left hemisphere configured (left-only mode)");
            Box::new(llama)
        } else {
            Box::new(LeftHemisphere::new())
        };
        Self {
            left,
            right: None,
            config,
            router: None,
        }
    }

    /// Attach an inference router to enable complexity-aware tier routing.
    ///
    /// When set, [`reason`](Self::reason) will classify the input prompt and
    /// record the routing decision in the result metadata.
    #[must_use]
    pub fn with_router(mut self, router: InferenceRouter) -> Self {
        self.router = Some(router);
        self
    }

    /// Attach a router from environment configuration.
    ///
    /// Convenience method that creates an [`InferenceRouter`] from env vars
    /// and attaches it via [`with_router`](Self::with_router).
    #[must_use]
    pub fn with_router_from_env(self) -> Self {
        self.with_router(InferenceRouter::from_env())
    }

    /// Check if the router is attached.
    #[must_use]
    pub const fn has_router(&self) -> bool {
        self.router.is_some()
    }

    /// Get the routing decision for a prompt without running full reasoning.
    ///
    /// Returns `None` if no router is attached.
    #[must_use]
    pub fn classify(&self, prompt: &str) -> Option<ComplexityAssessment> {
        let router = self.router.as_ref()?;
        Some(router.classify(prompt, None, None, false))
    }

    /// Get the router's budget summary, if a router is attached.
    #[must_use]
    pub fn budget_summary(&self) -> Option<BudgetSummary> {
        self.router.as_ref().map(InferenceRouter::budget_summary)
    }

    /// Get the number of collected training samples, if a router is attached.
    #[must_use]
    pub fn training_sample_count(&self) -> Option<usize> {
        self.router
            .as_ref()
            .map(InferenceRouter::training_sample_count)
    }

    /// Export training data to JSONL format, if a router is attached.
    #[must_use]
    pub fn export_training_data(&self, include_negative: bool) -> String {
        self.router
            .as_ref()
            .map_or(String::new(), |r| r.export_training_data(include_negative))
    }

    /// Export training data in llama.cpp format, if a router is attached.
    #[must_use]
    pub fn export_training_data_llama_cpp(&self) -> String {
        self.router.as_ref().map_or(
            String::new(),
            InferenceRouter::export_training_data_llama_cpp,
        )
    }

    /// Export training data in OpenAI chat format, if a router is attached.
    #[must_use]
    pub fn export_training_data_chat(&self) -> String {
        self.router
            .as_ref()
            .map_or(String::new(), InferenceRouter::export_training_data_chat)
    }

    /// Run bicameral reasoning on the given input.
    ///
    /// Both hemispheres analyze the input, then exchange critiques through
    /// the corpus callosum until they reach consensus or exhaust debate rounds.
    ///
    /// If a router is attached, the prompt is classified first and the
    /// routing tier is recorded in the result's `messages`.
    #[must_use]
    pub fn reason(&self, input: &HemisphereInput) -> ConsensusResult {
        let mut result =
            self.reason_gated(input, self.config.right_enabled, self.config.max_rounds);

        // If router is attached, record the routing decision
        if let Some(ref router) = self.router {
            let assessment = router.classify(&input.topic, None, None, false);
            result.routing_info = Some(RoutingInfo {
                tier: assessment.tier,
                task_type: assessment.task_type.clone(),
                confidence: assessment.confidence,
                reason: format!(
                    "routed to {:?} (task: {}, confidence: {:.2})",
                    assessment.tier, assessment.task_type, assessment.confidence
                ),
            });
        }

        result
    }

    /// Run bicameral reasoning with explicit gating parameters.
    ///
    /// This is used by [`GatedEngine`] to delegate debate execution
    /// without reimplementing the hemisphere orchestration logic.
    ///
    /// - `run_right`: whether to invoke the right hemisphere
    /// - `max_rounds`: maximum debate rounds (overrides `config.max_rounds`)
    #[must_use]
    pub fn reason_gated(
        &self,
        input: &HemisphereInput,
        run_right: bool,
        max_rounds: usize,
    ) -> ConsensusResult {
        let callosum = CorpusCallosum::new(self.config.callosum_bandwidth);
        let gate = ConsensusGate::new(max_rounds);

        // Left hemisphere always runs
        let left_output = self.left.analyze(input);

        // Right hemisphere runs only if requested and available
        let right_output = if run_right {
            self.right.as_ref().map(|rh| rh.analyze(input))
        } else {
            None
        };

        match right_output {
            Some(right_out) => gate.deliberate(&left_output, &right_out, &callosum, input),
            None => ConsensusResult {
                verdict: Verdict::LeftOnly,
                conclusion: left_output.conclusion.clone(),
                confidence: left_output.confidence,
                rounds: 0,
                left_output,
                right_output: None,
                messages: Vec::new(),
                routing_info: None,
            },
        }
    }

    /// Check if the right hemisphere is available.
    #[must_use]
    pub fn has_right_hemisphere(&self) -> bool {
        self.right.is_some()
    }

    /// Get the name of the left hemisphere backend.
    #[must_use]
    pub fn left_hemisphere_name(&self) -> &'static str {
        self.left.name()
    }

    /// Get the engine configuration.
    #[must_use]
    pub const fn config(&self) -> &BicameralConfig {
        &self.config
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn bicameral_left_only_fallback() {
        let engine = BicameralEngine::left_only(BicameralConfig::default());
        let input = HemisphereInput::new("test topic");
        let result = engine.reason(&input);
        assert_eq!(result.verdict, Verdict::LeftOnly);
        assert!(!result.conclusion.is_empty());
        assert!(result.right_output.is_none());
    }

    #[test]
    fn bicameral_with_stub_right_hemisphere() {
        let right = Arc::new(RightHemisphereStub::new()) as Arc<dyn RightHemisphere>;
        let engine = BicameralEngine::new(BicameralConfig::default(), Some(right));
        let input = HemisphereInput::new("test topic");
        let result = engine.reason(&input);
        assert!(result.right_output.is_some());
        assert!(!result.conclusion.is_empty());
    }

    #[test]
    fn bicameral_disabled_right_uses_left_only() {
        let right = Arc::new(RightHemisphereStub::new()) as Arc<dyn RightHemisphere>;
        let config = BicameralConfig {
            right_enabled: false,
            ..Default::default()
        };
        let engine = BicameralEngine::new(config, Some(right));
        assert!(!engine.has_right_hemisphere());
        let input = HemisphereInput::new("test topic");
        let result = engine.reason(&input);
        assert_eq!(result.verdict, Verdict::LeftOnly);
    }

    #[test]
    fn bicameral_consensus_when_both_agree() {
        let right = Arc::new(RightHemisphereStub::new()) as Arc<dyn RightHemisphere>;
        let engine = BicameralEngine::new(BicameralConfig::default(), Some(right));
        let input = HemisphereInput::new("rust is good");
        let result = engine.reason(&input);
        // Stub right hemisphere should agree with left on simple topics
        assert!(
            matches!(
                result.verdict,
                Verdict::Agreed | Verdict::LeftOnly | Verdict::LeftPrevailed
            ),
            "got {:?}",
            result.verdict
        );
    }

    #[test]
    fn bicameral_with_hemispheres_explicit() {
        let left: Box<dyn Hemisphere> = Box::new(LeftHemisphere::new());
        let right = Arc::new(RightHemisphereStub::new()) as Arc<dyn RightHemisphere>;
        let engine =
            BicameralEngine::with_hemispheres(BicameralConfig::default(), left, Some(right));
        assert_eq!(engine.left_hemisphere_name(), "left");
        let input = HemisphereInput::new("test topic");
        let result = engine.reason(&input);
        assert!(!result.conclusion.is_empty());
    }

    #[test]
    fn bicameral_left_hemisphere_name_default() {
        let engine = BicameralEngine::left_only(BicameralConfig::default());
        // Without WM_LLAMA_ENDPOINT set, should use heuristic left
        assert_eq!(engine.left_hemisphere_name(), "left");
    }

    // --- Router integration tests ---

    #[test]
    fn bicameral_with_router_attached() {
        let engine = BicameralEngine::left_only(BicameralConfig::default())
            .with_router(InferenceRouter::new(RouterConfig::default()));
        assert!(engine.has_router());
    }

    #[test]
    fn bicameral_without_router_has_none() {
        let engine = BicameralEngine::left_only(BicameralConfig::default());
        assert!(!engine.has_router());
    }

    #[test]
    fn bicameral_classify_with_router() {
        let engine = BicameralEngine::left_only(BicameralConfig::default())
            .with_router(InferenceRouter::new(RouterConfig::default()));
        let assessment = engine.classify("what is 2+2").unwrap();
        // Simple math should route to a local tier (not cloud)
        assert!(assessment.tier <= InferenceTier::LocalSmall);
    }

    #[test]
    fn bicameral_classify_without_router_returns_none() {
        let engine = BicameralEngine::left_only(BicameralConfig::default());
        assert!(engine.classify("test").is_none());
    }

    #[test]
    fn bicameral_reason_records_router_message() {
        let engine = BicameralEngine::left_only(BicameralConfig::default())
            .with_router(InferenceRouter::new(RouterConfig::default()));
        let input = HemisphereInput::new("what is rust");
        let result = engine.reason(&input);
        // Should have routing info in the result
        assert!(
            result.routing_info.is_some(),
            "expected routing info in result"
        );
    }

    #[test]
    fn bicameral_reason_without_router_no_router_message() {
        let engine = BicameralEngine::left_only(BicameralConfig::default());
        let input = HemisphereInput::new("what is rust");
        let result = engine.reason(&input);
        assert!(
            result.routing_info.is_none(),
            "should not have routing info without router"
        );
    }

    #[test]
    fn bicameral_budget_summary_with_router() {
        let engine = BicameralEngine::left_only(BicameralConfig::default())
            .with_router(InferenceRouter::new(RouterConfig::default()));
        let summary = engine.budget_summary().unwrap();
        assert_eq!(summary.total_budget, 100_000);
        assert_eq!(summary.used_tokens, 0);
    }

    #[test]
    fn bicameral_budget_summary_without_router() {
        let engine = BicameralEngine::left_only(BicameralConfig::default());
        assert!(engine.budget_summary().is_none());
    }

    #[test]
    fn bicameral_with_router_from_env() {
        let engine = BicameralEngine::left_only(BicameralConfig::default()).with_router_from_env();
        assert!(engine.has_router());
    }

    #[test]
    fn bicameral_classify_complex_prompt_routes_higher() {
        let engine = BicameralEngine::left_only(BicameralConfig::default())
            .with_router(InferenceRouter::new(RouterConfig::default()));
        let simple = engine.classify("what is 2+2").unwrap();
        let complex = engine.classify("analyze the philosophical implications of quantum mechanics in consciousness studies").unwrap();
        // Complex prompt should route to at least as high a tier as simple
        assert!(complex.tier >= simple.tier);
    }
}
