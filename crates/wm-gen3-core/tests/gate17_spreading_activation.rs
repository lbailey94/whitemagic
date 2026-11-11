//! Gate 17: associative recall and Hebbian consolidation.
//!
//! Validates:
//! 1. Multi-Hop Lateral Recall: Query for Concept A retrieves lexically-disjoint Concept C
//!    via associative graph resonance (Recall@5 = 1.0 vs 0.33 flat).
//! 2. Full-recall timing is qualified separately in a serialized release-mode
//!    test with the retained strict 5ms budget, including LMDB reads and journal writes.
//! 3. Hebbian Co-Activation Consolidation: Co-activated record pairs increment co-activation count
//!    and consolidate into durable `Associates` relations.

#![forbid(unsafe_code)]

use std::time::{Duration, Instant};
use wm_gen3_core::evidence::RatifiedChannel;
use wm_gen3_core::field::RelationKind;
use wm_gen3_core::ops::{Hit, ImportKind, RecallQuery, RememberItem, Substrate};
use wm_gen3_core::pulse::make_temp_substrate;

fn seed_lateral_recall(substrate: &mut Substrate) -> [u64; 3] {
    substrate.set_intake_authority(RatifiedChannel::mint("test-gate17"));

    // Ingest 3 records where 0 and 2 have disjoint lexical terms
    let ids = substrate.remember_batch(&[
        RememberItem {
            content: "compiler optimization passes in llvm backend".into(),
            source: "docs:llvm".into(),
            kind: ImportKind::Reported,
        },
        RememberItem {
            content: "neural code generator intermediate representation ast transform".into(),
            source: "docs:ir".into(),
            kind: ImportKind::Reported,
        },
        RememberItem {
            content: "hardware register allocator physical target execution".into(),
            source: "docs:allocator".into(),
            kind: ImportKind::Reported,
        },
    ]);
    let id0 = ids[0].as_ref().copied().expect("id0");
    let id1 = ids[1].as_ref().copied().expect("id1");
    let id2 = ids[2].as_ref().copied().expect("id2");

    // Flat query: Query "compiler optimization llvm" matches ONLY Record 0
    let flat_hits = substrate
        .recall(&RecallQuery {
            query: "compiler optimization llvm".into(),
            limit: 5,
            ..RecallQuery::default()
        })
        .expect("flat recall");
    assert_eq!(flat_hits.len(), 1);
    assert_eq!(flat_hits[0].id, id0);

    // Bind 2-hop causal chain: 0 -> 1 -> 2
    substrate
        .add_relation(RelationKind::Causal, id0, id1, 0.90)
        .expect("rel 0->1");
    substrate
        .add_relation(RelationKind::Causal, id1, id2, 0.85)
        .expect("rel 1->2");

    [id0, id1, id2]
}

fn assert_lateral_hits(resonant_hits: &[Hit], ids: &[u64; 3]) {
    assert!(
        resonant_hits.len() >= 3,
        "Resonant recall must retrieve all 3 linked records (got {})",
        resonant_hits.len()
    );
    let hit_ids: Vec<u64> = resonant_hits.iter().map(|h| h.id).collect();
    for id in ids {
        assert!(hit_ids.contains(id));
    }
}

#[test]
fn test_gate17_multi_hop_lateral_recall() {
    let (mut substrate, _s, _j) = make_temp_substrate("gate17_lateral_recall");
    let ids = seed_lateral_recall(&mut substrate);

    // Associative recall with 2 resonance hops
    let start = Instant::now();
    let resonant_hits = substrate
        .recall(&RecallQuery {
            query: "compiler optimization llvm".into(),
            limit: 5,
            ..RecallQuery::default().with_resonance(2)
        })
        .expect("resonant recall");
    let elapsed = start.elapsed();

    println!("Diagnostic full-recall latency (unqualified profile): {elapsed:?}");
    assert_lateral_hits(&resonant_hits, &ids);
}

#[test]
#[ignore = "run the serialized release-mode qualifier in scripts/qualify_gate17_timing.sh"]
fn test_gate17_release_recall_latency() {
    assert!(
        !cfg!(debug_assertions),
        "Gate17 timing qualification requires --release"
    );
    let (mut substrate, _s, _j) = make_temp_substrate("gate17_release_timing");
    let ids = seed_lateral_recall(&mut substrate);
    let query = RecallQuery {
        query: "compiler optimization llvm".into(),
        limit: 5,
        ..RecallQuery::default().with_resonance(2)
    };
    let budget = Duration::from_millis(5);
    let mut samples = Vec::new();
    for _ in 0..9 {
        let start = Instant::now();
        let hits = substrate.recall(&query).expect("resonant recall");
        samples.push(start.elapsed());
        assert_lateral_hits(&hits, &ids);
    }
    println!(
        "\nGATE17_TIMING_JSON={}",
        serde_json::json!({
            "protocol": "gate17-full-recall-v1",
            "profile": "release",
            "scope": "full recall including LMDB reads and journal writes",
            "arch": std::env::consts::ARCH,
            "os": std::env::consts::OS,
            "source_revision": std::env::var("GATE17_SOURCE_REVISION").ok(),
            "test_sha256": std::env::var("GATE17_TEST_SHA256").ok(),
            "ops_sha256": std::env::var("GATE17_OPS_SHA256").ok(),
            "budget_ns": budget.as_nanos(),
            "samples_ns": samples.iter().map(Duration::as_nanos).collect::<Vec<_>>(),
        })
    );
    assert!(
        samples.iter().all(|elapsed| *elapsed < budget),
        "Every full-recall sample must be strictly below 5ms: {samples:?}"
    );
}

#[test]
fn test_gate17_hebbian_coactivation_and_consolidation() {
    let (mut substrate, _s, _j) = make_temp_substrate("gate17_hebbian");
    substrate.set_intake_authority(RatifiedChannel::mint("test-gate17"));

    let ids = substrate.remember_batch(&[
        RememberItem {
            content: "hyperbolic manifold embedding geometry".into(),
            source: "math:geometry".into(),
            kind: ImportKind::Reported,
        },
        RememberItem {
            content: "hyperbolic curvature geodesic distance metric".into(),
            source: "math:metric".into(),
            kind: ImportKind::Reported,
        },
    ]);
    let id0 = ids[0].as_ref().copied().expect("id0");
    let id1 = ids[1].as_ref().copied().expect("id1");

    let pair = if id0 < id1 { (id0, id1) } else { (id1, id0) };

    // Fire co-activations by running queries matching both records
    for _ in 0..3 {
        let _ = substrate.recall(&RecallQuery {
            query: "hyperbolic curvature geometry".into(),
            limit: 5,
            ..RecallQuery::default()
        });
    }

    // Verify volatile Hebbian co-activation count
    let coactivations = substrate.hebbian_coactivations();
    assert!(
        coactivations.get(&pair).copied().unwrap_or(0) >= 3,
        "Pair must record at least 3 co-activations"
    );

    // Consolidate volatile Hebbian co-activations into durable Associates relation
    let wired = substrate
        .consolidate_hebbian_relations(2)
        .expect("consolidate_hebbian_relations");
    assert_eq!(wired, 1, "Must wire exactly 1 durable associative edge");

    // Verify relations view contains the newly wired edge
    let relations = substrate.store().iter_relations().expect("iter_relations");
    let associate_rel = relations
        .iter()
        .find(|r| r.kind() == RelationKind::Associates && (r.src() == pair.0 && r.dst() == pair.1));
    assert!(
        associate_rel.is_some(),
        "Durable Associates relation must exist in store"
    );
}
