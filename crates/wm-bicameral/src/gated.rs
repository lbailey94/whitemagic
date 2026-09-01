//! Router-Gated Hemisphere Execution (Phase N9).
//!
//! Uses the `InferenceRouter`'s complexity classification to gate
//! hemisphere execution:
//!
//! - **EdgeRules**: return left-only result immediately, skip right hemisphere
//! - **LocalLlamaCpp**: run left + right with 1 debate round (fast)
//! - **LocalSmall+**: run full debate (max_rounds from config)
//! - **Sensitive data**: never route to cloud right hemisphere
//!
//! Additionally, `TierHandler` implementations are registered for each tier,
//! backed by the `TriModelManager` and `EdgeRuleEngine`.

#![allow(clippy::significant_drop_tightening)]
#![allow(clippy::missing_const_for_fn)]

use serde::{Deserialize, Serialize};
use std::sync::Arc;

use crate::BicameralEngine;
use crate::consensus::{ConsensusResult, RoutingInfo};
use crate::edge_rules::EdgeRuleHandler;
use crate::hemisphere::{Hemisphere, HemisphereInput, RightHemisphere, RightHemisphereStub};
use crate::router::{InferenceRouter, InferenceTier, TierHandler};
use crate::tri_model::{TriModelHandler, TriModelManager};

// ── Gate Decision ─────────────────────────────────────────────────────

/// Decision made by the router gate for hemisphere execution.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct GateDecision {
    /// Which tier the router classified this prompt as.
    pub tier: InferenceTier,
    /// Whether to run the right hemisphere.
    pub run_right: bool,
    /// Maximum debate rounds (0 = left-only, 1 = fast, N = full).
    pub max_rounds: usize,
    /// Whether the prompt was classified as sensitive.
    pub sensitive: bool,
    /// Human-readable reason for the decision.
    pub reason: String,
}

impl GateDecision {
    /// Gate decision for EdgeRules tier — left-only, no debate.
    #[must_use]
    pub fn edge_rules() -> Self {
        Self {
            tier: InferenceTier::EdgeRules,
            run_right: false,
            max_rounds: 0,
            sensitive: false,
            reason: "edge rules: skip hemisphere debate".into(),
        }
    }

    /// Gate decision for LocalLlamaCpp tier — fast debate (1 round).
    #[must_use]
    pub fn fast() -> Self {
        Self {
            tier: InferenceTier::LocalLlamaCpp,
            run_right: true,
            max_rounds: 1,
            sensitive: false,
            reason: "local llama.cpp: fast 1-round debate".into(),
        }
    }

    /// Gate decision for LocalSmall+ tier — full debate.
    #[must_use]
    pub fn full(max_rounds: usize) -> Self {
        Self {
            tier: InferenceTier::LocalSmall,
            run_right: true,
            max_rounds,
            sensitive: false,
            reason: format!("local small: full {max_rounds}-round debate"),
        }
    }

    /// Gate decision for sensitive data — no cloud, full local debate.
    #[must_use]
    pub fn sensitive_local(max_rounds: usize) -> Self {
        Self {
            tier: InferenceTier::LocalLarge,
            run_right: true,
            max_rounds,
            sensitive: true,
            reason: "sensitive data: local-only full debate".into(),
        }
    }
}

// ── Router Gate ───────────────────────────────────────────────────────

/// Classifies a prompt and decides how to execute hemisphere debate.
///
/// Wraps the `InferenceRouter`'s complexity classification with
/// hemisphere-specific gating logic.
pub struct RouterGate {
    router: InferenceRouter,
    /// Default max rounds for full debate.
    default_max_rounds: usize,
    /// Whether sensitive data detection is enabled.
    sensitive_detection: bool,
}

impl RouterGate {
    /// Create a new router gate from an inference router.
    #[must_use]
    pub fn new(router: InferenceRouter) -> Self {
        Self {
            router,
            default_max_rounds: 3,
            sensitive_detection: true,
        }
    }

    /// Create from environment variables.
    #[must_use]
    pub fn from_env() -> Self {
        Self::new(InferenceRouter::from_env())
    }

    /// Set the default max rounds for full debate.
    #[must_use]
    pub fn with_max_rounds(mut self, rounds: usize) -> Self {
        self.default_max_rounds = rounds;
        self
    }

    /// Enable or disable sensitive data detection.
    #[must_use]
    pub fn with_sensitive_detection(mut self, enabled: bool) -> Self {
        self.sensitive_detection = enabled;
        self
    }

    /// Classify a prompt and produce a gate decision.
    #[must_use]
    pub fn classify(&self, prompt: &str) -> GateDecision {
        let assessment = self.router.classify(prompt, None, None, false);

        // Check for sensitive data
        if self.sensitive_detection && assessment.is_sensitive {
            return GateDecision::sensitive_local(self.default_max_rounds);
        }

        match assessment.tier {
            InferenceTier::EdgeRules => GateDecision::edge_rules(),
            InferenceTier::LocalLlamaCpp => GateDecision::fast(),
            InferenceTier::LocalSmall | InferenceTier::LocalLarge | InferenceTier::Cloud => {
                GateDecision::full(self.default_max_rounds)
            }
        }
    }

    /// Get the underlying router.
    #[must_use]
    pub fn router(&self) -> &InferenceRouter {
        &self.router
    }
}

// ── Gated Engine ──────────────────────────────────────────────────────

/// A bicameral engine with router-gated hemisphere execution.
///
/// Wraps a [`BicameralEngine`] with tier-aware gating:
/// - EdgeRules: skip debate, return left-only
/// - LocalLlamaCpp: fast 1-round debate
/// - LocalSmall+: full debate
/// - Sensitive: local-only, no cloud
///
/// Delegates the actual hemisphere debate to `BicameralEngine::reason_gated()`,
/// eliminating duplicated debate orchestration logic.
pub struct GatedEngine {
    engine: BicameralEngine,
    gate: RouterGate,
}

impl GatedEngine {
    /// Create a new gated engine from a `BicameralEngine` and `RouterGate`.
    #[must_use]
    pub fn with_engine(engine: BicameralEngine, gate: RouterGate) -> Self {
        Self { engine, gate }
    }

    /// Create a new gated engine with explicit hemispheres.
    #[must_use]
    pub fn new(
        left: Box<dyn Hemisphere>,
        right: Option<Arc<dyn RightHemisphere>>,
        gate: RouterGate,
    ) -> Self {
        let config = crate::BicameralConfig {
            max_rounds: gate.default_max_rounds,
            ..Default::default()
        };
        let engine = BicameralEngine::with_hemispheres(config, left, right);
        Self { engine, gate }
    }

    /// Create a default gated engine with heuristic hemispheres.
    #[must_use]
    pub fn heuristic(gate: RouterGate) -> Self {
        let left: Box<dyn Hemisphere> = Box::new(crate::hemisphere::LeftHemisphere::new());
        let right: Option<Arc<dyn RightHemisphere>> = Some(Arc::new(RightHemisphereStub::new()));
        Self::new(left, right, gate)
    }

    /// Run gated reasoning on the given input.
    ///
    /// The gate decision controls:
    /// - Whether the right hemisphere participates
    /// - How many debate rounds are allowed
    /// - Whether cloud is allowed (sensitive data)
    #[must_use]
    pub fn reason(&self, input: &HemisphereInput) -> ConsensusResult {
        let decision = self.gate.classify(&input.topic);

        // Delegate debate execution to BicameralEngine
        let mut result = self
            .engine
            .reason_gated(input, decision.run_right, decision.max_rounds);

        // Override routing info with gate decision
        result.routing_info = Some(RoutingInfo {
            tier: decision.tier,
            task_type: format!("{:?}", decision.tier),
            confidence: result.confidence,
            reason: decision.reason,
        });

        result
    }

    /// Get the gate decision for a prompt without running reasoning.
    #[must_use]
    pub fn classify(&self, prompt: &str) -> GateDecision {
        self.gate.classify(prompt)
    }

    /// Get the underlying router gate.
    #[must_use]
    pub fn gate(&self) -> &RouterGate {
        &self.gate
    }

    /// Get the underlying bicameral engine.
    #[must_use]
    pub fn engine(&self) -> &BicameralEngine {
        &self.engine
    }
}

// ── Tier Handler Registry ─────────────────────────────────────────────

/// Registry of `TierHandler`s for each inference tier.
///
/// Built from the `TriModelManager` (N1) and `EdgeRuleEngine` (N2).
/// The `InferenceRouter` uses these handlers to execute inference
/// at each tier.
pub struct TierHandlerRegistry {
    handlers: Vec<Option<Box<dyn TierHandler>>>,
}

impl TierHandlerRegistry {
    /// Create a new empty registry.
    #[must_use]
    pub fn new() -> Self {
        Self {
            handlers: (0..=4).map(|_| None::<Box<dyn TierHandler>>).collect(),
        }
    }

    /// Register a handler for a specific tier.
    pub fn register(&mut self, tier: InferenceTier, handler: Box<dyn TierHandler>) {
        self.handlers[tier as usize] = Some(handler);
    }

    /// Get the handler for a specific tier.
    #[must_use]
    pub fn get(&self, tier: InferenceTier) -> Option<&dyn TierHandler> {
        self.handlers[tier as usize].as_deref()
    }

    /// Check if a handler is registered for a tier.
    #[must_use]
    pub fn has(&self, tier: InferenceTier) -> bool {
        self.handlers[tier as usize].is_some()
    }

    /// Build a registry from the TriModelManager and EdgeRuleEngine.
    ///
    /// - `EdgeRules` → `EdgeRuleHandler`
    /// - `LocalLlamaCpp` → `TriModelHandler` (left, e.g. Qwen 0.5B)
    /// - `LocalSmall` → `TriModelHandler` (left/medium, e.g. Qwen 1.5B)
    /// - `LocalLarge` → `TriModelHandler` (right, e.g. Qwen 3B)
    /// - `Cloud` → not registered (handled externally)
    #[must_use]
    pub fn from_components(manager: Arc<TriModelManager>) -> Self {
        let mut registry = Self::new();

        // EdgeRules → EdgeRuleEngine
        registry.register(InferenceTier::EdgeRules, Box::new(EdgeRuleHandler::new()));

        // LocalLlamaCpp → Left model (0.5B)
        registry.register(
            InferenceTier::LocalLlamaCpp,
            Box::new(TriModelHandler::production(
                manager.clone(),
                InferenceTier::LocalLlamaCpp,
            )),
        );

        // LocalSmall → Left/Medium model (0.5B or 1.5B)
        registry.register(
            InferenceTier::LocalSmall,
            Box::new(TriModelHandler::production(
                manager.clone(),
                InferenceTier::LocalSmall,
            )),
        );

        // LocalLarge → Right model (3B)
        registry.register(
            InferenceTier::LocalLarge,
            Box::new(TriModelHandler::production(
                manager,
                InferenceTier::LocalLarge,
            )),
        );

        // Cloud is not registered by from_components
        // Cloud tier is handled externally
        registry
    }

    /// Execute inference at a specific tier.
    ///
    /// Returns `None` if no handler is registered for the tier.
    #[must_use]
    pub fn execute(
        &self,
        tier: InferenceTier,
        prompt: &str,
        max_tokens: usize,
    ) -> Option<Result<(String, f32), String>> {
        self.get(tier).map(|h| h.handle(prompt, max_tokens))
    }
}

impl Default for TierHandlerRegistry {
    fn default() -> Self {
        Self::new()
    }
}

// ── Tests ─────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use crate::consensus::Verdict;

    // ── GateDecision tests ─────────────────────────────────────────────

    #[test]
    fn gate_decision_edge_rules() {
        let d = GateDecision::edge_rules();
        assert!(!d.run_right);
        assert_eq!(d.max_rounds, 0);
        assert!(!d.sensitive);
    }

    #[test]
    fn gate_decision_fast() {
        let d = GateDecision::fast();
        assert!(d.run_right);
        assert_eq!(d.max_rounds, 1);
    }

    #[test]
    fn gate_decision_full() {
        let d = GateDecision::full(3);
        assert!(d.run_right);
        assert_eq!(d.max_rounds, 3);
    }

    #[test]
    fn gate_decision_sensitive() {
        let d = GateDecision::sensitive_local(3);
        assert!(d.run_right);
        assert!(d.sensitive);
        assert_eq!(d.tier, InferenceTier::LocalLarge);
    }

    // ── RouterGate tests ───────────────────────────────────────────────

    #[test]
    fn router_gate_classifies_simple_greeting() {
        let gate = RouterGate::from_env();
        let decision = gate.classify("hello");
        // "hello" should be classified as EdgeRules (greeting pattern)
        assert!(!decision.run_right);
        assert_eq!(decision.max_rounds, 0);
    }

    #[test]
    fn router_gate_classifies_complex_prompt() {
        let gate = RouterGate::from_env();
        let decision = gate.classify(
            "Analyze the trade-offs between distributed and monolithic architectures \
             in the context of microservices adoption for enterprise applications",
        );
        // Complex prompt → higher tier → full debate
        assert!(decision.run_right);
        assert!(decision.max_rounds > 0);
    }

    #[test]
    fn router_gate_with_custom_rounds() {
        let gate = RouterGate::from_env().with_max_rounds(5);
        let decision = gate
            .classify("Analyze the complex interdisciplinary trade-offs in this nuanced scenario");
        if decision.tier >= InferenceTier::LocalSmall {
            assert_eq!(decision.max_rounds, 5);
        }
    }

    #[test]
    fn router_gate_sensitive_detection() {
        let gate = RouterGate::from_env()
            .with_sensitive_detection(true)
            .with_max_rounds(3);

        // Prompt with sensitive keywords
        let decision = gate.classify("What is my SSN 123-45-6789 and password hunter2?");
        if decision.sensitive {
            assert_ne!(decision.tier, InferenceTier::Cloud);
        }
    }

    #[test]
    fn router_gate_router_accessible() {
        let gate = RouterGate::from_env();
        let _ = gate.router();
    }

    // ── GatedEngine tests ──────────────────────────────────────────────

    #[test]
    fn gated_engine_heuristic_creates() {
        let gate = RouterGate::from_env();
        let engine = GatedEngine::heuristic(gate);
        let _ = engine.gate();
    }

    #[test]
    fn gated_engine_reason_simple() {
        let gate = RouterGate::from_env();
        let engine = GatedEngine::heuristic(gate);

        let input = HemisphereInput::new("hello");
        let result = engine.reason(&input);

        // Simple greeting → left-only
        assert_eq!(result.verdict, Verdict::LeftOnly);
        assert!(result.right_output.is_none());
        assert!(result.routing_info.is_some());
    }

    #[test]
    fn gated_engine_reason_complex_2() {
        let gate = RouterGate::from_env();
        let engine = GatedEngine::heuristic(gate);

        let input = HemisphereInput::new(
            "Analyze the complex interdisciplinary trade-offs in this nuanced scenario \
             with multiple competing factors and conditional dependencies",
        );
        let result = engine.reason(&input);

        // Complex prompt → should run right hemisphere
        assert!(result.routing_info.is_some());
        let info = result.routing_info.as_ref().unwrap();
        assert!(info.tier >= InferenceTier::LocalLlamaCpp);
    }

    #[test]
    fn gated_engine_classify_without_reasoning() {
        let gate = RouterGate::from_env();
        let engine = GatedEngine::heuristic(gate);

        let decision = engine.classify("hello");
        assert!(!decision.run_right);
    }

    #[test]
    fn gated_engine_with_no_right_hemisphere() {
        let gate = RouterGate::from_env();
        let left: Box<dyn Hemisphere> = Box::new(crate::hemisphere::LeftHemisphere::new());
        let engine = GatedEngine::new(left, None, gate);

        let input = HemisphereInput::new("complex analysis required");
        let result = engine.reason(&input);

        // No right hemisphere → left-only regardless of gate
        assert_eq!(result.verdict, Verdict::LeftOnly);
    }

    // ── TierHandlerRegistry tests ──────────────────────────────────────

    #[test]
    fn registry_new_empty() {
        let registry = TierHandlerRegistry::new();
        for tier in InferenceTier::all() {
            assert!(!registry.has(tier) || tier == InferenceTier::Cloud);
        }
    }

    #[test]
    fn registry_register_and_get() {
        let mut registry = TierHandlerRegistry::new();
        let mgr = Arc::new(TriModelManager::default_manager());
        let handler = Box::new(TriModelHandler::new(mgr, InferenceTier::LocalSmall));

        registry.register(InferenceTier::LocalSmall, handler);
        assert!(registry.has(InferenceTier::LocalSmall));
        assert!(registry.get(InferenceTier::LocalSmall).is_some());
    }

    #[test]
    fn registry_from_components() {
        let mgr = Arc::new(TriModelManager::default_manager());

        let registry = TierHandlerRegistry::from_components(mgr);

        assert!(registry.has(InferenceTier::EdgeRules));
        assert!(registry.has(InferenceTier::LocalLlamaCpp));
        assert!(registry.has(InferenceTier::LocalSmall));
        assert!(registry.has(InferenceTier::LocalLarge));
        // Cloud is not registered by from_components
        assert!(!registry.has(InferenceTier::Cloud));
    }

    #[test]
    fn registry_execute_edge_rules() {
        let mgr = Arc::new(TriModelManager::default_manager());

        let registry = TierHandlerRegistry::from_components(mgr);

        let result = registry.execute(InferenceTier::EdgeRules, "hello", 64);
        assert!(result.is_some());
        // EdgeRuleHandler should handle "hello" (greeting rule)
        if let Some(Ok((answer, _))) = result {
            assert!(!answer.is_empty());
        }
    }

    #[test]
    fn registry_execute_local_small() {
        let mgr = Arc::new(TriModelManager::default_manager());

        let registry = TierHandlerRegistry::from_components(mgr);

        // TriModelHandler in stub mode
        let result = registry.execute(InferenceTier::LocalSmall, "test prompt", 64);
        assert!(result.is_some());
        if let Some(Ok((answer, _))) = result {
            assert!(!answer.is_empty());
        }
    }

    #[test]
    fn registry_execute_unregistered_tier() {
        let registry = TierHandlerRegistry::new();
        let result = registry.execute(InferenceTier::Cloud, "test", 64);
        assert!(result.is_none());
    }

    #[test]
    fn registry_default_is_empty() {
        let registry = TierHandlerRegistry::default();
        assert!(!registry.has(InferenceTier::EdgeRules));
    }

    #[test]
    fn registry_handler_names() {
        let mgr = Arc::new(TriModelManager::default_manager());
        let registry = TierHandlerRegistry::from_components(mgr);

        // Verify handler names
        assert_eq!(
            registry.get(InferenceTier::LocalLlamaCpp).unwrap().name(),
            "tri-model-llama-cpp"
        );
        assert_eq!(
            registry.get(InferenceTier::LocalSmall).unwrap().name(),
            "tri-model-small"
        );
        assert_eq!(
            registry.get(InferenceTier::LocalLarge).unwrap().name(),
            "tri-model-large"
        );
    }

    // ── Integration: GatedEngine + TriModelManager ─────────────────────

    #[test]
    fn gated_engine_with_tri_model_manager() {
        use crate::tri_model::ModelKind;
        let mgr = Arc::new(TriModelManager::default_manager());
        mgr.start_autonomic().unwrap();
        mgr.start(ModelKind::Left).unwrap();

        let gate = RouterGate::from_env();
        let engine = GatedEngine::heuristic(gate);

        let input = HemisphereInput::new("hello");
        let result = engine.reason(&input);

        // Edge rules → left-only
        assert_eq!(result.verdict, Verdict::LeftOnly);
    }
}
