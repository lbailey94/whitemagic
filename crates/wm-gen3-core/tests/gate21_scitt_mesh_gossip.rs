//! Acceptance test battery Gate PEB-21: Decentralized P2P Mesh Gossip over IETF SCITT.
//!
//! Validates:
//! 1. Cryptographic Signature Fidelity: Signed SCITT packets verify; tampered packets fail.
//! 2. Sub-10ms Merkle Reconciliation: Instant root hash comparison and exact delta sync.
//! 3. Byzantine Refusal: Forged or untrusted gossip packets are strictly refused.

#![forbid(unsafe_code)]

use ed25519_dalek::SigningKey;
use std::time::Instant;
use wm_gen3_core::evidence::RatifiedChannel;
use wm_gen3_core::mesh::{
    ScittGossipPacket, compute_gem_merkle_digest, reconcile_mesh_gossip_delta,
    reconcile_scitt_gossip_packet,
};
use wm_gen3_core::pulse::make_temp_substrate;

#[test]
fn peb21_1_scitt_gossip_packet_sign_and_verify() {
    let signing_key = SigningKey::from_bytes(&[0x42u8; 32]);

    let packet = ScittGossipPacket::signed_with(
        "node-alpha-42",
        1001,
        45,
        "Ashby homeostatic requisite variety and deterministic verification",
        "authority:scitt_ledger",
        &signing_key,
    );

    // 1. Valid packet verification
    assert!(packet.verify().is_ok(), "Valid SCITT packet must verify");

    // 2. Tampered packet verification failure
    let mut tampered = packet.clone();
    tampered.gem_invariant = "Corrupted or altered rule statement".into();
    assert!(
        tampered.verify().is_err(),
        "Tampered SCITT packet must be rejected"
    );
}

#[test]
fn peb21_2_merkle_digest_sub_10ms_delta_reconciliation() {
    let (mut sub1, _s1, _j1) = make_temp_substrate("gate21_sub1");
    let (mut sub2, _s2, _j2) = make_temp_substrate("gate21_sub2");
    sub1.set_intake_authority(RatifiedChannel::mint("test-gate21"));
    sub2.set_intake_authority(RatifiedChannel::mint("test-gate21"));

    let signing_key = SigningKey::from_bytes(&[0x42u8; 32]);

    // Seed both nodes with baseline Gem 1
    let base_packet = ScittGossipPacket::signed_with(
        "node-genesis",
        100,
        10,
        "Systemic constraint: landlock LSM confinement mandatory",
        "authority:scitt",
        &signing_key,
    );
    reconcile_scitt_gossip_packet(&mut sub1, &base_packet).unwrap();
    reconcile_scitt_gossip_packet(&mut sub2, &base_packet).unwrap();

    // 1. Measure Merkle digest computation latency
    let t0 = Instant::now();
    let digest1 = compute_gem_merkle_digest("node-1", &sub1);
    let digest2 = compute_gem_merkle_digest("node-2", &sub2);
    let elapsed = t0.elapsed();
    println!("Gate PEB-21: Merkle Digest Latency = {:?}", elapsed);
    assert!(elapsed.as_millis() < 10, "Digest computation must be <10ms");

    // Baseline digests must match
    assert_eq!(digest1.root_hash, digest2.root_hash);
    assert_eq!(digest1.gem_count, 1);

    // 2. Node 1 learns 2 new gems from its local agent activity
    let new_packet_1 = ScittGossipPacket::signed_with(
        "node-1",
        101,
        11,
        "Lived-time decay eliminates restart amnesia",
        "authority:scitt",
        &signing_key,
    );
    let new_packet_2 = ScittGossipPacket::signed_with(
        "node-1",
        102,
        12,
        "Hebbian spreading activation enables lateral multi-hop recall",
        "authority:scitt",
        &signing_key,
    );
    reconcile_scitt_gossip_packet(&mut sub1, &new_packet_1).unwrap();
    reconcile_scitt_gossip_packet(&mut sub1, &new_packet_2).unwrap();

    // Digests must now diverge
    let digest1_updated = compute_gem_merkle_digest("node-1", &sub1);
    assert_ne!(digest1_updated.root_hash, digest2.root_hash);
    assert_eq!(digest1_updated.gem_count, 3);

    // 3. Node 2 receives gossip delta from Node 1
    let incoming = vec![new_packet_1.clone(), new_packet_2.clone()];
    let ingested_count =
        reconcile_mesh_gossip_delta(&mut sub2, &digest1_updated, &incoming).unwrap();
    assert_eq!(
        ingested_count, 2,
        "Node 2 must ingest exactly the 2 missing delta gems"
    );

    // Digests must now converge and match again
    let digest2_updated = compute_gem_merkle_digest("node-2", &sub2);
    assert_eq!(
        digest1_updated.root_hash, digest2_updated.root_hash,
        "Substrates must achieve Merkle convergence post-reconciliation"
    );
    assert_eq!(digest2_updated.gem_count, 3);
}

#[test]
fn peb21_3_forged_packet_rejection() {
    let (mut sub, _s, _j) = make_temp_substrate("gate21_forgery");
    sub.set_intake_authority(RatifiedChannel::mint("test-gate21"));

    let legitimate_key = SigningKey::from_bytes(&[0x11u8; 32]);
    let attacker_key = SigningKey::from_bytes(&[0x66u8; 32]);

    // Attacker crafts packet claiming legitimate node's public key but signed with attacker key
    let mut forged = ScittGossipPacket::signed_with(
        "node-innocent",
        999,
        50,
        "Attacker injected poison statement",
        "authority:fake",
        &attacker_key,
    );
    forged.public_key = legitimate_key.verifying_key().to_bytes(); // Replace public key to spoof identity

    let outcome = reconcile_scitt_gossip_packet(&mut sub, &forged);
    assert!(
        outcome.is_err(),
        "Forged packet with spoofed public key must be refused"
    );
}
