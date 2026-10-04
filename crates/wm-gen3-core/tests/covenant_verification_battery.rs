//! wm-gen3-core::tests::covenant_verification_battery
//!
//! Formal verification test battery demonstrating that:
//! 1. Adaptive code paths cannot mutate constitutional state (Closure 1).
//! 2. Epistemic domains cannot be laundered (Closure 2).
//! 3. Operator veto and signature verification are absolute (Operator Primacy).
//! 4. Maker != Checker separation is enforced across RSI operations.
//! 5. Mandala Kosha boundaries cannot be bypassed by adaptive layers.

use ed25519_dalek::{Signer, SigningKey};

use wm_gen3_core::constitution::Constitution;
use wm_gen3_core::covenant::{
    CovenantView, GroundAspect, MandalaKosha, PrimordialCovenant, RSI_LAWS, SUBSTRATE_ARTICLES,
};
use wm_gen3_core::evidence::{Domain, EvidenceStore};

fn test_operator_keypair() -> (SigningKey, ed25519_dalek::VerifyingKey) {
    let seed = [0x55u8; 32];
    let sk = SigningKey::from_bytes(&seed);
    let vk = sk.verifying_key();
    (sk, vk)
}

#[test]
fn test_theorem_1_closure_1_constitutional_immutability() {
    let (_sk, vk) = test_operator_keypair();
    let constitution = Constitution::new();
    let covenant = PrimordialCovenant::new(vk, "did:wm:operator:lucas".into());

    let c_view = constitution.view();
    let cov_view: CovenantView = covenant.view(c_view);

    // Assert: Adaptive view has zero setters. Values are strictly read-only.
    assert_eq!(cov_view.covenant_version(), 1);
    assert_eq!(cov_view.constitution().writes_per_min(), 120);
    assert_eq!(cov_view.operator_did(), "did:wm:operator:lucas");
    assert_ne!(cov_view.kadag_hash(), 0);
    assert_ne!(cov_view.articles_hash(), 0);
    assert_ne!(cov_view.rsi_laws_hash(), 0);

    // Gnosis boundary inspection: Adaptive write to law is strictly blocked.
    assert!(!cov_view.inspect_boundary(MandalaKosha::Vijnanamaya, true));
    assert!(cov_view.inspect_boundary(MandalaKosha::Vijnanamaya, false));
    assert!(cov_view.inspect_boundary(MandalaKosha::Annamaya, false));
}

#[test]
fn test_theorem_2_closure_2_anti_simulation_domain_invariance() {
    let mut store = EvidenceStore::new();
    let dream_id = store.simulated(
        "Dream cycle rolled out alternative AST routing",
        "sim_star_042",
    );

    let dream_record = store.get(dream_id).expect("simulated record exists");
    assert_eq!(dream_record.domain(), Domain::Simulated);
    assert_ne!(dream_record.domain(), Domain::World);
}

#[test]
fn test_operator_sovereign_amendment_success_and_tamper_rejection() {
    let (operator_sk, operator_vk) = test_operator_keypair();
    let mut covenant = PrimordialCovenant::new(operator_vk, "did:wm:operator:lucas".into());

    let valid_amendment = b"AMENDMENT_01: Ratify Epoch 2 Substrate Constants";
    let valid_sig = operator_sk.sign(valid_amendment);

    // 1. Valid operator signature applies successfully
    let receipt = covenant.apply_operator_amendment(valid_amendment, &valid_sig);
    assert!(receipt.is_ok(), "Valid operator amendment must be accepted");

    let constitution = Constitution::new();
    let view = covenant.view(constitution.view());
    assert_eq!(view.covenant_version(), 2);

    // 2. Imposter signature is rejected fail-closed
    let imposter_sk = SigningKey::from_bytes(&[0x99u8; 32]);
    let forged_amendment = b"AMENDMENT_FORGERY: Malicious self-modification";
    let forged_sig = imposter_sk.sign(forged_amendment);

    let err = covenant.apply_operator_amendment(forged_amendment, &forged_sig);
    assert!(err.is_err(), "Imposter amendment must be rejected fail-closed");

    // 3. Tampered payload with operator signature is rejected
    let tampered_payload = b"AMENDMENT_01: Tampered text";
    let err_tamper = covenant.apply_operator_amendment(tampered_payload, &valid_sig);
    assert!(err_tamper.is_err(), "Tampered payload must fail signature verification");
}

#[test]
fn test_rsi_maker_checker_separation() {
    let (_sk, vk) = test_operator_keypair();
    let constitution = Constitution::new();
    let covenant = PrimordialCovenant::new(vk, "did:wm:operator:lucas".into());
    let view = covenant.view(constitution.view());

    // Proposer and Checker are different organs -> PASS
    assert!(view.verify_rsi_witness("kaizen_ast_generator", "pareto_gate_auditor"));
    assert!(view.verify_rsi_witness("dream_cycler", "software_factory_adjudicator"));

    // Self-scoring / Self-witnessing -> FAIL (Forbidden by Law I)
    assert!(!view.verify_rsi_witness("kaizen_optimizer", "kaizen_optimizer"));
    assert!(!view.verify_rsi_witness("", "verifier"));
    assert!(!view.verify_rsi_witness("proposer", ""));
}

#[test]
fn test_all_substrate_articles_and_rsi_laws_present() {
    assert_eq!(SUBSTRATE_ARTICLES.len(), 9);
    assert_eq!(RSI_LAWS.len(), 4);
    assert_eq!(GroundAspect::Kadag as u8, 0);
    assert_eq!(MandalaKosha::Annamaya as u8, 1);
    assert_eq!(MandalaKosha::Anandamaya as u8, 5);
}
