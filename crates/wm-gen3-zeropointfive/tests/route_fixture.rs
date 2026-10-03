//! Route-catalog regression fixtures.
//!
//! Validates the Rust System 0.5 organ against the recovered 80-intent route
//! set. Ignored by default; run with:
//!
//! ```sh
//! WM_GEN3_SYSTEM05_MODEL=~/.local/share/whitemagic/system05/potion-base-32M \
//! WM_SYSTEM05_INTENTS=/tmp/opencode/route_eval/route-eval/intents.jsonl \
//! WM_SYSTEM05_ROUTES=/home/lucas/SharedWorkspace/uploads/miranda-macbook/v9_curated_routes.json \
//! WM_SYSTEM05_ENRICHED_ROUTES=../catalogs/routes_v9_enriched.json \
//! cargo test -p wm-gen3-zeropointfive --test route_fixture -- --ignored --nocapture
//! ```
//!
//! Python baselines (potion-32M, same harness): baseline catalog top-1 0.438 /
//! R@16 0.838; enriched catalog top-1 0.800 / R@16 1.000.

use std::collections::BTreeMap;
use std::path::PathBuf;

use serde_json::{Value, json};
use wm_gen3_zeropointfive::System05;

const GOLD_MAP: &[(&str, &str)] = &[
    ("remember", "memory.create"),
    ("recall", "memory.search"),
    ("session_checkpoint", "session.checkpoint"),
    ("session_continuity", "session.continuity"),
    ("session_record", "session.record"),
    ("status", "gnosis.status"),
    ("inspect", "gnosis.explain"),
    ("ingest", "memory.ingest"),
];

const OVERRIDES: &[(&str, &str)] = &[
    ("memory.create", "Store a new memory or fact."),
    ("memory.search", "Retrieve memories by query."),
    (
        "session.checkpoint",
        "Save a session handoff or checkpoint.",
    ),
    (
        "session.continuity",
        "Resume or review the previous session.",
    ),
    (
        "session.record",
        "Record a turn or event in the current session.",
    ),
    ("gnosis.status", "Show system or store status and counts."),
    (
        "gnosis.explain",
        "Explain why a memory or route was selected.",
    ),
    (
        "memory.ingest",
        "Import documents, transcripts, or events from a directory.",
    ),
];

fn env_path(name: &str) -> Option<PathBuf> {
    std::env::var(name)
        .ok()
        .filter(|v| !v.is_empty())
        .map(PathBuf::from)
}

fn load_intents(path: &PathBuf) -> Vec<(String, String)> {
    let gold_map: BTreeMap<&str, &str> = GOLD_MAP.iter().copied().collect();
    let mut intents = Vec::new();
    for line in std::fs::read_to_string(path)
        .expect("intents readable")
        .lines()
    {
        if line.trim().is_empty() {
            continue;
        }
        let row: Value = serde_json::from_str(line).expect("intent parses");
        let gold = row["gold"].as_str().unwrap_or_default();
        if let Some(mapped) = gold_map.get(gold) {
            intents.push((
                row["text"].as_str().unwrap_or_default().to_string(),
                mapped.to_string(),
            ));
        }
    }
    intents
}

fn baseline_catalog(path: &PathBuf) -> Value {
    let raw: BTreeMap<String, String> =
        serde_json::from_str(&std::fs::read_to_string(path).expect("routes readable"))
            .expect("routes parse");
    let overrides: BTreeMap<&str, &str> = OVERRIDES.iter().copied().collect();
    let mut routes = serde_json::Map::new();
    for (name, description) in &raw {
        let one = overrides
            .get(name.as_str())
            .map(|value| value.to_string())
            .unwrap_or_else(|| {
                description
                    .split(". ")
                    .next()
                    .unwrap_or(name)
                    .trim()
                    .chars()
                    .take(90)
                    .collect()
            });
        routes.insert(name.clone(), json!(one));
    }
    Value::Object(routes)
}

fn evaluate(organ: &System05, routes: &Value, intents: &[(String, String)]) -> (f64, f64, f64) {
    let mut top1_hits = 0usize;
    let mut recall_hits = 0usize;
    let started = std::time::Instant::now();
    for (text, gold) in intents {
        let outcome = organ
            .shortlist(text, routes, 16)
            .expect("shortlist succeeds");
        let ranked: Vec<String> = outcome["ranked"]
            .as_array()
            .expect("ranked array")
            .iter()
            .map(|entry| entry["route"].as_str().unwrap_or_default().to_string())
            .collect();
        if ranked.first().map(String::as_str) == Some(gold.as_str()) {
            top1_hits += 1;
        }
        if ranked.iter().any(|route| route == gold) {
            recall_hits += 1;
        }
    }
    let elapsed = started.elapsed().as_secs_f64();
    (
        top1_hits as f64 / intents.len() as f64,
        recall_hits as f64 / intents.len() as f64,
        elapsed,
    )
}

#[test]
#[ignore = "requires WM_GEN3_SYSTEM05_MODEL, WM_SYSTEM05_INTENTS, WM_SYSTEM05_ROUTES"]
fn route_fixture_baseline() {
    let Some(model_dir) = env_path("WM_GEN3_SYSTEM05_MODEL") else {
        eprintln!("WM_GEN3_SYSTEM05_MODEL not set; skipping");
        return;
    };
    let Some(intents_path) = env_path("WM_SYSTEM05_INTENTS") else {
        eprintln!("WM_SYSTEM05_INTENTS not set; skipping");
        return;
    };
    let Some(routes_path) = env_path("WM_SYSTEM05_ROUTES") else {
        eprintln!("WM_SYSTEM05_ROUTES not set; skipping");
        return;
    };

    let routes = baseline_catalog(&routes_path);
    let intents = load_intents(&intents_path);
    let organ = System05::new(model_dir);
    let (top1, recall16, elapsed) = evaluate(&organ, &routes, &intents);
    eprintln!(
        "baseline: intents={} top1={top1:.3} R@16={recall16:.3} total={elapsed:.2}s",
        intents.len()
    );
    assert!(
        top1 >= 0.42,
        "baseline top1 {top1:.3} below 0.42 (Python 0.438)"
    );
    assert!(
        recall16 >= 0.82,
        "baseline R@16 {recall16:.3} below 0.82 (Python 0.838)"
    );
}

#[test]
#[ignore = "requires WM_GEN3_SYSTEM05_MODEL, WM_SYSTEM05_INTENTS, WM_SYSTEM05_ENRICHED_ROUTES"]
fn route_fixture_enriched() {
    let Some(model_dir) = env_path("WM_GEN3_SYSTEM05_MODEL") else {
        eprintln!("WM_GEN3_SYSTEM05_MODEL not set; skipping");
        return;
    };
    let Some(intents_path) = env_path("WM_SYSTEM05_INTENTS") else {
        eprintln!("WM_SYSTEM05_INTENTS not set; skipping");
        return;
    };
    let Some(enriched_path) = env_path("WM_SYSTEM05_ENRICHED_ROUTES") else {
        eprintln!("WM_SYSTEM05_ENRICHED_ROUTES not set; skipping");
        return;
    };

    let routes: Value =
        serde_json::from_str(&std::fs::read_to_string(&enriched_path).expect("catalog readable"))
            .expect("catalog parses");
    let intents = load_intents(&intents_path);
    let organ = System05::new(model_dir);
    let (top1, recall16, elapsed) = evaluate(&organ, &routes, &intents);
    eprintln!(
        "enriched: intents={} top1={top1:.3} R@16={recall16:.3} total={elapsed:.2}s ({:.1} ms/intent)",
        intents.len(),
        elapsed * 1000.0 / intents.len() as f64
    );
    assert!(
        top1 >= 0.75,
        "enriched top1 {top1:.3} below 0.75 (Python 0.800)"
    );
    assert!(
        recall16 >= 0.95,
        "enriched R@16 {recall16:.3} below 0.95 (Python 1.000)"
    );
}
