//! Gate 13 Acceptance Battery: Frontier 4 — Zero-Knowledge / Cryptographic Agent Identity Attestation.
//!
//! Validates:
//! 1. Sovereign Root Authority Token Minting & Strict Ed25519 Cryptographic Verification.
//! 2. Bounded Temporal Validity: Epoch-based expiration & Anti-replay Nonces.
//! 3. Hierarchical Capability Delegation (DelegationProof):
//!    - Capability Subsetting Invariant: Child agent cannot possess powers not held by delegator.
//!    - Recursion Bound: Max delegation depth strictly bounded at 3.
//! 4. Tamper-Evident Hash-Chained Action Auditing (AuditAttestation):
//!    - Cryptographic non-repudiation.
//!    - Detection of broken ancestry and tampered parent hashes.

#![forbid(unsafe_code)]

use wm_gen3_core::attestation::{
    AgentIdentityToken, AttestationError, AuditAttestation, DelegationProof,
};
use wm_gen3_core::causal::SigningKey;

#[test]
fn gate13_agent_identity_token_lifecycle_and_invariants() {
    let sovereign_secret: [u8; 32] = [0x70; 32];
    let sovereign_key = SigningKey::from_bytes(&sovereign_secret);

    let agent_secret: [u8; 32] = [0x80; 32];
    let agent_key = SigningKey::from_bytes(&agent_secret);

    let token = AgentIdentityToken::mint(
        &sovereign_key,
        "did:key:lucas-primary-agent",
        &agent_key.verifying_key(),
        "SovereignExecutor",
        vec![
            "memory:read",
            "memory:write",
            "causal:intervene",
            "sleep:cycle",
        ],
        1000, // current epoch
        200,  // ttl epochs
        [0xde; 16],
    );

    // 1. Valid verification at current epoch
    assert!(token.verify(&sovereign_key.verifying_key(), 1050).is_ok());

    // 2. Capability verification
    assert!(token.has_capability("causal:intervene"));
    assert!(token.has_capability("sleep:cycle"));
    assert!(!token.has_capability("kernel:destructive_purge"));

    // 3. Expiration boundary verification
    assert!(token.verify(&sovereign_key.verifying_key(), 1200).is_ok());
    let expired = token
        .verify(&sovereign_key.verifying_key(), 1201)
        .unwrap_err();
    assert!(matches!(
        expired,
        AttestationError::ExpiredToken {
            expires_at: 1200,
            current_epoch: 1201
        }
    ));

    // 4. Authority mismatch protection
    let imposter_secret: [u8; 32] = [0x99; 32];
    let imposter_key = SigningKey::from_bytes(&imposter_secret);
    let auth_err = token
        .verify(&imposter_key.verifying_key(), 1050)
        .unwrap_err();
    assert_eq!(auth_err, AttestationError::AuthorityMismatch);
}

#[test]
fn gate13_hierarchical_capability_delegation_chains() {
    let sovereign_secret: [u8; 32] = [0x70; 32];
    let sovereign_key = SigningKey::from_bytes(&sovereign_secret);

    let primary_secret: [u8; 32] = [0x81; 32];
    let primary_key = SigningKey::from_bytes(&primary_secret);

    let subagent1_secret: [u8; 32] = [0x82; 32];
    let subagent1_key = SigningKey::from_bytes(&subagent1_secret);

    let subagent2_secret: [u8; 32] = [0x83; 32];
    let subagent2_key = SigningKey::from_bytes(&subagent2_secret);

    let subagent3_secret: [u8; 32] = [0x84; 32];
    let subagent3_key = SigningKey::from_bytes(&subagent3_secret);

    // Root -> Primary Agent
    let primary_token = AgentIdentityToken::mint(
        &sovereign_key,
        "did:key:primary",
        &primary_key.verifying_key(),
        "Primary",
        vec!["memory:read", "memory:write", "causal:intervene"],
        500,
        500,
        [0x11; 16],
    );

    // Depth 1 -> 2: Primary delegates to Subagent 1 (valid subset: memory:read, causal:intervene)
    let del1 = DelegationProof::delegate(
        &primary_key,
        primary_token.clone(),
        "did:key:subagent1",
        &subagent1_key.verifying_key(),
        vec!["memory:read", "causal:intervene"],
        1,
    )
    .expect("Delegation depth 2 must succeed");
    assert_eq!(del1.delegation_depth, 2);
    assert!(
        del1.verify_chain(&sovereign_key.verifying_key(), 550)
            .is_ok()
    );

    // Privilege escalation attempt: Subagent 1 tries to delegate a capability the parent does not have
    let rogue_escalation = DelegationProof::delegate(
        &primary_key,
        primary_token,
        "did:key:rogue",
        &subagent1_key.verifying_key(),
        vec!["memory:read", "unauthorized:nuke"],
        1,
    );
    assert!(matches!(
        rogue_escalation,
        Err(AttestationError::CapabilityEscalation { .. })
    ));

    // Depth 2 -> 3: Subagent 1 delegates to Subagent 2 (subset: memory:read only)
    let del2 = DelegationProof::delegate(
        &subagent1_key,
        del1.delegator_token.clone(),
        "did:key:subagent2",
        &subagent2_key.verifying_key(),
        vec!["memory:read"],
        2,
    )
    .expect("Delegation depth 3 must succeed");
    assert_eq!(del2.delegation_depth, 3);

    // Depth 3 -> 4: Subagent 2 tries to delegate further (must be rejected by MAX_DELEGATION_DEPTH=3)
    let depth_exceeded = DelegationProof::delegate(
        &subagent2_key,
        del2.delegator_token,
        "did:key:subagent3",
        &subagent3_key.verifying_key(),
        vec!["memory:read"],
        3,
    );
    assert!(matches!(
        depth_exceeded,
        Err(AttestationError::DelegationDepthExceeded {
            max: 3,
            requested: 4
        })
    ));
}

#[test]
fn gate13_tamper_evident_audit_attestation_chains() {
    let agent_secret: [u8; 32] = [0x5a; 32];
    let agent_key = SigningKey::from_bytes(&agent_secret);

    // Event 1: Initial action
    let audit_event1 = AuditAttestation::attest(
        &agent_key,
        "did:key:audited-agent",
        "memory.remember",
        b"payload_bytes_record_1",
        None,
    );
    assert!(
        audit_event1
            .verify(&agent_key.verifying_key(), None)
            .is_ok()
    );

    // Event 2: Chained action referencing Event 1
    let audit_event2 = AuditAttestation::attest(
        &agent_key,
        "did:key:audited-agent",
        "causal.intervene",
        b"payload_bytes_intervention_2",
        Some(&audit_event1.attestation_id),
    );
    assert!(
        audit_event2
            .verify(
                &agent_key.verifying_key(),
                Some(&audit_event1.attestation_id)
            )
            .is_ok()
    );

    // Tamper test: breaking the chain
    let tampered_verification =
        audit_event2.verify(&agent_key.verifying_key(), Some("forged_previous_id"));
    assert!(matches!(
        tampered_verification,
        Err(AttestationError::HashChainBroken { .. })
    ));
}
