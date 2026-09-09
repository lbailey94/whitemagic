//! T1 twin-run replay acceptance (2026-09-09, session 7f56e966).
//!
//! The NEON transfer (`APPLICABILITY_SURVEY_NEON_TREMULOUS.md` T1) upgrades
//! the Q35b acceptance from "one replay run" to a TWIN-RUN property: the
//! SAME fixed dispatch sequence executed twice against fresh stores must
//! produce byte-identical journal streams after normalizing the only
//! volatile field (unix timestamp). The args digest (5461b09) is the
//! input-identity carrier the diff runs on.
//!
//! Two layers:
//! 1. `twin_run_journal_streams_identical` (journal level, wm-governance
//!    semantics exercised through real pipeline runs here) — full pipeline
//!    with mock tools, both arms, diff normalized entries.
//! 2. `twin_run_digest_chain_deterministic` — the digest chain alone is
//!    reproducible across independent runs of the same sequence.

use std::sync::{Arc, OnceLock};

use async_trait::async_trait;
use serde_json::{Value, json};
use wm_core::{Args, Context, EffectRow, Galaxy, Gana, Output, Resource, Tool, ToolStats};
use wm_dispatch::{
    CircuitBreakerRegistry, DispatchPipeline, RateLimiter, ToolRegistry, ToolRegistryBuilder,
};
use wm_governance::{DharmaGate, WriteAuditJournal};
use wm_memory::{Memory, MemoryStore};

// ── Deterministic mock tools ─────────────────────────────────────────

/// Writes `n` memories with content deterministically derived from args,
/// returns a deterministic output (content-hash ids, never random UUIDs).
struct DeterministicWriter {
    stats: ToolStats,
    effects: OnceLock<EffectRow>,
}

impl DeterministicWriter {
    fn new() -> Self {
        Self {
            stats: ToolStats::default(),
            effects: OnceLock::new(),
        }
    }
}

#[async_trait]
impl Tool for DeterministicWriter {
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
            let content = format!("twin:{key}:{i}");
            let mem = Memory::new(Galaxy::Codex, content);
            // content_hash is sha256 of content → deterministic; the UUID is
            // random and deliberately NOT surfaced into the journal.
            writes.push(json!(mem.metadata.content_hash));
        }
        let first_hash = writes
            .first()
            .and_then(Value::as_str)
            .unwrap_or_default()
            .to_string();
        Ok(json!({
            "id": first_hash,
            "content_hash": first_hash,
            "writes": writes,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// Pure read — declares no writes, echoes the requested id.
struct DeterministicReader {
    stats: ToolStats,
}

impl DeterministicReader {
    fn new() -> Self {
        Self {
            stats: ToolStats::default(),
        }
    }
}

#[async_trait]
impl Tool for DeterministicReader {
    fn name(&self) -> &str {
        "test.reader"
    }
    fn gana(&self) -> Gana {
        Gana::WinnowingBasket
    }
    fn effects(&self) -> &EffectRow {
        static EFFECTS: OnceLock<EffectRow> = OnceLock::new();
        EFFECTS.get_or_init(EffectRow::pure)
    }
    async fn call(&self, _ctx: &mut Context, args: Args) -> wm_core::Result<Output> {
        Ok(json!({ "echoed": args.get("id").cloned().unwrap_or(Value::Null) }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── Harness ──────────────────────────────────────────────────────────

struct Run {
    journal: Arc<WriteAuditJournal>,
    registry: ToolRegistry,
    _store_dir: tempfile::TempDir,
    pipeline: DispatchPipeline,
}

fn fresh_run() -> Run {
    let dir = tempfile::tempdir().unwrap();
    let store = Arc::new(MemoryStore::open_default(dir.path()).unwrap());
    let journal = Arc::new(WriteAuditJournal::with_flush_threshold(store, 0).unwrap());
    let mut builder = ToolRegistryBuilder::new();
    builder.register(Arc::new(DeterministicWriter::new()));
    builder.register(Arc::new(DeterministicReader::new()));
    let registry = builder.build();
    let pipeline = DispatchPipeline::new(
        Arc::new(RateLimiter::default()),
        Arc::new(CircuitBreakerRegistry::default()),
        Arc::new(DharmaGate::default()),
        None,
    )
    .with_write_audit(journal.clone());
    Run {
        journal,
        registry,
        _store_dir: dir,
        pipeline,
    }
}

/// The fixed twin sequence — identical args both runs.
const SEQUENCE: [&str; 3] = ["write-alpha-1", "read-fixed", "write-beta-3"];

async fn execute_sequence(run: &Run) {
    for step in SEQUENCE {
        match step {
            "write-alpha-1" => {
                let mut ctx = Context::default();
                run.pipeline
                    .dispatch_by_name(
                        &run.registry,
                        "test.writer",
                        &mut ctx,
                        json!({"key": "alpha", "n": 1}),
                    )
                    .await
                    .expect("dispatch 1");
            }
            "read-fixed" => {
                let mut ctx = Context::default();
                run.pipeline
                    .dispatch_by_name(
                        &run.registry,
                        "test.reader",
                        &mut ctx,
                        json!({"id": "fixed-id-0001"}),
                    )
                    .await
                    .expect("dispatch 2");
            }
            "write-beta-3" => {
                let mut ctx = Context::default();
                run.pipeline
                    .dispatch_by_name(
                        &run.registry,
                        "test.writer",
                        &mut ctx,
                        json!({"key": "beta", "n": 3}),
                    )
                    .await
                    .expect("dispatch 3");
            }
            _ => unreachable!(),
        }
    }
}

/// Normalize for the diff: the unix timestamp is the one volatile field
/// (wall clock); everything else — id, tool, memory_id, content_hash,
/// declared/reported/store deltas, success, confirmed, args_digest —
/// must match byte-for-byte.
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

// ── The twin-run property ────────────────────────────────────────────

#[tokio::test]
async fn twin_run_journal_streams_identical() {
    let a = fresh_run();
    let b = fresh_run();
    execute_sequence(&a).await;
    execute_sequence(&b).await;

    let entries_a = a.journal.scan_entries().unwrap();
    let entries_b = b.journal.scan_entries().unwrap();
    assert_eq!(entries_a.len(), 3, "sequence length journaled");
    assert_eq!(entries_a.len(), entries_b.len(), "twin stream lengths");

    let norm_a = normalize(&entries_a);
    let norm_b = normalize(&entries_b);
    assert_eq!(
        norm_a, norm_b,
        "twin runs must produce byte-identical normalized journal streams"
    );

    // The input-identity chain specifically: digests present and equal.
    for (ea, eb) in entries_a.iter().zip(entries_b.iter()) {
        let da = ea.args_digest.as_deref().expect("digest recorded");
        let db = eb.args_digest.as_deref().expect("digest recorded");
        assert_eq!(da, db, "args_digest twin equality");
        assert!(!da.is_empty());
    }
}

#[tokio::test]
async fn twin_run_digest_chain_deterministic() {
    // Same digests computed twice, independent invocations → equal chain.
    let seq = [
        ("test.writer", json!({"key": "alpha", "n": 1})),
        ("test.reader", json!({"id": "fixed-id-0001"})),
        ("test.writer", json!({"key": "beta", "n": 3})),
    ];
    let chain_a: Vec<String> = seq
        .iter()
        .map(|(t, a)| wm_governance::args_digest(t, a))
        .collect();
    let chain_b: Vec<String> = seq
        .iter()
        .map(|(t, a)| wm_governance::args_digest(t, a))
        .collect();
    assert_eq!(chain_a, chain_b, "digest chain is reproducible");
    // And distinct steps have distinct digests (identity, not collision).
    assert_ne!(chain_a[0], chain_a[1]);
    assert_ne!(chain_a[1], chain_a[2]);
    assert_ne!(chain_a[0], chain_a[2]);
}
