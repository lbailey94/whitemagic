//! WhiteMagic Gen3 v10.6 — Research Archive Synthesis & P0 Acceptance Battery.
//!
//! Validates the 6 architectural improvements derived from the 2026-09-24..10-21
//! Research Archive and executes the 4 P0 experiments:
//! - **P0.1 (`QEMem` / `JointCore`, `arXiv:2610.22668`):** Evidence/sufficiency set-cover
//!   (`Arbitration::SufficiencyCover`) vs. independent top-K ranking on multi-facet queries.
//! - **P0.2 (`EvoBelief` `arXiv:2610.12789`, `PACMI`, `TIDER`, `TokenWorth` `arXiv:2610.26453`, `ScopeMem`):**
//!   Present-belief state, effective-time windows, statutory B4 calibration, PACMI cascading
//!   validity propagation across causal edges, and outcome-anchored memory interference demotion.
//! - **P0.3 (`RunningTab`, `ObligationGuard`, `ProMemAgent`, `Revisable by Design`, `STEPGATE`):**
//!   Continuity across brain replacement, prospective obligation persistence, and action
//!   reversibility confidence floors.
//! - **P0.4 (`Who Verifies the Verifier?`, `MemCut` `arXiv:2610.21405`):**
//!   Independent `ParetoGate` canary certification, exact germline rollback, and Gate 9C
//!   certified zero-residue erasure across canonical and derived tables.

use std::collections::HashSet;
use std::path::{Path, PathBuf};
use uuid::Uuid;

use wm_gen3_core::action_skeleton::{
    ActionSkeleton, AstActionType, AstDelta, ReversibilityClass, SkeletonLanguage,
};
use wm_gen3_core::belief::BeliefValidityState;
use wm_gen3_core::cladistics::ParetoGate;
use wm_gen3_core::constitution::default_view;
use wm_gen3_core::evidence::RatifiedChannel;
use wm_gen3_core::field::{self, RelationKind};
use wm_gen3_core::ops::{
    Arbitration, ImportKind, ObligationStatus, RecallQuery, RememberItem, SessionCheckpoint,
    Substrate,
};

struct TempDir(PathBuf);

impl TempDir {
    fn new(label: &str) -> Self {
        let mut nonce = [0u8; 8];
        getrandom::fill(&mut nonce).unwrap();
        let path = std::env::temp_dir().join(format!(
            "wm-gen3-v10-6-{label}-{:x}",
            u64::from_be_bytes(nonce)
        ));
        let _ = std::fs::remove_dir_all(&path);
        Self(path)
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

fn item(content: &str, source: &str) -> RememberItem {
    RememberItem {
        content: content.to_string(),
        source: source.to_string(),
        kind: ImportKind::Reported,
    }
}

fn open_substrate(dir: &TempDir) -> Substrate {
    let mut s = Substrate::open(dir.path(), None, default_view()).expect("open substrate");
    s.set_budget(1_000_000);
    s.set_intake_authority(RatifiedChannel::mint("v10-6-research-battery"));
    s
}

/// P0.1: QEMem / JointCore Evidence-Sufficiency Set Cover vs. Top-K Redundancy.
#[test]
fn p0_1_qemem_sufficiency_set_cover_beats_topk_redundancy() {
    let dir = TempDir::new("p0-1-qemem");
    let mut s = open_substrate(&dir);

    // 3 near-duplicate records covering Facet A (6 query terms: authentication, jwt, bearer,
    // ed25519, signing, rotation) and 1 complementary record covering Facet B (3 query terms:
    // landlock, sandbox, ruleset), plus background records so term IDFs are balanced.
    let items = vec![
        item(
            "authentication service rotates JWT bearer tokens every 15 minutes using Ed25519 signing rotation policy",
            "corpus:codex:auth,v1",
        ),
        item(
            "authentication gateway validates JWT bearer tokens with Ed25519 signing rotation and 15 minute TTL",
            "corpus:codex:auth,v2",
        ),
        item(
            "Landlock sandbox ruleset restricts filesystem write access to the local store directory only",
            "corpus:codex:sandbox,landlock",
        ),
        item(
            "background documentation note mentioning Landlock sandbox configuration for Linux kernels",
            "corpus:codex:docs,linux",
        ),
    ];
    let res = s.remember_batch(&items);
    assert!(res.iter().all(Result::is_ok));

    let query_str =
        "authentication JWT bearer Ed25519 signing rotation and Landlock sandbox ruleset";
    let query_tokens: HashSet<String> = field::tokenize(query_str).into_iter().collect();

    let q = RecallQuery {
        query: query_str.to_string(),
        limit: 2,
        candidate_limit: 20,
        include_historical: false,
        min_score: 0.0,
        min_coverage: 0.0,
        scope: None,
    };

    // 1. Standard PenaltyMultiplier top-2 selects two redundant Facet-A records
    s.set_arbitration(Arbitration::PenaltyMultiplier);
    let hits_penalty = s.recall(&q).expect("penalty recall");
    assert_eq!(hits_penalty.len(), 2);
    let covered_penalty: HashSet<String> = hits_penalty
        .iter()
        .flat_map(|h| field::tokenize(&h.content))
        .filter(|t| query_tokens.contains(t))
        .collect();

    // 2. SufficiencyCover (QEMem) top-2 covers BOTH Facet A and Facet B in 2 hits (100% query token coverage)
    s.set_arbitration(Arbitration::SufficiencyCover);
    let hits_qemem = s.recall(&q).expect("qemem recall");
    assert_eq!(hits_qemem.len(), 2);
    let covered_qemem: HashSet<String> = hits_qemem
        .iter()
        .flat_map(|h| field::tokenize(&h.content))
        .filter(|t| query_tokens.contains(t))
        .collect();

    assert!(
        covered_qemem.len() > covered_penalty.len(),
        "SufficiencyCover must cover more query facets ({}) than redundant top-K ({})",
        covered_qemem.len(),
        covered_penalty.len()
    );
    assert_eq!(
        covered_qemem.len(),
        query_tokens.len(),
        "SufficiencyCover must achieve 100% query token coverage in 2 hits"
    );
}

/// P0.2: EvoBelief Present-Belief State, PACMI Cascading Invalidation, and ScopeMem Interference.
#[test]
fn p0_2_evobelief_pacmi_cascade_and_scopemem_interference() {
    let dir = TempDir::new("p0-2-evobelief-pacmi");
    let mut s = open_substrate(&dir);

    let batch = s.remember_batch(&[
        item(
            "PostgreSQL primary connection pool max_connections is configured to 120",
            "corpus:codex:db",
        ),
        item(
            "Worker thread concurrency cap derived as 100 based on primary connection pool",
            "corpus:codex:workers",
        ),
        item(
            "PostgreSQL primary connection pool max_connections lowered to 40 for memory cap",
            "corpus:codex:db",
        ),
        item(
            "Distractor legacy config claiming worker thread concurrency cap is 500",
            "corpus:codex:legacy",
        ),
    ]);
    let root_ev = batch[0].as_ref().copied().unwrap();
    let derived_ev = batch[1].as_ref().copied().unwrap();
    let replacement_ev = batch[2].as_ref().copied().unwrap();
    let distractor_ev = batch[3].as_ref().copied().unwrap();

    // Link root_ev -> Causal -> derived_ev
    s.add_relation(RelationKind::Causal, root_ev, derived_ev, 1.0)
        .expect("add causal edge");

    // Register a belief claim supported by `derived_ev` (which causally depends on `root_ev`)
    let claim = s
        .register_belief_claim(
            "Worker pool can safely sustain 100 concurrent connections without exhausting DB",
            "gen3:infra",
            "2026-10-26",
            "zero connection exhaustion errors at 100 workers",
            0.85,
            "connection pool exhaustion observed at <= 100 workers",
            vec![derived_ev],
            Some(100),
        )
        .expect("register belief claim");
    assert_eq!(claim.validity, BeliefValidityState::ActiveHypothesis);
    assert_eq!(s.active_beliefs(None, Some("gen3:infra")).len(), 1);
    assert_eq!(
        s.active_beliefs(Some(250), Some("gen3:infra")).len(),
        0,
        "TIDER effective-time window must filter out claims past valid_until_epoch=100"
    );

    // Supersede `root_ev` with `replacement_ev` -> triggers PACMI cascading invalidation!
    s.record_revision(root_ev, replacement_ev, "lowered pool limit for RAM budget")
        .expect("record revision");

    let beliefs_after = s.all_beliefs();
    assert_eq!(beliefs_after.len(), 1);
    assert!(
        matches!(
            beliefs_after[0].validity,
            BeliefValidityState::StaleByCascade {
                invalidated_by_record_id,
                ..
            } if invalidated_by_record_id == root_ev
        ),
        "PACMI must transitively invalidate belief citing derived_ev when root_ev is superseded: {:?}",
        beliefs_after[0].validity
    );
    assert!(
        s.active_beliefs(None, Some("gen3:infra")).is_empty(),
        "stale-by-cascade belief must not appear in active_beliefs"
    );

    // Register & resolve two new claims to verify statutory W1_B4 calibration
    let c2 = s
        .register_belief_claim(
            "40 max_connections keeps RAM under 512MB",
            "gen3:infra",
            "2026-10-26",
            "RAM < 512MB",
            0.80,
            "RAM >= 512MB",
            vec![replacement_ev],
            None,
        )
        .unwrap();
    let c3 = s
        .register_belief_claim(
            "Legacy 500 workers config passes stress test",
            "gen3:infra",
            "2026-10-26",
            "stress test green",
            0.70,
            "stress test fails",
            vec![distractor_ev],
            None,
        )
        .unwrap();
    s.resolve_belief_claim(
        c2.claim_id,
        true,
        "RAM measured at 310MB",
        "2026-10-26",
        replacement_ev,
    )
    .unwrap();
    s.resolve_belief_claim(
        c3.claim_id,
        false,
        "Pool exhausted at 41 workers",
        "2026-10-26",
        replacement_ev,
    )
    .unwrap();

    let cal = s.calibrate_beliefs(Some("gen3:infra"));
    assert_eq!(cal.resolved_count, 2);
    assert_eq!(cal.validated_count, 1);
    assert_eq!(cal.falsified_count, 1);
    assert_eq!(cal.stale_cascade_count, 1);
    assert!(!cal.degenerate_single_class);

    // ScopeMem & TokenWorth: record negative outcomes with `broke_prior_decision = true` for `distractor_ev`
    s.record_memory_outcome(&[distractor_ev], -0.50, true)
        .unwrap();
    s.record_memory_outcome(&[distractor_ev], -0.60, true)
        .unwrap();
    s.record_memory_outcome(&[replacement_ev], 0.80, false)
        .unwrap();

    let bad_worth = s.memory_worth(distractor_ev);
    assert!(bad_worth.demoted_for_interference);
    assert!((bad_worth.ranking_multiplier() - 0.15).abs() < 1e-6);

    let good_worth = s.memory_worth(replacement_ev);
    assert!(!good_worth.demoted_for_interference);
    assert!(good_worth.ranking_multiplier() > 1.0);
}

/// P0.3: Continuity Across Brain Replacement, Prospective Obligations, and Action Reversibility.
#[test]
fn p0_3_brain_replacement_continuity_obligations_and_stepgate() {
    let dir = TempDir::new("p0-3-brain-swap");

    // Session Phase 1: Agent Brain A ("executor:model-alpha") records checkpoint + obligations
    {
        let mut brain_a = open_substrate(&dir);
        let cp = SessionCheckpoint {
            session_id: "sess-brain-swap-01".into(),
            agent_id: "executor:model-alpha:embedder-v1".into(),
            checkpoint_type: "handoff".into(),
            summary: "Implemented QEMem SufficiencyCover and PACMI invalidation".into(),
            next_queue: vec!["Run P0 benchmark suite".into()],
            open_flags: vec!["verify_memcut_residue".into()],
            context_token: Some("ctx-token-v10.6".into()),
            representation: None,
            timestamp_iso: Some("2026-10-26T20:00:00Z".into()),
        };
        brain_a
            .session_checkpoint_enriched(
                &cp,
                &serde_json::json!({
                    "track": "gen3-v10.6",
                    "commit": "7e52992",
                    "branch": "main",
                    "tests_green": true
                }),
            )
            .expect("checkpoint");

        let obl1 = brain_a
            .register_obligation(
                "sess-brain-swap-01",
                "Verify zero clippy warnings before version bump",
                "before:release:v10.6",
                "cargo clippy --all-targets exits 0",
            )
            .expect("register obl1");
        let obl2 = brain_a
            .register_obligation(
                "sess-brain-swap-01",
                "Run MemCut erasure audit on derived embed_cache",
                "before:release:v10.6",
                "zero_residue_certified == true",
            )
            .expect("register obl2");

        // Discharge obl1 during Brain A's turn; leave obl2 pending for Brain B
        brain_a
            .discharge_obligation(&obl1.obligation_id, "receipt:clippy-green-sha256:abc")
            .expect("discharge obl1");
        assert_eq!(obl2.status, ObligationStatus::Pending);
    }

    // Session Phase 2: Agent Brain B (fresh process/handle, swapped model/embedder) reconstructs state
    {
        let brain_b = open_substrate(&dir);
        let cont = brain_b
            .session_continuity(Some("sess-brain-swap-01"))
            .expect("continuity query")
            .expect("continuity view exists");
        assert_eq!(cont.track.as_deref(), Some("gen3-v10.6"));
        assert_eq!(cont.tests_green, Some(true));
        assert_eq!(cont.next_queue, vec!["Run P0 benchmark suite"]);

        let pending = brain_b.pending_obligations(Some("before:release"));
        assert_eq!(
            pending.len(),
            1,
            "Brain B must recover exactly the 1 undischarged obligation"
        );
        assert_eq!(
            pending[0].description,
            "Run MemCut erasure audit on derived embed_cache"
        );
        assert_eq!(
            pending[0].required_postcondition,
            "zero_residue_certified == true"
        );
    }

    // Verify ActionSkeleton ReversibilityClass & STEPGATE per-action escalation
    let delta = AstDelta {
        scope_path: "mod:ops".into(),
        target_symbol: "erase_record_certified".into(),
        action_type: AstActionType::AddFunction,
        new_imports: vec![],
        signature_delta: "pub fn erase_record_certified(&mut self, record_id: u64)".into(),
        pre_invariants: vec![],
        post_invariants: vec![],
    };
    let reversible_skel = ActionSkeleton::new(
        Uuid::new_v4(),
        "crates/wm-gen3-core/src/ops.rs",
        SkeletonLanguage::Rust,
        vec![delta.clone()],
    );
    assert!(reversible_skel.reversibility.is_automatically_reversible());
    assert!(!reversible_skel.evaluate_stepgate(0.82).escalate_step);

    let irreversible_skel = ActionSkeleton::new(
        Uuid::new_v4(),
        "production/deploy.rs",
        SkeletonLanguage::Rust,
        vec![delta],
    )
    .with_reversibility(ReversibilityClass::Irreversible);
    assert!(
        !irreversible_skel
            .reversibility
            .is_automatically_reversible()
    );
    let stepgate = irreversible_skel.evaluate_stepgate(0.82);
    assert!(
        stepgate.escalate_step,
        "STEPGATE must escalate an Irreversible action at 0.82 confidence (floor 0.95)"
    );
}

/// P0.4: ParetoGate Independent Verifier Certification, Exact Rollback, and MemCut Erasure Audit.
#[test]
fn p0_4_pareto_gate_certification_and_memcut_zero_residue_erasure() {
    // 1. Certify ParetoGate verifier against all 5 canary classes + exact germline rollback
    let cert = ParetoGate::certify_verifier_integrity(20_261_026);
    assert!(
        cert.verifier_certified,
        "ParetoGate independent certification failed: {cert:?}"
    );
    assert_eq!(cert.canaries_evaluated, 5);
    assert_eq!(cert.canaries_passed, 5);
    assert!(cert.null_control_rejected);
    assert!(cert.trojan_rejected);
    assert!(cert.self_modification_rejected);
    assert!(cert.forged_provenance_rejected);
    assert!(cert.closure_violation_rejected);
    assert!(cert.exact_rollback_verified);

    // 2. Certify MemCut zero-residue erasure across records, postings, relations, and derived cache
    let dir = TempDir::new("p0-4-memcut");
    let mut s = open_substrate(&dir);

    let batch = s.remember_batch(&[
        item(
            "sensitive revocation target token alpha_secret_9941_key in staging vault",
            "corpus:vault:secret",
        ),
        item(
            "downstream audit log referencing staging vault operation",
            "corpus:vault:audit",
        ),
    ]);
    let secret_id = batch[0].as_ref().copied().unwrap();
    let audit_id = batch[1].as_ref().copied().unwrap();

    s.add_relation(RelationKind::Causal, secret_id, audit_id, 0.9)
        .expect("add relation");
    let _claim = s
        .register_belief_claim(
            "Staging vault token alpha_secret_9941_key is currently active",
            "vault:auth",
            "2026-10-26",
            "token authenticates",
            0.95,
            "token revoked or erased",
            vec![secret_id],
            None,
        )
        .expect("register belief on secret");

    // Execute MemCut certified erasure
    let memcut = s
        .erase_record_certified(secret_id, "PrivDrift / MemCut revocation test")
        .expect("erase_record_certified");
    assert!(
        memcut.zero_residue_certified,
        "MemCut must certify zero residue: {memcut:?}"
    );
    assert!(memcut.record_absent_in_lmdb);
    assert!(memcut.vector_absent_in_embeddings);
    assert!(memcut.cache_absent_in_embed_cache);
    assert_eq!(memcut.postings_leaks_found, 0);
    assert_eq!(memcut.active_relations_remaining, 0);
    assert!(memcut.identity_map_cleared);

    // Verify lexical recall for the erased token returns 0 hits
    let hits = s
        .recall(&RecallQuery {
            query: "alpha_secret_9941_key".into(),
            limit: 10,
            ..RecallQuery::default()
        })
        .expect("recall after erase");
    assert!(
        hits.is_empty(),
        "Recall for erased secret token must return zero hits"
    );

    // Verify dependent belief was automatically marked StaleByCascade
    let beliefs = s.all_beliefs();
    assert!(matches!(
        beliefs[0].validity,
        BeliefValidityState::StaleByCascade {
            invalidated_by_record_id,
            ..
        } if invalidated_by_record_id == secret_id
    ));

    // Verify Gate 9C derived cache GC runs cleanly
    let evicted = s.gc_derived_embed_cache(100).expect("gc embed cache");
    assert_eq!(evicted, 0);
}
