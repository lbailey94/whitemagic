//! Fuzz target: JSON-RPC parsing — feed arbitrary bytes as JSON-RPC requests.
//!
//! Invariant: Parsing arbitrary bytes must never panic. Valid JSON with
//! unexpected structure should produce a parse error, not a crash.

#![no_main]

use libfuzzer_sys::fuzz_target;
use serde::Deserialize;

#[derive(Debug, Deserialize)]
struct RpcRequest {
    #[allow(dead_code)]
    jsonrpc: String,
    #[serde(default)]
    #[allow(dead_code)]
    id: Option<serde_json::Value>,
    method: String,
    #[serde(default)]
    #[allow(dead_code)]
    params: serde_json::Value,
}

fuzz_target!(|data: &[u8]| {
    // Try parsing as JSON — must never panic
    let _ = serde_json::from_slice::<RpcRequest>(data);

    // Also try as a string (lossy UTF-8)
    let lossy = String::from_utf8_lossy(data);
    let _ = serde_json::from_str::<RpcRequest>(&lossy);

    // Try parsing as a generic JSON value first, then as RpcRequest
    if let Ok(value) = serde_json::from_slice::<serde_json::Value>(data) {
        // If it's a valid JSON value, try to interpret it as a request
        let json_str = serde_json::to_string(&value).unwrap_or_default();
        let _ = serde_json::from_str::<RpcRequest>(&json_str);
    }
});
