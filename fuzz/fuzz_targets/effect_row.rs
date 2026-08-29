//! Fuzz target: EffectRow — feed arbitrary effect rows to brain-wave filtering
//! and conflict detection.
//!
//! Invariants:
//! - `is_available_in()` must never panic and must return false for Delta
//! - `conflicts_with()` must never panic and must be symmetric

#![no_main]

use libfuzzer_sys::fuzz_target;
use wm_core::{BrainWave, EffectRow, Resource};

fuzz_target!(|data: &[u8]| {
    let effects_a = build_effects(data);
    let effects_b = build_effects(&data[data.len() / 2..]);

    // Delta must always return false
    assert!(
        !effects_a.is_available_in(BrainWave::Delta),
        "Delta should block all tools"
    );

    // Gamma must always return true
    assert!(
        effects_a.is_available_in(BrainWave::Gamma),
        "Gamma should allow all tools"
    );

    // Beta must always return true
    assert!(
        effects_a.is_available_in(BrainWave::Beta),
        "Beta should allow all tools"
    );

    // Alpha: no writes and not expensive
    let alpha_ok = effects_a.is_available_in(BrainWave::Alpha);
    if !effects_a.writes.is_empty() || effects_a.cost.expensive {
        assert!(!alpha_ok, "Alpha should block writes/expensive");
    } else {
        assert!(alpha_ok, "Alpha should allow reads");
    }

    // Theta: no writes, no spawns, not expensive
    let theta_ok = effects_a.is_available_in(BrainWave::Theta);
    if !effects_a.writes.is_empty() || effects_a.cost.expensive || effects_a.spawns {
        assert!(!theta_ok, "Theta should block writes/spawns/expensive");
    } else {
        assert!(theta_ok, "Theta should allow pure reads");
    }

    // Conflict detection symmetry
    let ab = effects_a.conflicts_with(&effects_b);
    let ba = effects_b.conflicts_with(&effects_a);
    assert_eq!(
        ab, ba,
        "conflicts_with must be symmetric: a→b={ab}, b→a={ba}"
    );
});

fn build_effects(data: &[u8]) -> EffectRow {
    let mut reads = Vec::new();
    let mut writes = Vec::new();
    let mut spawns = false;
    let mut expensive = false;

    for (i, &byte) in data.iter().enumerate().take(16) {
        match byte % 10 {
            0 => reads.push(Resource::Galaxy("codex".into())),
            1 => reads.push(Resource::Galaxy("citta".into())),
            2 => reads.push(Resource::Galaxy("aria".into())),
            3 => writes.push(Resource::Galaxy("codex".into())),
            4 => writes.push(Resource::Galaxy("citta".into())),
            5 => writes.push(Resource::Filesystem),
            6 => writes.push(Resource::Network),
            7 => writes.push(Resource::Process),
            8 => spawns = true,
            9 => expensive = true,
            _ => {}
        }
        let _ = i;
    }

    EffectRow {
        reads,
        writes,
        spawns,
        cost: wm_core::CostEstimate {
            expensive,
            ..Default::default()
        },
        ..Default::default()
    }
}
