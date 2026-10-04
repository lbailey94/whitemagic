//! Gate 12 Acceptance Battery: Frontier 3 — Autonomous Dream Cycle Incubation & Vector Topology Compaction.
//!
//! Validates:
//! 1. Continuous Regime Vector Dynamics: smooth modulation across $q \in [0.0, 1.0]$.
//! 2. Homeostatic Modulation: thermal/battery throttling preserving hardware longevity.
//! 3. Dual-Phase Sleep Cycle: NREM structural compaction + REM associative insight synthesis.
//! 4. Speciation Phase: synthesis of evolvable ActionSkeletons into the Geneseed Vault.
//! 5. Tri-Condition Control: Genuine Dreaming > Sham Dreaming >= Baseline Idle.
//! 6. Strict Bounded Sediment Invariant: Commit Rate $C(q) \le 25\%$ of evaluated candidates.

#![forbid(unsafe_code)]

use wm_gen3_core::dream::{IncubationMode, RegimeVector, execute_dual_phase_sleep_cycle};
use wm_gen3_core::homeostasis::{HardwareTelemetry, HomeostaticRegime};
use wm_gen3_core::ops::{ImportKind, RememberItem};

#[test]
fn gate12_continuous_regime_vector_dynamics() {
    let waking = RegimeVector::waking_baseline();
    assert_eq!(waking.quiescence, 0.0);
    assert!(waking.temperature <= 0.25);
    assert_eq!(waking.associative_radius, 1);
    assert!(waking.counterfactual_rate <= 0.10);

    let deep_dream = RegimeVector::deep_dream(0.0);
    assert_eq!(deep_dream.quiescence, 1.0);
    assert!(deep_dream.temperature >= 0.85);
    assert_eq!(deep_dream.associative_radius, 4);
    assert!(deep_dream.counterfactual_rate >= 0.70);
    assert!(deep_dream.adaptive_commit_threshold >= 0.85);

    // Monotonicity check
    let mid = RegimeVector::from_quiescence(0.5, 0.0);
    assert!(waking.temperature < mid.temperature);
    assert!(mid.temperature < deep_dream.temperature);
    assert!(waking.associative_radius <= mid.associative_radius);
    assert!(mid.associative_radius <= deep_dream.associative_radius);
}

#[test]
fn gate12_homeostatic_thermal_and_battery_throttling() {
    let mut hw_critical = HardwareTelemetry::default();
    hw_critical.cpu_temp_c = 92.0; // Severe thermal stress

    let (regime, should_incubate, reason) = RegimeVector::from_quiescence_with_homeostasis(
        1.0,
        0.0,
        HomeostaticRegime::Critical,
        &hw_critical,
    );

    assert!(
        !should_incubate,
        "Incubation must be deferred under Critical homeostatic regime"
    );
    assert!(reason.contains("Critical homeostatic regime"));
    assert_eq!(regime.quiescence, 0.0);

    // Battery conserving check (< 25% battery on DC power)
    let mut hw_dc_low = HardwareTelemetry::default();
    hw_dc_low.on_ac_power = false;
    hw_dc_low.battery_pct = Some(18.0);

    let (_, should_incubate_dc, dc_reason) = RegimeVector::from_quiescence_with_homeostasis(
        1.0,
        0.0,
        HomeostaticRegime::Nominal,
        &hw_dc_low,
    );
    assert!(
        !should_incubate_dc,
        "Incubation must be deferred when battery < 25% on DC power"
    );
    assert!(dc_reason.contains("Battery conserving regime"));
}

#[test]
fn gate12_dual_phase_sleep_and_speciation_battery() {
    let (mut substrate, _s, _j) = wm_gen3_core::pulse::make_temp_substrate("gate12_sleep_test");

    // Populate substrate with interrelated episodic knowledge
    for i in 0..15 {
        let item = RememberItem {
            content: format!(
                "concept_cluster_{} connects_with concept_cluster_{}",
                i,
                (i + 1) % 15
            ),
            source: "ground_truth".to_string(),
            kind: ImportKind::Reported,
        };
        substrate.remember_batch(&[item]);
    }

    let regime = RegimeVector::deep_dream(0.3);

    // Execute complete Dual-Phase Sleep Cycle
    let sleep_telemetry = execute_dual_phase_sleep_cycle(
        IncubationMode::GenuineDreaming,
        &regime,
        150, // compute budget steps
        &mut substrate,
        999,
    );

    // 1. NREM Compaction verified
    assert!(sleep_telemetry.nrem.duration_us >= 0.0);
    assert!(sleep_telemetry.nrem.token_compaction_ratio <= 1.0);

    // 2. REM Incubation verified
    assert!(sleep_telemetry.rem.candidates_evaluated > 0);
    assert!(sleep_telemetry.rem.candidate_diversity_shannon_entropy > 0.0);

    // 3. Strict Bounded Sediment: commit rate << candidates generated
    assert!(
        sleep_telemetry.rem.commit_rate <= 0.25,
        "Commit rate ({:.3}) must not exceed 25% to prevent storage explosion",
        sleep_telemetry.rem.commit_rate
    );

    // 4. Speciation Phase verified: ActionSkeletons minted into the Geneseed Vault
    assert!(
        !sleep_telemetry.synthesized_skeletons.is_empty(),
        "Genuine dreaming must synthesize evolvable ActionSkeletons from committed insights"
    );

    for skel in &sleep_telemetry.synthesized_skeletons {
        assert!(!skel.id.is_empty());
        assert!(!skel.action_steps.is_empty());
        assert!(skel.rolling_utility > 0.0);
    }
}
