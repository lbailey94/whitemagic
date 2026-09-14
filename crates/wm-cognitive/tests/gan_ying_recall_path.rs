//! Deterministic Gan Ying → recall-path trace (test-only).
//!
//! One invented strong coincidence is fed through the real detector into the
//! real Research-cycle consumer, then the persistence/indexing/retrieval
//! boundary is exercised: Research writes are not synchronously indexed, and
//! the documented maintenance heal makes them searchable later. Enabled and
//! disabled runs use identical invented cues; no live store, model, service,
//! or pilot material is used.
//!
//! This is a diagnostic receipt, not a benchmark or a claim of recall
//! efficacy. Activation (salience/repetition) is metadata, never
//! corroboration.

use std::sync::Arc;

use serde_json::json;
use wm_bicameral::{ScenarioEngine, ScenarioEvaluator, TierHandler, WorldModel};
use wm_cognitive::{
    AutonomousCycleRunner, CycleContext, CycleStatus, CycleType, EventType, ResonanceEvent,
    SynchronicityConfig, SynchronicityDetector,
};
use wm_core::Galaxy;
use wm_memory::{
    AssociationStore, MemoryStore, MemoryType, SearchEngine, reindex::heal_index_drift,
};

const CUE_TOKEN: &str = "zxqganyingcue741";

/// Synthetic inference only: require the cue in the actual planner input,
/// then return predictions that cross the unchanged production threshold.
struct CueBoundHandler;

impl TierHandler for CueBoundHandler {
    fn handle(&self, prompt: &str, _max_tokens: usize) -> Result<(String, f32), String> {
        if !prompt.contains(CUE_TOKEN) {
            return Err("synthetic handler requires the propagated cue".into());
        }
        let answer = if prompt.contains("creative action planner") {
            format!("1. Investigate {CUE_TOKEN} with an invented controlled experiment")
        } else {
            format!(
                "DESCRIPTION: Invented experiment resolves {CUE_TOKEN}\n\
                 CHANGES: invented observation\nRISKS: none\n\
                 PROGRESS: 0.95\nCONFIDENCE: 0.95"
            )
        };
        Ok((answer, 0.95))
    }

    fn name(&self) -> &'static str {
        "synthetic-cue-bound"
    }
}

#[test]
fn synthetic_generator_refuses_an_input_without_the_cue() {
    assert!(
        CueBoundHandler
            .handle("unrelated planner input", 256)
            .is_err()
    );
}

fn detector() -> SynchronicityDetector {
    SynchronicityDetector::new(SynchronicityConfig {
        time_window_ms: 2_000,
        min_subsystems: 3,
        max_window_events: 128,
        min_salience: 0.3,
    })
}

/// Event types chosen to span distinct nervous subsystems; the test asserts
/// the detector's own subsystem accounting rather than trusting these names.
fn invented_events() -> Vec<ResonanceEvent> {
    let mut events = Vec::new();
    for (i, event_type) in [
        EventType::CittaAdvance,
        EventType::MemoryCreated,
        EventType::SystemHeartbeat,
        EventType::MemorySearched,
        EventType::DreamPhaseStart,
        EventType::SystemError,
        EventType::MemoryRecalled,
    ]
    .into_iter()
    .enumerate()
    {
        let mut event = ResonanceEvent::new(event_type, "gan-ying-trace", json!({"i": i}));
        event.salience = 0.9;
        events.push(event);
    }
    events
}

#[test]
fn gan_ying_cue_reaches_bounded_research_receipt_and_eventual_index() {
    let tmp = tempfile::tempdir().unwrap();
    let store = Arc::new(MemoryStore::open_default(tmp.path().join("lmdb")).unwrap());
    let index_path = tmp.path().join("tantivy");
    std::fs::create_dir_all(&index_path).unwrap();
    let engine = SearchEngine::open(&index_path).unwrap();
    let assoc = AssociationStore::open(store.env()).unwrap();

    // 1. One invented strong coincidence.
    let mut det = detector();
    for event in invented_events() {
        det.observe(&event);
    }
    assert!(
        det.count() >= 1,
        "detector must record the invented coincidence"
    );
    let sync = det.recent(1)[0].clone();
    assert!(sync.is_strong(), "invented cue must be strong: {sync:?}");
    assert!(
        sync.subsystem_count >= 3,
        "invented cue must span 3+ subsystems: {sync:?}"
    );
    let hint = format!(
        "{} subsystems [{}] co-fired {} events ({}) salience {:.2} over {}ms for {CUE_TOKEN}",
        sync.subsystem_count,
        sync.subsystems
            .iter()
            .map(|s| s.as_str())
            .collect::<Vec<_>>()
            .join(", "),
        sync.event_count,
        sync.event_types
            .iter()
            .map(|e| e.as_str())
            .collect::<Vec<_>>()
            .join("+"),
        sync.mean_salience,
        sync.time_span_ms,
    );
    // Store-free cue: no database identifiers travel with the hint.
    fn looks_like_uuid(token: &str) -> bool {
        token.len() == 36
            && token.chars().filter(|c| *c == '-').count() == 4
            && token.chars().all(|c| c.is_ascii_hexdigit() || c == '-')
    }
    assert!(
        !hint.split_whitespace().any(looks_like_uuid),
        "hint must not carry UUID-shaped ids: {hint}"
    );

    // 2. Disabled control: identical cue withheld -> no proposals.
    let world = WorldModel::new(Arc::new(CueBoundHandler), None);
    let imagination = ScenarioEngine::with_defaults(world, ScenarioEvaluator::with_defaults());

    let mut runner = AutonomousCycleRunner::default();
    let disabled = CycleContext::new(&store, &assoc, 0.8).with_imagination(&imagination);
    let disabled_result = runner.run_cycle(CycleType::Research, &disabled);
    assert_eq!(
        disabled_result.status,
        CycleStatus::NoProposals,
        "disabled cue must not propose: {disabled_result:?}"
    );
    assert!(store.scan(Galaxy::Research, 1_000).unwrap().is_empty());

    // 3. Enabled: the cue becomes a bounded Research problem/hypothesis.
    let enabled = CycleContext::new(&store, &assoc, 0.8)
        .with_imagination(&imagination)
        .with_synchronicity(vec![hint]);
    let enabled_result = runner.run_cycle(CycleType::Research, &enabled);
    assert_eq!(enabled_result.status, CycleStatus::Completed);
    assert!(
        !enabled_result.hypotheses.is_empty(),
        "enabled cue must produce a receipt"
    );
    assert!(
        enabled_result.hypotheses[0]
            .problem
            .contains("Synchronicity:"),
        "hint provenance must stay visible: {}",
        enabled_result.hypotheses[0].problem
    );
    let stored_by_cycle = enabled_result
        .hypotheses
        .iter()
        .filter(|h| h.stored)
        .count();

    assert!(stored_by_cycle >= 1, "cycle must persist its own output");

    // 4. No substitute write: every stored record must correspond exactly to
    // a cue-bound, above-threshold proposal produced by this cycle.
    let research = store.scan(Galaxy::Research, 1_000).unwrap();
    assert_eq!(research.len(), stored_by_cycle);
    for memory in &research {
        assert_eq!(memory.metadata.memory_type, MemoryType::Hypothesis);
        assert!(
            enabled_result.hypotheses.iter().any(|proposal| {
                proposal.stored
                    && proposal.score > 0.5
                    && proposal.problem.contains(CUE_TOKEN)
                    && memory.content
                        == format!(
                            "Hypothesis: {} → Predicted: {} (score: {:.2}, confidence: {:.2})",
                            proposal.hypothesis,
                            proposal.predicted_outcome,
                            proposal.score,
                            proposal.confidence,
                        )
            }),
            "stored record must be the actual cycle output: {memory:?}"
        );
    }
    let boundary = research
        .iter()
        .find(|m| m.content.contains(CUE_TOKEN))
        .expect("a Research hypothesis carrying the cue token");
    let boundary_id = boundary.metadata.id.to_string();

    let pre = engine.search(CUE_TOKEN, 10).unwrap();
    assert!(
        !pre.iter().any(|r| r.memory_id == boundary_id),
        "Research writes must not be synchronously indexed: {pre:?}"
    );
    heal_index_drift(&store, &engine).unwrap();
    let post = engine.search(CUE_TOKEN, 10).unwrap();
    assert!(
        post.iter().any(|r| r.memory_id == boundary_id),
        "maintenance indexing must make the hypothesis retrievable: {post:?}"
    );
    let fetched = store
        .get(Galaxy::Research, boundary.metadata.id)
        .unwrap()
        .expect("indexed cycle record must resolve by its authoritative identity");
    assert_eq!(fetched.content, boundary.content);
    assert_eq!(
        fetched.metadata.content_hash,
        boundary.metadata.content_hash
    );

    eprintln!(
        "GAN_YING_TRACE strong_coincidences={} subsystems={} stored_by_cycle={} \
         enabled_proposals={} disabled_proposals=0 eventual_index=true boundary_id={}",
        det.strong_count(),
        sync.subsystem_count,
        stored_by_cycle,
        enabled_result.hypotheses.len(),
        boundary_id,
    );
}
