//! Gate 9A Slice 1 authorized-sweep acceptance through the public API.
//!
//! Compiled without `cfg(test)` helpers: every path here is the real downstream
//! surface (ratified profile v1, atomic v5 commit, authenticated replay). All
//! stores are disposable synthetic directories; no models or historical data.

use std::path::{Path, PathBuf};

use wm_gen3_core::constitution::default_view;
use wm_gen3_core::evidence::RatifiedChannel;
use wm_gen3_core::field::RelationState;
use wm_gen3_core::intake::CommitDisposition;
use wm_gen3_core::ops::{ImportKind, RecallQuery, RememberItem, Substrate};
use wm_gen3_core::sweep::{
    PRODUCTION_SWEEP_PROFILE_AVAILABLE, SWEEP_PROFILE_V1, SWEEP_USAGE_EVIDENCE_BASIS,
    SWEEP_USAGE_RESTART_PERSISTENT,
};

/// Compile-time assertion: the production profile must be available in this tree.
const _: () = assert!(PRODUCTION_SWEEP_PROFILE_AVAILABLE);

struct TempDir(PathBuf);

impl TempDir {
    fn new(label: &str) -> Self {
        let mut nonce = [0u8; 8];
        getrandom::fill(&mut nonce).unwrap();
        let path = std::env::temp_dir().join(format!(
            "wm-gen3-sweep-acceptance-{label}-{:x}",
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

fn substrate(dir: &TempDir) -> Substrate {
    let mut s = Substrate::open(dir.path(), None, default_view()).expect("open synthetic store");
    s.set_budget(1_000_000);
    s.set_intake_authority(RatifiedChannel::mint("gate9a-acceptance"));
    s
}

fn ingest(s: &mut Substrate, items: &[RememberItem]) {
    let results = s.remember_batch(items);
    for result in &results {
        assert!(result.is_ok(), "synthetic ingest failed: {result:?}");
    }
}

#[test]
fn profile_flag_is_available_and_ratified() {
    assert_eq!(SWEEP_PROFILE_V1.max_records_scanned, 256);
    assert_eq!(SWEEP_PROFILE_V1.max_raw_record_bytes, 16 * 1024);
    assert_eq!(SWEEP_PROFILE_V1.max_single_record_bytes, 1024);
    assert_eq!(SWEEP_PROFILE_V1.max_postings_bytes, 2 * 1024);
    assert_eq!(SWEEP_PROFILE_V1.max_token_occurrences, 1024);
    assert_eq!(SWEEP_PROFILE_V1.max_relations_scanned, 256);
    assert_eq!(SWEEP_PROFILE_V1.max_pair_examinations, 8192);
    assert_eq!(SWEEP_PROFILE_V1.max_effects, 1024);
}

#[test]
fn disabled_sweep_is_a_typed_no_op_without_allocation() {
    let dir = TempDir::new("disabled");
    let mut s = substrate(&dir);
    s.set_sweep_enabled(false);
    let stats = s.think_sweep();
    assert!(stats.disabled, "{stats:?}");
    assert!(!stats.refused, "{stats:?}");
    assert_eq!(stats.sweep, 0, "disabled peek must not consume an id");
    assert_eq!(s.intake_epoch().unwrap(), 0);
    assert!(s.store().iter_relations().unwrap().is_empty());

    s.set_sweep_enabled(true);
    let stats = s.think_sweep();
    assert!(!stats.disabled && !stats.refused, "{stats:?}");
    assert_eq!(stats.sweep, 0, "the first enabled sweep receives id 0");
    assert_eq!(s.intake_epoch().unwrap(), 1);
}

#[test]
fn restart_sensitivity_demotes_used_relations_when_lineage_is_lost() {
    // D2(b) disclosed behavior: usage evidence is process-local, so a restart can
    // demote a used-persistent relation once the durable age threshold is met.
    let dir = TempDir::new("restart-demotion");
    let mut s = substrate(&dir);
    ingest(
        &mut s,
        &[
            item("the color is red", "fixture:r:1"),
            item("the color is blue", "fixture:r:2"),
        ],
    );
    let stats = s.think_sweep();
    assert_eq!(stats.sweep, 0);
    assert_eq!(stats.proposals, 1);
    let relation_id = s.store().iter_relations().unwrap()[0].id();
    let hits = s
        .recall(&RecallQuery {
            query: "color blue".into(),
            limit: 10,
            candidate_limit: 100,
            include_historical: false,
            min_score: 0.0,
            min_coverage: 0.0,
            scope: None,
        })
        .expect("recall");
    assert!(
        hits.iter()
            .any(|hit| hit.superseded_by == Some(relation_id))
    );
    let stats = s.think_sweep();
    assert_eq!(stats.sweep, 1);
    assert!(stats.promotions >= 1, "{stats:?}");
    assert_eq!(
        s.store().iter_relations().unwrap()[0].state(),
        RelationState::Persistent
    );

    // Restart: the process-local usage lineage is gone (disclosed, not hidden).
    drop(s);
    let mut reopened = Substrate::open(dir.path(), None, default_view()).expect("reopen");
    reopened.set_intake_authority(RatifiedChannel::mint("gate9a-acceptance"));
    let stats = reopened.think_sweep();
    assert_eq!(stats.sweep, 2);
    assert_eq!(stats.demotions, 0, "age threshold not yet met: {stats:?}");
    let stats = reopened.think_sweep();
    assert_eq!(stats.sweep, 3);
    assert!(stats.demotions >= 1, "{stats:?}");
    assert_eq!(
        reopened.store().iter_relations().unwrap()[0].state(),
        RelationState::Cold
    );
}

#[test]
fn enabled_empty_sweep_commits_with_explicit_semantics() {
    // An enabled sweep over an empty store is distinct from a disabled one: it
    // consumes a sweep id, advances the epoch, and writes a zero-effect receipt.
    let dir = TempDir::new("empty");
    let mut s = substrate(&dir);
    let stats = s.think_sweep();
    assert!(!stats.disabled && !stats.refused, "{stats:?}");
    assert_eq!(stats.sweep, 0);
    assert_eq!(stats.proposals, 0);
    assert_eq!(s.intake_epoch().unwrap(), 1);
    let outcome = s
        .sweep_replay(stats.operation_id.expect("operation id"))
        .expect("replay");
    assert_eq!(outcome.receipt.effect_count, 0);
    assert!(outcome.receipt.allocated_relation_ids.is_empty());
    assert!(!outcome.receipt.usage_restart_persistent);
}

#[test]
fn oversized_records_refuse_before_any_mutation() {
    let dir = TempDir::new("records-cap");
    let mut s = substrate(&dir);
    let items: Vec<RememberItem> = (0..257)
        .map(|i| item(&format!("record number {i}"), &format!("fixture:{i}")))
        .collect();
    ingest(&mut s, &items);
    let epoch_before = s.intake_epoch().unwrap();
    let stats = s.think_sweep();
    assert!(stats.refused, "{stats:?}");
    assert!(
        stats
            .error
            .as_deref()
            .is_some_and(|e| e.contains("records_scanned")),
        "{:?}",
        stats.error
    );
    assert_eq!(s.intake_epoch().unwrap(), epoch_before);
    assert!(s.store().iter_relations().unwrap().is_empty());
}

#[test]
fn per_record_and_aggregate_byte_ceilings_refuse() {
    let dir = TempDir::new("single-byte-cap");
    let mut s = substrate(&dir);
    ingest(&mut s, &[item(&"ab ".repeat(342), "fixture:single")]);
    let stats = s.think_sweep();
    assert!(stats.refused, "{stats:?}");
    assert!(
        stats
            .error
            .as_deref()
            .is_some_and(|e| e.contains("largest_record_bytes")),
        "{:?}",
        stats.error
    );

    let dir = TempDir::new("aggregate-byte-cap");
    let mut s = substrate(&dir);
    // Each record stays under the 1 KiB per-record ceiling while seventeen of
    // them exceed the 16 KiB aggregate ceiling. Short tokens keep posting keys
    // within LMDB limits.
    let items: Vec<RememberItem> = (0..17)
        .map(|i| {
            let content = format!("{}x", "cd ".repeat(335));
            assert!(content.chars().count() <= 1024);
            item(&content, &format!("s{i}"))
        })
        .collect();
    ingest(&mut s, &items);
    let stats = s.think_sweep();
    assert!(stats.refused, "{stats:?}");
    assert!(
        stats
            .error
            .as_deref()
            .is_some_and(|e| e.contains("raw_record_bytes")),
        "{:?}",
        stats.error
    );
}

#[test]
fn token_occurrence_ceiling_refuses() {
    let dir = TempDir::new("token-cap");
    let mut s = substrate(&dir);
    let items: Vec<RememberItem> = (0..6)
        .map(|record| {
            let content = (0..200)
                .map(|token| format!("{record}{token:03}"))
                .collect::<Vec<_>>()
                .join(" ");
            item(&content, &format!("fixture:tokens:{record}"))
        })
        .collect();
    ingest(&mut s, &items);
    let stats = s.think_sweep();
    assert!(stats.refused, "{stats:?}");
    assert!(
        stats
            .error
            .as_deref()
            .is_some_and(|e| e.contains("token_occurrences")),
        "{:?}",
        stats.error
    );
}

#[test]
fn pair_examination_ceiling_refuses() {
    let dir = TempDir::new("pair-cap");
    let mut s = substrate(&dir);
    let items: Vec<RememberItem> = (0..130)
        .map(|record| {
            item(
                &format!("sh common u{record}"),
                &format!("fixture:pairs:{record}"),
            )
        })
        .collect();
    ingest(&mut s, &items);
    let stats = s.think_sweep();
    assert!(stats.refused, "{stats:?}");
    assert!(
        stats
            .error
            .as_deref()
            .is_some_and(|e| e.contains("pair_examinations")),
        "{:?}",
        stats.error
    );
}

#[test]
fn postings_byte_ceiling_refuses() {
    // 128 low-id fillers (one token each) + 128 high-id records with seven unique
    // tokens each = 1,024 token occurrences (at the occurrence ceiling) while the
    // decoded posting values exceed the 2 KiB posting-byte ceiling because ids
    // above 127 encode as two bytes each.
    let dir = TempDir::new("postings-cap");
    let mut s = substrate(&dir);
    let mut items: Vec<RememberItem> = (0..128)
        .map(|record| {
            item(
                &format!("aaaaaaaa{record:03}"),
                &format!("fixture:postings:a{record}"),
            )
        })
        .collect();
    items.extend((128..256).map(|record| {
        let content = (0..7)
            .map(|slot| format!("q{record:03}k{slot}"))
            .collect::<Vec<_>>()
            .join(" ");
        item(&content, &format!("fixture:postings:b{record}"))
    }));
    ingest(&mut s, &items);
    let stats = s.think_sweep();
    assert!(stats.refused, "{stats:?}");
    assert!(
        stats
            .error
            .as_deref()
            .is_some_and(|e| e.contains("postings_bytes")),
        "{:?}",
        stats.error
    );
}

#[test]
fn authorized_sweep_proposes_promotes_and_replays() {
    let dir = TempDir::new("lifecycle-replay");
    let mut s = substrate(&dir);
    ingest(
        &mut s,
        &[
            item("the color is red", "fixture:color:1"),
            item("the color is blue", "fixture:color:2"),
        ],
    );
    assert_eq!(s.intake_epoch().unwrap(), 2);

    // First sweep: one supersedes proposal, committed atomically.
    let stats = s.think_sweep();
    assert!(!stats.refused, "{:?}", stats.error);
    assert_eq!(stats.sweep, 0);
    assert_eq!(stats.proposals, 1, "{stats:?}");
    let operation_id = stats.operation_id.expect("committed operation id");
    let relations = s.store().iter_relations().unwrap();
    assert_eq!(relations.len(), 1);
    assert_eq!(relations[0].state(), RelationState::Candidate);
    assert_eq!(s.intake_epoch().unwrap(), 3);

    // Recall through the live relation records volatile usage for promotion.
    let hits = s
        .recall(&RecallQuery {
            query: "color blue".into(),
            limit: 10,
            candidate_limit: 100,
            include_historical: false,
            min_score: 0.0,
            min_coverage: 0.0,
            scope: None,
        })
        .expect("recall");
    assert!(
        hits.iter()
            .any(|hit| hit.superseded_by == Some(relations[0].id())),
        "expected the live supersedes relation to be applied"
    );

    // Second sweep: volatile usage promotes the used candidate.
    let stats = s.think_sweep();
    assert!(!stats.refused, "{:?}", stats.error);
    assert_eq!(stats.sweep, 1);
    assert!(stats.promotions >= 1, "{stats:?}");
    assert_eq!(
        s.store().iter_relations().unwrap()[0].state(),
        RelationState::Persistent
    );

    // Authenticated replay returns the original plan without re-planning.
    let replay = s.sweep_replay(operation_id).expect("replay");
    assert_eq!(replay.disposition, CommitDisposition::Replay);
    assert_eq!(replay.receipt.sweep_id, 0);
    assert_eq!(replay.receipt.effect_count, 1);
    assert_eq!(
        replay.receipt.usage_evidence_basis,
        SWEEP_USAGE_EVIDENCE_BASIS
    );
    assert_eq!(
        replay.receipt.usage_restart_persistent,
        SWEEP_USAGE_RESTART_PERSISTENT
    );

    // A later canonical commit moves the epoch; replay still returns the plan.
    ingest(&mut s, &[item("the color is green", "fixture:color:3")]);
    let epoch_after = s.intake_epoch().unwrap();
    let replay = s
        .sweep_replay(operation_id)
        .expect("replay after later commit");
    assert_eq!(replay.disposition, CommitDisposition::Replay);
    assert_eq!(s.intake_epoch().unwrap(), epoch_after);

    // A fresh process (new usage identity) replays the same stored plan.
    drop(s);
    let mut reopened = Substrate::open(dir.path(), None, default_view()).expect("reopen");
    reopened.set_intake_authority(RatifiedChannel::mint("gate9a-acceptance"));
    let replay = reopened
        .sweep_replay(operation_id)
        .expect("cross-restart replay");
    assert_eq!(replay.disposition, CommitDisposition::Replay);
    assert_eq!(replay.receipt.sweep_id, 0);
}
