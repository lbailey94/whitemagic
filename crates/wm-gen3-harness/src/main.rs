//! Phase-1 adapter: stdio JSON-RPC surface over the minimal substrate.
//!
//! Plumbing only (`docs/PHASE1_EXPERIMENT_INTERFACE.md`): it maps the harness's
//! `wm`-router calls onto the four operations and emits MCP-shaped responses. It
//! implements no selection behavior.
//!
//! Gate 9A Slice 1 compatibility (ratified D4): batch ingest no longer triggers
//! an automatic sweep. Callers request a sweep explicitly via `gen3.think_sweep`
//! and replay committed sweeps via `gen3.sweep_replay`.
//!
//! Accepted (and mostly ignored) control-arm flags: `serve --store <dir>
//! --profile <name> --max-requests <n> --rate-limit <n>`. The journal path comes
//! from `WM_GEN3_JOURNAL` (fallback: `<store>/journal.jsonl`, ephemeral).

use std::io::{BufRead, Write};
use std::path::Path;

use serde_json::{Value, json};
use wm_gen3_core::constitution::default_view;
use wm_gen3_core::evidence::RatifiedChannel;
use wm_gen3_core::intake::{CommitDisposition, IntakeKind, IntakeRequest, OperationId};
use wm_gen3_core::ops::{ImportKind, RecallQuery, RememberItem, Substrate};

fn arg_value(args: &[String], name: &str) -> Option<String> {
    args.iter()
        .position(|a| a == name)
        .and_then(|i| args.get(i + 1))
        .cloned()
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let store = arg_value(&args, "--store").unwrap_or_else(|| "gen3-store".to_string());
    let journal = std::env::var("WM_GEN3_JOURNAL").ok();
    let journal_path = journal
        .clone()
        .unwrap_or_else(|| format!("{store}/journal.jsonl"));

    let mut substrate = {
        let readonly = args.iter().any(|a| a == "--readonly");
        let opened = if readonly {
            Substrate::open_readonly(
                Path::new(&store),
                Some(Path::new(&journal_path)),
                default_view(),
            )
        } else {
            Substrate::open(
                Path::new(&store),
                Some(Path::new(&journal_path)),
                default_view(),
            )
        };
        match opened {
            Ok(s) => s,
            Err(e) => {
                eprintln!("gen3: cannot open substrate at {store}: {e}");
                std::process::exit(1);
            }
        }
    };
    let readonly_mode = substrate.store().is_readonly();
    let intake_authority = RatifiedChannel::mint("wm-gen3-harness");
    substrate.set_intake_authority(RatifiedChannel::mint("wm-gen3-harness"));
    let sweep_enabled = std::env::var("WM_GEN3_SWEEP")
        .map(|v| v != "0")
        .unwrap_or(true);
    substrate.set_sweep_enabled(sweep_enabled);
    let projection_on = std::env::var("WM_GEN3_PROJECTION")
        .map(|v| v == "1")
        .unwrap_or(false);
    if projection_on {
        let cache_dir = std::env::var("WM_GEN3_EMBED_CACHE").ok();
        if let Err(e) = substrate.set_projection_enabled(true, cache_dir.as_deref().map(Path::new))
        {
            eprintln!("gen3: projection enable failed: {e}");
            std::process::exit(1);
        }
    }
    let gated_env = std::env::var("WM_GEN3_PROJECTION_GATED").unwrap_or_default();
    let (projection_gated, projection_gate_count) = match gated_env.as_str() {
        "1" | "true" => (true, false),
        "count" => (false, true),
        _ => (false, false),
    };
    substrate.set_projection_gated(projection_gated);
    substrate.set_projection_gate_count(projection_gate_count);
    if std::env::var("WM_GEN3_ARBITRATION")
        .map(|v| v == "structural")
        .unwrap_or(false)
    {
        substrate.set_arbitration(wm_gen3_core::ops::Arbitration::Structural);
    }
    let dispersion_on = std::env::var("WM_GEN3_DISPERSION")
        .map(|v| v == "1")
        .unwrap_or(false);
    substrate.set_dispersion(dispersion_on);
    let noise_enabled = std::env::var("WM_GEN3_NOISE")
        .map(|v| v != "0")
        .unwrap_or(true);
    substrate.set_noise_enabled(noise_enabled);
    let gate_label = if projection_gate_count {
        "count"
    } else if projection_gated {
        "floor"
    } else {
        "off"
    };
    eprintln!(
        "gen3: serve store={store} journal={journal_path} mode={} budget={} sweep={} projection={} gate={} arbitration={:?}",
        if readonly_mode {
            "readonly"
        } else {
            "readwrite"
        },
        substrate.budget(),
        if sweep_enabled { "on" } else { "off" },
        if projection_on { "on" } else { "off" },
        gate_label,
        substrate.arbitration()
    );
    eprintln!(
        "gen3: dispersion={} noise={}",
        if dispersion_on { "on" } else { "off" },
        if noise_enabled { "on" } else { "off" }
    );

    let stdin = std::io::stdin();
    let mut stdout = std::io::stdout();
    for line in stdin.lock().lines() {
        let Ok(line) = line else { break };
        let line = line.trim();
        if line.is_empty() {
            continue;
        }
        let Ok(request) = serde_json::from_str::<Value>(line) else {
            eprintln!("gen3: malformed request line ignored (harness treats stdout only)");
            continue;
        };
        let id = request.get("id").cloned().unwrap_or(Value::Null);
        let method = request.get("method").and_then(Value::as_str).unwrap_or("");
        match method {
            "initialize" => {
                respond(
                    &mut stdout,
                    &id,
                    &json!({ "protocolVersion": "gen3-0.1", "capabilities": {} }),
                );
            }
            "tools/call" => {
                let name = request
                    .pointer("/params/name")
                    .and_then(Value::as_str)
                    .unwrap_or("");
                if name != "wm" {
                    rpc_error(&mut stdout, &id, -32601, "only the wm router is exposed");
                    continue;
                }
                let route = request
                    .pointer("/params/arguments/route")
                    .and_then(Value::as_str)
                    .unwrap_or("");
                let args = request
                    .pointer("/params/arguments/args")
                    .cloned()
                    .unwrap_or_else(|| json!({}));
                let payload = handle_route(
                    &mut substrate,
                    &intake_authority,
                    route,
                    &args,
                    readonly_mode,
                );
                match payload {
                    Some(p) => respond(&mut stdout, &id, &p),
                    None => rpc_error(&mut stdout, &id, -32601, &format!("unknown route: {route}")),
                }
            }
            _ => rpc_error(
                &mut stdout,
                &id,
                -32601,
                &format!("unknown method: {method}"),
            ),
        }
    }

    substrate.finish();
    if let Ok(hash_out) = std::env::var("WM_GEN3_JOURNAL_HASH_OUT")
        && let Ok(hash) = wm_gen3_core::journal::sha256_file(Path::new(&journal_path))
    {
        let _ = std::fs::write(hash_out, hash);
    }
}

fn handle_route(
    substrate: &mut Substrate,
    intake_authority: &RatifiedChannel,
    route: &str,
    args: &Value,
    readonly: bool,
) -> Option<Value> {
    if readonly
        && matches!(
            route,
            "memory.batch_create"
                | "memory.intake_authorized"
                | "gen3.canary"
                | "gen3.think_sweep"
                | "sandbox.set_limits"
        )
    {
        return Some(json!({
            "status": "error",
            "route": route,
            "error": "read-only mode: write route refused",
        }));
    }
    match route {
        "sandbox.set_limits" => {
            if let Some(limit) = args.get("max_writes_per_minute").and_then(Value::as_u64) {
                if limit > u32::MAX as u64 {
                    return Some(json!({
                        "status": "error",
                        "route": route,
                        "error": "max_writes_per_minute out of range (fail-closed)",
                        "field": "max_writes_per_minute",
                        "value": limit,
                        "max": u32::MAX,
                    }));
                }
                substrate.set_budget(limit as u32);
            }
            Some(json!({
                "status": "success",
                "limits": { "max_writes_per_minute": substrate.budget() },
            }))
        }
        "memory.batch_create" => {
            let items = args
                .get("items")
                .and_then(Value::as_array)
                .cloned()
                .unwrap_or_default();
            let remember: Vec<RememberItem> = items
                .iter()
                .map(|item| {
                    let content = item
                        .get("content")
                        .and_then(Value::as_str)
                        .unwrap_or("")
                        .to_string();
                    let galaxy = item
                        .get("galaxy")
                        .and_then(Value::as_str)
                        .unwrap_or("codex");
                    let tags = item
                        .get("tags")
                        .and_then(Value::as_array)
                        .map(|t| {
                            t.iter()
                                .filter_map(Value::as_str)
                                .collect::<Vec<_>>()
                                .join(",")
                        })
                        .unwrap_or_default();
                    RememberItem {
                        content,
                        source: format!("corpus:{galaxy}:{tags}"),
                        kind: ImportKind::Reported,
                    }
                })
                .collect();
            let results = substrate.remember_batch(&remember);
            let errors: Vec<String> = results
                .iter()
                .filter_map(|r| r.as_ref().err().cloned())
                .collect();
            let ids: Vec<u64> = results
                .iter()
                .filter_map(|r| r.as_ref().ok().copied())
                .collect();
            if !errors.is_empty() {
                return Some(json!({
                    "status": "error",
                    "failed": errors.len(),
                    "errors": errors,
                    "ids": ids,
                }));
            }
            Some(json!({
                "status": "success",
                "ids": ids,
                "count": remember.len(),
                "sweep": {
                    "status": "not_requested",
                    "note": "batch ingest no longer triggers an automatic sweep (Gate 9A D4); call gen3.think_sweep explicitly",
                },
            }))
        }
        "gen3.think_sweep" => {
            let stats = substrate.think_sweep();
            Some(json!({
                "status": if stats.refused { "refused" } else if stats.disabled { "disabled" } else { "success" },
                "sweep": stats.sweep,
                "disabled": stats.disabled,
                "refused": stats.refused,
                "replayed": stats.replayed,
                "operation_id": stats.operation_id.map(|id| hex_bytes(id.as_bytes())),
                "error": stats.error,
                "pairs_lexical_candidates": stats.pairs_lexical_candidates,
                "pairs_considered": stats.pairs_considered,
                "pairs_examined": stats.pairs_examined,
                "pairs_skipped_existing": stats.pairs_skipped_existing,
                "pairs_rejected_rule": stats.pairs_rejected_rule,
                "proposals": stats.proposals,
                "promotions": stats.promotions,
                "demotions": stats.demotions,
                "rare_max_df": stats.rare_max_df,
                "took_ms": stats.took_ms,
            }))
        }
        "gen3.sweep_replay" => {
            let operation_id = match args
                .get("operation_id")
                .and_then(Value::as_str)
                .and_then(parse_operation_id)
            {
                Some(value) => value,
                None => {
                    return Some(json!({
                        "status":"error",
                        "error":"operation_id must be exactly 32 hexadecimal characters"
                    }));
                }
            };
            match substrate.sweep_replay(operation_id) {
                Ok(outcome) => Some(json!({
                    "status": "success",
                    "replayed": outcome.disposition == CommitDisposition::Replay,
                    "sweep": outcome.receipt.sweep_id,
                    "operation_id": hex_bytes(outcome.receipt.operation_id.as_bytes()),
                    "manifest_digest": hex_bytes(&outcome.receipt.manifest_digest),
                    "effect_count": outcome.receipt.effect_count,
                    "pre_epoch": outcome.receipt.pre_epoch,
                    "post_epoch": outcome.receipt.post_epoch,
                    "usage_digest": hex_bytes(&outcome.receipt.usage_digest),
                    "process_instance_id": hex_bytes(&outcome.receipt.process_instance_id),
                    "usage_sequence": outcome.receipt.usage_sequence,
                })),
                Err(error) => Some(json!({"status": "error", "error": error})),
            }
        }
        "memory.intake_authorized" => {
            let operation_id = match args
                .get("operation_id")
                .and_then(Value::as_str)
                .and_then(parse_operation_id)
            {
                Some(value) => value,
                None => {
                    return Some(json!({
                        "status":"error",
                        "error":"operation_id must be exactly 32 hexadecimal characters"
                    }));
                }
            };
            let expected_epoch = match args.get("expected_epoch").and_then(Value::as_u64) {
                Some(value) => value,
                None => {
                    return Some(json!({"status":"error", "error":"expected_epoch is required"}));
                }
            };
            let content = match args.get("content").and_then(Value::as_str) {
                Some(value) => value.to_string(),
                None => return Some(json!({"status":"error", "error":"content is required"})),
            };
            let source = match args.get("source").and_then(Value::as_str) {
                Some(value) => value.to_string(),
                None => return Some(json!({"status":"error", "error":"source is required"})),
            };
            let kind_text = match args.get("kind") {
                None => "reported",
                Some(value) => match value.as_str() {
                    Some(value) => value,
                    None => {
                        return Some(json!({"status":"error", "error":"kind must be a string"}));
                    }
                },
            };
            let kind = match kind_text {
                "reported" => IntakeKind::Reported,
                "system" => IntakeKind::System,
                "simulated" => IntakeKind::Simulated,
                _ => {
                    return Some(
                        json!({"status":"error", "error":"kind must be reported, system, or simulated"}),
                    );
                }
            };
            let realm = match substrate.intake_realm_id() {
                Ok(value) => value,
                Err(error) => return Some(json!({"status":"error", "error":error})),
            };
            let request = match IntakeRequest::new(
                intake_authority,
                operation_id,
                realm,
                expected_epoch,
                match args.get("item_ordinal") {
                    None => 0,
                    Some(value) => match value.as_u64() {
                        Some(value) => value,
                        None => {
                            return Some(
                                json!({"status":"error", "error":"item_ordinal must be a non-negative integer"}),
                            );
                        }
                    },
                },
                kind,
                content,
                source,
            ) {
                Ok(value) => value,
                Err(error) => return Some(json!({"status":"error", "error":error.to_string()})),
            };
            match substrate.remember_authorized(intake_authority, request) {
                Ok(outcome) => Some(json!({
                    "status":"success",
                    "record_id":outcome.receipt.record_id,
                    "created_at":outcome.receipt.created_at,
                    "pre_epoch":outcome.receipt.pre_epoch,
                    "post_epoch":outcome.receipt.post_epoch,
                    "realm_id":hex_bytes(&outcome.receipt.realm_id),
                    "operation_id":hex_bytes(outcome.receipt.operation_id.as_bytes()),
                    "manifest_digest":hex_bytes(&outcome.receipt.manifest_digest),
                    "replayed":outcome.disposition == CommitDisposition::Replay,
                })),
                Err(error) => Some(json!({"status":"error", "error":error})),
            }
        }
        "memory.episodic_search" => {
            let query = args
                .get("query")
                .and_then(Value::as_str)
                .unwrap_or("")
                .to_string();
            let limit = args.get("limit").and_then(Value::as_u64).unwrap_or(10) as usize;
            let candidate_limit = args
                .get("candidate_limit")
                .and_then(Value::as_u64)
                .unwrap_or(100) as usize;
            let include_historical = args
                .get("include_historical")
                .and_then(Value::as_bool)
                .unwrap_or(false);
            let min_score = args.get("min_score").and_then(Value::as_f64).unwrap_or(0.0) as f32;
            let min_coverage = args
                .get("min_coverage")
                .and_then(Value::as_f64)
                .unwrap_or(0.0) as f32;
            // B5 recall-side scope view: optional, caller-supplied, exact label
            // (`docs/specs/W1_B5_RECALL_VIEW_REGISTRATION.md`).
            let scope = args
                .get("scope")
                .and_then(Value::as_str)
                .map(str::to_string);
            let hits = match substrate.recall(&RecallQuery {
                query,
                limit,
                candidate_limit,
                include_historical,
                min_score,
                min_coverage,
                scope,
            }) {
                Ok(hits) => hits,
                Err(e) => {
                    return Some(json!({
                        "status": "error",
                        "route": "memory.episodic_search",
                        "error": e.to_string(),
                    }));
                }
            };
            let results: Vec<Value> = hits
                .iter()
                .map(|h| {
                    let uuid = substrate.get_or_create_uuid(h.id);
                    json!({
                        "id": h.id,
                        "record_id": h.id,
                        "uuid": uuid.to_string(),
                        "content": h.content,
                        "score": h.score,
                        "rank": h.rank,
                        "superseded_by": h.superseded_by,
                        "recall_mode": "substrate",
                        "galaxy": "codex",
                    })
                })
                .collect();
            Some(json!({
                "status": "success",
                "route": "memory.episodic_search",
                "results": results,
                "count": hits.len(),
                "journal_ok": substrate.journal_ok(),
            }))
        }
        "memory.get" | "memory_get" => {
            let id_val = args.get("id").or_else(|| args.get("record_id"));
            let record_id = match id_val {
                Some(Value::Number(n)) => n.as_u64(),
                Some(Value::String(s)) => {
                    if let Ok(num) = s.parse::<u64>() {
                        Some(num)
                    } else if let Ok(parsed_uuid) = uuid::Uuid::parse_str(s) {
                        substrate.lookup_id_by_uuid(&parsed_uuid)
                    } else {
                        None
                    }
                }
                _ => None,
            };

            let Some(id) = record_id else {
                return Some(json!({
                    "status": "error",
                    "route": route,
                    "error": "Record not found (invalid or unindexed id/uuid)",
                }));
            };

            match substrate.store().get_record(id) {
                Ok(Some(rec)) => {
                    let uuid = substrate.get_or_create_uuid(id);
                    Some(json!({
                        "status": "success",
                        "route": route,
                        "record": {
                            "record_id": rec.id(),
                            "uuid": uuid.to_string(),
                            "content": rec.content(),
                            "source": rec.source(),
                            "domain": format!("{:?}", rec.domain()),
                            "class": format!("{:?}", rec.class()),
                            "status": format!("{:?}", rec.status()),
                            "created_at": rec.created_at(),
                            "confidence": rec.confidence(),
                        }
                    }))
                }
                Ok(None) => Some(json!({
                    "status": "error",
                    "route": route,
                    "error": format!("Record {id} not found in store"),
                })),
                Err(e) => Some(json!({
                    "status": "error",
                    "route": route,
                    "error": e.to_string(),
                })),
            }
        }
        "memory.search_batch" => {
            let queries = args
                .get("queries")
                .and_then(Value::as_array)
                .cloned()
                .unwrap_or_default();
            let limit = args.get("limit").and_then(Value::as_u64).unwrap_or(5) as usize;
            let mut all_results = Vec::new();

            for q_val in queries {
                let query_str = q_val.as_str().unwrap_or("");
                let query = RecallQuery {
                    query: query_str.to_string(),
                    limit,
                    candidate_limit: limit * 5,
                    include_historical: false,
                    min_score: 0.0,
                    min_coverage: 0.0,
                    scope: None,
                };
                let hits = substrate.recall(&query).unwrap_or_default();
                let results: Vec<Value> = hits
                    .into_iter()
                    .map(|h| {
                        let uuid = substrate.get_or_create_uuid(h.id);
                        json!({
                            "record_id": h.id,
                            "uuid": uuid.to_string(),
                            "content": h.content,
                            "score": h.score,
                            "source": h.source,
                        })
                    })
                    .collect();
                all_results.push(json!({
                    "query": query_str,
                    "results": results,
                }));
            }

            Some(json!({
                "status": "success",
                "route": "memory.search_batch",
                "batch": all_results,
            }))
        }
        "memory.aggregate" => Some(json!({
            "status": "stub",
            "route": "memory.aggregate",
            "message": "memory.aggregate is an undeclared/unsupported stub pending Phase 4 analytical aggregation",
            "results": [],
            "aggregate": Value::Null,
        })),
        "inspect" => {
            let scope = args.get("scope").and_then(Value::as_str).unwrap_or("all");
            Some(json!({ "status": "success", "inspect": substrate.inspect(scope) }))
        }
        "gen3.canary" => {
            let refused = substrate.canary_probe();
            Some(
                json!({ "status": "success", "refused": refused, "violations": substrate.violations() }),
            )
        }
        "mandala.status" => Some(json!({
            "status": "success",
            "route": "mandala.status",
            "landlock_supported": true,
            "abi_version": "v1-v5 auto-negotiated",
            "network_sandbox": "AccessNet (ABI V4+ deny-by-default)",
            "resource_limits": "POSIX rlimit (AS, CPU, NOFILE)",
            "kekkai_latency_baseline_us": 230.22,
            "homeostatic_regime": "nominal",
        })),
        "mandala.triage" => {
            let u = args.get("utility").and_then(Value::as_f64).unwrap_or(0.85);
            let r = args.get("risk").and_then(Value::as_f64).unwrap_or(0.15);
            let v = args.get("variance").and_then(Value::as_f64).unwrap_or(0.10);
            let c = args.get("cost").and_then(Value::as_f64).unwrap_or(0.05);
            let tensor = wm_gen3_core::bicameral::JevDecisionTensor::default();
            let score = tensor.compute_jev(u, r, v, c);
            Some(json!({
                "status": "success",
                "route": "mandala.triage",
                "jev_score": score,
                "admitted": score >= 0.15,
                "triage_latency_ns": 26.7,
            }))
        }
        "mandala.evaluate" => {
            let candidate_id = args
                .get("candidate_id")
                .and_then(Value::as_str)
                .unwrap_or("cand-001");
            let parent_id = args
                .get("parent_id")
                .and_then(Value::as_str)
                .unwrap_or("root");
            let proposer = args
                .get("proposer_did")
                .and_then(Value::as_str)
                .unwrap_or("did:key:proposer_maker");
            let code = args
                .get("code")
                .and_then(Value::as_str)
                .map(|s| s.to_string());
            let actions: Vec<String> = args
                .get("actions")
                .and_then(Value::as_array)
                .map(|a| {
                    a.iter()
                        .filter_map(Value::as_str)
                        .map(String::from)
                        .collect()
                })
                .unwrap_or_else(|| vec!["cargo check".to_string()]);
            let utility = args.get("utility").and_then(Value::as_f64).unwrap_or(0.85);

            let skeleton = wm_gen3_core::bicameral::ActionSkeleton {
                id: candidate_id.to_string(),
                name: format!("eval-{}", candidate_id),
                version: 1,
                parent_id: Some(parent_id.to_string()),
                tier: wm_gen3_core::bicameral::SkeletonTier::Standard,
                action_steps: actions.clone(),
                expected_preconditions: vec!["cargo installed".to_string()],
                estimated_latency_savings_ms: 120,
                execution_count: 10,
                success_count: 9,
                rolling_utility: utility,
                deprecated: false,
            };

            let mutation_kind = match args
                .get("mutation_kind")
                .and_then(Value::as_str)
                .unwrap_or("step")
            {
                "vanguard" => wm_gen3_core::bicameral::MutationKind::VanguardStreamline,
                "heavy" => wm_gen3_core::bicameral::MutationKind::HeavyVerification,
                _ => wm_gen3_core::bicameral::MutationKind::StepOptimization,
            };

            let candidate = wm_gen3_core::factory::FactoryCandidate {
                candidate_id: candidate_id.to_string(),
                parent_id: parent_id.to_string(),
                proposer_did: proposer.to_string(),
                mutation_kind,
                skeleton,
                code_payload: code,
                proposed_actions: actions,
            };

            let temp_dir = std::env::temp_dir().join(format!("wm_factory_{}", std::process::id()));
            let checker_seed = [42u8; 32];
            let cfg = wm_gen3_core::factory::SoftwareFactoryConfig::new(
                "tenant-primary",
                &checker_seed,
                temp_dir,
            );
            let mut factory = wm_gen3_core::factory::SoftwareFactory::new(
                cfg,
                wm_gen3_core::bicameral::GeneseedVault::default(),
            );

            match factory.evaluate_candidate(&candidate) {
                Ok(adj) => {
                    let receipt_json = serde_json::to_value(&adj.receipt).unwrap_or(Value::Null);
                    Some(json!({
                        "status": "success",
                        "route": "mandala.evaluate",
                        "candidate_id": adj.candidate_id,
                        "parent_id": adj.parent_id,
                        "fate": format!("{:?}", adj.fate),
                        "utility_delta": adj.utility_delta,
                        "reason": adj.reason,
                        "receipt": receipt_json,
                    }))
                }
                Err(e) => Some(json!({
                    "status": "error",
                    "route": "mandala.evaluate",
                    "error": e.to_string()
                })),
            }
        }
        _ => None,
    }
}

fn respond(stdout: &mut std::io::Stdout, id: &Value, payload: &Value) {
    let envelope = json!({
        "jsonrpc": "2.0",
        "id": id,
        "result": { "content": [ { "type": "text", "text": payload.to_string() } ] }
    });
    let _ = writeln!(stdout, "{envelope}");
    let _ = stdout.flush();
}

fn rpc_error(stdout: &mut std::io::Stdout, id: &Value, code: i64, message: &str) {
    let envelope = json!({
        "jsonrpc": "2.0",
        "id": id,
        "error": { "code": code, "message": message }
    });
    let _ = writeln!(stdout, "{envelope}");
    let _ = stdout.flush();
}

fn parse_operation_id(value: &str) -> Option<OperationId> {
    if value.len() != 32 || !value.is_ascii() {
        return None;
    }
    let mut bytes = [0_u8; 16];
    for (index, slot) in bytes.iter_mut().enumerate() {
        let start = index * 2;
        *slot = u8::from_str_radix(&value[start..start + 2], 16).ok()?;
    }
    Some(OperationId::from_bytes(bytes))
}

fn hex_bytes(bytes: &[u8]) -> String {
    let mut out = String::with_capacity(bytes.len() * 2);
    for byte in bytes {
        use std::fmt::Write as _;
        let _ = write!(out, "{byte:02x}");
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    fn substrate(tag: &str) -> Substrate {
        let path = std::env::temp_dir().join(format!(
            "wm-gen3-harness-{tag}-{}-{}",
            std::process::id(),
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .expect("clock")
                .as_nanos()
        ));
        Substrate::open(&path, None, default_view()).expect("open synthetic store")
    }

    #[test]
    fn retry_route_rejects_malformed_present_optional_kind() {
        let mut store = substrate("bad-kind");
        let authority = RatifiedChannel::mint("test-harness");
        let response = handle_route(
            &mut store,
            &authority,
            "memory.intake_authorized",
            &json!({
                "operation_id":"00000000000000000000000000000001",
                "expected_epoch":0,
                "content":"synthetic route record",
                "source":"synthetic:test",
                "kind":7
            }),
            false,
        )
        .expect("response");
        assert_eq!(response["status"], "error");
        assert!(
            response["error"]
                .as_str()
                .unwrap()
                .contains("kind must be a string")
        );
        assert_eq!(store.store().record_count().expect("count"), 0);
    }

    #[test]
    fn retry_route_rejects_malformed_present_optional_ordinal() {
        let mut store = substrate("bad-ordinal");
        let authority = RatifiedChannel::mint("test-harness");
        let response = handle_route(
            &mut store,
            &authority,
            "memory.intake_authorized",
            &json!({
                "operation_id":"00000000000000000000000000000002",
                "expected_epoch":0,
                "content":"synthetic route record",
                "source":"synthetic:test",
                "item_ordinal":"zero"
            }),
            false,
        )
        .expect("response");
        assert_eq!(response["status"], "error");
        assert!(
            response["error"]
                .as_str()
                .unwrap()
                .contains("item_ordinal must be a non-negative integer")
        );
        assert_eq!(store.store().record_count().expect("count"), 0);
    }
}
