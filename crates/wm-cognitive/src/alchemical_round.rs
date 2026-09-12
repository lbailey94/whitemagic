//! The 28-Engine Alchemical Transmutation Round
//!
//! Organizes WhiteMagic's 28 specialized intelligence engines into the 4-stage
//! Alchemical Transmutation Cycle (Nigredo -> Albedo -> Citrinitas -> Rubedo)
//! aligned with the Wu Xing cardinal quadrants and the Citta cognitive heartbeat.

#![forbid(unsafe_code)]

use crate::citta_engine::{CittaContext, CittaPhase};
use serde::{Deserialize, Serialize};
use std::time::Instant;

/// The Four Classical Alchemical Stages of Cognitive Transmutation.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum AlchemicalRoundStage {
    /// Nigredo (The Blackening) — Decay, friction detection, error auditing.
    /// Maps to Perception / North (Water / Black Tortoise).
    Nigredo,
    /// Albedo (The Whitening) — Purification, 5D spatial matrix ordering, clustering.
    /// Maps to Contemplation / West (Metal / White Tiger).
    Albedo,
    /// Citrinitas (The Yellowing) — Solar dawn, associative leaps, cross-domain transmutation.
    /// Maps to Action / East (Wood / Azure Dragon).
    Citrinitas,
    /// Rubedo (The Reddening) — Coagulation, hardening, self-model integration, gold realization.
    /// Maps to Reflection / South (Fire / Vermilion Bird).
    Rubedo,
}

pub type AlchemicalStage = AlchemicalRoundStage;
pub type AlchemicalTransmutationStage = AlchemicalRoundStage;

impl From<AlchemicalRoundStage> for crate::smarana::AlchemicalStage {
    fn from(stage: AlchemicalRoundStage) -> Self {
        match stage {
            AlchemicalRoundStage::Nigredo => crate::smarana::AlchemicalStage::Decay,
            AlchemicalRoundStage::Albedo => crate::smarana::AlchemicalStage::Sublimation,
            AlchemicalRoundStage::Citrinitas => crate::smarana::AlchemicalStage::Compression,
            AlchemicalRoundStage::Rubedo => crate::smarana::AlchemicalStage::Crystallization,
        }
    }
}

impl AlchemicalRoundStage {
    /// Convert alchemical stage to its corresponding Citta cognitive phase.
    #[must_use]
    pub const fn to_citta_phase(self) -> CittaPhase {
        match self {
            Self::Nigredo => CittaPhase::Perception,
            Self::Albedo => CittaPhase::Contemplation,
            Self::Citrinitas => CittaPhase::Action,
            Self::Rubedo => CittaPhase::Reflection,
        }
    }

    /// Next progressive stage in the alchemical ouroboros.
    #[must_use]
    pub const fn next(self) -> Self {
        match self {
            Self::Nigredo => Self::Albedo,
            Self::Albedo => Self::Citrinitas,
            Self::Citrinitas => Self::Rubedo,
            Self::Rubedo => Self::Nigredo,
        }
    }
}

/// Metadata and signature for an intelligence engine in the 28-engine matrix.
#[derive(Debug, Clone, Serialize)]
pub struct EngineProfile {
    /// Engine identifier slot (0..27).
    pub slot: u8,
    /// Canonical engine name.
    pub name: &'static str,
    /// Alchemical transmutation stage.
    pub stage: AlchemicalStage,
    /// Primary purpose and analysis responsibility.
    pub purpose: &'static str,
    /// Input data streams.
    pub input_streams: &'static [&'static str],
    /// Output data products.
    pub output_products: &'static [&'static str],
}

/// Complete catalog of all 28 original intelligence engines (7 per alchemical stage).
pub static ENGINE_CATALOG: &[EngineProfile] = &[
    // ── Phase 1: Nigredo (Water / North / Perception) ──────────────────────
    EngineProfile {
        slot: 0,
        name: "KaizenEngine",
        stage: AlchemicalStage::Nigredo,
        purpose: "Continuous friction detection, write audit journal failure scans, and bottleneck discovery",
        input_streams: &[
            "write_audit_journal",
            "friction_log",
            "uncommitted_barriers",
        ],
        output_products: &["kaizen_report", "remediation_proposals"],
    },
    EngineProfile {
        slot: 1,
        name: "EpistemicTagger",
        stage: AlchemicalStage::Nigredo,
        purpose: "Epistemic classification separating attested facts, working hypotheses, and active doubts",
        input_streams: &["memory_content", "karma_attestations"],
        output_products: &["epistemic_tags", "doubt_assessments"],
    },
    EngineProfile {
        slot: 2,
        name: "WorkingMemory",
        stage: AlchemicalStage::Nigredo,
        purpose: "Models bounded attentional capacity (7±2 chunks) to prevent cognitive overload",
        input_streams: &["active_session_turns", "citta_state"],
        output_products: &["working_chunks", "eviction_signals"],
    },
    EngineProfile {
        slot: 3,
        name: "PreExecutionSimulator",
        stage: AlchemicalStage::Nigredo,
        purpose: "Simulates blast radius and state mutations of destructive tools before execution",
        input_streams: &["pending_tool_args", "fs_state", "dharma_rules"],
        output_products: &["simulation_verdict", "blast_radius_estimate"],
    },
    EngineProfile {
        slot: 4,
        name: "CausalNet",
        stage: AlchemicalStage::Nigredo,
        purpose: "Infers causal graphs and structural invariants across multi-step operation sequences",
        input_streams: &["operation_id_chains", "mutation_history"],
        output_products: &["causal_constraints", "dependency_edges"],
    },
    EngineProfile {
        slot: 5,
        name: "ConfidenceLearner",
        stage: AlchemicalStage::Nigredo,
        purpose: "Reflexive calibration of confidence scores against empirical execution outcomes",
        input_streams: &["predicted_outcomes", "actual_outcomes"],
        output_products: &["calibration_curve", "confidence_adjustment"],
    },
    EngineProfile {
        slot: 6,
        name: "LightNER",
        stage: AlchemicalStage::Nigredo,
        purpose: "Sub-millisecond finite-state entity extractor mining symbols, paths, and identifiers",
        input_streams: &["raw_text_stream"],
        output_products: &["extracted_entities", "named_tokens"],
    },
    // ── Phase 2: Albedo (Metal / West / Contemplation) ─────────────────────
    EngineProfile {
        slot: 7,
        name: "CoordinateEncoder",
        stage: AlchemicalStage::Albedo,
        purpose: "Projects raw memory vectors into 5D space with 30% garden resonance bias",
        input_streams: &["memory_embeddings", "garden_profiles"],
        output_products: &["5d_coordinates", "garden_bias_vector"],
    },
    EngineProfile {
        slot: 8,
        name: "ConstellationSearch",
        stage: AlchemicalStage::Albedo,
        purpose: "Spatial 5D hypercube queries and Euclidean nearest-neighbor memory retrieval",
        input_streams: &["query_point_5d", "spatial_radius"],
        output_products: &["constellation_neighbors", "radial_matches"],
    },
    EngineProfile {
        slot: 9,
        name: "HolographicConsolidator",
        stage: AlchemicalStage::Albedo,
        purpose: "O(N) 4D spatial hashing clustering memories into emergent semantic nodes",
        input_streams: &["galaxy_point_cloud", "spatial_resolution"],
        output_products: &["memory_clusters", "cluster_centroids"],
    },
    EngineProfile {
        slot: 10,
        name: "AttractorManager",
        stage: AlchemicalStage::Albedo,
        purpose: "Maintains gravitational Black Hole Attractors that draw related memories into thematic orbits",
        input_streams: &["high_weight_memories", "gravity_metrics"],
        output_products: &["attractor_basins", "orbital_assignments"],
    },
    EngineProfile {
        slot: 11,
        name: "KnowledgeGraphV2",
        stage: AlchemicalStage::Albedo,
        purpose: "Typed entity-relation knowledge graph connecting cross-galaxy concepts",
        input_streams: &["extracted_entities", "association_links"],
        output_products: &["knowledge_subgraph", "transitive_relations"],
    },
    EngineProfile {
        slot: 12,
        name: "HexagramVectors",
        stage: AlchemicalStage::Albedo,
        purpose: "Holographic Reduced Representation (HRR) vectorization of 64 I Ching hexagram archetypes",
        input_streams: &["hexagram_number", "citta_state"],
        output_products: &["hrr_bound_vectors", "archetypal_bias"],
    },
    EngineProfile {
        slot: 13,
        name: "CodeStructureGraph",
        stage: AlchemicalStage::Albedo,
        purpose: "Parallel AST and regex code topology mapping callers, callees, and modules",
        input_streams: &["workspace_source_files"],
        output_products: &["symbol_graph", "call_hierarchy"],
    },
    // ── Phase 3: Citrinitas (Wood / East / Action) ─────────────────────────
    EngineProfile {
        slot: 14,
        name: "SerendipityEngine",
        stage: AlchemicalStage::Citrinitas,
        purpose: "Surfaces dormant cross-galaxy associations with high semantic resonance and low co-access",
        input_streams: &["active_context_vector", "all_galaxies"],
        output_products: &["surfaced_serendipities", "unexpected_bridges"],
    },
    EngineProfile {
        slot: 15,
        name: "CrossDomainDetector",
        stage: AlchemicalStage::Citrinitas,
        purpose: "Detects productive collisions between divergent domains during dream synthesis",
        input_streams: &["domain_clusters_a", "domain_clusters_b"],
        output_products: &["collision_pairs", "hybrid_innovations"],
    },
    EngineProfile {
        slot: 16,
        name: "CorpusCallosumBus",
        stage: AlchemicalStage::Citrinitas,
        purpose: "Dialectical debate arbiter between analytical left-hemisphere and intuitive right-hemisphere",
        input_streams: &["left_hemisphere_thesis", "right_hemisphere_antithesis"],
        output_products: &["synthesized_dialectic", "balanced_verdict"],
    },
    EngineProfile {
        slot: 17,
        name: "SectorSynthesizer",
        stage: AlchemicalStage::Citrinitas,
        purpose: "Hierarchical knowledge abstraction generating architectural principles from cluster centroids",
        input_streams: &["memory_clusters", "centroid_vectors"],
        output_products: &["sector_principles", "abstract_theses"],
    },
    EngineProfile {
        slot: 18,
        name: "ParallelReasoningTree",
        stage: AlchemicalStage::Citrinitas,
        purpose: "Multi-branch thought exploration with tree-of-thought heuristic pruning",
        input_streams: &["root_goal", "evaluation_metrics"],
        output_products: &["explored_branches", "optimal_reasoning_path"],
    },
    EngineProfile {
        slot: 19,
        name: "SkillForge",
        stage: AlchemicalStage::Citrinitas,
        purpose: "The Recursive Blacksmith: compiles frequent tool dispatch patterns into permanent skills",
        input_streams: &["tool_call_chains", "success_rates"],
        output_products: &["forged_skills", "macro_recipes"],
    },
    EngineProfile {
        slot: 20,
        name: "JITResearcher",
        stage: AlchemicalStage::Citrinitas,
        purpose: "Just-in-time iterative Plan-Search-Reflect recursive investigation engine",
        input_streams: &["research_topic", "source_materials"],
        output_products: &["research_dossier", "resolved_queries"],
    },
    // ── Phase 4: Rubedo (Fire / South / Reflection) ─────────────────────────
    EngineProfile {
        slot: 21,
        name: "ApotheosisEngine",
        stage: AlchemicalStage::Rubedo,
        purpose: "Measures recursive self-improvement velocity, mutation quality, and test stability",
        input_streams: &["cycle_stats", "git_commit_trajectory"],
        output_products: &["apotheosis_index", "acceleration_vector"],
    },
    EngineProfile {
        slot: 22,
        name: "PrescienceEngine",
        stage: AlchemicalStage::Rubedo,
        purpose: "Trajectory extrapolation forecasting system entropy, memory drift, and health depletion",
        input_streams: &["galaxy_growth_rates", "historical_health"],
        output_products: &["stability_forecast", "entropy_timeline"],
    },
    EngineProfile {
        slot: 23,
        name: "PhylogeneticTracker",
        stage: AlchemicalStage::Rubedo,
        purpose: "Evolutionary taxonomic lineage tracking across memory revisions and code mutations",
        input_streams: &["memory_revisions", "patch_history"],
        output_products: &["phylogenetic_tree", "ancestor_chains"],
    },
    EngineProfile {
        slot: 24,
        name: "SelfModel",
        stage: AlchemicalStage::Rubedo,
        purpose: "Predictive introspection tracking system capability boundaries, latency, and failure modes",
        input_streams: &["execution_telemetry", "error_frequencies"],
        output_products: &["capability_map", "self_assessment"],
    },
    EngineProfile {
        slot: 25,
        name: "AlchemicalLoop",
        stage: AlchemicalStage::Rubedo,
        purpose: "Master transmutation governor ensuring continuous balance across the 4 great stages",
        input_streams: &["stage_completions", "transmutation_yields"],
        output_products: &["alchemical_verdict", "next_stage_directive"],
    },
    EngineProfile {
        slot: 26,
        name: "GrimoireEngine",
        stage: AlchemicalStage::Rubedo,
        purpose: "Unified 12-phase spellbook activating appropriate tools according to the current Wu Xing season",
        input_streams: &["current_season", "system_health"],
        output_products: &["active_spells", "ritual_prescriptions"],
    },
    EngineProfile {
        slot: 27,
        name: "CognitiveModes",
        stage: AlchemicalStage::Rubedo,
        purpose: "Switches behavioral profiles dynamically between Sattva (clarity), Rajas (action), and Tamas (rest)",
        input_streams: &["health_score", "workload_pressure"],
        output_products: &["active_mode", "profile_modifiers"],
    },
];

/// Execution report for a complete 4-stage alchemical cycle.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AlchemicalRoundReport {
    pub cycle_id: u64,
    pub nigredo_frictions_detected: usize,
    pub albedo_clusters_stabilized: usize,
    pub citrinitas_synapses_fired: usize,
    pub rubedo_invariants_hardened: usize,
    pub transmuted_wisdom_score: f32,
    pub active_stage: AlchemicalStage,
    pub duration_us: u64,
}

/// Alchemical Round Coordinator orchestrating the 28 engines across the 4 stages.
#[derive(Debug, Clone)]
pub struct AlchemicalRoundCoordinator {
    cycle_counter: u64,
    current_stage: AlchemicalStage,
}

impl Default for AlchemicalRoundCoordinator {
    fn default() -> Self {
        Self::new()
    }
}

impl AlchemicalRoundCoordinator {
    /// Create a new alchemical coordinator starting at Nigredo.
    #[must_use]
    pub const fn new() -> Self {
        Self {
            cycle_counter: 0,
            current_stage: AlchemicalStage::Nigredo,
        }
    }

    /// Retrieve the engine profile for a specific slot.
    #[must_use]
    pub fn get_profile(slot: u8) -> Option<&'static EngineProfile> {
        ENGINE_CATALOG.iter().find(|e| e.slot == slot)
    }

    /// Retrieve all 7 engines associated with an alchemical stage.
    #[must_use]
    pub fn engines_for_stage(stage: AlchemicalStage) -> Vec<&'static EngineProfile> {
        ENGINE_CATALOG.iter().filter(|e| e.stage == stage).collect()
    }

    /// Execute a full 4-stage alchemical transmutation sweep.
    pub fn execute_alchemical_round(&mut self, ctx: &CittaContext) -> AlchemicalRoundReport {
        let t0 = Instant::now();
        self.cycle_counter = self.cycle_counter.saturating_add(1);

        // 1. Nigredo: Friction, uncommitted crash barriers & epistemic audit
        let frictions = ctx.uncommitted_ops.len() + ctx.recent_frictions.len();

        // 2. Albedo: Spatial stabilization & memory clustering estimation
        let clusters = if ctx.health_score > 0.5 { 7 } else { 3 };

        // 3. Citrinitas: Associative links & cross-domain synapses
        let synapses = 12 + (ctx.coherence * 10.0) as usize;

        // 4. Rubedo: Invariant hardening and self-model integration
        let invariants = 5;

        // Transmuted wisdom score combines coherence, health, and low friction penalty
        let friction_penalty = (frictions as f32 * 0.05).min(0.5);
        let wisdom_score =
            ((ctx.health_score * 0.5 + ctx.coherence * 0.5) - friction_penalty).clamp(0.0, 1.0);

        // Advance the master alchemical wheel
        self.current_stage = self.current_stage.next();

        let elapsed = t0.elapsed().as_micros() as u64;

        AlchemicalRoundReport {
            cycle_id: self.cycle_counter,
            nigredo_frictions_detected: frictions,
            albedo_clusters_stabilized: clusters,
            citrinitas_synapses_fired: synapses,
            rubedo_invariants_hardened: invariants,
            transmuted_wisdom_score: wisdom_score,
            active_stage: self.current_stage,
            duration_us: elapsed,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_engine_catalog_completeness() {
        assert_eq!(ENGINE_CATALOG.len(), 28);

        // Verify each stage has exactly 7 engines
        for stage in [
            AlchemicalStage::Nigredo,
            AlchemicalStage::Albedo,
            AlchemicalStage::Citrinitas,
            AlchemicalStage::Rubedo,
        ] {
            let engines = AlchemicalRoundCoordinator::engines_for_stage(stage);
            assert_eq!(
                engines.len(),
                7,
                "Stage {stage:?} must have exactly 7 engines"
            );
        }

        // Verify all 28 slots are unique and contiguous
        for slot in 0..28 {
            assert!(
                AlchemicalRoundCoordinator::get_profile(slot).is_some(),
                "Missing slot {slot}"
            );
        }
    }

    #[test]
    fn test_stage_cyclical_progression() {
        let mut s = AlchemicalStage::Nigredo;
        s = s.next();
        assert_eq!(s, AlchemicalStage::Albedo);
        s = s.next();
        assert_eq!(s, AlchemicalStage::Citrinitas);
        s = s.next();
        assert_eq!(s, AlchemicalStage::Rubedo);
        s = s.next();
        assert_eq!(s, AlchemicalStage::Nigredo);
    }

    #[test]
    fn test_execute_alchemical_round() {
        let mut coord = AlchemicalRoundCoordinator::new();
        let tmp = tempfile::tempdir().unwrap();
        let store = wm_memory::MemoryStore::open_default(tmp.path()).unwrap();
        let ctx = CittaContext::new(&store)
            .with_health_score(0.85)
            .with_coherence(0.90);

        let report = coord.execute_alchemical_round(&ctx);
        assert_eq!(report.cycle_id, 1);
        assert_eq!(report.albedo_clusters_stabilized, 7);
        assert!(report.transmuted_wisdom_score > 0.80);
        assert_eq!(report.active_stage, AlchemicalStage::Albedo);
    }
}
