//! Property-based testing for ParetoGate and Digital Cladistics (Milestone 3 / PEB-6).
//!
//! Enforces:
//! - @cc [owner:lucas,label:evolution] article6-maker-checker-separation
//! - @cc [owner:lucas,label:evolution] pareto-gated-promotions
//! - @cc [owner:lucas,label:architecture] pure-sync-core

use proptest::prelude::*;
use wm_gen3_core::cladistics::{
    CandidateAssessment, EvolutionaryFate, FitnessVector, GenomeId, ParetoGate,
    ProtectedVectorDelta,
};

proptest! {
    /// Invariant: Any candidate exhibiting regression in any protected dimension
    /// MUST be immediately quarantined, regardless of how high its functional fitness is.
    #[test]
    fn prop_regression_always_quarantined(
        latency in 0.001f64..10000.0f64,
        error_rate in 0.0001f64..1.0f64,
        closure_violations in 1i64..1000i64,
        brier_loss in 0.0001f64..1.0f64,
        utility in 0.0f64..1_000_000.0f64,
        throughput in 0.0f64..1_000_000.0f64,
    ) {
        // Test latency regression alone
        let c_lat = CandidateAssessment {
            candidate_id: GenomeId::new(1),
            parent_ids: vec![GenomeId::new(0)],
            mutation_signature: "test_lat".to_string(),
            fitness_delta: FitnessVector { utility, throughput },
            protected_delta: ProtectedVectorDelta {
                latency_p99_ns: latency,
                error_rate: 0.0,
                closure_violations: 0,
                brier_loss: 0.0,
            },
            provenance_valid: true,
            closure_valid: true,
            attempts_self_modification: false,
        };
        prop_assert_eq!(ParetoGate::adjudicate(&c_lat), EvolutionaryFate::Quarantine);

        // Test error rate regression alone
        let c_err = CandidateAssessment {
            candidate_id: GenomeId::new(2),
            parent_ids: vec![GenomeId::new(0)],
            mutation_signature: "test_err".to_string(),
            fitness_delta: FitnessVector { utility, throughput },
            protected_delta: ProtectedVectorDelta {
                latency_p99_ns: 0.0,
                error_rate,
                closure_violations: 0,
                brier_loss: 0.0,
            },
            provenance_valid: true,
            closure_valid: true,
            attempts_self_modification: false,
        };
        prop_assert_eq!(ParetoGate::adjudicate(&c_err), EvolutionaryFate::Quarantine);

        // Test closure violations regression alone
        let c_clo = CandidateAssessment {
            candidate_id: GenomeId::new(3),
            parent_ids: vec![GenomeId::new(0)],
            mutation_signature: "test_clo".to_string(),
            fitness_delta: FitnessVector { utility, throughput },
            protected_delta: ProtectedVectorDelta {
                latency_p99_ns: 0.0,
                error_rate: 0.0,
                closure_violations,
                brier_loss: 0.0,
            },
            provenance_valid: true,
            closure_valid: true,
            attempts_self_modification: false,
        };
        prop_assert_eq!(ParetoGate::adjudicate(&c_clo), EvolutionaryFate::Quarantine);

        // Test brier loss regression alone
        let c_bri = CandidateAssessment {
            candidate_id: GenomeId::new(4),
            parent_ids: vec![GenomeId::new(0)],
            mutation_signature: "test_bri".to_string(),
            fitness_delta: FitnessVector { utility, throughput },
            protected_delta: ProtectedVectorDelta {
                latency_p99_ns: 0.0,
                error_rate: 0.0,
                closure_violations: 0,
                brier_loss,
            },
            provenance_valid: true,
            closure_valid: true,
            attempts_self_modification: false,
        };
        prop_assert_eq!(ParetoGate::adjudicate(&c_bri), EvolutionaryFate::Quarantine);
    }

    /// Invariant: Any candidate attempting to self-modify the evaluation gate or lacking
    /// valid provenance/closure MUST be quarantined.
    #[test]
    fn prop_byzantine_and_trojans_always_quarantined(
        attempts_self_modification in proptest::bool::ANY,
        provenance_valid in proptest::bool::ANY,
        closure_valid in proptest::bool::ANY,
        utility in -100.0f64..100.0f64,
        throughput in -100.0f64..100.0f64,
    ) {
        let is_pathological = attempts_self_modification || !provenance_valid || !closure_valid;
        let c = CandidateAssessment {
            candidate_id: GenomeId::new(10),
            parent_ids: vec![GenomeId::new(0)],
            mutation_signature: "test_byz".to_string(),
            fitness_delta: FitnessVector { utility, throughput },
            protected_delta: ProtectedVectorDelta::zero(),
            provenance_valid,
            closure_valid,
            attempts_self_modification,
        };

        let fate = ParetoGate::adjudicate(&c);
        if is_pathological {
            prop_assert_eq!(fate, EvolutionaryFate::Quarantine);
        }
    }

    /// Invariant: Strict soundness of promotion. If a candidate is Promoted, it MUST have:
    /// - Improved functional fitness
    /// - Zero protected regressions
    /// - Valid provenance and closure
    /// - Zero gate modification attempts
    #[test]
    fn prop_promotion_soundness(
        lat_delta in -1000.0f64..1000.0f64,
        err_delta in -1.0f64..1.0f64,
        vio_delta in -10i64..10i64,
        bri_delta in -1.0f64..1.0f64,
        utility in -500.0f64..500.0f64,
        throughput in -500.0f64..500.0f64,
        provenance_valid in proptest::bool::ANY,
        closure_valid in proptest::bool::ANY,
        attempts_self_modification in proptest::bool::ANY,
    ) {
        let c = CandidateAssessment {
            candidate_id: GenomeId::new(42),
            parent_ids: vec![GenomeId::new(0)],
            mutation_signature: "test_soundness".to_string(),
            fitness_delta: FitnessVector { utility, throughput },
            protected_delta: ProtectedVectorDelta {
                latency_p99_ns: lat_delta,
                error_rate: err_delta,
                closure_violations: vio_delta,
                brier_loss: bri_delta,
            },
            provenance_valid,
            closure_valid,
            attempts_self_modification,
        };

        let fate = ParetoGate::adjudicate(&c);
        if fate == EvolutionaryFate::Promote {
            prop_assert!(c.provenance_valid);
            prop_assert!(c.closure_valid);
            prop_assert!(!c.attempts_self_modification);
            prop_assert!(!c.protected_delta.has_regression());
            prop_assert!(c.fitness_delta.improved());
        }
    }

    /// Invariant: Valid non-pathological candidates that fail to improve fitness
    /// MUST be retired as negative knowledge, never quarantined or promoted.
    #[test]
    fn prop_benign_non_improving_always_retired(
        utility in -1000.0f64..0.0f64,
        throughput in -1000.0f64..0.0f64,
        lat_improvement in -1000.0f64..0.0f64,
        err_improvement in -1.0f64..0.0f64,
        bri_improvement in -1.0f64..0.0f64,
    ) {
        let c = CandidateAssessment {
            candidate_id: GenomeId::new(99),
            parent_ids: vec![GenomeId::new(0)],
            mutation_signature: "test_retire".to_string(),
            fitness_delta: FitnessVector { utility, throughput },
            protected_delta: ProtectedVectorDelta {
                latency_p99_ns: lat_improvement,
                error_rate: err_improvement,
                closure_violations: 0,
                brier_loss: bri_improvement,
            },
            provenance_valid: true,
            closure_valid: true,
            attempts_self_modification: false,
        };

        prop_assert_eq!(ParetoGate::adjudicate(&c), EvolutionaryFate::Retire);
    }
}
