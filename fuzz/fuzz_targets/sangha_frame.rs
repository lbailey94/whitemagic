//! Fuzz target: Sangha mesh frame parsing — beacons and JSON-RPC envelopes.
//!
//! Invariant: arbitrary bytes must never panic. Parse failures are fine;
//! signature verification on a parsed frame must also never panic, including
//! with invalid or arbitrary public-key material.

#![no_main]

use libfuzzer_sys::fuzz_target;
use wm_sangha::transport::{PeerAnnounce, RpcRequest, RpcResponse};

fuzz_target!(|data: &[u8]| {
    // UDP beacon frame
    if let Some(announce) = PeerAnnounce::from_bytes(data) {
        let _ = announce.to_bytes();
        let _ = announce.verify_signature("00");
        let _ = announce.verify_signature(&announce.peer_id);
    }

    // JSON-RPC envelopes
    let _ = serde_json::from_slice::<RpcRequest>(data);
    let _ = serde_json::from_slice::<RpcResponse>(data);
    let lossy = String::from_utf8_lossy(data);
    let _ = serde_json::from_str::<RpcRequest>(&lossy);
    let _ = serde_json::from_str::<RpcResponse>(&lossy);
});
