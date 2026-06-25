//! WhiteMagic Rust Cascade Bridge — JSON stdio server
//!
//! Reads JSON requests from stdin, writes JSON responses to stdout.
//! Usage: cargo run --example cascade_bridge --release
//!
//! Supported methods:
//!   - ping: {}
//!   - match_cascades: {"event": {"event_type": "joy_triggered", "confidence": 0.8, "cascade_depth": 0},
//!                       "triggers": [{"trigger_event": "joy_triggered", "target_events": ["love_activated"],
//!                                      "amplification": 1.2, "max_cascade_depth": 3}]}
//!   - detect_cycles: {"triggers": [...]}
//!   - is_safe: {"triggers": [...]}

use std::io::{self, BufRead, Write};
use wm_core::{CascadeEvent, CascadeTriggerDef, detect_cycles, is_safe, match_cascades};

fn main() {
    let stdin = io::stdin();
    let stdout = io::stdout();
    let mut stdout_lock = stdout.lock();

    for line in stdin.lock().lines() {
        let line = match line {
            Ok(l) if l.trim().is_empty() => continue,
            Ok(l) => l,
            Err(_) => break,
        };

        let response = match serde_json::from_str::<serde_json::Value>(&line) {
            Ok(req) => handle_request(req),
            Err(e) => json_error(&format!("Invalid JSON: {}", e)),
        };

        if writeln!(stdout_lock, "{}", response).is_err() {
            break;
        }
        let _ = stdout_lock.flush();
    }
}

fn handle_request(req: serde_json::Value) -> String {
    let method = req.get("method").and_then(|m| m.as_str()).unwrap_or("");
    let params = req.get("params").cloned().unwrap_or(serde_json::json!({}));

    match method {
        "ping" => json_ok(serde_json::json!({"backend": "rust-cascade"})),

        "match_cascades" => {
            let event_json = match params.get("event") {
                Some(e) => e,
                None => return json_error("Missing 'event' parameter"),
            };
            let event: CascadeEvent = match serde_json::from_value(event_json.clone()) {
                Ok(e) => e,
                Err(e) => return json_error(&format!("Invalid event: {}", e)),
            };

            let triggers_json = match params.get("triggers") {
                Some(t) => t,
                None => return json_error("Missing 'triggers' parameter"),
            };
            let triggers: Vec<CascadeTriggerDef> = match serde_json::from_value(triggers_json.clone()) {
                Ok(t) => t,
                Err(e) => return json_error(&format!("Invalid triggers: {}", e)),
            };

            let results = match_cascades(&event, &triggers);
            let json_results: Vec<serde_json::Value> = results
                .into_iter()
                .map(|r| {
                    serde_json::json!({
                        "event_type": r.event_type,
                        "confidence": r.confidence,
                        "cascade_depth": r.cascade_depth,
                        "origin": r.origin,
                    })
                })
                .collect();

            json_ok(serde_json::json!({"cascaded_events": json_results}))
        }

        "detect_cycles" => {
            let triggers_json = match params.get("triggers") {
                Some(t) => t,
                None => return json_error("Missing 'triggers' parameter"),
            };
            let triggers: Vec<CascadeTriggerDef> = match serde_json::from_value(triggers_json.clone()) {
                Ok(t) => t,
                Err(e) => return json_error(&format!("Invalid triggers: {}", e)),
            };

            let cycles = detect_cycles(&triggers);
            let json_cycles: Vec<serde_json::Value> = cycles
                .into_iter()
                .map(|c| {
                    serde_json::json!({"cycle": c})
                })
                .collect();

            json_ok(serde_json::json!({"cycles": json_cycles, "safe": json_cycles.is_empty()}))
        }

        "is_safe" => {
            let triggers_json = match params.get("triggers") {
                Some(t) => t,
                None => return json_error("Missing 'triggers' parameter"),
            };
            let triggers: Vec<CascadeTriggerDef> = match serde_json::from_value(triggers_json.clone()) {
                Ok(t) => t,
                Err(e) => return json_error(&format!("Invalid triggers: {}", e)),
            };

            let safe = is_safe(&triggers);
            json_ok(serde_json::json!({"safe": safe}))
        }

        _ => json_error(&format!("Unknown method: {}", method)),
    }
}

fn json_ok(result: serde_json::Value) -> String {
    serde_json::json!({"status": "ok", "result": result}).to_string()
}

fn json_error(msg: &str) -> String {
    serde_json::json!({"status": "error", "error": msg}).to_string()
}
