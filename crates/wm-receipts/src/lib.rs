//! WM receipts core — continuity-receipt emission, verification, and the WM
//! bundle profiles (session receipts, karma-chain-head attestations).
//!
//! Wire format: `continuity-receipt/0.2`. Canonicalization and verification
//! are delegated to the independent `continuity-receipt` Rust crate so WM
//! emission and the Python reference share one byte-exact rule. This crate is
//! local-only: no network, local keys, standard bundles any CR verifier reads.
//!
//! Naming (decided 2026-09-22): a *receipt* is the neutral, portable atom; the
//! WM-side accumulated record is *karma*, and "karma receipts" is the bridge
//! phrase. Receipts attest integrity, never goodness — no score, no ranking.

#![forbid(unsafe_code)]

pub mod disclose;
pub mod emit;
pub mod error;
pub mod keys;
pub mod profiles;
pub mod verify;

pub use disclose::{attach_map, redact_bundle, reveal_paths};
pub use emit::{RECORD_TYPES, SPEC_ID, TaskChain, content_digest, receipt_digest, unsigned_view};
pub use error::{ReceiptError, Result};
pub use keys::ReceiptKey;
pub use profiles::{
    KarmaHeadInput, ModelRef, SessionReceiptInput, TurnEvidence, karma_head_bundle, session_bundle,
    turn_digest,
};
pub use verify::{VerifyOutcome, verify_bundle};
