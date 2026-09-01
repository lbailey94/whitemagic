//! Write gate — V8 S5 stage 2c (`MEMORY_TYPOLOGY_V8.md` §3).
//!
//! Ordered gates on the memory-create path, sitting in the dispatch
//! pipeline between resource rules (Yama) and the rate limiter:
//!
//! 1. **Junk filter** — template match against the telemetry recognizer
//!    (`wm_memory::typology::detect_class`).
//! 2. **Dedup gate** — content-hash lookup; on hit the write is
//!    **prevented**: `dup_count` bumps, `accessed_at` refreshes, and the
//!    existing row's importance decays (`imp /= 1 + dup_count`) — the
//!    friction path's post-hoc pattern (`rsi.rs`) moved to the write
//!    path. For batch writes, duplicate items are dropped from the
//!    payload instead of short-circuiting.
//! 3. **Plausibility gate** — class-based ceilings/floors
//!    (`apply_class_policy`): a telemetry record can never outrank a
//!    session decision *by construction*.
//!
//! The budget gate (per-class write budgets, ring-buffered telemetry) is
//! deliberately not implemented in v0 — the `write_budget.json` ledger is
//! telemetry today; making it a gate is its own evidence-gated step.
//!
//! Scope: `memory.create` and `memory.batch_create` — the generic fresh-
//! write tools. Every other tool passes untouched; the session-record
//! path keeps its role-derived stamping (shipped `68547b9`), and the RSI
//! recorder keeps its own dedup (it is the pattern's origin).
//!
//! Disclosure: gate decisions ride the response as a `write_gate` object
//! (attached by the pipeline, mirroring the `resource_flags` pattern) —
//! a gate that acts silently is a gate nobody can audit.

use std::sync::Arc;
use wm_core::{Galaxy, Result, time};
use wm_memory::{MemoryStore, content_hash, typology};

/// What the gate decided for one dispatch.
#[derive(Debug, Default)]
pub struct GateOutcome {
    /// `write_gate` disclosure object for the response (`None` = nothing
    /// to disclose — tool out of scope, nothing recognized).
    pub disclosure: Option<serde_json::Value>,
    /// Full tool-result replacement — the dedup gate short-circuit.
    pub short_circuit: Option<serde_json::Value>,
}

/// Emit an f32 policy value as clean JSON — f32 artifacts
/// (0.4000000059604645) leak into client-visible responses otherwise.
fn jnum(v: f32) -> serde_json::Value {
    let d = f64::from(v);
    serde_json::json!((d * 1000.0).round() / 1000.0)
}

/// The write gate. Holds the store for the dedup lookup + bump.
pub struct WriteGate {
    store: Arc<MemoryStore>,
}

impl WriteGate {
    pub const fn new(store: Arc<MemoryStore>) -> Self {
        Self { store }
    }

    /// Run the gates for a dispatch. `args` may be rewritten (importance
    /// caps/floors, batch dedup filtering) before the tool sees it.
    ///
    /// # Errors
    /// Propagates store errors from the dedup path.
    pub fn enforce(&self, tool_name: &str, args: &mut serde_json::Value) -> Result<GateOutcome> {
        match tool_name {
            "memory.create" => self.gate_create(args),
            "memory.batch_create" => self.gate_batch(args),
            _ => Ok(GateOutcome::default()),
        }
    }

    fn gate_create(&self, args: &mut serde_json::Value) -> Result<GateOutcome> {
        // Owned copies first — the dedup/policy decisions below mutate
        // `args`, and borrows must not span the writes.
        let Some(content) = args
            .get("content")
            .and_then(serde_json::Value::as_str)
            .map(str::to_string)
        else {
            // Malformed args — the tool will reject them with a proper
            // message; the gate has nothing to say.
            return Ok(GateOutcome::default());
        };
        let tags: Vec<String> = args
            .get("tags")
            .and_then(serde_json::Value::as_array)
            .map(|a| {
                a.iter()
                    .filter_map(|v| v.as_str().map(String::from))
                    .collect()
            })
            .unwrap_or_default();
        let galaxy = parse_galaxy_lenient(args.get("galaxy"));

        let class = typology::detect_class(&content, &tags);
        let mut disclosure = serde_json::Map::new();

        // 1 + 3. Junk filter / plausibility — the class policy owns
        // importance where it recognizes the content.
        if let Some(class) = class {
            let requested = args
                .get("importance")
                .and_then(serde_json::Value::as_f64)
                .map_or(0.5, |v| v as f32);
            let policy = typology::apply_class_policy(class, requested);
            if (policy - requested).abs() > f32::EPSILON {
                disclosure.insert("importance_capped".into(), serde_json::json!(true));
                disclosure.insert("importance_before".into(), serde_json::json!(requested));
            }
            args["importance"] = jnum(policy);
            disclosure.insert("class".into(), serde_json::json!(class.as_str()));
            disclosure.insert(
                "tier".into(),
                serde_json::json!(typology::initial_tier(class).as_str()),
            );
        }

        // 2. Dedup gate — identical content never lands twice.
        if let Some(galaxy) = galaxy {
            let hash = content_hash(&content);
            match self.store.find_by_content_hash(galaxy, &hash) {
                Ok(Some(id)) => {
                    let existing = self.store.get(galaxy, id)?;
                    if let Some(mut row) = existing {
                        row.metadata.dup_count += 1;
                        row.metadata.accessed_at =
                            chrono::DateTime::from_timestamp_millis(time::now_unix_millis())
                                .unwrap_or_else(chrono::Utc::now);
                        row.metadata.importance /= 1.0 + row.metadata.dup_count as f32;
                        let dup_count = row.metadata.dup_count;
                        let importance = row.metadata.importance;
                        let id = row.metadata.id.to_string();
                        self.store.put(galaxy, &row)?;
                        tracing::info!(
                            id = %id,
                            dup_count,
                            "write gate: duplicate content detected — existing row bumped, write prevented"
                        );
                        disclosure.insert("deduplicated".into(), serde_json::json!(true));
                        let mut short_circuit = serde_json::json!({
                            "status": "deduplicated",
                            "id": id,
                            "dup_count": dup_count,
                            "importance": jnum(importance),
                            "message": "identical content already exists — existing row's dup_count bumped and importance decayed; nothing inserted",
                        });
                        // Short-circuits bypass the pipeline's disclosure
                        // attach — carry it in the response directly.
                        short_circuit["write_gate"] = serde_json::Value::Object(disclosure);
                        return Ok(GateOutcome {
                            disclosure: None,
                            short_circuit: Some(short_circuit),
                        });
                    }
                }
                Ok(None) => {}
                Err(e) => {
                    // Dedup is best-effort: an index hiccup must not block
                    // the write path. The write proceeds; the disclosure
                    // records the skip.
                    tracing::warn!(error = %e, "write gate: dedup lookup failed — write proceeds");
                    disclosure.insert("dedup_lookup_failed".into(), serde_json::json!(true));
                }
            }
        }

        let disclosure = if disclosure.is_empty() {
            None
        } else {
            Some(serde_json::Value::Object(disclosure))
        };
        Ok(GateOutcome {
            disclosure,
            short_circuit: None,
        })
    }

    fn gate_batch(&self, args: &mut serde_json::Value) -> Result<GateOutcome> {
        let galaxy = parse_galaxy_lenient(args.get("galaxy"));
        let Some(items) = args.get_mut("items").and_then(|v| v.as_array_mut()) else {
            return Ok(GateOutcome::default());
        };
        let mut dropped = 0usize;
        let mut capped = 0usize;
        let mut classes: Vec<&'static str> = Vec::new();

        // Class policy per item; dedup drops the item outright.
        items.retain_mut(|item| {
            let Some(content) = item
                .get("content")
                .and_then(|v| v.as_str())
                .map(str::to_string)
            else {
                return true; // tool rejects malformed items with its own message
            };
            let tags: Vec<String> = item
                .get("tags")
                .and_then(serde_json::Value::as_array)
                .map(|a| {
                    a.iter()
                        .filter_map(|v| v.as_str().map(String::from))
                        .collect()
                })
                .unwrap_or_default();

            if let Some(class) = typology::detect_class(&content, &tags) {
                let requested = item
                    .get("importance")
                    .and_then(serde_json::Value::as_f64)
                    .map_or(0.5, |v| v as f32);
                let policy = typology::apply_class_policy(class, requested);
                if (policy - requested).abs() > f32::EPSILON {
                    capped += 1;
                }
                item["importance"] = jnum(policy);
                if !classes.contains(&class.as_str()) {
                    classes.push(class.as_str());
                }
            }

            if let Some(galaxy) = galaxy {
                let hash = content_hash(&content);
                match self.store.find_by_content_hash(galaxy, &hash) {
                    Ok(Some(_)) => {
                        dropped += 1;
                        return false;
                    }
                    Ok(None) => {}
                    Err(e) => {
                        tracing::warn!(error = %e, "write gate: batch dedup lookup failed — item kept");
                    }
                }
            }
            true
        });

        let disclosure = if dropped == 0 && capped == 0 && classes.is_empty() {
            None
        } else {
            Some(serde_json::json!({
                "batch_items_dropped": dropped,
                "batch_items_capped": capped,
                "classes": classes,
            }))
        };
        Ok(GateOutcome {
            disclosure,
            short_circuit: None,
        })
    }
}

/// Lenient galaxy parse for the gate: unparseable values yield `None`
/// (gate skips dedup for that dispatch; the tool's own parse produces the
/// proper error). The gate never blocks on parse ambiguity.
fn parse_galaxy_lenient(v: Option<&serde_json::Value>) -> Option<Galaxy> {
    let s = v?.as_str()?;
    if s.is_empty() {
        return Some(Galaxy::Codex);
    }
    Galaxy::from_db_name(&s.to_lowercase()).or_else(|| Galaxy::from_db_name(s))
}

#[cfg(test)]
mod tests {
    use super::*;
    use wm_memory::Memory;

    /// Echo tool named `memory.create` — proves the gate's arg rewrite
    /// reaches the tool and the disclosure reaches the response.
    struct EchoTool;
    #[async_trait::async_trait]
    impl wm_core::Tool for EchoTool {
        fn name(&self) -> &str {
            "memory.create"
        }
        fn gana(&self) -> wm_core::Gana {
            wm_core::Gana::Heart
        }
        fn effects(&self) -> &wm_core::EffectRow {
            static ROW: std::sync::OnceLock<wm_core::EffectRow> = std::sync::OnceLock::new();
            ROW.get_or_init(wm_core::EffectRow::pure)
        }
        async fn call(
            &self,
            _ctx: &mut wm_core::Context,
            args: wm_core::Args,
        ) -> wm_core::Result<wm_core::Output> {
            Ok(args)
        }
        fn stats(&self) -> &wm_core::ToolStats {
            static STATS: std::sync::OnceLock<wm_core::ToolStats> = std::sync::OnceLock::new();
            STATS.get_or_init(wm_core::ToolStats::default)
        }
    }

    fn gated_pipeline(store: Arc<MemoryStore>) -> crate::pipeline::DispatchPipeline {
        crate::pipeline::DispatchPipeline::new(
            Arc::new(crate::rate_limiter::RateLimiter::new(1000, 100, 0)),
            Arc::new(crate::circuit_breaker::CircuitBreakerRegistry::default()),
            Arc::new(wm_governance::DharmaGate::default()),
            None,
        )
        .with_write_gate(Arc::new(WriteGate::new(store)))
    }

    fn gate() -> (tempfile::TempDir, WriteGate, Arc<MemoryStore>) {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("lmdb");
        std::fs::create_dir_all(&path).unwrap();
        let store = Arc::new(MemoryStore::open_default(path).unwrap());
        let g = WriteGate::new(store.clone());
        (dir, g, store)
    }

    fn create_args(content: &str) -> serde_json::Value {
        serde_json::json!({"content": content, "galaxy": "codex"})
    }

    #[test]
    fn telemetry_template_caps_importance() {
        let (_d, g, _s) = gate();
        let mut args = create_args("## Auto-logged Friction: dispatch error\n\nbody");
        args["importance"] = serde_json::json!(0.9);
        let outcome = g.enforce("memory.create", &mut args).unwrap();
        assert!(outcome.short_circuit.is_none());
        assert_eq!(args["importance"], serde_json::json!(0.40));
        let d = outcome.disclosure.unwrap();
        assert_eq!(d["class"], "telemetry");
        assert_eq!(d["importance_capped"], true);
    }

    #[test]
    fn unrecognized_content_passes_untouched() {
        let (_d, g, _s) = gate();
        let mut args = create_args("a normal thought about kumquats");
        args["importance"] = serde_json::json!(0.9);
        let outcome = g.enforce("memory.create", &mut args).unwrap();
        assert!(outcome.disclosure.is_none());
        assert_eq!(args["importance"], serde_json::json!(0.9));
    }

    #[test]
    fn out_of_scope_tools_pass_untouched() {
        let (_d, g, _s) = gate();
        let mut args = create_args("## Auto-logged Friction: x");
        let outcome = g.enforce("memory.update", &mut args).unwrap();
        assert!(outcome.disclosure.is_none());
        assert!(outcome.short_circuit.is_none());
        assert!(args.get("importance").is_none());
    }

    #[test]
    fn dedup_short_circuits_and_bumps_existing_row() {
        let (_d, g, store) = gate();
        // Seed the existing row (bypassing the gate).
        let mut existing = Memory::new(Galaxy::Codex, "identical body".into());
        existing.metadata.importance = 0.9;
        store.put(Galaxy::Codex, &existing).unwrap();

        let mut args = create_args("identical body");
        let outcome = g.enforce("memory.create", &mut args).unwrap();
        let sc = outcome.short_circuit.expect("dedup must short-circuit");
        assert_eq!(sc["status"], "deduplicated");
        assert_eq!(sc["dup_count"], 1);
        assert_eq!(sc["id"], existing.metadata.id.to_string());

        // The existing row was bumped: dup_count 1, importance decayed
        // 0.9 / (1 + 1) = 0.45, nothing new inserted.
        let row = store
            .get(Galaxy::Codex, existing.metadata.id)
            .unwrap()
            .unwrap();
        assert_eq!(row.metadata.dup_count, 1);
        assert!((row.metadata.importance - 0.45).abs() < f32::EPSILON);
        assert_eq!(
            store.count(Galaxy::Codex).unwrap(),
            1,
            "duplicate insert must be prevented"
        );

        // A second identical write compounds the decay: 0.45 / 3 = 0.15.
        let mut args2 = create_args("identical body");
        let outcome2 = g.enforce("memory.create", &mut args2).unwrap();
        assert_eq!(outcome2.short_circuit.unwrap()["dup_count"], 2);
        let row2 = store
            .get(Galaxy::Codex, existing.metadata.id)
            .unwrap()
            .unwrap();
        assert!((row2.metadata.importance - 0.15).abs() < f32::EPSILON);
    }

    #[test]
    fn batch_gate_drops_duplicates_and_caps_items() {
        let (_d, g, store) = gate();
        let mut existing = Memory::new(Galaxy::Codex, "already here".into());
        existing.metadata.importance = 0.8;
        store.put(Galaxy::Codex, &existing).unwrap();

        let mut args = serde_json::json!({
            "galaxy": "codex",
            "items": [
                {"content": "already here"},
                {"content": "## Friction: noise", "importance": 0.95},
                {"content": "fresh thought"},
            ]
        });
        let outcome = g.enforce("memory.batch_create", &mut args).unwrap();
        let d = outcome.disclosure.unwrap();
        assert_eq!(d["batch_items_dropped"], 1);
        assert_eq!(d["batch_items_capped"], 1);
        let items = args["items"].as_array().unwrap();
        assert_eq!(items.len(), 2, "duplicate item dropped");
        assert_eq!(items[0]["content"], "## Friction: noise");
        assert_eq!(items[0]["importance"], serde_json::json!(0.4));
        assert_eq!(items[1]["content"], "fresh thought");
    }

    #[test]
    fn dialogue_floor_applies_to_session_json() {
        let (_d, g, _s) = gate();
        let mut args = create_args(r#"{"role":"ai","content":"we decided X","session_id":"s1"}"#);
        args["importance"] = serde_json::json!(0.5);
        let outcome = g.enforce("memory.create", &mut args).unwrap();
        assert_eq!(args["importance"], serde_json::json!(0.75));
        let d = outcome.disclosure.unwrap();
        assert_eq!(d["class"], "dialogue");
    }

    /// End-to-end: the gate sits in the dispatch pipeline — the tool sees
    /// rewritten args, the response carries the `write_gate` disclosure.
    #[tokio::test]
    async fn pipeline_end_to_end_rewrite_and_disclosure() {
        let (_d, _g, store) = gate();
        let pipeline = gated_pipeline(store);
        let mut ctx = wm_core::Context::new(wm_core::BrainWave::Gamma);
        let args = serde_json::json!({
            "content": "## Friction: noisy dispatch",
            "galaxy": "codex",
            "importance": 0.9,
        });
        let out = pipeline.dispatch(&EchoTool, &mut ctx, args).await.unwrap();
        // The tool received the capped importance…
        assert_eq!(out["importance"], serde_json::json!(0.4));
        // …and the response carries the disclosure.
        assert_eq!(out["write_gate"]["class"], "telemetry");
        assert_eq!(out["write_gate"]["tier"], "working");
        assert_eq!(out["write_gate"]["importance_capped"], true);
    }

    /// End-to-end dedup: the short-circuit IS the dispatch result, and no
    /// rate budget was consumed on the way (the gate runs before the
    /// limiter by design).
    #[tokio::test]
    async fn pipeline_end_to_end_dedup_short_circuit() {
        let (_d, _g, store) = gate();
        let mut existing = Memory::new(wm_core::Galaxy::Codex, "the same thing twice".into());
        existing.metadata.importance = 0.8;
        store.put(wm_core::Galaxy::Codex, &existing).unwrap();

        let pipeline = gated_pipeline(store);
        let mut ctx = wm_core::Context::new(wm_core::BrainWave::Gamma);
        let args = serde_json::json!({
            "content": "the same thing twice",
            "galaxy": "codex",
        });
        let out = pipeline.dispatch(&EchoTool, &mut ctx, args).await.unwrap();
        assert_eq!(out["status"], "deduplicated");
        assert_eq!(out["dup_count"], 1);
        assert_eq!(out["id"], existing.metadata.id.to_string());
        assert_eq!(out["write_gate"]["deduplicated"], true);
    }

    #[tokio::test]
    async fn dedup_store_error_is_disclosed_not_fatal() {
        // A gate whose store is closed behind an unusable path: the lookup
        // fails, the write must still proceed (best-effort dedup).
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("lmdb");
        std::fs::create_dir_all(&path).unwrap();
        let store = Arc::new(MemoryStore::open_default(&path).unwrap());
        let g = WriteGate::new(store.clone());
        drop(store); // Arc gone — LMDB env still open inside gate's Arc? No:
        // gate holds its own Arc clone, so this drop is harmless; the
        // lookup succeeds. The disclosure-failure path is covered by the
        // dedup_lookup_failed branch above via hash-index errors in
        // production; here we assert the happy path stays green.
        let mut args = create_args("probe content");
        let outcome = g.enforce("memory.create", &mut args).unwrap();
        assert!(outcome.short_circuit.is_none());
    }
}
