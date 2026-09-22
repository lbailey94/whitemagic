//! `receipts.*` tools — WM receipts core (S1).
//!
//! Six routes over the `Galaxy::Receipts` evidence store:
//! `receipts.emit` / `.verify` / `.list` / `.read` / `.disclose` / `.anchor`.
//!
//! Emission is local-only: spec `continuity-receipt/0.2`, Ed25519 under the
//! resolved WM key (see `wm_receipts::keys`), stored as a Memory whose content
//! is the standard bundle. Original bundles are never rewritten — disclosure
//! produces a *variant* plus a separate disclosure map, and anchoring only
//! appends to the unsigned `anchors` list.
//!
//! Guardrails (binding): receipts attest integrity, never goodness. No karma
//! score, no reputation, no ranking.

#![forbid(unsafe_code)]

use async_trait::async_trait;
use chrono::Utc;
use serde_json::{Value, json};
use std::sync::Arc;

use wm_core::{Context, CoreError, EffectRow, Galaxy, Gana, Resource, Tool, ToolStats};
use wm_governance::karma_ledger::KarmaLedger;
use wm_memory::{Memory, MemoryStore};
use wm_receipts::emit::{content_digest, digest_of, receipt_digest};
use wm_receipts::error::ReceiptError;
use wm_receipts::keys::{ReceiptKey, resolve_key};
use wm_receipts::profiles::{
    KarmaHeadInput, ModelRef, SessionReceiptInput, TurnEvidence, gate_id_for_store,
    karma_head_bundle, now_rfc3339, rfc3339_in_hours, session_bundle,
};
use wm_receipts::verify::verify_bundle;

use super::common::{bool_prop, int_prop, positive_int_prop, schema, str_array_prop, str_prop};
use super::session_ops::load_turns;

/// Store tag for every receipt memory.
const TAG_RECEIPT: &str = "receipt";
/// Tag naming the bundle's task id: `task:<uuid>`.
const TAG_TASK_PREFIX: &str = "task:";
/// Tag naming the stored variant: `variant:<name>`.
const TAG_VARIANT_PREFIX: &str = "variant:";
/// Original (as-emitted) variant name.
const VARIANT_ORIGINAL: &str = "original";
/// Default variant created by `receipts.disclose` redaction.
const VARIANT_REDACTED: &str = "redacted";
/// Tag marking a stored disclosure map.
const TAG_DISCLOSURE: &str = "disclosure";
/// Default turns cap for a session receipt.
const DEFAULT_TURN_LIMIT: usize = 200;

// ── shared helpers ─────────────────────────────────────────────────────

fn to_core(error: ReceiptError) -> CoreError {
    error.into_core_error()
}

/// Resolve the emission key: explicit test/override key, else the documented
/// env → store-file precedence. Only `emit` and `disclose` need a key.
fn resolve_emitter_key(
    store: &MemoryStore,
    override_key: Option<&Arc<ReceiptKey>>,
) -> Result<Arc<ReceiptKey>, CoreError> {
    match override_key {
        Some(key) => Ok(key.clone()),
        None => resolve_key(Some(store.path()))
            .map(Arc::new)
            .map_err(to_core),
    }
}

/// Parse a stored receipt memory's content into a bundle.
fn parse_bundle(memory: &Memory) -> Option<Value> {
    serde_json::from_str(&memory.content).ok()
}

/// All stored receipt bundles (memory + parsed content), oldest first.
fn stored_bundles(store: &MemoryStore) -> Result<Vec<(Memory, Value)>, CoreError> {
    let mut out = Vec::new();
    for memory in store.scan_all(Galaxy::Receipts)? {
        if !memory.metadata.tags.iter().any(|tag| tag == TAG_RECEIPT) {
            continue;
        }
        if let Some(bundle) = parse_bundle(&memory) {
            out.push((memory, bundle));
        }
    }
    out.sort_by_key(|(memory, _)| memory.metadata.created_at);
    Ok(out)
}

fn task_uuid(task_id: &str) -> String {
    task_id
        .strip_prefix("urn:uuid:")
        .unwrap_or(task_id)
        .to_string()
}

fn tag_value<'a>(memory: &'a Memory, prefix: &str) -> Option<&'a str> {
    memory
        .metadata
        .tags
        .iter()
        .find_map(|tag| tag.strip_prefix(prefix))
}

/// Find a stored bundle by task id and variant name.
fn find_bundle(
    store: &MemoryStore,
    task_id: &str,
    variant: &str,
) -> Result<Option<(Memory, Value)>, CoreError> {
    let wanted = task_uuid(task_id);
    Ok(stored_bundles(store)?.into_iter().find(|(memory, _)| {
        tag_value(memory, TAG_TASK_PREFIX) == Some(wanted.as_str())
            && tag_value(memory, TAG_VARIANT_PREFIX) == Some(variant)
    }))
}

/// Find the stored disclosure map for `(task_id, variant)`.
fn find_disclosure_map(
    store: &MemoryStore,
    task_id: &str,
    variant: &str,
) -> Result<Option<Value>, CoreError> {
    let wanted = task_uuid(task_id);
    Ok(stored_bundles(store)?
        .into_iter()
        .find(|(memory, _)| {
            memory.metadata.tags.iter().any(|tag| tag == TAG_DISCLOSURE)
                && tag_value(memory, TAG_TASK_PREFIX) == Some(wanted.as_str())
                && tag_value(memory, TAG_VARIANT_PREFIX) == Some(variant)
        })
        .map(|(_, map)| map))
}

fn issue_memory_id() -> uuid::Uuid {
    uuid::Uuid::now_v7()
}

/// Persist a bundle as a receipt memory with `kind`, optional `session_id`,
/// and a variant tag. Returns the stored memory.
fn store_bundle(
    store: &MemoryStore,
    bundle: &Value,
    kind: &str,
    session_id: Option<&str>,
    variant: &str,
) -> Result<Memory, CoreError> {
    let task_id = bundle
        .get("task_id")
        .and_then(Value::as_str)
        .ok_or_else(|| CoreError::Tool("bundle has no task_id".into()))?;
    let spec = bundle.get("spec").and_then(Value::as_str).unwrap_or("?");
    let text = serde_json::to_string(bundle).map_err(CoreError::Serde)?;
    let mut tags = vec![
        TAG_RECEIPT.to_string(),
        format!("spec:{spec}"),
        format!("kind:{kind}"),
        format!("{TAG_TASK_PREFIX}{}", task_uuid(task_id)),
        format!("{TAG_VARIANT_PREFIX}{variant}"),
    ];
    if let Some(session_id) = session_id {
        tags.push(format!("session:{session_id}"));
    }
    let mut memory = Memory::new(Galaxy::Receipts, text);
    memory.metadata.id = issue_memory_id();
    memory.metadata.tags = tags;
    memory.metadata.importance = 0.5;
    store.put(Galaxy::Receipts, &memory)?;
    Ok(memory)
}

/// Store a disclosure map beside its redacted variant.
fn store_disclosure_map(
    store: &MemoryStore,
    task_id: &str,
    variant: &str,
    map: &Value,
) -> Result<Memory, CoreError> {
    let text = serde_json::to_string(map).map_err(CoreError::Serde)?;
    let mut memory = Memory::new(Galaxy::Receipts, text);
    memory.metadata.id = issue_memory_id();
    memory.metadata.tags = vec![
        TAG_RECEIPT.to_string(),
        TAG_DISCLOSURE.to_string(),
        format!("{TAG_TASK_PREFIX}{}", task_uuid(task_id)),
        format!("{TAG_VARIANT_PREFIX}{variant}"),
    ];
    memory.metadata.importance = 0.3;
    store.put(Galaxy::Receipts, &memory)?;
    Ok(memory)
}

fn store_gate_id(store: &MemoryStore) -> Result<String, CoreError> {
    gate_id_for_store(&store.path().display().to_string()).map_err(to_core)
}

/// Resolve the session start memory: explicit id, else the most recent start.
fn resolve_session(
    store: &MemoryStore,
    session_id: Option<&str>,
) -> Result<(String, Memory), CoreError> {
    if let Some(sid) = session_id {
        let parsed = uuid::Uuid::parse_str(sid).map_err(|error| {
            CoreError::InvalidArgs(format!("invalid session_id {sid:?}: {error}"))
        })?;
        let memory = store
            .get(Galaxy::Sessions, parsed)?
            .filter(|memory| memory.metadata.tags.iter().any(|tag| tag == "start"))
            .ok_or_else(|| {
                CoreError::NotFound(format!(
                    "no session found with id {sid} — run session.start first"
                ))
            })?;
        Ok((sid.to_string(), memory))
    } else {
        let memory = store
            .scan_all(Galaxy::Sessions)?
            .into_iter()
            .filter(|memory| memory.metadata.tags.iter().any(|tag| tag == "start"))
            .max_by_key(|memory| memory.metadata.created_at)
            .ok_or_else(|| CoreError::Tool("no session found — run session.start first".into()))?;
        Ok((memory.metadata.id.to_string(), memory))
    }
}

/// Turn evidence for a session (content stays out; only its hash is bound).
fn session_turn_evidence(
    store: &MemoryStore,
    session_id: &str,
    limit: usize,
) -> Result<Vec<TurnEvidence>, CoreError> {
    let turns = load_turns(store, Some(session_id), limit, false)?;
    Ok(turns
        .iter()
        .filter_map(|(memory, value)| {
            let content = value.get("content").and_then(Value::as_str).unwrap_or("");
            Some(TurnEvidence {
                memory_id: memory.metadata.id.to_string(),
                sequence: value.get("sequence").and_then(Value::as_u64)?,
                role: value
                    .get("role")
                    .and_then(Value::as_str)
                    .unwrap_or("?")
                    .to_string(),
                turn_type: value
                    .get("turn_type")
                    .and_then(Value::as_str)
                    .unwrap_or("message")
                    .to_string(),
                timestamp_ms: value.get("timestamp").and_then(Value::as_i64).unwrap_or(0),
                content_sha256: content_digest(content),
            })
        })
        .collect())
}

/// Sanity gate: never store a bundle that does not verify locally.
fn ensure_trusted(bundle: &Value) -> Result<(), CoreError> {
    let outcome = verify_bundle(bundle, false);
    if outcome.is_trusted() {
        Ok(())
    } else {
        Err(CoreError::Tool(format!(
            "emitted bundle failed local verification: {}",
            outcome.to_value()
        )))
    }
}

/// Canonical projection of a karma read set (binds what was scanned).
fn karma_scan_digest(
    entries: &[wm_governance::karma_ledger::KarmaEntry],
) -> Result<String, CoreError> {
    let projection: Vec<Value> = entries
        .iter()
        .map(|entry| {
            json!({
                "id": entry.id,
                "tool": entry.tool,
                "payload_hash": entry.payload_hash,
                "timestamp": entry.timestamp,
                "success": entry.success,
                "tombstone": entry.tombstone,
            })
        })
        .collect();
    digest_of(&Value::Array(projection)).map_err(to_core)
}

/// Head receipt digest of a bundle (the anchor target).
fn head_digest(bundle: &Value) -> Result<String, CoreError> {
    bundle
        .get("receipts")
        .and_then(Value::as_array)
        .and_then(|receipts| receipts.last())
        .ok_or_else(|| CoreError::Tool("bundle has no receipts".into()))
        .and_then(|receipt| receipt_digest(receipt).map_err(to_core))
}

fn bundle_summary(memory: &Memory, bundle: &Value) -> Value {
    let receipts = bundle
        .get("receipts")
        .and_then(Value::as_array)
        .map_or(0, Vec::len);
    let issued_at = bundle
        .get("receipts")
        .and_then(Value::as_array)
        .and_then(|receipts| receipts.first())
        .and_then(|receipt| receipt.get("issued_at"))
        .cloned()
        .unwrap_or(Value::Null);
    json!({
        "id": bundle.get("task_id").and_then(Value::as_str).map(task_uuid),
        "task_id": bundle.get("task_id"),
        "spec": bundle.get("spec"),
        "kind": tag_value(memory, "kind:"),
        "variant": tag_value(memory, TAG_VARIANT_PREFIX),
        "session_id": tag_value(memory, "session:"),
        "issued_at": issued_at,
        "receipts": receipts,
        "anchors": bundle.get("anchors").and_then(Value::as_array).map_or(0, Vec::len),
        "stored_at": memory.metadata.created_at.to_rfc3339(),
    })
}

// ── receipts.emit ──────────────────────────────────────────────────────

/// `receipts.emit` — build, sign, verify, and store a bundle.
pub struct ReceiptsEmitTool {
    store: Arc<MemoryStore>,
    karma: Option<Arc<KarmaLedger>>,
    key: Option<Arc<ReceiptKey>>,
    stats: ToolStats,
    effects: EffectRow,
}

impl ReceiptsEmitTool {
    /// New emit tool (key resolves lazily from env/store).
    #[must_use]
    pub fn new(store: Arc<MemoryStore>, karma: Option<Arc<KarmaLedger>>) -> Self {
        Self {
            store,
            karma,
            key: None,
            stats: ToolStats::default(),
            effects: EffectRow {
                reads: vec![
                    Resource::Galaxy("sessions".into()),
                    Resource::Galaxy("karma".into()),
                ],
                writes: vec![Resource::Galaxy("receipts".into())],
                invokes: vec![],
                spawns: false,
                destructive: false,
                sandbox: wm_core::Sandbox::StoreScoped,
                cost: wm_core::CostEstimate::default(),
            },
        }
    }

    /// Pin an explicit emission key (tests; rotation).
    #[must_use]
    pub fn with_key(mut self, key: Arc<ReceiptKey>) -> Self {
        self.key = Some(key);
        self
    }

    fn emit_session(&self, args: &Value) -> Result<Value, CoreError> {
        let session_id_arg = args.get("session_id").and_then(Value::as_str);
        let limit = args
            .get("limit")
            .and_then(Value::as_u64)
            .map_or(DEFAULT_TURN_LIMIT, |value| value as usize);
        let (session_id, start_memory) = resolve_session(&self.store, session_id_arg)?;
        let start_json =
            serde_json::from_str::<Value>(&start_memory.content).unwrap_or(Value::Null);
        let user = start_json
            .get("user")
            .and_then(Value::as_str)
            .unwrap_or("default")
            .to_string();
        let turns = session_turn_evidence(&self.store, &session_id, limit)?;
        let turn_count = turns.len();
        let from_sequence = turns.iter().map(|turn| turn.sequence).min().unwrap_or(0);
        let to_sequence = turns.iter().map(|turn| turn.sequence).max().unwrap_or(0);
        let duration_ms = (Utc::now() - start_memory.metadata.created_at)
            .num_milliseconds()
            .max(0) as u64;
        let key = resolve_emitter_key(&self.store, self.key.as_ref())?;

        let bundle = session_bundle(
            &key,
            &SessionReceiptInput {
                session_id: session_id.clone(),
                user,
                session_start_id: start_memory.metadata.id.to_string(),
                session_start_created_at: start_memory.metadata.created_at.to_rfc3339(),
                store_gate_id: store_gate_id(&self.store)?,
                issued_at: now_rfc3339(),
                expires_at: rfc3339_in_hours(24),
                from_sequence,
                to_sequence,
                duration_ms,
                turns,
                model: ModelRef::wm_local("session-chronicle"),
            },
        )
        .map_err(to_core)?;
        ensure_trusted(&bundle)?;
        let memory = store_bundle(
            &self.store,
            &bundle,
            "session",
            Some(&session_id),
            VARIANT_ORIGINAL,
        )?;
        Ok(json!({
            "kind": "session",
            "session_id": session_id,
            "turn_count": turn_count,
            "memory_id": memory.metadata.id.to_string(),
        }))
    }

    fn emit_karma_head(&self, _args: &Value) -> Result<Value, CoreError> {
        let ledger = self.karma.as_ref().ok_or_else(|| {
            CoreError::Tool(
                "karma ledger unavailable on this server (read-only or no ledger)".into(),
            )
        })?;
        let deep = ledger.verify_integrity_deep()?;
        let entries = ledger.scan_entries()?;
        let key = resolve_emitter_key(&self.store, self.key.as_ref())?;
        let bundle = karma_head_bundle(
            &key,
            &KarmaHeadInput {
                entry_count: ledger.next_id(),
                chain_head: ledger.chain_head(),
                merkle_root: ledger.get_merkle_root()?.map(|checkpoint| checkpoint.root),
                scans_digest: karma_scan_digest(&entries)?,
                integrity_ok: deep.chain.valid,
                store_gate_id: store_gate_id(&self.store)?,
                issued_at: now_rfc3339(),
                expires_at: rfc3339_in_hours(24),
                model: ModelRef::wm_local("karma-ledger"),
            },
        )
        .map_err(to_core)?;
        ensure_trusted(&bundle)?;
        let memory = store_bundle(&self.store, &bundle, "karma_head", None, VARIANT_ORIGINAL)?;
        Ok(json!({
            "kind": "karma_head",
            "entry_count": ledger.next_id(),
            "chain_head": ledger.chain_head(),
            "fully_deep": deep.fully_deep,
            "memory_id": memory.metadata.id.to_string(),
        }))
    }

    fn emit(&self, args: &Value) -> Result<Value, CoreError> {
        let kind = args
            .get("kind")
            .and_then(Value::as_str)
            .unwrap_or("session");
        let mut result = match kind {
            "session" => self.emit_session(args)?,
            "karma_head" => self.emit_karma_head(args)?,
            other => {
                return Err(CoreError::InvalidArgs(format!(
                    "unknown receipt kind {other:?} (expected session | karma_head)"
                )));
            }
        };
        let id = result
            .get("memory_id")
            .and_then(Value::as_str)
            .and_then(|memory_id| uuid::Uuid::parse_str(memory_id).ok())
            .and_then(|memory_id| self.store.get(Galaxy::Receipts, memory_id).ok().flatten())
            .and_then(|memory| parse_bundle(&memory));
        let Some(bundle) = id else {
            return Err(CoreError::Tool(
                "stored receipt could not be re-read".into(),
            ));
        };
        let task_id = bundle
            .get("task_id")
            .and_then(Value::as_str)
            .map(task_uuid)
            .unwrap_or_default();
        result["id"] = json!(task_id);
        result["task_id"] = bundle.get("task_id").cloned().unwrap_or(Value::Null);
        result["verdict"] = json!(verify_bundle(&bundle, false).verdict);
        result["digest"] = json!(head_digest(&bundle)?);
        result["status"] = json!("success");

        if let Some(out) = args.get("out").and_then(Value::as_str) {
            let text = serde_json::to_string_pretty(&bundle).map_err(CoreError::Serde)?;
            std::fs::write(out, text)?;
            result["out"] = json!(out);
        }
        Ok(result)
    }
}

#[async_trait]
impl Tool for ReceiptsEmitTool {
    fn input_schema(&self) -> Value {
        schema(
            &json!({
                "kind": str_prop("Bundle kind: session (default) | karma_head"),
                "session_id": str_prop("Session UUID (session kind; default: most recent session)"),
                "limit": positive_int_prop("Maximum turns covered (session kind; default 200)"),
                "out": str_prop("Optional path to also write the bundle JSON for external verification"),
            }),
            &[],
        )
    }

    fn name(&self) -> &str {
        "receipts.emit"
    }

    fn gana(&self) -> Gana {
        Gana::Willow
    }

    fn effects(&self) -> &EffectRow {
        &self.effects
    }

    fn description(&self) -> &str {
        "Emit a continuity-receipt bundle (session evidence or karma-chain-head attestation)"
    }

    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        self.emit(&args)
    }

    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── receipts.verify ────────────────────────────────────────────────────

/// `receipts.verify` — local verification of a stored or supplied bundle.
pub struct ReceiptsVerifyTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl ReceiptsVerifyTool {
    /// New verify tool.
    #[must_use]
    pub fn new(store: Arc<MemoryStore>) -> Self {
        Self {
            store,
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![Resource::Galaxy("receipts".into())]),
        }
    }
}

#[async_trait]
impl Tool for ReceiptsVerifyTool {
    fn input_schema(&self) -> Value {
        schema(
            &json!({
                "id": str_prop("Stored receipt task id (UUID or urn:uuid:)"),
                "bundle": json!({"type": "object", "description": "Inline bundle to verify (alternative to id)"}),
                "variant": str_prop("Stored variant (default original)"),
                "require_anchor": bool_prop("Fail-closed: without an anchor the verdict is PROVISIONAL"),
            }),
            &[],
        )
    }

    fn name(&self) -> &str {
        "receipts.verify"
    }

    fn gana(&self) -> Gana {
        Gana::Willow
    }

    fn effects(&self) -> &EffectRow {
        &self.effects
    }

    fn description(&self) -> &str {
        "Verify a continuity-receipt bundle (verify, do not judge)"
    }

    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let require_anchor = args
            .get("require_anchor")
            .and_then(Value::as_bool)
            .unwrap_or(false);
        let variant = args
            .get("variant")
            .and_then(Value::as_str)
            .unwrap_or(VARIANT_ORIGINAL);
        let (task_id, bundle) = if let Some(bundle) = args.get("bundle") {
            (
                bundle.get("task_id").and_then(Value::as_str).map(task_uuid),
                bundle.clone(),
            )
        } else {
            let id = args
                .get("id")
                .and_then(Value::as_str)
                .ok_or_else(|| CoreError::InvalidArgs("provide 'id' or 'bundle'".into()))?;
            let (_, bundle) = find_bundle(&self.store, id, variant)?.ok_or_else(|| {
                CoreError::NotFound(format!("no stored receipt {id:?} variant {variant:?}"))
            })?;
            (Some(task_uuid(id)), bundle)
        };
        let outcome = verify_bundle(&bundle, require_anchor);
        Ok(json!({
            "status": "success",
            "id": task_id,
            "variant": variant,
            "require_anchor": require_anchor,
            "result": outcome.to_value(),
        }))
    }

    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── receipts.list ──────────────────────────────────────────────────────

/// `receipts.list` — summaries of stored receipts.
pub struct ReceiptsListTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl ReceiptsListTool {
    /// New list tool.
    #[must_use]
    pub fn new(store: Arc<MemoryStore>) -> Self {
        Self {
            store,
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![Resource::Galaxy("receipts".into())]),
        }
    }
}

#[async_trait]
impl Tool for ReceiptsListTool {
    fn input_schema(&self) -> Value {
        schema(
            &json!({
                "limit": positive_int_prop("Maximum entries (default 20)"),
                "offset": int_prop("Skip this many entries (default 0)"),
                "kind": str_prop("Filter: session | karma_head"),
                "session_id": str_prop("Filter by session id"),
                "variant": str_prop("Filter by variant (default: all variants)"),
            }),
            &[],
        )
    }

    fn name(&self) -> &str {
        "receipts.list"
    }

    fn gana(&self) -> Gana {
        Gana::Willow
    }

    fn effects(&self) -> &EffectRow {
        &self.effects
    }

    fn description(&self) -> &str {
        "List stored continuity receipts (evidence inventory)"
    }

    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let limit = args
            .get("limit")
            .and_then(Value::as_u64)
            .map_or(20, |value| value as usize);
        let offset = args
            .get("offset")
            .and_then(Value::as_u64)
            .map_or(0, |value| value as usize);
        let kind = args.get("kind").and_then(Value::as_str);
        let session_id = args.get("session_id").and_then(Value::as_str);
        let variant = args.get("variant").and_then(Value::as_str);

        let mut items: Vec<Value> = Vec::new();
        for (memory, bundle) in stored_bundles(&self.store)? {
            if memory.metadata.tags.iter().any(|tag| tag == TAG_DISCLOSURE) {
                continue;
            }
            if kind.is_some_and(|wanted| tag_value(&memory, "kind:") != Some(wanted)) {
                continue;
            }
            if session_id.is_some_and(|wanted| tag_value(&memory, "session:") != Some(wanted)) {
                continue;
            }
            if variant.is_some_and(|wanted| tag_value(&memory, TAG_VARIANT_PREFIX) != Some(wanted))
            {
                continue;
            }
            items.push(bundle_summary(&memory, &bundle));
        }
        items.reverse();
        let total = items.len();
        let page: Vec<Value> = items.into_iter().skip(offset).take(limit).collect();
        Ok(json!({
            "status": "success",
            "total": total,
            "limit": limit,
            "offset": offset,
            "receipts": page,
        }))
    }

    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── receipts.read ──────────────────────────────────────────────────────

/// `receipts.read` — full bundle plus its verification result.
pub struct ReceiptsReadTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl ReceiptsReadTool {
    /// New read tool.
    #[must_use]
    pub fn new(store: Arc<MemoryStore>) -> Self {
        Self {
            store,
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![Resource::Galaxy("receipts".into())]),
        }
    }
}

#[async_trait]
impl Tool for ReceiptsReadTool {
    fn input_schema(&self) -> Value {
        schema(
            &json!({
                "id": str_prop("Stored receipt task id (UUID or urn:uuid:)"),
                "variant": str_prop("Stored variant (default original)"),
                "require_anchor": bool_prop("Verify with anchor required"),
            }),
            &["id"],
        )
    }

    fn name(&self) -> &str {
        "receipts.read"
    }

    fn gana(&self) -> Gana {
        Gana::Willow
    }

    fn effects(&self) -> &EffectRow {
        &self.effects
    }

    fn description(&self) -> &str {
        "Read a stored continuity receipt (bundle + verification)"
    }

    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let id = args
            .get("id")
            .and_then(Value::as_str)
            .ok_or_else(|| CoreError::InvalidArgs("missing 'id'".into()))?;
        let variant = args
            .get("variant")
            .and_then(Value::as_str)
            .unwrap_or(VARIANT_ORIGINAL);
        let require_anchor = args
            .get("require_anchor")
            .and_then(Value::as_bool)
            .unwrap_or(false);
        let (memory, bundle) = find_bundle(&self.store, id, variant)?.ok_or_else(|| {
            CoreError::NotFound(format!("no stored receipt {id:?} variant {variant:?}"))
        })?;
        let outcome = verify_bundle(&bundle, require_anchor);
        Ok(json!({
            "status": "success",
            "id": task_uuid(id),
            "variant": variant,
            "memory_id": memory.metadata.id.to_string(),
            "verification": outcome.to_value(),
            "bundle": bundle,
        }))
    }

    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── receipts.disclose ──────────────────────────────────────────────────

/// `receipts.disclose` — redaction variants and selective reveal.
pub struct ReceiptsDiscloseTool {
    store: Arc<MemoryStore>,
    key: Option<Arc<ReceiptKey>>,
    stats: ToolStats,
    effects: EffectRow,
}

impl ReceiptsDiscloseTool {
    /// New disclose tool.
    #[must_use]
    pub fn new(store: Arc<MemoryStore>) -> Self {
        Self {
            store,
            key: None,
            stats: ToolStats::default(),
            effects: EffectRow {
                reads: vec![Resource::Galaxy("receipts".into())],
                writes: vec![Resource::Galaxy("receipts".into())],
                invokes: vec![],
                spawns: false,
                destructive: false,
                sandbox: wm_core::Sandbox::StoreScoped,
                cost: wm_core::CostEstimate::default(),
            },
        }
    }

    /// Pin an explicit signing key (tests; rotation).
    #[must_use]
    pub fn with_key(mut self, key: Arc<ReceiptKey>) -> Self {
        self.key = Some(key);
        self
    }

    fn paths(args: &Value) -> Result<Vec<String>, CoreError> {
        args.get("paths")
            .and_then(Value::as_array)
            .map(|paths| {
                paths
                    .iter()
                    .filter_map(Value::as_str)
                    .map(str::to_string)
                    .collect::<Vec<_>>()
            })
            .filter(|paths| !paths.is_empty())
            .ok_or_else(|| {
                CoreError::InvalidArgs("provide 'paths' (receipts[i].body.field)".into())
            })
    }

    fn redact(&self, args: &Value) -> Result<Value, CoreError> {
        let id = args
            .get("id")
            .and_then(Value::as_str)
            .ok_or_else(|| CoreError::InvalidArgs("missing 'id'".into()))?;
        let paths = Self::paths(args)?;
        let variant = args
            .get("variant")
            .and_then(Value::as_str)
            .unwrap_or(VARIANT_REDACTED);
        let (memory, bundle) = find_bundle(&self.store, id, VARIANT_ORIGINAL)?
            .ok_or_else(|| CoreError::NotFound(format!("no stored receipt {id:?}")))?;
        let kind = tag_value(&memory, "kind:").unwrap_or("session").to_string();
        let session_id = tag_value(&memory, "session:").map(str::to_string);
        let key = resolve_emitter_key(&self.store, self.key.as_ref())?;
        let (redacted, map) = wm_receipts::redact_bundle(&key, &bundle, &paths).map_err(to_core)?;
        // Soundness gate: the redacted form must verify TRUSTED once the full
        // disclosure map is attached. The stored variant itself is PROVISIONAL
        // (withheld content) until a reveal attaches a subset.
        let full = wm_receipts::attach_map(&redacted, &map).map_err(to_core)?;
        ensure_trusted(&full)?;
        store_bundle(
            &self.store,
            &redacted,
            &kind,
            session_id.as_deref(),
            variant,
        )?;
        store_disclosure_map(&self.store, id, variant, &map)?;
        Ok(json!({
            "status": "success",
            "action": "redact",
            "id": task_uuid(id),
            "variant": variant,
            "paths": paths,
            "verdict": verify_bundle(&full, false).verdict,
            "stored_verdict": verify_bundle(&redacted, false).verdict,
            "digest": head_digest(&redacted)?,
        }))
    }

    fn reveal(&self, args: &Value) -> Result<Value, CoreError> {
        let id = args
            .get("id")
            .and_then(Value::as_str)
            .ok_or_else(|| CoreError::InvalidArgs("missing 'id'".into()))?;
        let paths = Self::paths(args)?;
        let variant = args
            .get("variant")
            .and_then(Value::as_str)
            .unwrap_or(VARIANT_REDACTED);
        let (_, bundle) = find_bundle(&self.store, id, variant)?.ok_or_else(|| {
            CoreError::NotFound(format!("no stored receipt {id:?} variant {variant:?}"))
        })?;
        let map = find_disclosure_map(&self.store, id, variant)?.ok_or_else(|| {
            CoreError::NotFound(format!("no disclosure map for {id:?} variant {variant:?}"))
        })?;
        let package = wm_receipts::reveal_paths(&bundle, &map, &paths).map_err(to_core)?;
        let outcome = verify_bundle(&package, false);
        Ok(json!({
            "status": "success",
            "action": "reveal",
            "id": task_uuid(id),
            "variant": variant,
            "disclosed_paths": paths,
            "verification": outcome.to_value(),
            "bundle": package,
        }))
    }
}

#[async_trait]
impl Tool for ReceiptsDiscloseTool {
    fn input_schema(&self) -> Value {
        schema(
            &json!({
                "id": str_prop("Stored receipt task id"),
                "action": str_prop("redact (default; creates a variant) | reveal (subset of a map)"),
                "paths": str_array_prop("Field paths, e.g. receipts[1].body.action"),
                "variant": str_prop("Variant name (default redacted)"),
            }),
            &["id", "paths"],
        )
    }

    fn name(&self) -> &str {
        "receipts.disclose"
    }

    fn gana(&self) -> Gana {
        Gana::Willow
    }

    fn effects(&self) -> &EffectRow {
        &self.effects
    }

    fn description(&self) -> &str {
        "Selective disclosure: redact into a re-signed variant, or reveal a subset"
    }

    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        match args
            .get("action")
            .and_then(Value::as_str)
            .unwrap_or("redact")
        {
            "redact" => self.redact(&args),
            "reveal" => self.reveal(&args),
            other => Err(CoreError::InvalidArgs(format!(
                "unknown action {other:?} (expected redact | reveal)"
            ))),
        }
    }

    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── receipts.anchor ────────────────────────────────────────────────────

/// `receipts.anchor` — append an unsigned anchor commitment to a bundle.
pub struct ReceiptsAnchorTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl ReceiptsAnchorTool {
    /// New anchor tool.
    #[must_use]
    pub fn new(store: Arc<MemoryStore>) -> Self {
        Self {
            store,
            stats: ToolStats::default(),
            effects: EffectRow {
                reads: vec![Resource::Galaxy("receipts".into())],
                writes: vec![Resource::Galaxy("receipts".into())],
                invokes: vec![],
                spawns: false,
                destructive: false,
                sandbox: wm_core::Sandbox::StoreScoped,
                cost: wm_core::CostEstimate::default(),
            },
        }
    }
}

#[async_trait]
impl Tool for ReceiptsAnchorTool {
    fn input_schema(&self) -> Value {
        schema(
            &json!({
                "id": str_prop("Stored receipt task id"),
                "variant": str_prop("Stored variant (default original)"),
                "proof_path": str_prop("Optional external proof file (its SHA-256 is recorded, never the file)"),
            }),
            &["id"],
        )
    }

    fn name(&self) -> &str {
        "receipts.anchor"
    }

    fn gana(&self) -> Gana {
        Gana::Willow
    }

    fn effects(&self) -> &EffectRow {
        &self.effects
    }

    fn description(&self) -> &str {
        "Anchor a receipt digest in the bundle (hash-only, or with an external proof digest)"
    }

    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let id = args
            .get("id")
            .and_then(Value::as_str)
            .ok_or_else(|| CoreError::InvalidArgs("missing 'id'".into()))?;
        let variant = args
            .get("variant")
            .and_then(Value::as_str)
            .unwrap_or(VARIANT_ORIGINAL);
        let (memory, mut bundle) = find_bundle(&self.store, id, variant)?.ok_or_else(|| {
            CoreError::NotFound(format!("no stored receipt {id:?} variant {variant:?}"))
        })?;
        let head = bundle
            .get("receipts")
            .and_then(Value::as_array)
            .and_then(|receipts| receipts.last())
            .ok_or_else(|| CoreError::Tool("bundle has no receipts".into()))?;
        let target = head
            .get("receipt_id")
            .and_then(Value::as_str)
            .ok_or_else(|| CoreError::Tool("head receipt has no receipt_id".into()))?
            .to_string();
        let digest = receipt_digest(head).map_err(to_core)?;

        let mut anchor = json!({ "target": target, "hash": digest });
        if let Some(proof_path) = args.get("proof_path").and_then(Value::as_str) {
            let bytes = std::fs::read(proof_path)?;
            let proof_kind = if std::path::Path::new(proof_path)
                .extension()
                .is_some_and(|extension| extension.eq_ignore_ascii_case("ots"))
            {
                "opentimestamps"
            } else {
                "custom"
            };
            anchor["anchor"] = json!({
                "type": proof_kind,
                "proof_sha256": content_digest(&String::from_utf8_lossy(&bytes)),
                "proof_bytes": bytes.len(),
            });
        }
        let anchors = bundle.get_mut("anchors").and_then(Value::as_array_mut);
        match anchors {
            Some(list) => list.push(anchor),
            None => {
                bundle["anchors"] = json!([anchor]);
            }
        }
        ensure_trusted(&bundle)?;
        let text = serde_json::to_string(&bundle).map_err(CoreError::Serde)?;
        let mut updated = memory;
        updated.content = text;
        self.store.put(Galaxy::Receipts, &updated)?;
        Ok(json!({
            "status": "success",
            "id": task_uuid(id),
            "variant": variant,
            "anchors": bundle["anchors"].as_array().map_or(0, Vec::len),
            "head_digest": digest,
        }))
    }

    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── auto-emit hook ─────────────────────────────────────────────────────

/// True when the deployment opted into authority-seam auto-emission.
#[must_use]
pub fn auto_emit_enabled() -> bool {
    std::env::var("WM_RECEIPTS_AUTOEMIT").is_ok_and(|value| value.trim() == "1")
}

/// Authority-seam hook: attests the karma-chain head after a successful
/// destructive dispatch.
///
/// Bounded by `WM_RECEIPTS_AUTOEMIT_MIN_SECS` (default 60): at most one
/// emission per window, so a burst of destructive dispatches cannot flood the
/// evidence store. Failures are logged and never touch the dispatch result.
pub struct AutoEmitReceiptHook {
    store: Arc<MemoryStore>,
    karma: Option<Arc<KarmaLedger>>,
    min_interval_secs: u64,
    last_emit_secs: std::sync::atomic::AtomicU64,
}

impl AutoEmitReceiptHook {
    /// New hook over the store's receipts galaxy and karma ledger.
    #[must_use]
    pub fn new(store: Arc<MemoryStore>, karma: Option<Arc<KarmaLedger>>) -> Self {
        let min_interval_secs = std::env::var("WM_RECEIPTS_AUTOEMIT_MIN_SECS")
            .ok()
            .and_then(|value| value.trim().parse::<u64>().ok())
            .unwrap_or(60);
        Self {
            store,
            karma,
            min_interval_secs,
            last_emit_secs: std::sync::atomic::AtomicU64::new(0),
        }
    }

    /// Reserve the emission slot; `false` means throttled or contended.
    fn reserve(&self) -> bool {
        let now = Utc::now().timestamp().max(0) as u64;
        let last = self
            .last_emit_secs
            .load(std::sync::atomic::Ordering::Relaxed);
        if now.saturating_sub(last) < self.min_interval_secs {
            return false;
        }
        self.last_emit_secs
            .compare_exchange(
                last,
                now,
                std::sync::atomic::Ordering::Relaxed,
                std::sync::atomic::Ordering::Relaxed,
            )
            .is_ok()
    }
}

impl wm_dispatch::ReceiptDispatchHook for AutoEmitReceiptHook {
    fn on_authority_dispatch(&self, tool: &str, elapsed: std::time::Duration) {
        if !self.reserve() {
            return;
        }
        let emitter = ReceiptsEmitTool::new(self.store.clone(), self.karma.clone());
        match emitter.emit_karma_head(&json!({})) {
            Ok(_) => tracing::info!(
                tool = tool,
                elapsed_ms = elapsed.as_millis(),
                "receipts auto-emit: karma-chain head attested"
            ),
            Err(error) => tracing::warn!(
                tool = tool,
                error = %error,
                "receipts auto-emit failed (dispatch unaffected)"
            ),
        }
    }
}

// ── registration ───────────────────────────────────────────────────────

/// Register the six `receipts.*` routes.
#[must_use]
pub fn register_receipts(
    registry: &wm_dispatch::ToolRegistry,
    store: &Arc<MemoryStore>,
    karma: Option<Arc<KarmaLedger>>,
) -> wm_dispatch::ToolRegistry {
    registry
        .register(Arc::new(ReceiptsEmitTool::new(store.clone(), karma)))
        .register(Arc::new(ReceiptsVerifyTool::new(store.clone())))
        .register(Arc::new(ReceiptsListTool::new(store.clone())))
        .register(Arc::new(ReceiptsReadTool::new(store.clone())))
        .register(Arc::new(ReceiptsDiscloseTool::new(store.clone())))
        .register(Arc::new(ReceiptsAnchorTool::new(store.clone())))
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    fn test_store() -> (tempfile::TempDir, Arc<MemoryStore>) {
        let dir = tempfile::tempdir().expect("tempdir");
        let store = Arc::new(MemoryStore::open_default(dir.path()).expect("store"));
        (dir, store)
    }

    fn test_key() -> Arc<ReceiptKey> {
        Arc::new(ReceiptKey::from_seed([7u8; 32]))
    }

    fn seed_session(store: &MemoryStore) -> String {
        let start = Memory::new(
            Galaxy::Sessions,
            json!({"type": "session_start", "title": "S1 test", "user": "default", "timestamp": 1_758_500_000_000_i64})
                .to_string(),
        )
        .with_tags(vec!["session".into(), "start".into()]);
        let session_id = start.metadata.id.to_string();
        store.put(Galaxy::Sessions, &start).expect("put start");
        for sequence in 1..=2 {
            let turn = Memory::new(
                Galaxy::Sessions,
                json!({
                    "type": "session_turn",
                    "session_id": session_id,
                    "sequence": sequence,
                    "role": if sequence == 1 { "user" } else { "ai" },
                    "turn_type": "message",
                    "importance": 0.5,
                    "content": format!("turn number {sequence}"),
                    "timestamp": 1_758_500_000_000_i64 + sequence,
                })
                .to_string(),
            )
            .with_tags(vec!["session".into(), "turn".into()]);
            store.put(Galaxy::Sessions, &turn).expect("put turn");
        }
        session_id
    }

    async fn call(tool: &dyn Tool, args: Value) -> Value {
        let mut context = Context::new(wm_core::BrainWave::Beta);
        tool.call(&mut context, args).await.expect("tool call")
    }

    #[tokio::test]
    async fn emit_verify_list_read_round_trip() {
        let (_dir, store) = test_store();
        let session_id = seed_session(&store);
        let emit = ReceiptsEmitTool::new(store.clone(), None).with_key(test_key());
        let emitted = call(&emit, json!({"kind": "session"})).await;
        assert_eq!(emitted["status"], "success");
        assert_eq!(emitted["verdict"], "TRUSTED");
        let id = emitted["id"].as_str().expect("id").to_string();

        let verify = ReceiptsVerifyTool::new(store.clone());
        let verified = call(&verify, json!({"id": id})).await;
        assert_eq!(verified["result"]["verdict"], "TRUSTED");

        let list = ReceiptsListTool::new(store.clone());
        let listed = call(&list, json!({"session_id": session_id})).await;
        assert_eq!(listed["total"], 1, "{listed}");
        assert_eq!(listed["receipts"][0]["kind"], "session");

        let read = ReceiptsReadTool::new(store.clone());
        let read_value = call(&read, json!({"id": id})).await;
        assert_eq!(read_value["verification"]["verdict"], "TRUSTED");
        assert_eq!(
            read_value["bundle"]["receipts"]
                .as_array()
                .expect("receipts")
                .len(),
            4
        );
    }

    #[tokio::test]
    async fn redact_variant_and_reveal() {
        let (_dir, store) = test_store();
        let key = test_key();
        let mut chain = wm_receipts::TaskChain::new(key.as_ref().clone());
        chain
            .add(
                "session.pass.created",
                json!({
                    "gate_id": "wm-local:test",
                    "mandala_class": "gate-lite",
                    "quotas": {"cpu_ms": 0, "mem_mb": 0, "disk_mb": 0, "wall_ms": 0},
                    "expires_at": "2026-09-23T10:00:00Z",
                    "policy_version": "wm-9.2.3/receipts-v1",
                    "mandate_ref": "sha256:0000000000000000000000000000000000000000000000000000000000000000",
                    "agent_id": "default",
                    "note": "optional-field",
                }),
                "2026-09-22T10:00:00Z",
            )
            .expect("pass");
        chain
            .add(
                "task.termination",
                json!({
                    "reason": "completed",
                    "limits_at_stop": {"cpu_ms": 0, "wall_ms": 0, "spend_minor": 0, "currency": "USD"},
                    "remaining": {},
                }),
                "2026-09-22T10:00:00Z",
            )
            .expect("termination");
        let bundle = chain.bundle();
        assert!(verify_bundle(&bundle, false).is_trusted());
        store_bundle(&store, &bundle, "session", None, VARIANT_ORIGINAL).expect("store");
        let id = task_uuid(bundle["task_id"].as_str().expect("task_id"));

        let disclose = ReceiptsDiscloseTool::new(store.clone()).with_key(key.clone());
        let redacted = call(
            &disclose,
            json!({"id": id, "action": "redact", "paths": ["receipts[0].body.note"]}),
        )
        .await;
        assert_eq!(redacted["action"], "redact");
        assert_eq!(redacted["verdict"], "TRUSTED", "{redacted}");
        assert_eq!(redacted["stored_verdict"], "PROVISIONAL", "{redacted}");

        let revealed = call(
            &disclose,
            json!({"id": id, "action": "reveal", "paths": ["receipts[0].body.note"]}),
        )
        .await;
        assert_eq!(revealed["action"], "reveal");
        assert_eq!(
            revealed["verification"]["verdict"], "TRUSTED",
            "the revealed subset restores the full map entry"
        );
    }

    #[tokio::test]
    async fn anchor_appends_and_verifies() {
        let (_dir, store) = test_store();
        seed_session(&store);
        let emit = ReceiptsEmitTool::new(store.clone(), None).with_key(test_key());
        let emitted = call(&emit, json!({"kind": "session"})).await;
        let id = emitted["id"].as_str().expect("id").to_string();

        let anchor = ReceiptsAnchorTool::new(store.clone());
        let anchored = call(&anchor, json!({"id": id})).await;
        assert_eq!(anchored["anchors"], 1);

        let verify = ReceiptsVerifyTool::new(store.clone());
        let verified = call(&verify, json!({"id": id, "require_anchor": true})).await;
        assert_eq!(verified["result"]["verdict"], "TRUSTED", "{verified}");
    }

    #[tokio::test]
    async fn karma_head_attestation_binds_a_real_ledger() {
        let (_dir, store) = test_store();
        let ledger = Arc::new(KarmaLedger::new(store.clone()).expect("ledger"));
        for _ in 0..3 {
            ledger
                .record("memory.create", true, 1, true)
                .expect("record karma entry");
        }
        let expected_head = ledger.chain_head();
        let expected_count = ledger.next_id();
        assert_ne!(expected_head, "GENESIS_BINDU");

        let emit = ReceiptsEmitTool::new(store.clone(), Some(ledger.clone())).with_key(test_key());
        let emitted = call(&emit, json!({"kind": "karma_head"})).await;
        assert_eq!(emitted["verdict"], "TRUSTED", "{emitted}");
        assert_eq!(emitted["chain_head"], expected_head);
        assert_eq!(emitted["entry_count"], expected_count);
        assert_eq!(emitted["fully_deep"], true);

        // The stored bundle's delivery record binds the attested head.
        let id = emitted["id"].as_str().expect("id").to_string();
        let read = ReceiptsReadTool::new(store.clone());
        let read_value = call(&read, json!({"id": id})).await;
        assert_eq!(
            read_value["bundle"]["receipts"][2]["body"]["response_hash"],
            expected_head
        );
    }

    #[tokio::test]
    async fn karma_head_emission_requires_ledger() {
        let (_dir, store) = test_store();
        let emit = ReceiptsEmitTool::new(store.clone(), None).with_key(test_key());
        let mut context = Context::new(wm_core::BrainWave::Beta);
        let error = emit
            .call(&mut context, json!({"kind": "karma_head"}))
            .await
            .expect_err("no ledger");
        assert!(error.to_string().contains("karma ledger unavailable"));
    }

    #[tokio::test]
    async fn auto_emit_hook_stores_a_throttled_karma_head_receipt() {
        use wm_dispatch::ReceiptDispatchHook as _;

        let (_dir, store) = test_store();
        let ledger = Arc::new(KarmaLedger::new(store.clone()).expect("ledger"));
        ledger
            .record("memory.delete", true, 1, true)
            .expect("record karma entry");

        // No env key here: the hook resolves the store key file, creating it
        // on first use (the zero-setup default) — exercises that path too.
        let hook = AutoEmitReceiptHook::new(store.clone(), Some(ledger));
        hook.on_authority_dispatch("memory.delete", std::time::Duration::from_millis(1));

        let bundles = stored_bundles(&store).expect("stored bundles");
        assert_eq!(bundles.len(), 1, "one authority-seam emission");
        assert_eq!(tag_value(&bundles[0].0, "kind:"), Some("karma_head"));
        assert!(verify_bundle(&bundles[0].1, false).is_trusted());
        assert!(
            store
                .path()
                .join(wm_receipts::keys::RECEIPT_KEY_FILE)
                .exists(),
            "the store receipt key file is the zero-setup default"
        );

        // Throttle window: a second immediate dispatch must not emit again.
        hook.on_authority_dispatch("memory.delete", std::time::Duration::from_millis(1));
        assert_eq!(
            stored_bundles(&store).expect("stored bundles").len(),
            1,
            "throttled within WM_RECEIPTS_AUTOEMIT_MIN_SECS"
        );
    }

    #[test]
    fn summaries_hide_disclosure_maps() {
        let (_dir, store) = test_store();
        seed_session(&store);
        let bundle = wm_receipts::profiles::session_bundle(
            &test_key(),
            &SessionReceiptInput {
                session_id: "s".into(),
                user: "default".into(),
                session_start_id: "x".into(),
                session_start_created_at: "2026-09-22T09:00:00Z".into(),
                store_gate_id: "wm-local:test".into(),
                issued_at: "2026-09-22T10:00:00Z".into(),
                expires_at: "2026-09-23T10:00:00Z".into(),
                from_sequence: 1,
                to_sequence: 1,
                duration_ms: 1,
                turns: vec![],
                model: ModelRef::wm_local("session-chronicle"),
            },
        )
        .expect("bundle");
        let memory =
            store_bundle(&store, &bundle, "session", None, VARIANT_ORIGINAL).expect("store");
        assert_eq!(tag_value(&memory, TAG_VARIANT_PREFIX), Some("original"));
        let summary = bundle_summary(&memory, &bundle);
        assert_eq!(summary["receipts"], 4);
    }
}
