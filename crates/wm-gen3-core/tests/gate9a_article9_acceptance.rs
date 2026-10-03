//! Gate 9A Article 9 acceptance: external-effect boundaries through the public API.
//!
//! Covers audit failure after a canonical commit, deliberately lost acknowledgement
//! with authenticated retry, and proof that production commits create no JSONL
//! ledgers (the reference nullifier journal is never used by the canonical path).

use std::path::{Path, PathBuf};

use wm_gen3_core::constitution::default_view;
use wm_gen3_core::evidence::RatifiedChannel;
use wm_gen3_core::intake::{CommitDisposition, IntakeKind, IntakeRequest, OperationId};
use wm_gen3_core::ops::Substrate;

struct TempDir(PathBuf);

impl TempDir {
    fn new(label: &str) -> Self {
        let mut nonce = [0u8; 8];
        getrandom::fill(&mut nonce).unwrap();
        let path = std::env::temp_dir().join(format!(
            "wm-gen3-article9-{label}-{:x}",
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

fn authority() -> RatifiedChannel {
    RatifiedChannel::mint("gate9a-article9")
}

fn request(
    channel: &RatifiedChannel,
    substrate: &Substrate,
    operation: [u8; 16],
    epoch: u64,
    content: &str,
    source: &str,
) -> IntakeRequest {
    IntakeRequest::new(
        channel,
        OperationId::from_bytes(operation),
        substrate.intake_realm_id().unwrap(),
        epoch,
        0,
        IntakeKind::Reported,
        content.into(),
        source.into(),
    )
    .unwrap()
}

#[test]
fn audit_failure_after_commit_does_not_undo_the_commit() {
    if !Path::new("/dev/full").exists() {
        eprintln!("skipped: /dev/full is unavailable on this host");
        return;
    }
    let dir = TempDir::new("journal-failure");
    let channel = authority();
    // /dev/full accepts the open and fails every write with ENOSPC, so audit
    // events fail after the canonical commit.
    let mut substrate =
        Substrate::open(dir.path(), Some(Path::new("/dev/full")), default_view()).expect("open");
    substrate.set_intake_authority(authority());
    let intake = request(
        &channel,
        &substrate,
        [42; 16],
        0,
        "article nine audit failure payload",
        "fixture:a9:audit",
    );
    let outcome = substrate
        .remember_authorized(&channel, intake.clone())
        .expect("canonical commit");
    assert_eq!(outcome.disposition, CommitDisposition::Committed);
    assert!(
        !substrate.journal_ok(),
        "audit failure must be reported, not hidden"
    );
    assert_eq!(substrate.store().record_count().unwrap(), 1);
    assert_eq!(substrate.intake_epoch().unwrap(), 1);

    // Recovery is authenticated receipt lookup, never an implied rollback.
    let retry = substrate
        .remember_authorized(&channel, intake)
        .expect("authenticated retry");
    assert_eq!(retry.disposition, CommitDisposition::Replay);
    assert_eq!(retry.receipt, outcome.receipt);
    assert_eq!(substrate.intake_epoch().unwrap(), 1);
}

#[test]
fn lost_acknowledgement_retry_recovers_identical_receipt() {
    let dir = TempDir::new("lost-ack");
    let channel = authority();
    let intake;
    let receipt;
    {
        let mut substrate = Substrate::open(dir.path(), None, default_view()).expect("open");
        substrate.set_intake_authority(authority());
        intake = request(
            &channel,
            &substrate,
            [43; 16],
            0,
            "article nine lost acknowledgement payload",
            "fixture:a9:lost",
        );
        let outcome = substrate
            .remember_authorized(&channel, intake.clone())
            .expect("canonical commit");
        receipt = outcome.receipt;
        // The outcome is deliberately dropped here: the acknowledgement is lost.
    }

    let mut reopened = Substrate::open(dir.path(), None, default_view()).expect("reopen");
    reopened.set_intake_authority(authority());
    let retry = reopened
        .remember_authorized(&channel, intake)
        .expect("retry after lost acknowledgement");
    assert_eq!(retry.disposition, CommitDisposition::Replay);
    assert_eq!(retry.receipt, receipt, "identical committed receipt");
    assert_eq!(reopened.intake_epoch().unwrap(), 1, "no double advance");
    assert_eq!(reopened.store().record_count().unwrap(), 1);
}

#[test]
fn production_commits_create_no_jsonl_ledgers() {
    let dir = TempDir::new("no-jsonl");
    let channel = authority();
    let mut substrate = Substrate::open(dir.path(), None, default_view()).expect("open");
    substrate.set_intake_authority(authority());
    let intake = request(
        &channel,
        &substrate,
        [44; 16],
        0,
        "article nine ledger separation payload",
        "fixture:a9:ledger",
    );
    substrate
        .remember_authorized(&channel, intake)
        .expect("canonical commit");
    let stats = substrate.think_sweep();
    assert!(!stats.refused, "{:?}", stats.error);

    let entries: Vec<String> = std::fs::read_dir(dir.path())
        .expect("read store dir")
        .filter_map(|entry| entry.ok())
        .map(|entry| entry.file_name().to_string_lossy().into_owned())
        .collect();
    assert!(
        !entries.iter().any(|name| name.ends_with(".jsonl")),
        "production commits must not create JSONL ledgers: {entries:?}"
    );
    assert!(
        entries.iter().any(|name| name == "data.mdb"),
        "the canonical LMDB store must exist: {entries:?}"
    );
}
