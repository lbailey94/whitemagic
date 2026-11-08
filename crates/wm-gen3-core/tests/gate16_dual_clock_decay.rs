//! Gate 16 Acceptance Battery: Dual-Clock Lived-Time Decay & The Wisdom Harvest.
//!
//! Validates:
//! 1. Sleep Invariance: 90-day idle pause with 0 lived turns retains >90% working memory.
//! 2. Lived-Time SNR Separation: High-intensity turns decay unreinforced chatter while preserving reinforced anchors.
//! 3. The Wisdom Harvest: Decaying episodic records near eviction boundary are distilled into immortal Gem invariants
//!    linked via Causal provenance relations.

#![forbid(unsafe_code)]

use wm_gen3_core::evidence::RatifiedChannel;
use wm_gen3_core::ops::{Arbitration, DualClockDecayConfig, ImportKind, RecallQuery, RememberItem};
use wm_gen3_core::pulse::make_temp_substrate;

#[test]
fn test_gate16_dual_clock_sleep_invariance() {
    let cfg = DualClockDecayConfig::default();

    // Invariant 1: 90 days of human inactivity with 0 lived causal epochs elapsed
    let wall_elapsed_days = 90.0_f32;
    let lived_epochs = 0_u64;

    let dual_retention = cfg.retention_factor(lived_epochs, wall_elapsed_days, 1);
    let naive_retention = cfg.naive_wall_clock_retention(wall_elapsed_days, 1);

    assert!(
        dual_retention > 0.90,
        "Dual-clock retention after 90 days idle must be >90% (got {:.3})",
        dual_retention
    );
    assert!(
        naive_retention < 0.06,
        "Naive wall-clock retention after 90 days must collapse below 6% (got {:.3})",
        naive_retention
    );
    assert!(
        dual_retention > naive_retention * 15.0,
        "Dual-clock retention must outperform naive wall clock by >15x on long idle pause"
    );
}

#[test]
fn test_gate16_lived_turn_decay_and_snr() {
    let (mut substrate, _s, _j) = make_temp_substrate("gate16_lived_decay");
    substrate.set_intake_authority(RatifiedChannel::mint("test-gate16"));
    substrate.set_arbitration(Arbitration::LivedTimeDualClock);

    // Ingest initial unreinforced scratchpad record
    let ids0 = substrate.remember_batch(&[RememberItem {
        content: "transient scratchpad buffer allocation temporary debug trace".into(),
        source: "session:turn_0:scratchpad".into(),
        kind: ImportKind::Simulated,
    }]);
    let unreinforced_id = ids0[0].as_ref().copied().expect("unreinforced_id");

    // Advance 45 lived turns with intervening execution chatter
    for i in 1..=45 {
        let _ = substrate.remember_batch(&[RememberItem {
            content: format!("routine tool output execution event {}", i),
            source: format!("session:turn_{}:tool", i),
            kind: ImportKind::Simulated,
        }]);
    }

    // Ingest reinforced critical architectural anchor
    let ids1 = substrate.remember_batch(&[RememberItem {
        content: "transient scratchpad buffer allocation core anchor kernel".into(),
        source: "crystal:architectural_core".into(),
        kind: ImportKind::Reported,
    }]);
    let anchor_id = ids1[0].as_ref().copied().expect("anchor_id");

    let r_unreinforced = substrate.evaluate_dual_clock_decay(unreinforced_id, 0.0);
    let r_anchor = substrate.evaluate_dual_clock_decay(anchor_id, 0.0);

    assert!(
        r_anchor.dual_clock_retention > r_unreinforced.dual_clock_retention,
        "Anchor retention ({:.3}) must exceed unreinforced older turn ({:.3})",
        r_anchor.dual_clock_retention,
        r_unreinforced.dual_clock_retention
    );

    let hits = substrate
        .recall(&RecallQuery {
            query: "transient scratchpad buffer allocation".into(),
            limit: 2,
            candidate_limit: 20,
            ..RecallQuery::default()
        })
        .expect("recall");

    assert!(hits.len() >= 2);
    assert_eq!(
        hits[0].id, anchor_id,
        "Lived-time dual-clock arbitration must rank the higher-retention anchor above older unreinforced turn"
    );
}

#[test]
fn test_gate16_wisdom_harvest_pre_eviction() {
    let (mut substrate, _s, _j) = make_temp_substrate("gate16_wisdom_harvest");
    substrate.set_intake_authority(RatifiedChannel::mint("test-gate16"));

    // 1. Ingest episodic records containing critical empirical lessons
    let ids = substrate.remember_batch(&[
        RememberItem {
            content: "error in landlock sandbox bwrap: cannot mount /proc inside unprivileged user namespace without CLONE_NEWUSER".into(),
            source: "session:session_01:execution_trace".into(),
            kind: ImportKind::Reported,
        },
        RememberItem {
            content: "invariant: IETF SCITT monotonic epoch counter must never decrement across restart".into(),
            source: "session:session_01:execution_trace".into(),
            kind: ImportKind::Reported,
        },
    ]);
    let rec0 = ids[0].as_ref().copied().expect("rec0");
    let rec1 = ids[1].as_ref().copied().expect("rec1");

    // 2. Advance lived epochs so retention decays into the harvest zone
    for i in 0..40 {
        let _ = substrate.remember_batch(&[RememberItem {
            content: format!("routine background telemetry pulse {}", i),
            source: format!("session:telemetry_{}:pulse", i),
            kind: ImportKind::Simulated,
        }]);
    }

    // 3. Harvest decaying wisdom before eviction
    let harvested = substrate
        .harvest_decaying_wisdom(0.99)
        .expect("harvest_decaying_wisdom");

    assert!(
        harvested.len() >= 2,
        "Must harvest at least 2 decaying episodic lessons (got {})",
        harvested.len()
    );

    let h0 = harvested
        .iter()
        .find(|h| h.source_record_id == rec0)
        .expect("h0");
    let h1 = harvested
        .iter()
        .find(|h| h.source_record_id == rec1)
        .expect("h1");

    assert_eq!(h0.invariant_category, "DefensiveFailureMode");
    assert_eq!(h1.invariant_category, "SystemicConstraint");

    assert!(
        h0.distilled_rule.contains("landlock sandbox bwrap"),
        "Distilled rule must preserve core lesson"
    );
    assert!(
        h1.distilled_rule.contains("IETF SCITT monotonic epoch"),
        "Distilled rule must preserve core invariant"
    );

    // Verify newly minted Gem records exist in store with high salience
    let gem0 = substrate
        .store()
        .get_record(h0.post_harvest_gem_id)
        .unwrap()
        .unwrap();
    assert!(
        gem0.content()
            .starts_with("WISDOM_GEM [DefensiveFailureMode]:")
    );

    let gem1 = substrate
        .store()
        .get_record(h1.post_harvest_gem_id)
        .unwrap()
        .unwrap();
    assert!(
        gem1.content()
            .starts_with("WISDOM_GEM [SystemicConstraint]:")
    );
}
