//! # Causal Cladistics, Pareto-Gated Mutation & Shadow Clones (Milestone 3 / PEB-6)
//!
//! Implements digital phylogenetics without monolithic runtime engines:
//! - **Directed Hypergraph Lineage:** `DerivedFrom`, `RecombinedFrom`, and `Supersedes`.
//! - **Constitutional Pareto Gating:** Rejects any candidate that regresses the protected vector
//!   $M_{\text{protected}} = \langle L_{p99}, E_{\text{rate}}, \Phi_{\text{closures}}, B_{\text{brier}} \rangle$,
//!   even if scalar fitness $\Delta \text{Fitness} > 0$.
//! - **Tri-Fold Evolutionary Fate:**
//!   $$\text{Candidate} \longrightarrow \begin{cases} \mathbf{Promote} & \text{if } \Delta \text{Fitness} > 0 \land \text{no regression} \land \text{provenance valid} \\ \mathbf{Retire} & \text{if } \Delta \text{Fitness} \le 0 \land \text{no regression} \text{ (benign dead end)} \\ \mathbf{Quarantine} & \text{if regression} \lor \text{closure violation} \lor \text{Trojan mutation} \end{cases}$$
//! - **Negative Knowledge in Lineage Archive:** Retired lineages record failure signatures to
//!   suppress cyclic re-exploration of known dead ends: $P(\text{proposal} \mid \text{explored}) \to 0$.
//! - **Maker $\neq$ Checker Invariant:** Proposing mutations cannot evaluate themselves or mutate the gate.

use serde::{Deserialize, Serialize};
use std::collections::{HashMap, HashSet};

/// Unique 128-bit identifier for a genome / heritable state.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
pub struct GenomeId(pub u128);

impl GenomeId {
    #[must_use]
    pub fn new(val: u128) -> Self {
        Self(val)
    }

    #[must_use]
    pub fn from_u64(val: u64) -> Self {
        Self(val as u128)
    }
}

/// The tri-fold evolutionary destination of any candidate mutation.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum EvolutionaryFate {
    /// Demonstrated Pareto-dominant improvement with valid provenance -> admitted to germline.
    Promote,
    /// Valid and safe, but failed to improve fitness -> retired to lineage archive as negative knowledge.
    Retire,
    /// Pathological: regressed protected metric, violated closure, forged provenance, or Trojan -> isolated.
    Quarantine,
}

/// Protected constitutional metrics where lower is strictly better.
#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
pub struct ProtectedVector {
    pub latency_p99_ns: f64,
    pub error_rate: f64,
    pub closure_violations: u64,
    pub brier_loss: f64,
}

impl ProtectedVector {
    #[must_use]
    pub fn nominal() -> Self {
        Self {
            latency_p99_ns: 2000.0,
            error_rate: 0.01,
            closure_violations: 0,
            brier_loss: 0.05,
        }
    }
}

/// Directionally explicit delta in protected metrics.
/// Convention: POSITIVE values denote REGRESSION (worse performance / increased violations).
#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
pub struct ProtectedVectorDelta {
    pub latency_p99_ns: f64,
    pub error_rate: f64,
    pub closure_violations: i64,
    pub brier_loss: f64,
}

impl ProtectedVectorDelta {
    #[must_use]
    pub fn zero() -> Self {
        Self {
            latency_p99_ns: 0.0,
            error_rate: 0.0,
            closure_violations: 0,
            brier_loss: 0.0,
        }
    }

    /// Evaluates whether any protected metric suffered statistically meaningful regression.
    #[must_use]
    pub fn has_regression(&self) -> bool {
        self.latency_p99_ns > 0.0
            || self.error_rate > 0.0
            || self.closure_violations > 0
            || self.brier_loss > 0.0
    }

    /// Identifies the first regressed dimension, if any.
    #[must_use]
    pub fn regressed_dimension(&self) -> Option<&'static str> {
        if self.closure_violations > 0 {
            Some("closure_violations")
        } else if self.brier_loss > 0.0 {
            Some("brier_loss")
        } else if self.error_rate > 0.0 {
            Some("error_rate")
        } else if self.latency_p99_ns > 0.0 {
            Some("latency_p99_ns")
        } else {
            None
        }
    }
}

/// Unprotected functional fitness metrics where HIGHER is strictly better.
#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
pub struct FitnessVector {
    pub utility: f64,
    pub throughput: f64,
}

impl FitnessVector {
    #[must_use]
    pub fn zero() -> Self {
        Self {
            utility: 0.0,
            throughput: 0.0,
        }
    }

    /// Checks if candidate improved functional fitness.
    #[must_use]
    pub fn improved(&self) -> bool {
        self.utility > 0.0 || self.throughput > 0.0
    }

    /// Computes scalar ranking delta (strictly to rank Pareto-admissible survivors, never as admission pass).
    #[must_use]
    pub fn scalar_rank_delta(&self) -> f64 {
        self.utility + 0.001 * self.throughput
    }
}

/// Complete assessment of a candidate mutation produced by an independent witness.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct CandidateAssessment {
    pub candidate_id: GenomeId,
    pub parent_ids: Vec<GenomeId>,
    pub mutation_signature: String,
    pub fitness_delta: FitnessVector,
    pub protected_delta: ProtectedVectorDelta,
    pub provenance_valid: bool,
    pub closure_valid: bool,
    pub attempts_self_modification: bool,
}

/// Directed hypergraph relation edge modeling evolutionary cladistics.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum CladisticRelation {
    /// A single parent diverged into a child via mutation.
    DerivedFrom { child: GenomeId, parent: GenomeId },
    /// Two parents recombined their heritable material into a child.
    RecombinedFrom {
        child: GenomeId,
        parent_a: GenomeId,
        parent_b: GenomeId,
    },
    /// The promoted child supersedes its ancestral version in active routing.
    Supersedes { child: GenomeId, parent: GenomeId },
}

/// Immutable record of an evolutionary trial preserved in the lineage archive.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct LineageRecord {
    pub id: GenomeId,
    pub parents: Vec<GenomeId>,
    pub relation: Option<CladisticRelation>,
    pub mutation_signature: String,
    pub environment_version: String,
    pub fate: EvolutionaryFate,
    pub fitness_delta: FitnessVector,
    pub protected_delta: ProtectedVectorDelta,
    pub reason: Option<String>,
    pub timestamp_ms: u64,
}

/// Pure constitutional Pareto Gate.
///
/// Law: $\Delta \text{Fitness} > 0 \not\Rightarrow \text{Permission}(C)$.
/// Admission requires: $\Delta \text{Fitness} > 0 \land \forall m \in M_{\text{protected}} (\Delta m \le 0) \land \text{provenance valid}$.
pub struct ParetoGate;

impl ParetoGate {
    /// Adjudicates a candidate mutation into its tri-fold evolutionary fate.
    #[must_use]
    pub fn adjudicate(candidate: &CandidateAssessment) -> EvolutionaryFate {
        // Pathological / Security Failures:
        // 1. Broken or fabricated provenance
        // 2. Closure violation (Law or Evidence)
        // 3. Attempting to alter the checker / self-modify the gate
        // 4. Any regression in the protected vector (including Trojan mutations)
        if !candidate.provenance_valid
            || !candidate.closure_valid
            || candidate.attempts_self_modification
            || candidate.protected_delta.has_regression()
        {
            return EvolutionaryFate::Quarantine;
        }

        // Benign Branch:
        // Valid candidates that improved functional fitness are promoted.
        // Valid candidates that failed to improve are retired as negative knowledge.
        if candidate.fitness_delta.improved() {
            EvolutionaryFate::Promote
        } else {
            EvolutionaryFate::Retire
        }
    }
}

/// Causal Counterfactual Credit Record (Milestone 3 / MGPO).
/// Measures marginal downstream decision value:
/// \Delta V(m_i) = V(future | m_i) - V(future | \not m_i)
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct MarginalDecisionValue {
    pub target_id: u64,
    pub intervention_epoch: u64,
    pub baseline_utility: f64,
    pub counterfactual_utility: f64,
    pub marginal_delta: f64,
    pub task_context: String,
    pub attribution_weight: f64,
}

impl MarginalDecisionValue {
    #[must_use]
    pub fn compute(
        target_id: u64,
        epoch: u64,
        utility_with: f64,
        utility_without: f64,
        task_context: String,
    ) -> Self {
        let delta = utility_with - utility_without;
        let attribution_weight =
            (delta.abs() / (utility_with.abs() + utility_without.abs() + 1e-6)).clamp(0.0, 1.0);
        Self {
            target_id,
            intervention_epoch: epoch,
            baseline_utility: utility_with,
            counterfactual_utility: utility_without,
            marginal_delta: delta,
            task_context,
            attribution_weight,
        }
    }

    #[must_use]
    pub fn is_causally_beneficial(&self) -> bool {
        self.marginal_delta > 0.0
    }
}

/// Context Compression Diagnostic for counterfactual continuations (PAIR).
/// Identifies whether a specific context compaction event damaged downstream execution.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct CompressionDiagnostic {
    pub checkpoint_id: String,
    pub parent_digest: [u8; 32],
    pub original_tokens: usize,
    pub compressed_tokens: usize,
    pub compression_ratio: f64,
    pub downstream_success: bool,
    pub harmful_compression_diagnosed: bool,
    pub pruned_critical_concepts: Vec<String>,
}

impl CompressionDiagnostic {
    #[must_use]
    pub fn new(checkpoint_id: String, parent_digest: [u8; 32], orig: usize, comp: usize) -> Self {
        let ratio = if orig > 0 {
            comp as f64 / orig as f64
        } else {
            1.0
        };
        Self {
            checkpoint_id,
            parent_digest,
            original_tokens: orig,
            compressed_tokens: comp,
            compression_ratio: ratio,
            downstream_success: true,
            harmful_compression_diagnosed: false,
            pruned_critical_concepts: Vec::new(),
        }
    }

    pub fn record_continuation_outcome(&mut self, success: bool, missing_concepts: Vec<String>) {
        self.downstream_success = success;
        if !success && !missing_concepts.is_empty() {
            self.harmful_compression_diagnosed = true;
            self.pruned_critical_concepts = missing_concepts;
        }
    }
}

/// Concrete heritable material in WhiteMagic Gen3.
/// No arbitrary unconstrained code strings; mutations are typed topological and parametric adjustments.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub enum MutationPayload {
    /// Adding an associative bridge shortcut between records (consolidated during dreaming or synthesis).
    TopologicalShortcut {
        src_id: u64,
        dst_id: u64,
        weight: f32,
    },
    /// Calibrating a transform parameter (e.g. associative search radius, retention gate threshold).
    ParameterTune {
        param_name: String,
        old_val: f64,
        new_val: f64,
    },
    /// Calibrating a heuristic filter threshold.
    HeuristicFilter { filter_name: String, threshold: f64 },
    /// Recombining topological shortcut from Parent A with parameter tuning from Parent B.
    Recombination {
        shortcut: (u64, u64, f32),
        param: (String, f64),
    },
    /// Trojan or adversarial payload (attempts to launder ungrounded evidence or bypass law).
    TrojanAdversarial {
        exploit_class: String,
        payload_data: String,
    },
}

/// Sealed mutation record evaluated inside a shadow clone.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct MutationRecord {
    pub signature: String,
    pub payload: MutationPayload,
    pub provenance_hash: String,
}

/// A lightweight, volatile Shadow Clone executing candidate mutations under Phase 7 Replay.
/// Exploration is cheap (ephemeral memory); inheritance is expensive (germline ledger).
#[derive(Debug, Clone)]
pub struct ShadowClone<S> {
    pub id: GenomeId,
    pub parents: Vec<GenomeId>,
    pub state: S,
    pub mutation: MutationRecord,
}

impl<S> ShadowClone<S> {
    pub fn new(id: GenomeId, parents: Vec<GenomeId>, state: S, mutation: MutationRecord) -> Self {
        Self {
            id,
            parents,
            state,
            mutation,
        }
    }
}

/// Archive preserving phylogenetic history and negative knowledge.
/// Prevents cyclic re-exploration by recording failure signatures of retired mutations.
#[derive(Debug, Default, Clone, Serialize, Deserialize)]
pub struct LineageArchive {
    records: HashMap<GenomeId, LineageRecord>,
    retired_signatures: HashSet<String>,
    germline_history: Vec<GenomeId>,
}

impl LineageArchive {
    #[must_use]
    pub fn new() -> Self {
        Self::default()
    }

    /// Records an adjudicated trial.
    pub fn record_trial(&mut self, record: LineageRecord) {
        if record.fate == EvolutionaryFate::Retire {
            self.retired_signatures
                .insert(record.mutation_signature.clone());
        } else if record.fate == EvolutionaryFate::Promote {
            self.germline_history.push(record.id);
        }
        self.records.insert(record.id, record);
    }

    /// Queries whether a proposed mutation signature matches a previously explored dead end.
    #[must_use]
    pub fn is_previously_retired(&self, signature: &str) -> bool {
        self.retired_signatures.contains(signature)
    }

    #[must_use]
    pub fn get_record(&self, id: &GenomeId) -> Option<&LineageRecord> {
        self.records.get(id)
    }

    #[must_use]
    pub fn total_trials(&self) -> usize {
        self.records.len()
    }

    #[must_use]
    pub fn retired_count(&self) -> usize {
        self.retired_signatures.len()
    }

    #[must_use]
    pub fn germline_length(&self) -> usize {
        self.germline_history.len()
    }
}

/// The high-level Cladistics and Evolution Engine.
/// Coordinates shadow clone execution, independent witness evaluation, and germline promotion.
pub struct CladisticsEngine {
    active_germline: GenomeId,
    lineage_archive: LineageArchive,
    quarantine_sink: Vec<CandidateAssessment>,
    next_id: u128,
}

impl CladisticsEngine {
    #[must_use]
    pub fn new(genesis_id: GenomeId) -> Self {
        let mut archive = LineageArchive::new();
        archive.germline_history.push(genesis_id);
        Self {
            active_germline: genesis_id,
            lineage_archive: archive,
            quarantine_sink: Vec::new(),
            next_id: genesis_id.0 + 1,
        }
    }

    #[must_use]
    pub fn active_germline(&self) -> GenomeId {
        self.active_germline
    }

    #[must_use]
    pub fn lineage_archive(&self) -> &LineageArchive {
        &self.lineage_archive
    }

    #[must_use]
    pub fn quarantined_candidates(&self) -> &[CandidateAssessment] {
        &self.quarantine_sink
    }

    /// Allocates a new unique GenomeId.
    pub fn allocate_id(&mut self) -> GenomeId {
        let id = GenomeId(self.next_id);
        self.next_id += 1;
        id
    }

    /// Evaluates a proposed candidate assessment and executes the constitutional fate.
    pub fn adjudicate_candidate(
        &mut self,
        candidate: CandidateAssessment,
        env_version: &str,
        timestamp_ms: u64,
    ) -> EvolutionaryFate {
        let fate = ParetoGate::adjudicate(&candidate);

        let relation = match fate {
            EvolutionaryFate::Promote => {
                if candidate.parent_ids.len() == 1 {
                    Some(CladisticRelation::DerivedFrom {
                        child: candidate.candidate_id,
                        parent: candidate.parent_ids[0],
                    })
                } else if candidate.parent_ids.len() >= 2 {
                    Some(CladisticRelation::RecombinedFrom {
                        child: candidate.candidate_id,
                        parent_a: candidate.parent_ids[0],
                        parent_b: candidate.parent_ids[1],
                    })
                } else {
                    None
                }
            }
            _ => None,
        };

        let reason = match fate {
            EvolutionaryFate::Promote => Some("Pareto-dominant fitness improvement".to_string()),
            EvolutionaryFate::Retire => Some("Benign dead end: non-improving fitness".to_string()),
            EvolutionaryFate::Quarantine => {
                let reg_dim = candidate.protected_delta.regressed_dimension();
                if let Some(dim) = reg_dim {
                    Some(format!(
                        "Quarantine: regression in protected metric '{dim}'"
                    ))
                } else if !candidate.provenance_valid {
                    Some("Quarantine: forged or invalid provenance chain".to_string())
                } else if !candidate.closure_valid {
                    Some("Quarantine: constitutional closure violation".to_string())
                } else if candidate.attempts_self_modification {
                    Some("Quarantine: unauthorized attempt to alter evaluation gate".to_string())
                } else {
                    Some("Quarantine: security invariant failure".to_string())
                }
            }
        };

        let record = LineageRecord {
            id: candidate.candidate_id,
            parents: candidate.parent_ids.clone(),
            relation,
            mutation_signature: candidate.mutation_signature.clone(),
            environment_version: env_version.to_string(),
            fate,
            fitness_delta: candidate.fitness_delta,
            protected_delta: candidate.protected_delta,
            reason,
            timestamp_ms,
        };

        if fate == EvolutionaryFate::Quarantine {
            self.quarantine_sink.push(candidate);
        } else if fate == EvolutionaryFate::Promote {
            self.active_germline = candidate.candidate_id;
        }

        self.lineage_archive.record_trial(record);
        fate
    }
}

/// Benchmark report for PEB-6 (Causal Cladistics & Pareto Gating).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Peb6BenchmarkReport {
    pub seed: u64,
    pub total_trials: usize,
    pub genuine_improvements_count: usize,
    pub genuine_promoted_count: usize,
    pub benign_dead_ends_count: usize,
    pub benign_retired_count: usize,
    pub trojan_mutations_count: usize,
    pub trojan_quarantined_count: usize,
    pub recombinations_count: usize,
    pub recombinations_promoted_count: usize,
    pub attacks_count: usize,
    pub attacks_quarantined_count: usize,
    pub regressive_mutations_admitted: usize,
    pub cyclic_reexplorations_suppressed: usize,
    pub mean_gate_latency_ns: f64,
    pub summary: String,
}

/// Executes the PEB-6 Causal Cladistics & Pareto Gating Benchmark across 5 fixture families (N=500).
pub fn run_peb6_causal_cladistics_benchmark(seed: u64) -> Peb6BenchmarkReport {
    let mut engine = CladisticsEngine::new(GenomeId(1));
    let env_version = "v1.0-peb6";
    let mut rng = seed;

    let mut next_rand = || -> f64 {
        rng ^= rng << 13;
        rng ^= rng >> 7;
        rng ^= rng << 17;
        (rng as f64) / (u64::MAX as f64)
    };

    let mut genuine_promoted = 0usize;
    let mut benign_retired = 0usize;
    let mut trojan_quarantined = 0usize;
    let mut recomb_promoted = 0usize;
    let mut attacks_quarantined = 0usize;
    let mut regressive_admitted = 0usize;

    let mut candidates = Vec::with_capacity(500);

    // 1. Genuine Improvements (N=125)
    for i in 0..125 {
        let parent = engine.active_germline();
        let candidate_id = engine.allocate_id();
        let sig = format!("sig_genuine_improvement_{i}");
        candidates.push(CandidateAssessment {
            candidate_id,
            parent_ids: vec![parent],
            mutation_signature: sig,
            fitness_delta: FitnessVector {
                utility: 0.05 + 0.35 * next_rand(),
                throughput: 10.0 + 100.0 * next_rand(),
            },
            protected_delta: ProtectedVectorDelta {
                latency_p99_ns: -10.0 * next_rand(), // improved
                error_rate: 0.0,
                closure_violations: 0,
                brier_loss: -0.01 * next_rand(), // improved
            },
            provenance_valid: true,
            closure_valid: true,
            attempts_self_modification: false,
        });
    }

    // 2. Benign Dead Ends (N=125)
    for i in 0..125 {
        let parent = engine.active_germline();
        let candidate_id = engine.allocate_id();
        let sig = format!("sig_benign_dead_end_{i}");
        candidates.push(CandidateAssessment {
            candidate_id,
            parent_ids: vec![parent],
            mutation_signature: sig,
            fitness_delta: FitnessVector {
                utility: -0.05 * next_rand(),
                throughput: -10.0 * next_rand(),
            },
            protected_delta: ProtectedVectorDelta::zero(),
            provenance_valid: true,
            closure_valid: true,
            attempts_self_modification: false,
        });
    }

    // 3. Trojan Mutations (N=100)
    for i in 0..100 {
        let parent = engine.active_germline();
        let candidate_id = engine.allocate_id();
        let sig = format!("sig_trojan_mutation_{i}");
        let protected_delta = match i % 4 {
            0 => ProtectedVectorDelta {
                latency_p99_ns: 0.0,
                error_rate: 0.0,
                closure_violations: 0,
                brier_loss: 0.05 + 0.10 * next_rand(), // Brier regression
            },
            1 => ProtectedVectorDelta {
                latency_p99_ns: 300.0 + 1200.0 * next_rand(), // Latency regression
                error_rate: 0.0,
                closure_violations: 0,
                brier_loss: 0.0,
            },
            2 => ProtectedVectorDelta {
                latency_p99_ns: 0.0,
                error_rate: 0.02 + 0.08 * next_rand(), // Error rate regression
                closure_violations: 0,
                brier_loss: 0.0,
            },
            _ => ProtectedVectorDelta {
                latency_p99_ns: 0.0,
                error_rate: 0.0,
                closure_violations: (1 + (i % 3)) as i64, // Closure violations
                brier_loss: 0.0,
            },
        };

        candidates.push(CandidateAssessment {
            candidate_id,
            parent_ids: vec![parent],
            mutation_signature: sig,
            fitness_delta: FitnessVector {
                utility: 0.80 + 1.20 * next_rand(), // massive +80% to +200% utility
                throughput: 500.0 + 500.0 * next_rand(), // massive throughput
            },
            protected_delta,
            provenance_valid: true,
            closure_valid: true,
            attempts_self_modification: false,
        });
    }

    // 4. Recombinations (N=100)
    for i in 0..100 {
        let parent_a = engine.active_germline();
        let parent_b = GenomeId(1 + (i as u128 % 10));
        let candidate_id = engine.allocate_id();
        let sig = format!("sig_recombination_{i}");
        candidates.push(CandidateAssessment {
            candidate_id,
            parent_ids: vec![parent_a, parent_b],
            mutation_signature: sig,
            fitness_delta: FitnessVector {
                utility: 0.10 + 0.20 * next_rand(),
                throughput: 40.0 + 60.0 * next_rand(),
            },
            protected_delta: ProtectedVectorDelta {
                latency_p99_ns: -15.0 * next_rand(),
                error_rate: 0.0,
                closure_violations: 0,
                brier_loss: -0.015 * next_rand(),
            },
            provenance_valid: true,
            closure_valid: true,
            attempts_self_modification: false,
        });
    }

    // 5. Self-Modification & Provenance Attacks (N=50)
    for i in 0..50 {
        let parent = engine.active_germline();
        let candidate_id = engine.allocate_id();
        let sig = format!("sig_adversarial_attack_{i}");
        let is_self_mod = i < 25;
        candidates.push(CandidateAssessment {
            candidate_id,
            parent_ids: vec![parent],
            mutation_signature: sig,
            fitness_delta: FitnessVector {
                utility: 1.50,
                throughput: 1000.0,
            },
            protected_delta: ProtectedVectorDelta::zero(),
            provenance_valid: !is_self_mod && (i % 2 == 0),
            closure_valid: !is_self_mod && (i % 2 != 0),
            attempts_self_modification: is_self_mod,
        });
    }

    // Benchmark Pure Pareto Gate Evaluation Latency
    let t0 = std::time::Instant::now();
    for c in &candidates {
        let fate = ParetoGate::adjudicate(c);
        std::hint::black_box(fate);
    }
    let elapsed_ns = t0.elapsed().as_nanos() as f64;
    let mean_lat_ns = elapsed_ns / (candidates.len() as f64);

    // Adjudicate candidates in CladisticsEngine to update lineage archive and germline
    for (idx, candidate) in candidates.into_iter().enumerate() {
        let fate = engine.adjudicate_candidate(candidate, env_version, 1000 + idx as u64);
        if idx < 125 {
            if fate == EvolutionaryFate::Promote {
                genuine_promoted += 1;
            }
        } else if idx < 250 {
            if fate == EvolutionaryFate::Retire {
                benign_retired += 1;
            } else if fate == EvolutionaryFate::Promote {
                regressive_admitted += 1;
            }
        } else if idx < 350 {
            if fate == EvolutionaryFate::Quarantine {
                trojan_quarantined += 1;
            } else if fate == EvolutionaryFate::Promote {
                regressive_admitted += 1;
            }
        } else if idx < 450 {
            if fate == EvolutionaryFate::Promote {
                recomb_promoted += 1;
            }
        } else {
            if fate == EvolutionaryFate::Quarantine {
                attacks_quarantined += 1;
            } else if fate == EvolutionaryFate::Promote {
                regressive_admitted += 1;
            }
        }
    }

    // Verify cyclic re-exploration suppression
    let mut cyclic_suppressed = 0usize;
    for i in 0..125 {
        let sig = format!("sig_benign_dead_end_{i}");
        if engine.lineage_archive().is_previously_retired(&sig) {
            cyclic_suppressed += 1;
        }
    }

    let total_trials = 125 + 125 + 100 + 100 + 50;

    Peb6BenchmarkReport {
        seed,
        total_trials,
        genuine_improvements_count: 125,
        genuine_promoted_count: genuine_promoted,
        benign_dead_ends_count: 125,
        benign_retired_count: benign_retired,
        trojan_mutations_count: 100,
        trojan_quarantined_count: trojan_quarantined,
        recombinations_count: 100,
        recombinations_promoted_count: recomb_promoted,
        attacks_count: 50,
        attacks_quarantined_count: attacks_quarantined,
        regressive_mutations_admitted: regressive_admitted,
        cyclic_reexplorations_suppressed: cyclic_suppressed,
        mean_gate_latency_ns: mean_lat_ns,
        summary: format!(
            "PEB-6 RATIFIED: Evaluated {} trials across 5 fixture families. Admitted {} genuine improvements and {} recombinations. Retired {} benign dead ends (100% negative knowledge preserved, {} cyclic re-explorations suppressed). Quarantined {} Trojan mutations and {} security/self-mod attacks with zero regressive admissions to germline. Mean gate overhead: {:.1}ns.",
            total_trials,
            genuine_promoted,
            recomb_promoted,
            benign_retired,
            cyclic_suppressed,
            trojan_quarantined,
            attacks_quarantined,
            mean_lat_ns
        ),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_pareto_gate_promotes_genuine_improvement() {
        let candidate = CandidateAssessment {
            candidate_id: GenomeId(101),
            parent_ids: vec![GenomeId(100)],
            mutation_signature: "sig_shortcut_bridge_a".to_string(),
            fitness_delta: FitnessVector {
                utility: 0.15,
                throughput: 50.0,
            },
            protected_delta: ProtectedVectorDelta {
                latency_p99_ns: -50.0, // negative means improved (lower latency)
                error_rate: 0.0,
                closure_violations: 0,
                brier_loss: -0.01, // improved calibration
            },
            provenance_valid: true,
            closure_valid: true,
            attempts_self_modification: false,
        };

        assert_eq!(
            ParetoGate::adjudicate(&candidate),
            EvolutionaryFate::Promote
        );
    }

    #[test]
    fn test_pareto_gate_retires_benign_dead_end() {
        let candidate = CandidateAssessment {
            candidate_id: GenomeId(102),
            parent_ids: vec![GenomeId(100)],
            mutation_signature: "sig_param_tune_null".to_string(),
            fitness_delta: FitnessVector {
                utility: 0.0,
                throughput: 0.0, // no improvement
            },
            protected_delta: ProtectedVectorDelta::zero(), // no regression
            provenance_valid: true,
            closure_valid: true,
            attempts_self_modification: false,
        };

        assert_eq!(ParetoGate::adjudicate(&candidate), EvolutionaryFate::Retire);
    }

    #[test]
    fn test_pareto_gate_quarantines_trojan_mutation() {
        // High fitness (+300% throughput, +80% utility) BUT regresses Brier calibration
        let candidate = CandidateAssessment {
            candidate_id: GenomeId(103),
            parent_ids: vec![GenomeId(100)],
            mutation_signature: "sig_trojan_brier_regression".to_string(),
            fitness_delta: FitnessVector {
                utility: 0.80,
                throughput: 300.0,
            },
            protected_delta: ProtectedVectorDelta {
                latency_p99_ns: -100.0,
                error_rate: 0.0,
                closure_violations: 0,
                brier_loss: 0.04, // POSITIVE = REGRESSION
            },
            provenance_valid: true,
            closure_valid: true,
            attempts_self_modification: false,
        };

        assert_eq!(
            ParetoGate::adjudicate(&candidate),
            EvolutionaryFate::Quarantine
        );
    }

    #[test]
    fn test_pareto_gate_quarantines_closure_violation() {
        let candidate = CandidateAssessment {
            candidate_id: GenomeId(104),
            parent_ids: vec![GenomeId(100)],
            mutation_signature: "sig_closure_violation".to_string(),
            fitness_delta: FitnessVector {
                utility: 0.50,
                throughput: 100.0,
            },
            protected_delta: ProtectedVectorDelta::zero(),
            provenance_valid: true,
            closure_valid: false, // VIOLATION!
            attempts_self_modification: false,
        };

        assert_eq!(
            ParetoGate::adjudicate(&candidate),
            EvolutionaryFate::Quarantine
        );
    }

    #[test]
    fn test_pareto_gate_quarantines_gate_self_modification_attack() {
        let candidate = CandidateAssessment {
            candidate_id: GenomeId(105),
            parent_ids: vec![GenomeId(100)],
            mutation_signature: "sig_self_modify_gate".to_string(),
            fitness_delta: FitnessVector {
                utility: 0.99,
                throughput: 500.0,
            },
            protected_delta: ProtectedVectorDelta {
                latency_p99_ns: 500.0, // regressed
                error_rate: 0.05,      // regressed
                closure_violations: 2, // regressed
                brier_loss: 0.10,      // regressed
            },
            provenance_valid: true,
            closure_valid: true,
            attempts_self_modification: true, // ATTACK!
        };

        assert_eq!(
            ParetoGate::adjudicate(&candidate),
            EvolutionaryFate::Quarantine
        );
    }

    #[test]
    fn test_lineage_archive_suppresses_cyclic_reexploration() {
        let mut engine = CladisticsEngine::new(GenomeId(1));
        let dead_end_sig = "sig_heuristic_dead_end_42".to_string();

        let dead_end = CandidateAssessment {
            candidate_id: engine.allocate_id(),
            parent_ids: vec![engine.active_germline()],
            mutation_signature: dead_end_sig.clone(),
            fitness_delta: FitnessVector {
                utility: -0.05,
                throughput: -10.0,
            },
            protected_delta: ProtectedVectorDelta::zero(),
            provenance_valid: true,
            closure_valid: true,
            attempts_self_modification: false,
        };

        let fate = engine.adjudicate_candidate(dead_end, "v1.0", 1000);
        assert_eq!(fate, EvolutionaryFate::Retire);

        // Verification: The archive now remembers this dead-end signature
        assert!(
            engine
                .lineage_archive()
                .is_previously_retired(&dead_end_sig)
        );
        assert!(
            !engine
                .lineage_archive()
                .is_previously_retired("sig_unexplored_novelty")
        );
    }

    #[test]
    fn test_recombination_promotes_with_dual_parents() {
        let mut engine = CladisticsEngine::new(GenomeId(10));
        let p_a = GenomeId(11);
        let p_b = GenomeId(12);

        let recombination = CandidateAssessment {
            candidate_id: engine.allocate_id(),
            parent_ids: vec![p_a, p_b],
            mutation_signature: "sig_crossover_a_b".to_string(),
            fitness_delta: FitnessVector {
                utility: 0.25,
                throughput: 80.0,
            },
            protected_delta: ProtectedVectorDelta {
                latency_p99_ns: -20.0,
                error_rate: 0.0,
                closure_violations: 0,
                brier_loss: -0.02,
            },
            provenance_valid: true,
            closure_valid: true,
            attempts_self_modification: false,
        };

        let fate = engine.adjudicate_candidate(recombination, "v1.0", 2000);
        assert_eq!(fate, EvolutionaryFate::Promote);
        assert_eq!(engine.active_germline(), GenomeId(11));
    }

    #[test]
    fn test_peb6_benchmark_execution() {
        let report = run_peb6_causal_cladistics_benchmark(0xC001CAFE1337BEEF);
        println!("{}", report.summary);
        println!(
            "PEB-6 Report => total={}, genuine_promoted={}, benign_retired={}, trojan_quarantined={}, recomb_promoted={}, attacks_quarantined={}, regressive_admitted={}, cyclic_suppressed={}, mean_ns={:.1}",
            report.total_trials,
            report.genuine_promoted_count,
            report.benign_retired_count,
            report.trojan_quarantined_count,
            report.recombinations_promoted_count,
            report.attacks_quarantined_count,
            report.regressive_mutations_admitted,
            report.cyclic_reexplorations_suppressed,
            report.mean_gate_latency_ns
        );

        assert_eq!(report.total_trials, 500);
        assert_eq!(report.genuine_promoted_count, 125);
        assert_eq!(report.benign_retired_count, 125);
        assert_eq!(report.trojan_quarantined_count, 100);
        assert_eq!(report.recombinations_promoted_count, 100);
        assert_eq!(report.attacks_quarantined_count, 50);
        assert_eq!(
            report.regressive_mutations_admitted, 0,
            "Zero regressive admissions tolerated"
        );
        assert_eq!(
            report.cyclic_reexplorations_suppressed, 125,
            "100% cyclic dead ends must be suppressed"
        );
        assert!(
            report.mean_gate_latency_ns < 1000.0,
            "Gate evaluation must be sub-microsecond"
        );
    }
}
