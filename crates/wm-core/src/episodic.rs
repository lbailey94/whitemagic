//! V6 typed contracts for lossless episodic memory.
//!
//! These types describe source records and their lifecycle without changing
//! the v5 `Memory` representation. Derived memories can reference episodic
//! records through `EvidenceRef` instead of replacing source evidence.

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use thiserror::Error;
use uuid::Uuid;

/// Stable identifier for a raw episodic record.
pub type EpisodicId = Uuid;

/// Wire/schema version for persisted episodic records.
pub const EPISODIC_SCHEMA_VERSION: u16 = 1;

/// Capture policy for the episodic lane.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub struct EpisodicCapturePolicy {
    /// Automatic observation capture is opt-in.
    pub capture_observations: bool,
    /// Redact obvious key/value secret tokens in the episodic copy.
    pub redact_sensitive: bool,
}

impl Default for EpisodicCapturePolicy {
    fn default() -> Self {
        Self {
            capture_observations: false,
            redact_sensitive: true,
        }
    }
}

impl EpisodicCapturePolicy {
    /// The conservative default: explicit writes only, with redaction enabled.
    #[must_use]
    pub const fn explicit_only() -> Self {
        Self {
            capture_observations: false,
            redact_sensitive: true,
        }
    }

    /// Prepare content for the episodic copy without changing the v5 memory.
    #[must_use]
    pub fn prepare_content(self, content: &str) -> String {
        if self.redact_sensitive {
            redact_sensitive_tokens(content)
        } else {
            content.to_string()
        }
    }
}

/// Broad class of an event in the agent experience stream.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum EpisodicKind {
    Observation,
    UserStatement,
    AssistantResponse,
    ToolCall,
    ToolResult,
    Decision,
    Error,
    SystemEvent,
}

/// Origin of a source record.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ProvenanceSource {
    User,
    Tool,
    Agent,
    External,
    System,
}

/// Source and authority metadata for an episodic record.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Provenance {
    pub source: ProvenanceSource,
    pub actor: Option<String>,
    pub source_id: Option<Uuid>,
    /// Confidence in source attribution, not truth of the content.
    pub confidence: f32,
}

impl Provenance {
    /// Create provenance with full source attribution confidence.
    #[must_use]
    pub const fn new(source: ProvenanceSource) -> Self {
        Self {
            source,
            actor: None,
            source_id: None,
            confidence: 1.0,
        }
    }

    /// Clamp source attribution confidence to the valid range.
    #[must_use]
    pub const fn with_confidence(mut self, confidence: f32) -> Self {
        self.confidence = confidence.clamp(0.0, 1.0);
        self
    }

    /// Attach an actor or process identity.
    #[must_use]
    pub fn with_actor(mut self, actor: impl Into<String>) -> Self {
        self.actor = Some(actor.into());
        self
    }
}

/// Relation between a derived item and source evidence.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum EvidenceRelation {
    Supports,
    Contradicts,
    DerivedFrom,
    Supersedes,
}

/// A reference to source evidence, optionally narrowed to a character span.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct EvidenceRef {
    pub record_id: EpisodicId,
    pub relation: EvidenceRelation,
    pub start: Option<u32>,
    pub end: Option<u32>,
}

impl EvidenceRef {
    /// Reference a complete source record.
    #[must_use]
    pub const fn whole(record_id: EpisodicId, relation: EvidenceRelation) -> Self {
        Self {
            record_id,
            relation,
            start: None,
            end: None,
        }
    }

    /// Reference a bounded character span.
    #[must_use]
    pub const fn span(
        record_id: EpisodicId,
        relation: EvidenceRelation,
        start: u32,
        end: u32,
    ) -> Self {
        Self {
            record_id,
            relation,
            start: Some(start),
            end: Some(end),
        }
    }
}

/// Current lifecycle state of a source record.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize, Default)]
#[serde(rename_all = "snake_case", tag = "state")]
pub enum ValidityState {
    #[default]
    Active,
    Superseded {
        by: EpisodicId,
    },
    Revoked {
        reason: String,
    },
    Archived,
    Erased,
}

impl ValidityState {
    /// Whether this record may support a current answer.
    #[must_use]
    pub const fn is_current(&self) -> bool {
        matches!(self, Self::Active)
    }

    /// Whether this record remains available as historical evidence.
    #[must_use]
    pub const fn is_historical(&self) -> bool {
        matches!(self, Self::Superseded { .. } | Self::Archived)
    }
}

/// Explicit lifecycle operation for a source record.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum MemoryTransition {
    Supersede { replacement: EpisodicId },
    Revoke { reason: String },
    Archive,
    Erase,
}

/// Rejected lifecycle transition.
#[derive(Debug, Clone, PartialEq, Eq, Error)]
pub enum ValidityTransitionError {
    #[error("erased records cannot transition")]
    Erased,
    #[error("revoked records cannot transition except erase")]
    Revoked,
    #[error("invalid transition '{transition}' from state '{state}'")]
    Invalid {
        state: &'static str,
        transition: &'static str,
    },
    #[error("a record cannot supersede itself")]
    SelfSupersession,
}

impl ValidityState {
    /// Apply a lifecycle operation without permitting revival of old evidence.
    pub fn transition(
        &mut self,
        record_id: EpisodicId,
        transition: MemoryTransition,
    ) -> Result<(), ValidityTransitionError> {
        if matches!(self, Self::Erased) {
            return Err(ValidityTransitionError::Erased);
        }
        if matches!(self, Self::Revoked { .. }) && !matches!(transition, MemoryTransition::Erase) {
            return Err(ValidityTransitionError::Revoked);
        }

        let transition_name = match &transition {
            MemoryTransition::Supersede { .. } => "supersede",
            MemoryTransition::Revoke { .. } => "revoke",
            MemoryTransition::Archive => "archive",
            MemoryTransition::Erase => "erase",
        };

        match transition {
            MemoryTransition::Supersede { replacement } => {
                if replacement == record_id {
                    return Err(ValidityTransitionError::SelfSupersession);
                }
                if !matches!(self, Self::Active | Self::Archived) {
                    return Err(ValidityTransitionError::Invalid {
                        state: self.name(),
                        transition: transition_name,
                    });
                }
                *self = Self::Superseded { by: replacement };
            }
            MemoryTransition::Revoke { reason } => {
                if !matches!(
                    self,
                    Self::Active | Self::Superseded { .. } | Self::Archived
                ) {
                    return Err(ValidityTransitionError::Invalid {
                        state: self.name(),
                        transition: transition_name,
                    });
                }
                *self = Self::Revoked { reason };
            }
            MemoryTransition::Archive => {
                if !matches!(self, Self::Active | Self::Superseded { .. }) {
                    return Err(ValidityTransitionError::Invalid {
                        state: self.name(),
                        transition: transition_name,
                    });
                }
                *self = Self::Archived;
            }
            MemoryTransition::Erase => *self = Self::Erased,
        }
        Ok(())
    }

    const fn name(&self) -> &'static str {
        match self {
            Self::Active => "active",
            Self::Superseded { .. } => "superseded",
            Self::Revoked { .. } => "revoked",
            Self::Archived => "archived",
            Self::Erased => "erased",
        }
    }
}

/// Lossless source record for the v6 episodic memory lane.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct EpisodicRecord {
    pub schema_version: u16,
    pub id: EpisodicId,
    pub session_id: Option<Uuid>,
    pub sequence: u64,
    pub kind: EpisodicKind,
    pub content: String,
    pub content_hash: String,
    pub provenance: Provenance,
    pub validity: ValidityState,
    #[serde(default)]
    pub is_private: bool,
    #[serde(default)]
    pub model_exclude: bool,
    pub evidence: Vec<EvidenceRef>,
    pub created_at: DateTime<Utc>,
}

impl EpisodicRecord {
    /// Create a new active source record.
    #[must_use]
    pub fn new(
        session_id: Option<Uuid>,
        sequence: u64,
        kind: EpisodicKind,
        content: impl Into<String>,
        provenance: Provenance,
    ) -> Self {
        let content = content.into();
        Self {
            schema_version: EPISODIC_SCHEMA_VERSION,
            id: Uuid::new_v4(),
            session_id,
            sequence,
            kind,
            content_hash: hash_content(&content),
            content,
            provenance,
            validity: ValidityState::Active,
            is_private: false,
            model_exclude: false,
            evidence: Vec::new(),
            created_at: Utc::now(),
        }
    }

    /// Add source references to a derived record.
    #[must_use]
    pub fn with_evidence(mut self, evidence: Vec<EvidenceRef>) -> Self {
        self.evidence = evidence;
        self
    }

    /// Set the canonical source ID while preserving the content hash.
    #[must_use]
    pub const fn with_id(mut self, id: EpisodicId) -> Self {
        self.id = id;
        self
    }

    /// Replace content and recompute its source hash.
    #[must_use]
    pub fn with_content(mut self, content: impl Into<String>) -> Self {
        self.content = content.into();
        self.content_hash = hash_content(&self.content);
        self
    }

    /// Apply the source memory visibility policy to the episodic copy.
    #[must_use]
    pub const fn with_visibility(mut self, is_private: bool, model_exclude: bool) -> Self {
        self.is_private = is_private;
        self.model_exclude = model_exclude;
        self
    }

    /// Apply an explicit lifecycle transition.
    pub fn transition(
        &mut self,
        transition: MemoryTransition,
    ) -> Result<(), ValidityTransitionError> {
        self.validity.transition(self.id, transition)
    }
}

fn hash_content(content: &str) -> String {
    let digest = Sha256::digest(content.as_bytes());
    let mut result = String::with_capacity(digest.len() * 2);
    use std::fmt::Write as _;
    for byte in digest {
        write!(&mut result, "{byte:02x}").expect("writing to a String cannot fail");
    }
    result
}

fn redact_sensitive_tokens(content: &str) -> String {
    const SENSITIVE_KEYS: &[&str] = &[
        "password",
        "passwd",
        "api_key",
        "apikey",
        "secret",
        "token",
        "authorization",
        "credential",
    ];

    content
        .split_whitespace()
        .map(|token| {
            for delimiter in ['=', ':'] {
                let Some(index) = token.find(delimiter) else {
                    continue;
                };
                let prefix =
                    token[..index].trim_matches(|c: char| matches!(c, '"' | '\'' | '{' | '['));
                if SENSITIVE_KEYS
                    .iter()
                    .any(|key| prefix.eq_ignore_ascii_case(key))
                {
                    return format!("{}<REDACTED>", &token[..=index]);
                }
            }
            token.to_string()
        })
        .collect::<Vec<_>>()
        .join(" ")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn record_hashes_source_content() {
        let record = EpisodicRecord::new(
            None,
            1,
            EpisodicKind::Observation,
            "hello",
            Provenance::new(ProvenanceSource::User),
        );
        assert_eq!(record.content_hash.len(), 64);
        assert!(record.validity.is_current());
    }

    #[test]
    fn supersession_preserves_historical_state_without_revival() {
        let id = Uuid::new_v4();
        let replacement = Uuid::new_v4();
        let mut state = ValidityState::Active;
        state
            .transition(id, MemoryTransition::Supersede { replacement })
            .unwrap();
        assert_eq!(state, ValidityState::Superseded { by: replacement });
        assert!(state.is_historical());

        state
            .transition(
                id,
                MemoryTransition::Revoke {
                    reason: "invalidated".into(),
                },
            )
            .unwrap();
        assert!(matches!(state, ValidityState::Revoked { .. }));
        assert_eq!(
            state.transition(id, MemoryTransition::Archive),
            Err(ValidityTransitionError::Revoked)
        );
    }

    #[test]
    fn erased_records_are_terminal() {
        let id = Uuid::new_v4();
        let mut state = ValidityState::Active;
        state.transition(id, MemoryTransition::Erase).unwrap();
        assert_eq!(
            state.transition(id, MemoryTransition::Archive),
            Err(ValidityTransitionError::Erased)
        );
    }

    #[test]
    fn self_supersession_is_rejected() {
        let id = Uuid::new_v4();
        let mut state = ValidityState::Active;
        assert_eq!(
            state.transition(id, MemoryTransition::Supersede { replacement: id }),
            Err(ValidityTransitionError::SelfSupersession)
        );
    }

    #[test]
    fn explicit_capture_redacts_obvious_secret_tokens() {
        let policy = EpisodicCapturePolicy::explicit_only();
        let content = policy.prepare_content("api_key=abc123 note password:secret");
        assert_eq!(content, "api_key=<REDACTED> note password:<REDACTED>");
    }

    #[test]
    fn observation_capture_is_opt_in() {
        assert!(!EpisodicCapturePolicy::default().capture_observations);
    }
}
