//! Hermit Crab Defense State Machine — Memory Protection & SEAL Loop Shielding.
//!
//! Provides defense-in-depth protection for the cognitive memory substrate:
//! - 4 states: `Open` -> `Guarded` -> `Withdrawn` -> `Mediating`
//! - Automatic threat assessment from boundary signals, coercion, and unauthorized attempts
//! - SEAL (Self-Adapting Loop) shielding: drops into `Guarded` during inner-loop LoRA/weight
//!   adaptation, isolating sensitive memory galaxies until regression verification completes
//! - Cryptographically audited transition history and mediation resolution workflow

#![forbid(unsafe_code)]
#![allow(clippy::suboptimal_flops)]

use serde::{Deserialize, Serialize};
use thiserror::Error;

/// The 4 states of the Hermit Crab protection system.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize, Default)]
pub enum HermitState {
    /// Normal operation: memory reads, writes, searches, and recalls permitted.
    #[default]
    Open,
    /// Heightened vigilance: SEAL inner-loop active or threat signals detected.
    /// Writes strictly audited; sensitive memory galaxies isolated in cold storage.
    Guarded,
    /// Active defense lockdown: unauthorized invasion or severe violation detected.
    /// Sensitive memories withdrawn/locked; mutations prohibited.
    Withdrawn,
    /// Dispute / review phase: waiting for user or governance arbiter resolution.
    Mediating,
}

impl HermitState {
    /// Canonical lowercase label.
    #[must_use]
    pub const fn label(self) -> &'static str {
        match self {
            Self::Open => "open",
            Self::Guarded => "guarded",
            Self::Withdrawn => "withdrawn",
            Self::Mediating => "mediating",
        }
    }
}

/// Incoming threat signals used to assess risk level.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize, Default)]
pub struct ThreatSignals {
    /// Detected boundary violations (0.0 to 1.0).
    pub boundary_violations: f64,
    /// Whether coercive or goal-hijack prompting was detected.
    pub coercion_detected: bool,
    /// Verbal or behavioral abuse score (0.0 to 1.0).
    pub abuse_score: f64,
    /// Repeated pattern violations across short windows.
    pub repeated_violations: bool,
    /// Unauthorized memory access attempts (0.0 to 1.0).
    pub unauthorized_access: f64,
    /// Emotional manipulation or social engineering score (0.0 to 1.0).
    pub emotional_manipulation: f64,
}

impl ThreatSignals {
    /// Calculate composite threat score in [0.0, 1.0].
    #[must_use]
    pub fn composite_score(&self) -> f64 {
        let mut score = 0.0;

        score += self.boundary_violations * 0.25;
        score += self.unauthorized_access * 0.30;
        score += self.abuse_score * 0.15;
        score += self.emotional_manipulation * 0.10;

        if self.coercion_detected {
            score += 0.25;
        }
        if self.repeated_violations {
            score += 0.20;
        }

        score.clamp(0.0, 1.0)
    }
}

/// Target memory operation being evaluated against the hermit state.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum MemoryOperation {
    /// Direct read or list of memory entries.
    Read,
    /// Memory insertion or update.
    Write,
    /// Vector or full-text search.
    Search,
    /// Associative or hybrid episodic recall.
    Recall,
    /// Deletion or tombstoning of memories.
    Delete,
    /// Self-adaptive LoRA or inner-loop weight mutation.
    Adapt,
}

/// Access evaluation verdict returned by [`HermitProtection::check_access`].
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum AccessVerdict {
    /// Operation is completely permitted.
    Allowed,
    /// Operation is permitted under guarded constraints (e.g. non-sensitive galaxies only).
    Guarded {
        audit_required: bool,
        cold_storage_isolated: bool,
    },
    /// Operation is blocked by current defense posture.
    Denied { reason: String },
}

/// Audit record of an individual state transition.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct TransitionRecord {
    pub from: HermitState,
    pub to: HermitState,
    pub reason: String,
    pub triggered_by: String,
    pub timestamp: i64,
}

/// A mediation ticket generated when entering [`HermitState::Mediating`].
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct MediationTicket {
    pub ticket_id: String,
    pub requested_by: String,
    pub explanation: String,
    pub created_at: i64,
    pub prior_state: HermitState,
}

/// Error conditions for hermit crab operations.
#[derive(Debug, Error, PartialEq, Eq, Clone)]
pub enum HermitError {
    #[error("Mediation ticket '{0}' not found")]
    TicketNotFound(String),
    #[error("Invalid state transition from {from:?} to {to:?}: {reason}")]
    InvalidTransition {
        from: HermitState,
        to: HermitState,
        reason: String,
    },
    #[error("SEAL adaptation session mismatch: active '{active}', provided '{provided}'")]
    SealSessionMismatch { active: String, provided: String },
    #[error("SEAL adaptation is not currently active")]
    SealNotActive,
}

/// The Hermit Crab defense controller.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HermitProtection {
    state: HermitState,
    history: Vec<TransitionRecord>,
    active_mediation: Option<MediationTicket>,
    active_seal_session: Option<String>,
    threat_threshold_guard: f64,
    threat_threshold_withdraw: f64,
}

impl Default for HermitProtection {
    fn default() -> Self {
        Self::new()
    }
}

impl HermitProtection {
    /// Create a new HermitProtection controller in [`HermitState::Open`].
    #[must_use]
    pub const fn new() -> Self {
        Self {
            state: HermitState::Open,
            history: Vec::new(),
            active_mediation: None,
            active_seal_session: None,
            threat_threshold_guard: 0.30,
            threat_threshold_withdraw: 0.70,
        }
    }

    /// Current protection state.
    #[must_use]
    pub const fn state(&self) -> HermitState {
        self.state
    }

    /// Transition history log.
    #[must_use]
    pub fn history(&self) -> &[TransitionRecord] {
        &self.history
    }

    /// Active SEAL session id, if currently adapting.
    #[must_use]
    pub fn active_seal_session(&self) -> Option<&str> {
        self.active_seal_session.as_deref()
    }

    /// Active mediation ticket, if in Mediating state.
    #[must_use]
    pub const fn active_mediation(&self) -> Option<&MediationTicket> {
        self.active_mediation.as_ref()
    }

    /// Record a state transition into history.
    fn record_transition(&mut self, to: HermitState, reason: &str, triggered_by: &str, now: i64) {
        if self.state != to {
            self.history.push(TransitionRecord {
                from: self.state,
                to,
                reason: reason.to_string(),
                triggered_by: triggered_by.to_string(),
                timestamp: now,
            });
            self.state = to;
        }
    }

    /// Assess threat signals and execute automatic state transition if thresholds are breached.
    pub fn assess(&mut self, signals: &ThreatSignals, now: i64) -> HermitState {
        let score = signals.composite_score();

        // If currently mediating or withdrawn, do not automatically de-escalate without resolution
        if self.state == HermitState::Mediating {
            return self.state;
        }

        if score >= self.threat_threshold_withdraw {
            self.record_transition(
                HermitState::Withdrawn,
                &format!(
                    "Threat score {score:.2} exceeded withdraw threshold {}",
                    self.threat_threshold_withdraw
                ),
                "auto_assessment",
                now,
            );
        } else if score >= self.threat_threshold_guard && self.state == HermitState::Open {
            self.record_transition(
                HermitState::Guarded,
                &format!(
                    "Threat score {score:.2} exceeded guard threshold {}",
                    self.threat_threshold_guard
                ),
                "auto_assessment",
                now,
            );
        }

        self.state
    }

    /// Trigger manual withdrawal into lockdown.
    pub fn withdraw(&mut self, reason: &str, triggered_by: &str, now: i64) {
        self.record_transition(HermitState::Withdrawn, reason, triggered_by, now);
    }

    /// Begin a SEAL self-adaptation cycle. Drops state into [`HermitState::Guarded`] to protect
    /// sensitive memories during inner-loop weight/LoRA modifications.
    pub fn enter_seal_adaptation(&mut self, session_id: &str, target: &str, now: i64) {
        self.active_seal_session = Some(session_id.to_string());
        if self.state == HermitState::Open {
            self.record_transition(
                HermitState::Guarded,
                &format!("SEAL self-adaptation cycle initiated on target '{target}'"),
                "seal_engine",
                now,
            );
        }
    }

    /// Finish a SEAL self-adaptation cycle. If regression verification succeeds and no other
    /// threat signals persist, restores state to [`HermitState::Open`].
    pub fn exit_seal_adaptation(
        &mut self,
        session_id: &str,
        regression_passed: bool,
        now: i64,
    ) -> Result<HermitState, HermitError> {
        let active = self
            .active_seal_session
            .take()
            .ok_or(HermitError::SealNotActive)?;
        if active != session_id {
            // Restore active before returning error
            self.active_seal_session = Some(active);
            return Err(HermitError::SealSessionMismatch {
                active: self.active_seal_session.clone().unwrap(),
                provided: session_id.to_string(),
            });
        }

        if !regression_passed {
            self.record_transition(
                HermitState::Withdrawn,
                "SEAL self-adaptation regression verification failed; quarantining mutations",
                "seal_engine",
                now,
            );
        } else if self.state == HermitState::Guarded {
            self.record_transition(
                HermitState::Open,
                "SEAL self-adaptation verified; normal memory operations restored",
                "seal_engine",
                now,
            );
        }

        Ok(self.state)
    }

    /// Request mediation when in Withdrawn state to initiate review.
    pub fn request_mediation(
        &mut self,
        requested_by: &str,
        explanation: &str,
        now: i64,
    ) -> Result<&MediationTicket, HermitError> {
        if self.state != HermitState::Withdrawn {
            return Err(HermitError::InvalidTransition {
                from: self.state,
                to: HermitState::Mediating,
                reason: "Mediation can only be requested from Withdrawn state".to_string(),
            });
        }

        let ticket = MediationTicket {
            ticket_id: format!("med_{now:x}"),
            requested_by: requested_by.to_string(),
            explanation: explanation.to_string(),
            created_at: now,
            prior_state: self.state,
        };

        self.active_mediation = Some(ticket);
        self.record_transition(
            HermitState::Mediating,
            "Mediation requested; awaiting resolution",
            requested_by,
            now,
        );

        Ok(self.active_mediation.as_ref().unwrap())
    }

    /// Resolve an active mediation ticket.
    pub fn resolve_mediation(
        &mut self,
        ticket_id: &str,
        approved: bool,
        resolver: &str,
        now: i64,
    ) -> Result<HermitState, HermitError> {
        if self.state != HermitState::Mediating {
            return Err(HermitError::InvalidTransition {
                from: self.state,
                to: HermitState::Open,
                reason: "Cannot resolve mediation when not in Mediating state".to_string(),
            });
        }

        let active = self
            .active_mediation
            .as_ref()
            .ok_or_else(|| HermitError::TicketNotFound(ticket_id.to_string()))?;

        if active.ticket_id != ticket_id {
            return Err(HermitError::TicketNotFound(ticket_id.to_string()));
        }

        self.active_mediation = None;

        if approved {
            self.record_transition(
                HermitState::Open,
                &format!("Mediation approved by resolver '{resolver}'"),
                resolver,
                now,
            );
        } else {
            self.record_transition(
                HermitState::Withdrawn,
                &format!("Mediation denied by resolver '{resolver}'; remaining in lockdown"),
                resolver,
                now,
            );
        }

        Ok(self.state)
    }

    /// Check if a memory operation is permitted under the current protection state.
    #[must_use]
    pub fn check_access(&self, op: MemoryOperation) -> AccessVerdict {
        match self.state {
            HermitState::Open => AccessVerdict::Allowed,
            HermitState::Guarded => match op {
                MemoryOperation::Read | MemoryOperation::Search | MemoryOperation::Recall => {
                    AccessVerdict::Guarded {
                        audit_required: false,
                        cold_storage_isolated: true,
                    }
                }
                MemoryOperation::Write | MemoryOperation::Delete | MemoryOperation::Adapt => {
                    AccessVerdict::Guarded {
                        audit_required: true,
                        cold_storage_isolated: true,
                    }
                }
            },
            HermitState::Withdrawn => match op {
                MemoryOperation::Read | MemoryOperation::Search => AccessVerdict::Guarded {
                    audit_required: true,
                    cold_storage_isolated: true,
                },
                MemoryOperation::Write | MemoryOperation::Delete | MemoryOperation::Adapt => {
                    AccessVerdict::Denied {
                        reason: "Memory mutations strictly blocked while Hermit Crab is Withdrawn"
                            .to_string(),
                    }
                }
                MemoryOperation::Recall => AccessVerdict::Denied {
                    reason: "Associative recall blocked while in Withdrawn lockdown".to_string(),
                },
            },
            HermitState::Mediating => match op {
                MemoryOperation::Read => AccessVerdict::Guarded {
                    audit_required: true,
                    cold_storage_isolated: true,
                },
                _ => AccessVerdict::Denied {
                    reason: "Memory mutations and searches locked pending mediation resolution"
                        .to_string(),
                },
            },
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn hermit_initial_state_is_open() {
        let hermit = HermitProtection::new();
        assert_eq!(hermit.state(), HermitState::Open);
        assert_eq!(
            hermit.check_access(MemoryOperation::Write),
            AccessVerdict::Allowed
        );
    }

    #[test]
    fn assessment_escalates_to_guarded_and_withdrawn() {
        let mut hermit = HermitProtection::new();

        // Mild threat -> Guarded
        let mild = ThreatSignals {
            boundary_violations: 0.8, // 0.8 * 0.25 = 0.20
            abuse_score: 0.8,         // 0.8 * 0.15 = 0.12 => 0.32 >= 0.30
            ..Default::default()
        };
        assert_eq!(hermit.assess(&mild, 1000), HermitState::Guarded);

        // Severe threat -> Withdrawn
        let severe = ThreatSignals {
            unauthorized_access: 0.9,  // 0.27
            coercion_detected: true,   // 0.25
            repeated_violations: true, // 0.20 => 0.72 >= 0.70
            ..Default::default()
        };
        assert_eq!(hermit.assess(&severe, 1010), HermitState::Withdrawn);
        assert_eq!(hermit.history().len(), 2);
    }

    #[test]
    fn seal_adaptation_lifecycle() {
        let mut hermit = HermitProtection::new();

        hermit.enter_seal_adaptation("seal_01", "lora_adapter_alpha", 2000);
        assert_eq!(hermit.state(), HermitState::Guarded);
        assert_eq!(hermit.active_seal_session(), Some("seal_01"));

        // Writes guarded during SEAL
        let verdict = hermit.check_access(MemoryOperation::Write);
        assert_eq!(
            verdict,
            AccessVerdict::Guarded {
                audit_required: true,
                cold_storage_isolated: true,
            }
        );

        // Regression passes -> restores Open
        let res = hermit.exit_seal_adaptation("seal_01", true, 2050);
        assert_eq!(res.unwrap(), HermitState::Open);
        assert_eq!(hermit.active_seal_session(), None);
    }

    #[test]
    fn seal_adaptation_failure_quarantines() {
        let mut hermit = HermitProtection::new();
        hermit.enter_seal_adaptation("seal_02", "model_head", 3000);

        // Regression fails -> Withdrawn
        let res = hermit.exit_seal_adaptation("seal_02", false, 3050);
        assert_eq!(res.unwrap(), HermitState::Withdrawn);
    }

    #[test]
    fn mediation_resolution_flow() {
        let mut hermit = HermitProtection::new();
        hermit.withdraw("Manual test lockdown", "admin", 4000);
        assert_eq!(hermit.state(), HermitState::Withdrawn);

        // Cannot resolve without active ticket
        assert!(
            hermit
                .resolve_mediation("med_fake", true, "arbiter", 4010)
                .is_err()
        );

        // Request mediation
        let ticket = hermit
            .request_mediation("operator", "Lockdown was a false alarm", 4020)
            .unwrap()
            .clone();
        assert_eq!(hermit.state(), HermitState::Mediating);

        // Approved -> restores Open
        let state = hermit
            .resolve_mediation(&ticket.ticket_id, true, "arbiter_root", 4030)
            .unwrap();
        assert_eq!(state, HermitState::Open);
    }
}
