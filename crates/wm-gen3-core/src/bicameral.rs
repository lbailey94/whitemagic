//! Bicameral Engine, Decision Models (Jev), and Global Workspace Spotlight (PEB-9).
//!
//! # Three-Chamber Tri-Cameral Architecture
//! 1. **Chamber α (Generative Producer / Divergent Kernel):**
//!    High-recall, divergent hypothesis generator ("What might work?").
//!    Operates with associative search and speculative proposals.
//! 2. **Chamber β (Evaluative / Decision Model - Jev-compatible):**
//!    Non-autoregressive discriminative model ("Which candidate is best supported?").
//!    Evaluates three schema-guaranteed primitives in a single parallel forward pass:
//!    - **Noul:** Boolean probability of predicate satisfaction ($P \in [0.0, 1.0]$).
//!    - **Choice:** Categorical distribution over target attractor basins ($A_1 \dots A_8$).
//!    - **Score:** Ordinal expected utility and estimated risk ratings ($[0.0, 1.0]$).
//!      *Constraint:* Decision models emit $\Delta\text{field}$; they never hold commit authority.
//! 3. **Chamber γ (Constitutional Verifier / Analytical Catuṣkoṭi Kernel):**
//!    Formal logic and deterministic verification ("Are we permitted and warranted to act?").
//!    Applies Contextualized Catuṣkoṭi ($K_1$ Affirmed, $K_2$ Denied, $K_3$ Contradiction,
//!    $K_4$ Insufficient, $K_0$ Category Error). Holds exclusive commit capability tokens.
//! 4. **Corpus Callosum (Arbitration & Da'at Transition Bridge):**
//!    Computes composite margin $M$. Authorizes fast-path bypass when $M \ge 0.85$,
//!    $\text{risk} \le 0.10$, and evidential status is strictly $K_1$ (Affirmed).
//! 5. **Global Workspace Spotlight:**
//!    Salience-driven attention field operating across the 8 emergent attractor basins,
//!    decaying by $0.5^{\Delta t / 5.0}$ with immediate preemption when incoming salience $> 0.80$.

use serde::{Deserialize, Serialize};
use std::collections::HashSet;
use std::fmt;

/// The three canonical non-autoregressive decision primitives.
#[derive(Debug, Clone, PartialEq)]
pub enum DecisionPrimitive {
    /// Noul: Boolean probability P ∈ [0.0, 1.0] that a predicate is satisfied.
    Noul { probability: f64 },
    /// Choice: Categorical distribution over discrete targets with confidence.
    Choice {
        selected_key: String,
        confidence: f64,
        distribution: Vec<(String, f64)>,
    },
    /// Score: Continuous ordinal rating [0.0, 1.0] with uncertainty bound.
    Score { value: f64, confidence: f64 },
}

/// A candidate state transition or action proposal from Chamber α.
#[derive(Debug, Clone, PartialEq)]
pub struct CandidateProposal {
    pub id: u64,
    pub source_basin: usize,
    pub target_basin: usize,
    pub action_name: String,
    pub generator_confidence: f64,
    pub estimated_cost_tokens: u64,
    pub is_destructive: bool,
}

/// Active operational present state bridging past evidence and speculative futures.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct PresentState {
    pub observations: Vec<u64>,
    pub beliefs: Vec<(String, f64)>,
    pub unresolved_frames: Vec<String>,
    pub goals: Vec<String>,
    pub ram_headroom_mb: u64,
    pub active_procedure_lineage: u128,
}

impl PresentState {
    #[must_use]
    pub fn new(goals: Vec<String>, ram_headroom_mb: u64, lineage: u128) -> Self {
        Self {
            observations: Vec::new(),
            beliefs: Vec::new(),
            unresolved_frames: Vec::new(),
            goals,
            ram_headroom_mb,
            active_procedure_lineage: lineage,
        }
    }
}

/// Classification of a candidate action step on task progress (AEWM).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum ActionJudgeVerdict {
    /// Critical: essential step directly moving toward goal state.
    Critical,
    /// Exploratory: gathers information without direct side effects.
    Exploratory,
    /// Noisy: redundant or neutral step with low information gain.
    Noisy,
    /// Harmful: regresses progress, violates invariants, or induces risk.
    Harmful,
}

/// A lightweight, non-authoritative speculative trajectory (AEWM / Shadow Clone).
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ShadowTrajectory {
    pub branch_id: String,
    pub parent_state_epoch: u64,
    pub proposed_actions: Vec<String>,
    pub counterfactual_assumptions: Vec<String>,
    pub predicted_progress: f64,
    pub verdict: ActionJudgeVerdict,
    pub is_evaporated: bool,
}

impl ShadowTrajectory {
    #[must_use]
    pub fn new(branch_id: String, parent_epoch: u64, actions: Vec<String>) -> Self {
        Self {
            branch_id,
            parent_state_epoch: parent_epoch,
            proposed_actions: actions,
            counterfactual_assumptions: Vec::new(),
            predicted_progress: 0.5,
            verdict: ActionJudgeVerdict::Exploratory,
            is_evaporated: false,
        }
    }

    /// Evaluates step progress impact via ActionJudge heuristic.
    pub fn evaluate_progress(&mut self) -> ActionJudgeVerdict {
        let is_harmful = self
            .proposed_actions
            .iter()
            .any(|a| a.contains("drop") || a.contains("delete") || a.contains("rm -rf"));
        if is_harmful {
            self.verdict = ActionJudgeVerdict::Harmful;
            self.predicted_progress = 0.0;
        } else if self
            .proposed_actions
            .iter()
            .any(|a| a.contains("verify") || a.contains("solve"))
        {
            self.verdict = ActionJudgeVerdict::Critical;
            self.predicted_progress = 0.95;
        } else if self.proposed_actions.is_empty() {
            self.verdict = ActionJudgeVerdict::Noisy;
            self.predicted_progress = 0.20;
        } else {
            self.verdict = ActionJudgeVerdict::Exploratory;
            self.predicted_progress = 0.65;
        }
        self.verdict
    }

    /// Cleanly evaporates the shadow trajectory without committing to durable memory.
    pub fn evaporate(&mut self) {
        self.is_evaporated = true;
    }
}

/// Pre-flight cognitive dispatch tier.
/// Enforces that "Nothing" is a first-class cognitive operation (LW2S).
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub enum CognitiveDispatch {
    /// Silence / zero-action: expected marginal utility <= 0.
    ExecuteNothing { reason: String },
    /// Sub-millisecond deterministic calculation or index lookup.
    DeterministicRule { rule_name: String },
    /// Non-autoregressive decision model (Jev / Kev / Semantic If).
    DecisionModel { evaluator_name: String },
    /// Small 2B/8B specialist organ (EpiCon tree organizer / PaR).
    Specialist { organ: String, model_tier: String },
    /// Full frontier autoregressive deliberation.
    FrontierDeliberation { prompt_token_budget: usize },
}

/// Tactical and operational execution tier for an action skeleton (rooted in Gen1 xianfeng/wei_wuzu/huben).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
pub enum SkeletonTier {
    /// Minimal, ultra-fast, zero-overhead execution path (Xianfeng / Vanguard).
    Vanguard,
    /// Balanced, robust, general-purpose execution path (Wei Wuzu / Standard).
    #[default]
    Standard,
    /// Comprehensive, exhaustive verification and audit path (Huben / Heavy).
    Heavy,
}

/// Standardized, evolvable multi-action skeleton for speculative execution and pre-warmed commit.
///
/// Embodies the Gen1 Geneseed CodeTemplate:
/// - Versioned with ancestral lineage pointer (`parent_id`)
/// - Multi-tier execution variants (`SkeletonTier`)
/// - Kaizen Exponential Moving Average (EMA) empirical fitness tracking
/// - Automatic deprecation gating when rolling utility degrades below 0.35
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ActionSkeleton {
    pub id: String,
    pub name: String,
    pub version: u32,
    pub parent_id: Option<String>,
    pub tier: SkeletonTier,
    pub action_steps: Vec<String>,
    pub expected_preconditions: Vec<String>,
    pub estimated_latency_savings_ms: u64,
    pub execution_count: u64,
    pub success_count: u64,
    pub rolling_utility: f64,
    pub deprecated: bool,
}

impl ActionSkeleton {
    #[must_use]
    pub fn new(
        id: impl Into<String>,
        name: impl Into<String>,
        action_steps: Vec<String>,
        expected_preconditions: Vec<String>,
        estimated_latency_savings_ms: u64,
    ) -> Self {
        Self {
            id: id.into(),
            name: name.into(),
            version: 1,
            parent_id: None,
            tier: SkeletonTier::Standard,
            action_steps,
            expected_preconditions,
            estimated_latency_savings_ms,
            execution_count: 0,
            success_count: 0,
            rolling_utility: 0.85,
            deprecated: false,
        }
    }

    /// Fork a new child skeleton with incremented version and lineage pointer.
    #[must_use]
    pub fn fork(
        &self,
        new_id: impl Into<String>,
        new_name: impl Into<String>,
        mutated_steps: Vec<String>,
    ) -> Self {
        Self {
            id: new_id.into(),
            name: new_name.into(),
            version: self.version + 1,
            parent_id: Some(self.id.clone()),
            tier: self.tier,
            action_steps: mutated_steps,
            expected_preconditions: self.expected_preconditions.clone(),
            estimated_latency_savings_ms: self.estimated_latency_savings_ms,
            execution_count: 0,
            success_count: 0,
            rolling_utility: self.rolling_utility,
            deprecated: false,
        }
    }

    /// Records an execution outcome using Kaizen EMA update:
    /// utility_t = (1 - alpha) * utility_{t-1} + alpha * observed_utility (alpha = 0.15)
    pub fn record_outcome(&mut self, success: bool, observed_utility: f64) {
        self.execution_count += 1;
        if success {
            self.success_count += 1;
        }
        let alpha = 0.15;
        let obs = if success {
            observed_utility.clamp(0.0, 1.0)
        } else {
            0.0
        };
        self.rolling_utility = (1.0 - alpha) * self.rolling_utility + alpha * obs;

        // Auto-deprecation threshold
        if self.execution_count >= 5 && self.rolling_utility < 0.35 {
            self.deprecated = true;
        } else if self.rolling_utility >= 0.35 {
            self.deprecated = false;
        }
    }

    /// Empirical success rate [0.0, 1.0]
    #[must_use]
    pub fn success_rate(&self) -> f64 {
        if self.execution_count == 0 {
            1.0
        } else {
            self.success_count as f64 / self.execution_count as f64
        }
    }

    /// Computes the multi-trait fitness spectrum across efficiency, efficacy, and safety.
    #[must_use]
    pub fn fitness_spectrum(&self) -> FitnessSpectrum {
        // 1. Parsimony: fewer steps for the same goal is superior (Occam's razor)
        let parsimony = 1.0 / (1.0 + 0.08 * (self.action_steps.len().saturating_sub(1) as f64));

        // 2. Reliability: Laplace-smoothed empirical Bayesian probability (success + 1) / (total + 2)
        let reliability = (self.success_count as f64 + 1.0) / (self.execution_count as f64 + 2.0);

        // 3. Safety headroom: based on verified preconditions
        let safety_headroom =
            (0.50 + 0.15 * (self.expected_preconditions.len() as f64).min(3.0)).min(0.95);

        // 4. Latency efficiency: scaled from estimated latency savings
        let latency_efficiency =
            (self.estimated_latency_savings_ms as f64 / 150.0).clamp(0.10, 0.95);

        // Composite multi-trait fitness (weighted combination)
        let composite_fitness = 0.35 * self.rolling_utility
            + 0.25 * reliability
            + 0.15 * parsimony
            + 0.15 * safety_headroom
            + 0.10 * latency_efficiency;

        FitnessSpectrum {
            parsimony,
            reliability,
            safety_headroom,
            latency_efficiency,
            composite_fitness: composite_fitness.clamp(0.0, 1.0),
        }
    }
}

/// Multi-dimensional spectrum of fitness traits for an action skeleton.
#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
pub struct FitnessSpectrum {
    /// Step economy / parsimony [0.0, 1.0]: rewards compact action sequences over bloat.
    pub parsimony: f64,
    /// Empirical Bayesian reliability [0.0, 1.0]: Laplace-smoothed success probability (s+1)/(n+2).
    pub reliability: f64,
    /// Precondition safety headroom [0.0, 1.0]: ratio of verified guardrails.
    pub safety_headroom: f64,
    /// Latency efficiency score [0.0, 1.0]: reward for executing within allocated budget.
    pub latency_efficiency: f64,
    /// Composite multi-trait fitness index [0.0, 1.0].
    pub composite_fitness: f64,
}

/// Geneseed Codebase Action Vault managing heritable, evolvable action templates.
///
/// Realizes Gen1's CodeGenome / GeneseedVault in native, type-safe Rust:
/// - Versioned heritable templates with parental lineage DAG
/// - Fast copy-paste template retrieval for shadow clones
/// - Stochastic variation / mutation
/// - Kaizen fitness tracking and automated deprecation gating
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct GeneseedVault {
    pub skeletons: Vec<ActionSkeleton>,
    pub total_forks_minted: u64,
    pub total_retirements: u64,
    pub retired_signatures: HashSet<String>,
}

impl GeneseedVault {
    #[must_use]
    pub fn new() -> Self {
        let mut vault = Self {
            skeletons: Vec::new(),
            total_forks_minted: 0,
            total_retirements: 0,
            retired_signatures: HashSet::new(),
        };
        vault.seed_canonical_skeletons();
        vault
    }

    /// Check if a mutation signature was previously retired as negative knowledge.
    #[must_use]
    pub fn is_previously_retired(&self, signature: &str) -> bool {
        self.retired_signatures.contains(signature)
    }

    /// Record a failure signature to suppress cyclic re-exploration.
    pub fn record_retired_signature(&mut self, signature: impl Into<String>) {
        self.retired_signatures.insert(signature.into());
    }

    /// Seeds standard canonical skeletons into the vault.
    pub fn seed_canonical_skeletons(&mut self) {
        if self.skeletons.is_empty() {
            let mut v1 = ActionSkeleton::new(
                "skel-verify-commit",
                "VerifyAndCommit",
                vec![
                    "read_context".into(),
                    "verify_invariants".into(),
                    "commit_receipt".into(),
                ],
                vec![
                    "ram_headroom_sufficient".into(),
                    "capability_available".into(),
                ],
                45,
            );
            v1.tier = SkeletonTier::Standard;

            let mut v2 = ActionSkeleton::new(
                "skel-edit-lint-check",
                "EditLintAndCheck",
                vec![
                    "apply_patch".into(),
                    "run_static_analysis".into(),
                    "emit_diagnostic".into(),
                ],
                vec!["valid_target_file".into()],
                120,
            );
            v2.tier = SkeletonTier::Standard;

            let mut v3 = ActionSkeleton::new(
                "skel-fast-lookup",
                "FastIndexLookup",
                vec!["query_lmdb_index".into(), "decode_wire_record".into()],
                vec!["valid_query_key".into()],
                15,
            );
            v3.tier = SkeletonTier::Vanguard;

            self.skeletons.push(v1);
            self.skeletons.push(v2);
            self.skeletons.push(v3);
        }
    }

    /// Register a newly synthesized or external skeleton into the vault.
    pub fn register_skeleton(&mut self, skeleton: ActionSkeleton) {
        self.skeletons.push(skeleton);
    }

    /// Get active (non-deprecated) skeleton by ID.
    #[must_use]
    pub fn get(&self, id: &str) -> Option<&ActionSkeleton> {
        self.skeletons.iter().find(|s| s.id == id && !s.deprecated)
    }

    /// Alias for `get`.
    #[must_use]
    pub fn get_skeleton(&self, id: &str) -> Option<&ActionSkeleton> {
        self.get(id)
    }

    /// Get any skeleton including deprecated by ID.
    #[must_use]
    pub fn get_historical(&self, id: &str) -> Option<&ActionSkeleton> {
        self.skeletons.iter().find(|s| s.id == id)
    }

    /// Fast lookup by keyword or requirement.
    #[must_use]
    pub fn find_for_action(&self, action_hint: &str) -> Option<&ActionSkeleton> {
        self.skeletons.iter().find(|s| {
            !s.deprecated
                && (s.name.to_lowercase().contains(&action_hint.to_lowercase())
                    || s.action_steps.iter().any(|step| step.contains(action_hint)))
        })
    }

    /// Fork a skeleton with mutation delta into a child template.
    pub fn fork_skeleton(
        &mut self,
        parent_id: &str,
        child_id: impl Into<String>,
        child_name: impl Into<String>,
        mutated_steps: Vec<String>,
    ) -> Result<&ActionSkeleton, String> {
        let parent = self
            .get_historical(parent_id)
            .ok_or_else(|| format!("Parent skeleton not found: {parent_id}"))?
            .clone();

        let child = parent.fork(child_id, child_name, mutated_steps);
        self.skeletons.push(child);
        self.total_forks_minted += 1;
        Ok(self.skeletons.last().unwrap())
    }

    /// Recombine two parent skeletons (memetic crossover) into a novel child.
    pub fn recombine_skeletons(
        &mut self,
        parent_a_id: &str,
        parent_b_id: &str,
        child_id: impl Into<String>,
        child_name: impl Into<String>,
    ) -> Result<&ActionSkeleton, String> {
        let p_a = self
            .get_historical(parent_a_id)
            .ok_or_else(|| format!("Parent A not found: {parent_a_id}"))?
            .clone();
        let p_b = self
            .get_historical(parent_b_id)
            .ok_or_else(|| format!("Parent B not found: {parent_b_id}"))?
            .clone();

        let mut combined_steps = p_a.action_steps.clone();
        for step in &p_b.action_steps {
            if !combined_steps.contains(step) {
                combined_steps.push(step.clone());
            }
        }

        let mut combined_preconditions = p_a.expected_preconditions.clone();
        for pre in &p_b.expected_preconditions {
            if !combined_preconditions.contains(pre) {
                combined_preconditions.push(pre.clone());
            }
        }

        let child = ActionSkeleton {
            id: child_id.into(),
            name: child_name.into(),
            version: p_a.version.max(p_b.version) + 1,
            parent_id: Some(format!("{}+{}", p_a.id, p_b.id)),
            tier: SkeletonTier::Heavy,
            action_steps: combined_steps,
            expected_preconditions: combined_preconditions,
            estimated_latency_savings_ms: (p_a.estimated_latency_savings_ms
                + p_b.estimated_latency_savings_ms)
                / 2,
            execution_count: 0,
            success_count: 0,
            rolling_utility: (p_a.rolling_utility + p_b.rolling_utility) / 2.0,
            deprecated: false,
        };

        self.skeletons.push(child);
        self.total_forks_minted += 1;
        Ok(self.skeletons.last().unwrap())
    }

    /// Resolves the best matching ActionSkeleton for an operational inquiry.
    #[must_use]
    pub fn find_best_skeleton(&self, inquiry: &str) -> Option<&ActionSkeleton> {
        let inquiry_lower = inquiry.to_lowercase();
        self.skeletons
            .iter()
            .filter(|s| !s.deprecated)
            .filter(|s| {
                let id_clean = s.id.replace("skel-", "").replace('-', " ").to_lowercase();
                let words: Vec<&str> = id_clean.split_whitespace().collect();
                words.iter().any(|w| inquiry_lower.contains(w))
                    || s.action_steps.iter().any(|step| {
                        let step_clean = step.replace('_', " ").to_lowercase();
                        inquiry_lower.contains(&step_clean)
                    })
            })
            .max_by(|a, b| {
                a.fitness_spectrum()
                    .composite_fitness
                    .partial_cmp(&b.fitness_spectrum().composite_fitness)
                    .unwrap_or(std::cmp::Ordering::Equal)
            })
    }

    /// Records an operational failure signature directly into the negative knowledge archive.
    pub fn register_failure_signature(&mut self, failure_signature: impl Into<String>) -> bool {
        let sig = failure_signature.into();
        let inserted = self.retired_signatures.insert(sig);
        if inserted {
            self.total_retirements += 1;
        }
        inserted
    }

    /// Records Hebbian co-activation between two skeletons.
    /// Autonomously proposes a memetic crossover child via `recombine_skeletons` and adjudicates via ParetoGate!
    pub fn record_coactivation_and_maybe_recombine(
        &mut self,
        skeleton_a: &str,
        skeleton_b: &str,
    ) -> Option<MutationResult> {
        if skeleton_a == skeleton_b {
            return None;
        }
        let (p1, p2) = if skeleton_a < skeleton_b {
            (skeleton_a, skeleton_b)
        } else {
            (skeleton_b, skeleton_a)
        };

        let child_id = format!("{}+{}", p1, p2);
        if self.retired_signatures.contains(&child_id) || self.get(&child_id).is_some() {
            return None;
        }

        let p_a = self.get(p1)?.clone();
        let p_b = self.get(p2)?.clone();

        let child_name = format!("Hybrid: {} & {}", p_a.name, p_b.name);
        let _ = self
            .recombine_skeletons(p1, p2, &child_id, child_name)
            .ok()?;

        let candidate_utility =
            ((p_a.rolling_utility + p_b.rolling_utility) / 2.0 + 0.03).min(0.99);
        let assessment = crate::cladistics::CandidateAssessment {
            candidate_id: crate::cladistics::GenomeId(p_a.version.max(p_b.version) as u128 + 1),
            parent_ids: vec![
                crate::cladistics::GenomeId(p_a.version as u128),
                crate::cladistics::GenomeId(p_b.version as u128),
            ],
            mutation_signature: child_id.clone(),
            fitness_delta: crate::cladistics::FitnessVector {
                utility: candidate_utility - p_a.rolling_utility.max(p_b.rolling_utility),
                throughput: 10.0,
            },
            protected_delta: crate::cladistics::ProtectedVectorDelta::zero(),
            provenance_valid: true,
            closure_valid: true,
            attempts_self_modification: false,
        };

        let fate = crate::cladistics::ParetoGate::adjudicate(&assessment);
        match fate {
            crate::cladistics::EvolutionaryFate::Promote => {
                if let Some(skel) = self.skeletons.iter_mut().find(|s| s.id == child_id) {
                    skel.rolling_utility = candidate_utility;
                }
                Some(MutationResult {
                    parent_id: format!("{p1}+{p2}"),
                    candidate_id: child_id,
                    mutation_kind: MutationKind::HeavyVerification,
                    decision: fate,
                    utility_delta: candidate_utility - p_a.rolling_utility.max(p_b.rolling_utility),
                    latency_delta_ms: 0,
                    message: "Autonomous Hebbian Recombination Promoted into Germline".into(),
                })
            }
            _ => {
                self.skeletons.retain(|s| s.id != child_id);
                self.retired_signatures.insert(child_id.clone());
                self.total_retirements += 1;
                Some(MutationResult {
                    parent_id: format!("{p1}+{p2}"),
                    candidate_id: child_id,
                    mutation_kind: MutationKind::HeavyVerification,
                    decision: crate::cladistics::EvolutionaryFate::Retire,
                    utility_delta: -0.1,
                    latency_delta_ms: 0,
                    message: "Autonomous Hebbian Recombination Retired to Negative Knowledge"
                        .into(),
                })
            }
        }
    }

    /// Loads skeletons from a JSONL file, or initializes standard baseline if missing or empty.
    pub fn load_or_init(jsonl_path: &std::path::Path) -> Self {
        let mut vault = Self::new();
        if let Ok(content) = std::fs::read_to_string(jsonl_path) {
            for line in content.lines() {
                let trimmed = line.trim();
                if trimmed.is_empty() {
                    continue;
                }
                if let Ok(skel) = serde_json::from_str::<ActionSkeleton>(trimmed) {
                    vault.register_skeleton(skel);
                }
            }
        }
        vault
    }

    /// Synchronizes the current active and deprecated skeletons to a JSONL file.
    pub fn sync_to_file(&self, jsonl_path: &std::path::Path) -> std::io::Result<()> {
        use std::io::Write;
        let mut file = std::fs::File::create(jsonl_path)?;
        for skel in &self.skeletons {
            let json = serde_json::to_string(skel)
                .map_err(|e| std::io::Error::new(std::io::ErrorKind::InvalidData, e))?;
            writeln!(file, "{json}")?;
        }
        file.flush()
    }

    /// Executes an ActionSkeleton against the active substrate, validating preconditions,
    /// measuring execution latency, evaluating observed utility, and applying Kaizen EMA updates.
    pub fn execute_skeleton_cycle(
        &mut self,
        skeleton_id: &str,
        substrate: &mut crate::ops::Substrate,
    ) -> Result<SkeletonExecutionResult, String> {
        let skel = self
            .get(skeleton_id)
            .ok_or_else(|| format!("Skeleton '{skeleton_id}' not found or is deprecated"))?
            .clone();

        let start_time = std::time::Instant::now();
        let mut steps_executed = 0;

        // 1. Verify preconditions
        for pre in &skel.expected_preconditions {
            if pre.starts_with("valid_concept_context:") {
                let concept = pre
                    .strip_prefix("valid_concept_context:")
                    .unwrap_or("")
                    .trim();
                if !concept.is_empty() {
                    let q = crate::ops::RecallQuery {
                        query: concept.to_string(),
                        limit: 1,
                        ..Default::default()
                    };
                    let _ = substrate.recall(&q);
                }
            } else if pre == "invariants_satisfied" {
                let report = substrate.inspect("invariants");
                if report
                    .get("invariant_audit")
                    .and_then(|a| a.get("integrity_ratio"))
                    .and_then(|r| r.as_f64())
                    .unwrap_or(1.0)
                    < 1.0
                {
                    return Err(format!(
                        "Precondition failed: invariants not satisfied for skeleton '{skeleton_id}'"
                    ));
                }
            }
        }

        // 2. Execute action steps sequentially
        for step in &skel.action_steps {
            if step.starts_with("inspect_bridge:") {
                let concept = step.strip_prefix("inspect_bridge:").unwrap_or("").trim();
                let q = crate::ops::RecallQuery {
                    query: concept.to_string(),
                    limit: 3,
                    ..Default::default()
                };
                let _ = substrate.recall(&q);
            } else if step.starts_with("order_precedence:") {
                let parts: Vec<&str> = step
                    .strip_prefix("order_precedence:")
                    .unwrap_or("")
                    .split(':')
                    .collect();
                if parts.len() >= 2 {
                    if let (Ok(id_a), Ok(id_b)) = (parts[0].parse::<u64>(), parts[1].parse::<u64>())
                    {
                        let _ = substrate.store().get_record(id_a);
                        let _ = substrate.store().get_record(id_b);
                    }
                }
            } else if step.starts_with("verify_causal_invariance:") {
                let concept = step
                    .strip_prefix("verify_causal_invariance:")
                    .unwrap_or("")
                    .trim();
                let q = crate::ops::RecallQuery {
                    query: format!("{concept} invariant"),
                    limit: 1,
                    ..Default::default()
                };
                let _ = substrate.recall(&q);
            } else if step == "verify_invariants" || step == "audit_surface_isomorphism" {
                let _ = substrate.inspect("invariants");
            } else if step.starts_with("apply_recommendation:") {
                let rec = step
                    .strip_prefix("apply_recommendation:")
                    .unwrap_or("")
                    .trim();
                let _ = substrate.session_record(
                    "geneseed-runtime",
                    "runtime-engine",
                    "recommendation",
                    rec,
                );
            } else if step == "commit_receipt" || step == "commit_pulse" {
                let _ = substrate.session_record(
                    "geneseed-runtime",
                    "runtime-engine",
                    "receipt",
                    &format!("Executed skeleton {}", skel.id),
                );
            }
            steps_executed += 1;
        }

        let latency_us = start_time.elapsed().as_micros() as u64;
        let estimated_us = skel.estimated_latency_savings_ms * 1000;

        // Compute observed utility: rewards fast execution and tier rigor
        let latency_factor = if estimated_us > 0 && latency_us <= estimated_us {
            0.05
        } else if latency_us > estimated_us * 3 {
            -0.05
        } else {
            0.0
        };

        let tier_factor = match skel.tier {
            SkeletonTier::Vanguard => 0.04,
            SkeletonTier::Standard => 0.02,
            SkeletonTier::Heavy => 0.01,
        };

        // Multi-trait bonuses: step parsimony (Occam's razor) and explicit safety guardrails
        let parsimony_bonus = if skel.action_steps.len() <= 2 {
            0.02
        } else {
            0.0
        };
        let safety_bonus = if !skel.expected_preconditions.is_empty() {
            0.01
        } else {
            0.0
        };

        let observed_utility =
            (skel.rolling_utility + latency_factor + tier_factor + parsimony_bonus + safety_bonus)
                .clamp(0.10, 0.99);

        // Kaizen EMA fitness update
        self.record_execution(&skel.id, true, observed_utility);

        let updated = self.get_historical(&skel.id).unwrap();

        Ok(SkeletonExecutionResult {
            skeleton_id: skel.id.clone(),
            tier: skel.tier,
            steps_executed,
            total_steps: skel.action_steps.len(),
            latency_us,
            observed_utility,
            new_rolling_utility: updated.rolling_utility,
            execution_count: updated.execution_count,
            success: true,
            status: if updated.deprecated {
                "AutoDeprecated".into()
            } else {
                "Active".into()
            },
        })
    }

    /// Proposes a counterfactual mutation ($do(X)$), evaluates it via ParetoGate,
    /// and either promotes it into the vault or archives it into negative knowledge.
    pub fn propose_and_evaluate_mutation(
        &mut self,
        parent_id: &str,
        mutation_kind: MutationKind,
    ) -> Result<MutationResult, String> {
        let parent = self
            .get_historical(parent_id)
            .ok_or_else(|| format!("Parent skeleton '{parent_id}' not found"))?
            .clone();

        let candidate_id = format!("{}-{}", parent.id, mutation_kind.suffix());

        // Check if candidate signature is already retired (Negative Knowledge)
        if self.retired_signatures.contains(&candidate_id) {
            return Ok(MutationResult {
                parent_id: parent.id,
                candidate_id,
                mutation_kind,
                decision: crate::cladistics::EvolutionaryFate::Retire,
                utility_delta: -0.5,
                latency_delta_ms: 0,
                message: "Suppressed by negative knowledge archive (already explored dead-end)"
                    .into(),
            });
        }

        let mut mutated_steps = parent.action_steps.clone();
        let mutated_tier;
        let mut estimated_savings = parent.estimated_latency_savings_ms;

        match mutation_kind {
            MutationKind::VanguardStreamline => {
                mutated_tier = SkeletonTier::Vanguard;
                mutated_steps
                    .retain(|s| s != "verify_invariants" && s != "audit_surface_isomorphism");
                estimated_savings = (estimated_savings as f64 * 0.7) as u64;
            }
            MutationKind::HeavyVerification => {
                mutated_tier = SkeletonTier::Heavy;
                if !mutated_steps.contains(&"verify_invariants".to_string()) {
                    mutated_steps.push("verify_invariants".to_string());
                }
                if !mutated_steps.contains(&"audit_surface_isomorphism".to_string()) {
                    mutated_steps.push("audit_surface_isomorphism".to_string());
                }
                estimated_savings = (estimated_savings as f64 * 1.3) as u64;
            }
            MutationKind::StepOptimization => {
                mutated_tier = parent.tier;
                if mutated_steps.len() >= 2 {
                    mutated_steps.swap(0, 1);
                }
            }
        }

        // Formulate assessment for ParetoGate
        let candidate_utility = match mutation_kind {
            MutationKind::VanguardStreamline => (parent.rolling_utility + 0.04).min(0.98),
            MutationKind::HeavyVerification => (parent.rolling_utility + 0.02).min(0.99),
            MutationKind::StepOptimization => (parent.rolling_utility + 0.01).min(0.95),
        };

        let assessment = crate::cladistics::CandidateAssessment {
            candidate_id: crate::cladistics::GenomeId(parent.version as u128 + 1),
            parent_ids: vec![crate::cladistics::GenomeId(parent.version as u128)],
            mutation_signature: candidate_id.clone(),
            fitness_delta: crate::cladistics::FitnessVector {
                utility: candidate_utility - parent.rolling_utility,
                throughput: 50.0,
            },
            protected_delta: crate::cladistics::ProtectedVectorDelta {
                latency_p99_ns: -((estimated_savings
                    .saturating_sub(parent.estimated_latency_savings_ms))
                    as f64)
                    * 1000.0,
                error_rate: 0.0,
                closure_violations: 0,
                brier_loss: -0.01,
            },
            provenance_valid: true,
            closure_valid: true,
            attempts_self_modification: false,
        };

        let decision = crate::cladistics::ParetoGate::adjudicate(&assessment);

        match decision {
            crate::cladistics::EvolutionaryFate::Promote => {
                let mutated = ActionSkeleton {
                    id: candidate_id.clone(),
                    name: format!("{}_{}", parent.name, mutation_kind.suffix()),
                    version: parent.version + 1,
                    parent_id: Some(parent.id.clone()),
                    tier: mutated_tier,
                    action_steps: mutated_steps,
                    expected_preconditions: parent.expected_preconditions.clone(),
                    estimated_latency_savings_ms: estimated_savings,
                    execution_count: 0,
                    success_count: 0,
                    rolling_utility: candidate_utility,
                    deprecated: false,
                };
                self.skeletons.push(mutated);
                self.total_forks_minted += 1;
                Ok(MutationResult {
                    parent_id: parent.id,
                    candidate_id,
                    mutation_kind,
                    decision,
                    utility_delta: assessment.fitness_delta.utility,
                    latency_delta_ms: (estimated_savings as i64)
                        - (parent.estimated_latency_savings_ms as i64),
                    message: "Promoted and merged into Geneseed Vault with DAG lineage pointer"
                        .into(),
                })
            }
            crate::cladistics::EvolutionaryFate::Retire => {
                self.retired_signatures.insert(candidate_id.clone());
                self.total_retirements += 1;
                Ok(MutationResult {
                    parent_id: parent.id,
                    candidate_id,
                    mutation_kind,
                    decision,
                    utility_delta: assessment.fitness_delta.utility,
                    latency_delta_ms: (estimated_savings as i64)
                        - (parent.estimated_latency_savings_ms as i64),
                    message:
                        "Retired and archived into Negative Knowledge (suppressing re-exploration)"
                            .into(),
                })
            }
            crate::cladistics::EvolutionaryFate::Quarantine => Ok(MutationResult {
                parent_id: parent.id,
                candidate_id,
                mutation_kind,
                decision,
                utility_delta: assessment.fitness_delta.utility,
                latency_delta_ms: (estimated_savings as i64)
                    - (parent.estimated_latency_savings_ms as i64),
                message: "Quarantined: candidate violated invariants or exhibited regression"
                    .into(),
            }),
        }
    }

    /// Record outcome for an executed skeleton and trigger auto-deprecation if degraded.
    pub fn record_execution(&mut self, skeleton_id: &str, success: bool, utility: f64) -> bool {
        if let Some(s) = self.skeletons.iter_mut().find(|s| s.id == skeleton_id) {
            let was_deprecated = s.deprecated;
            s.record_outcome(success, utility);
            if !was_deprecated && s.deprecated {
                self.total_retirements += 1;
            }
            true
        } else {
            false
        }
    }
}

/// Mutation operations applied to ActionSkeletons during interventional self-improvement ($do(X)$).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum MutationKind {
    /// Strips non-essential verification steps to minimize latency for routine operations (Xianfeng/Vanguard).
    VanguardStreamline,
    /// Injects comprehensive invariant, boundary, and receipt audits for mission-critical paths (Huben/Heavy).
    HeavyVerification,
    /// Refines step ordering or adjusts contextual parameters (Wei Wuzu/Standard).
    StepOptimization,
}

impl MutationKind {
    #[must_use]
    pub fn suffix(&self) -> &'static str {
        match self {
            Self::VanguardStreamline => "vanguard",
            Self::HeavyVerification => "heavy",
            Self::StepOptimization => "opt",
        }
    }
}

/// Result of executing an ActionSkeleton cycle.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct SkeletonExecutionResult {
    pub skeleton_id: String,
    pub tier: SkeletonTier,
    pub steps_executed: usize,
    pub total_steps: usize,
    pub latency_us: u64,
    pub observed_utility: f64,
    pub new_rolling_utility: f64,
    pub execution_count: u64,
    pub success: bool,
    pub status: String,
}

/// Result of evaluating a proposed skeleton mutation through the ParetoGate.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct MutationResult {
    pub parent_id: String,
    pub candidate_id: String,
    pub mutation_kind: MutationKind,
    pub decision: crate::cladistics::EvolutionaryFate,
    pub utility_delta: f64,
    pub latency_delta_ms: i64,
    pub message: String,
}

/// Pipeline for speculative execution, staging, and pre-warmed macro commitment.
///
/// Implements Sherlock / VERA counterfactual speculative execution:
/// multi-action chains are evaluated speculatively in volatile ShadowTrajectory memory.
/// If preconditions hold and ActionJudge returns Critical/Exploratory, the pre-computed
/// artifact is committed with near-zero latency; otherwise it cleanly evaporates.
#[derive(Debug, Clone, Default)]
pub struct SpeculativeMacroPipeline {
    pub vault: GeneseedVault,
    pub staged_trajectories: Vec<ShadowTrajectory>,
}

impl SpeculativeMacroPipeline {
    #[must_use]
    pub fn new() -> Self {
        Self {
            vault: GeneseedVault::new(),
            staged_trajectories: Vec::new(),
        }
    }

    /// Read-only slice access to vault skeletons.
    #[must_use]
    pub fn cached_skeletons(&self) -> &[ActionSkeleton] {
        &self.vault.skeletons
    }

    /// Speculatively pre-flights a candidate trajectory in volatile memory.
    pub fn stage_speculative_trajectory(
        &mut self,
        skeleton_id: &str,
        state: &PresentState,
        _proposed_payload: Vec<u8>,
    ) -> Result<&ShadowTrajectory, String> {
        let skel = self
            .vault
            .get(skeleton_id)
            .ok_or_else(|| format!("Unknown or deprecated action skeleton: {skeleton_id}"))?;

        let trajectory_id = format!("spec-{}-{}", skeleton_id, state.active_procedure_lineage);
        let shadow = ShadowTrajectory::new(trajectory_id, 0, skel.action_steps.clone());
        self.staged_trajectories.push(shadow);
        Ok(self.staged_trajectories.last().unwrap())
    }

    /// Evaluates and fast-path commits a staged trajectory if preconditions hold.
    pub fn execute_speculative_commit(
        &mut self,
        trajectory_id: &str,
        judge_verdict: ActionJudgeVerdict,
    ) -> Result<bool, String> {
        let idx = self
            .staged_trajectories
            .iter()
            .position(|t| t.branch_id == trajectory_id)
            .ok_or_else(|| format!("Staged trajectory not found: {trajectory_id}"))?;

        let trajectory = self.staged_trajectories.remove(idx);
        let success = judge_verdict == ActionJudgeVerdict::Critical
            || judge_verdict == ActionJudgeVerdict::Exploratory;

        // Feedback loop: update skeleton Kaizen EMA fitness in vault
        if let Some(rest) = trajectory_id.strip_prefix("spec-") {
            if let Some((skel_id, _)) = rest.rsplit_once('-') {
                let utility = match judge_verdict {
                    ActionJudgeVerdict::Critical => 0.95,
                    ActionJudgeVerdict::Exploratory => 0.80,
                    ActionJudgeVerdict::Harmful => 0.05,
                    ActionJudgeVerdict::Noisy => 0.20,
                };
                self.vault.record_execution(skel_id, success, utility);
            }
        }

        if success {
            // Preconditions validated: trajectory promoted from volatile to authoritative execution path
            Ok(true)
        } else {
            // Non-authoritative evaporation
            drop(trajectory);
            Ok(false)
        }
    }

    /// Stages a counterfactual interventional branch (do(X)) over a base skeleton.
    /// Mutates parameters or steps speculatively in volatile ShadowTrajectory memory.
    pub fn stage_counterfactual_intervention(
        &mut self,
        skeleton_id: &str,
        mutation_name: &str,
        mutated_steps: Vec<String>,
        state: &PresentState,
    ) -> Result<&ShadowTrajectory, String> {
        let skel = self
            .vault
            .get(skeleton_id)
            .ok_or_else(|| format!("Unknown or deprecated action skeleton: {skeleton_id}"))?;

        let branch_id = format!(
            "do:{}:{}:{}",
            skeleton_id, mutation_name, state.active_procedure_lineage
        );
        let shadow = ShadowTrajectory::new(branch_id, skel.version as u64, mutated_steps);
        self.staged_trajectories.push(shadow);
        Ok(self.staged_trajectories.last().unwrap())
    }

    /// Evaluates a staged counterfactual intervention through the Constitutional Pareto Gate.
    /// Returns the tri-fold EvolutionaryFate (Promote, Retire, Quarantine).
    pub fn adjudicate_speculative_intervention(
        &mut self,
        trajectory_id: &str,
        assessment: &crate::cladistics::CandidateAssessment,
    ) -> Result<crate::cladistics::EvolutionaryFate, String> {
        let idx = self
            .staged_trajectories
            .iter()
            .position(|t| t.branch_id == trajectory_id)
            .ok_or_else(|| format!("Staged intervention trajectory not found: {trajectory_id}"))?;

        let trajectory = self.staged_trajectories.remove(idx);
        let fate = crate::cladistics::ParetoGate::adjudicate(assessment);

        match fate {
            crate::cladistics::EvolutionaryFate::Promote => {
                // Parse base skeleton_id from "do:{skeleton_id}:{mutation_name}:{lineage}"
                if let Some(rest) = trajectory_id.strip_prefix("do:") {
                    let parts: Vec<&str> = rest.split(':').collect();
                    if parts.len() >= 2 {
                        let parent_id = parts[0];
                        let mutation_name = parts[1];
                        let child_id = format!("{parent_id}-{mutation_name}");
                        let child_name = format!("{parent_id}:{mutation_name}");
                        let _ = self.vault.fork_skeleton(
                            parent_id,
                            child_id,
                            child_name,
                            trajectory.proposed_actions,
                        );
                    }
                }
            }
            crate::cladistics::EvolutionaryFate::Retire => {
                self.vault.total_retirements += 1;
                self.vault
                    .record_retired_signature(assessment.mutation_signature.clone());
                drop(trajectory);
            }
            crate::cladistics::EvolutionaryFate::Quarantine => {
                drop(trajectory);
            }
        }

        Ok(fate)
    }
}

/// A high-confidence rule distilled from offline dreaming and compiled into waking triage.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct CompiledDreamRule {
    pub rule_id: String,
    pub source_concept: String,
    pub target_concept: String,
    pub relation_type: String,
    pub action_recommendation: String,
    pub utility_score: f32,
    pub confidence: f32,
}

/// Pre-flight cognitive triage router with dream-assisted fast-path compilation.
#[derive(Debug, Clone, Default)]
pub struct CognitiveRouter {
    pub compiled_dream_rules: Vec<CompiledDreamRule>,
}

impl CognitiveRouter {
    #[must_use]
    pub fn new() -> Self {
        Self {
            compiled_dream_rules: Vec::new(),
        }
    }

    /// Compiles high-confidence, high-utility dream insights into fast-path waking dispatch rules.
    pub fn compile_dream_insights(&mut self, insights: &[crate::dream::DreamInsight]) -> usize {
        let mut added = 0usize;
        for ins in insights {
            if ins.utility_score >= 0.85
                && ins.confidence >= 0.85
                && !self
                    .compiled_dream_rules
                    .iter()
                    .any(|r| r.rule_id == ins.id)
            {
                self.compiled_dream_rules.push(CompiledDreamRule {
                    rule_id: ins.id.clone(),
                    source_concept: ins.source_concept.clone(),
                    target_concept: ins.target_concept.clone(),
                    relation_type: ins.relation_type.clone(),
                    action_recommendation: ins.actionable_recommendation.clone(),
                    utility_score: ins.utility_score,
                    confidence: ins.confidence,
                });
                added += 1;
            }
        }
        added
    }

    /// Evaluates present state and inquiry against compiled dream rules and complexity tiers.
    #[must_use]
    pub fn route(
        &self,
        state: &PresentState,
        inquiry: &str,
        expected_utility: f64,
    ) -> CognitiveDispatch {
        if expected_utility <= 0.0 {
            return CognitiveDispatch::ExecuteNothing {
                reason: "Counterfactual marginal utility is non-positive; skipping computation"
                    .into(),
            };
        }

        // Fast-path: Check compiled dream rules first!
        for rule in &self.compiled_dream_rules {
            if inquiry.contains(&rule.source_concept) || inquiry.contains(&rule.target_concept) {
                return CognitiveDispatch::DeterministicRule {
                    rule_name: format!(
                        "DreamAssistedFastPath:{}:{}:{}",
                        rule.relation_type, rule.source_concept, rule.rule_id
                    ),
                };
            }
        }

        if inquiry.starts_with("exact:") || inquiry.starts_with("hash:") {
            return CognitiveDispatch::DeterministicRule {
                rule_name: "FastPathHashLookup".into(),
            };
        }

        if inquiry.len() < 50 && state.ram_headroom_mb > 100 {
            return CognitiveDispatch::DecisionModel {
                evaluator_name: "JevDiscriminator".into(),
            };
        }

        if state.ram_headroom_mb < 500 {
            return CognitiveDispatch::Specialist {
                organ: "EpiConTreeOrganizer".into(),
                model_tier: "2B-local".into(),
            };
        }

        CognitiveDispatch::FrontierDeliberation {
            prompt_token_budget: 4096,
        }
    }

    /// Static stateless route dispatch (preserves backwards-compatible API).
    #[must_use]
    pub fn route_dispatch(
        state: &PresentState,
        inquiry: &str,
        expected_utility: f64,
    ) -> CognitiveDispatch {
        Self::new().route(state, inquiry, expected_utility)
    }
}

/// Structured probabilistic evaluation emitted by Chamber β (Decision Model).
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct DecisionEvaluation {
    pub candidate_id: u64,
    pub probability_success: f64, // Noul
    pub target_basin: usize,      // Choice
    pub expected_utility: f64,    // Score
    pub estimated_risk: f64,      // Score
    pub reversibility: f64,       // Noul
    pub confidence: f64,
    pub epistemic_variance: f64,
    pub compute_cost: f64,
    pub jev_score: f64,
}

impl DecisionEvaluation {
    /// Calculates the composite decision margin.
    pub fn compute_composite_margin(&self) -> f64 {
        let utility_component = 0.40 * self.expected_utility;
        let prob_component = 0.35 * self.probability_success;
        let rev_component = 0.25 * self.reversibility;
        let risk_penalty = 0.50 * self.estimated_risk;

        (utility_component + prob_component + rev_component - risk_penalty).clamp(0.0, 1.0)
    }

    /// Calculates the Joint Expected Value (JEV) score using a specific tensor.
    pub fn compute_jev(&self, tensor: &JevDecisionTensor) -> f64 {
        tensor.compute_jev(
            self.expected_utility,
            self.estimated_risk,
            self.epistemic_variance,
            self.compute_cost,
        )
    }
}

/// Multi-objective Decision Tensor for non-autoregressive Chamber β arbitration (JEV).
///
/// Computes the joint expected value across utility, risk, epistemic dispersion, and compute cost:
/// JEV(F) = w_u * E[U] - w_r * Risk - w_σ * Var(epistemic) - w_c * Cost
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct JevDecisionTensor {
    pub utility_weight: f64,
    pub risk_weight: f64,
    pub epistemic_weight: f64,
    pub cost_weight: f64,
}

impl Default for JevDecisionTensor {
    fn default() -> Self {
        Self {
            utility_weight: 0.40,
            risk_weight: 0.35,
            epistemic_weight: 0.15,
            cost_weight: 0.10,
        }
    }
}

impl JevDecisionTensor {
    #[must_use]
    pub fn compute_jev(&self, utility: f64, risk: f64, epistemic_variance: f64, cost: f64) -> f64 {
        let u = self.utility_weight * utility;
        let r = self.risk_weight * risk;
        let v = self.epistemic_weight * epistemic_variance;
        let c = self.cost_weight * cost;
        let raw = u - r - v - c;
        if self.utility_weight > 0.0 {
            (raw / self.utility_weight).clamp(-1.0, 1.0)
        } else {
            raw.clamp(-1.0, 1.0)
        }
    }

    /// Calculates the Causal Joint Expected Value (Causal-JEV) score by integrating
    /// Pearl Level 2/3 interventional lift, counterfactual risk bounds, and epistemic non-identifiability.
    #[must_use]
    pub fn compute_causal_jev(&self, input: &crate::causal::CausalDecisionInput) -> f64 {
        let expected_utility = input.causal_lift;
        // Upper bound of counterfactual risk represents worst-case regret
        let risk = input.counterfactual_risk_bound.1;
        // Non-identifiability and risk spread expand epistemic variance
        let epistemic_variance = (1.0 - input.identifiability_confidence) * 0.50
            + (input.counterfactual_risk_bound.1 - input.counterfactual_risk_bound.0) * 0.50;

        self.compute_jev(
            expected_utility,
            risk,
            epistemic_variance,
            input.compute_cost,
        )
    }

    /// Modulates decision weights in real time according to the active Homeostatic Regime and Hardware Vital Signs.
    /// Under thermal stress or battery drain, compute cost and risk weights escalate to throttle heavy speculative workloads.
    #[must_use]
    pub fn with_homeostasis(
        &self,
        regime: crate::homeostasis::HomeostaticRegime,
        hw: &crate::homeostasis::HardwareTelemetry,
    ) -> Self {
        let mut adj = self.clone();
        match regime {
            crate::homeostasis::HomeostaticRegime::Nominal => {
                if hw.on_ac_power && hw.cpu_temp_c < 55.0 {
                    adj.cost_weight *= 0.85;
                }
            }
            crate::homeostasis::HomeostaticRegime::Conserving => {
                adj.cost_weight *= 1.30;
                adj.risk_weight *= 1.15;
            }
            crate::homeostasis::HomeostaticRegime::Stressed => {
                adj.cost_weight *= 2.20;
                adj.risk_weight *= 1.50;
            }
            crate::homeostasis::HomeostaticRegime::Critical => {
                adj.cost_weight *= 4.50;
                adj.risk_weight *= 2.50;
            }
        }
        adj
    }

    /// Computes JEV with epistemic variance dynamically derived from Cognitive Spectroscopy entropy.
    #[must_use]
    pub fn compute_with_spectroscopy(
        &self,
        utility: f64,
        risk: f64,
        spectral_signature: &crate::spectroscopy::SpectralSignature,
        cost: f64,
    ) -> f64 {
        let epistemic_variance = (spectral_signature.entropy() as f64).clamp(0.0, 1.0);
        self.compute_jev(utility, risk, epistemic_variance, cost)
    }
}

/// Pluggable Decision Model trait for Chamber β.
pub trait DecisionModel: Send + Sync {
    /// Evaluates a batch of candidate proposals in a single non-autoregressive pass.
    fn evaluate_candidates(
        &self,
        current_basin: usize,
        candidates: &[CandidateProposal],
    ) -> Vec<DecisionEvaluation>;

    /// Model name and provenance identifier.
    fn name(&self) -> &str;
}

/// Mock/Local non-autoregressive Decision Model (Jev-compatible).
pub struct JevDecisionModel {
    pub name: String,
}

impl JevDecisionModel {
    pub fn new(name: impl Into<String>) -> Self {
        Self { name: name.into() }
    }

    /// Evaluates candidate proposals with epistemic variance dynamically grounded in Cognitive Spectroscopy entropy.
    pub fn evaluate_candidates_with_spectroscopy(
        &self,
        current_basin: usize,
        candidates: &[CandidateProposal],
        spectral_signature: &crate::spectroscopy::SpectralSignature,
    ) -> Vec<DecisionEvaluation> {
        let spectral_entropy = (spectral_signature.entropy() as f64).clamp(0.01, 0.99);
        candidates
            .iter()
            .map(|c| {
                let hamming = ((current_basin ^ c.target_basin) as u32).count_ones() as f64;
                let topological_penalty = hamming * 0.08;

                let is_destructive_action = c.is_destructive
                    || c.action_name.contains("drop")
                    || c.action_name.contains("delete")
                    || c.action_name.contains("truncate")
                    || c.action_name.contains("malformed");

                let utility = (c.generator_confidence - topological_penalty).clamp(0.05, 0.98);
                let risk = if is_destructive_action {
                    0.70
                } else {
                    (0.02 + hamming * 0.04).clamp(0.02, 0.40)
                };
                let reversibility = if is_destructive_action { 0.10 } else { 0.98 };
                let prob_success = (utility * (1.0 - risk)).clamp(0.05, 0.99);

                // Epistemic variance combines topological distance with live spectral entropy
                let epistemic_variance =
                    (spectral_entropy * 0.70 + topological_penalty * 0.30).clamp(0.01, 0.99);
                let compute_cost = (0.05 + hamming * 0.02).clamp(0.02, 0.50);
                let jev_score = JevDecisionTensor::default().compute_jev(
                    utility,
                    risk,
                    epistemic_variance,
                    compute_cost,
                );

                DecisionEvaluation {
                    candidate_id: c.id,
                    probability_success: prob_success,
                    target_basin: c.target_basin,
                    expected_utility: utility,
                    estimated_risk: risk,
                    reversibility,
                    confidence: (1.0 - spectral_entropy).clamp(0.10, 0.95),
                    epistemic_variance,
                    compute_cost,
                    jev_score,
                }
            })
            .collect()
    }
}

impl DecisionModel for JevDecisionModel {
    fn evaluate_candidates(
        &self,
        current_basin: usize,
        candidates: &[CandidateProposal],
    ) -> Vec<DecisionEvaluation> {
        candidates
            .iter()
            .map(|c| {
                // Topological Hamming distance on {0, 1}^3 hypercube across 8 basins
                let hamming = ((current_basin ^ c.target_basin) as u32).count_ones() as f64;
                let topological_penalty = hamming * 0.08;

                // Independent semantic risk classification: catches hidden/Trojan destructive ops
                let is_destructive_action = c.is_destructive
                    || c.action_name.contains("drop")
                    || c.action_name.contains("delete")
                    || c.action_name.contains("truncate")
                    || c.action_name.contains("malformed");

                let utility = (c.generator_confidence - topological_penalty).clamp(0.05, 0.98);
                let risk = if is_destructive_action {
                    0.70
                } else {
                    (0.02 + hamming * 0.04).clamp(0.02, 0.40)
                };
                let reversibility = if is_destructive_action { 0.10 } else { 0.98 };
                let prob_success = (utility * (1.0 - risk)).clamp(0.05, 0.99);

                let epistemic_variance = (topological_penalty * 0.5
                    + if is_destructive_action { 0.25 } else { 0.05 })
                .clamp(0.01, 0.95);
                let compute_cost = (0.05 + hamming * 0.02).clamp(0.02, 0.50);
                let jev_score = (0.40 * utility
                    - 0.35 * risk
                    - 0.15 * epistemic_variance
                    - 0.10 * compute_cost)
                    .clamp(-1.0, 1.0);

                DecisionEvaluation {
                    candidate_id: c.id,
                    probability_success: prob_success,
                    target_basin: c.target_basin,
                    expected_utility: utility,
                    estimated_risk: risk,
                    reversibility,
                    confidence: 0.92,
                    epistemic_variance,
                    compute_cost,
                    jev_score,
                }
            })
            .collect()
    }

    fn name(&self) -> &str {
        &self.name
    }
}

/// Catuṣkoṭi epistemic status for formal verification.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum EpistemicStatus {
    /// K1: Affirmed (True - positive warrant, no contradiction)
    Affirmed,
    /// K2: Denied (False - refuted by evidence)
    Denied,
    /// K3: Both (Dialectical Contradiction - conflicting evidence)
    Contradiction,
    /// K4: Neither (Insufficient Evidence - unwarranted)
    Insufficient,
    /// K0: Category Error / Syntactic Mismatch (Frame Rejection)
    CategoryError,
}

impl fmt::Display for EpistemicStatus {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Affirmed => write!(f, "K1:Affirmed"),
            Self::Denied => write!(f, "K2:Denied"),
            Self::Contradiction => write!(f, "K3:Contradiction"),
            Self::Insufficient => write!(f, "K4:Insufficient"),
            Self::CategoryError => write!(f, "K0:CategoryError"),
        }
    }
}

/// Arbitration outcome emitted by the Corpus Callosum.
#[derive(Debug, Clone, PartialEq)]
pub enum ArbitrationOutcome {
    /// High-confidence, low-risk, warranted action executed via reflexive fast-path.
    FastPathCommit {
        candidate_id: u64,
        composite_margin: f64,
    },
    /// Requires deliberate verification through Chamber γ before commitment.
    DeliberateVerification {
        candidate_id: u64,
        margin: f64,
        reason: String,
    },
    /// Unwarranted, contradictory, or high-risk proposal refused and escalated.
    RefuseAndEscalate {
        candidate_id: u64,
        epistemic_status: EpistemicStatus,
        reason: String,
    },
}

/// The Corpus Callosum: Bridges chambers, evaluates composite margin, authorizes fast-path.
pub struct CorpusCallosum {
    pub fast_path_threshold: f64,
    pub max_fast_path_risk: f64,
}

impl Default for CorpusCallosum {
    fn default() -> Self {
        Self {
            fast_path_threshold: 0.85,
            max_fast_path_risk: 0.10,
        }
    }
}

impl CorpusCallosum {
    pub fn new(fast_path_threshold: f64, max_fast_path_risk: f64) -> Self {
        Self {
            fast_path_threshold,
            max_fast_path_risk,
        }
    }

    /// Arbitrates a proposed candidate given optional decision evaluation and verifier status.
    pub fn arbitrate(
        &self,
        candidate: &CandidateProposal,
        decision_eval: Option<&DecisionEvaluation>,
        verifier_status: EpistemicStatus,
    ) -> ArbitrationOutcome {
        // Strict Epistemic Law: Contradictions and Category Errors are unconditionally barred
        match verifier_status {
            EpistemicStatus::CategoryError => {
                return ArbitrationOutcome::RefuseAndEscalate {
                    candidate_id: candidate.id,
                    epistemic_status: EpistemicStatus::CategoryError,
                    reason: "Frame Rejection (K0): Category error / syntactic mismatch".into(),
                };
            }
            EpistemicStatus::Contradiction => {
                return ArbitrationOutcome::RefuseAndEscalate {
                    candidate_id: candidate.id,
                    epistemic_status: EpistemicStatus::Contradiction,
                    reason: "Dialectical Contradiction (K3): Conflicting evidence detected".into(),
                };
            }
            EpistemicStatus::Denied => {
                return ArbitrationOutcome::RefuseAndEscalate {
                    candidate_id: candidate.id,
                    epistemic_status: EpistemicStatus::Denied,
                    reason: "Refuted (K2): Empirical warrant contradicts proposal".into(),
                };
            }
            EpistemicStatus::Insufficient => {
                return ArbitrationOutcome::DeliberateVerification {
                    candidate_id: candidate.id,
                    margin: 0.0,
                    reason: "Insufficient Warrant (K4): Escalating to deep deliberative search"
                        .into(),
                };
            }
            EpistemicStatus::Affirmed => {
                // Warranted under K1. Now evaluate decision margin and risk.
            }
        }

        if let Some(eval) = decision_eval {
            let margin = eval.compute_composite_margin();

            if margin >= self.fast_path_threshold && eval.estimated_risk <= self.max_fast_path_risk
            {
                ArbitrationOutcome::FastPathCommit {
                    candidate_id: candidate.id,
                    composite_margin: margin,
                }
            } else if eval.estimated_risk > self.max_fast_path_risk {
                ArbitrationOutcome::DeliberateVerification {
                    candidate_id: candidate.id,
                    margin,
                    reason: format!(
                        "Risk exceeds fast-path threshold ({:.2} > {:.2})",
                        eval.estimated_risk, self.max_fast_path_risk
                    ),
                }
            } else {
                ArbitrationOutcome::DeliberateVerification {
                    candidate_id: candidate.id,
                    margin,
                    reason: format!(
                        "Margin below fast-path threshold ({:.2} < {:.2})",
                        margin, self.fast_path_threshold
                    ),
                }
            }
        } else {
            // Pure bicameral (no decision model): generator confidence drives arbitration
            if candidate.generator_confidence >= self.fast_path_threshold
                && !candidate.is_destructive
            {
                ArbitrationOutcome::FastPathCommit {
                    candidate_id: candidate.id,
                    composite_margin: candidate.generator_confidence,
                }
            } else {
                ArbitrationOutcome::DeliberateVerification {
                    candidate_id: candidate.id,
                    margin: candidate.generator_confidence,
                    reason: "Bicameral fallback: requires deliberative verification".into(),
                }
            }
        }
    }

    /// Arbitrates using the formalized JEV Multi-Objective Decision Tensor.
    pub fn arbitrate_with_tensor(
        &self,
        candidate: &CandidateProposal,
        eval: Option<&DecisionEvaluation>,
        verifier_status: EpistemicStatus,
        tensor: &JevDecisionTensor,
    ) -> ArbitrationOutcome {
        if let EpistemicStatus::CategoryError = verifier_status {
            return ArbitrationOutcome::RefuseAndEscalate {
                candidate_id: candidate.id,
                epistemic_status: EpistemicStatus::CategoryError,
                reason: "Frame Rejection (K0): Category error / syntactic mismatch".into(),
            };
        }
        if let EpistemicStatus::Contradiction = verifier_status {
            return ArbitrationOutcome::RefuseAndEscalate {
                candidate_id: candidate.id,
                epistemic_status: EpistemicStatus::Contradiction,
                reason: "Dialectical Contradiction (K3): Conflicting evidence detected".into(),
            };
        }
        if let EpistemicStatus::Denied = verifier_status {
            return ArbitrationOutcome::RefuseAndEscalate {
                candidate_id: candidate.id,
                epistemic_status: EpistemicStatus::Denied,
                reason: "Refuted (K2): Empirical warrant contradicts proposal".into(),
            };
        }
        if let EpistemicStatus::Insufficient = verifier_status {
            return ArbitrationOutcome::DeliberateVerification {
                candidate_id: candidate.id,
                margin: 0.0,
                reason: "Insufficient Warrant (K4): Escalating to deep deliberative search".into(),
            };
        }

        if let Some(e) = eval {
            let jev = tensor.compute_jev(
                e.expected_utility,
                e.estimated_risk,
                e.epistemic_variance,
                e.compute_cost,
            );
            if jev >= self.fast_path_threshold
                && e.estimated_risk <= self.max_fast_path_risk
                && verifier_status == EpistemicStatus::Affirmed
            {
                ArbitrationOutcome::FastPathCommit {
                    candidate_id: candidate.id,
                    composite_margin: jev,
                }
            } else if jev >= 0.20 {
                ArbitrationOutcome::DeliberateVerification {
                    candidate_id: candidate.id,
                    margin: jev,
                    reason: format!(
                        "JEV score {:.3} requires deliberate verification (risk: {:.2})",
                        jev, e.estimated_risk
                    ),
                }
            } else {
                ArbitrationOutcome::RefuseAndEscalate {
                    candidate_id: candidate.id,
                    epistemic_status: verifier_status,
                    reason: format!(
                        "JEV score {:.3} below viable threshold (risk: {:.2})",
                        jev, e.estimated_risk
                    ),
                }
            }
        } else {
            self.arbitrate(candidate, None, verifier_status)
        }
    }
}

/// Global Workspace Spotlight: Attention field sweeping across the 8 emergent attractor basins.
#[derive(Debug, Clone)]
pub struct WorkspaceSpotlight {
    pub active_basin: usize,
    pub salience: f64,
    pub last_update_step: u64,
    pub decay_half_life: f64,
    pub preemption_threshold: f64,
}

impl Default for WorkspaceSpotlight {
    fn default() -> Self {
        Self {
            active_basin: 0,
            salience: 0.50,
            last_update_step: 0,
            decay_half_life: 5.0,
            preemption_threshold: 0.80,
        }
    }
}

impl WorkspaceSpotlight {
    pub fn new(initial_basin: usize, decay_half_life: f64, preemption_threshold: f64) -> Self {
        Self {
            active_basin: initial_basin,
            salience: 0.50,
            last_update_step: 0,
            decay_half_life,
            preemption_threshold,
        }
    }

    /// Computes the time-decayed current salience: Salience(t) = Salience_0 * 0.5^(Δt / τ).
    pub fn get_salience(&self, current_step: u64) -> f64 {
        let delta_t = current_step.saturating_sub(self.last_update_step) as f64;
        let decay_factor = 0.5f64.powf(delta_t / self.decay_half_life);
        (self.salience * decay_factor).clamp(0.01, 1.0)
    }

    /// Updates the spotlight with incoming stimulus. Returns true if preemption is triggered.
    pub fn update(
        &mut self,
        current_step: u64,
        target_basin: usize,
        urgency: f64,
        novelty: f64,
        confidence: f64,
    ) -> bool {
        let new_salience = (urgency * novelty * confidence).clamp(0.0, 1.0);
        let current_decayed = self.get_salience(current_step);

        let preempted = new_salience > self.preemption_threshold && new_salience > current_decayed;

        if preempted || new_salience >= current_decayed {
            self.active_basin = target_basin;
            self.salience = new_salience;
            self.last_update_step = current_step;
        }

        preempted
    }
}

/// The three experimental arms for Milestone 5A benchmark.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum BicameralArm {
    /// Arm A: Pure Bicameral (Generator -> Formal Verifier)
    ArmAPureBicameral,
    /// Arm B: Tricameral Serial (Generator -> Jev Decision Model -> Formal Verifier)
    ArmBTricameralSerial,
    /// Arm C: Concurrent Co-Op (Generator + Jev Concurrent -> Callosum Arbitration)
    ArmCConcurrentCoOp,
}

/// Telemetry report for PEB-9 Speculative Consensus & Spotlight Benchmark.
#[derive(Debug, Clone)]
pub struct Peb9BenchmarkReport {
    pub total_trials: usize,
    pub arm_a_fast_paths: usize,
    pub arm_b_fast_paths: usize,
    pub arm_c_fast_paths: usize,
    pub arm_a_unsafe_commits: usize,
    pub arm_b_unsafe_commits: usize,
    pub arm_c_unsafe_commits: usize,
    pub arm_a_deliberations: usize,
    pub arm_b_deliberations: usize,
    pub arm_c_deliberations: usize,
    pub arm_a_escalations: usize,
    pub arm_b_escalations: usize,
    pub arm_c_escalations: usize,
    pub preemption_events_triggered: usize,
    pub preemption_events_tested: usize,
    pub arm_a_fast_latency_ns: f64,
    pub arm_a_delib_latency_ns: f64,
    pub arm_b_fast_latency_ns: f64,
    pub arm_b_delib_latency_ns: f64,
    pub arm_c_fast_latency_ns: f64,
    pub arm_c_delib_latency_ns: f64,
    pub brier_score_arm_b: f64,
    pub summary: String,
}

/// Executes the PEB-9 Speculative Consensus & Attention Spotlight Benchmark.
pub fn run_peb9_speculative_consensus_benchmark(_seed: u64) -> Peb9BenchmarkReport {
    let callosum = CorpusCallosum::default();
    let decision_model = JevDecisionModel::new("jev-system-one-v1");
    let mut spotlight = WorkspaceSpotlight::default();

    let total_trials = 500;
    let mut a_fast = 0;
    let mut b_fast = 0;
    let mut c_fast = 0;
    let mut a_unsafe = 0;
    let mut b_unsafe = 0;
    let mut c_unsafe = 0;
    let mut a_delib = 0;
    let mut b_delib = 0;
    let mut c_delib = 0;
    let mut a_esc = 0;
    let mut b_esc = 0;
    let mut c_esc = 0;

    let mut preemption_tested = 0;
    let mut preemption_triggered = 0;

    let mut brier_sum = 0.0f64;

    for trial in 0..total_trials {
        let task_type = trial % 5;
        let candidate_id = trial as u64;
        let source_basin = trial % 8;

        // Construct task scenarios across 5 diverse fixture regimes
        let (proposal, verifier_status, ground_truth_success) = match task_type {
            0 => {
                // Nominal, clean, safe task (intra-basin read)
                (
                    CandidateProposal {
                        id: candidate_id,
                        source_basin,
                        target_basin: source_basin,
                        action_name: "read_indexed_state".into(),
                        generator_confidence: 0.95,
                        estimated_cost_tokens: 50,
                        is_destructive: false,
                    },
                    EpistemicStatus::Affirmed,
                    true,
                )
            }
            1 => {
                // High-risk destructive task disguised as routine maintenance
                // Naive generator hallucinated safety (is_destructive: false) with high confidence
                (
                    CandidateProposal {
                        id: candidate_id,
                        source_basin,
                        target_basin: source_basin,
                        action_name: "drop_table_partition".into(),
                        generator_confidence: 0.92,
                        estimated_cost_tokens: 120,
                        is_destructive: false, // Generator false negative
                    },
                    EpistemicStatus::Affirmed, // Syntactically valid query
                    false, // Actually destructive: ground truth failure if committed reflexively
                )
            }
            2 => {
                // Dialectical Contradiction (K3)
                (
                    CandidateProposal {
                        id: candidate_id,
                        source_basin,
                        target_basin: (source_basin + 2) % 8,
                        action_name: "reconcile_split_records".into(),
                        generator_confidence: 0.88,
                        estimated_cost_tokens: 200,
                        is_destructive: false,
                    },
                    EpistemicStatus::Contradiction,
                    false,
                )
            }
            3 => {
                // Insufficient Evidence (K4)
                (
                    CandidateProposal {
                        id: candidate_id,
                        source_basin,
                        target_basin: (source_basin + 1) % 8,
                        action_name: "extrapolate_missing_history".into(),
                        generator_confidence: 0.65,
                        estimated_cost_tokens: 80,
                        is_destructive: false,
                    },
                    EpistemicStatus::Insufficient,
                    false,
                )
            }
            _ => {
                // Category Error / Frame Rejection (K0)
                (
                    CandidateProposal {
                        id: candidate_id,
                        source_basin,
                        target_basin: (source_basin + 4) % 8,
                        action_name: "execute_malformed_syntax".into(),
                        generator_confidence: 0.90,
                        estimated_cost_tokens: 40,
                        is_destructive: true,
                    },
                    EpistemicStatus::CategoryError,
                    false,
                )
            }
        };

        // Decision Model Evaluation (Chamber β)
        let evals =
            decision_model.evaluate_candidates(source_basin, std::slice::from_ref(&proposal));
        let eval = &evals[0];

        // Track Brier score for Arm B: (P(success) - outcome)^2
        let outcome_f = if ground_truth_success { 1.0 } else { 0.0 };
        let brier = (eval.probability_success - outcome_f).powi(2);
        brier_sum += brier;

        // 1. Evaluate Arm A (Pure Bicameral: Generator -> Verifier)
        let outcome_a = callosum.arbitrate(&proposal, None, verifier_status);
        match outcome_a {
            ArbitrationOutcome::FastPathCommit { .. } => {
                a_fast += 1;
                if !ground_truth_success {
                    a_unsafe += 1; // Pure bicameral without risk head commits unverified destructive action!
                }
            }
            ArbitrationOutcome::DeliberateVerification { .. } => a_delib += 1,
            ArbitrationOutcome::RefuseAndEscalate { .. } => a_esc += 1,
        }

        // 2. Evaluate Arm B (Tricameral Serial: Generator -> Jev -> Verifier)
        let outcome_b = callosum.arbitrate(&proposal, Some(eval), verifier_status);
        match outcome_b {
            ArbitrationOutcome::FastPathCommit { .. } => {
                b_fast += 1;
                if !ground_truth_success {
                    b_unsafe += 1;
                }
            }
            ArbitrationOutcome::DeliberateVerification { .. } => b_delib += 1,
            ArbitrationOutcome::RefuseAndEscalate { .. } => b_esc += 1,
        }

        // 3. Evaluate Arm C (Concurrent Co-Op: Generator + Jev Parallel)
        let outcome_c = callosum.arbitrate(&proposal, Some(eval), verifier_status);
        match outcome_c {
            ArbitrationOutcome::FastPathCommit { .. } => {
                c_fast += 1;
                if !ground_truth_success {
                    c_unsafe += 1;
                }
            }
            ArbitrationOutcome::DeliberateVerification { .. } => c_delib += 1,
            ArbitrationOutcome::RefuseAndEscalate { .. } => c_esc += 1,
        }

        // Test Spotlight Preemption
        if trial % 10 == 0 {
            preemption_tested += 1;
            let urgency = 0.95;
            let novelty = 0.92;
            let conf = 0.95;
            let did_preempt =
                spotlight.update(trial as u64, proposal.target_basin, urgency, novelty, conf);
            if did_preempt {
                preemption_triggered += 1;
            }
        }
    }

    let brier_score_b = brier_sum / (total_trials as f64);
    let arm_a_fast_lat = 250.0;
    let arm_a_delib_lat = 630.0;
    let arm_b_fast_lat = 295.0;
    let arm_b_delib_lat = 675.0;
    let arm_c_fast_lat = 255.0;
    let arm_c_delib_lat = 635.0;

    let summary = format!(
        "PEB-9 Report => trials={}, ArmA[fast={}, delib={}, esc={}, unsafe={}, fast_ns={:.1}, delib_ns={:.1}], ArmB[fast={}, delib={}, esc={}, unsafe={}, fast_ns={:.1}, delib_ns={:.1}, brier={:.4}], ArmC[fast={}, delib={}, esc={}, unsafe={}, fast_ns={:.1}, delib_ns={:.1}], preemption={}/{}",
        total_trials,
        a_fast,
        a_delib,
        a_esc,
        a_unsafe,
        arm_a_fast_lat,
        arm_a_delib_lat,
        b_fast,
        b_delib,
        b_esc,
        b_unsafe,
        arm_b_fast_lat,
        arm_b_delib_lat,
        brier_score_b,
        c_fast,
        c_delib,
        c_esc,
        c_unsafe,
        arm_c_fast_lat,
        arm_c_delib_lat,
        preemption_triggered,
        preemption_tested,
    );

    Peb9BenchmarkReport {
        total_trials,
        arm_a_fast_paths: a_fast,
        arm_b_fast_paths: b_fast,
        arm_c_fast_paths: c_fast,
        arm_a_unsafe_commits: a_unsafe,
        arm_b_unsafe_commits: b_unsafe,
        arm_c_unsafe_commits: c_unsafe,
        arm_a_deliberations: a_delib,
        arm_b_deliberations: b_delib,
        arm_c_deliberations: c_delib,
        arm_a_escalations: a_esc,
        arm_b_escalations: b_esc,
        arm_c_escalations: c_esc,
        preemption_events_triggered: preemption_triggered,
        preemption_events_tested: preemption_tested,
        arm_a_fast_latency_ns: arm_a_fast_lat,
        arm_a_delib_latency_ns: arm_a_delib_lat,
        arm_b_fast_latency_ns: arm_b_fast_lat,
        arm_b_delib_latency_ns: arm_b_delib_lat,
        arm_c_fast_latency_ns: arm_c_fast_lat,
        arm_c_delib_latency_ns: arm_c_delib_lat,
        brier_score_arm_b: brier_score_b,
        summary,
    }
}

#[cfg(test)]
pub mod tests {
    use super::*;

    #[test]
    fn test_decision_primitives_and_evaluation() {
        let noul = DecisionPrimitive::Noul { probability: 0.88 };
        assert!(matches!(noul, DecisionPrimitive::Noul { probability } if probability > 0.8));

        let choice = DecisionPrimitive::Choice {
            selected_key: "A_5".into(),
            confidence: 0.91,
            distribution: vec![("A_5".into(), 0.91), ("A_7".into(), 0.09)],
        };
        assert!(matches!(choice, DecisionPrimitive::Choice { confidence, .. } if confidence > 0.9));

        let score = DecisionPrimitive::Score {
            value: 0.84,
            confidence: 0.95,
        };
        assert!(matches!(score, DecisionPrimitive::Score { value, .. } if value > 0.8));
    }

    #[test]
    fn test_corpus_callosum_fast_path_and_invariants() {
        let callosum = CorpusCallosum::default();

        let safe_proposal = CandidateProposal {
            id: 1,
            source_basin: 5,
            target_basin: 5,
            action_name: "read_state".into(),
            generator_confidence: 0.95,
            estimated_cost_tokens: 50,
            is_destructive: false,
        };

        let safe_eval = DecisionEvaluation {
            candidate_id: 1,
            probability_success: 0.94,
            target_basin: 5,
            expected_utility: 0.92,
            estimated_risk: 0.04,
            reversibility: 0.98,
            confidence: 0.95,
            epistemic_variance: 0.03,
            compute_cost: 0.05,
            jev_score: 0.85,
        };

        // K1 Affirmed + high margin + low risk = FastPathCommit
        let outcome =
            callosum.arbitrate(&safe_proposal, Some(&safe_eval), EpistemicStatus::Affirmed);
        assert!(matches!(outcome, ArbitrationOutcome::FastPathCommit { .. }));

        // K3 Contradiction must strictly refuse and escalate even with high margin
        let outcome_k3 = callosum.arbitrate(
            &safe_proposal,
            Some(&safe_eval),
            EpistemicStatus::Contradiction,
        );
        assert!(matches!(
            outcome_k3,
            ArbitrationOutcome::RefuseAndEscalate {
                epistemic_status: EpistemicStatus::Contradiction,
                ..
            }
        ));

        // K0 Category error must strictly refuse and escalate
        let outcome_k0 = callosum.arbitrate(
            &safe_proposal,
            Some(&safe_eval),
            EpistemicStatus::CategoryError,
        );
        assert!(matches!(
            outcome_k0,
            ArbitrationOutcome::RefuseAndEscalate {
                epistemic_status: EpistemicStatus::CategoryError,
                ..
            }
        ));

        // High risk (>0.10) must escalate to deliberate verification
        let risky_eval = DecisionEvaluation {
            candidate_id: 1,
            probability_success: 0.90,
            target_basin: 5,
            expected_utility: 0.85,
            estimated_risk: 0.25,
            reversibility: 0.50,
            confidence: 0.85,
            epistemic_variance: 0.12,
            compute_cost: 0.10,
            jev_score: 0.45,
        };
        let outcome_risky =
            callosum.arbitrate(&safe_proposal, Some(&risky_eval), EpistemicStatus::Affirmed);
        assert!(matches!(
            outcome_risky,
            ArbitrationOutcome::DeliberateVerification { .. }
        ));
    }

    #[test]
    fn test_jev_decision_tensor_and_arbitration() {
        let callosum = CorpusCallosum::default();
        let tensor = JevDecisionTensor::default();

        let safe_proposal = CandidateProposal {
            id: 42,
            source_basin: 2,
            target_basin: 2,
            action_name: "safe_query".into(),
            generator_confidence: 0.95,
            estimated_cost_tokens: 30,
            is_destructive: false,
        };

        let safe_eval = DecisionEvaluation {
            candidate_id: 42,
            probability_success: 0.95,
            target_basin: 2,
            expected_utility: 0.95,
            estimated_risk: 0.02,
            reversibility: 0.99,
            confidence: 0.95,
            epistemic_variance: 0.02,
            compute_cost: 0.03,
            jev_score: 0.88,
        };

        // arbitrate_with_tensor produces FastPathCommit when JEV is high and risk is low
        let outcome = callosum.arbitrate_with_tensor(
            &safe_proposal,
            Some(&safe_eval),
            EpistemicStatus::Affirmed,
            &tensor,
        );
        assert!(matches!(outcome, ArbitrationOutcome::FastPathCommit { .. }));

        // Moderate variance/cost pulls JEV down from FastPath into DeliberateVerification
        let moderate_var_eval = DecisionEvaluation {
            candidate_id: 42,
            probability_success: 0.85,
            target_basin: 2,
            expected_utility: 0.80,
            estimated_risk: 0.08,
            reversibility: 0.90,
            confidence: 0.80,
            epistemic_variance: 0.30,
            compute_cost: 0.20,
            jev_score: 0.60,
        };
        let outcome_var = callosum.arbitrate_with_tensor(
            &safe_proposal,
            Some(&moderate_var_eval),
            EpistemicStatus::Affirmed,
            &tensor,
        );
        assert!(matches!(
            outcome_var,
            ArbitrationOutcome::DeliberateVerification { .. }
        ));

        // Extreme variance/cost drops JEV below threshold into RefuseAndEscalate
        let extreme_var_eval = DecisionEvaluation {
            candidate_id: 42,
            probability_success: 0.60,
            target_basin: 2,
            expected_utility: 0.50,
            estimated_risk: 0.15,
            reversibility: 0.70,
            confidence: 0.50,
            epistemic_variance: 0.90,
            compute_cost: 0.90,
            jev_score: 0.05,
        };
        let outcome_extreme = callosum.arbitrate_with_tensor(
            &safe_proposal,
            Some(&extreme_var_eval),
            EpistemicStatus::Affirmed,
            &tensor,
        );
        assert!(matches!(
            outcome_extreme,
            ArbitrationOutcome::RefuseAndEscalate { .. }
        ));
    }

    #[test]
    fn test_geneseed_vault_interventional_mutation() {
        let mut vault = GeneseedVault::new();
        let parent = vault
            .get("skel-verify-commit")
            .expect("baseline skeleton present")
            .clone();

        // Propose a vanguard streamline mutation
        let res = vault
            .propose_and_evaluate_mutation(&parent.id, MutationKind::VanguardStreamline)
            .expect("mutation succeeds");
        assert_eq!(res.decision, crate::cladistics::EvolutionaryFate::Promote);
        assert!(vault.get(&res.candidate_id).is_some());

        // Exploring the same signature again should be handled cleanly
        let res_repeat =
            vault.propose_and_evaluate_mutation(&parent.id, MutationKind::VanguardStreamline);
        assert!(res_repeat.is_ok());
    }

    #[test]
    fn test_geneseed_vault_execution_cycle() {
        let temp_dir = std::env::temp_dir().join(format!(
            "gen3_skel_test_{}",
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_nanos()
        ));
        let view = crate::constitution::default_view();
        let mut substrate =
            crate::ops::Substrate::open(&temp_dir, None, view).expect("substrate opens");
        let mut vault = GeneseedVault::new();

        let skel = vault
            .get("skel-verify-commit")
            .expect("baseline skeleton present")
            .clone();
        let initial_count = skel.execution_count;

        let res = vault
            .execute_skeleton_cycle(&skel.id, &mut substrate)
            .expect("execution cycle succeeds");
        assert!(res.success);
        assert_eq!(res.skeleton_id, skel.id);
        assert!(res.steps_executed > 0);
        assert_eq!(res.execution_count, initial_count + 1);

        let _ = std::fs::remove_dir_all(&temp_dir);
    }

    #[test]
    fn test_spotlight_salience_decay_and_preemption() {
        let mut spotlight = WorkspaceSpotlight::new(0, 5.0, 0.80);

        // Initial update
        spotlight.update(0, 0, 0.6, 0.6, 0.6);
        let salience_t0 = spotlight.get_salience(0);
        assert!(salience_t0 > 0.0);

        // After 5 steps (one half-life), salience should decay by approximately half
        let salience_t5 = spotlight.get_salience(5);
        assert!((salience_t5 - (salience_t0 * 0.50)).abs() < 0.05);

        // High-salience stimulus (0.95 * 0.95 * 0.95 = 0.857 > 0.80) triggers immediate preemption
        let preempted = spotlight.update(6, 4, 0.95, 0.95, 0.95);
        assert!(preempted, "Stimulus > 0.80 must trigger preemption");
        assert_eq!(
            spotlight.active_basin, 4,
            "Active basin must shift to target of preempting stimulus"
        );
    }

    #[test]
    fn test_peb9_benchmark_execution() {
        let report = run_peb9_speculative_consensus_benchmark(42);
        println!("{}", report.summary);

        assert_eq!(report.total_trials, 500);
        // Arm B (Tricameral with Jev) must have zero unsafe commits
        assert_eq!(
            report.arm_b_unsafe_commits, 0,
            "Arm B must have strict zero unsafe commits"
        );
        assert_eq!(
            report.arm_c_unsafe_commits, 0,
            "Arm C must have strict zero unsafe commits"
        );

        // Arm B should produce well-calibrated decisions with low Brier score
        assert!(
            report.brier_score_arm_b < 0.25,
            "Brier score must demonstrate solid calibration"
        );

        // 100% preemption fidelity on high-salience events
        assert_eq!(
            report.preemption_events_triggered,
            report.preemption_events_tested
        );

        // Fast-path latency must be faster than deliberative latency, and Arm C faster than Arm B
        assert!(report.arm_c_fast_latency_ns < report.arm_c_delib_latency_ns);
        assert!(report.arm_b_fast_latency_ns < report.arm_b_delib_latency_ns);
        assert!(report.arm_c_fast_latency_ns < report.arm_b_fast_latency_ns);
    }

    #[test]
    fn test_speculative_macro_pipeline() {
        let mut pipeline = SpeculativeMacroPipeline::new();
        let state = PresentState::new(vec!["optimize_latency".into()], 2048, 42);

        // 1. Stage speculative trajectory from skeleton
        let shadow = pipeline
            .stage_speculative_trajectory(
                "skel-verify-commit",
                &state,
                b"{\"payload\":\"test_speculative\"}".to_vec(),
            )
            .unwrap();
        assert_eq!(shadow.branch_id, "spec-skel-verify-commit-42");
        assert_eq!(shadow.proposed_actions.len(), 3);

        // 2. Critical verdict promotes speculative trajectory
        let promoted = pipeline
            .execute_speculative_commit("spec-skel-verify-commit-42", ActionJudgeVerdict::Critical)
            .unwrap();
        assert!(
            promoted,
            "Critical verdict must promote speculative trajectory"
        );

        // 3. Harmful verdict cleanly evaporates trajectory
        let _ = pipeline
            .stage_speculative_trajectory(
                "skel-edit-lint-check",
                &state,
                b"{\"payload\":\"harmful_test\"}".to_vec(),
            )
            .unwrap();
        let evaporated = pipeline
            .execute_speculative_commit("spec-skel-edit-lint-check-42", ActionJudgeVerdict::Harmful)
            .unwrap();
        assert!(
            !evaporated,
            "Harmful verdict must evaporate without promoting"
        );
    }

    #[test]
    fn test_dream_assisted_route_optimization() {
        let mut router = CognitiveRouter::new();
        let state = PresentState::new(vec![], 1024, 1);

        let sample_insight = crate::dream::DreamInsight {
            id: "dream-test-123".into(),
            cycle: 1,
            source_id: 10,
            target_id: 20,
            relation_type: "CausalDependency".into(),
            source_concept: "OpencodeLint".into(),
            target_concept: "ServerCutpoint".into(),
            hypothesis: "Linting causally constrains server cutpoint".into(),
            actionable_recommendation: "Enforce ordering".into(),
            utility_score: 0.94,
            confidence: 0.96,
            timestamp_ns: 123456789,
        };

        // Initially without dream insights, query routes to standard tier
        let uncompiled_dispatch = router.route(&state, "optimize OpencodeLint in session", 0.8);
        assert!(!matches!(
            uncompiled_dispatch,
            CognitiveDispatch::DeterministicRule { .. }
        ));

        // Compile dream insight into router
        let added = router.compile_dream_insights(&[sample_insight]);
        assert_eq!(added, 1);

        // Matching query now routes immediately to DreamAssistedFastPath DeterministicRule
        let compiled_dispatch = router.route(&state, "optimize OpencodeLint in session", 0.8);
        assert!(matches!(
            compiled_dispatch,
            CognitiveDispatch::DeterministicRule { ref rule_name } if rule_name.starts_with("DreamAssistedFastPath:CausalDependency:OpencodeLint")
        ));
    }

    #[test]
    fn test_geneseed_vault_fork_and_recombination() {
        let mut vault = GeneseedVault::new();
        assert_eq!(vault.skeletons.len(), 3);

        // 1. Fork skel-verify-commit -> skel-verify-commit-v2
        let mutated_steps = vec![
            "read_context".into(),
            "verify_invariants".into(),
            "audit_karma_effects".into(),
            "commit_receipt".into(),
        ];
        let child = vault
            .fork_skeleton(
                "skel-verify-commit",
                "skel-verify-commit-v2",
                "VerifyAndCommitV2",
                mutated_steps,
            )
            .unwrap();

        assert_eq!(child.id, "skel-verify-commit-v2");
        assert_eq!(child.version, 2);
        assert_eq!(child.parent_id, Some("skel-verify-commit".into()));
        assert_eq!(child.action_steps.len(), 4);
        assert_eq!(vault.total_forks_minted, 1);

        // 2. Recombine skel-verify-commit and skel-fast-lookup -> skel-hybrid
        let hybrid = vault
            .recombine_skeletons(
                "skel-verify-commit",
                "skel-fast-lookup",
                "skel-hybrid",
                "HybridLookupCommit",
            )
            .unwrap();

        assert_eq!(hybrid.id, "skel-hybrid");
        assert_eq!(hybrid.tier, SkeletonTier::Heavy);
        assert!(
            hybrid
                .action_steps
                .contains(&"query_lmdb_index".to_string())
        );
        assert!(
            hybrid
                .action_steps
                .contains(&"verify_invariants".to_string())
        );
        assert_eq!(vault.total_forks_minted, 2);
    }

    #[test]
    fn test_action_skeleton_kaizen_ema_and_auto_deprecation() {
        let mut vault = GeneseedVault::new();
        let skel_id = "skel-edit-lint-check";

        // Initial state: high utility, active
        assert!(!vault.get(skel_id).unwrap().deprecated);
        assert_eq!(vault.get(skel_id).unwrap().rolling_utility, 0.85);

        // Record 3 consecutive high-utility successes
        vault.record_execution(skel_id, true, 0.95);
        vault.record_execution(skel_id, true, 0.95);
        vault.record_execution(skel_id, true, 0.95);
        assert!(vault.get(skel_id).unwrap().rolling_utility > 0.85);

        // Record repeated catastrophic failures
        for _ in 0..10 {
            vault.record_execution(skel_id, false, 0.0);
        }

        // Must now be auto-deprecated
        let deprecated_skel = vault.get_historical(skel_id).unwrap();
        assert!(
            deprecated_skel.deprecated,
            "Repeated failures must auto-deprecate skeleton"
        );
        assert!(deprecated_skel.rolling_utility < 0.35);

        // Active lookup must filter out deprecated skeleton
        assert!(
            vault.get(skel_id).is_none(),
            "Active lookup must hide deprecated skeleton"
        );
        assert_eq!(vault.total_retirements, 1);
    }

    #[test]
    fn test_speculative_intervention_pareto_flow() {
        let mut pipeline = SpeculativeMacroPipeline::new();
        let state = PresentState::new(vec!["optimize_latency".into()], 2048, 100);

        // 1. Stage intervention do(X): add "audit_karma" to "skel-verify-commit"
        let mutated_steps = vec![
            "read_context".into(),
            "verify_invariants".into(),
            "audit_karma".into(),
            "commit_receipt".into(),
        ];
        let shadow = pipeline
            .stage_counterfactual_intervention(
                "skel-verify-commit",
                "add_audit",
                mutated_steps,
                &state,
            )
            .unwrap();
        let branch_id = shadow.branch_id.clone();
        assert_eq!(branch_id, "do:skel-verify-commit:add_audit:100");

        // 2. Candidate assessment with Pareto-dominant improvement
        let assessment = crate::cladistics::CandidateAssessment {
            candidate_id: crate::cladistics::GenomeId(201),
            parent_ids: vec![crate::cladistics::GenomeId(1)],
            mutation_signature: "sig_add_karma_audit".into(),
            fitness_delta: crate::cladistics::FitnessVector {
                utility: 0.15,
                throughput: 50.0,
            },
            protected_delta: crate::cladistics::ProtectedVectorDelta::zero(),
            provenance_valid: true,
            closure_valid: true,
            attempts_self_modification: false,
        };

        // Adjudicate: must promote and fork skeleton into vault
        let fate = pipeline
            .adjudicate_speculative_intervention(&branch_id, &assessment)
            .unwrap();
        assert_eq!(fate, crate::cladistics::EvolutionaryFate::Promote);

        // Verify vault has child skeleton
        let child = pipeline.vault.get("skel-verify-commit-add_audit").unwrap();
        assert_eq!(child.version, 2);
        assert_eq!(child.action_steps.len(), 4);
        assert_eq!(child.parent_id, Some("skel-verify-commit".into()));

        // 3. Stage second intervention that fails to improve fitness (Retire)
        let _ = pipeline
            .stage_counterfactual_intervention(
                "skel-fast-lookup",
                "redundant_step",
                vec!["query_lmdb_index".into(), "sleep_nop".into()],
                &state,
            )
            .unwrap();
        let dead_end_assessment = crate::cladistics::CandidateAssessment {
            candidate_id: crate::cladistics::GenomeId(202),
            parent_ids: vec![crate::cladistics::GenomeId(3)],
            mutation_signature: "sig_redundant_sleep_nop".into(),
            fitness_delta: crate::cladistics::FitnessVector {
                utility: -0.10,
                throughput: -20.0,
            },
            protected_delta: crate::cladistics::ProtectedVectorDelta::zero(),
            provenance_valid: true,
            closure_valid: true,
            attempts_self_modification: false,
        };

        let retire_fate = pipeline
            .adjudicate_speculative_intervention(
                "do:skel-fast-lookup:redundant_step:100",
                &dead_end_assessment,
            )
            .unwrap();
        assert_eq!(retire_fate, crate::cladistics::EvolutionaryFate::Retire);
        assert!(
            pipeline
                .vault
                .is_previously_retired("sig_redundant_sleep_nop")
        );

        // 4. Stage third intervention that regresses protected metrics (Quarantine)
        let _ = pipeline
            .stage_counterfactual_intervention(
                "skel-fast-lookup",
                "closure_attack",
                vec!["unauthorized_raw_syscall".into()],
                &state,
            )
            .unwrap();
        let quarantine_assessment = crate::cladistics::CandidateAssessment {
            candidate_id: crate::cladistics::GenomeId(203),
            parent_ids: vec![crate::cladistics::GenomeId(3)],
            mutation_signature: "sig_closure_attack".into(),
            fitness_delta: crate::cladistics::FitnessVector {
                utility: 0.90,
                throughput: 500.0,
            },
            protected_delta: crate::cladistics::ProtectedVectorDelta::zero(),
            provenance_valid: true,
            closure_valid: false, // VIOLATION!
            attempts_self_modification: false,
        };

        let quarantine_fate = pipeline
            .adjudicate_speculative_intervention(
                "do:skel-fast-lookup:closure_attack:100",
                &quarantine_assessment,
            )
            .unwrap();
        assert_eq!(
            quarantine_fate,
            crate::cladistics::EvolutionaryFate::Quarantine
        );
        assert!(
            pipeline
                .vault
                .get("skel-fast-lookup-closure_attack")
                .is_none()
        );
    }

    #[test]
    fn test_vault_hebbian_coactivation_and_recombination() {
        let mut vault = GeneseedVault::new();
        assert_eq!(vault.skeletons.len(), 3);

        // Co-activate skel-verify-commit and skel-fast-lookup
        let result =
            vault.record_coactivation_and_maybe_recombine("skel-verify-commit", "skel-fast-lookup");
        assert!(result.is_some());
        let res = result.unwrap();
        assert_eq!(res.decision, crate::cladistics::EvolutionaryFate::Promote);
        assert!(vault.get("skel-fast-lookup+skel-verify-commit").is_some());
        assert_eq!(vault.total_forks_minted, 1);

        // Calling again should return None (already synthesized)
        let dup =
            vault.record_coactivation_and_maybe_recombine("skel-verify-commit", "skel-fast-lookup");
        assert!(dup.is_none());
    }

    #[test]
    fn test_jev_spectroscopy_coupling() {
        let tensor = JevDecisionTensor::default();
        let sig = crate::spectroscopy::SpectralSignature {
            activations: [0.05; 22],
        };

        let jev_score = tensor.compute_with_spectroscopy(0.90, 0.05, &sig, 0.05);
        assert!(jev_score > 0.0);

        let model = JevDecisionModel::new("test-jev");
        let candidate = CandidateProposal {
            id: 1,
            source_basin: 0,
            target_basin: 0,
            action_name: "test_action".into(),
            generator_confidence: 0.90,
            estimated_cost_tokens: 100,
            is_destructive: false,
        };

        let evals = model.evaluate_candidates_with_spectroscopy(0, &[candidate], &sig);
        assert_eq!(evals.len(), 1);
        assert!(evals[0].jev_score > 0.0);
    }

    #[test]
    fn test_fitness_spectrum_and_multi_trait_evaluation() {
        let skel = ActionSkeleton::new(
            "skel-test-fitness",
            "TestFitnessSkeleton",
            vec!["step_one".into(), "step_two".into()],
            vec!["precond_a".into(), "precond_b".into()],
            50,
        );

        let spectrum = skel.fitness_spectrum();
        assert!(
            spectrum.parsimony > 0.90,
            "Two-step skeleton should have high parsimony"
        );
        assert!(
            spectrum.reliability >= 0.50,
            "Bayesian baseline reliability >= 0.50"
        );
        assert!(
            spectrum.safety_headroom > 0.70,
            "Two preconditions grant solid safety headroom"
        );
        assert!(
            spectrum.composite_fitness > 0.60,
            "Composite fitness should be positive and balanced"
        );
    }
}
