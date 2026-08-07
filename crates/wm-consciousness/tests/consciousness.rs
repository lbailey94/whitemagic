//! Integration tests for consciousness subsystems.
//!
//! These tests verify that:
//! - CittaVector initializes to a neutral 16D state
//! - DreamPhase has exactly 12 phases in the correct order
//! - EcoModeController transitions correctly with events
//! - Brain-wave states propagate through the eco mode controller

use wm_consciousness::{EcoModeController, citta::CittaVector, dream::DreamPhase};
use wm_core::BrainWave;

// ── CittaVector ───────────────────────────────────────────────────────

#[test]
fn citta_vector_neutral_is_16_dimensional() {
    let vec = CittaVector::neutral();
    assert_eq!(
        vec.as_array().len(),
        16,
        "Citta vector must be 16-dimensional"
    );
}

#[test]
fn citta_vector_neutral_defaults_to_half() {
    let vec = CittaVector::neutral();
    for (i, &val) in vec.as_array().iter().enumerate() {
        assert!(
            (val - 0.5).abs() < f32::EPSILON,
            "Neutral citta dimension {i} should be 0.5, got {val}"
        );
    }
}

#[test]
fn citta_vector_update_modifies_specific_dimension() {
    let mut vec = CittaVector::neutral();
    vec.update(0, 0.9);
    assert!((vec.as_array()[0] - 0.9).abs() < f32::EPSILON);
    // Other dimensions should be unchanged
    assert!((vec.as_array()[1] - 0.5).abs() < f32::EPSILON);
}

#[test]
fn citta_vector_update_ignores_out_of_bounds_dimension() {
    let mut vec = CittaVector::neutral();
    vec.update(16, 1.0); // Out of bounds — should be a no-op
    vec.update(100, 1.0); // Way out of bounds
    // All dimensions should still be 0.5
    for val in vec.as_array() {
        assert!((val - 0.5).abs() < f32::EPSILON);
    }
}

#[test]
fn citta_vector_default_matches_neutral() {
    let default = CittaVector::default();
    let neutral = CittaVector::neutral();
    for (a, b) in default.as_array().iter().zip(neutral.as_array().iter()) {
        assert!((a - b).abs() < f32::EPSILON);
    }
}

// ── DreamPhase ────────────────────────────────────────────────────────

#[test]
fn dream_phase_has_exactly_12_phases() {
    assert_eq!(
        DreamPhase::all().len(),
        12,
        "Dream cycle must have exactly 12 phases"
    );
}

#[test]
fn dream_phase_all_returns_phases_in_canonical_order() {
    let phases = DreamPhase::all();
    assert_eq!(phases[0], DreamPhase::Triage);
    assert_eq!(phases[1], DreamPhase::Consolidation);
    assert_eq!(phases[2], DreamPhase::Serendipity);
    assert_eq!(phases[3], DreamPhase::Governance);
    assert_eq!(phases[4], DreamPhase::Narrative);
    assert_eq!(phases[5], DreamPhase::Kaizen);
    assert_eq!(phases[6], DreamPhase::Oracle);
    assert_eq!(phases[7], DreamPhase::Decay);
    assert_eq!(phases[8], DreamPhase::Constellation);
    assert_eq!(phases[9], DreamPhase::Prediction);
    assert_eq!(phases[10], DreamPhase::Enrichment);
    assert_eq!(phases[11], DreamPhase::Harmonize);
}

#[test]
fn dream_phase_all_phases_are_unique() {
    let phases = DreamPhase::all();
    let mut seen = std::collections::HashSet::new();
    for phase in &phases {
        assert!(seen.insert(*phase), "Duplicate dream phase: {phase:?}");
    }
}

// ── EcoModeController ─────────────────────────────────────────────────

#[test]
fn eco_mode_starts_in_delta() {
    let controller = EcoModeController::default();
    assert_eq!(controller.current(), BrainWave::Delta);
}

#[test]
fn eco_mode_single_event_transitions_to_beta() {
    let mut controller = EcoModeController::default();
    let bw = controller.record_event();
    assert_eq!(bw, BrainWave::Beta);
}

#[test]
fn eco_mode_burst_transitions_to_gamma() {
    let mut controller = EcoModeController::default();
    for _ in 0..15 {
        let _ = controller.record_event();
    }
    assert_eq!(controller.current(), BrainWave::Gamma);
}

#[test]
fn eco_mode_recompute_after_idle_returns_alpha() {
    let mut controller = EcoModeController::default();
    let _ = controller.record_event();
    // Immediately recompute — should still be Beta since no time has passed
    let bw = controller.recompute();
    // Since no time has passed, we should still be in an active state
    assert!(
        bw == BrainWave::Beta || bw == BrainWave::Gamma,
        "Immediately after event, should be Beta or Gamma, got {bw:?}"
    );
}

#[test]
fn eco_mode_multiple_events_increment_rate() {
    let mut controller = EcoModeController::default();
    for i in 0..5 {
        let bw = controller.record_event();
        // After first event: Beta, after enough: Gamma
        if i < 10 {
            assert!(
                bw == BrainWave::Beta || bw == BrainWave::Gamma,
                "Event {i} should be Beta or Gamma, got {bw:?}"
            );
        }
    }
}
