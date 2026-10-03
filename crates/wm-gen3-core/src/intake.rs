//! Gate 9A Slice 1 authorized-ingestion types.
//!
//! These types bind one non-World record request to a stable operation ID, store realm,
//! expected epoch, and local ratified-channel authority. The affine capability is issued only
//! after the caller has applied the existing budget/noise/duplicate policy gates.

use std::collections::HashSet;
use std::fmt;

use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};

use crate::evidence::RatifiedChannel;

pub const STORE_FORMAT_VERSION: u32 = 5;
pub const COMMIT_RECEIPT_VERSION: u8 = 2;
pub const FEASIBILITY_CAPABILITY_CLASS: u8 = 1;
pub const REMEMBER_OPERATION_KIND: u8 = 1;
pub const INTAKE_SCOPE: &str = "wm.gen3.remember.v1";
pub const CREDENTIAL_CLASS: &str = "local-ratified-channel-v1";

const MANIFEST_DOMAIN: &[u8] = b"wm.gen3.commit-manifest";
const POSTING_DERIVATION: &[u8] = b"field-tokenizer-v1";

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct OperationId([u8; 16]);

impl OperationId {
    #[must_use]
    pub const fn from_bytes(bytes: [u8; 16]) -> Self {
        Self(bytes)
    }

    #[must_use]
    pub const fn as_bytes(&self) -> &[u8; 16] {
        &self.0
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[repr(u8)]
pub enum IntakeKind {
    Reported = 0,
    System = 1,
    Simulated = 2,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct AuthorityDescriptor {
    version: u8,
    credential_class: String,
    issuer_label: String,
    scope: String,
}

impl AuthorityDescriptor {
    fn from_channel(channel: &RatifiedChannel) -> Result<Self, IntakeError> {
        if channel.name().is_empty() {
            return Err(IntakeError::InvalidAuthorityLabel);
        }
        Ok(Self {
            version: 1,
            credential_class: CREDENTIAL_CLASS.to_string(),
            issuer_label: channel.name().to_string(),
            scope: INTAKE_SCOPE.to_string(),
        })
    }

    #[must_use]
    pub const fn version(&self) -> u8 {
        self.version
    }

    #[must_use]
    pub fn credential_class(&self) -> &str {
        &self.credential_class
    }

    #[must_use]
    pub fn issuer_label(&self) -> &str {
        &self.issuer_label
    }

    #[must_use]
    pub fn scope(&self) -> &str {
        &self.scope
    }

    #[must_use]
    pub fn is_canonical(&self) -> bool {
        self.version == 1
            && self.credential_class == CREDENTIAL_CLASS
            && !self.issuer_label.is_empty()
            && self.scope == INTAKE_SCOPE
    }

    /// Stable compiler-visible binding for the complete authority descriptor.
    #[must_use]
    pub fn digest(&self) -> [u8; 32] {
        let mut hash = Sha256::new();
        hash_bytes(&mut hash, b"wm.gen3.intake-authority");
        hash.update([self.version]);
        hash_bytes(&mut hash, self.credential_class.as_bytes());
        hash_bytes(&mut hash, self.issuer_label.as_bytes());
        hash_bytes(&mut hash, self.scope.as_bytes());
        hash.finalize().into()
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct IntakeRequest {
    operation_id: OperationId,
    realm_id: [u8; 16],
    expected_epoch: u64,
    item_ordinal: u64,
    kind: IntakeKind,
    content: String,
    source: String,
    authority: AuthorityDescriptor,
}

impl IntakeRequest {
    #[allow(clippy::too_many_arguments)]
    pub fn new(
        channel: &RatifiedChannel,
        operation_id: OperationId,
        realm_id: [u8; 16],
        expected_epoch: u64,
        item_ordinal: u64,
        kind: IntakeKind,
        content: String,
        source: String,
    ) -> Result<Self, IntakeError> {
        Ok(Self {
            operation_id,
            realm_id,
            expected_epoch,
            item_ordinal,
            kind,
            content,
            source,
            authority: AuthorityDescriptor::from_channel(channel)?,
        })
    }

    #[must_use]
    pub const fn operation_id(&self) -> OperationId {
        self.operation_id
    }
    #[must_use]
    pub const fn realm_id(&self) -> &[u8; 16] {
        &self.realm_id
    }
    #[must_use]
    pub const fn expected_epoch(&self) -> u64 {
        self.expected_epoch
    }
    #[must_use]
    pub const fn item_ordinal(&self) -> u64 {
        self.item_ordinal
    }
    #[must_use]
    pub const fn kind(&self) -> IntakeKind {
        self.kind
    }
    #[must_use]
    pub fn content(&self) -> &str {
        &self.content
    }
    #[must_use]
    pub fn source(&self) -> &str {
        &self.source
    }
    #[must_use]
    pub fn authority(&self) -> &AuthorityDescriptor {
        &self.authority
    }

    /// Require fresh possession of the same typed local authority for submission or retry.
    pub fn authenticate(&self, channel: &RatifiedChannel) -> Result<(), IntakeError> {
        let presented = AuthorityDescriptor::from_channel(channel)?;
        if self.authority == presented && self.authority.is_canonical() {
            Ok(())
        } else {
            Err(IntakeError::AuthorityMismatch)
        }
    }

    /// Exact canonical Gate 9A Slice 1 manifest digest.
    #[must_use]
    pub fn digest(&self) -> [u8; 32] {
        let mut hash = Sha256::new();
        hash_bytes(&mut hash, MANIFEST_DOMAIN);
        hash.update([1]); // manifest version
        hash.update(STORE_FORMAT_VERSION.to_be_bytes());
        hash.update(self.realm_id);
        hash.update(self.operation_id.as_bytes());
        hash.update([1]); // operation kind: remember
        hash.update([self.authority.version]);
        hash_bytes(&mut hash, self.authority.credential_class.as_bytes());
        hash_bytes(&mut hash, self.authority.issuer_label.as_bytes());
        hash_bytes(&mut hash, self.authority.scope.as_bytes());
        hash.update(self.expected_epoch.to_be_bytes());
        hash.update(1_u64.to_be_bytes()); // one target
        hash.update([1, 1]); // records table, store-next-contiguous allocation
        hash.update(self.item_ordinal.to_be_bytes());
        hash.update([self.kind as u8]);
        hash_bytes(&mut hash, self.content.as_bytes());
        hash_bytes(&mut hash, self.source.as_bytes());
        hash.update([0, 2]); // Evidence, Persistent
        hash.update(1.0_f32.to_bits().to_be_bytes());
        hash.update([1]); // created_at == assigned id
        hash_bytes(&mut hash, POSTING_DERIVATION);
        hash.update([0]); // vector absent
        hash.finalize().into()
    }
}

fn hash_bytes(hash: &mut Sha256, bytes: &[u8]) {
    hash.update((bytes.len() as u64).to_be_bytes());
    hash.update(bytes);
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct CommitReceipt {
    pub version: u8,
    pub realm_id: [u8; 16],
    pub operation_id: OperationId,
    pub manifest_digest: [u8; 32],
    pub authority: AuthorityDescriptor,
    pub capability_class: u8,
    pub compiler_scope: String,
    pub authority_digest: [u8; 32],
    pub operation_kind: u8,
    pub target_table: u8,
    pub pre_epoch: u64,
    pub post_epoch: u64,
    pub record_id: u64,
    pub created_at: u64,
    pub record_digest: [u8; 32],
    pub postings_digest: [u8; 32],
    pub vector_effect: u8,
    pub committed: bool,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CommitDisposition {
    Committed,
    Replay,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CommitOutcome {
    pub receipt: CommitReceipt,
    pub disposition: CommitDisposition,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum IntakeError {
    InvalidAuthorityLabel,
    AuthorityMismatch,
    IdempotencyConflict,
    CorruptCommitState,
    StaleEpoch { expected: u64, actual: u64 },
    IdExhausted,
    EpochExhausted,
    ProjectionForbidden,
    UnauthorizedCapability { field: &'static str },
}

impl fmt::Display for IntakeError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::InvalidAuthorityLabel => write!(f, "intake authority label is empty"),
            Self::AuthorityMismatch => {
                write!(f, "intake request was issued by a different authority")
            }
            Self::IdempotencyConflict => write!(f, "operation id belongs to a different request"),
            Self::CorruptCommitState => write!(f, "nullifier and receipt state is inconsistent"),
            Self::StaleEpoch { expected, actual } => {
                write!(f, "stale epoch: expected {expected}, actual {actual}")
            }
            Self::IdExhausted => write!(f, "record id space exhausted"),
            Self::EpochExhausted => write!(f, "store epoch exhausted"),
            Self::ProjectionForbidden => {
                write!(f, "projection is excluded from Gate 9A Slice 1 intake")
            }
            Self::UnauthorizedCapability { field } => {
                write!(
                    f,
                    "commit capability does not authorize intake field {field}"
                )
            }
        }
    }
}

impl std::error::Error for IntakeError {}

/// Epistemic Admission Guard (Anti-Echo Chamber & Correlated Promotion Defense).
/// Evaluates whether multiple testimony streams share an upstream origin,
/// collapsing duplicate lineages to a single independent evidentiary vote (N = 1).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct EpistemicAdmissionGuard {
    pub seen_lineages: HashSet<[u8; 32]>,
}

impl Default for EpistemicAdmissionGuard {
    fn default() -> Self {
        Self::new()
    }
}

impl EpistemicAdmissionGuard {
    #[must_use]
    pub fn new() -> Self {
        Self {
            seen_lineages: HashSet::new(),
        }
    }

    /// Evaluates candidate testimony against historical lineage roots.
    /// Returns true if this is an independent lineage, false if it is correlated repetition.
    pub fn admit_testimony(&mut self, root_digest: &[u8; 32]) -> bool {
        self.seen_lineages.insert(*root_digest)
    }

    /// Computes canonical lineage digest from source and root claim.
    #[must_use]
    pub fn compute_lineage_digest(source: &str, content: &str) -> [u8; 32] {
        let mut hasher = Sha256::new();
        hasher.update(b"wm.gen3.lineage.root:");
        hasher.update(source.as_bytes());
        hasher.update(b":");
        hasher.update(content.as_bytes());
        hasher.finalize().into()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn request(content: &str) -> IntakeRequest {
        IntakeRequest::new(
            &RatifiedChannel::stub("synthetic-test-issuer"),
            OperationId::from_bytes([7; 16]),
            [9; 16],
            3,
            0,
            IntakeKind::Reported,
            content.to_string(),
            "synthetic:source".to_string(),
        )
        .expect("valid request")
    }

    #[test]
    fn manifest_binds_payload_and_is_deterministic() {
        assert_eq!(
            request("synthetic alpha").digest(),
            request("synthetic alpha").digest()
        );
        assert_ne!(
            request("synthetic alpha").digest(),
            request("synthetic beta").digest()
        );
    }

    #[test]
    fn empty_authority_label_is_rejected() {
        let result = IntakeRequest::new(
            &RatifiedChannel::stub(""),
            OperationId::from_bytes([0; 16]),
            [0; 16],
            0,
            0,
            IntakeKind::Reported,
            "synthetic".into(),
            "fixture".into(),
        );
        assert_eq!(result, Err(IntakeError::InvalidAuthorityLabel));
    }

    #[test]
    fn submission_requires_fresh_matching_typed_authority() {
        let request = request("synthetic alpha");
        assert!(
            request
                .authenticate(&RatifiedChannel::stub("synthetic-test-issuer"))
                .is_ok()
        );
        assert_eq!(
            request.authenticate(&RatifiedChannel::stub("different-issuer")),
            Err(IntakeError::AuthorityMismatch)
        );
    }
}
