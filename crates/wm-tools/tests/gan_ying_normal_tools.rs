//! Deterministic Gan Ying → normal-tool retrieval proof (test-only).
//!
//! One invented strong coincidence is fed through the real detector into the
//! real Research cycle; the cycle's own above-threshold hypothesis must be
//! persisted, maintenance-indexed, discovered by the normal `memory.search`
//! verb and read back byte-exact by the normal `memory.read` verb. Enabled and
//! disabled runs use identical invented cues, and the fixture is prohibited
//! from writing substitute records. No live store, model, service or pilot
//! material is used.
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
use wm_core::{Context, Galaxy, Tool};
use wm_memory::{
    AssociationStore, MemoryStore, MemoryType, SearchEngine, reindex::heal_index_drift,
};
use wm_tools::{MemoryReadTool, expansion::MemoryHybridRecallTool};

const CUE_TOKEN: &str = "zxqganyingtool742";

/// Synthetic inference only: require the cue in the actual planner input, then
/// return predictions that cross the unchanged production storage threshold.
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
        let mut event = ResonanceEvent::new(event_type, "gan-ying-tools", json!({"i": i}));
        event.salience = 0.9;
        events.push(event);
    }
    events
}

#[tokio::test]
async fn cue_authored_hypothesis_resolves_through_normal_search_and_read() {
    let tmp = tempfile::tempdir().unwrap();
    let store = Arc::new(MemoryStore::open_default(tmp.path().join("lmdb")).unwrap());
    let index_path = tmp.path().join("tantivy");
    std::fs::create_dir_all(&index_path).unwrap();
    let engine = Arc::new(SearchEngine::open(&index_path).unwrap());
    let assoc = AssociationStore::open(store.env()).unwrap();

    // The normal retrieval verbs under test: memory.search (live hybrid verb)
    // and memory.read. Neither is a mock or a substitute implementation.
    let search_tool = MemoryHybridRecallTool::as_search(store.clone(), Some(engine.clone()), None);
    let read_tool = MemoryReadTool::new(store.clone());

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

    // 2. Disabled control: the identical cue withheld -> no proposals, no
    //    persistence, and the normal search verb discovers nothing.
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
    let disabled_search = search_tool
        .call(
            &mut Context::default(),
            json!({"query": CUE_TOKEN, "limit": 10}),
        )
        .await
        .unwrap();
    assert!(
        disabled_search["results"].as_array().unwrap().is_empty(),
        "disabled cue must stay undiscoverable: {disabled_search}"
    );

    // 3. Enabled: the cue becomes the cycle's own persisted hypothesis. No
    //    substitute store write is permitted: every Research record must
    //    correspond exactly to a stored proposal from this cycle.
    let enabled = CycleContext::new(&store, &assoc, 0.8)
        .with_imagination(&imagination)
        .with_synchronicity(vec![hint]);
    let enabled_result = runner.run_cycle(CycleType::Research, &enabled);
    assert_eq!(enabled_result.status, CycleStatus::Completed);
    let stored_by_cycle = enabled_result
        .hypotheses
        .iter()
        .filter(|h| h.stored)
        .count();
    assert!(stored_by_cycle >= 1, "cycle must persist its own output");
    let research = store.scan(Galaxy::Research, 1_000).unwrap();
    assert_eq!(
        research.len(),
        stored_by_cycle,
        "Research must contain only this cycle's stored proposals"
    );
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
    let hypothesis = research
        .iter()
        .find(|m| m.content.contains(CUE_TOKEN))
        .expect("a Research hypothesis carrying the cue token");
    let hypothesis_id = hypothesis.metadata.id.to_string();
    let hypothesis_content = hypothesis.content.clone();
    let hypothesis_hash = hypothesis.metadata.content_hash.clone();

    // 4. Before maintenance the normal search verb cannot discover it;
    //    Research writes are not synchronously indexed.
    let pre = search_tool
        .call(
            &mut Context::default(),
            json!({"query": CUE_TOKEN, "limit": 10}),
        )
        .await
        .unwrap();
    assert!(
        !pre["results"]
            .as_array()
            .unwrap()
            .iter()
            .any(|r| r["id"].as_str() == Some(hypothesis_id.as_str())),
        "Research writes must not be synchronously indexable: {pre}"
    );
    heal_index_drift(&store, &engine).unwrap();

    // 5. Maintenance indexing makes the same cue-bound record discoverable by
    //    the normal search verb, with authoritative identity metadata.
    let post = search_tool
        .call(
            &mut Context::default(),
            json!({"query": CUE_TOKEN, "limit": 10}),
        )
        .await
        .unwrap();
    let hit = post["results"]
        .as_array()
        .unwrap()
        .iter()
        .find(|r| r["id"].as_str() == Some(hypothesis_id.as_str()))
        .unwrap_or_else(|| panic!("maintenance-indexed hypothesis must be discoverable: {post}"));
    assert_eq!(hit["galaxy"], "research", "{hit}");
    assert_eq!(hit["source"], "fts", "{hit}");

    // 6. The normal read verb returns the exact original by authoritative
    //    identity and galaxy — no thaw, no summary, no substitute record.
    let read = read_tool
        .call(
            &mut Context::default(),
            json!({"id": hypothesis_id, "galaxy": "research"}),
        )
        .await
        .unwrap();
    assert_eq!(read["status"], "success", "{read}");
    assert_eq!(read["id"], hypothesis_id, "{read}");
    assert_eq!(
        read["content"].as_str().unwrap().as_bytes(),
        hypothesis_content.as_bytes(),
        "normal read must return the exact cue-bound original"
    );
    let stored = store
        .get(Galaxy::Research, hypothesis.metadata.id)
        .unwrap()
        .expect("cycle record must resolve by its authoritative identity");
    assert_eq!(stored.metadata.content_hash, hypothesis_hash);
    assert_eq!(stored.content, hypothesis_content);

    eprintln!(
        "GAN_YING_NORMAL_TOOLS stored_by_cycle={} research_records={} pre_index_discovery=false \
         post_index_discovery=true read_exact_bytes={} search_route={} no_substitute_writes=true",
        stored_by_cycle,
        research.len(),
        hypothesis_content.len(),
        hit["source"],
    );
}
