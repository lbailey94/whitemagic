//! Q35b replay acceptance — flight-recorder driven (layer 2).
//!
//! The full manifest acceptance, upgraded by the NEON twin-run transfer:
//! record a live-ish session on store A (real store mutations through the
//! pipeline, flight sidecar ON), then REPLAY FROM THE SIDECAR FILE onto
//! fresh store B — not by re-running the same code path — verifying at
//! every step that the replayed dispatch's args_digest matches the source
//! journal (the identity gate), and finally diffing normalized journal
//! streams byte-identical.

use std::sync::{Arc, OnceLock};

use async_trait::async_trait;
use serde_json::{Value, json};
use wm_core::{Args, Context, EffectRow, Galaxy, Gana, Output, Resource, Tool, ToolStats};
use wm_dispatch::{
    CircuitBreakerRegistry, DispatchPipeline, FlightEntry, FlightRecorder, RateLimiter,
    ToolRegistry, ToolRegistryBuilder,
};
use wm_governance::{DharmaGate, WriteAuditJournal};
use wm_memory::{Memory, MemoryStore};

// ── Real-store deterministic tools ───────────────────────────────────

/// Writes n memories to the REAL store (store.put), deterministic content,
/// content-hash ids surfaced (random UUIDs deliberately never surface).
struct RealWriter {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: OnceLock<EffectRow>,
}

impl RealWriter {
    fn new(store: Arc<MemoryStore>) -> Self {
        Self {
            store,
            stats: ToolStats::default(),
            effects: OnceLock::new(),
        }
    }
}

#[async_trait]
impl Tool for RealWriter {
    fn name(&self) -> &str {
        "test.writer"
    }
    fn gana(&self) -> Gana {
        Gana::Horn
    }
    fn effects(&self) -> &EffectRow {
        self.effects.get_or_init(|| EffectRow {
            writes: vec![Resource::Galaxy(Galaxy::Codex.to_string())],
            ..EffectRow::default()
        })
    }
    async fn call(&self, _ctx: &mut Context, args: Args) -> wm_core::Result<Output> {
        let key = args.get("key").and_then(Value::as_str).unwrap_or("k");
        let n = args.get("n").and_then(Value::as_u64).unwrap_or(1) as usize;
        let mut writes = Vec::new();
        for i in 0..n {
            let mem = Memory::new(Galaxy::Codex, format!("flight:{key}:{i}"));
            self.store
                .put(Galaxy::Codex, &mem)
                .map_err(|e| wm_core::CoreError::Tool(format!("put failed: {e}")))?;
            writes.push(json!(mem.metadata.content_hash));
        }
        let first_hash = writes
            .first()
            .and_then(Value::as_str)
            .unwrap_or_default()
            .to_string();
        Ok(json!({ "id": first_hash, "content_hash": first_hash, "writes": writes }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// Counts memories whose content starts with a prefix (real store read).
struct RealCounter {
    store: Arc<MemoryStore>,
    stats: ToolStats,
}

impl RealCounter {
    fn new(store: Arc<MemoryStore>) -> Self {
        Self {
            store,
            stats: ToolStats::default(),
        }
    }
}

#[async_trait]
impl Tool for RealCounter {
    fn name(&self) -> &str {
        "test.counter"
    }
    fn gana(&self) -> Gana {
        Gana::WinnowingBasket
    }
    fn effects(&self) -> &EffectRow {
        static EFFECTS: OnceLock<EffectRow> = OnceLock::new();
        EFFECTS.get_or_init(EffectRow::pure)
    }
    async fn call(&self, _ctx: &mut Context, args: Args) -> wm_core::Result<Output> {
        let prefix = args
            .get("prefix")
            .and_then(Value::as_str)
            .unwrap_or("flight:")
            .to_string();
        let memories = self
            .store
            .scan(Galaxy::Codex, 1000)
            .map_err(|e| wm_core::CoreError::Tool(format!("scan failed: {e}")))?;
        let count = memories
            .iter()
            .filter(|m| m.content.starts_with(&prefix))
            .count();
        Ok(json!({ "count": count, "prefix": prefix }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── Harness ──────────────────────────────────────────────────────────

struct Run {
    journal: Arc<WriteAuditJournal>,
    flight_path: std::path::PathBuf,
    registry: ToolRegistry,
    _store_dir: tempfile::TempDir,
    pipeline: DispatchPipeline,
}

/// Build a run with identical tool construction; `record` enables the
/// flight sidecar (store A) or not (store B, the replay target).
fn fresh_run(record: bool, tag: &str) -> Run {
    let dir = tempfile::tempdir().unwrap();
    let store = Arc::new(MemoryStore::open_default(dir.path()).unwrap());
    let journal = Arc::new(WriteAuditJournal::with_flush_threshold(store.clone(), 0).unwrap());
    let flight_path =
        std::env::temp_dir().join(format!("wm-flight-{tag}-{}.jsonl", std::process::id()));
    let mut builder = ToolRegistryBuilder::new();
    builder.register(Arc::new(RealWriter::new(store.clone())));
    builder.register(Arc::new(RealCounter::new(store)));
    let registry = builder.build();
    let flight = if record {
        Some(Arc::new(FlightRecorder::new(&flight_path).unwrap()))
    } else {
        None
    };
    let pipeline = DispatchPipeline::new(
        Arc::new(RateLimiter::default()),
        Arc::new(CircuitBreakerRegistry::default()),
        Arc::new(DharmaGate::default()),
        None,
    )
    .with_write_audit(journal.clone())
    .with_flight_recorder(flight);
    Run {
        journal,
        flight_path,
        registry,
        _store_dir: dir,
        pipeline,
    }
}

/// The recorded session — a mixed write/read/write sequence.
async fn run_session(run: &Run) {
    let mut ctx = Context::default();
    run.pipeline
        .dispatch_by_name(
            &run.registry,
            "test.writer",
            &mut ctx,
            json!({"key": "alpha", "n": 2}),
        )
        .await
        .expect("step 1");
    run.pipeline
        .dispatch_by_name(
            &run.registry,
            "test.counter",
            &mut ctx,
            json!({"prefix": "flight:alpha"}),
        )
        .await
        .expect("step 2");
    run.pipeline
        .dispatch_by_name(
            &run.registry,
            "test.writer",
            &mut ctx,
            json!({"key": "beta", "n": 3}),
        )
        .await
        .expect("step 3");
}

/// Normalize for diffing: timestamp is the sole volatile field.
fn normalize(entries: &[wm_governance::WriteAuditEntry]) -> Vec<Value> {
    entries
        .iter()
        .map(|e| {
            let mut v = serde_json::to_value(e).unwrap();
            v["timestamp"] = json!(0);
            v
        })
        .collect()
}

// ── The acceptance ───────────────────────────────────────────────────

#[tokio::test]
async fn flight_record_then_replay_from_sidecar() {
    let a = fresh_run(true, "replay-src");
    run_session(&a).await;

    // ── The record ──
    let (flight_entries, malformed) = FlightRecorder::read_entries(&a.flight_path).unwrap();
    assert_eq!(malformed, 0, "source log must be clean");
    assert_eq!(flight_entries.len(), 3, "one capture per dispatch");
    let source_journal = a.journal.scan_entries().unwrap();
    assert_eq!(source_journal.len(), 3);

    // ── The replay (from the sidecar, identity-gated) ──
    let b = fresh_run(false, "replay-dst");
    for fe in &flight_entries {
        // Identity gate: the sidecar args must hash to the source journal
        // digest for this step BEFORE anything executes on store B.
        let idx = fe.seq as usize;
        let expected = source_journal[idx]
            .args_digest
            .as_deref()
            .expect("source entry carries a digest");
        let actual = wm_governance::args_digest(&fe.tool, &fe.args);
        assert_eq!(actual, expected, "step {idx} identity gate");
        // Execute the recorded payload.
        b.pipeline
            .dispatch_by_name(
                &b.registry,
                &fe.tool,
                &mut Context::default(),
                fe.args.clone(),
            )
            .await
            .unwrap_or_else(|e| panic!("replay step {idx} ({}) failed: {e}", fe.tool));
    }

    // ── The diff: replayed journal == source journal (normalized) ──
    let replay_journal = b.journal.scan_entries().unwrap();
    assert_eq!(replay_journal.len(), source_journal.len());
    assert_eq!(
        normalize(&source_journal),
        normalize(&replay_journal),
        "replayed journal stream must be byte-identical to the recorded one"
    );

    // And the stores converged: the counter sees the same world.
    let count_a = a
        .pipeline
        .dispatch_by_name(
            &a.registry,
            "test.counter",
            &mut Context::default(),
            json!({"prefix": "flight:"}),
        )
        .await
        .unwrap();
    let count_b = b
        .pipeline
        .dispatch_by_name(
            &b.registry,
            "test.counter",
            &mut Context::default(),
            json!({"prefix": "flight:"}),
        )
        .await
        .unwrap();
    assert_eq!(
        count_a["count"], count_b["count"],
        "store states must converge after replay"
    );
    assert_eq!(count_a["count"], json!(5), "2 + 3 writes recorded");

    let _ = std::fs::remove_file(&a.flight_path);
    let _ = std::fs::remove_file(&b.flight_path);
}

#[tokio::test]
async fn replay_refuses_identity_mismatch() {
    // A tampered sidecar (args swapped) must FAIL the identity gate, not
    // silently replay a different session.
    let a = fresh_run(true, "tamper-src");
    run_session(&a).await;
    let (mut flight_entries, _) = FlightRecorder::read_entries(&a.flight_path).unwrap();
    let source_journal = a.journal.scan_entries().unwrap();

    // Tamper: swap step 0's args for step 2's.
    flight_entries[0].args = flight_entries[2].args.clone();

    let b = fresh_run(false, "tamper-dst");
    let mut refused = 0usize;
    for fe in &flight_entries {
        let expected = source_journal[fe.seq as usize]
            .args_digest
            .as_deref()
            .unwrap_or_default();
        if wm_governance::args_digest(&fe.tool, &fe.args) != expected {
            refused += 1;
            continue; // identity gate refuses — nothing executes
        }
        b.pipeline
            .dispatch_by_name(
                &b.registry,
                &fe.tool,
                &mut Context::default(),
                fe.args.clone(),
            )
            .await
            .expect("untampered steps replay");
    }
    assert_eq!(refused, 1, "tampered step refused by the identity gate");
    assert_eq!(
        b.journal.scan_entries().unwrap().len(),
        2,
        "only clean steps ran"
    );
    let _ = std::fs::remove_file(&a.flight_path);
    let _ = std::fs::remove_file(&b.flight_path);
}

#[allow(unused)]
fn type_witness(e: &FlightEntry) {}
