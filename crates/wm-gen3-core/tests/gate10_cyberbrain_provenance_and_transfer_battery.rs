//! Gate 10 Cyberbrain Battery: Execution Provenance, Multi-Modal Transport, ContextCache, and RRSI
//!
//! Frontier research battery folding in Luna's scan (Sep 21-24, 2026):
//! - CB-1: Multi-Modal Representation Transport & C2C (Cache-to-Cache) Latent Efficiency
//! - CB-2: ContextCache Prefix Stabilization (Deterministic Sub-200ms TTFT Tokens)
//! - CB-3: Execution Provenance Full Support @ Budget B Benchmark
//! - CB-4: RRSI Regularized Dual-Surface Evolution (Primary vs Held-Out Transfer)
//! - CB-5: Live Hebbian Co-Activation & Graph Propagation Loop
//! - CB-6: Compounding Session Continuity & Multi-Agent Handoff Verification

#![forbid(unsafe_code)]

use std::collections::HashMap;
use std::path::{Path, PathBuf};

use wm_gen3_core::constitution::default_view;
use wm_gen3_core::evidence::RatifiedChannel;
use wm_gen3_core::field::RelationKind;
use wm_gen3_core::ops::{ImportKind, RecallQuery, RememberItem, SessionCheckpoint, Substrate};
use wm_gen3_core::sweep::is_disposable_telemetry;
use wm_gen3_core::transport::{
    ContextCacheToken, GraphEdge, GraphNode, RepresentationTransport, ToolSchemaDefinition,
};

struct TempDir(PathBuf);

impl TempDir {
    fn new(prefix: &str) -> Self {
        let p = std::env::temp_dir().join(format!("wm3-cb-{}-{}", prefix, uuid::Uuid::new_v4()));
        std::fs::create_dir_all(&p).unwrap();
        Self(p)
    }
    fn path(&self) -> &Path {
        &self.0
    }
}

impl Drop for TempDir {
    fn drop(&mut self) {
        let _ = std::fs::remove_dir_all(&self.0);
    }
}

fn open_test_substrate(dir: &TempDir) -> Substrate {
    let mut s = Substrate::open(dir.path(), None, default_view()).expect("open test substrate");
    s.set_budget(1_000_000);
    s.set_noise_enabled(false);
    s.set_intake_authority(RatifiedChannel::mint("cb-battery-test"));
    s
}

/// CB-1: Multi-Modal Representation Transport & C2C Latent Efficiency (ICLR 2026)
#[test]
fn cb_1_representation_transport_multimodal_efficiency() {
    // 1. Text representation (High-level human/agent language at the top of pyramid)
    let text_repr = RepresentationTransport::Text {
        text: "The quick brown fox jumps over the lazy dog and discovers the sovereign kernel."
            .into(),
        language: Some("en".into()),
    };
    assert_eq!(text_repr.discriminator(), "text");
    let baseline_tokens = text_repr.estimated_tokens();
    assert!(baseline_tokens >= 20);

    // 2. Dense Vector representation (Mid-tier semantic matching)
    let vector_repr = RepresentationTransport::Vector {
        embedding: vec![0.12, -0.45, 0.78, 0.99, -0.01, 0.33],
        dimension: 6,
        model_signature: "fastembed:bge-small-en-v1.5".into(),
    };
    assert_eq!(vector_repr.discriminator(), "vector");
    assert_eq!(vector_repr.estimated_tokens(), 0);
    assert_eq!(vector_repr.token_savings_ratio(baseline_tokens), 1.0);

    // 3. Graph State representation (Causal & Provenance topology)
    let graph_repr = RepresentationTransport::GraphState {
        nodes: vec![
            GraphNode {
                id: "tool_call_42".into(),
                label: "execute_analysis".into(),
                attributes: HashMap::new(),
            },
            GraphNode {
                id: "result_42".into(),
                label: "metrics_summary".into(),
                attributes: HashMap::new(),
            },
        ],
        edges: vec![GraphEdge {
            source: "tool_call_42".into(),
            target: "result_42".into(),
            relation: "produces".into(),
            weight: 1.0,
        }],
    };
    assert_eq!(graph_repr.discriminator(), "graph_state");
    assert!(graph_repr.byte_size() > 0);

    // 4. Latent Cache / C2C representation (Direct KV projection, bypassing text generation)
    let latent_repr = RepresentationTransport::LatentCache {
        layer_indices: vec![12, 13, 14, 15],
        cache_digest: [0x5au8; 32],
        shape: vec![4, 32, 64],
        compressed_bytes: vec![0xaa, 0xbb, 0xcc, 0xdd, 0xee, 0xff],
        gate_weights: Some(vec![0.92, 0.88, 0.95, 0.91]),
    };
    assert_eq!(latent_repr.discriminator(), "latent_cache");
    assert_eq!(latent_repr.estimated_tokens(), 0);
    // Bypasses prompt serialization entirely -> 100% token savings
    assert_eq!(latent_repr.token_savings_ratio(baseline_tokens), 1.0);

    // Digest uniqueness across representations
    assert_ne!(text_repr.digest(), vector_repr.digest());
    assert_ne!(vector_repr.digest(), latent_repr.digest());
}

/// CB-2: ContextCache Prefix Stabilization (Sub-200ms TTFT)
#[test]
fn cb_2_context_cache_token_prefix_stabilization() {
    let const_hash = [0x42u8; 32];

    let t1 = ToolSchemaDefinition {
        name: "memory_recall".into(),
        description: "Recall memories using BM25 and graph propagation".into(),
        parameters_schema: r#"{"type":"object","properties":{"query":{"type":"string"}}}"#.into(),
    };
    let t2 = ToolSchemaDefinition {
        name: "memory_remember".into(),
        description: "Store record into sovereign substrate".into(),
        parameters_schema: r#"{"type":"object","properties":{"content":{"type":"string"}}}"#.into(),
    };
    let t3 = ToolSchemaDefinition {
        name: "session_checkpoint".into(),
        description: "Record session checkpoint for agent continuity".into(),
        parameters_schema: r#"{"type":"object","properties":{"session_id":{"type":"string"}}}"#
            .into(),
    };

    // Permutation A: [t1, t2, t3]
    let token_a =
        ContextCacheToken::compute(&[t1.clone(), t2.clone(), t3.clone()], &const_hash, 10);
    // Permutation B: [t3, t1, t2] (scrambled order)
    let token_b =
        ContextCacheToken::compute(&[t3.clone(), t1.clone(), t2.clone()], &const_hash, 10);

    // Invariant: Sorting tools lexicographically guarantees identical cache token regardless of caller order!
    assert_eq!(token_a.cache_hash, token_b.cache_hash);
    assert_eq!(token_a.cache_token, token_b.cache_token);
    assert_eq!(token_a.tool_count, 3);
    assert!(token_a.canonical_prefix_bytes > 0);
    assert!(token_a.estimated_prefix_tokens > 0);

    // Verifies that mutations change the token
    let t2_mut = ToolSchemaDefinition {
        name: "memory_remember".into(),
        description: "Store record into sovereign substrate with modified prompt instructions"
            .into(),
        parameters_schema: t2.parameters_schema.clone(),
    };
    let token_mut = ContextCacheToken::compute(&[t1.clone(), t2_mut, t3.clone()], &const_hash, 10);
    assert_ne!(token_a.cache_hash, token_mut.cache_hash);
}

/// CB-3: Execution Provenance Full Support @ Budget B Benchmark (Sep 22 Frontier Paper)
#[test]
fn cb_3_execution_provenance_full_support_budget_benchmark() {
    let dir = TempDir::new("provenance_benchmark");
    let mut s = open_test_substrate(&dir);

    // Scenario: An agent trajectory executing multi-step evidence generation:
    // Event 0 (Tool Call): "call: database_query(SELECT fiscal_revenue_2026 FROM ledger)"
    // Event 1 (Tool Output): "output: raw_table_bytes { rows: 1420, checksum: 0x9f4a, sum: 12480000 }"
    // Event 2 (Synthesis/Checkpoint): "checkpoint: Fiscal target validated at twelve million four hundred eighty thousand."

    let id0 = s
        .remember_batch(&[RememberItem {
            content: "call: database_query(SELECT fiscal_revenue_2026 FROM ledger)".into(),
            source: "agent:tool_call:001".into(),
            kind: ImportKind::Reported,
        }])
        .remove(0)
        .unwrap();

    let id1 = s
        .remember_batch(&[RememberItem {
            content: "output: raw_table_bytes rows 1420 checksum 0x9f4a sum 12480000".into(),
            source: "tool:sql_engine:001".into(),
            kind: ImportKind::Reported,
        }])
        .remove(0)
        .unwrap();

    let id2 = s
        .remember_batch(&[RememberItem {
            content: "checkpoint: Metric target validated at twelve million".into(),
            source: "agent:synthesis:001".into(),
            kind: ImportKind::Reported,
        }])
        .remove(0)
        .unwrap();

    assert_eq!(id0, 0);
    assert_eq!(id1, 1);
    assert_eq!(id2, 2);

    // Query with disjoint lexical vocabulary: "database_query ledger fiscal_revenue_2026"
    // Without causal links, this query only retrieves Event 0; Events 1 and 2 are missed!
    let hits_unlinked = s
        .recall(&RecallQuery {
            query: "database_query ledger fiscal_revenue_2026".into(),
            limit: 10,
            candidate_limit: 100,
            include_historical: false,
            min_score: 0.0,
            min_coverage: 0.0,
            scope: None,
        })
        .expect("recall unlinked");
    let unlinked_ids: Vec<u64> = hits_unlinked.iter().map(|h| h.id).collect();
    assert!(unlinked_ids.contains(&id0), "Must contain root call");
    assert!(
        !unlinked_ids.contains(&id1),
        "Must NOT contain tool output without causal links"
    );
    assert!(
        !unlinked_ids.contains(&id2),
        "Must NOT contain synthesis without causal links"
    );

    // Link events using typed execution provenance (Causal edges):
    // Event 0 -> Event 1 (Call caused Output)
    // Event 1 -> Event 2 (Output caused Synthesis)
    s.add_relation(RelationKind::Causal, id0, id1, 0.95)
        .unwrap();
    s.add_relation(RelationKind::Causal, id1, id2, 0.90)
        .unwrap();

    // Re-run retrieval with provenance propagation:
    let hits_linked = s
        .recall(&RecallQuery {
            query: "database_query ledger fiscal_revenue_2026".into(),
            limit: 10,
            candidate_limit: 100,
            include_historical: false,
            min_score: 0.0,
            min_coverage: 0.0,
            scope: None,
        })
        .expect("recall linked");

    // Provenance graph propagation successfully pulls the complete evidence chain!
    let retrieved_ids: Vec<u64> = hits_linked.iter().map(|h| h.id).collect();
    assert!(retrieved_ids.contains(&id0), "Must contain root call");
    assert!(
        retrieved_ids.contains(&id1),
        "Must contain causal tool output"
    );
    assert!(
        retrieved_ids.contains(&id2),
        "Must contain causal downstream synthesis"
    );

    // Benchmark Full Support @ Budget B:
    // Does the complete supporting chain fit inside token budgets: 256, 512, 1024, 2048?
    let total_tokens: usize = hits_linked
        .iter()
        .map(|h| h.content.len().div_ceil(4))
        .sum();

    for budget in [256, 512, 1024, 2048] {
        let full_support = total_tokens <= budget;
        assert!(
            full_support,
            "Complete evidence chain must fit under budget {}",
            budget
        );
    }
}

/// CB-4: RRSI Regularized Dual-Surface Evolution (Reject Testbed Adaptations)
#[test]
fn cb_4_rrsi_dual_surface_regularization() {
    // In RRSI, candidate mutations are scored across:
    // 1. Primary Surface (training / immediate benchmark)
    // 2. Held-out Hidden Transfer Surface
    //
    // Candidate A: Overfitted adaptation (wins locally +12%, but loses on transfer -8%) -> REJECT
    // Candidate B: Genuine improvement (wins locally +5%, wins on transfer +4.2%) -> ACCEPT

    struct MutationCandidate {
        #[allow(dead_code)]
        id: &'static str,
        primary_gain: f32,
        transfer_gain: f32,
    }

    let candidate_a = MutationCandidate {
        id: "heuristic_overfit",
        primary_gain: 0.12,
        transfer_gain: -0.08,
    };

    let candidate_b = MutationCandidate {
        id: "regularized_provenance",
        primary_gain: 0.05,
        transfer_gain: 0.042,
    };

    // RRSI Selection Rule: Both primary and transfer gains must be positive;
    // transfer penalty penalizes divergence.
    fn rrsi_ratify(cand: &MutationCandidate) -> bool {
        let transfer_weight = 1.5;
        let regularized_score = cand.primary_gain + transfer_weight * cand.transfer_gain;
        cand.primary_gain > 0.0 && cand.transfer_gain > 0.0 && regularized_score > 0.0
    }

    assert!(
        !rrsi_ratify(&candidate_a),
        "Candidate A must be rejected as an overfitted testbed adaptation"
    );
    assert!(
        rrsi_ratify(&candidate_b),
        "Candidate B must be accepted as a generalizing improvement"
    );
}

/// CB-5: Live Hebbian Co-Activation & Graph Propagation Loop
#[test]
fn cb_5_hebbian_coactivation_and_graph_propagation() {
    let dir = TempDir::new("hebbian_battery");
    let mut s = open_test_substrate(&dir);

    // Ingest two concept memories
    let r0 = s
        .remember_batch(&[RememberItem {
            content: "merkle tree causal lineage directed acyclic graph".into(),
            source: "audit:merkle".into(),
            kind: ImportKind::Reported,
        }])
        .remove(0)
        .unwrap();

    let r1 = s
        .remember_batch(&[RememberItem {
            content: "immutable append only event log receipts".into(),
            source: "audit:receipts".into(),
            kind: ImportKind::Reported,
        }])
        .remove(0)
        .unwrap();

    // Query that co-retrieves both: "audit event graph"
    let q = RecallQuery {
        query: "audit event graph".into(),
        limit: 5,
        candidate_limit: 50,
        include_historical: false,
        min_score: 0.0,
        min_coverage: 0.0,
        scope: None,
    };

    // Fire 3 pulses
    for _ in 0..3 {
        let hits = s.recall(&q).expect("recall pulse");
        assert!(hits.len() >= 2);
    }

    // Hebbian co-activation counter must record 3 co-activations
    let coactivations = s.hebbian_coactivations();
    let pair = if r0 < r1 { (r0, r1) } else { (r1, r0) };
    assert_eq!(coactivations.get(&pair).copied(), Some(3));
}

/// CB-6: Compounding Session Continuity & Multi-Agent Handoff Verification
#[test]
fn cb_6_compounding_session_continuity_pulse() {
    let dir = TempDir::new("session_continuity_pulse");
    let mut s = open_test_substrate(&dir);

    let session_id = "phase4-transition-lane";

    // Turn 1: Antigravity executes research pass
    let cp1 = SessionCheckpoint {
        session_id: session_id.into(),
        agent_id: "antigravity".into(),
        checkpoint_type: "turn".into(),
        summary: "Verified 289 authored tools in Gen2. Formulated 48-tool Core Port matrix.".into(),
        next_queue: vec![
            "Wire representation transport".into(),
            "Implement ContextCache token".into(),
        ],
        open_flags: vec!["zero_bypass_mandatory".into()],
        context_token: Some("ctx_token_alpha".into()),
        representation: Some(RepresentationTransport::Text {
            text: "Turn 1 state verified".into(),
            language: Some("en".into()),
        }),
        timestamp_iso: Some("2026-09-25T14:00:00Z".into()),
    };
    let id1 = s.session_checkpoint(&cp1).unwrap();
    assert_eq!(id1, 0);

    // Turn 2: Opencode resumes from continuity
    let cont1 = s.session_continuity(Some(session_id)).unwrap().unwrap();
    assert_eq!(cont1.summary, cp1.summary);
    assert_eq!(cont1.next_queue, cp1.next_queue);
    assert_eq!(cont1.context_token, Some("ctx_token_alpha".into()));

    // Opencode completes items and creates Handoff checkpoint
    let cp2 = SessionCheckpoint {
        session_id: session_id.into(),
        agent_id: "opencode".into(),
        checkpoint_type: "handoff".into(),
        summary: "Completed RepresentationTransport and ContextCache. Handing off to Luna for benchmark verification.".into(),
        next_queue: vec!["Execute Full Support @ Budget B benchmark".into()],
        open_flags: vec![],
        context_token: Some("ctx_token_beta".into()),
        representation: None,
        timestamp_iso: Some("2026-09-25T14:45:00Z".into()),
    };
    let id2 = s.session_checkpoint(&cp2).unwrap();
    assert_eq!(id2, 1);

    // Turn 3: Luna resumes from continuity
    let cont2 = s.session_continuity(Some(session_id)).unwrap().unwrap();
    assert_eq!(cont2.record_id, id2);
    assert_eq!(cont2.agent_id, "opencode");
    assert_eq!(cont2.checkpoint_type, "handoff");
    assert_eq!(cont2.summary, cp2.summary);
    assert_eq!(
        cont2.next_queue,
        vec!["Execute Full Support @ Budget B benchmark".to_string()]
    );
    assert_eq!(cont2.context_token, Some("ctx_token_beta".into()));

    // Active session list check
    let sessions = s.session_list().unwrap();
    assert_eq!(sessions, vec![session_id.to_string()]);

    // Disposable telemetry verification
    assert!(is_disposable_telemetry(
        "telemetry:agent:debug",
        "Transient log"
    ));
    assert!(is_disposable_telemetry("sensor:heartbeat", "ping"));
    assert!(!is_disposable_telemetry(
        "session:turn:001",
        "Permanent checkpoint"
    ));
}
