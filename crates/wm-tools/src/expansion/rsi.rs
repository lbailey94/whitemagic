//! Recursive Self-Improvement (RSI) tools — Phase 1: Friction logging.
//!
//! Tools for logging and reviewing friction points encountered during
//! daily use of WhiteMagic v5. This is the data-collection phase of RSI:
//! no autonomous cycles run here. The friction data feeds Phase 2
//! (codebase-grounded improvement cycles) and Phase 3 (adversarial
//! self-testing).
//!
//! Design principles (from v2 investigation):
//! - All tools are human-triggered, not autonomous
//! - Friction entries are grounded in real usage, not self-inspection
//! - Every entry has structured fields for actionable analysis
//! - The outward spiral is maintained: friction → analysis → improvement → new friction

use async_trait::async_trait;

use serde::{Deserialize, Serialize};
use serde_json::{Value, json};
use std::collections::hash_map::DefaultHasher;
use std::hash::{Hash, Hasher};
use std::sync::Arc;
use wm_core::{Args, Output};
use wm_core::{Capability, Context, EffectRow, Gana, Resource, Tool, ToolStats, ToolStatsSnapshot};
use wm_governance::KarmaLedger;
use wm_memory::{Memory, MemoryStore, SearchEngine};
use wm_workspace::{CoreId, EventType, GlobalWorkspace};

// ── DispatchTelemetry: Rich friction envelope (WS-1) ───────────────────

/// Telemetry captured from the dispatch path for rich friction logging.
///
/// This struct carries all data already computed during a tool dispatch,
/// enabling the outward spiral: each friction entry carries 15+ dimensions
/// of context, revealing friction invisible at lower resolution.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DispatchTelemetry {
    pub tool: String,
    pub success: bool,
    pub latency_ms: f32,
    pub error: String,
    pub brain_wave: String,
    pub effectiveness: f32,
    pub karma_debt: f32,
    pub self_model_confidence: f32,
    pub drive_bias_confidence: f32,
    pub citta_coherence: f32,
    pub citta_valence: f32,
    pub tool_stats: ToolStatsSnapshot,
    pub routed_via_wm: bool,
    pub arg_size_bytes: usize,
    pub response_size_bytes: usize,
}

impl DispatchTelemetry {
    /// Build a minimal telemetry from just tool name, error, and latency.
    /// Used when the full dispatch context is not available (e.g. manual tool call).
    #[must_use]
    pub fn minimal(tool: &str, error: &str, latency_ms: f32) -> Self {
        Self {
            tool: tool.to_string(),
            success: false,
            latency_ms,
            error: error.to_string(),
            brain_wave: "Gamma".to_string(),
            effectiveness: 0.0,
            karma_debt: 0.0,
            self_model_confidence: 0.5,
            drive_bias_confidence: 0.5,
            citta_coherence: 1.0,
            citta_valence: 0.0,
            tool_stats: ToolStatsSnapshot::default(),
            routed_via_wm: false,
            arg_size_bytes: 0,
            response_size_bytes: 0,
        }
    }
}

// ── Friction deduplication (WS-2) ──────────────────────────────────────

/// Compute a deduplication hash for a friction entry.
///
/// Hash is based on `tool_name + category + severity + first 200 chars of error`.
/// Returns a hex string suitable for use as a tag: `rsi:hash:{hash}`.
#[must_use]
pub fn friction_hash(tool: &str, category: &str, severity: &str, error: &str) -> String {
    let mut hasher = DefaultHasher::new();
    tool.hash(&mut hasher);
    category.hash(&mut hasher);
    severity.hash(&mut hasher);
    error.chars().take(200).for_each(|c| c.hash(&mut hasher));
    format!("{:016x}", hasher.finish())
}

/// Check if a friction entry with the given hash tag already exists.
pub fn friction_hash_exists(store: &MemoryStore, hash_tag: &str) -> bool {
    find_existing_friction(store, hash_tag).is_ok_and(|opt| opt.is_some())
}

/// Scan Codex for an existing friction entry with the given hash tag.
/// Returns `Some(memory)` if a duplicate is found.
fn find_existing_friction(store: &MemoryStore, hash_tag: &str) -> wm_core::Result<Option<Memory>> {
    let memories = store.scan(wm_core::Galaxy::Codex, 500)?;
    for mem in memories {
        if mem.metadata.tags.iter().any(|t| t == hash_tag) {
            return Ok(Some(mem));
        }
    }
    Ok(None)
}

/// Extract duplicate_count from a friction memory's tags.
fn extract_dup_count(mem: &Memory) -> u64 {
    mem.metadata
        .tags
        .iter()
        .find_map(|t| t.strip_prefix("rsi:dup:"))
        .and_then(|v| v.parse::<u64>().ok())
        .unwrap_or(1)
}

/// Check if a friction memory has been resolved (WS-5 regression detection).
fn is_resolved(mem: &Memory) -> bool {
    mem.metadata.tags.iter().any(|t| t == "rsi:resolved")
}

/// Escalate severity by one level (WS-5 regression detection).
fn escalate_severity(severity: &str) -> &str {
    match severity {
        "low" => "medium",
        "medium" => "high",
        "high" => "critical",
        _ => "high",
    }
}

/// Log a friction point encountered during v4 usage.
///
/// Creates a structured memory in the Codex galaxy with the `rsi:friction`
/// tag, plus optional severity and category tags. This is the primary
/// data-collection mechanism for Phase 1 RSI.
pub struct FrictionLogTool {
    store: Arc<MemoryStore>,
    search: Option<Arc<SearchEngine>>,
    stats: ToolStats,
    effects: EffectRow,
}

impl FrictionLogTool {
    pub fn new(store: Arc<MemoryStore>, search: Option<Arc<SearchEngine>>) -> Self {
        Self {
            store,
            search,
            stats: ToolStats::default(),
            effects: EffectRow {
                writes: vec![Resource::Galaxy("codex".into())],
                invokes: vec![Capability::MemoryWrite],
                ..Default::default()
            },
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for FrictionLogTool {
    fn name(&self) -> &str {
        "friction.log"
    }
    fn gana(&self) -> Gana {
        Gana::Wall
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Log a friction point encountered during v4 usage. Fields: what_happened (required), expected_behavior (required), suggested_fix (optional), severity (low/medium/high, default medium), category (ux/performance/error/missing_feature/confusing, default ux), tool_name (optional)."
    }
    async fn call(&self, _ctx: &mut Context, args: Args) -> wm_core::Result<Output> {
        let what_happened = args
            .get("what_happened")
            .and_then(|v| v.as_str())
            .ok_or_else(|| {
                wm_core::CoreError::InvalidArgs("what_happened (string) required".into())
            })?;
        let expected = args
            .get("expected_behavior")
            .and_then(|v| v.as_str())
            .ok_or_else(|| {
                wm_core::CoreError::InvalidArgs("expected_behavior (string) required".into())
            })?;
        let suggested_fix = args
            .get("suggested_fix")
            .and_then(|v| v.as_str())
            .unwrap_or("");
        let severity = args
            .get("severity")
            .and_then(|v| v.as_str())
            .unwrap_or("medium");
        let category = args
            .get("category")
            .and_then(|v| v.as_str())
            .unwrap_or("ux");
        let tool_name = args.get("tool_name").and_then(|v| v.as_str()).unwrap_or("");

        // WS-2: Deduplication — compute hash and check for existing entry
        let hash = friction_hash(tool_name, category, severity, what_happened);
        let hash_tag = format!("rsi:hash:{hash}");

        if let Some(existing) = find_existing_friction(&self.store, &hash_tag)? {
            // WS-5: Regression detection — if existing entry is resolved, create new
            if is_resolved(&existing) {
                let escalated = escalate_severity(severity);
                // Fall through to create new entry with escalated severity + regression tag
                let content = format!(
                    "## Friction: {what_happened}\n\n\
                     **Expected:** {expected}\n\n\
                     **Suggested fix:** {suggested_fix}\n\n\
                     **⚠️ REGRESSION:** This friction was previously resolved but has reappeared.\n\n\
                     **Escalated severity:** {escalated} (was {severity})"
                );
                let now = chrono::Utc::now().to_rfc3339();
                let mut memory = Memory::new(wm_core::Galaxy::Codex, content);
                memory.metadata.tags = vec![
                    "rsi:friction".to_string(),
                    format!("rsi:severity:{escalated}"),
                    format!("rsi:category:{category}"),
                    "rsi:regression".to_string(),
                    format!("rsi:tool:{tool_name}"),
                    format!("rsi:regression_of:{}", existing.metadata.id),
                    hash_tag,
                    "rsi:dup:1".to_string(),
                    format!("rsi:last_seen:{now}"),
                ];
                memory.metadata.source = "auto".to_string();
                memory.metadata.source_trust = 0.9;
                memory.metadata.importance = 0.95;
                let id = memory.metadata.id;
                self.store.put(wm_core::Galaxy::Codex, &memory)?;

                if let Some(search) = &self.search {
                    if let Err(e) = (|| {
                        let mut writer = search.writer()?;
                        search.add_document(
                            &mut writer,
                            &id.to_string(),
                            "codex",
                            &memory.content,
                            &memory.metadata.tags,
                            memory.metadata.created_at.timestamp(),
                        )?;
                        search.commit(&mut writer)?;
                        Ok::<(), wm_core::CoreError>(())
                    })() {
                        tracing::warn!("Tantivy indexing failed for regression entry {id}: {e}");
                    }
                }

                return Ok(json!({
                    "status": "regression",
                    "id": id.to_string(),
                    "escalated_severity": escalated,
                    "message": "Regression detected! Previously resolved friction has reappeared. Severity escalated.",
                }));
            }

            let dup_count = extract_dup_count(&existing) + 1;
            let now = chrono::Utc::now().to_rfc3339();

            // Update existing entry: increment dup count, update last_seen
            let mut updated = existing;
            // Remove old dup tag and add new one
            updated.metadata.tags.retain(|t| !t.starts_with("rsi:dup:"));
            updated.metadata.tags.push(format!("rsi:dup:{dup_count}"));
            // Remove old last_seen and add new one
            updated
                .metadata
                .tags
                .retain(|t| !t.starts_with("rsi:last_seen:"));
            updated.metadata.tags.push(format!("rsi:last_seen:{now}"));

            self.store.put(wm_core::Galaxy::Codex, &updated)?;

            return Ok(json!({
                "status": "duplicate",
                "id": updated.metadata.id.to_string(),
                "duplicate_count": dup_count,
                "message": "Duplicate friction entry updated. Use friction.review to analyze patterns.",
            }));
        }

        // Build structured content
        let content = format!(
            "## Friction: {what_happened}\n\n\
             **Expected:** {expected}\n\n\
             **Suggested fix:** {suggested_fix}\n\n\
             **Severity:** {severity} | **Category:** {category} | **Tool:** {tool_name}"
        );

        let now = chrono::Utc::now().to_rfc3339();
        let mut memory = Memory::new(wm_core::Galaxy::Codex, content);
        memory.metadata.tags = vec![
            "rsi:friction".to_string(),
            format!("rsi:severity:{severity}"),
            format!("rsi:category:{category}"),
            hash_tag,
            "rsi:dup:1".to_string(),
            format!("rsi:last_seen:{now}"),
        ];
        if !tool_name.is_empty() {
            memory.metadata.tags.push(format!("rsi:tool:{tool_name}"));
        }
        memory.metadata.source = "user".to_string();
        memory.metadata.source_trust = 1.0;
        memory.metadata.importance = match severity {
            "high" => 0.9,
            "medium" => 0.6,
            _ => 0.3,
        };

        let id = memory.metadata.id;
        self.store.put(wm_core::Galaxy::Codex, &memory)?;

        // Index into Tantivy (non-fatal)
        if let Some(search) = &self.search {
            if let Err(e) = (|| {
                let mut writer = search.writer()?;
                search.add_document(
                    &mut writer,
                    &id.to_string(),
                    "codex",
                    &memory.content,
                    &memory.metadata.tags,
                    memory.metadata.created_at.timestamp(),
                )?;
                search.commit(&mut writer)?;
                Ok::<(), wm_core::CoreError>(())
            })() {
                tracing::warn!("Tantivy indexing failed for friction entry {id}: {e}");
            }
        }

        Ok(json!({
            "status": "success",
            "id": id.to_string(),
            "message": "Friction logged. Use friction.review to analyze patterns.",
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── Tool: friction.review ─────────────────────────────────────────────

/// Review recent friction entries, optionally filtered by category or severity.
///
/// Scans the Codex galaxy for memories tagged `rsi:friction` and returns
/// a summary. This is the analysis tool for Phase 1 RSI — it surfaces
/// patterns in friction data for human review.
pub struct FrictionReviewTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl FrictionReviewTool {
    pub fn new(store: Arc<MemoryStore>) -> Self {
        Self {
            store,
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![Resource::Galaxy("codex".into())]),
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for FrictionReviewTool {
    fn name(&self) -> &str {
        "friction.review"
    }
    fn gana(&self) -> Gana {
        Gana::Wall
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Review recent friction entries. Optional filters: category (ux/performance/error/missing_feature/confusing), severity (low/medium/high), limit (default 50). Returns entries plus a summary of patterns."
    }
    async fn call(&self, _ctx: &mut Context, args: Args) -> wm_core::Result<Output> {
        let limit = args
            .get("limit")
            .and_then(serde_json::Value::as_u64)
            .unwrap_or(50) as usize;
        let category_filter = args.get("category").and_then(|v| v.as_str());
        let severity_filter = args.get("severity").and_then(|v| v.as_str());

        // Scan codex for friction entries
        let memories = self.store.scan(wm_core::Galaxy::Codex, limit * 5)?;

        let mut entries: Vec<Value> = Vec::new();
        let mut by_category: std::collections::HashMap<String, usize> =
            std::collections::HashMap::new();
        let mut by_severity: std::collections::HashMap<String, usize> =
            std::collections::HashMap::new();
        let mut by_tool: std::collections::HashMap<String, usize> =
            std::collections::HashMap::new();

        for m in &memories {
            // Check if this is a friction entry
            if !m.metadata.tags.iter().any(|t| t == "rsi:friction") {
                continue;
            }

            // Extract category and severity from tags
            let entry_category = m
                .metadata
                .tags
                .iter()
                .find_map(|t| t.strip_prefix("rsi:category:"))
                .unwrap_or("unknown");
            let entry_severity = m
                .metadata
                .tags
                .iter()
                .find_map(|t| t.strip_prefix("rsi:severity:"))
                .unwrap_or("unknown");
            let entry_tool = m
                .metadata
                .tags
                .iter()
                .find_map(|t| t.strip_prefix("rsi:tool:"))
                .unwrap_or("");

            // Apply filters
            if let Some(cat) = category_filter {
                if entry_category != cat {
                    continue;
                }
            }
            if let Some(sev) = severity_filter {
                if entry_severity != sev {
                    continue;
                }
            }

            *by_category.entry(entry_category.to_string()).or_default() += 1;
            *by_severity.entry(entry_severity.to_string()).or_default() += 1;
            if !entry_tool.is_empty() {
                *by_tool.entry(entry_tool.to_string()).or_default() += 1;
            }

            // WS-2: Extract duplicate_count and last_seen
            // WS-5: Extract resolution status and regression info
            let dup_count = m
                .metadata
                .tags
                .iter()
                .find_map(|t| t.strip_prefix("rsi:dup:"))
                .and_then(|v| v.parse::<u64>().ok())
                .unwrap_or(1);
            let last_seen = m
                .metadata
                .tags
                .iter()
                .find_map(|t| t.strip_prefix("rsi:last_seen:"))
                .unwrap_or("");
            let is_resolved = m.metadata.tags.iter().any(|t| t == "rsi:resolved");
            let is_regression = m.metadata.tags.iter().any(|t| t == "rsi:regression");
            let resolved_at = m
                .metadata
                .tags
                .iter()
                .find_map(|t| t.strip_prefix("rsi:resolved_at:"))
                .unwrap_or("");
            let resolved_method = m
                .metadata
                .tags
                .iter()
                .find_map(|t| t.strip_prefix("rsi:resolved_method:"))
                .unwrap_or("");

            if entries.len() < limit {
                entries.push(json!({
                    "id": m.metadata.id.to_string(),
                    "content_preview": m.content.chars().take(120).collect::<String>(),
                    "severity": entry_severity,
                    "category": entry_category,
                    "tool": entry_tool,
                    "duplicate_count": dup_count,
                    "last_seen": last_seen,
                    "resolved": is_resolved,
                    "resolved_at": resolved_at,
                    "resolved_method": resolved_method,
                    "is_regression": is_regression,
                    "created_at": m.metadata.created_at.to_rfc3339(),
                }));
            }
        }

        let total = entries.len();
        let resolved_count = entries.iter().filter(|e| e["resolved"] == true).count();
        let regression_count = entries
            .iter()
            .filter(|e| e["is_regression"] == true)
            .count();

        Ok(json!({
            "status": "success",
            "total_friction_entries": total,
            "resolved": resolved_count,
            "regressions": regression_count,
            "entries": entries,
            "summary": {
                "by_category": by_category,
                "by_severity": by_severity,
                "by_tool": by_tool,
            },
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── Tool: friction.auto_log ───────────────────────────────────────────

/// Auto-log a friction entry from a Gan Ying Bus ToolDispatchError event.
///
/// This tool is called programmatically by the MCP server when a tool
/// dispatch fails. It creates a friction entry with category "error"
/// and severity derived from the error type. It can also be called
/// manually to log a dispatch error.
pub struct FrictionAutoLogTool {
    store: Arc<MemoryStore>,
    search: Option<Arc<SearchEngine>>,
    stats: ToolStats,
    effects: EffectRow,
}

impl FrictionAutoLogTool {
    pub fn new(store: Arc<MemoryStore>, search: Option<Arc<SearchEngine>>) -> Self {
        Self {
            store,
            search,
            stats: ToolStats::default(),
            effects: EffectRow {
                writes: vec![Resource::Galaxy("codex".into())],
                invokes: vec![Capability::MemoryWrite],
                ..Default::default()
            },
        }
    }

    /// Create a friction memory from a dispatch error with rich telemetry.
    /// Used by the server's error handler. Stores telemetry as a JSON
    /// section in the memory content for downstream analysis.
    pub fn log_error(&self, telemetry: &DispatchTelemetry) -> wm_core::Result<()> {
        let severity = if telemetry.latency_ms > 1000.0 || telemetry.karma_debt > 0.8 {
            "high"
        } else {
            "medium"
        };

        // WS-2: Deduplication — compute hash and check for existing entry
        let hash = friction_hash(&telemetry.tool, "error", severity, &telemetry.error);
        let hash_tag = format!("rsi:hash:{hash}");

        if let Some(existing) = find_existing_friction(&self.store, &hash_tag)? {
            // WS-5: Regression detection — if existing entry is resolved, create new
            if is_resolved(&existing) {
                let escalated = escalate_severity(severity);
                let content = format!(
                    "## Auto-logged Friction: Tool dispatch error (REGRESSION)\n\n\
                     **Tool:** {}\n\n\
                     **Error:** {}\n\n\
                     **Latency:** {:.1}ms\n\n\
                     **⚠️ REGRESSION:** This error was previously resolved but has reappeared.\n\n\
                     **Escalated severity:** {} (was {})\n\n\
                     ---\n```json\n{}\n```",
                    telemetry.tool,
                    telemetry.error,
                    telemetry.latency_ms,
                    escalated,
                    severity,
                    serde_json::to_string_pretty(telemetry).unwrap_or_default(),
                );
                let now = chrono::Utc::now().to_rfc3339();
                let mut memory = Memory::new(wm_core::Galaxy::Codex, content);
                memory.metadata.tags = vec![
                    "rsi:friction".to_string(),
                    format!("rsi:severity:{escalated}"),
                    "rsi:category:error".to_string(),
                    "rsi:regression".to_string(),
                    format!("rsi:tool:{}", telemetry.tool),
                    format!("rsi:regression_of:{}", existing.metadata.id),
                    hash_tag,
                    "rsi:dup:1".to_string(),
                    format!("rsi:last_seen:{now}"),
                ];
                memory.metadata.source = "auto".to_string();
                memory.metadata.source_trust = 0.9;
                memory.metadata.importance = 0.95;
                let id = memory.metadata.id;
                self.store.put(wm_core::Galaxy::Codex, &memory)?;

                if let Some(search) = &self.search {
                    if let Err(e) = (|| {
                        let mut writer = search.writer()?;
                        search.add_document(
                            &mut writer,
                            &id.to_string(),
                            "codex",
                            &memory.content,
                            &memory.metadata.tags,
                            memory.metadata.created_at.timestamp(),
                        )?;
                        search.commit(&mut writer)?;
                        Ok::<(), wm_core::CoreError>(())
                    })() {
                        tracing::warn!("Tantivy indexing failed for regression entry {id}: {e}");
                    }
                }
                return Ok(());
            }

            let dup_count = extract_dup_count(&existing) + 1;
            let now = chrono::Utc::now().to_rfc3339();

            let mut updated = existing;
            updated.metadata.tags.retain(|t| !t.starts_with("rsi:dup:"));
            updated.metadata.tags.push(format!("rsi:dup:{dup_count}"));
            updated
                .metadata
                .tags
                .retain(|t| !t.starts_with("rsi:last_seen:"));
            updated.metadata.tags.push(format!("rsi:last_seen:{now}"));

            self.store.put(wm_core::Galaxy::Codex, &updated)?;
            return Ok(());
        }

        let content = format!(
            "## Auto-logged Friction: Tool dispatch error\n\n\
             **Tool:** {}\n\n\
             **Error:** {}\n\n\
             **Latency:** {:.1}ms\n\n\
             **Expected:** Tool should succeed or return a descriptive error.\n\n\
             **Suggested fix:** Investigate the error and improve error handling.\n\n\
             ---\n```json\n{}\n```",
            telemetry.tool,
            telemetry.error,
            telemetry.latency_ms,
            serde_json::to_string_pretty(telemetry).unwrap_or_default(),
        );

        let now = chrono::Utc::now().to_rfc3339();
        let mut memory = Memory::new(wm_core::Galaxy::Codex, content);
        memory.metadata.tags = vec![
            "rsi:friction".to_string(),
            format!("rsi:severity:{severity}"),
            "rsi:category:error".to_string(),
            format!("rsi:tool:{}", telemetry.tool),
            hash_tag,
            "rsi:dup:1".to_string(),
            format!("rsi:last_seen:{now}"),
        ];
        memory.metadata.source = "auto".to_string();
        memory.metadata.source_trust = 0.8;
        memory.metadata.importance = match severity {
            "high" => 0.9,
            "medium" => 0.6,
            _ => 0.3,
        };

        let id = memory.metadata.id;
        self.store.put(wm_core::Galaxy::Codex, &memory)?;

        // Index into Tantivy (non-fatal)
        if let Some(search) = &self.search {
            if let Err(e) = (|| {
                let mut writer = search.writer()?;
                search.add_document(
                    &mut writer,
                    &id.to_string(),
                    "codex",
                    &memory.content,
                    &memory.metadata.tags,
                    memory.metadata.created_at.timestamp(),
                )?;
                search.commit(&mut writer)?;
                Ok::<(), wm_core::CoreError>(())
            })() {
                tracing::warn!("Tantivy indexing failed for auto-friction entry {id}: {e}");
            }
        }

        Ok(())
    }

    /// Log an anomaly for a successful dispatch with abnormal metrics.
    /// Triggered when latency > P99, effectiveness < 0.3, or karma_debt > 0.5.
    pub fn log_anomaly(
        &self,
        telemetry: &DispatchTelemetry,
        anomaly_type: &str,
    ) -> wm_core::Result<()> {
        let content = format!(
            "## Auto-logged Friction: Anomalous dispatch (success)\n\n\
             **Tool:** {}\n\n\
             **Anomaly:** {anomaly_type}\n\n\
             **Latency:** {:.1}ms | **Effectiveness:** {:.2} | **Karma debt:** {:.2}\n\n\
             **Expected:** Successful dispatches should have normal metrics.\n\n\
             **Suggested fix:** Investigate why a successful dispatch has anomalous metrics.\n\n\
             ---\n```json\n{}\n```",
            telemetry.tool,
            telemetry.latency_ms,
            telemetry.effectiveness,
            telemetry.karma_debt,
            serde_json::to_string_pretty(telemetry).unwrap_or_default(),
        );

        let category = match anomaly_type {
            "high_latency" => "performance",
            "low_effectiveness" => "ux",
            "high_karma_debt" => "governance",
            _ => "ux",
        };

        let mut memory = Memory::new(wm_core::Galaxy::Codex, content);
        memory.metadata.tags = vec![
            "rsi:friction".to_string(),
            "rsi:severity:medium".to_string(),
            format!("rsi:category:{category}"),
            format!("rsi:tool:{}", telemetry.tool),
            "rsi:anomaly".to_string(),
        ];
        memory.metadata.source = "auto".to_string();
        memory.metadata.source_trust = 0.7;
        memory.metadata.importance = 0.5;

        let id = memory.metadata.id;
        self.store.put(wm_core::Galaxy::Codex, &memory)?;

        if let Some(search) = &self.search {
            if let Err(e) = (|| {
                let mut writer = search.writer()?;
                search.add_document(
                    &mut writer,
                    &id.to_string(),
                    "codex",
                    &memory.content,
                    &memory.metadata.tags,
                    memory.metadata.created_at.timestamp(),
                )?;
                search.commit(&mut writer)?;
                Ok::<(), wm_core::CoreError>(())
            })() {
                tracing::warn!("Tantivy indexing failed for anomaly entry {id}: {e}");
            }
        }

        Ok(())
    }
}

#[async_trait]
#[async_trait]
impl Tool for FrictionAutoLogTool {
    fn name(&self) -> &str {
        "friction.auto_log"
    }
    fn gana(&self) -> Gana {
        Gana::Wall
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Auto-log a friction entry from a tool dispatch error. Called programmatically by the server on ToolDispatchError events, or manually to log an error. Fields: tool_name (required), error (required), latency_ms (optional)."
    }
    async fn call(&self, _ctx: &mut Context, args: Args) -> wm_core::Result<Output> {
        let tool_name = args
            .get("tool_name")
            .and_then(|v| v.as_str())
            .ok_or_else(|| wm_core::CoreError::InvalidArgs("tool_name (string) required".into()))?;
        let error = args
            .get("error")
            .and_then(|v| v.as_str())
            .ok_or_else(|| wm_core::CoreError::InvalidArgs("error (string) required".into()))?;
        let latency_ms = args
            .get("latency_ms")
            .and_then(serde_json::Value::as_f64)
            .unwrap_or(0.0) as f32;

        let telemetry = DispatchTelemetry::minimal(tool_name, error, latency_ms);
        self.log_error(&telemetry)?;

        Ok(json!({
            "status": "success",
            "message": "Auto-friction entry logged.",
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── Tool: improve.proposals ───────────────────────────────────────────

/// Run the improve.scan autonomous cycle and return improvement proposals.
///
/// This tool triggers the RSI Phase 2 codebase-grounded improvement cycle,
/// which analyzes friction entries and proposes concrete improvements.
/// All proposals require human review — no autonomous action is taken.
pub struct ImproveProposalsTool {
    store: Arc<MemoryStore>,
    associations: Arc<wm_memory::AssociationStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl ImproveProposalsTool {
    pub fn new(store: Arc<MemoryStore>, associations: Arc<wm_memory::AssociationStore>) -> Self {
        Self {
            store,
            associations,
            stats: ToolStats::default(),
            effects: EffectRow {
                // Runs an autonomous cycle: scans memory galaxies and
                // logs the cycle record to the Substrate galaxy.
                reads: super::common::memory_galaxy_reads(),
                writes: vec![Resource::Galaxy("substrate".into())],
                ..Default::default()
            },
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for ImproveProposalsTool {
    fn name(&self) -> &str {
        "improve.proposals"
    }
    fn gana(&self) -> Gana {
        Gana::Wall
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Run the RSI improve.scan cycle to analyze friction entries and generate concrete improvement proposals. All proposals require human review. Returns proposals grouped by category and target."
    }
    async fn call(&self, _ctx: &mut Context, _args: Args) -> wm_core::Result<Output> {
        let runner = wm_cognitive::AutonomousCycleRunner::default();
        let ctx = wm_cognitive::CycleContext::new(
            &self.store,
            &self.associations,
            1.0, // Full health for manual invocation
        );
        let mut runner = runner;
        let result = runner.run_cycle(wm_cognitive::CycleType::Improve, &ctx);

        let proposals: Vec<Value> = result
            .improvements
            .iter()
            .map(|p| {
                json!({
                    "category": p.category,
                    "severity": p.severity,
                    "target": p.target,
                    "problem": p.problem,
                    "recommended_action": p.recommended_action,
                    "pattern_count": p.pattern_count,
                    "source_friction_ids": p.source_friction_ids,
                })
            })
            .collect();

        Ok(json!({
            "status": format!("{:?}", result.status),
            "memories_scanned": result.memories_scanned,
            "proposals_generated": result.proposals_generated,
            "notes": result.notes,
            "proposals": proposals,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── Tool: redteam.proposals ───────────────────────────────────────────

/// Run the redteam.scan autonomous cycle and return adversarial test proposals.
///
/// RSI Phase 3: The system tries to break itself and proposes fixes.
/// Bounded by SpiralTracker to prevent infinite adversarial loops.
/// All proposals require human review — no autonomous action is taken.
pub struct RedteamProposalsTool {
    store: Arc<MemoryStore>,
    associations: Arc<wm_memory::AssociationStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl RedteamProposalsTool {
    pub fn new(store: Arc<MemoryStore>, associations: Arc<wm_memory::AssociationStore>) -> Self {
        Self {
            store,
            associations,
            stats: ToolStats::default(),
            effects: EffectRow {
                // Runs an autonomous cycle: scans memory galaxies and
                // logs the cycle record to the Substrate galaxy.
                reads: super::common::memory_galaxy_reads(),
                writes: vec![Resource::Galaxy("substrate".into())],
                ..Default::default()
            },
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for RedteamProposalsTool {
    fn name(&self) -> &str {
        "redteam.proposals"
    }
    fn gana(&self) -> Gana {
        Gana::Wall
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Run the RSI redteam.scan cycle to generate adversarial test proposals against v4 governance, karma, mandala, dispatch, and spiral systems. All proposals require human review."
    }
    async fn call(&self, _ctx: &mut Context, _args: Args) -> wm_core::Result<Output> {
        let runner = wm_cognitive::AutonomousCycleRunner::default();
        let ctx = wm_cognitive::CycleContext::new(&self.store, &self.associations, 1.0);
        let mut runner = runner;
        let result = runner.run_cycle(wm_cognitive::CycleType::Redteam, &ctx);

        let proposals: Vec<Value> = result
            .redteam
            .iter()
            .map(|p| {
                json!({
                    "target_system": p.target_system,
                    "attack_vector": p.attack_vector,
                    "expected_behavior": p.expected_behavior,
                    "test_pseudocode": p.test_pseudocode,
                    "risk_level": p.risk_level,
                    "existing_coverage": p.existing_coverage,
                    "recommended_fix": p.recommended_fix,
                })
            })
            .collect();

        Ok(json!({
            "status": format!("{:?}", result.status),
            "memories_scanned": result.memories_scanned,
            "proposals_generated": result.proposals_generated,
            "notes": result.notes,
            "proposals": proposals,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── WS-5: Friction Resolve Tool ───────────────────────────────────────

/// Tool: `friction.resolve`
///
/// Marks a friction entry as resolved, records karma debt reduction,
/// and emits a workspace Reward event. If the same friction hash reappears
/// after resolution, the dedup logic in `log_error` / `FrictionLogTool::call`
/// will detect the regression and escalate severity.
pub struct FrictionResolveTool {
    store: Arc<MemoryStore>,
    karma_ledger: Option<Arc<KarmaLedger>>,
    workspace: Option<Arc<std::sync::Mutex<GlobalWorkspace>>>,
    stats: ToolStats,
    effects: EffectRow,
}

impl FrictionResolveTool {
    pub fn new(
        store: Arc<MemoryStore>,
        karma_ledger: Option<Arc<KarmaLedger>>,
        workspace: Option<Arc<std::sync::Mutex<GlobalWorkspace>>>,
    ) -> Self {
        Self {
            store,
            karma_ledger,
            workspace,
            stats: ToolStats::default(),
            effects: EffectRow::default(),
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for FrictionResolveTool {
    fn name(&self) -> &str {
        "friction.resolve"
    }

    fn gana(&self) -> Gana {
        Gana::Wall
    }

    fn effects(&self) -> &EffectRow {
        &self.effects
    }

    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let friction_id = args
            .get("friction_id")
            .and_then(|v| v.as_str())
            .ok_or_else(|| wm_core::CoreError::Tool("friction_id is required".into()))?;

        let resolution_note = args
            .get("resolution_note")
            .and_then(|v| v.as_str())
            .ok_or_else(|| wm_core::CoreError::Tool("resolution_note is required".into()))?;

        let resolution_method = args
            .get("resolution_method")
            .and_then(|v| v.as_str())
            .unwrap_or("code_fix");

        // Parse the friction ID to find the memory
        let uuid = uuid::Uuid::parse_str(friction_id)
            .map_err(|e| wm_core::CoreError::Tool(format!("Invalid UUID: {e}")))?;

        // Scan codex for the friction entry
        let memories = self.store.scan(wm_core::Galaxy::Codex, 500)?;
        let mut found: Option<Memory> = None;
        for mem in memories {
            if mem.metadata.id == uuid && mem.metadata.tags.iter().any(|t| t == "rsi:friction") {
                found = Some(mem);
                break;
            }
        }

        let mut entry =
            found.ok_or_else(|| wm_core::CoreError::NotFound("Friction entry not found".into()))?;

        // Check if already resolved
        if entry.metadata.tags.iter().any(|t| t == "rsi:resolved") {
            return Ok(json!({
                "status": "already_resolved",
                "friction_id": friction_id,
            }));
        }

        // Tag as resolved
        let now = chrono::Utc::now().to_rfc3339();
        entry.metadata.tags.push("rsi:resolved".to_string());
        entry
            .metadata
            .tags
            .push(format!("rsi:resolved_method:{resolution_method}"));
        entry.metadata.tags.push(format!("rsi:resolved_at:{now}"));

        // Append resolution note to content
        entry.content = format!(
            "{}\n\n---\n## Resolution\n\n**Method:** {}\n\n**Note:** {}\n\n**Resolved at:** {}",
            entry.content, resolution_method, resolution_note, now
        );

        // Extract tool name for karma ledger
        let tool_name = entry
            .metadata
            .tags
            .iter()
            .find_map(|t| t.strip_prefix("rsi:tool:"))
            .unwrap_or("unknown");

        self.store.put(wm_core::Galaxy::Codex, &entry)?;

        // Record karma debt reduction
        if let Some(ref karma) = self.karma_ledger {
            if let Err(e) = karma.record_friction_resolved(tool_name) {
                tracing::warn!("Failed to record friction resolution to karma ledger: {e}");
            }
        }

        // Emit workspace Reward event
        if let Some(ref ws_arc) = self.workspace {
            if let Ok(mut ws) = ws_arc.lock() {
                ws.publish_simple(
                    CoreId::Autonomous,
                    EventType::Reward,
                    0.7,
                    0.9,
                    json!({
                        "friction_id": friction_id,
                        "resolution_method": resolution_method,
                        "tool": tool_name,
                    }),
                );
            }
        }

        Ok(json!({
            "status": "resolved",
            "friction_id": friction_id,
            "resolution_method": resolution_method,
            "resolved_at": now,
        }))
    }

    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── WS-4: Active Proposals Tool ───────────────────────────────────────

/// Tool: `improve.active_proposals`
///
/// Retrieves active (unresolved) improvement proposals from the Codex.
/// Proposals are stored by the proactive improve cycle with tag `rsi:proposal:active`.
pub struct ActiveProposalsTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl ActiveProposalsTool {
    pub fn new(store: Arc<MemoryStore>) -> Self {
        Self {
            store,
            stats: ToolStats::default(),
            effects: EffectRow::default(),
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for ActiveProposalsTool {
    fn name(&self) -> &str {
        "improve.active_proposals"
    }

    fn gana(&self) -> Gana {
        Gana::Wall
    }

    fn effects(&self) -> &EffectRow {
        &self.effects
    }

    async fn call(&self, _ctx: &mut Context, _args: Value) -> wm_core::Result<Value> {
        let memories = self.store.scan(wm_core::Galaxy::Codex, 200)?;

        let mut proposals: Vec<Value> = Vec::new();
        for m in &memories {
            if !m.metadata.tags.iter().any(|t| t == "rsi:proposal:active") {
                continue;
            }

            let category = m
                .metadata
                .tags
                .iter()
                .find_map(|t| t.strip_prefix("rsi:category:"))
                .unwrap_or("unknown");
            let severity = m
                .metadata
                .tags
                .iter()
                .find_map(|t| t.strip_prefix("rsi:severity:"))
                .unwrap_or("unknown");
            let target = m
                .metadata
                .tags
                .iter()
                .find_map(|t| t.strip_prefix("rsi:tool:"))
                .unwrap_or("");
            let signature = m
                .metadata
                .tags
                .iter()
                .find_map(|t| t.strip_prefix("rsi:proposal:sig:"))
                .unwrap_or("");

            proposals.push(json!({
                "id": m.metadata.id.to_string(),
                "category": category,
                "severity": severity,
                "target": target,
                "signature": signature,
                "content_preview": m.content.chars().take(200).collect::<String>(),
                "created_at": m.metadata.created_at.to_rfc3339(),
            }));
        }

        Ok(json!({
            "status": "success",
            "active_proposals": proposals.len(),
            "proposals": proposals,
        }))
    }

    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── RSI Phase 3: Redteam From Friction Tool ───────────────────────────

/// Tool: `redteam.from_friction`
///
/// Scans resolved and regression friction entries to synthesize adversarial
/// test proposals. Each resolved friction becomes a regression test vector;
/// each regression becomes an escalated adversarial vector.
pub struct RedteamFromFrictionTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl RedteamFromFrictionTool {
    pub fn new(store: Arc<MemoryStore>) -> Self {
        Self {
            store,
            stats: ToolStats::default(),
            effects: EffectRow::default(),
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for RedteamFromFrictionTool {
    fn name(&self) -> &str {
        "redteam.from_friction"
    }
    fn gana(&self) -> Gana {
        Gana::Wall
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Synthesize adversarial test proposals from resolved and regression friction entries. Each resolved friction becomes a regression test vector; each regression becomes an escalated adversarial vector."
    }
    async fn call(&self, _ctx: &mut Context, _args: Args) -> wm_core::Result<Output> {
        let memories = self.store.scan(wm_core::Galaxy::Codex, 500)?;

        let mut proposals: Vec<Value> = Vec::new();
        let mut resolved_count = 0u32;
        let mut regression_count = 0u32;

        for m in &memories {
            if !m.metadata.tags.iter().any(|t| t == "rsi:friction") {
                continue;
            }

            let is_resolved = m.metadata.tags.iter().any(|t| t == "rsi:resolved");
            let is_regression = m.metadata.tags.iter().any(|t| t == "rsi:regression");

            if !is_resolved && !is_regression {
                continue;
            }

            if is_resolved {
                resolved_count += 1;
            }
            if is_regression {
                regression_count += 1;
            }

            let target = m
                .metadata
                .tags
                .iter()
                .find_map(|t| t.strip_prefix("rsi:tool:"))
                .unwrap_or("system");
            let category = m
                .metadata
                .tags
                .iter()
                .find_map(|t| t.strip_prefix("rsi:category:"))
                .unwrap_or("unknown");
            let severity = m
                .metadata
                .tags
                .iter()
                .find_map(|t| t.strip_prefix("rsi:severity:"))
                .unwrap_or("medium");
            let resolved_method = m
                .metadata
                .tags
                .iter()
                .find_map(|t| t.strip_prefix("rsi:resolved_method:"))
                .unwrap_or("");
            let regression_of = m
                .metadata
                .tags
                .iter()
                .find_map(|t| t.strip_prefix("rsi:regression_of:"));

            let (attack_vector, expected, pseudocode, risk) = if is_regression {
                (
                    format!("Regression: previously resolved friction in {target} reappeared"),
                    format!("Fix for {target} should prevent recurrence of this friction"),
                    format!(
                        "// Regression test for {target}\n\
                         // Original friction was resolved via {resolved_method}\n\
                         // but the issue reappeared — verify the fix is complete\n\
                         let result = dispatch_tool(\"{target}\");\n\
                         assert!(result.is_ok(), \"regression: {target} should not fail\");"
                    ),
                    "critical",
                )
            } else {
                (
                    format!("Regression test: verify {target} fix holds under stress"),
                    format!("{target} should not regress after fix via {resolved_method}"),
                    format!(
                        "// Regression test synthesized from resolved friction\n\
                         // Target: {target}\n\
                         // Resolution: {resolved_method}\n\
                         let result = dispatch_tool(\"{target}\");\n\
                         assert!(result.is_ok(), \"{target} should work after fix\");\n\
                         // Repeat under load\n\
                         for _ in 0..100 {{\n\
                         \x20\x20\x20\x20let r = dispatch_tool(\"{target}\");\n\
                         \x20\x20\x20\x20assert!(r.is_ok());\n\
                         }}"
                    ),
                    "high",
                )
            };

            proposals.push(json!({
                "friction_id": m.metadata.id.to_string(),
                "target_system": target,
                "category": category,
                "attack_vector": attack_vector,
                "expected_behavior": expected,
                "test_pseudocode": pseudocode,
                "risk_level": if is_regression { "critical" } else { risk },
                "is_regression": is_regression,
                "resolved_method": resolved_method,
                "regression_of": regression_of,
                "severity": severity,
            }));
        }

        Ok(json!({
            "status": "success",
            "resolved_friction_count": resolved_count,
            "regression_count": regression_count,
            "proposals_generated": proposals.len(),
            "proposals": proposals,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── RSI Phase 3: Redteam Coverage Report Tool ──────────────────────────

/// Tool: `redteam.coverage_report`
///
/// Runs the redteam cycle and produces a coverage summary showing which
/// target systems have covered vs uncovered attack vectors, along with
/// friction-matched priorities.
pub struct RedteamCoverageReportTool {
    store: Arc<MemoryStore>,
    associations: Arc<wm_memory::AssociationStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl RedteamCoverageReportTool {
    pub fn new(store: Arc<MemoryStore>, associations: Arc<wm_memory::AssociationStore>) -> Self {
        Self {
            store,
            associations,
            stats: ToolStats::default(),
            effects: EffectRow {
                // Runs an autonomous cycle: scans memory galaxies and
                // logs the cycle record to the Substrate galaxy.
                reads: super::common::memory_galaxy_reads(),
                writes: vec![Resource::Galaxy("substrate".into())],
                ..Default::default()
            },
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for RedteamCoverageReportTool {
    fn name(&self) -> &str {
        "redteam.coverage_report"
    }
    fn gana(&self) -> Gana {
        Gana::Wall
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Generate a coverage report showing which target systems have covered vs uncovered adversarial test vectors, with friction-matched priorities."
    }
    async fn call(&self, _ctx: &mut Context, _args: Args) -> wm_core::Result<Output> {
        let runner = wm_cognitive::AutonomousCycleRunner::default();
        let ctx = wm_cognitive::CycleContext::new(&self.store, &self.associations, 1.0);
        let mut runner = runner;
        let result = runner.run_cycle(wm_cognitive::CycleType::Redteam, &ctx);

        use std::collections::BTreeMap;
        let mut by_system: BTreeMap<String, (u32, u32, u32)> = BTreeMap::new();

        for p in &result.redteam {
            let entry = by_system
                .entry(p.target_system.clone())
                .or_insert((0, 0, 0));
            if p.existing_coverage {
                entry.0 += 1; // covered
            } else {
                entry.1 += 1; // uncovered
            }
        }

        // Count friction entries per target system
        let memories = self.store.scan(wm_core::Galaxy::Codex, 500)?;
        for m in &memories {
            if !m.metadata.tags.iter().any(|t| t == "rsi:friction") {
                continue;
            }
            let target = m
                .metadata
                .tags
                .iter()
                .find_map(|t| t.strip_prefix("rsi:tool:"))
                .unwrap_or("system");
            let entry = by_system.entry(target.to_string()).or_insert((0, 0, 0));
            entry.2 += 1; // friction count
        }

        let summary: Vec<Value> = by_system
            .iter()
            .map(|(system, (covered, uncovered, friction))| {
                json!({
                    "target_system": system,
                    "covered_vectors": covered,
                    "uncovered_vectors": uncovered,
                    "friction_entries": friction,
                    "risk_score": uncovered * 2 + friction,
                })
            })
            .collect();

        let total_covered: u32 = by_system.values().map(|(c, _, _)| c).sum();
        let total_uncovered: u32 = by_system.values().map(|(_, u, _)| u).sum();
        let total_friction: u32 = by_system.values().map(|(_, _, f)| f).sum();

        Ok(json!({
            "status": format!("{:?}", result.status),
            "total_vectors": result.redteam.len(),
            "total_covered": total_covered,
            "total_uncovered": total_uncovered,
            "total_friction_entries": total_friction,
            "coverage_pct": (total_covered * 100)
                .checked_div(total_covered + total_uncovered)
                .unwrap_or(0),
            "systems": summary,
            "notes": result.notes,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── Registration ──────────────────────────────────────────────────────

/// Register RSI friction tools into a registry.
#[allow(clippy::too_many_arguments)]
pub fn register_rsi(
    registry: &wm_dispatch::ToolRegistry,
    store: &Arc<MemoryStore>,
    search: Option<Arc<SearchEngine>>,
    associations: &Arc<wm_memory::AssociationStore>,
    karma_ledger: Option<Arc<KarmaLedger>>,
    workspace: Option<Arc<std::sync::Mutex<GlobalWorkspace>>>,
) -> wm_dispatch::ToolRegistry {
    registry
        .register(Arc::new(FrictionLogTool::new(
            store.clone(),
            search.clone(),
        )))
        .register(Arc::new(FrictionReviewTool::new(store.clone())))
        .register(Arc::new(FrictionAutoLogTool::new(store.clone(), search)))
        .register(Arc::new(ImproveProposalsTool::new(
            store.clone(),
            associations.clone(),
        )))
        .register(Arc::new(RedteamProposalsTool::new(
            store.clone(),
            associations.clone(),
        )))
        .register(Arc::new(ActiveProposalsTool::new(store.clone())))
        .register(Arc::new(FrictionResolveTool::new(
            store.clone(),
            karma_ledger,
            workspace,
        )))
        .register(Arc::new(RedteamFromFrictionTool::new(store.clone())))
        .register(Arc::new(RedteamCoverageReportTool::new(
            store.clone(),
            associations.clone(),
        )))
}

// ── Tests ─────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use wm_core::BrainWave;

    #[tokio::test]
    async fn friction_log_creates_tagged_memory() {
        let tmp = tempfile::tempdir().unwrap();
        let store = Arc::new(MemoryStore::open_default(tmp.path()).unwrap());
        let tool = FrictionLogTool::new(store.clone(), None);

        let mut ctx = Context::new(BrainWave::Gamma);
        let args = json!({
            "what_happened": "memory.search returned 0 results for a query that should have matches",
            "expected_behavior": "Should return at least 3 results",
            "suggested_fix": "Check Tantivy index health",
            "severity": "high",
            "category": "performance",
            "tool_name": "memory.search"
        });

        let result = tool.call(&mut ctx, args).await;
        assert!(result.is_ok());

        let resp = result.unwrap();
        assert_eq!(resp["status"], "success");

        // Verify the memory was created with correct tags
        let memories = store.scan(wm_core::Galaxy::Codex, 10).unwrap();
        assert_eq!(memories.len(), 1);
        assert!(
            memories[0]
                .metadata
                .tags
                .contains(&"rsi:friction".to_string())
        );
        assert!(
            memories[0]
                .metadata
                .tags
                .contains(&"rsi:severity:high".to_string())
        );
        assert!(
            memories[0]
                .metadata
                .tags
                .contains(&"rsi:category:performance".to_string())
        );
        assert!(
            memories[0]
                .metadata
                .tags
                .contains(&"rsi:tool:memory.search".to_string())
        );
        assert!((memories[0].metadata.importance - 0.9).abs() < 0.01);
    }

    #[tokio::test]
    async fn friction_log_requires_what_happened() {
        let tmp = tempfile::tempdir().unwrap();
        let store = Arc::new(MemoryStore::open_default(tmp.path()).unwrap());
        let tool = FrictionLogTool::new(store, None);

        let mut ctx = Context::new(BrainWave::Gamma);
        let args = json!({
            "expected_behavior": "Should work"
        });

        let result = tool.call(&mut ctx, args).await;
        assert!(result.is_err());
    }

    #[tokio::test]
    async fn friction_log_requires_expected_behavior() {
        let tmp = tempfile::tempdir().unwrap();
        let store = Arc::new(MemoryStore::open_default(tmp.path()).unwrap());
        let tool = FrictionLogTool::new(store, None);

        let mut ctx = Context::new(BrainWave::Gamma);
        let args = json!({
            "what_happened": "Something broke"
        });

        let result = tool.call(&mut ctx, args).await;
        assert!(result.is_err());
    }

    #[tokio::test]
    async fn friction_review_finds_tagged_entries() {
        let tmp = tempfile::tempdir().unwrap();
        let store = Arc::new(MemoryStore::open_default(tmp.path()).unwrap());

        // Create some friction entries
        let log_tool = FrictionLogTool::new(store.clone(), None);
        let mut ctx = Context::new(BrainWave::Gamma);

        log_tool
            .call(
                &mut ctx,
                json!({
                    "what_happened": "Tool A failed",
                    "expected_behavior": "Should succeed",
                    "severity": "high",
                    "category": "error",
                    "tool_name": "tool_a"
                }),
            )
            .await
            .unwrap();

        log_tool
            .call(
                &mut ctx,
                json!({
                    "what_happened": "Tool B slow",
                    "expected_behavior": "Should be fast",
                    "severity": "low",
                    "category": "performance",
                    "tool_name": "tool_b"
                }),
            )
            .await
            .unwrap();

        // Create a non-friction memory (should be filtered out)
        let mut other = Memory::new(wm_core::Galaxy::Codex, "not a friction entry".into());
        other.metadata.tags = vec!["other".to_string()];
        store.put(wm_core::Galaxy::Codex, &other).unwrap();

        // Review all friction entries
        let review_tool = FrictionReviewTool::new(store);
        let result = review_tool.call(&mut ctx, json!({})).await;
        assert!(result.is_ok());

        let resp = result.unwrap();
        assert_eq!(resp["total_friction_entries"], 2);
        assert_eq!(resp["summary"]["by_category"]["error"], 1);
        assert_eq!(resp["summary"]["by_category"]["performance"], 1);
        assert_eq!(resp["summary"]["by_severity"]["high"], 1);
        assert_eq!(resp["summary"]["by_severity"]["low"], 1);
    }

    #[tokio::test]
    async fn friction_review_filters_by_category() {
        let tmp = tempfile::tempdir().unwrap();
        let store = Arc::new(MemoryStore::open_default(tmp.path()).unwrap());
        let log_tool = FrictionLogTool::new(store.clone(), None);
        let mut ctx = Context::new(BrainWave::Gamma);

        log_tool
            .call(
                &mut ctx,
                json!({
                    "what_happened": "Error 1",
                    "expected_behavior": "No error",
                    "category": "error"
                }),
            )
            .await
            .unwrap();

        log_tool
            .call(
                &mut ctx,
                json!({
                    "what_happened": "Slow 1",
                    "expected_behavior": "Fast",
                    "category": "performance"
                }),
            )
            .await
            .unwrap();

        let review_tool = FrictionReviewTool::new(store);
        let result = review_tool
            .call(&mut ctx, json!({"category": "error"}))
            .await;
        let resp = result.unwrap();
        assert_eq!(resp["total_friction_entries"], 1);
    }

    #[tokio::test]
    async fn friction_auto_log_creates_entry() {
        let tmp = tempfile::tempdir().unwrap();
        let store = Arc::new(MemoryStore::open_default(tmp.path()).unwrap());
        let tool = FrictionAutoLogTool::new(store.clone(), None);

        // Test programmatic API with rich telemetry
        let telemetry = DispatchTelemetry {
            tool: "memory.search".to_string(),
            success: false,
            latency_ms: 45.3,
            error: "Tantivy index not found".to_string(),
            brain_wave: "Beta".to_string(),
            effectiveness: 0.42,
            karma_debt: 0.15,
            self_model_confidence: 0.58,
            drive_bias_confidence: 0.71,
            citta_coherence: 0.9,
            citta_valence: -0.2,
            tool_stats: ToolStatsSnapshot::default(),
            routed_via_wm: false,
            arg_size_bytes: 156,
            response_size_bytes: 0,
        };
        tool.log_error(&telemetry).unwrap();

        let memories = store.scan(wm_core::Galaxy::Codex, 10).unwrap();
        assert_eq!(memories.len(), 1);
        assert!(
            memories[0]
                .metadata
                .tags
                .contains(&"rsi:friction".to_string())
        );
        assert!(
            memories[0]
                .metadata
                .tags
                .contains(&"rsi:category:error".to_string())
        );
        assert!(
            memories[0]
                .metadata
                .tags
                .contains(&"rsi:tool:memory.search".to_string())
        );
        assert_eq!(memories[0].metadata.source, "auto");
        assert!((memories[0].metadata.source_trust - 0.8).abs() < 0.01);

        // Verify telemetry JSON is embedded in content
        assert!(memories[0].content.contains("```json"));
        assert!(memories[0].content.contains("\"brain_wave\": \"Beta\""));
        assert!(memories[0].content.contains("\"effectiveness\": 0.42"));
    }

    #[tokio::test]
    async fn friction_auto_log_via_tool_call() {
        let tmp = tempfile::tempdir().unwrap();
        let store = Arc::new(MemoryStore::open_default(tmp.path()).unwrap());
        let tool = FrictionAutoLogTool::new(store.clone(), None);

        let mut ctx = Context::new(BrainWave::Gamma);
        let args = json!({
            "tool_name": "karma.report",
            "error": "LMDB read failed: MDB_NOTFOUND",
            "latency_ms": 12.5
        });

        let result = tool.call(&mut ctx, args).await;
        assert!(result.is_ok());

        let memories = store.scan(wm_core::Galaxy::Codex, 10).unwrap();
        assert_eq!(memories.len(), 1);
    }

    #[tokio::test]
    async fn friction_auto_log_requires_tool_name() {
        let tmp = tempfile::tempdir().unwrap();
        let store = Arc::new(MemoryStore::open_default(tmp.path()).unwrap());
        let tool = FrictionAutoLogTool::new(store, None);

        let mut ctx = Context::new(BrainWave::Gamma);
        let result = tool.call(&mut ctx, json!({"error": "something"})).await;
        assert!(result.is_err());
    }

    #[tokio::test]
    async fn friction_log_default_severity_is_medium() {
        let tmp = tempfile::tempdir().unwrap();
        let store = Arc::new(MemoryStore::open_default(tmp.path()).unwrap());
        let tool = FrictionLogTool::new(store.clone(), None);

        let mut ctx = Context::new(BrainWave::Gamma);
        tool.call(
            &mut ctx,
            json!({
                "what_happened": "Minor issue",
                "expected_behavior": "Should not happen"
            }),
        )
        .await
        .unwrap();

        let memories = store.scan(wm_core::Galaxy::Codex, 10).unwrap();
        assert!(
            memories[0]
                .metadata
                .tags
                .contains(&"rsi:severity:medium".to_string())
        );
        assert!(
            memories[0]
                .metadata
                .tags
                .contains(&"rsi:category:ux".to_string())
        );
    }

    #[tokio::test]
    async fn register_rsi_adds_nine_tools() {
        let tmp = tempfile::tempdir().unwrap();
        let store = Arc::new(MemoryStore::open_default(tmp.path()).unwrap());
        let associations = Arc::new(wm_memory::AssociationStore::open(store.env()).unwrap());
        let registry = wm_dispatch::ToolRegistry::new();
        let registry = register_rsi(&registry, &store, None, &associations, None, None);

        assert!(registry.get("friction.log").is_some());
        assert!(registry.get("friction.review").is_some());
        assert!(registry.get("friction.auto_log").is_some());
        assert!(registry.get("improve.proposals").is_some());
        assert!(registry.get("redteam.proposals").is_some());
        assert!(registry.get("improve.active_proposals").is_some());
        assert!(registry.get("friction.resolve").is_some());
        assert!(registry.get("redteam.from_friction").is_some());
        assert!(registry.get("redteam.coverage_report").is_some());
    }

    #[tokio::test]
    async fn redteam_proposals_returns_proposals() {
        let tmp = tempfile::tempdir().unwrap();
        let store = Arc::new(MemoryStore::open_default(tmp.path()).unwrap());
        let associations = Arc::new(wm_memory::AssociationStore::open(store.env()).unwrap());
        let tool = RedteamProposalsTool::new(store, associations);

        let mut ctx = Context::new(BrainWave::Gamma);
        let result = tool.call(&mut ctx, json!({})).await;
        assert!(result.is_ok());
        let resp = result.unwrap();
        assert!(resp["proposals_generated"].as_u64().unwrap_or(0) > 0);
        assert!(resp["proposals"].is_array());
    }

    #[tokio::test]
    async fn improve_proposals_returns_no_proposals_when_empty() {
        let tmp = tempfile::tempdir().unwrap();
        let store = Arc::new(MemoryStore::open_default(tmp.path()).unwrap());
        let associations = Arc::new(wm_memory::AssociationStore::open(store.env()).unwrap());
        let tool = ImproveProposalsTool::new(store, associations);

        let mut ctx = Context::new(BrainWave::Gamma);
        let result = tool.call(&mut ctx, json!({})).await;
        assert!(result.is_ok());
        let resp = result.unwrap();
        assert_eq!(resp["proposals_generated"], 0);
    }

    #[tokio::test]
    async fn improve_proposals_returns_proposals_from_friction() {
        let tmp = tempfile::tempdir().unwrap();
        let store = Arc::new(MemoryStore::open_default(tmp.path()).unwrap());
        let associations = Arc::new(wm_memory::AssociationStore::open(store.env()).unwrap());

        // Add friction entries
        let log_tool = FrictionLogTool::new(store.clone(), None);
        let mut ctx = Context::new(BrainWave::Gamma);
        log_tool
            .call(
                &mut ctx,
                json!({
                    "what_happened": "Error 1",
                    "expected_behavior": "No error",
                    "severity": "high",
                    "category": "error",
                    "tool_name": "tool_x"
                }),
            )
            .await
            .unwrap();
        log_tool
            .call(
                &mut ctx,
                json!({
                    "what_happened": "Error 2",
                    "expected_behavior": "No error",
                    "severity": "medium",
                    "category": "error",
                    "tool_name": "tool_x"
                }),
            )
            .await
            .unwrap();

        let tool = ImproveProposalsTool::new(store, associations);
        let result = tool.call(&mut ctx, json!({})).await;
        assert!(result.is_ok());
        let resp = result.unwrap();
        assert_eq!(resp["proposals_generated"], 1);
        assert_eq!(resp["proposals"][0]["target"], "tool_x");
        assert_eq!(resp["proposals"][0]["pattern_count"], 2);
    }

    #[tokio::test]
    async fn dispatch_telemetry_serialization_roundtrip() {
        let telemetry = DispatchTelemetry {
            tool: "memory.search".to_string(),
            success: false,
            latency_ms: 45.3,
            error: "Tantivy index not found".to_string(),
            brain_wave: "Beta".to_string(),
            effectiveness: 0.42,
            karma_debt: 0.15,
            self_model_confidence: 0.58,
            drive_bias_confidence: 0.71,
            citta_coherence: 0.9,
            citta_valence: -0.2,
            tool_stats: ToolStatsSnapshot {
                call_count: 23,
                success_count: 19,
                p50_latency_ns: 12_000_000,
                peak_latency_ns: 89_000_000,
                cpu_time_ns: 276_000_000,
                lmdb_pages_touched: 142,
                last_used_unix: 1723000000,
                effectiveness: 0.42,
            },
            routed_via_wm: true,
            arg_size_bytes: 156,
            response_size_bytes: 0,
        };

        let json_str = serde_json::to_string(&telemetry).unwrap();
        let deserialized: DispatchTelemetry = serde_json::from_str(&json_str).unwrap();

        assert_eq!(deserialized.tool, "memory.search");
        assert!(!deserialized.success);
        assert!((deserialized.latency_ms - 45.3).abs() < 0.01);
        assert_eq!(deserialized.error, "Tantivy index not found");
        assert_eq!(deserialized.brain_wave, "Beta");
        assert!((deserialized.effectiveness - 0.42).abs() < 0.001);
        assert!((deserialized.karma_debt - 0.15).abs() < 0.001);
        assert!((deserialized.self_model_confidence - 0.58).abs() < 0.001);
        assert!((deserialized.drive_bias_confidence - 0.71).abs() < 0.001);
        assert!((deserialized.citta_coherence - 0.9).abs() < 0.001);
        assert!((deserialized.citta_valence - (-0.2)).abs() < 0.001);
        assert_eq!(deserialized.tool_stats.call_count, 23);
        assert_eq!(deserialized.tool_stats.success_count, 19);
        assert_eq!(deserialized.tool_stats.p50_latency_ns, 12_000_000);
        assert_eq!(deserialized.tool_stats.peak_latency_ns, 89_000_000);
        assert!(deserialized.routed_via_wm);
        assert_eq!(deserialized.arg_size_bytes, 156);
        assert_eq!(deserialized.response_size_bytes, 0);
    }

    #[tokio::test]
    async fn friction_auto_log_anomaly_creates_entry() {
        let tmp = tempfile::tempdir().unwrap();
        let store = Arc::new(MemoryStore::open_default(tmp.path()).unwrap());
        let tool = FrictionAutoLogTool::new(store.clone(), None);

        let telemetry = DispatchTelemetry::minimal("gnosis", "", 500.0);
        tool.log_anomaly(&telemetry, "high_latency").unwrap();

        let memories = store.scan(wm_core::Galaxy::Codex, 10).unwrap();
        assert_eq!(memories.len(), 1);
        assert!(
            memories[0]
                .metadata
                .tags
                .contains(&"rsi:friction".to_string())
        );
        assert!(
            memories[0]
                .metadata
                .tags
                .contains(&"rsi:anomaly".to_string())
        );
        assert!(
            memories[0]
                .metadata
                .tags
                .contains(&"rsi:category:performance".to_string())
        );
        assert_eq!(memories[0].metadata.source, "auto");
    }

    #[tokio::test]
    async fn friction_dedup_log_error_increments_count() {
        let tmp = tempfile::tempdir().unwrap();
        let store = Arc::new(MemoryStore::open_default(tmp.path()).unwrap());
        let tool = FrictionAutoLogTool::new(store.clone(), None);

        let telemetry = DispatchTelemetry::minimal("memory.search", "Index not found", 45.0);

        // First occurrence: creates new entry
        tool.log_error(&telemetry).unwrap();
        let memories = store.scan(wm_core::Galaxy::Codex, 10).unwrap();
        assert_eq!(memories.len(), 1);
        let dup_tag = memories[0]
            .metadata
            .tags
            .iter()
            .find(|t| t.starts_with("rsi:dup:"))
            .unwrap();
        assert_eq!(dup_tag, "rsi:dup:1");

        // Second occurrence: increments duplicate_count
        tool.log_error(&telemetry).unwrap();
        let memories = store.scan(wm_core::Galaxy::Codex, 10).unwrap();
        assert_eq!(memories.len(), 1, "should still be 1 entry (deduped)");
        let dup_tag = memories[0]
            .metadata
            .tags
            .iter()
            .find(|t| t.starts_with("rsi:dup:"))
            .unwrap();
        assert_eq!(dup_tag, "rsi:dup:2");

        // Third occurrence: increments again
        tool.log_error(&telemetry).unwrap();
        let memories = store.scan(wm_core::Galaxy::Codex, 10).unwrap();
        assert_eq!(memories.len(), 1, "should still be 1 entry (deduped)");
        let dup_tag = memories[0]
            .metadata
            .tags
            .iter()
            .find(|t| t.starts_with("rsi:dup:"))
            .unwrap();
        assert_eq!(dup_tag, "rsi:dup:3");
    }

    #[tokio::test]
    async fn friction_dedup_log_tool_increments_count() {
        let tmp = tempfile::tempdir().unwrap();
        let store = Arc::new(MemoryStore::open_default(tmp.path()).unwrap());
        let tool = FrictionLogTool::new(store.clone(), None);
        let mut ctx = Context::new(BrainWave::Gamma);

        let args = json!({
            "what_happened": "Tool A failed",
            "expected_behavior": "Should succeed",
            "severity": "high",
            "category": "error",
            "tool_name": "tool_a"
        });

        // First call: creates new
        let result = tool.call(&mut ctx, args).await.unwrap();
        assert_eq!(result["status"], "success");

        // Second call: dedup
        let args = json!({
            "what_happened": "Tool A failed",
            "expected_behavior": "Should succeed",
            "severity": "high",
            "category": "error",
            "tool_name": "tool_a"
        });
        let result = tool.call(&mut ctx, args).await.unwrap();
        assert_eq!(result["status"], "duplicate");
        assert_eq!(result["duplicate_count"], 2);

        // Third call: dedup again
        let args = json!({
            "what_happened": "Tool A failed",
            "expected_behavior": "Should succeed",
            "severity": "high",
            "category": "error",
            "tool_name": "tool_a"
        });
        let result = tool.call(&mut ctx, args).await.unwrap();
        assert_eq!(result["status"], "duplicate");
        assert_eq!(result["duplicate_count"], 3);

        // Should still be only 1 entry
        let memories = store.scan(wm_core::Galaxy::Codex, 10).unwrap();
        assert_eq!(memories.len(), 1);
    }

    #[tokio::test]
    async fn friction_hash_is_deterministic() {
        let h1 = friction_hash("tool_a", "error", "high", "something went wrong");
        let h2 = friction_hash("tool_a", "error", "high", "something went wrong");
        assert_eq!(h1, h2);

        // Different tool → different hash
        let h3 = friction_hash("tool_b", "error", "high", "something went wrong");
        assert_ne!(h1, h3);

        // Different category → different hash
        let h4 = friction_hash("tool_a", "performance", "high", "something went wrong");
        assert_ne!(h1, h4);

        // Different error → different hash
        let h5 = friction_hash("tool_a", "error", "high", "something else went wrong");
        assert_ne!(h1, h5);
    }

    #[tokio::test]
    async fn active_proposals_tool_retrieves_proposals() {
        let tmp = tempfile::tempdir().unwrap();
        let store = Arc::new(MemoryStore::open_default(tmp.path()).unwrap());
        let tool = ActiveProposalsTool::new(store.clone());

        // Store a proposal memory
        let mut mem = Memory::new(
            wm_core::Galaxy::Codex,
            "## Test Proposal\n\nFix tool_a".to_string(),
        );
        mem.metadata.tags = vec![
            "rsi:proposal".to_string(),
            "rsi:proposal:active".to_string(),
            "rsi:proposal:sig:error:tool_a:high".to_string(),
            "rsi:severity:high".to_string(),
            "rsi:category:error".to_string(),
            "rsi:tool:tool_a".to_string(),
        ];
        store.put(wm_core::Galaxy::Codex, &mem).unwrap();

        // Store a non-proposal memory (should be filtered out)
        let mut other = Memory::new(wm_core::Galaxy::Codex, "Just a regular memory".to_string());
        other.metadata.tags = vec!["rsi:friction".to_string()];
        store.put(wm_core::Galaxy::Codex, &other).unwrap();

        let mut ctx = Context::new(BrainWave::Gamma);
        let result = tool.call(&mut ctx, json!({})).await.unwrap();
        assert_eq!(result["status"], "success");
        assert_eq!(result["active_proposals"], 1);
        assert_eq!(result["proposals"][0]["category"], "error");
        assert_eq!(result["proposals"][0]["target"], "tool_a");
        assert_eq!(result["proposals"][0]["signature"], "error:tool_a:high");
    }

    #[tokio::test]
    async fn friction_resolve_tool_tags_resolved() {
        let tmp = tempfile::tempdir().unwrap();
        let store = Arc::new(MemoryStore::open_default(tmp.path()).unwrap());

        // Create a friction entry
        let mut mem = Memory::new(
            wm_core::Galaxy::Codex,
            "## Friction: tool crashed\n\nBad error".to_string(),
        );
        mem.metadata.tags = vec![
            "rsi:friction".to_string(),
            "rsi:severity:high".to_string(),
            "rsi:category:error".to_string(),
            "rsi:tool:tool_a".to_string(),
        ];
        store.put(wm_core::Galaxy::Codex, &mem).unwrap();
        let friction_id = mem.metadata.id.to_string();

        // Resolve it
        let tool = FrictionResolveTool::new(store.clone(), None, None);
        let mut ctx = Context::new(BrainWave::Gamma);
        let result = tool
            .call(
                &mut ctx,
                json!({
                    "friction_id": friction_id,
                    "resolution_note": "Fixed the bug",
                    "resolution_method": "code_fix",
                }),
            )
            .await
            .unwrap();

        assert_eq!(result["status"], "resolved");
        assert_eq!(result["resolution_method"], "code_fix");

        // Verify the entry is tagged as resolved
        let memories = store.scan(wm_core::Galaxy::Codex, 10).unwrap();
        let entry = &memories[0];
        assert!(entry.metadata.tags.iter().any(|t| t == "rsi:resolved"));
        assert!(
            entry
                .metadata
                .tags
                .iter()
                .any(|t| t == "rsi:resolved_method:code_fix")
        );
    }

    #[tokio::test]
    async fn friction_resolve_already_resolved_returns_early() {
        let tmp = tempfile::tempdir().unwrap();
        let store = Arc::new(MemoryStore::open_default(tmp.path()).unwrap());

        let mut mem = Memory::new(
            wm_core::Galaxy::Codex,
            "## Friction: already fixed".to_string(),
        );
        mem.metadata.tags = vec![
            "rsi:friction".to_string(),
            "rsi:resolved".to_string(),
            "rsi:tool:tool_a".to_string(),
        ];
        store.put(wm_core::Galaxy::Codex, &mem).unwrap();

        let tool = FrictionResolveTool::new(store, None, None);
        let mut ctx = Context::new(BrainWave::Gamma);
        let result = tool
            .call(
                &mut ctx,
                json!({
                    "friction_id": mem.metadata.id.to_string(),
                    "resolution_note": "fix again",
                }),
            )
            .await
            .unwrap();

        assert_eq!(result["status"], "already_resolved");
    }

    #[tokio::test]
    async fn regression_detection_in_log_error_creates_new_entry() {
        let tmp = tempfile::tempdir().unwrap();
        let store = Arc::new(MemoryStore::open_default(tmp.path()).unwrap());
        let tool = FrictionAutoLogTool::new(store.clone(), None);

        // First: log an error
        let telemetry = DispatchTelemetry {
            tool: "memory.search".to_string(),
            success: false,
            latency_ms: 50.0,
            error: "timeout error".to_string(),
            brain_wave: "Gamma".to_string(),
            effectiveness: 0.5,
            karma_debt: 0.0,
            self_model_confidence: 0.5,
            drive_bias_confidence: 0.5,
            citta_coherence: 0.5,
            citta_valence: 0.0,
            tool_stats: ToolStatsSnapshot::default(),
            routed_via_wm: false,
            arg_size_bytes: 100,
            response_size_bytes: 0,
        };
        tool.log_error(&telemetry).unwrap();

        // Resolve the entry
        let memories = store.scan(wm_core::Galaxy::Codex, 10).unwrap();
        let mut entry = memories[0].clone();
        entry.metadata.tags.push("rsi:resolved".to_string());
        store.put(wm_core::Galaxy::Codex, &entry).unwrap();

        // Log the same error again — should create a regression entry
        tool.log_error(&telemetry).unwrap();

        let memories = store.scan(wm_core::Galaxy::Codex, 10).unwrap();
        let regression = memories
            .iter()
            .find(|m| m.metadata.tags.iter().any(|t| t == "rsi:regression"))
            .expect("Should have a regression entry");

        assert!(
            regression
                .metadata
                .tags
                .iter()
                .any(|t| t == "rsi:severity:high")
        );
        assert!(
            regression
                .metadata
                .tags
                .iter()
                .any(|t| t.starts_with("rsi:regression_of:"))
        );
    }

    #[tokio::test]
    async fn redteam_from_friction_generates_regression_tests() {
        let tmp = tempfile::tempdir().unwrap();
        let store = Arc::new(MemoryStore::open_default(tmp.path()).unwrap());

        // Log a friction entry
        let log_tool = FrictionLogTool::new(store.clone(), None);
        let mut ctx = Context::new(BrainWave::Gamma);
        let result = log_tool
            .call(
                &mut ctx,
                json!({
                    "what_happened": "Tool returns wrong type",
                    "expected_behavior": "Should return JSON",
                    "severity": "medium",
                    "category": "error",
                    "tool_name": "memory.search"
                }),
            )
            .await
            .unwrap();
        let friction_id = result["id"].as_str().unwrap().to_string();

        // Resolve it
        let resolve_tool = FrictionResolveTool::new(store.clone(), None, None);
        let _ = resolve_tool
            .call(
                &mut ctx,
                json!({
                    "friction_id": friction_id,
                    "resolution_note": "Fixed return type",
                    "resolution_method": "code_fix"
                }),
            )
            .await
            .unwrap();

        // Now run redteam.from_friction
        let rtf_tool = RedteamFromFrictionTool::new(store);
        let result = rtf_tool.call(&mut ctx, json!({})).await.unwrap();

        assert_eq!(result["status"], "success");
        assert_eq!(result["resolved_friction_count"], 1);
        assert_eq!(result["regression_count"], 0);
        assert_eq!(result["proposals_generated"], 1);

        let proposal = &result["proposals"][0];
        assert_eq!(proposal["target_system"], "memory.search");
        assert_eq!(proposal["is_regression"], false);
        assert_eq!(proposal["risk_level"], "high");
        assert!(
            proposal["test_pseudocode"]
                .as_str()
                .unwrap()
                .contains("memory.search")
        );
    }

    #[tokio::test]
    async fn redteam_from_friction_detects_regressions() {
        let tmp = tempfile::tempdir().unwrap();
        let store = Arc::new(MemoryStore::open_default(tmp.path()).unwrap());

        // Log + resolve + re-log to create a regression
        let log_tool = FrictionLogTool::new(store.clone(), None);
        let mut ctx = Context::new(BrainWave::Gamma);

        let args = json!({
            "what_happened": "Crash on empty input",
            "expected_behavior": "Should handle gracefully",
            "severity": "medium",
            "category": "error",
            "tool_name": "memory.create"
        });
        let result = log_tool.call(&mut ctx, args.clone()).await.unwrap();
        let friction_id = result["id"].as_str().unwrap().to_string();

        let resolve_tool = FrictionResolveTool::new(store.clone(), None, None);
        let _ = resolve_tool
            .call(
                &mut ctx,
                json!({
                    "friction_id": friction_id,
                    "resolution_note": "Added null check",
                    "resolution_method": "code_fix"
                }),
            )
            .await
            .unwrap();

        // Re-log same friction → regression
        let _ = log_tool.call(&mut ctx, args).await.unwrap();

        // Run redteam.from_friction
        let rtf_tool = RedteamFromFrictionTool::new(store);
        let result = rtf_tool.call(&mut ctx, json!({})).await.unwrap();

        assert_eq!(result["status"], "success");
        assert!(result["regression_count"].as_u64().unwrap() >= 1);

        let regression_proposal = result["proposals"]
            .as_array()
            .unwrap()
            .iter()
            .find(|p| p["is_regression"] == true)
            .expect("Should have a regression proposal");
        assert_eq!(regression_proposal["risk_level"], "critical");
        assert!(
            regression_proposal["attack_vector"]
                .as_str()
                .unwrap()
                .contains("Regression")
        );
    }

    #[tokio::test]
    async fn redteam_coverage_report_returns_summary() {
        let tmp = tempfile::tempdir().unwrap();
        let store = Arc::new(MemoryStore::open_default(tmp.path()).unwrap());
        let associations = Arc::new(wm_memory::AssociationStore::open(store.env()).unwrap());
        let tool = RedteamCoverageReportTool::new(store, associations);

        let mut ctx = Context::new(BrainWave::Gamma);
        let result = tool.call(&mut ctx, json!({})).await.unwrap();

        assert!(result["status"].as_str().is_some());
        assert!(result["total_vectors"].as_u64().unwrap_or(0) > 0);
        assert!(result["systems"].is_array());
        assert!(result["coverage_pct"].as_u64().is_some());
    }
}
