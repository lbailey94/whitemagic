//! Fuzz target: Dharma Gate evaluate — feed arbitrary effect rows + contexts.
//!
//! Invariant: `evaluate()` must never panic and must return a valid verdict.

#![no_main]

use libfuzzer_sys::fuzz_target;
use wm_core::{BrainWave, Context, EffectRow, Resource};
use wm_governance::{ActionVerdict, DharmaGate};

fuzz_target!(|data: &[u8]| {
    if data.len() < 4 {
        return;
    }

    // Derive brain-wave state from first byte
    let bw = match data[0] % 5 {
        0 => BrainWave::Gamma,
        1 => BrainWave::Beta,
        2 => BrainWave::Alpha,
        3 => BrainWave::Theta,
        _ => BrainWave::Delta,
    };

    // Derive karma_debt and intent_score from bytes
    let karma_debt = (data[1] as f32) / 255.0 * 10.0; // 0.0..10.0
    let intent_score = (data[2] as f32) / 255.0; // 0.0..1.0
    let cpu_load = (data[3] as f32) / 255.0;
    let mem_pressure = if data.len() > 4 {
        (data[4] as f32) / 255.0
    } else {
        0.0
    };

    let gate = DharmaGate::new();
    gate.update_homeostasis(wm_governance::Homeostasis {
        cpu_load,
        memory_pressure: mem_pressure,
        active: cpu_load > 0.15,
    });

    let mut ctx = Context::new(bw);
    ctx.karma_debt = karma_debt;
    ctx.intent_score = intent_score;

    // Build effect rows from remaining data
    let effects = build_effects(&data[4.min(data.len())..]);

    let verdict = gate.evaluate(&effects, &ctx);
    // Verify the verdict is well-formed
    let _ = verdict.blocks();
    let _ = verdict.is_warning();
    let _ = verdict.reason();
});

fn build_effects(data: &[u8]) -> EffectRow {
    let mut reads = Vec::new();
    let mut writes = Vec::new();
    let mut spawns = false;

    for (i, &byte) in data.iter().enumerate().take(32) {
        match byte % 8 {
            0 => reads.push(Resource::Galaxy("codex".into())),
            1 => reads.push(Resource::Galaxy("citta".into())),
            2 => writes.push(Resource::Galaxy("codex".into())),
            3 => writes.push(Resource::Galaxy("citta".into())),
            4 => writes.push(Resource::Filesystem),
            5 => writes.push(Resource::Network),
            6 => writes.push(Resource::Process),
            7 => spawns = true,
            _ => {}
        }
        let _ = i;
    }

    EffectRow {
        reads,
        writes,
        spawns,
        ..Default::default()
    }
}
