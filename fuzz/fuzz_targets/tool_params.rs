#![no_main]

use libfuzzer_sys::fuzz_target;
use serde_json::Value;

fuzz_target!(|data: &[u8]| {
    // Fuzz JSON-RPC tool call parameters
    if let Ok(v) = serde_json::from_slice::<Value>(data) {
        // Ensure extracting string fields doesn't panic
        if let Some(params) = v.get("params") {
            if let Some(obj) = params.as_object() {
                for (key, val) in obj {
                    let _ = key.as_str();
                    if let Some(s) = val.as_str() {
                        // Check for injection patterns in parameter values
                        let _ = wm_core::security::is_description_safe(s);
                    }
                    if let Some(n) = val.as_f64() {
                        let _ = n.is_finite();
                    }
                }
            }
        }
    }
});
