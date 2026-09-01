//! Integration tests for the effect row system and brain-wave state machine.
//!
//! These tests verify that effect-based filtering, conflict detection,
//! and brain-wave transitions work correctly — the invariants that
//! governance and dispatch rely on.

use std::time::{Duration, Instant};
use wm_core::brain_wave::{BrainWaveConfig, BrainWaveTracker};
use wm_core::{BrainWave, Capability, CostEstimate, EffectRow, Resource};

// ── EffectRow Construction ────────────────────────────────────────────

#[test]
fn pure_effect_has_no_side_effects() {
    let e = EffectRow::pure();
    assert!(e.reads.is_empty());
    assert!(e.writes.is_empty());
    assert!(e.invokes.is_empty());
    assert!(!e.spawns);
}

#[test]
fn read_only_effect_has_no_writes_or_invokes() {
    let e = EffectRow::read_only(vec![Resource::Galaxy("citta".into())]);
    assert_eq!(e.reads.len(), 1);
    assert!(e.writes.is_empty());
    assert!(e.invokes.is_empty());
    assert!(!e.spawns);
}

// ── EffectRow Brain-Wave Filtering ────────────────────────────────────

#[test]
fn all_effects_available_in_gamma() {
    {
        let bw = BrainWave::Gamma;
        let expensive_writer = EffectRow {
            writes: vec![Resource::KarmaLedger],
            spawns: true,
            cost: CostEstimate {
                expensive: true,
                ..Default::default()
            },
            ..Default::default()
        };
        assert!(
            expensive_writer.is_available_in(bw),
            "Gamma should allow all effects, failed for {bw:?}"
        );
    }
}

#[test]
fn alpha_blocks_expensive_and_write_effects() {
    let alpha = BrainWave::Alpha;

    let cheap_reader = EffectRow::read_only(vec![Resource::Galaxy("codex".into())]);
    assert!(
        cheap_reader.is_available_in(alpha),
        "Alpha should allow cheap reads"
    );

    let expensive_reader = EffectRow {
        cost: CostEstimate {
            expensive: true,
            ..Default::default()
        },
        ..Default::default()
    };
    assert!(
        !expensive_reader.is_available_in(alpha),
        "Alpha should block expensive tools"
    );

    let cheap_writer = EffectRow {
        writes: vec![Resource::Galaxy("citta".into())],
        ..Default::default()
    };
    assert!(
        !cheap_writer.is_available_in(alpha),
        "Alpha should block writes"
    );
}

#[test]
fn theta_blocks_spawns_in_addition_to_alpha_restrictions() {
    let theta = BrainWave::Theta;

    let spawner = EffectRow {
        spawns: true,
        ..Default::default()
    };
    assert!(
        !spawner.is_available_in(theta),
        "Theta should block process spawning"
    );

    let cheap_reader = EffectRow::read_only(vec![Resource::Galaxy("codex".into())]);
    assert!(
        cheap_reader.is_available_in(theta),
        "Theta should allow cheap reads"
    );
}

#[test]
fn delta_blocks_all_tools() {
    let delta = BrainWave::Delta;
    let pure = EffectRow::pure();
    assert!(!pure.is_available_in(delta), "Delta should block all tools");
}

// ── EffectRow Conflict Detection ──────────────────────────────────────

#[test]
fn write_read_conflict_detected() {
    let writer = EffectRow {
        writes: vec![Resource::Galaxy("citta".into())],
        ..Default::default()
    };
    let reader = EffectRow {
        reads: vec![Resource::Galaxy("citta".into())],
        ..Default::default()
    };
    assert!(
        writer.conflicts_with(&reader),
        "Write-read on same resource should conflict"
    );
    assert!(
        reader.conflicts_with(&writer),
        "Conflict detection should be symmetric"
    );
}

#[test]
fn write_write_conflict_detected() {
    let writer_a = EffectRow {
        writes: vec![Resource::KarmaLedger],
        ..Default::default()
    };
    let writer_b = EffectRow {
        writes: vec![Resource::KarmaLedger],
        ..Default::default()
    };
    assert!(
        writer_a.conflicts_with(&writer_b),
        "Write-write on same resource should conflict"
    );
}

#[test]
fn independent_reads_do_not_conflict() {
    let reader_a = EffectRow::read_only(vec![Resource::Galaxy("aria".into())]);
    let reader_b = EffectRow::read_only(vec![Resource::Galaxy("codex".into())]);
    assert!(
        !reader_a.conflicts_with(&reader_b),
        "Reads on different resources should not conflict"
    );
}

#[test]
fn double_spawn_conflicts() {
    let spawner_a = EffectRow {
        spawns: true,
        ..Default::default()
    };
    let spawner_b = EffectRow {
        spawns: true,
        ..Default::default()
    };
    assert!(
        spawner_a.conflicts_with(&spawner_b),
        "Two spawners should conflict"
    );
}

#[test]
fn pure_effects_never_conflict() {
    let pure_a = EffectRow::pure();
    let pure_b = EffectRow::pure();
    assert!(!pure_a.conflicts_with(&pure_b));
}

// ── BrainWave State Machine ───────────────────────────────────────────

#[test]
fn brain_wave_allows_tools_only_in_active_states() {
    assert!(BrainWave::Gamma.allows_tools());
    assert!(BrainWave::Beta.allows_tools());
    assert!(BrainWave::Alpha.allows_tools());
    assert!(!BrainWave::Theta.allows_tools());
    assert!(!BrainWave::Delta.allows_tools());
}

#[test]
fn brain_wave_allows_consolidation_only_in_theta() {
    assert!(!BrainWave::Gamma.allows_consolidation());
    assert!(!BrainWave::Beta.allows_consolidation());
    assert!(!BrainWave::Alpha.allows_consolidation());
    assert!(BrainWave::Theta.allows_consolidation());
    assert!(!BrainWave::Delta.allows_consolidation());
}

#[test]
fn brain_wave_is_dormant_only_in_delta() {
    assert!(!BrainWave::Gamma.is_dormant());
    assert!(!BrainWave::Beta.is_dormant());
    assert!(!BrainWave::Alpha.is_dormant());
    assert!(!BrainWave::Theta.is_dormant());
    assert!(BrainWave::Delta.is_dormant());
}

#[test]
fn brain_wave_names_are_human_readable() {
    assert!(BrainWave::Gamma.name().contains("Gamma"));
    assert!(BrainWave::Beta.name().contains("Beta"));
    assert!(BrainWave::Alpha.name().contains("Alpha"));
    assert!(BrainWave::Theta.name().contains("Theta"));
    assert!(BrainWave::Delta.name().contains("Delta"));
}

// ── BrainWaveTracker Transitions ──────────────────────────────────────

#[test]
fn tracker_starts_in_delta() {
    let tracker = BrainWaveTracker::new(BrainWaveConfig::default());
    assert_eq!(tracker.current(), BrainWave::Delta);
}

#[test]
fn single_event_transitions_to_beta() {
    let mut tracker = BrainWaveTracker::new(BrainWaveConfig::default());
    let bw = tracker.record_event();
    assert_eq!(
        bw,
        BrainWave::Beta,
        "Single event should transition to Beta"
    );
}

#[test]
fn burst_of_events_transitions_to_gamma() {
    let mut tracker = BrainWaveTracker::new(BrainWaveConfig::default());
    for _ in 0..15 {
        let _ = tracker.record_event();
    }
    assert_eq!(
        tracker.current(),
        BrainWave::Gamma,
        "15 events should transition to Gamma"
    );
}

#[test]
fn recompute_after_idle_transitions_to_alpha() {
    let mut tracker = BrainWaveTracker::new(BrainWaveConfig::default());
    let _ = tracker.record_event();
    assert_eq!(tracker.current(), BrainWave::Beta);

    // Simulate idle time beyond the 60s event-rate window so rate drops to 0,
    // but below the theta_idle threshold (300s default) so we land in Alpha.
    let future = Instant::now() + Duration::from_secs(61);
    let bw = tracker.recompute(future);
    assert_eq!(
        bw,
        BrainWave::Alpha,
        "61s idle should transition to Alpha (rate=0, idle<theta)"
    );
}

#[test]
fn recompute_after_long_idle_transitions_to_delta() {
    let mut tracker = BrainWaveTracker::new(BrainWaveConfig::default());
    let _ = tracker.record_event();

    // Simulate idle time beyond delta_idle threshold (1800s = 30min default)
    let future = Instant::now() + Duration::from_secs(1801);
    let bw = tracker.recompute(future);
    assert_eq!(
        bw,
        BrainWave::Delta,
        "30min+ idle should transition to Delta"
    );
}

#[test]
fn custom_config_changes_thresholds() {
    let config = BrainWaveConfig {
        gamma_rate: 5.0, // Lower threshold for Gamma
        alpha_idle: Duration::from_secs(10),
        theta_idle: Duration::from_secs(60),
        delta_idle: Duration::from_secs(120),
    };
    let mut tracker = BrainWaveTracker::new(config);

    // 6 events should trigger Gamma with threshold 5
    for _ in 0..6 {
        let _ = tracker.record_event();
    }
    assert_eq!(tracker.current(), BrainWave::Gamma);

    // 65s idle — beyond 60s event window (rate=0) but below theta_idle (60s)
    // Actually theta_idle is 60s, so 65s would be Theta. Use 61s.
    let future = Instant::now() + Duration::from_secs(61);
    let bw = tracker.recompute(future);
    // With custom config: theta_idle=60s, so 61s idle → Theta
    assert_eq!(
        bw,
        BrainWave::Theta,
        "61s idle with theta_idle=60s should be Theta"
    );
}

// ── Capability and Resource Coverage ──────────────────────────────────

#[test]
fn all_resources_can_be_used_in_effect_rows() {
    let resources = vec![
        Resource::Galaxy("test".into()),
        Resource::KarmaLedger,
        Resource::DharmaRules,
        Resource::SearchIndex,
        Resource::VectorStore,
        Resource::Network,
        Resource::Filesystem,
        Resource::Process,
        Resource::Inference,
        Resource::Session,
    ];
    let e = EffectRow {
        reads: resources.clone(),
        writes: resources,
        invokes: vec![
            Capability::MemoryRead,
            Capability::MemoryWrite,
            Capability::MemoryDelete,
            Capability::Search,
            Capability::VectorSearch,
            Capability::Embed,
            Capability::LlmInfer,
            Capability::Delegate,
            Capability::Execute,
            Capability::NetworkRequest,
            Capability::Dream,
            Capability::CittaUpdate,
        ],
        spawns: true,
        destructive: false,
        sandbox: wm_core::Sandbox::Inherit,
        cost: CostEstimate {
            expensive: true,
            ..Default::default()
        },
    };
    // Should serialize and deserialize
    let json = serde_json::to_string(&e).unwrap();
    let back: EffectRow = serde_json::from_str(&json).unwrap();
    assert_eq!(back.reads.len(), 10);
    assert_eq!(back.writes.len(), 10);
    assert_eq!(back.invokes.len(), 12);
    assert!(back.spawns);
}
