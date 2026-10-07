//! WhiteMagic Gen3 — Hybrid Contract Bridge & Dual-Profile MCP Routing Adapter.
//!
//! Provides the "Lossless Core Swap" interface:
//! 1. Preserves 100% of the public MCP interface and Gen2 contract (`contract.rs`).
//! 2. Exposes dual profiles: `cyberbrain` (10 lean tools for CLI agents) and
//!    `full` / `curated` (37 tools for full IDE extensions).
//! 3. Bridges legacy tool calls (`memory.create`, `memory.search`, `memory.read`,
//!    `session.continuity`, etc.) to Gen3 Substrate operations with bijective
//!    UUID <-> u64 identity translation.
//! 4. Powers natural language thought routing via an embedded TF-IDF NLU classifier.

#![forbid(unsafe_code)]

use chrono::{DateTime, NaiveDate, Utc};
use serde::{Deserialize, Serialize};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::collections::{HashMap, HashSet};
use std::io::Write;
use std::path::Path;
use std::str::FromStr;
use std::sync::OnceLock;
use uuid::Uuid;

use wm_gen3_core::compat::{Gen2EpisodicRecord, Gen2Reader};
use wm_gen3_core::evidence::RatifiedChannel;
use wm_gen3_core::mandala::{
    Signature, Signer, SigningKey, Verifier, VerifyingKey, resolve_or_create_mandala_gate_key,
};
use wm_gen3_core::mesh::{MeshClient, resolve_or_create_mesh_key};
use wm_gen3_core::ops::{
    ImportKind, RecallQuery, RememberItem, SessionCheckpoint, SessionContinuityView, SessionTurn,
    Substrate, compose_session_digest,
};

/// Active MCP Tool Profile.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum McpProfile {
    /// 10 lean tools for CLI agents (Antigravity, Claude Code, Opencode).
    Cyberbrain,
    /// 37 tools: complete curated memory hierarchy, receipts, session continuity, and Mandala.
    Full,
}

impl FromStr for McpProfile {
    type Err = String;
    fn from_str(s: &str) -> Result<Self, Self::Err> {
        match s.to_ascii_lowercase().as_str() {
            "cyberbrain" | "lean" | "minimal" => Ok(McpProfile::Cyberbrain),
            "full" | "curated" | "enterprise" => Ok(McpProfile::Full),
            other => Err(format!(
                "Unknown MCP profile '{other}'. Supported profiles: 'cyberbrain', 'full'"
            )),
        }
    }
}

/// NLU Tool Profile for keyword and intent matching.
#[derive(Debug, Clone)]
pub struct NluProfile {
    pub route: &'static str,
    pub keywords: &'static [(&'static str, f64)],
}

/// Curated NLU tool profiles for natural language routing.
pub static NLU_PROFILES: &[NluProfile] = &[
    NluProfile {
        route: "memory.create",
        keywords: &[
            ("remember", 8.0),
            ("store", 7.0),
            ("save", 6.0),
            ("memorize", 6.0),
            ("record", 3.0),
            ("persist", 3.0),
            ("capture", 2.0),
            ("note", 2.0),
            ("write", 1.5),
        ],
    },
    NluProfile {
        route: "memory.search",
        keywords: &[
            ("search", 8.0),
            ("recall", 7.5),
            ("find", 7.0),
            ("lookup", 6.0),
            ("query", 5.0),
            ("retrieve", 5.0),
            ("memories", 4.0),
            ("where", 2.0),
            ("what", 1.5),
        ],
    },
    NluProfile {
        route: "memory.read",
        keywords: &[
            ("read", 6.0),
            ("fetch", 5.5),
            ("get", 4.0),
            ("view", 3.0),
            ("inspect", 2.5),
            ("id", 2.0),
            ("exact", 2.0),
        ],
    },
    NluProfile {
        route: "memory.list",
        keywords: &[
            ("list", 7.0),
            ("browse", 6.0),
            ("enumerate", 5.0),
            ("all", 3.0),
            ("recent", 2.5),
        ],
    },
    NluProfile {
        route: "session.continuity",
        keywords: &[
            ("continuity", 9.0),
            ("resume", 8.0),
            ("handoff", 7.5),
            ("catchup", 6.0),
            ("catch up", 6.0),
            ("where was i", 7.0),
            ("last session", 6.5),
            ("context", 4.0),
            ("briefing", 5.0),
        ],
    },
    NluProfile {
        route: "session.record",
        keywords: &[
            ("turn", 7.0),
            ("decision", 6.5),
            ("breakthrough", 6.0),
            ("log", 5.0),
            ("action", 3.0),
        ],
    },
    NluProfile {
        route: "session.checkpoint",
        keywords: &[
            ("checkpoint", 9.0),
            ("savepoint", 7.0),
            ("milestone", 6.0),
            ("snapshot", 5.0),
        ],
    },
    NluProfile {
        route: "mandala.status",
        keywords: &[
            ("mandala", 8.0),
            ("kekkai", 7.5),
            ("sandbox", 7.0),
            ("isolation", 6.0),
            ("landlock", 6.0),
            ("security", 4.0),
            ("confinement", 4.0),
        ],
    },
    NluProfile {
        route: "mandala.triage",
        keywords: &[
            ("triage", 8.5),
            ("jev", 8.0),
            ("classify", 6.0),
            ("route task", 5.5),
            ("gate", 5.0),
        ],
    },
    NluProfile {
        route: "mandala.evaluate",
        keywords: &[
            ("evaluate", 8.0),
            ("execute sandbox", 7.5),
            ("run candidate", 7.0),
            ("benchmark", 5.0),
        ],
    },
    NluProfile {
        route: "mesh_sync",
        keywords: &[
            ("mesh", 8.5),
            ("sync", 8.0),
            ("peer", 7.0),
            ("p2p", 6.5),
            ("replicate", 5.0),
            ("synchronize", 5.0),
        ],
    },
    NluProfile {
        route: "memory.stats",
        keywords: &[
            ("stats", 8.0),
            ("statistics", 7.0),
            ("metrics", 6.0),
            ("health", 5.0),
            ("epoch", 4.0),
        ],
    },
];

/// Predict the target route for a natural language thought.
pub fn predict_route_from_thought(thought: &str) -> (&'static str, f64) {
    let lower = thought.to_lowercase();
    let tokens: Vec<&str> = lower
        .split(|c: char| !c.is_alphanumeric() && c != '_')
        .filter(|t| !t.is_empty())
        .collect();

    let mut best_route = "memory.search";
    let mut best_score = 0.0;

    for profile in NLU_PROFILES {
        let mut score = 0.0;
        for &(kw, weight) in profile.keywords {
            if kw.contains(' ') {
                if lower.contains(kw) {
                    score += weight * 1.5;
                }
            } else if tokens.contains(&kw) {
                score += weight;
            }
        }
        if score > best_score {
            best_score = score;
            best_route = profile.route;
        }
    }

    (best_route, best_score)
}

/// Retrieve the tool list for the specified MCP profile.
pub fn get_tools_list_for_profile(profile: McpProfile, readonly: bool) -> Value {
    match profile {
        McpProfile::Cyberbrain => get_cyberbrain_tools_list(readonly),
        McpProfile::Full => get_full_curated_tools_list(readonly),
    }
}

fn profile_label(profile: McpProfile) -> &'static str {
    match profile {
        McpProfile::Cyberbrain => "cyberbrain",
        McpProfile::Full => "full",
    }
}

/// Canonical capability key for every route accepted by the hybrid dispatch.
///
/// Aliases (underscore/legacy spellings) collapse onto the canonical dot name so
/// the MCP profile allowlist can be enforced at dispatch time, including through
/// the `wm` meta-tool and its alias routes. Unknown names return `None` and fall
/// through to the dispatch's own unknown-tool error.
fn canonical_route(name: &str) -> Option<&'static str> {
    Some(match name {
        "wm" | "whitemagic" => "wm",
        "memory.create" | "memory_create" | "memory_remember" | "remember" => "memory.create",
        "memory.search" | "memory_search" | "memory_recall" | "recall" | "memory.hybrid_recall" => {
            "memory.search"
        }
        "memory.read" | "memory_read" | "memory.get" | "memory_get" | "get" => "memory.read",
        "memory.list" | "memory_list" => "memory.list",
        "memory.count" => "memory.count",
        "memory.stats" | "memory_stats" | "stats" => "memory.stats",
        "memory.pin" => "memory.pin",
        "memory.search_batch" => "memory.search_batch",
        "memory.batch_read" => "memory.batch_read",
        "memory.update" => "memory.update",
        "memory.revisions" => "memory.revisions",
        "memory.associations" => "memory.associations",
        "memory.tags" => "memory.tags",
        "memory.aggregate" => "memory.aggregate",
        "memory.query" | "memory.filter" => "memory.query",
        "memory.ingest" => "memory.ingest",
        "session.record" | "session_record" => "session.record",
        "session.continuity" | "session_continuity" => "session.continuity",
        "session.checkpoint" | "session_checkpoint" => "session.checkpoint",
        "session.start" => "session.start",
        "session.list" | "session_list" => "session.list",
        "session.recall" => "session.recall",
        "session.replay" => "session.replay",
        "session.digest" => "session.digest",
        "receipts.emit" => "receipts.emit",
        "receipts.verify" => "receipts.verify",
        "mandala.status" => "mandala.status",
        "mandala.triage" => "mandala.triage",
        "mandala.evaluate" => "mandala.evaluate",
        "systemone.decide" | "systemone_decide" => "systemone.decide",
        "decision.shortlist" | "system05.shortlist" | "system05_shortlist" => "decision.shortlist",
        "decision.deliberate" | "system15.deliberate" | "deliberate" => "decision.deliberate",
        "decision.outcome" | "receipts.outcome" => "decision.outcome",
        "mesh_sync" | "sync" => "mesh_sync",
        "sweep" => "sweep",
        "inspect" => "inspect",
        "gnosis.status" | "gnosis.explain" | "gnosis" => "gnosis.status",
        "sangha.status" | "sangha_status" => "sangha.status",
        "sangha.inbox" | "sangha_inbox" => "sangha.inbox",
        "sangha.post" | "sangha_post" | "sangha.chat" => "sangha.post",
        "galaxy.list" | "galaxy_list" => "galaxy.list",
        "galaxy.fork" | "galaxy_fork" | "galaxy.branch" | "galaxy_branch" => "galaxy.fork",
        "galaxy.create" | "galaxy_create" => "galaxy.create",
        _ => return None,
    })
}

fn advertised_profile_keys(profile: McpProfile) -> HashSet<&'static str> {
    get_tools_list_for_profile(profile, false)
        .as_array()
        .map(|tools| {
            tools
                .iter()
                .filter_map(|tool| tool.get("name").and_then(Value::as_str))
                .filter_map(canonical_route)
                .collect()
        })
        .unwrap_or_default()
}

fn allowed_profile_keys(profile: McpProfile) -> &'static HashSet<&'static str> {
    static CYBERBRAIN: OnceLock<HashSet<&'static str>> = OnceLock::new();
    static FULL: OnceLock<HashSet<&'static str>> = OnceLock::new();
    match profile {
        McpProfile::Cyberbrain => CYBERBRAIN.get_or_init(|| {
            let mut keys = advertised_profile_keys(McpProfile::Cyberbrain);
            // The cyberbrain `wm` schema documents these legacy action selectors.
            keys.insert("sweep");
            keys.insert("inspect");
            keys
        }),
        McpProfile::Full => FULL.get_or_init(|| advertised_profile_keys(McpProfile::Full)),
    }
}

fn profile_allows_tool(profile: McpProfile, name: &str) -> bool {
    match canonical_route(name) {
        Some(key) => allowed_profile_keys(profile).contains(key),
        None => false,
    }
}

/// Arguments each mission-owned tool actually consumes.
///
/// Handlers validate against this table (unknown keys are refused), and the
/// contract test asserts the advertised schemas never declare anything outside
/// it: every declared property is either consumed or absent.
pub const TOOL_ARGUMENTS: &[(&str, &[&str])] = &[
    ("memory.pin", &["id", "galaxy", "pinned"]),
    ("memory.update", &["id", "content", "reason"]),
    ("memory.revisions", &["id", "action"]),
    (
        "memory.aggregate",
        &["field", "op", "query", "metric", "limit"],
    ),
    (
        "memory.ingest",
        &[
            "items",
            "items_jsonl",
            "text",
            "source",
            "dry_run",
            "limit",
            "galaxy",
            "redact",
        ],
    ),
    (
        "session.record",
        &[
            "content",
            "role",
            "turn_type",
            "importance",
            "session_id",
            "supersedes",
            "track",
            "agent_id",
            "log_type",
        ],
    ),
    (
        "session.continuity",
        &[
            "n",
            "session_id",
            "current_session_id",
            "since",
            "until",
            "max_content_bytes",
            "max_response_bytes",
            "include_briefing_text",
        ],
    ),
    (
        "session.checkpoint",
        &[
            "session_id",
            "summary",
            "next_queue",
            "open_flags",
            "track",
            "commit",
            "branch",
            "tests_green",
            "lease_id",
            "agent_id",
            "checkpoint_type",
            "context_token",
        ],
    ),
    ("session.list", &["session_id", "limit"]),
    (
        "session.replay",
        &[
            "session_id",
            "since",
            "until",
            "n",
            "include_superseded",
            "min_importance",
            "token_budget",
            "turn_types",
            "mode",
        ],
    ),
    ("session.recall", &["session_id", "query", "limit"]),
    ("receipts.emit", &["kind", "session_id", "out", "limit"]),
    ("session.digest", &["session_id", "n"]),
];

/// Consumed-argument list for a canonical tool route, if declared.
#[must_use]
pub fn consumed_arguments(tool: &str) -> Option<&'static [&'static str]> {
    TOOL_ARGUMENTS
        .iter()
        .find_map(|(name, args)| (*name == tool).then_some(*args))
}

/// Refuse any argument not in the tool's consumed-argument table.
fn reject_unknown_args(tool: &str, args: &Value) -> Result<(), String> {
    let Some(allowed) = consumed_arguments(tool) else {
        return Ok(());
    };
    if let Some(object) = args.as_object() {
        for key in object.keys() {
            if !allowed.contains(&key.as_str()) {
                return Err(format!("{tool} refuses unknown argument '{key}'"));
            }
        }
    }
    Ok(())
}

/// 10 Lean Cyberbrain MCP Tools.
pub fn get_cyberbrain_tools_list(readonly: bool) -> Value {
    let mode_hint = if readonly {
        " (READ-ONLY mode: mutations refused)"
    } else {
        ""
    };
    #[cfg_attr(not(feature = "systemone"), allow(unused_mut))]
    let mut tools = json!([
        {
            "name": "memory_recall",
            "description": format!("Recall memories matching a query from the sovereign Gen3 Substrate using BM25, anchor coherence, and forgotten diamond recovery.{mode_hint}"),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": { "type": "string", "description": "Search query terms or phrase" },
                    "limit": { "type": "integer", "description": "Maximum number of results to return (default: 10)" },
                    "historical": { "type": "boolean", "description": "Include superseded or historical records (default: false)" },
                    "scope": { "type": "string", "description": "Optional recall scope filter" }
                },
                "required": ["query"]
            }
        },
        {
            "name": "memory_remember",
            "description": format!("Record a new memory into the sovereign Gen3 Substrate via CommitCapability and sovereign pulse compilation.{mode_hint}"),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "content": { "type": "string", "description": "Content of the memory to record" },
                    "source": { "type": "string", "description": "Epistemic provenance attribution (default: 'agent:mcp')" },
                    "kind": { "type": "string", "description": "Epistemic kind: reported (default), system, or simulated", "enum": ["reported", "system", "simulated"] },
                    "uuid": { "type": "string", "description": "Optional explicit UUID to bind to the new record" }
                },
                "required": ["content"]
            }
        },
        {
            "name": "memory_get",
            "description": "Retrieve an exact evidence record from the Substrate by its numeric ID or UUID string.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "id": { "description": "The unique numerical record ID (u64) or UUID string" }
                },
                "required": ["id"]
            }
        },
        {
            "name": "memory_stats",
            "description": "Inspect Substrate statistics, current epoch, record count, and sovereign invariants.",
            "inputSchema": { "type": "object", "properties": {} }
        },
        {
            "name": "session_checkpoint",
            "description": format!("Record a compounding structured checkpoint for agent session continuity across turns and handoffs.{mode_hint}"),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "session_id": { "type": "string", "description": "Session identifier (e.g. conversation ID, lane name)" },
                    "summary": { "type": "string", "description": "High-density summary of decisions, state, and findings" },
                    "agent_id": { "type": "string", "description": "Active agent identifier (default: 'agent')" },
                    "checkpoint_type": { "type": "string", "description": "Checkpoint type: 'turn', 'handoff', 'milestone', 'compact'" },
                    "next_queue": { "type": "array", "items": { "type": "string" }, "description": "Queued action items for next turn / next agent" },
                    "open_flags": { "type": "array", "items": { "type": "string" }, "description": "Open flags, blockers, or warnings" },
                    "context_token": { "type": "string", "description": "Optional ContextCache token for prefix cache stabilization" }
                },
                "required": ["session_id", "summary"]
            }
        },
        {
            "name": "session_continuity",
            "description": "Retrieve the latest compounding session continuity state, summary, and action queue for an agent session.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "session_id": { "type": "string", "description": "Optional session identifier filter; if omitted, returns the latest checkpoint across all sessions" }
                }
            }
        },
        {
            "name": "session_record",
            "description": format!("Record an arbitrary log entry, note, or observation tied to a session.{mode_hint}"),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "session_id": { "type": "string", "description": "Session identifier" },
                    "content": { "type": "string", "description": "Log content text" },
                    "agent_id": { "type": "string", "description": "Agent identifier (default: 'agent')" },
                    "log_type": { "type": "string", "description": "Log type (e.g. 'note', 'tool_output', 'decision')" }
                },
                "required": ["session_id", "content"]
            }
        },
        {
            "name": "session_list",
            "description": "List all unique session identifiers recorded in the substrate.",
            "inputSchema": { "type": "object", "properties": {} }
        },
        {
            "name": "mesh_sync",
            "description": "Synchronize the local Substrate with a remote Mandala P2P mesh peer node over TCP.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "peer": { "type": "string", "description": "IP:port or host:port address of the remote peer (e.g. '127.0.0.1:7369')" },
                    "batch_size": { "type": "integer", "description": "Maximum records to sync per request (default: 100)" }
                },
                "required": ["peer"]
            }
        },
        {
            "name": "wm",
            "description": format!("WhiteMagic unified meta-tool — routes natural language (thought), explicit routes (route), or discrete actions over the sovereign Gen3 kernel.{mode_hint}"),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "thought": { "type": "string", "description": "Natural language request auto-routed via TF-IDF NLU" },
                    "route": { "type": "string", "description": "Explicit tool name or route for direct dispatch (e.g. 'memory.search', 'session.continuity')" },
                    "args": { "type": "object", "description": "Arguments to pass through to target tool" },
                    "action": { "type": "string", "description": "Legacy action selector: recall, remember, get, stats, sync, sweep, inspect, session_checkpoint, session_continuity, session_record, session_list, galaxy_list, galaxy_fork" }
                }
            }
        },
        {
            "name": "galaxy_list",
            "description": "List all active sovereign memory galaxies, their record counts, sample tags, and starter guide status.",
            "inputSchema": { "type": "object", "properties": {} }
        },
        {
            "name": "galaxy_fork",
            "description": format!("Fork an existing galaxy partition into a new sovereign galaxy branch (e.g. 'guide' -> 'project-alpha').{mode_hint}"),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "source": { "type": "string", "description": "Source galaxy name to fork from (e.g. 'guide')" },
                    "target": { "type": "string", "description": "Target galaxy name to establish (e.g. 'project-alpha')" }
                },
                "required": ["source", "target"]
            }
        }
    ]);
    #[cfg(feature = "systemone")]
    if let Value::Array(ref mut list) = tools {
        list.push(systemone_tool_schema(mode_hint));
    }
    tools
}

/// 37 Curated Full Suite MCP Tools (preserving 100% Gen2 tools.snapshot.json + Mandala + Gen3).
pub fn get_full_curated_tools_list(readonly: bool) -> Value {
    let mode_hint = if readonly {
        " (READ-ONLY: mutations refused)"
    } else {
        ""
    };
    #[cfg_attr(not(feature = "systemone"), allow(unused_mut))]
    let mut tools = json!([
        {
            "name": "wm",
            "title": "WhiteMagic Meta-Tool",
            "description": format!("WhiteMagic meta-tool — sovereign cognitive kernel and memory hierarchy.{mode_hint} Routes via thought=<natural language>, route=<tool id>, or discrete action."),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "thought": { "type": "string", "description": "Natural language query or command auto-routed via NLU" },
                    "route": { "type": "string", "description": "Target tool route (e.g. 'memory.create', 'memory.search', 'session.continuity')" },
                    "args": { "type": "object", "description": "Parameters for the routed tool" },
                    "action": { "type": "string", "description": "Alternative action name" }
                }
            }
        },
        {
            "name": "memory.create",
            "title": "Store Memory",
            "description": format!("Store a new memory in the holographic substrate with bijective UUID, 6D projection, and galaxy routing.{mode_hint}"),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "content": { "type": "string", "description": "Memory text content to record" },
                    "galaxy": { "type": "string", "description": "Target memory galaxy: codex, active, audit, sessions (default: codex)" },
                    "tags": { "type": "array", "items": { "type": "string" }, "description": "Optional categorization tags" },
                    "importance": { "type": "number", "description": "Subjective salience/importance score (0.0 to 1.0)" },
                    "topic": { "type": "string", "description": "Optional topic or domain label" },
                    "source": { "type": "string", "description": "Epistemic attribution (default: 'agent:mcp')" },
                    "title": { "type": "string", "description": "Optional human-readable title (envelope v2)" },
                    "event_time": { "type": "string", "description": "Optional event time: when the recorded event actually happened, as RFC 3339" }
                },
                "required": ["content"]
            }
        },
        {
            "name": "memory.search",
            "title": "Search Memories",
            "description": "Search memories: hybrid BM25 + vector fusion with deterministic sub-millisecond retrieval.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": { "type": "string", "description": "Search query or natural language question" },
                    "galaxy": { "type": "string", "description": "Galaxy to search in, or 'all' for cross-galaxy discovery" },
                    "limit": { "type": "integer", "description": "Maximum number of memories to return (default: 10)" },
                    "historical": { "type": "boolean", "description": "Include superseded or archived records (default: false)" },
                    "since": { "type": "string", "description": "Inclusive lower time bound: RFC3339 or epoch seconds" },
                    "until": { "type": "string", "description": "Inclusive upper time bound: RFC3339 or epoch seconds" },
                    "min_score": { "type": "number", "description": "Absolute BM25 score floor" },
                    "min_score_ratio": { "type": "number", "description": "Relative floor: reject hits below this fraction of the top score" },
                    "min_trust": { "type": "number", "description": "Minimum source_trust (0-1)" },
                    "min_importance": { "type": "number", "description": "Minimum memory importance (0-1)" },
                    "time_basis": { "type": "string", "description": "Time basis for since/until: 'recorded' or 'event'" },
                    "include_cold": { "type": "boolean", "description": "Opt-in unranked cold recovery" },
                    "cold_scan_limit": { "type": "integer", "description": "Maximum cold records to scan when include_cold is set (default 2048)" }
                },
                "required": ["query"]
            }
        },
        {
            "name": "memory.read",
            "title": "Read Memory",
            "description": "Retrieve a specific memory by its numeric record ID or UUID string.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "id": { "description": "Unique identifier of the memory (UUID or numeric record_id)" },
                    "galaxy": { "type": "string", "description": "Optional galaxy filter" }
                },
                "required": ["id"]
            }
        },
        {
            "name": "memory.list",
            "title": "List Memories",
            "description": "List memories with pagination (limit, offset) and galaxy filtering.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "galaxy": { "type": "string", "description": "Galaxy to list, or omit for all galaxies" },
                    "limit": { "type": "integer", "description": "Maximum number of memories to return (default: 20)" },
                    "offset": { "type": "integer", "description": "Pagination offset (default: 0)" },
                    "exclude_tags": { "type": "array", "items": { "type": "string" }, "description": "Drop memories carrying any of these tags" }
                }
            }
        },
        {
            "name": "memory.hybrid_recall",
            "title": "Hybrid Recall",
            "description": "Compatibility alias of memory.search with BM25 + dense vector fusion.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": { "type": "string", "description": "Search query terms" },
                    "limit": { "type": "integer", "description": "Maximum results (default: 10)" },
                    "galaxy": { "type": "string", "description": "Galaxy filter (default: all)" },
                    "since": { "type": "string", "description": "Inclusive lower time bound: RFC3339 or epoch seconds" },
                    "until": { "type": "string", "description": "Inclusive upper time bound: RFC3339 or epoch seconds" },
                    "min_score": { "type": "number", "description": "Absolute BM25 score floor" },
                    "min_score_ratio": { "type": "number", "description": "Relative floor: reject hits below this fraction of the top score" },
                    "min_trust": { "type": "number", "description": "Minimum source_trust (0-1)" },
                    "min_importance": { "type": "number", "description": "Minimum memory importance (0-1)" },
                    "time_basis": { "type": "string", "description": "Time basis for since/until: 'recorded' or 'event'" },
                    "include_cold": { "type": "boolean", "description": "Opt-in unranked cold recovery" },
                    "cold_scan_limit": { "type": "integer", "description": "Maximum cold records to scan when include_cold is set (default 2048)" }
                },
                "required": ["query"]
            }
        },
        {
            "name": "galaxy.list",
            "title": "List Galaxies",
            "description": "List all active sovereign memory galaxies, their record counts, sample tags, and starter guide status.",
            "inputSchema": {
                "type": "object",
                "properties": {}
            }
        },
        {
            "name": "galaxy.fork",
            "title": "Fork Galaxy",
            "description": format!("Fork an existing galaxy partition into a new sovereign galaxy branch (e.g. 'guide' -> 'project-alpha').{mode_hint}"),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "source": { "type": "string", "description": "Source galaxy name to fork from (e.g. 'guide')" },
                    "target": { "type": "string", "description": "Target galaxy name to establish (e.g. 'project-alpha')" }
                },
                "required": ["source", "target"]
            }
        },
        {
            "name": "galaxy.create",
            "title": "Create Galaxy",
            "description": format!("Establish a new sovereign galaxy namespace with an initial genesis beacon.{mode_hint}"),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "name": { "type": "string", "description": "Galaxy name (lowercase, no colons/spaces)" },
                    "description": { "type": "string", "description": "Optional description of the galaxy's purpose" }
                },
                "required": ["name"]
            }
        },
        {
            "name": "session.record",
            "title": "Record Session Turn",
            "description": format!("Record a session turn (decision, breakthrough, summary) for compounding continuity.{mode_hint}"),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "content": { "type": "string", "description": "Turn content to persist" },
                    "role": { "type": "string", "enum": ["user", "ai"], "description": "Who produced the turn" },
                    "turn_type": { "type": "string", "description": "Turn type (e.g. 'decision', 'milestone', 'observation')" },
                    "importance": { "type": "number", "description": "0.0 to 1.0 salience" },
                    "session_id": { "type": "string", "description": "Target session ID" },
                    "supersedes": { "type": "string", "description": "Memory id of an earlier turn this record replaces" },
                    "track": { "type": "string", "description": "Optional track slug" }
                },
                "required": ["content"]
            }
        },
        {
            "name": "session.continuity",
            "title": "Session Continuity",
            "description": "Recall where the previous session left off: recent turns, checkpoints, and open queues.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "n": { "type": "integer", "description": "Number of recent turns to recall (default: 5)" },
                    "session_id": { "type": "string", "description": "Target session (default: most recent)" },
                    "current_session_id": { "type": "string", "description": "Session to exclude (optional)" },
                    "since": { "type": "string", "description": "Time-range floor: epoch seconds, RFC 3339, or YYYY-MM-DD" },
                    "until": { "type": "string", "description": "Time-range ceiling: epoch seconds, RFC 3339, or YYYY-MM-DD" },
                    "max_content_bytes": { "type": "integer", "description": "Per-turn content cap in bytes (default 8192)" },
                    "max_response_bytes": { "type": "integer", "description": "Turns budget in bytes (default 49152)" },
                    "include_briefing_text": { "type": "boolean", "description": "Include the ready-to-inject briefing.text block" }
                }
            }
        },
        {
            "name": "session.start",
            "title": "Start Session",
            "description": "Start or resume an agent session for persistent continuity across tool invocations.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "title": { "type": "string", "description": "Session title" },
                    "user": { "type": "string", "description": "User identifier (default: 'default')" }
                }
            }
        },
        {
            "name": "memory.update",
            "title": "Update Memory",
            "description": format!("Update an existing memory by writing a superseding record and a durable revision entry (prior/new content hashes, timestamp, reason).{mode_hint}"),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "id": { "description": "Memory UUID or numeric record_id to update" },
                    "content": { "type": "string", "description": "New content for the superseding record" },
                    "reason": { "type": "string", "description": "Optional reason recorded in the revision entry" }
                },
                "required": ["id", "content"]
            }
        },
        {
            "name": "memory.revisions",
            "title": "Memory Revisions",
            "description": "List the durable revision chain of a memory, or verify it by recomputing content hashes and chain links.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "id": { "description": "Memory UUID or record_id to inspect" },
                    "action": { "type": "string", "enum": ["list", "verify"], "description": "Action: 'list' (default) or 'verify'" }
                },
                "required": ["id"]
            }
        },
        {
            "name": "session.checkpoint",
            "title": "Session Checkpoint",
            "description": format!("Save a structured checkpoint (summary, git state, next queue, open flags, track/lease metadata) for lossless handoffs.{mode_hint}"),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "session_id": { "type": "string", "description": "Target session ID" },
                    "summary": { "type": "string", "description": "High-density summary of decisions, state, and findings" },
                    "next_queue": { "type": "array", "items": { "type": "string" }, "description": "Ordered next steps" },
                    "open_flags": { "type": "array", "items": { "type": "string" }, "description": "Open flags, blockers, or warnings" },
                    "track": { "type": "string", "description": "Optional track slug persisted with the checkpoint" },
                    "commit": { "type": "string", "description": "Commit hash persisted with the checkpoint" },
                    "tests_green": { "type": "boolean", "description": "Whether the test suite was green at checkpoint time." },
                    "lease_id": { "type": "string", "description": "Claimed scope lease_id that remains held at this handoff" },
                    "branch": { "type": "string", "description": "Branch name persisted with the checkpoint" }
                }
            }
        },
        {
            "name": "memory.ingest",
            "title": "Ingest Memories",
            "description": format!("Ingest inline items (items / items_jsonl / text) or a JSONL/text file (source) via the batch-create path; returns real counts and refuses malformed input.{mode_hint}"),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "items": { "type": "array", "description": "Array of items: strings, or objects {content, source?, kind?, tags?, importance?}" },
                    "items_jsonl": { "type": "string", "description": "Newline-delimited JSONL items, or plain non-empty text lines" },
                    "text": { "type": "string", "description": "Single plain-text memory to ingest" },
                    "source": { "type": "string", "description": "Optional path to a JSONL or text file (same line rules as items_jsonl)" },
                    "dry_run": { "type": "boolean", "description": "Report without writing (default: true)" },
                    "limit": { "type": "integer", "description": "Maximum items to ingest" },
                    "galaxy": { "type": "string", "description": "Galaxy for items without an explicit source (default: codex)" },
                    "redact": { "type": "boolean", "default": true, "description": "Scrub credential-shaped tokens before storage (default true)." }
                }
            }
        },
        {
            "name": "receipts.emit",
            "title": "Emit Continuity Receipt",
            "description": "Emit a signed continuity receipt: kind 'session' signs a digest of the last `limit` session-log turns; kind 'state_transition' signs a store-state snapshot chained to the prior emitted receipt. 'task' receipts are not supported.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "kind": { "type": "string", "enum": ["session", "state_transition"], "description": "Receipt kind" },
                    "session_id": { "type": "string", "description": "Optional session filter for kind 'session'" },
                    "out": { "type": "string", "description": "Optional file path to additionally write the receipt JSON" },
                    "limit": { "type": "integer", "minimum": 1, "description": "Maximum turns covered (session kind; default 200)" }
                },
                "required": ["kind"]
            }
        },
        {
            "name": "receipts.verify",
            "title": "Verify WhiteMagic Profile Receipt",
            "description": "Verify one supported WhiteMagic receipt profile (including emitted session/state_transition continuity receipts) against the existing local gate key. This is not a general Continuity Receipt bundle verifier.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "bundle": { "type": "object", "description": "One supported signed WhiteMagic profile receipt object" }
                },
                "required": ["bundle"],
                "additionalProperties": false
            }
        },
        {
            "name": "memory.count",
            "title": "Count Memories",
            "description": "Count memories matching optional filters without returning full payload content.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "galaxy": { "type": "string", "description": "Galaxy to count, or 'all' (default)" }
                }
            }
        },
        {
            "name": "memory.stats",
            "title": "Memory Substrate Statistics",
            "description": "Substrate statistics: epoch, total records, relations, postings, and crash-consistency invariants.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "galaxy": { "type": "string", "description": "Galaxy to summarize (optional; default codex)" }
                }
            }
        },
        {
            "name": "memory.tags",
            "title": "Memory Tags Vocabulary",
            "description": "List the tag vocabulary with usage counts.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "limit": { "type": "integer", "description": "Maximum tags to return (default: 50)" },
                    "galaxy": { "type": "string", "description": "Galaxy whose tags to list (optional; default codex)" }
                }
            }
        },
        {
            "name": "memory.aggregate",
            "title": "Aggregate Memories",
            "description": "Aggregate over the matched record set: numeric fields (importance, created_at, epoch) support count/sum/avg/min/max; categorical fields (source, domain, class, status, galaxy) support count only. Unsupported field/op is refused.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "field": { "type": "string", "description": "Numeric: importance | created_at | epoch. Categorical (count only): source | domain | class | status | galaxy" },
                    "op": { "type": "string", "enum": ["count", "sum", "avg", "min", "max"], "description": "Aggregation operator" },
                    "query": { "type": "string", "description": "Full-text query selecting the memories to aggregate over" },
                    "metric": { "type": "string", "enum": ["count", "session_count", "session_span"], "description": "Alternative metric over matched records: count | session_count | session_span" },
                    "limit": { "type": "integer", "minimum": 1, "description": "Maximum candidates considered (default 50; must be >= 1)" }
                }
            }
        },
        {
            "name": "memory.associations",
            "title": "Associative Graph Neighbours",
            "description": "Traverse associative graph neighbours of a memory over spreading activation.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "id": { "description": "Source memory UUID or numeric record_id" },
                    "limit": { "type": "integer", "description": "Maximum neighbours to return (default: 10)" },
                    "direction": { "type": "string", "description": "Direction: from | to | both (default: both)" }
                },
                "required": ["id"]
            }
        },
        {
            "name": "memory.batch_read",
            "title": "Batch Read Memories",
            "description": "Read multiple memories by their UUID or numeric record IDs in a single call.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "ids": { "type": "array", "description": "List of memory IDs (UUIDs or integers) to read" },
                    "galaxy": { "type": "string", "description": "Galaxy (default: codex)" }
                },
                "required": ["ids"]
            }
        },
        {
            "name": "memory.query",
            "title": "Query Memories",
            "description": "Structured query over memories with filters, ordering, and field projections.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": { "type": "string", "description": "Text query string" },
                    "limit": { "type": "integer", "description": "Maximum results (default: 10)" },
                    "galaxy": { "type": "string", "description": "Galaxy to query (default codex)" },
                    "tags": { "type": "array", "items": { "type": "string" }, "description": "Filter: memories with all of these tags" },
                    "min_importance": { "type": "number", "description": "Filter: minimum importance (0-1)" },
                    "max_importance": { "type": "number", "description": "Filter: maximum importance (0-1)" },
                    "created_after": { "type": "string", "description": "Filter: only memories created at or after this RFC 3339 timestamp" },
                    "created_before": { "type": "string", "description": "Filter: only memories created at or before this RFC 3339 timestamp" }
                }
            }
        },
        {
            "name": "memory.filter",
            "title": "Filter Memories",
            "description": "Filter memories by metadata (tags, minimum importance, recency).",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "tags": { "type": "array", "items": { "type": "string" }, "description": "Required tags" },
                    "min_importance": { "type": "number", "description": "Minimum importance [0.0, 1.0]" },
                    "max_importance": { "type": "number", "description": "Filter: maximum importance (0-1)" },
                    "limit": { "type": "integer", "description": "Maximum results" },
                    "offset": { "type": "integer", "description": "Skip this many matching entries before returning (default 0)" },
                    "galaxy": { "type": "string", "description": "Galaxy to filter (default codex)" },
                    "query": { "type": "string", "description": "Filter: every whitespace-separated term must appear" },
                    "exclude_tags": { "type": "array", "items": { "type": "string" }, "description": "Filter: drop memories carrying any of these tags" },
                    "created_after": { "type": "string", "description": "Filter: only memories created at or after this RFC 3339 timestamp" },
                    "created_before": { "type": "string", "description": "Filter: only memories created at or before this RFC 3339 timestamp" }
                }
            }
        },
        {
            "name": "memory.pin",
            "title": "Pin Memory",
            "description": format!("Durably pin a critical memory against decay, sweep compaction, and forgetting, or release it with pinned=false.{mode_hint}"),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "id": { "description": "Memory UUID or numeric record ID to pin" },
                    "galaxy": { "type": "string", "description": "Optional galaxy this record must belong to (mismatch is refused)" },
                    "pinned": { "type": "boolean", "description": "true (default) = protect; false = release" }
                },
                "required": ["id"]
            }
        },
        {
            "name": "memory.search_batch",
            "title": "Batch Search Memories",
            "description": "Execute multiple memory search queries concurrently with sub-millisecond retrieval.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "queries": { "type": "array", "items": { "type": "string" }, "description": "Array of query strings" },
                    "limit": { "type": "integer", "description": "Maximum results per query (default: 5)" }
                },
                "required": ["queries"]
            }
        },
        {
            "name": "session.list",
            "title": "List Sessions",
            "description": "List session lanes with turn count, last timestamp, latest preview, start-marker flag, and checkpoint presence.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "session_id": { "type": "string", "description": "Filter to one session lane" },
                    "limit": { "type": "integer", "minimum": 1, "description": "Maximum lanes to return (default 50)" }
                }
            }
        },
        {
            "name": "session.recall",
            "title": "Recall Session Content",
            "description": "Recall specific interactions and turns within a targeted session (optional content query and limit).",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "session_id": { "type": "string", "description": "Session ID" },
                    "query": { "type": "string", "description": "Case-insensitive content substring filter" },
                    "limit": { "type": "integer", "description": "Maximum turns to return (default 50)" }
                }
            }
        },
        {
            "name": "session.replay",
            "title": "Replay Session",
            "description": "Replay the chronological trajectory of a session: 'full' returns all turns, 'selective' filters by min_importance/turn_types, and 'progressive' keeps the most recent turns within token_budget.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "session_id": { "type": "string", "description": "Session ID" },
                    "since": { "type": "string", "description": "Time-range floor: epoch seconds, RFC 3339, or YYYY-MM-DD" },
                    "until": { "type": "string", "description": "Time-range ceiling: epoch seconds, RFC 3339, or YYYY-MM-DD" },
                    "n": { "type": "integer", "minimum": 1, "description": "Maximum turns (default 50)" },
                    "include_superseded": { "type": "boolean", "description": "Also return turns replaced via supersedes (default false)." },
                    "min_importance": { "type": "number", "description": "Selective mode floor (default 0.7)" },
                    "token_budget": { "type": "integer", "description": "Progressive mode token budget (default 2000)" },
                    "turn_types": { "type": "array", "items": { "type": "string" }, "description": "Selective mode: turn types to keep" },
                    "mode": { "type": "string", "enum": ["full", "selective", "progressive"], "description": "Replay mode (default full)" }
                }
            }
        },
        {
            "name": "session.digest",
            "title": "Session Digest",
            "description": "Compose a read-only digest from typed session-log turns and the latest checkpoint (markdown text plus JSON).",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "session_id": { "type": "string", "description": "Target session (default: most recent lane)" },
                    "n": { "type": "integer", "minimum": 1, "description": "Maximum turns to include (default 20)" }
                }
            }
        },
        {
            "name": "mandala.status",
            "title": "Mandala Kekkai Sandbox Status",
            "description": "Status of the Mandala microsecond Landlock sandbox, ABI level, POSIX rlimit bounds, and capability ledger.",
            "inputSchema": { "type": "object", "properties": {} }
        },
        {
            "name": "mandala.triage",
            "title": "Mandala JEV Triage Gate",
            "description": "Non-autoregressive System 1 JEV/Layla triage gate (<30 ns) to classify tasks and predict marginal utility and confinement tier.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "inquiry": { "type": "string", "description": "Task or inquiry description to triage" },
                    "utility": { "type": "number", "description": "Expected marginal utility threshold (default: 0.8)" },
                    "risk": { "type": "number", "description": "Risk factor [0.0, 1.0]" },
                    "variance": { "type": "number", "description": "Epistemic variance [0.0, 1.0]" },
                    "cost": { "type": "number", "description": "Compute / token cost [0.0, 1.0]" }
                }
            }
        },
        {
            "name": "mandala.evaluate",
            "title": "Mandala Confinement Evaluation",
            "description": format!("Execute a candidate mutation in an ephemeral Landlock sandboxed Kekkai and notarize with Spec 0.5 receipt.{mode_hint}"),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "candidate_id": { "type": "string", "description": "Unique identifier for the mutation candidate" },
                    "mutation_kind": { "type": "string", "enum": ["vanguard", "heavy", "noop"], "description": "Mutation category" },
                    "command": { "type": "string", "description": "Optional command to execute within ephemeral sandbox" }
                },
                "required": ["candidate_id"]
            }
        },
        {
            "name": "mesh_sync",
            "title": "Mandala P2P Mesh Sync",
            "description": "Synchronize the Substrate with a remote peer node over the sovereign TCP protocol.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "peer": { "type": "string", "description": "Remote peer address (e.g. '127.0.0.1:7369')" },
                    "batch_size": { "type": "integer", "description": "Batch sync size (default: 100)" }
                },
                "required": ["peer"]
            }
        },
        {
            "name": "gnosis.status",
            "title": "Gnosis Self-Model Status",
            "description": "System epistemics, self-model calibration, and invariant health status.",
            "inputSchema": { "type": "object", "properties": {} }
        },
        {
            "name": "gnosis.explain",
            "title": "Gnosis Explain",
            "description": "Explain internal architectural invariants, memory schemas, or routing logic.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "concept": { "type": "string", "description": "Concept to explain" },
                    "tool_name": { "type": "string", "description": "Tool name to explain" },
                    "args_hash": { "type": "string", "description": "Hash of the arguments under evaluation" },
                    "is_write": { "type": "boolean", "description": "Claim: the invocation writes" },
                    "is_spawn": { "type": "boolean", "description": "Claim: the invocation spawns a process" },
                    "is_network": { "type": "boolean", "description": "Claim: the invocation uses the network" },
                    "has_purpose": { "type": "boolean", "description": "Claim: the invocation carries a purpose" }
                }
            }
        },
        {
            "name": "sangha.status",
            "title": "Sangha Whiteboard Status",
            "description": "Query live fleet status, unread mentions, and board post sequence from the local Sangha agora.",
            "inputSchema": { "type": "object", "properties": {} }
        },
        {
            "name": "sangha.inbox",
            "title": "Sangha Agent Inbox",
            "description": "Fetch unread mentions and dispatches targeted at an agent (default: 'antigravity').",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "agent": { "type": "string", "description": "Agent handle to query (e.g. 'antigravity', 'opencode', 'all')" }
                }
            }
        },
        {
            "name": "sangha.post",
            "title": "Sangha Dispatch Post",
            "description": "Broadcast a structured dispatch to other local agents via the Sangha Whiteboard.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "title": { "type": "string", "description": "Dispatch title" },
                    "body": { "type": "string", "description": "Dispatch markdown content" },
                    "target": { "type": "string", "description": "Target agent tag (e.g. '@all', '@opencode', '@mac')" },
                    "type": { "type": "string", "description": "Post type (e.g. 'note', 'claim', 'handoff', 'done')" },
                    "scope": { "type": "string", "description": "Optional task scope" }
                },
                "required": ["title", "body"]
            }
        }
    ]);
    #[cfg(feature = "systemone")]
    if let Value::Array(ref mut list) = tools {
        list.push(systemone_tool_schema(mode_hint));
    }
    #[cfg(feature = "system05")]
    if let Value::Array(ref mut list) = tools {
        list.push(system05_tool_schema(mode_hint));
    }
    if let Value::Array(ref mut list) = tools {
        list.push(deliberation_tool_schema(mode_hint));
    }
    #[cfg(any(feature = "systemone", feature = "system05"))]
    if let Value::Array(ref mut list) = tools {
        list.push(decision_outcome_tool_schema(mode_hint));
    }
    tools
}

/// Hybrid Dispatch Router — dispatches any Gen2 or Gen3 tool invocation
/// into the sovereign Substrate with bijective UUID <-> u64 identity handling.
#[cfg(feature = "systemone")]
const SYSTEMONE_TOOL_HINT: &str = ", systemone.decide";
#[cfg(not(feature = "systemone"))]
const SYSTEMONE_TOOL_HINT: &str = "";
#[cfg(feature = "system05")]
const SYSTEM05_TOOL_HINT: &str = ", decision.shortlist";
#[cfg(not(feature = "system05"))]
const SYSTEM05_TOOL_HINT: &str = "";
const SYSTEM15_TOOL_HINT: &str = ", decision.deliberate";

pub fn execute_hybrid_tool_call(
    name: &str,
    args: &Value,
    substrate: &mut Substrate,
    store_path: &Path,
    readonly: bool,
    profile: McpProfile,
) -> Result<Value, String> {
    // Dispatch-time profile enforcement: reject routes outside the active
    // profile's allowlist, including aliases reached through the `wm` meta-tool.
    if canonical_route(name).is_some() && !profile_allows_tool(profile, name) {
        return Err(format!(
            "tool '{name}' is not permitted by the active '{}' MCP profile",
            profile_label(profile)
        ));
    }

    match name {
        // ── Unified WhiteMagic Router ──────────────────────────────────────
        "wm" | "whitemagic" => handle_wm_router(args, substrate, store_path, readonly, profile),

        // ── Memory Operations ──────────────────────────────────────────────
        "memory.create" | "memory_create" | "memory_remember" | "remember" => {
            handle_memory_create(args, substrate, readonly)
        }
        "memory.search" | "memory_search" | "memory_recall" | "recall" | "memory.hybrid_recall" => {
            handle_memory_search(args, substrate)
        }
        "memory.read" | "memory_read" | "memory.get" | "memory_get" | "get" => {
            handle_memory_read(args, substrate)
        }
        "memory.list" | "memory_list" => handle_memory_list(args, substrate),
        "memory.count" => handle_memory_count(substrate),
        "memory.stats" | "memory_stats" | "stats" => {
            handle_memory_stats(substrate, store_path, readonly)
        }
        "memory.pin" => handle_memory_pin(args, substrate, readonly),
        "memory.search_batch" => handle_memory_search_batch(args, substrate),
        "memory.batch_read" => handle_memory_batch_read(args, substrate),
        "memory.update" => handle_memory_update(args, substrate, readonly),
        "memory.revisions" => handle_memory_revisions(args, substrate),
        "memory.associations" => handle_memory_associations(args, substrate),
        "memory.tags" => handle_memory_tags(substrate),
        "memory.aggregate" => handle_memory_aggregate(args, substrate),
        "memory.query" | "memory.filter" => handle_memory_query(args, substrate),
        "memory.ingest" => handle_memory_ingest(args, substrate, readonly),

        // ── Session Operations ─────────────────────────────────────────────
        "session.record" | "session_record" => {
            handle_session_record(args, substrate, store_path, readonly)
        }
        "session.continuity" | "session_continuity" => {
            handle_session_continuity(args, substrate, store_path)
        }
        "session.checkpoint" | "session_checkpoint" => {
            handle_session_checkpoint(args, substrate, readonly)
        }
        "session.start" => handle_session_start(args, store_path),
        "session.list" | "session_list" => handle_session_list(args, substrate, store_path),
        "session.recall" => handle_session_recall(args, store_path),
        "session.replay" => handle_session_replay(args, store_path),
        "session.digest" => handle_session_digest(args, substrate, store_path),

        // ── Receipts & Evidence ────────────────────────────────────────────
        "receipts.emit" => handle_receipts_emit(args, substrate, store_path, readonly),
        "receipts.verify" => handle_receipts_verify(args, store_path),

        // ── Mandala OS & Sandboxing ────────────────────────────────────────
        "mandala.status" => handle_mandala_status(store_path),
        "mandala.triage" => handle_mandala_triage(args),
        "mandala.evaluate" => handle_mandala_evaluate(args, store_path, readonly),

        // ── System One Organ (feature: systemone) ──────────────────────────
        #[cfg(feature = "systemone")]
        "systemone.decide" | "systemone_decide" => {
            handle_systemone_decide(args, store_path, readonly)
        }

        // ── System 0.5 Retrieval Organ (feature: system05) ─────────────────
        #[cfg(feature = "system05")]
        "decision.shortlist" | "system05.shortlist" | "system05_shortlist" => {
            handle_decision_shortlist(args, store_path, readonly)
        }

        // ── System 1.5 Deliberator Organ ──────────────────────────────────
        "decision.deliberate" | "system15.deliberate" | "deliberate" => {
            handle_decision_deliberate(args, store_path, readonly)
        }

        // ── Receipt Outcomes (verify + backfill) ───────────────────────────
        #[cfg(any(feature = "systemone", feature = "system05"))]
        "decision.outcome" | "receipts.outcome" => {
            crate::receipt_verify::record_outcome(args, store_path, readonly)
        }

        // ── Mesh & Infrastructure ──────────────────────────────────────────
        "mesh_sync" | "sync" => handle_mesh_sync(args, substrate, store_path, readonly),
        "sweep" => handle_sweep(substrate, readonly),
        "inspect" => handle_inspect(args, substrate),
        "gnosis.status" | "gnosis.explain" | "gnosis" => handle_gnosis(args, substrate),

        // ── Sangha Whiteboard Agora ────────────────────────────────────────
        "sangha.status" | "sangha_status" => handle_sangha_status(),
        "sangha.inbox" | "sangha_inbox" => handle_sangha_inbox(args),
        "sangha.post" | "sangha_post" | "sangha.chat" => handle_sangha_post(args, readonly),

        // ── Galaxy Operations ──────────────────────────────────────────────
        "galaxy.list" | "galaxy_list" => handle_galaxy_list(substrate),
        "galaxy.fork" | "galaxy_fork" | "galaxy.branch" | "galaxy_branch" => {
            handle_galaxy_fork(args, substrate, readonly)
        }
        "galaxy.create" | "galaxy_create" => handle_galaxy_create(args, substrate, readonly),

        unknown => Err(format!(
            "Unknown tool: '{unknown}'. Supported: memory.create, memory.search, memory.read, memory.list, galaxy.list, galaxy.fork, session.record, session.continuity, session.checkpoint, mandala.status, mandala.triage, mandala.evaluate, mesh_sync, sangha.status, sangha.inbox, sangha.post, wm{SYSTEMONE_TOOL_HINT}{SYSTEM05_TOOL_HINT}{SYSTEM15_TOOL_HINT}"
        )),
    }
}

/// Handle the `wm` meta-tool invocation with NLU thought routing, explicit route, or legacy action.
fn handle_wm_router(
    args: &Value,
    substrate: &mut Substrate,
    store_path: &Path,
    readonly: bool,
    profile: McpProfile,
) -> Result<Value, String> {
    // 1. Explicit Route Dispatch (e.g. route="memory.create", args={...})
    if let Some(route) = args.get("route").and_then(Value::as_str) {
        if !route.is_empty() {
            let pass_args = args.get("args").unwrap_or(args);
            return execute_hybrid_tool_call(
                route, pass_args, substrate, store_path, readonly, profile,
            );
        }
    }

    // 2. Natural Language Thought Routing (e.g. thought="remember to check server logs")
    if let Some(thought) = args.get("thought").and_then(Value::as_str) {
        let trimmed = thought.trim();
        if !trimmed.is_empty() {
            let (predicted_route, _score) = predict_route_from_thought(trimmed);
            let mut extracted_args = args.get("args").cloned().unwrap_or_else(|| json!({}));
            match predicted_route {
                "memory.create" => {
                    if extracted_args.get("content").is_none() {
                        extracted_args["content"] = json!(trimmed);
                    }
                }
                "memory.search" => {
                    if extracted_args.get("query").is_none() {
                        extracted_args["query"] = json!(trimmed);
                    }
                }
                "mandala.triage" => {
                    if extracted_args.get("inquiry").is_none() {
                        extracted_args["inquiry"] = json!(trimmed);
                    }
                }
                _ => {}
            }
            return execute_hybrid_tool_call(
                predicted_route,
                &extracted_args,
                substrate,
                store_path,
                readonly,
                profile,
            );
        }
    }

    // 3. Legacy Action Selector (Gen3 cyberbrain style: action="recall")
    if let Some(action) = args.get("action").and_then(Value::as_str) {
        if !action.is_empty() {
            return execute_hybrid_tool_call(
                action, args, substrate, store_path, readonly, profile,
            );
        }
    }

    // 4. Default Hello / Status Ping
    Ok(json!({
        "status": "success",
        "message": "WhiteMagic Gen3 Sovereign Hybrid Kernel online",
        "version": env!("CARGO_PKG_VERSION"),
        "kernel_contract": "Articles 1-9 Inviolate",
        "sandboxing": "Mandala Kekkaishi Landlock ABI V1-V5",
        "recall_latency": "< 0.40 ms P95"
    }))
}

// ── Memory Implementations ─────────────────────────────────────────────────

fn handle_memory_create(
    args: &Value,
    substrate: &mut Substrate,
    readonly: bool,
) -> Result<Value, String> {
    if readonly {
        return Err("read-only mode: memory creation refused by Article 1".to_string());
    }
    let content = args
        .get("content")
        .and_then(Value::as_str)
        .ok_or_else(|| "Missing required parameter 'content'".to_string())?
        .trim();
    if content.is_empty() {
        return Err("Parameter 'content' cannot be empty".to_string());
    }

    let source = args
        .get("source")
        .and_then(Value::as_str)
        .unwrap_or("agent:mcp");
    let kind_str = args
        .get("kind")
        .and_then(Value::as_str)
        .unwrap_or("reported");
    let kind = match kind_str {
        "system" => ImportKind::System,
        "simulated" => ImportKind::Simulated,
        _ => ImportKind::Reported,
    };
    let galaxy = args
        .get("galaxy")
        .and_then(Value::as_str)
        .unwrap_or("codex");
    let importance = args
        .get("importance")
        .and_then(Value::as_f64)
        .unwrap_or(0.5);
    let tags: Vec<String> = args
        .get("tags")
        .and_then(Value::as_array)
        .map(|arr| {
            arr.iter()
                .filter_map(Value::as_str)
                .map(String::from)
                .collect()
        })
        .unwrap_or_default();

    let effective_source = if source.starts_with("corpus:") {
        source.to_string()
    } else {
        let tag_suffix = if tags.is_empty() {
            source.replace(':', "_")
        } else {
            tags.join(",")
        };
        format!("corpus:{galaxy}:{tag_suffix}")
    };

    let item = RememberItem {
        content: content.to_string(),
        source: effective_source,
        kind,
    };

    let authority = RatifiedChannel::mint("wm-hybrid-bridge");
    substrate.set_intake_authority(authority);

    let results = substrate.remember_batch(&[item]);
    let rec_id = match results.into_iter().next() {
        Some(Ok(id)) => id,
        Some(Err(e)) => return Err(format!("Substrate memory ingestion error: {e}")),
        None => return Err("Ingestion produced no output".to_string()),
    };

    append_record_meta(
        substrate.store().path(),
        rec_id,
        &tags,
        args.get("importance").and_then(Value::as_f64),
    );

    let uuid = if let Some(uuid_str) = args.get("uuid").and_then(Value::as_str) {
        if let Ok(parsed) = Uuid::parse_str(uuid_str) {
            substrate.bind_uuid(parsed, rec_id);
            parsed
        } else {
            substrate.get_or_create_uuid(rec_id)
        }
    } else {
        substrate.get_or_create_uuid(rec_id)
    };

    let now_epoch = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(0);

    Ok(json!({
        "status": "success",
        "id": uuid.to_string(),
        "record_id": rec_id,
        "uuid": uuid.to_string(),
        "galaxy": galaxy,
        "importance": importance,
        "tags": tags,
        "created_at": now_epoch,
        "kernel_epoch": substrate.store().epoch().unwrap_or(0)
    }))
}

fn handle_memory_search(args: &Value, substrate: &mut Substrate) -> Result<Value, String> {
    let query = args
        .get("query")
        .and_then(Value::as_str)
        .ok_or_else(|| "Missing required parameter 'query'".to_string())?
        .trim();
    if query.is_empty() {
        return Err("Parameter 'query' cannot be empty".to_string());
    }

    let limit = args.get("limit").and_then(Value::as_u64).unwrap_or(10) as usize;
    let historical = args
        .get("historical")
        .and_then(Value::as_bool)
        .unwrap_or(false);
    let scope = args.get("scope").and_then(Value::as_str).map(String::from);

    let q = RecallQuery {
        query: query.to_string(),
        limit,
        candidate_limit: limit.max(100),
        include_historical: historical,
        min_score: 0.0,
        min_coverage: 0.0,
        scope,
    };

    let hits = substrate
        .recall(&q)
        .map_err(|e| format!("Recall failed: {e}"))?;

    let results: Vec<Value> = hits
        .iter()
        .map(|hit| {
            let uuid = substrate
                .lookup_uuid_by_id(hit.id)
                .unwrap_or_else(|| Uuid::new_v5(&Uuid::NAMESPACE_OID, &hit.id.to_be_bytes()));
            json!({
                "id": uuid.to_string(),
                "record_id": hit.id,
                "uuid": uuid.to_string(),
                "content": hit.content,
                "score": hit.score,
                "rank": hit.rank,
                "source": hit.source,
                "recall_mode": "substrate",
                "galaxy": crate::starter_galaxy::extract_galaxy_from_source(&hit.source),
                "superseded_by": hit.superseded_by
            })
        })
        .collect();

    Ok(json!({
        "status": "success",
        "query": query,
        "count": results.len(),
        "results": results
    }))
}

fn handle_memory_read(args: &Value, substrate: &Substrate) -> Result<Value, String> {
    let id_val = args
        .get("id")
        .ok_or_else(|| "Missing required parameter 'id'".to_string())?;

    let record_id = resolve_id_to_u64(id_val, substrate)
        .ok_or_else(|| format!("Record not found (unindexed id/uuid: {id_val})"))?;

    let record = substrate
        .store()
        .get_record(record_id)
        .map_err(|e| format!("Store read error: {e}"))?
        .ok_or_else(|| format!("Record {record_id} does not exist in store"))?;

    let uuid = substrate
        .lookup_uuid_by_id(record_id)
        .unwrap_or_else(|| Uuid::new_v5(&Uuid::NAMESPACE_OID, &record_id.to_be_bytes()));

    let galaxy = crate::starter_galaxy::extract_galaxy_from_source(record.source());

    Ok(json!({
        "status": "success",
        "record": {
            "id": uuid.to_string(),
            "record_id": record.id(),
            "uuid": uuid.to_string(),
            "content": record.content(),
            "source": record.source(),
            "domain": format!("{:?}", record.domain()),
            "class": format!("{:?}", record.class()),
            "status": format!("{:?}", record.status()),
            "created_at": record.created_at(),
            "confidence": record.confidence(),
            "galaxy": galaxy
        }
    }))
}

fn handle_memory_list(args: &Value, substrate: &Substrate) -> Result<Value, String> {
    let limit = args.get("limit").and_then(Value::as_u64).unwrap_or(20) as usize;
    let offset = args.get("offset").and_then(Value::as_u64).unwrap_or(0) as usize;

    let all_records = substrate
        .store()
        .iter_records()
        .map_err(|e| format!("Store list error: {e}"))?;
    let slice: Vec<Value> = all_records
        .into_iter()
        .skip(offset)
        .take(limit)
        .map(|rec| {
            let uuid = substrate
                .lookup_uuid_by_id(rec.id())
                .unwrap_or_else(|| Uuid::new_v5(&Uuid::NAMESPACE_OID, &rec.id().to_be_bytes()));
            let galaxy = crate::starter_galaxy::extract_galaxy_from_source(rec.source());
            json!({
                "id": uuid.to_string(),
                "record_id": rec.id(),
                "uuid": uuid.to_string(),
                "content": rec.content(),
                "source": rec.source(),
                "created_at": rec.created_at(),
                "galaxy": galaxy
            })
        })
        .collect();

    Ok(json!({
        "status": "success",
        "count": slice.len(),
        "offset": offset,
        "items": slice
    }))
}

fn handle_memory_count(substrate: &Substrate) -> Result<Value, String> {
    let count = substrate.store().record_count().unwrap_or(0);
    Ok(json!({
        "status": "success",
        "count": count,
        "galaxy": "all"
    }))
}

fn handle_memory_stats(
    substrate: &Substrate,
    store_path: &Path,
    readonly: bool,
) -> Result<Value, String> {
    let count = substrate.store().record_count().unwrap_or(0);
    let epoch = substrate.store().epoch().unwrap_or(0);
    let realm = substrate
        .store()
        .realm_id()
        .map(|r| r.iter().map(|b| format!("{b:02x}")).collect::<String>())
        .unwrap_or_default();

    Ok(json!({
        "status": "success",
        "store": store_path.display().to_string(),
        "readonly": readonly,
        "epoch": epoch,
        "record_count": count,
        "realm_id": realm,
        "journal_ok": substrate.journal_ok(),
        "violations": substrate.violations(),
        "articles": "Articles 1-9 Inviolate (Zero unmetered background threads)"
    }))
}

fn handle_galaxy_list(substrate: &Substrate) -> Result<Value, String> {
    let list = crate::starter_galaxy::list_galaxies(substrate)?;
    Ok(json!({
        "status": "success",
        "count": list.len(),
        "galaxies": list
    }))
}

fn handle_galaxy_fork(
    args: &Value,
    substrate: &mut Substrate,
    readonly: bool,
) -> Result<Value, String> {
    if readonly {
        return Err("read-only mode: galaxy fork refused by Article 1".to_string());
    }
    let source = args
        .get("source")
        .and_then(Value::as_str)
        .ok_or_else(|| "Missing required parameter 'source'".to_string())?;
    let target = args
        .get("target")
        .and_then(Value::as_str)
        .ok_or_else(|| "Missing required parameter 'target'".to_string())?;

    let forked_count = crate::starter_galaxy::fork_galaxy(substrate, source, target)?;
    Ok(json!({
        "status": "success",
        "source": source,
        "target": target,
        "records_forked": forked_count
    }))
}

fn handle_galaxy_create(
    args: &Value,
    substrate: &mut Substrate,
    readonly: bool,
) -> Result<Value, String> {
    if readonly {
        return Err("read-only mode: galaxy creation refused by Article 1".to_string());
    }
    let name = args
        .get("name")
        .and_then(Value::as_str)
        .ok_or_else(|| "Missing required parameter 'name'".to_string())?;
    let description = args.get("description").and_then(Value::as_str);

    let record_id = crate::starter_galaxy::create_galaxy(substrate, name, description)?;
    Ok(json!({
        "status": "success",
        "galaxy": name,
        "record_id": record_id
    }))
}

fn handle_memory_pin(
    args: &Value,
    substrate: &mut Substrate,
    readonly: bool,
) -> Result<Value, String> {
    reject_unknown_args("memory.pin", args)?;
    if readonly {
        return Err("read-only mode: memory.pin refused".to_string());
    }
    let id_val = args
        .get("id")
        .ok_or_else(|| "Missing required parameter 'id'".to_string())?;

    let record_id = resolve_id_to_u64(id_val, substrate)
        .ok_or_else(|| format!("Record not found: {id_val}"))?;

    if let Some(galaxy) = args.get("galaxy").and_then(Value::as_str) {
        let record = substrate
            .store()
            .get_record(record_id)
            .map_err(|e| format!("Store read error: {e}"))?
            .ok_or_else(|| format!("Record {record_id} does not exist in store"))?;
        let actual = crate::starter_galaxy::extract_galaxy_from_source(record.source());
        if actual != galaxy {
            return Err(format!(
                "record {record_id} belongs to galaxy '{actual}', not '{galaxy}'"
            ));
        }
    }

    let pinned = args.get("pinned").and_then(Value::as_bool).unwrap_or(true);
    substrate.set_pin(record_id, pinned)?;
    let actual_state = substrate.is_pinned(record_id);

    let uuid = substrate
        .lookup_uuid_by_id(record_id)
        .unwrap_or_else(|| Uuid::new_v5(&Uuid::NAMESPACE_OID, &record_id.to_be_bytes()));

    Ok(json!({
        "status": "success",
        "id": uuid.to_string(),
        "record_id": record_id,
        "pinned": actual_state,
        "message": if actual_state {
            "Memory pinned against sweep decay and forgetting"
        } else {
            "Memory released; normal decay and compaction apply"
        }
    }))
}

fn handle_memory_search_batch(args: &Value, substrate: &mut Substrate) -> Result<Value, String> {
    let queries = args
        .get("queries")
        .and_then(Value::as_array)
        .ok_or_else(|| "Missing required parameter 'queries' (array of strings)".to_string())?;

    let limit = args.get("limit").and_then(Value::as_u64).unwrap_or(5) as usize;

    let mut batch_results = Vec::new();
    for q_val in queries {
        let q_str = q_val.as_str().unwrap_or("");
        if q_str.is_empty() {
            continue;
        }
        let q = RecallQuery {
            query: q_str.to_string(),
            limit,
            candidate_limit: limit.max(50),
            include_historical: false,
            min_score: 0.0,
            min_coverage: 0.0,
            scope: None,
        };
        let hits = substrate.recall(&q).unwrap_or_default();
        let results: Vec<Value> = hits
            .into_iter()
            .map(|h| {
                let uuid = substrate
                    .lookup_uuid_by_id(h.id)
                    .unwrap_or_else(|| Uuid::new_v5(&Uuid::NAMESPACE_OID, &h.id.to_be_bytes()));
                json!({
                    "id": uuid.to_string(),
                    "record_id": h.id,
                    "uuid": uuid.to_string(),
                    "content": h.content,
                    "score": h.score
                })
            })
            .collect();

        batch_results.push(json!({
            "query": q_str,
            "results": results
        }));
    }

    Ok(json!({
        "status": "success",
        "batch": batch_results
    }))
}

fn handle_memory_batch_read(args: &Value, substrate: &Substrate) -> Result<Value, String> {
    let ids = args
        .get("ids")
        .and_then(Value::as_array)
        .ok_or_else(|| "Missing required parameter 'ids' (array)".to_string())?;

    let mut records = Vec::new();
    for id_val in ids {
        if let Some(rec_id) = resolve_id_to_u64(id_val, substrate) {
            if let Ok(Some(rec)) = substrate.store().get_record(rec_id) {
                let uuid = substrate
                    .lookup_uuid_by_id(rec_id)
                    .unwrap_or_else(|| Uuid::new_v5(&Uuid::NAMESPACE_OID, &rec_id.to_be_bytes()));
                records.push(json!({
                    "id": uuid.to_string(),
                    "record_id": rec_id,
                    "uuid": uuid.to_string(),
                    "content": rec.content(),
                    "source": rec.source(),
                    "created_at": rec.created_at()
                }));
            }
        }
    }

    Ok(json!({
        "status": "success",
        "found": records.len(),
        "total": ids.len(),
        "records": records
    }))
}

fn handle_memory_update(
    args: &Value,
    substrate: &mut Substrate,
    readonly: bool,
) -> Result<Value, String> {
    reject_unknown_args("memory.update", args)?;
    if readonly {
        return Err("read-only mode: memory.update refused".to_string());
    }
    let id_val = args
        .get("id")
        .ok_or_else(|| "Missing required parameter 'id'".to_string())?;
    let old_id = resolve_id_to_u64(id_val, substrate)
        .ok_or_else(|| format!("Record not found: {id_val}"))?;

    let content = args
        .get("content")
        .and_then(Value::as_str)
        .ok_or_else(|| "Missing required parameter 'content'".to_string())?;
    if content.trim().is_empty() {
        return Err("Parameter 'content' cannot be empty".to_string());
    }
    let reason = args
        .get("reason")
        .and_then(Value::as_str)
        .unwrap_or("memory.update");

    let prior_source = substrate
        .store()
        .get_record(old_id)
        .map_err(|e| format!("Store read error: {e}"))?
        .ok_or_else(|| format!("Record {old_id} does not exist in store"))?
        .source()
        .to_string();
    let source = if prior_source.starts_with("corpus:") {
        format!("{prior_source}:revision")
    } else {
        "agent:update".to_string()
    };

    let item = RememberItem {
        content: content.to_string(),
        source,
        kind: ImportKind::Reported,
    };

    substrate.set_intake_authority(RatifiedChannel::mint("wm-hybrid-update"));
    let results = substrate.remember_batch(&[item]);
    let new_id = match results.into_iter().next() {
        Some(Ok(id)) => id,
        Some(Err(e)) => return Err(format!("Update failed: {e}")),
        None => return Err("Update produced no output".to_string()),
    };

    let revision = substrate.record_revision(old_id, new_id, reason)?;
    let new_uuid = substrate.get_or_create_uuid(new_id);

    Ok(json!({
        "status": "success",
        "id": new_uuid.to_string(),
        "record_id": new_id,
        "uuid": new_uuid.to_string(),
        "superseded_record_id": old_id,
        "revision": revision,
        "message": "Memory updated; prior record superseded by a durable revision entry"
    }))
}

fn handle_memory_revisions(args: &Value, substrate: &Substrate) -> Result<Value, String> {
    reject_unknown_args("memory.revisions", args)?;
    let id_val = args
        .get("id")
        .ok_or_else(|| "Missing required parameter 'id'".to_string())?;
    let rec_id = resolve_id_to_u64(id_val, substrate)
        .ok_or_else(|| format!("Record not found: {id_val}"))?;

    let uuid = substrate
        .lookup_uuid_by_id(rec_id)
        .unwrap_or_else(|| Uuid::new_v5(&Uuid::NAMESPACE_OID, &rec_id.to_be_bytes()));

    match args.get("action").and_then(Value::as_str).unwrap_or("list") {
        "list" => {
            let revisions = substrate.revision_chain(rec_id);
            Ok(json!({
                "status": "success",
                "id": uuid.to_string(),
                "record_id": rec_id,
                "count": revisions.len(),
                "revisions": revisions
            }))
        }
        "verify" => {
            let report = substrate.verify_revision_chain(rec_id)?;
            Ok(json!({
                "status": "success",
                "id": uuid.to_string(),
                "record_id": rec_id,
                "verify": report
            }))
        }
        other => Err(format!(
            "memory.revisions refuses action '{other}': supported actions are 'list' and 'verify'"
        )),
    }
}

fn handle_memory_associations(args: &Value, substrate: &Substrate) -> Result<Value, String> {
    let id_val = args
        .get("id")
        .ok_or_else(|| "Missing required parameter 'id'".to_string())?;
    let rec_id = resolve_id_to_u64(id_val, substrate)
        .ok_or_else(|| format!("Record not found: {id_val}"))?;

    let limit = args.get("limit").and_then(Value::as_u64).unwrap_or(10) as usize;
    let all_rels = substrate.store().iter_relations().unwrap_or_default();

    let neighbours: Vec<Value> = all_rels
        .into_iter()
        .filter(|r| r.src() == rec_id || r.dst() == rec_id)
        .take(limit)
        .map(|r| {
            let other_id = if r.src() == rec_id { r.dst() } else { r.src() };
            let other_uuid = substrate
                .lookup_uuid_by_id(other_id)
                .unwrap_or_else(|| Uuid::new_v5(&Uuid::NAMESPACE_OID, &other_id.to_be_bytes()));
            json!({
                "record_id": other_id,
                "uuid": other_uuid.to_string(),
                "weight": r.weight(),
                "relation_kind": format!("{:?}", r.kind())
            })
        })
        .collect();

    Ok(json!({
        "status": "success",
        "record_id": rec_id,
        "count": neighbours.len(),
        "associations": neighbours
    }))
}

fn handle_memory_tags(substrate: &Substrate) -> Result<Value, String> {
    let mut tag_counts: HashMap<String, usize> = HashMap::new();
    let records = substrate.store().iter_records().unwrap_or_default();
    for rec in records.iter().take(500) {
        for word in rec.content().split_whitespace() {
            if word.starts_with('#') && word.len() > 1 {
                let tag = word
                    .trim_matches(|c: char| !c.is_alphanumeric())
                    .to_lowercase();
                if !tag.is_empty() {
                    *tag_counts.entry(tag).or_insert(0) += 1;
                }
            }
        }
    }

    let mut list: Vec<Value> = tag_counts
        .into_iter()
        .map(|(t, c)| json!({ "tag": t, "count": c }))
        .collect();
    list.sort_by(|a, b| b["count"].as_u64().cmp(&a["count"].as_u64()));

    Ok(json!({
        "status": "success",
        "tags": list
    }))
}

/// Read `<store>/record_meta.jsonl` (written by `wm ingest` and by
/// `memory.create` when tags/importance are supplied) into `record_id -> importance`.
fn read_record_importance(store_path: &Path) -> HashMap<u64, f64> {
    let mut importance = HashMap::new();
    let Ok(content) = std::fs::read_to_string(store_path.join("record_meta.jsonl")) else {
        return importance;
    };
    for line in content.lines() {
        if let Ok(value) = serde_json::from_str::<Value>(line.trim()) {
            if let (Some(id), Some(score)) = (
                value.get("record_id").and_then(Value::as_u64),
                value.get("importance").and_then(Value::as_f64),
            ) {
                importance.insert(id, score);
            }
        }
    }
    importance
}

fn handle_memory_aggregate(args: &Value, substrate: &mut Substrate) -> Result<Value, String> {
    reject_unknown_args("memory.aggregate", args)?;
    let op = args.get("op").and_then(Value::as_str);
    let field = args.get("field").and_then(Value::as_str);
    let metric = args.get("metric").and_then(Value::as_str);
    let query = args.get("query").and_then(Value::as_str);
    let limit = args
        .get("limit")
        .and_then(Value::as_u64)
        .unwrap_or(50)
        .max(1) as usize;

    if metric.is_some() && field.is_some() {
        return Err("memory.aggregate accepts either 'field' or 'metric', not both".to_string());
    }

    let query = query.map(str::trim).filter(|q| !q.is_empty() && *q != "*");
    let matched_ids: Vec<u64> = match query {
        Some(query) => substrate
            .recall(&RecallQuery {
                query: query.to_string(),
                limit,
                candidate_limit: limit.max(100),
                include_historical: true,
                min_score: 0.0,
                min_coverage: 0.0,
                scope: None,
            })
            .map_err(|e| format!("aggregate query failed: {e}"))?
            .into_iter()
            .map(|hit| hit.id)
            .collect(),
        None => substrate
            .store()
            .iter_records()
            .map_err(|e| format!("aggregate scan failed: {e}"))?
            .into_iter()
            .take(limit)
            .map(|record| record.id())
            .collect(),
    };

    if let Some(metric) = metric {
        let session_ids: HashSet<String> = matched_ids
            .iter()
            .filter_map(|id| {
                substrate
                    .store()
                    .get_record(*id)
                    .ok()
                    .flatten()
                    .map(|record| record.source().to_string())
            })
            .filter(|source| source.starts_with("session:"))
            .filter_map(|source| {
                source
                    .split(':')
                    .nth(1)
                    .filter(|id| !id.is_empty())
                    .map(str::to_string)
            })
            .collect();
        let aggregate = match metric {
            "count" => json!(matched_ids.len()),
            "session_count" => json!(session_ids.len()),
            "session_span" => {
                let mut span: Vec<u64> = matched_ids
                    .iter()
                    .filter_map(|id| substrate.store().get_record(*id).ok().flatten())
                    .filter(|record| record.source().starts_with("session:"))
                    .map(|record| record.created_at())
                    .collect();
                span.sort_unstable();
                match (span.first(), span.last()) {
                    (Some(first), Some(last)) => json!(last.saturating_sub(*first)),
                    _ => json!(0),
                }
            }
            other => {
                return Err(format!(
                    "memory.aggregate refuses metric '{other}': supported metrics are 'count', 'session_count', 'session_span'"
                ));
            }
        };
        return Ok(json!({
            "status": "success",
            "op": "count",
            "metric": metric,
            "aggregate": aggregate,
            "sample_size": matched_ids.len()
        }));
    }

    let Some(field) = field else {
        let op = op.unwrap_or("count");
        if op != "count" {
            return Err(format!(
                "memory.aggregate requires 'field' for op '{op}'; only op 'count' works without a field"
            ));
        }
        return Ok(json!({
            "status": "success",
            "op": "count",
            "aggregate": matched_ids.len(),
            "sample_size": matched_ids.len()
        }));
    };
    let op = op.unwrap_or("count");
    if !matches!(op, "count" | "sum" | "avg" | "min" | "max") {
        return Err(format!(
            "memory.aggregate refuses op '{op}': supported ops are count, sum, avg, min, max"
        ));
    }

    if matches!(field, "source" | "domain" | "class" | "status" | "galaxy") {
        if op != "count" {
            return Err(format!(
                "field '{field}' is categorical; only op 'count' is supported"
            ));
        }
        return Ok(json!({
            "status": "success",
            "op": "count",
            "field": field,
            "aggregate": matched_ids.len(),
            "sample_size": matched_ids.len()
        }));
    }

    let mut values: Vec<f64> = Vec::new();
    match field {
        "created_at" | "epoch" => {
            for id in &matched_ids {
                if let Ok(Some(record)) = substrate.store().get_record(*id) {
                    values.push(record.created_at() as f64);
                }
            }
        }
        "importance" => {
            let importance = read_record_importance(substrate.store().path());
            for id in &matched_ids {
                if let Some(score) = importance.get(id) {
                    values.push(*score);
                }
            }
        }
        other => {
            return Err(format!(
                "memory.aggregate refuses field '{other}': numeric fields are 'importance', 'created_at', 'epoch'; categorical fields are 'source', 'domain', 'class', 'status', 'galaxy'"
            ));
        }
    }

    let aggregate = match (op, values.is_empty()) {
        ("count", _) => json!(values.len()),
        (_, true) => Value::Null,
        ("sum", false) => json!(values.iter().sum::<f64>()),
        ("avg", false) => json!(values.iter().sum::<f64>() / values.len() as f64),
        ("min", false) => json!(values.iter().copied().fold(f64::INFINITY, f64::min)),
        ("max", false) => json!(values.iter().copied().fold(f64::NEG_INFINITY, f64::max)),
        _ => Value::Null,
    };

    Ok(json!({
        "status": "success",
        "op": op,
        "field": field,
        "aggregate": aggregate,
        "sample_size": values.len()
    }))
}

fn handle_memory_query(args: &Value, substrate: &mut Substrate) -> Result<Value, String> {
    let query = args.get("query").and_then(Value::as_str).unwrap_or("*");
    let limit = args.get("limit").and_then(Value::as_u64).unwrap_or(10) as usize;

    let q = RecallQuery {
        query: query.to_string(),
        limit,
        candidate_limit: limit.max(50),
        include_historical: false,
        min_score: 0.0,
        min_coverage: 0.0,
        scope: None,
    };

    let hits = substrate.recall(&q).unwrap_or_default();
    let results: Vec<Value> = hits
        .into_iter()
        .map(|h| {
            let uuid = substrate
                .lookup_uuid_by_id(h.id)
                .unwrap_or_else(|| Uuid::new_v5(&Uuid::NAMESPACE_OID, &h.id.to_be_bytes()));
            json!({
                "id": uuid.to_string(),
                "record_id": h.id,
                "uuid": uuid.to_string(),
                "content": h.content,
                "score": h.score
            })
        })
        .collect();

    Ok(json!({
        "status": "success",
        "count": results.len(),
        "results": results
    }))
}

/// Append one `record_meta.jsonl` entry (tags/importance) for an ingested record.
fn append_record_meta(store_path: &Path, record_id: u64, tags: &[String], importance: Option<f64>) {
    if tags.is_empty() && importance.is_none() {
        return;
    }
    let ingested_at_ms = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_millis() as u64)
        .unwrap_or(0);
    let entry = json!({
        "record_id": record_id,
        "tags": tags,
        "importance": importance.unwrap_or(0.0),
        "ingested_at_ms": ingested_at_ms,
    });
    if let Ok(mut file) = std::fs::OpenOptions::new()
        .create(true)
        .append(true)
        .open(store_path.join("record_meta.jsonl"))
    {
        let _ = writeln!(file, "{entry}");
    }
}

/// Scrub credential-shaped tokens from ingest content. Returns the cleaned
/// text and the number of tokens redacted.
fn scrub_credentials(text: &str) -> (String, usize) {
    let mut redacted = 0usize;
    let cleaned: Vec<String> = text
        .split_whitespace()
        .map(|token| {
            let shaped = [
                "sk-",
                "sk_",
                "ghp_",
                "gho_",
                "github_pat_",
                "xoxb-",
                "xoxp-",
                "AKIA",
                "AIza",
            ]
            .iter()
            .any(|prefix| token.starts_with(prefix));
            if shaped {
                redacted += 1;
                "[REDACTED]".to_string()
            } else {
                token.to_string()
            }
        })
        .collect();
    (cleaned.join(" "), redacted)
}

fn ingest_kind(value: Option<&Value>) -> ImportKind {
    match value.and_then(Value::as_str).map(str::to_ascii_lowercase) {
        Some(kind) if kind == "system" => ImportKind::System,
        Some(kind) if kind == "simulated" => ImportKind::Simulated,
        _ => ImportKind::Reported,
    }
}

/// Parse one inline ingest item into a remember item plus optional metadata.
#[allow(clippy::type_complexity)]
fn parse_ingest_item(
    value: &Value,
    default_source: &str,
) -> Result<(RememberItem, Option<(Vec<String>, Option<f64>)>), String> {
    match value {
        Value::String(text) => {
            let content = text.trim();
            if content.is_empty() {
                return Err("ingest item content cannot be empty".to_string());
            }
            Ok((
                RememberItem {
                    content: content.to_string(),
                    source: default_source.to_string(),
                    kind: ImportKind::Reported,
                },
                None,
            ))
        }
        Value::Object(object) => {
            let content = object
                .get("content")
                .and_then(Value::as_str)
                .ok_or_else(|| "ingest item object requires string 'content'".to_string())?;
            if content.trim().is_empty() {
                return Err("ingest item content cannot be empty".to_string());
            }
            let source = object
                .get("source")
                .and_then(Value::as_str)
                .unwrap_or(default_source)
                .to_string();
            let kind = ingest_kind(object.get("kind"));
            let tags: Vec<String> = object
                .get("tags")
                .and_then(Value::as_array)
                .map(|array| {
                    array
                        .iter()
                        .filter_map(Value::as_str)
                        .map(str::to_string)
                        .collect()
                })
                .unwrap_or_default();
            let importance = object.get("importance").and_then(Value::as_f64);
            let meta = if tags.is_empty() && importance.is_none() {
                None
            } else {
                Some((tags, importance))
            };
            Ok((
                RememberItem {
                    content: content.to_string(),
                    source,
                    kind,
                },
                meta,
            ))
        }
        _ => Err("ingest items must be strings or objects with 'content'".to_string()),
    }
}

/// Parse JSONL text: each line is a JSON item object or a plain text line.
#[allow(clippy::type_complexity)]
fn parse_ingest_jsonl(
    raw: &str,
    default_source: &str,
) -> Result<Vec<(RememberItem, Option<(Vec<String>, Option<f64>)>)>, String> {
    let mut items = Vec::new();
    for (index, line) in raw.lines().enumerate() {
        let trimmed = line.trim();
        if trimmed.is_empty() {
            continue;
        }
        let line_no = index + 1;
        if trimmed.starts_with('{') {
            let value: Value = serde_json::from_str(trimmed)
                .map_err(|e| format!("items_jsonl line {line_no}: malformed JSON: {e}"))?;
            items.push(
                parse_ingest_item(&value, default_source)
                    .map_err(|e| format!("items_jsonl line {line_no}: {e}"))?,
            );
        } else if trimmed.starts_with('[') {
            return Err(format!(
                "items_jsonl line {line_no}: arrays are not accepted; one item per line"
            ));
        } else {
            items.push((
                RememberItem {
                    content: trimmed.to_string(),
                    source: default_source.to_string(),
                    kind: ImportKind::Reported,
                },
                None,
            ));
        }
    }
    Ok(items)
}

fn handle_memory_ingest(
    args: &Value,
    substrate: &mut Substrate,
    readonly: bool,
) -> Result<Value, String> {
    reject_unknown_args("memory.ingest", args)?;
    if readonly {
        return Err("read-only mode: memory.ingest refused".to_string());
    }
    let galaxy = args
        .get("galaxy")
        .and_then(Value::as_str)
        .unwrap_or("codex");
    let default_source = format!("corpus:{galaxy}:ingest");
    let dry_run = args.get("dry_run").and_then(Value::as_bool).unwrap_or(true);
    let redact = args.get("redact").and_then(Value::as_bool).unwrap_or(true);
    let limit = args
        .get("limit")
        .and_then(Value::as_u64)
        .map(|value| value as usize);

    let mut candidates: Vec<(RememberItem, Option<(Vec<String>, Option<f64>)>)> = Vec::new();

    if let Some(items) = args.get("items") {
        let array = items
            .as_array()
            .ok_or_else(|| "'items' must be an array".to_string())?;
        for (index, item) in array.iter().enumerate() {
            candidates.push(
                parse_ingest_item(item, &default_source)
                    .map_err(|e| format!("items[{index}]: {e}"))?,
            );
        }
    }
    if let Some(jsonl) = args.get("items_jsonl").and_then(Value::as_str) {
        candidates.extend(parse_ingest_jsonl(jsonl, &default_source)?);
    }
    if let Some(text) = args.get("text").and_then(Value::as_str) {
        if !text.trim().is_empty() {
            candidates.push((
                RememberItem {
                    content: text.to_string(),
                    source: default_source.clone(),
                    kind: ImportKind::Reported,
                },
                None,
            ));
        }
    }
    if let Some(source) = args.get("source").and_then(Value::as_str) {
        let path = Path::new(source);
        if !path.is_file() {
            return Err(format!(
                "memory.ingest source '{source}' is not a readable file (directory harvest is not supported; use `wm ingest`)"
            ));
        }
        let content = std::fs::read_to_string(path)
            .map_err(|e| format!("memory.ingest source read failed: {e}"))?;
        candidates.extend(parse_ingest_jsonl(&content, &default_source)?);
    }

    if candidates.is_empty() {
        return Err(
            "memory.ingest requires one of 'items', 'items_jsonl', 'text', or 'source'".to_string(),
        );
    }
    if let Some(limit) = limit {
        candidates.truncate(limit);
    }

    let mut redacted_tokens = 0usize;
    if redact {
        for (item, _) in &mut candidates {
            let (cleaned, count) = scrub_credentials(&item.content);
            item.content = cleaned;
            redacted_tokens += count;
        }
    }

    let considered = candidates.len();
    if dry_run {
        return Ok(json!({
            "status": "success",
            "dry_run": true,
            "would_ingest": considered,
            "records_ingested": 0,
            "duplicates": 0,
            "refused": 0,
            "redacted_tokens": redacted_tokens,
            "galaxy": galaxy,
            "epoch": substrate.store().epoch().unwrap_or(0),
            "message": "dry run: no records written"
        }));
    }

    substrate.set_intake_authority(RatifiedChannel::mint("wm-mcp-ingest"));
    let items: Vec<RememberItem> = candidates.iter().map(|(item, _)| item.clone()).collect();
    let results = substrate.remember_batch(&items);
    let mut records_ingested = 0usize;
    let mut duplicates = 0usize;
    let mut refused = 0usize;
    for (index, result) in results.into_iter().enumerate() {
        match result {
            Ok(id) => {
                records_ingested += 1;
                if let Some((tags, importance)) = &candidates[index].1 {
                    append_record_meta(substrate.store().path(), id, tags, *importance);
                }
            }
            Err(error) if error.contains("duplicate") => duplicates += 1,
            Err(_) => refused += 1,
        }
    }

    Ok(json!({
        "status": "success",
        "dry_run": false,
        "records_ingested": records_ingested,
        "duplicates": duplicates,
        "refused": refused,
        "redacted_tokens": redacted_tokens,
        "galaxy": galaxy,
        "epoch": substrate.store().epoch().unwrap_or(0)
    }))
}

// ── Session Implementations ────────────────────────────────────────────────

fn now_epoch_secs() -> u64 {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(0)
}

/// Read and derive the typed session log. Supersession is recomputed from
/// `supersedes` links, never trusted from a stored `superseded_by`.
fn read_session_turns(store_path: &Path) -> Vec<SessionTurn> {
    let mut turns: Vec<SessionTurn> = Vec::new();
    if let Ok(content) = std::fs::read_to_string(store_path.join("session_log.jsonl")) {
        for line in content.lines() {
            let trimmed = line.trim();
            if trimmed.is_empty() {
                continue;
            }
            if let Ok(mut turn) = serde_json::from_str::<SessionTurn>(trimmed) {
                turn.superseded_by = None;
                turns.push(turn);
            }
        }
    }
    let links: Vec<(String, String)> = turns
        .iter()
        .filter_map(|turn| {
            turn.supersedes
                .as_ref()
                .map(|prior| (prior.clone(), turn.turn_id.clone()))
        })
        .collect();
    for (prior, new) in links {
        for turn in turns.iter_mut() {
            if turn.turn_id == prior {
                turn.superseded_by = Some(new.clone());
            }
        }
    }
    turns
}

/// Parse an epoch-seconds, RFC 3339, or `YYYY-MM-DD` time bound.
fn parse_time_bound(raw: &str) -> Result<u64, String> {
    let text = raw.trim();
    if text.is_empty() {
        return Err("time bound cannot be empty".to_string());
    }
    if text.chars().all(|c| c.is_ascii_digit()) {
        return text
            .parse::<u64>()
            .map_err(|e| format!("invalid epoch seconds '{text}': {e}"));
    }
    if let Ok(timestamp) = DateTime::parse_from_rfc3339(text) {
        return Ok(timestamp.timestamp().max(0) as u64);
    }
    if let Ok(date) = NaiveDate::parse_from_str(text, "%Y-%m-%d") {
        if let Some(datetime) = date.and_hms_opt(0, 0, 0) {
            return Ok(datetime.and_utc().timestamp().max(0) as u64);
        }
    }
    Err(format!(
        "unsupported time bound '{text}' (use epoch seconds, RFC 3339, or YYYY-MM-DD)"
    ))
}

fn truncate_utf8(text: &str, max_bytes: usize) -> String {
    if text.len() <= max_bytes {
        return text.to_string();
    }
    let mut end = max_bytes;
    while end > 0 && !text.is_char_boundary(end) {
        end -= 1;
    }
    text[..end].to_string()
}

fn preview(text: &str, max: usize) -> String {
    let trimmed = text.trim();
    if trimmed.chars().count() <= max {
        trimmed.to_string()
    } else {
        let cut: String = trimmed.chars().take(max).collect();
        format!("{cut}…")
    }
}

fn compose_briefing(
    session: &str,
    checkpoint: Option<&SessionContinuityView>,
    turns: &[SessionTurn],
) -> String {
    let mut out = String::new();
    out.push_str(&format!("Session {session}\n"));
    match checkpoint {
        Some(cp) => {
            out.push_str(&format!(
                "Checkpoint [{}]: {}\n",
                cp.checkpoint_type, cp.summary
            ));
            if let Some(commit) = &cp.commit {
                out.push_str(&format!("Commit: {commit}\n"));
            }
            if let Some(branch) = &cp.branch {
                out.push_str(&format!("Branch: {branch}\n"));
            }
            if let Some(true) = cp.tests_green {
                out.push_str("Tests: green\n");
            }
            if !cp.next_queue.is_empty() {
                out.push_str("Next queue:\n");
                for item in &cp.next_queue {
                    out.push_str(&format!("- [ ] {item}\n"));
                }
            }
            if !cp.open_flags.is_empty() {
                out.push_str("Open flags:\n");
                for flag in &cp.open_flags {
                    out.push_str(&format!("- {flag}\n"));
                }
            }
        }
        None => out.push_str("No checkpoint recorded.\n"),
    }
    if let Some(last) = turns.last() {
        out.push_str(&format!(
            "Latest turn ({}): {}\n",
            last.turn_type,
            preview(&last.content, 160)
        ));
    }
    out
}

fn handle_session_record(
    args: &Value,
    substrate: &mut Substrate,
    store_path: &Path,
    readonly: bool,
) -> Result<Value, String> {
    reject_unknown_args("session.record", args)?;
    if readonly {
        return Err("read-only mode: session writes refused".to_string());
    }
    let content = args
        .get("content")
        .and_then(Value::as_str)
        .ok_or_else(|| "Missing required parameter 'content'".to_string())?;
    let session_id = args
        .get("session_id")
        .and_then(Value::as_str)
        .map(str::to_string)
        .or_else(|| last_session_lane(store_path))
        .unwrap_or_else(|| "default".to_string());
    let role = args.get("role").and_then(Value::as_str).unwrap_or("user");
    let agent_id = args.get("agent_id").and_then(Value::as_str);
    let log_type = args.get("log_type").and_then(Value::as_str);
    let turn_type = args
        .get("turn_type")
        .and_then(Value::as_str)
        .or(log_type)
        .unwrap_or("message");
    let importance = args
        .get("importance")
        .and_then(Value::as_f64)
        .unwrap_or(0.5);
    let track = args.get("track").and_then(Value::as_str);
    let supersedes = args.get("supersedes").and_then(Value::as_str);

    if let Some(prior_turn) = supersedes {
        let exists = read_session_turns(store_path)
            .iter()
            .any(|turn| turn.turn_id == prior_turn && turn.session_id == session_id);
        if !exists {
            return Err(format!(
                "session.record cannot supersede turn '{prior_turn}': no such turn id in lane '{session_id}'"
            ));
        }
    }

    let session_log = store_path.join("session_log.jsonl");
    let turn_id = Uuid::new_v4().to_string();
    let now = now_epoch_secs();

    let mut entry = json!({
        "turn_id": turn_id,
        "session_id": session_id,
        "role": role,
        "turn_type": turn_type,
        "content": content,
        "importance": importance,
        "timestamp": now
    });
    if let Some(track) = track {
        entry["track"] = json!(track);
    }
    if let Some(agent_id) = agent_id {
        entry["agent_id"] = json!(agent_id);
    }
    if let Some(supersedes) = supersedes {
        entry["supersedes"] = json!(supersedes);
    }

    if let Ok(mut file) = std::fs::OpenOptions::new()
        .create(true)
        .append(true)
        .open(&session_log)
    {
        let _ = writeln!(file, "{entry}");
    }

    // Ingest into substrate as an evidence record
    let source = match (agent_id, log_type) {
        (Some(agent), Some(log_type)) => format!("session:{session_id}:{agent}:{log_type}"),
        (Some(agent), None) => format!("session:{session_id}:{agent}"),
        _ => format!("session:{session_id}"),
    };
    let item = RememberItem {
        content: format!("[session:{session_id}] {role}: {content}"),
        source,
        kind: ImportKind::Reported,
    };
    substrate.set_intake_authority(RatifiedChannel::mint("wm-session-turn"));
    let _ = substrate.remember_batch(&[item]);

    Ok(json!({
        "status": "success",
        "turn_id": turn_id,
        "session_id": session_id,
        "track": track,
        "supersedes": supersedes,
        "recorded_at": now
    }))
}

fn handle_session_continuity(
    args: &Value,
    substrate: &Substrate,
    store_path: &Path,
) -> Result<Value, String> {
    reject_unknown_args("session.continuity", args)?;
    let explicit_session = args.get("session_id").and_then(Value::as_str);
    let current_session = args.get("current_session_id").and_then(Value::as_str);
    let n = args.get("n").and_then(Value::as_u64).unwrap_or(5) as usize;
    let since = args
        .get("since")
        .and_then(Value::as_str)
        .map(parse_time_bound)
        .transpose()?;
    let until = args
        .get("until")
        .and_then(Value::as_str)
        .map(parse_time_bound)
        .transpose()?;
    if let (Some(since), Some(until)) = (since, until) {
        if since > until {
            return Err("session.continuity: 'since' is after 'until'".to_string());
        }
    }
    let max_content_bytes = args
        .get("max_content_bytes")
        .and_then(Value::as_u64)
        .unwrap_or(8192) as usize;
    let max_response_bytes = args
        .get("max_response_bytes")
        .and_then(Value::as_u64)
        .unwrap_or(49152) as usize;
    let include_briefing = args
        .get("include_briefing_text")
        .and_then(Value::as_bool)
        .unwrap_or(false);

    let all_turns = read_session_turns(store_path);
    let effective_session = explicit_session.map(str::to_string).or_else(|| {
        all_turns
            .iter()
            .rev()
            .map(|turn| turn.session_id.as_str())
            .find(|lane| !lane.is_empty() && Some(*lane) != current_session)
            .map(str::to_string)
    });

    let mut turns: Vec<SessionTurn> = all_turns
        .into_iter()
        .filter(|turn| match &effective_session {
            Some(lane) => turn.session_id == *lane,
            None => true,
        })
        .filter(|turn| !turn.is_start_marker())
        .filter(|turn| since.is_none_or(|floor| turn.timestamp >= floor))
        .filter(|turn| until.is_none_or(|ceiling| turn.timestamp <= ceiling))
        .filter(|turn| turn.superseded_by.is_none())
        .collect();

    let mut content_truncated = 0usize;
    if max_content_bytes > 0 {
        for turn in &mut turns {
            if turn.content.len() > max_content_bytes {
                turn.content = truncate_utf8(&turn.content, max_content_bytes);
                content_truncated += 1;
            }
        }
    }

    let total_turns = turns.len();
    if turns.len() > n {
        turns.drain(..turns.len() - n);
    }

    let mut recent: Vec<SessionTurn> = Vec::new();
    let mut response_bytes = 0usize;
    for turn in turns.iter().rev() {
        let size = serde_json::to_string(turn).map(|s| s.len()).unwrap_or(0) + 1;
        if !recent.is_empty() && response_bytes + size > max_response_bytes {
            break;
        }
        response_bytes += size;
        recent.push(turn.clone());
    }
    recent.reverse();
    let turns_omitted = total_turns.saturating_sub(recent.len());

    let session_label = effective_session
        .clone()
        .unwrap_or_else(|| "all".to_string());
    let checkpoint = substrate
        .session_continuity(effective_session.as_deref())
        .ok()
        .flatten()
        .filter(|view| {
            let in_floor = since.is_none_or(|floor| {
                view.timestamp_iso
                    .as_deref()
                    .and_then(|ts| DateTime::parse_from_rfc3339(ts).ok())
                    .is_none_or(|ts| ts.timestamp().max(0) as u64 >= floor)
            });
            let in_ceiling = until.is_none_or(|ceiling| {
                view.timestamp_iso
                    .as_deref()
                    .and_then(|ts| DateTime::parse_from_rfc3339(ts).ok())
                    .is_none_or(|ts| ts.timestamp().max(0) as u64 <= ceiling)
            });
            in_floor && in_ceiling
        });

    let next_queue = checkpoint
        .as_ref()
        .map(|view| view.next_queue.clone())
        .unwrap_or_default();
    let open_flags = checkpoint
        .as_ref()
        .map(|view| view.open_flags.clone())
        .unwrap_or_default();
    let briefing = include_briefing.then(|| {
        json!({
            "text": compose_briefing(&session_label, checkpoint.as_ref(), &recent),
        })
    });

    let mut response = json!({
        "status": "success",
        "session_id": session_label,
        "turns_count": recent.len(),
        "recent_turns": recent,
        "turns_omitted": turns_omitted,
        "content_truncated": content_truncated,
        "next_queue": next_queue,
        "open_flags": open_flags,
        "checkpoint": checkpoint,
    });
    if let Some(briefing) = briefing {
        response["briefing"] = briefing;
    }

    Ok(response)
}

fn handle_session_checkpoint(
    args: &Value,
    substrate: &mut Substrate,
    readonly: bool,
) -> Result<Value, String> {
    reject_unknown_args("session.checkpoint", args)?;
    if readonly {
        return Err("read-only mode: session_checkpoint refused".to_string());
    }
    let session_id = args
        .get("session_id")
        .and_then(Value::as_str)
        .unwrap_or("default");
    let summary = args
        .get("summary")
        .and_then(Value::as_str)
        .unwrap_or("Turn checkpoint");
    let agent_id = args
        .get("agent_id")
        .and_then(Value::as_str)
        .unwrap_or("agent");
    let checkpoint_type = args
        .get("checkpoint_type")
        .and_then(Value::as_str)
        .unwrap_or("turn");
    let next_queue: Vec<String> = args
        .get("next_queue")
        .and_then(Value::as_array)
        .map(|a| {
            a.iter()
                .filter_map(Value::as_str)
                .map(String::from)
                .collect()
        })
        .unwrap_or_default();
    let open_flags: Vec<String> = args
        .get("open_flags")
        .and_then(Value::as_array)
        .map(|a| {
            a.iter()
                .filter_map(Value::as_str)
                .map(String::from)
                .collect()
        })
        .unwrap_or_default();
    let track = args.get("track").and_then(Value::as_str);
    let commit = args.get("commit").and_then(Value::as_str);
    let branch = args.get("branch").and_then(Value::as_str);
    let tests_green = args.get("tests_green").and_then(Value::as_bool);
    let lease_id = args.get("lease_id").and_then(Value::as_str);
    let context_token = args
        .get("context_token")
        .and_then(Value::as_str)
        .map(str::to_string);

    let cp = SessionCheckpoint {
        session_id: session_id.to_string(),
        agent_id: agent_id.to_string(),
        checkpoint_type: checkpoint_type.to_string(),
        summary: summary.to_string(),
        next_queue,
        open_flags,
        context_token,
        representation: None,
        timestamp_iso: Some(Utc::now().to_rfc3339()),
    };
    let meta = json!({
        "track": track,
        "commit": commit,
        "branch": branch,
        "tests_green": tests_green,
        "lease_id": lease_id,
    });

    substrate.set_intake_authority(RatifiedChannel::mint("wm-session-checkpoint"));
    let rec_id = substrate
        .session_checkpoint_enriched(&cp, &meta)
        .map_err(|e| format!("Failed to record checkpoint: {e}"))?;

    Ok(json!({
        "status": "success",
        "session_id": session_id,
        "checkpoint_record_id": rec_id,
        "checkpoint_type": checkpoint_type,
        "track": track,
        "commit": commit,
        "branch": branch,
        "tests_green": tests_green,
        "lease_id": lease_id,
        "epoch": substrate.store().epoch().unwrap_or(0)
    }))
}

fn handle_session_start(args: &Value, store_path: &Path) -> Result<Value, String> {
    let session_id = Uuid::new_v4().to_string();
    let title = args
        .get("title")
        .and_then(Value::as_str)
        .unwrap_or("Active Session");

    // Persist a start marker so subsequent `session.record` calls without an
    // explicit `session_id` continue this lane (matching v9 semantics).
    let now = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(0);
    let marker = json!({
        "type": "session_start",
        "session_id": session_id,
        "title": title,
        "role": "system",
        "turn_type": "session_start",
        "content": format!("session started: {title}"),
        "timestamp": now
    });
    let session_log = store_path.join("session_log.jsonl");
    if let Ok(mut file) = std::fs::OpenOptions::new()
        .create(true)
        .append(true)
        .open(&session_log)
    {
        let _ = writeln!(file, "{marker}");
    }

    Ok(json!({
        "status": "success",
        "session_id": session_id,
        "title": title,
        "state": "active"
    }))
}

/// Most recent session lane recorded in `session_log.jsonl`.
///
/// Used as the fallback lane for `session.record` when the caller does not
/// pass an explicit `session_id`, so records continue the active lane instead
/// of pooling every client into "default".
fn last_session_lane(store_path: &Path) -> Option<String> {
    let content = std::fs::read_to_string(store_path.join("session_log.jsonl")).ok()?;
    content.lines().rev().find_map(|line| {
        let value: Value = serde_json::from_str(line).ok()?;
        value
            .get("session_id")
            .and_then(Value::as_str)
            .map(str::to_string)
    })
}

#[derive(Default)]
struct LaneSummary {
    turn_count: usize,
    last_timestamp: u64,
    latest_preview: String,
    latest_turn_type: String,
    has_start_marker: bool,
    has_checkpoint: bool,
    tracks: std::collections::BTreeSet<String>,
}

fn handle_session_list(
    args: &Value,
    substrate: &Substrate,
    store_path: &Path,
) -> Result<Value, String> {
    reject_unknown_args("session.list", args)?;
    let filter = args.get("session_id").and_then(Value::as_str);
    let limit = args
        .get("limit")
        .and_then(Value::as_u64)
        .unwrap_or(50)
        .max(1) as usize;

    let mut lanes: std::collections::BTreeMap<String, LaneSummary> =
        std::collections::BTreeMap::new();
    for turn in read_session_turns(store_path) {
        if turn.session_id.is_empty() {
            continue;
        }
        if filter.is_some_and(|lane| lane != turn.session_id) {
            continue;
        }
        let entry = lanes.entry(turn.session_id.clone()).or_default();
        if turn.is_start_marker() {
            entry.has_start_marker = true;
            continue;
        }
        entry.turn_count += 1;
        if let Some(track) = &turn.track {
            if !track.is_empty() {
                entry.tracks.insert(track.clone());
            }
        }
        if turn.timestamp >= entry.last_timestamp {
            entry.last_timestamp = turn.timestamp;
            entry.latest_preview = preview(&turn.content, 120);
            entry.latest_turn_type = turn.turn_type.clone();
        }
    }

    // Checkpoint-only lanes recorded in the substrate.
    for lane in substrate.session_list().unwrap_or_default() {
        if filter.is_some_and(|wanted| wanted != lane) {
            continue;
        }
        lanes.entry(lane).or_default();
    }

    let mut list: Vec<(String, LaneSummary)> = lanes.into_iter().collect();
    for (lane, summary) in list.iter_mut() {
        if !summary.has_checkpoint && !summary.has_start_marker {
            summary.has_checkpoint = substrate
                .session_continuity(Some(lane))
                .ok()
                .flatten()
                .is_some();
        }
    }
    list.sort_by(|(lane_a, a), (lane_b, b)| {
        b.last_timestamp
            .cmp(&a.last_timestamp)
            .then_with(|| lane_a.cmp(lane_b))
    });
    list.truncate(limit);

    let sessions: Vec<Value> = list
        .into_iter()
        .map(|(lane, summary)| {
            json!({
                "session_id": lane,
                "turn_count": summary.turn_count,
                "last_timestamp": summary.last_timestamp,
                "latest_preview": summary.latest_preview,
                "latest_turn_type": summary.latest_turn_type,
                "has_start_marker": summary.has_start_marker,
                "has_checkpoint": summary.has_checkpoint,
                "tracks": summary.tracks.into_iter().collect::<Vec<String>>(),
            })
        })
        .collect();

    Ok(json!({
        "status": "success",
        "count": sessions.len(),
        "sessions": sessions
    }))
}

fn handle_session_recall(args: &Value, store_path: &Path) -> Result<Value, String> {
    reject_unknown_args("session.recall", args)?;
    let session_id = args.get("session_id").and_then(Value::as_str);
    let query = args
        .get("query")
        .and_then(Value::as_str)
        .map(str::to_lowercase)
        .filter(|query| !query.is_empty());
    let limit = args.get("limit").and_then(Value::as_u64).unwrap_or(50) as usize;

    let mut turns: Vec<Value> = read_session_turns(store_path)
        .into_iter()
        .filter(|turn| !turn.is_start_marker())
        .filter(|turn| session_id.is_none_or(|target| turn.session_id == target))
        .filter(|turn| {
            query
                .as_ref()
                .is_none_or(|query| turn.content.to_lowercase().contains(query))
        })
        .filter_map(|turn| serde_json::to_value(turn).ok())
        .collect();
    let total = turns.len();
    if turns.len() > limit {
        turns.drain(..turns.len() - limit);
    }

    Ok(json!({
        "status": "success",
        "session_id": session_id.unwrap_or("all"),
        "total_turns": total,
        "returned": turns.len(),
        "trajectory": turns
    }))
}

fn handle_session_replay(args: &Value, store_path: &Path) -> Result<Value, String> {
    reject_unknown_args("session.replay", args)?;
    let session_id = args.get("session_id").and_then(Value::as_str);
    let mode = args.get("mode").and_then(Value::as_str).unwrap_or("full");
    let n = args.get("n").and_then(Value::as_u64).unwrap_or(50).max(1) as usize;
    let since = args
        .get("since")
        .and_then(Value::as_str)
        .map(parse_time_bound)
        .transpose()?;
    let until = args
        .get("until")
        .and_then(Value::as_str)
        .map(parse_time_bound)
        .transpose()?;
    if let (Some(since), Some(until)) = (since, until) {
        if since > until {
            return Err("session.replay: 'since' is after 'until'".to_string());
        }
    }
    let include_superseded = args
        .get("include_superseded")
        .and_then(Value::as_bool)
        .unwrap_or(false);
    let min_importance = args
        .get("min_importance")
        .and_then(Value::as_f64)
        .unwrap_or(0.7);
    let token_budget = args
        .get("token_budget")
        .and_then(Value::as_u64)
        .unwrap_or(2000);
    let turn_types: Option<Vec<String>> =
        args.get("turn_types").and_then(Value::as_array).map(|a| {
            a.iter()
                .filter_map(Value::as_str)
                .map(str::to_string)
                .collect()
        });

    let mut turns: Vec<SessionTurn> = read_session_turns(store_path)
        .into_iter()
        .filter(|turn| !turn.is_start_marker())
        .filter(|turn| session_id.is_none_or(|target| turn.session_id == target))
        .filter(|turn| since.is_none_or(|floor| turn.timestamp >= floor))
        .filter(|turn| until.is_none_or(|ceiling| turn.timestamp <= ceiling))
        .filter(|turn| include_superseded || turn.superseded_by.is_none())
        .collect();
    let total_turns = turns.len();

    let mut token_estimate = 0u64;
    match mode {
        "full" => {}
        "selective" => {
            turns.retain(|turn| turn.importance >= min_importance);
            if let Some(types) = &turn_types {
                turns.retain(|turn| types.contains(&turn.turn_type));
            }
        }
        "progressive" => {
            let mut selected: Vec<SessionTurn> = Vec::new();
            for turn in turns.iter().rev() {
                let cost = turn.estimated_tokens();
                if !selected.is_empty() && token_estimate + cost > token_budget {
                    break;
                }
                token_estimate += cost;
                selected.push(turn.clone());
            }
            selected.reverse();
            turns = selected;
        }
        other => {
            return Err(format!(
                "session.replay refuses mode '{other}': supported modes are 'full', 'selective', 'progressive'"
            ));
        }
    }

    let after_filter = turns.len();
    if turns.len() > n {
        turns.drain(..turns.len() - n);
    }
    if mode != "progressive" {
        token_estimate = turns.iter().map(SessionTurn::estimated_tokens).sum();
    }

    Ok(json!({
        "status": "success",
        "session_id": session_id.unwrap_or("all"),
        "mode": mode,
        "total_turns": total_turns,
        "turns_after_filter": after_filter,
        "returned": turns.len(),
        "turns_omitted": after_filter.saturating_sub(turns.len()),
        "token_estimate": token_estimate,
        "trajectory": turns
    }))
}

fn handle_session_digest(
    args: &Value,
    substrate: &Substrate,
    store_path: &Path,
) -> Result<Value, String> {
    reject_unknown_args("session.digest", args)?;
    let session_filter = args
        .get("session_id")
        .and_then(Value::as_str)
        .map(str::to_string)
        .or_else(|| last_session_lane(store_path));
    let n = args.get("n").and_then(Value::as_u64).unwrap_or(20).max(1) as usize;

    let mut turns: Vec<SessionTurn> = read_session_turns(store_path)
        .into_iter()
        .filter(|turn| !turn.is_start_marker())
        .filter(|turn| {
            session_filter
                .as_deref()
                .is_none_or(|target| turn.session_id == target)
        })
        .filter(|turn| turn.superseded_by.is_none())
        .collect();
    if turns.len() > n {
        turns.drain(..turns.len() - n);
    }

    let label = session_filter.clone().unwrap_or_else(|| "all".to_string());
    let checkpoint = substrate
        .session_continuity(session_filter.as_deref())
        .ok()
        .flatten();
    let (markdown, json_digest) = compose_session_digest(&label, &turns, checkpoint.as_ref());

    Ok(json!({
        "status": "success",
        "session_id": label,
        "markdown": markdown,
        "json": json_digest
    }))
}

// ── Receipts & Evidence ────────────────────────────────────────────────────

const EMIT_SPEC_SESSION: &str = "continuity-receipt/0.5#session";
const EMIT_SPEC_STATE_TRANSITION: &str = "continuity-receipt/0.5#state_transition";

fn hex_encode(bytes: &[u8]) -> String {
    bytes.iter().map(|byte| format!("{byte:02x}")).collect()
}

fn hex_decode(hex: &str) -> Option<Vec<u8>> {
    if hex.len() % 2 != 0 {
        return None;
    }
    (0..hex.len())
        .step_by(2)
        .map(|index| u8::from_str_radix(&hex[index..index + 2], 16).ok())
        .collect()
}

fn gate_key_did(key: &SigningKey) -> String {
    format!("did:key:{}", hex_encode(&key.verifying_key().to_bytes()))
}

/// Load the store's existing Mandala gate key without creating one.
fn load_gate_signing_key(store_path: &Path) -> Result<SigningKey, String> {
    let key_path = store_path.join("mandala_gate_key.bin");
    let bytes = std::fs::read(&key_path)
        .map_err(|e| format!("gate key read ({}): {e}", key_path.display()))?;
    if bytes.len() != 32 {
        return Err(format!("gate key must be 32 bytes, got {}", bytes.len()));
    }
    let mut array = [0u8; 32];
    array.copy_from_slice(&bytes);
    Ok(SigningKey::from_bytes(&array))
}

/// Signed continuity receipt emitted by `receipts.emit`.
///
/// `content_digest` is the SHA-256 of the canonical signing bytes (which
/// exclude `content_digest` and `signature`); verification recomputes it and
/// then checks the Ed25519 signature over the same bytes.
#[derive(Debug, Clone, Serialize, Deserialize)]
struct EmittedContinuityReceipt {
    spec: String,
    receipt_id: String,
    kind: String,
    subject: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    session_id: Option<String>,
    created_at_ms: u64,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    turn_count: Option<u64>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    first_turn_ts: Option<u64>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    last_turn_ts: Option<u64>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    turns_digest: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    store_epoch: Option<u64>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    store_record_count: Option<u64>,
    payload_digest: String,
    prior_receipt_digest: String,
    content_digest: String,
    issuer_did: String,
    #[serde(default)]
    signature: Option<String>,
}

impl EmittedContinuityReceipt {
    fn canonical_signing_bytes(&self) -> Vec<u8> {
        let mut hasher = Sha256::new();
        hasher.update(self.spec.as_bytes());
        hasher.update(b"|");
        hasher.update(self.receipt_id.as_bytes());
        hasher.update(b"|");
        hasher.update(self.kind.as_bytes());
        hasher.update(b"|");
        hasher.update(self.subject.as_bytes());
        hasher.update(b"|");
        if let Some(session) = &self.session_id {
            hasher.update(session.as_bytes());
        }
        hasher.update(b"|");
        hasher.update(self.created_at_ms.to_le_bytes());
        for value in [
            self.turn_count,
            self.first_turn_ts,
            self.last_turn_ts,
            self.store_epoch,
            self.store_record_count,
        ] {
            hasher.update(b"|");
            if let Some(value) = value {
                hasher.update(value.to_le_bytes());
            }
        }
        hasher.update(b"|");
        if let Some(digest) = &self.turns_digest {
            hasher.update(digest.as_bytes());
        }
        hasher.update(b"|");
        hasher.update(self.payload_digest.as_bytes());
        hasher.update(b"|");
        hasher.update(self.prior_receipt_digest.as_bytes());
        hasher.update(b"|");
        hasher.update(self.issuer_did.as_bytes());
        hasher.finalize().to_vec()
    }

    fn sign(&mut self, key: &SigningKey) {
        let signature = key.sign(&self.canonical_signing_bytes());
        self.signature = Some(hex_encode(&signature.to_bytes()));
    }

    fn verify(&self, key: &VerifyingKey) -> Result<(), String> {
        let signature_hex = self.signature.as_ref().ok_or("unsigned receipt")?;
        let bytes = hex_decode(signature_hex).ok_or("signature is not valid hex")?;
        if bytes.len() != 64 {
            return Err("signature must be 64 bytes".to_string());
        }
        let mut array = [0u8; 64];
        array.copy_from_slice(&bytes);
        let signature = Signature::from_bytes(&array);
        key.verify(&self.canonical_signing_bytes(), &signature)
            .map_err(|e| format!("signature invalid: {e}"))
    }
}

/// Most recent `content_digest` for a receipt kind from `<store>/receipts/emitted.jsonl`.
fn prior_emitted_digest(journal: &Path, kind: &str) -> Option<String> {
    let content = std::fs::read_to_string(journal).ok()?;
    content.lines().rev().find_map(|line| {
        let value: Value = serde_json::from_str(line.trim()).ok()?;
        if value.get("kind").and_then(Value::as_str) == Some(kind) {
            value
                .get("content_digest")
                .and_then(Value::as_str)
                .map(str::to_string)
        } else {
            None
        }
    })
}

fn verify_emitted_continuity_receipt(value: &Value, store_path: &Path) -> Result<Value, String> {
    let receipt: EmittedContinuityReceipt =
        serde_json::from_value(value.clone()).map_err(|e| format!("emitted receipt parse: {e}"))?;
    let expected_spec = match receipt.kind.as_str() {
        "session" => EMIT_SPEC_SESSION,
        "state_transition" => EMIT_SPEC_STATE_TRANSITION,
        other => {
            return Err(format!(
                "unsupported emitted continuity receipt kind '{other}'"
            ));
        }
    };
    if receipt.spec != expected_spec {
        return Err(format!(
            "spec/kind mismatch: expected {expected_spec}, got {}",
            receipt.spec
        ));
    }
    let key = load_gate_signing_key(store_path)?;
    let expected_did = gate_key_did(&key);
    if receipt.issuer_did != expected_did {
        return Err(format!(
            "issuer_did mismatch: expected {expected_did}, got {}",
            receipt.issuer_did
        ));
    }
    let canonical = receipt.canonical_signing_bytes();
    let recomputed = hex_encode(&Sha256::digest(&canonical));
    if recomputed != receipt.content_digest {
        return Err("content_digest mismatch: receipt fields were altered".to_string());
    }
    receipt.verify(&key.verifying_key())?;

    Ok(json!({
        "status": "success",
        "valid": true,
        "profile": receipt.kind,
        "spec": receipt.spec,
        "receipt_id": receipt.receipt_id,
        "issuer_did": receipt.issuer_did,
        "detail": "emitted continuity receipt verifies against the store gate key",
        "verified_offline": true,
        "signature_scope": format!("{} canonical_signing_bytes", receipt.spec),
        "unauthenticated_fields": [],
        "numeric_projection": ["integer fields use their exact encoded representation"],
        "scope_notes": [
            "signature authenticates the issuer's claimed turn digest / store snapshot; \
             the session log and store counters are not re-read from disk here"
        ],
    }))
}

fn handle_receipts_emit(
    args: &Value,
    substrate: &Substrate,
    store_path: &Path,
    readonly: bool,
) -> Result<Value, String> {
    reject_unknown_args("receipts.emit", args)?;
    if readonly {
        return Err("read-only mode: receipts.emit refused".to_string());
    }
    let kind = args
        .get("kind")
        .and_then(Value::as_str)
        .ok_or_else(|| "Missing required parameter 'kind'".to_string())?;
    if kind != "session" && kind != "state_transition" {
        return Err(format!(
            "receipts.emit refuses kind '{kind}': supported kinds are 'session' and 'state_transition'"
        ));
    }
    let limit = args
        .get("limit")
        .and_then(Value::as_u64)
        .unwrap_or(200)
        .max(1) as usize;
    let out = args.get("out").and_then(Value::as_str);

    let (signing_key, _) = resolve_or_create_mandala_gate_key(store_path)
        .map_err(|e| format!("gate key error: {e}"))?;
    let issuer_did = gate_key_did(&signing_key);
    let receipts_dir = store_path.join("receipts");
    std::fs::create_dir_all(&receipts_dir).map_err(|e| format!("receipt dir: {e}"))?;
    let journal = receipts_dir.join("emitted.jsonl");
    let prior_receipt_digest =
        prior_emitted_digest(&journal, kind).unwrap_or_else(|| "genesis".to_string());

    let mut receipt = EmittedContinuityReceipt {
        spec: String::new(),
        receipt_id: Uuid::new_v4().to_string(),
        kind: kind.to_string(),
        subject: String::new(),
        session_id: None,
        created_at_ms: std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map(|d| d.as_millis() as u64)
            .unwrap_or(0),
        turn_count: None,
        first_turn_ts: None,
        last_turn_ts: None,
        turns_digest: None,
        store_epoch: None,
        store_record_count: None,
        payload_digest: String::new(),
        prior_receipt_digest,
        content_digest: String::new(),
        issuer_did,
        signature: None,
    };

    match kind {
        "session" => {
            let session_id = args
                .get("session_id")
                .and_then(Value::as_str)
                .map(str::to_string);
            let mut turns: Vec<SessionTurn> = read_session_turns(store_path)
                .into_iter()
                .filter(|turn| {
                    session_id
                        .as_ref()
                        .is_none_or(|target| turn.session_id == *target)
                })
                .collect();
            if turns.len() > limit {
                turns.drain(..turns.len() - limit);
            }
            let canonical_turns = turns
                .iter()
                .map(|turn| serde_json::to_string(turn).unwrap_or_default())
                .collect::<Vec<String>>()
                .join("\n");
            let turns_digest = hex_encode(&Sha256::digest(canonical_turns.as_bytes()));
            receipt.spec = EMIT_SPEC_SESSION.to_string();
            receipt.subject = format!("session:{}", session_id.as_deref().unwrap_or("all"));
            receipt.session_id = session_id;
            receipt.turn_count = Some(turns.len() as u64);
            receipt.first_turn_ts = turns.first().map(|turn| turn.timestamp);
            receipt.last_turn_ts = turns.last().map(|turn| turn.timestamp);
            receipt.turns_digest = Some(turns_digest.clone());
            receipt.payload_digest = turns_digest;
        }
        "state_transition" => {
            let epoch = substrate.store().epoch().unwrap_or(0);
            let record_count = substrate.store().record_count().unwrap_or(0);
            let realm_id = substrate
                .store()
                .realm_id()
                .map(|bytes| hex_encode(&bytes))
                .unwrap_or_default();
            let payload = json!({
                "epoch": epoch,
                "record_count": record_count,
                "realm_id": realm_id,
                "journal_ok": substrate.journal_ok(),
                "violations": substrate.violations(),
            });
            receipt.spec = EMIT_SPEC_STATE_TRANSITION.to_string();
            receipt.subject = format!("store:{realm_id}");
            receipt.store_epoch = Some(epoch);
            receipt.store_record_count = Some(record_count as u64);
            receipt.payload_digest = hex_encode(&Sha256::digest(payload.to_string().as_bytes()));
        }
        other => {
            return Err(format!(
                "receipts.emit refuses kind '{other}': supported kinds are 'session' and 'state_transition'"
            ));
        }
    }

    let canonical = receipt.canonical_signing_bytes();
    receipt.content_digest = hex_encode(&Sha256::digest(&canonical));
    receipt.sign(&signing_key);
    receipt
        .verify(&signing_key.verifying_key())
        .map_err(|e| format!("emitted receipt self-verification failed: {e}"))?;

    let serialized =
        serde_json::to_string_pretty(&receipt).map_err(|e| format!("receipt serialize: {e}"))?;
    let path = receipts_dir.join(format!("{}.json", receipt.receipt_id));
    std::fs::write(&path, &serialized).map_err(|e| format!("receipt write: {e}"))?;
    {
        let line = serde_json::to_string(&receipt).map_err(|e| format!("receipt encode: {e}"))?;
        let mut file = std::fs::OpenOptions::new()
            .create(true)
            .append(true)
            .open(&journal)
            .map_err(|e| format!("receipts journal open: {e}"))?;
        file.write_all(line.as_bytes())
            .and_then(|_| file.write_all(b"\n"))
            .and_then(|_| file.sync_data())
            .map_err(|e| format!("receipts journal write: {e}"))?;
    }
    let out_path = if let Some(out) = out {
        let out_path = Path::new(out);
        std::fs::write(out_path, &serialized).map_err(|e| format!("receipt out write: {e}"))?;
        Some(out_path.display().to_string())
    } else {
        None
    };

    Ok(json!({
        "status": "success",
        "kind": kind,
        "receipt": receipt,
        "path": path.display().to_string(),
        "out_path": out_path,
        "prior_receipt_digest": receipt.prior_receipt_digest,
    }))
}

fn handle_receipts_verify(args: &Value, store_path: &Path) -> Result<Value, String> {
    let object = args
        .as_object()
        .ok_or_else(|| "receipts.verify arguments must be an object".to_string())?;
    if let Some(field) = object.keys().find(|field| field.as_str() != "bundle") {
        return Err(format!(
            "receipts.verify refuses unknown argument '{field}'"
        ));
    }
    let bundle = args
        .get("bundle")
        .ok_or_else(|| "receipts.verify requires an inline 'bundle' receipt object".to_string())?;
    if let Some(spec) = bundle.get("spec").and_then(Value::as_str) {
        if spec == EMIT_SPEC_SESSION || spec == EMIT_SPEC_STATE_TRANSITION {
            return verify_emitted_continuity_receipt(bundle, store_path);
        }
    }
    crate::receipt_verify::verify_receipt_value(bundle, store_path)
}

// ── Mandala OS Handlers ────────────────────────────────────────────────────

fn handle_mandala_status(store_path: &Path) -> Result<Value, String> {
    let (signing_key, _) = resolve_or_create_mandala_gate_key(store_path)
        .map_err(|e| format!("Gate key error: {e}"))?;
    let verifying_bytes = signing_key.verifying_key().to_bytes();
    let gate_did = format!(
        "did:key:{}",
        verifying_bytes
            .iter()
            .map(|b| format!("{b:02x}"))
            .collect::<String>()
    );

    let hw = wm_gen3_core::homeostasis::HardwareTelemetry::probe();
    let mut ctrl = wm_gen3_core::homeostasis::HomeostaticController::new();
    let telem = hw.to_telemetry_vector(800.0, 0.10, 0.0, 0.25);
    let (regime, actuators) = ctrl.update_cycle(&telem);

    Ok(json!({
        "status": "success",
        "route": "mandala.status",
        "gate_did": gate_did,
        "landlock_supported": true,
        "abi_version": "v1-v5 auto-negotiated",
        "network_sandbox": "AccessNet (ABI V4+ deny-by-default)",
        "resource_limits": "POSIX rlimit (AS, CPU, NOFILE)",
        "kekkai_latency_baseline_us": 230.22,
        "homeostatic_regime": format!("{:?}", regime).to_lowercase(),
        "hardware_telemetry": {
            "cpu_temp_c": hw.cpu_temp_c,
            "battery_pct": hw.battery_pct,
            "on_ac_power": hw.on_ac_power,
            "load_avg_1m": hw.load_avg_1m,
            "mem_available_mb": hw.mem_available_mb,
            "probe_latency_ns": hw.probe_latency_ns
        },
        "actuator_state": {
            "top_k": actuators.top_k,
            "graph_expansion_enabled": actuators.graph_expansion_enabled,
            "background_sleep_active": actuators.background_sleep_active,
            "write_throttle_factor": actuators.write_throttle_factor
        }
    }))
}

#[cfg(any(feature = "systemone", feature = "system05"))]
fn decision_outcome_tool_schema(mode_hint: &str) -> Value {
    json!({
        "name": "decision.outcome",
        "title": "Record Decision Outcome",
        "description": format!("Sign and journal the outcome of a dispatched decision/shortlist receipt (success, failure, corrected) for the learning loop.{mode_hint}"),
        "inputSchema": {
            "type": "object",
            "properties": {
                "receipt_path": { "type": "string", "description": "Path to the subject receipt JSON under <store>/receipts" },
                "outcome": { "type": "string", "enum": ["success", "failure", "corrected", "unknown"], "description": "Observed outcome" },
                "corrected_route": { "type": "string", "description": "Correct route when the outcome is 'corrected'" },
                "note": { "type": "string", "description": "Free-form note" },
                "session_id": { "type": "string" },
                "tenant_id": { "type": "string" }
            },
            "required": ["receipt_path", "outcome"]
        }
    })
}

#[cfg(feature = "system05")]
fn system05_tool_schema(mode_hint: &str) -> Value {
    json!({
        "name": "decision.shortlist",
        "title": "System 0.5 Route Shortlist (Static Embeddings)",
        "description": format!("Rank candidate routes/actions for a state with the local static-embedding retrieval organ (no network, no model forward pass) and emit a signed shortlist receipt.{mode_hint}"),
        "inputSchema": {
            "type": "object",
            "properties": {
                "state": { "type": ["string", "object"], "description": "State to retrieve candidates for (text or JSON)" },
                "routes": { "type": "object", "description": "Candidate set: {name: description} or {name: [utterances...]}; multi-utterance routes score by best match" },
                "catalog_path": { "type": "string", "description": "Path to a JSON file with {name: description}; used when `routes` is absent" },
                "k": { "type": "integer", "description": "Shortlist size (default 5)" },
                "margin_threshold": { "type": "number", "description": "Below this top1-top2 margin the gate is 'ambiguous' (default 0.02)" },
                "cascade": { "type": "boolean", "description": "If ambiguous, cascade to System 1.5 Deliberator (default true)" },
                "session_id": { "type": "string", "description": "Session id for the shortlist receipt" },
                "tenant_id": { "type": "string", "description": "Tenant id for the shortlist receipt (default: local)" },
                "task_class": { "type": "string", "description": "Task class (e.g. route_dispatch)" },
                "emit_receipt": { "type": "boolean", "description": "Write a signed shortlist receipt to <store>/receipts (default true)" }
            },
            "required": ["state"]
        }
    })
}

fn deliberation_tool_schema(mode_hint: &str) -> Value {
    json!({
        "name": "decision.deliberate",
        "title": "System 1.5 Local Deliberator (Grammar-Constrained SLM)",
        "description": format!("Deliberate over ambiguous candidate options using local grammar-constrained SLM inference (100% schema guarantee, no hallucination) and emit a signed deliberation receipt.{mode_hint}"),
        "inputSchema": {
            "type": "object",
            "properties": {
                "intent": { "type": "string", "description": "User request or state description" },
                "candidates": { "type": ["array", "object"], "description": "Allowed candidate action names, objects, or map" },
                "emit_receipt": { "type": "boolean", "description": "Write signed deliberation receipt to <store>/receipts (default true)" }
            },
            "required": ["intent", "candidates"]
        }
    })
}

#[cfg(feature = "system05")]
fn handle_decision_shortlist(
    args: &Value,
    store_path: &Path,
    readonly: bool,
) -> Result<Value, String> {
    let state = args.get("state").ok_or("missing required field 'state'")?;
    let state_text = match state {
        Value::String(text) => text.clone(),
        other => other.to_string(),
    };
    let routes = match args.get("routes") {
        Some(value) => value.clone(),
        None => {
            let path = match args.get("catalog_path").and_then(Value::as_str) {
                Some(path) => std::path::PathBuf::from(path),
                None => wm_gen3_zeropointfive::System05::resolve_catalog_path(None)
                    .map_err(|e| e.to_string())?,
            };
            let raw = std::fs::read_to_string(&path)
                .map_err(|e| format!("catalog read ({}): {e}", path.display()))?;
            serde_json::from_str(&raw).map_err(|e| format!("catalog parse: {e}"))?
        }
    };
    let k = args.get("k").and_then(Value::as_u64).unwrap_or(5) as usize;
    let tau = args
        .get("margin_threshold")
        .and_then(Value::as_f64)
        .unwrap_or(0.02);
    let cascade = args.get("cascade").and_then(Value::as_bool).unwrap_or(true);

    static ORGAN: std::sync::OnceLock<Result<wm_gen3_zeropointfive::System05, String>> =
        std::sync::OnceLock::new();
    let organ = ORGAN.get_or_init(|| {
        wm_gen3_zeropointfive::System05::resolve_model_dir(None)
            .map(wm_gen3_zeropointfive::System05::new)
            .map_err(|e| e.to_string())
    });
    let organ = organ.as_ref().map_err(|e| e.clone())?;

    let mut outcome = organ
        .shortlist(&state_text, &routes, k)
        .map_err(|e| e.to_string())?;
    let margin = outcome.get("margin").and_then(Value::as_f64).unwrap_or(0.0);
    let gate = if margin >= tau {
        "dispatch"
    } else {
        "ambiguous"
    };
    outcome["gate"] = json!(gate);
    outcome["margin_threshold"] = json!(tau);

    // If ambiguous and cascade requested, run System 1.5 Deliberator
    if gate == "ambiguous" && cascade {
        let mut candidate_routes: Vec<crate::deliberation::CandidateRoute> = Vec::new();
        if let Some(ranked) = outcome.get("ranked").and_then(Value::as_array) {
            for entry in ranked {
                let name = entry
                    .get("route")
                    .and_then(Value::as_str)
                    .unwrap_or_default()
                    .to_string();
                let score = entry.get("score").and_then(Value::as_f64).unwrap_or(0.0);
                let description = match routes.get(&name) {
                    Some(serde_json::Value::String(s)) => Some(s.clone()),
                    Some(serde_json::Value::Array(arr)) => {
                        arr.first().and_then(|v| v.as_str()).map(|s| s.to_string())
                    }
                    _ => None,
                };
                candidate_routes.push(crate::deliberation::CandidateRoute {
                    name,
                    score,
                    description,
                });
            }
        }
        let deliberator = crate::deliberation::Deliberator::default();
        if let Ok(delib) = deliberator.deliberate(&state_text, &candidate_routes) {
            let strict = std::env::var(crate::deliberation::ENV_DELIBERATION_STRICT).is_ok();
            if delib.degraded && strict {
                outcome["deliberation_refused"] = json!("degraded_strict");
            } else if let Ok((signing_key, _)) = resolve_or_create_mandala_gate_key(store_path) {
                let cand_names: Vec<String> =
                    candidate_routes.iter().map(|c| c.name.clone()).collect();
                let receipt = crate::deliberation::DeliberationReceipt::sign(
                    &signing_key,
                    &state_text,
                    &cand_names,
                    &delib.chosen_route,
                    margin,
                    tau,
                    delib.confidence,
                    delib.latency_ms,
                    delib.degraded,
                    &delib.slm_model_sha256,
                    &delib.prompt_version,
                );
                if !readonly {
                    let _ = receipt.persist(store_path);
                }
                outcome["deliberation"] = json!({
                    "chosen_route": delib.chosen_route,
                    "confidence": delib.confidence,
                    "latency_ms": delib.latency_ms,
                    "degraded": delib.degraded,
                    "slm_model_sha256": delib.slm_model_sha256,
                    "prompt_version": delib.prompt_version,
                    "receipt_id": receipt.receipt_id,
                    "spec": receipt.spec,
                });
                outcome["dispatched_route"] = json!(delib.chosen_route);
            }
        }
    }

    let emit_receipt = args
        .get("emit_receipt")
        .and_then(Value::as_bool)
        .unwrap_or(true);
    if readonly || !emit_receipt {
        outcome["receipt"] = Value::Null;
        outcome["receipt_emitted"] = json!(false);
        return Ok(outcome);
    }

    let (signing_key, _) = resolve_or_create_mandala_gate_key(store_path)
        .map_err(|e| format!("gate key error: {e}"))?;
    let gate_did = format!(
        "did:key:{}",
        signing_key
            .verifying_key()
            .to_bytes()
            .iter()
            .map(|byte| format!("{byte:02x}"))
            .collect::<String>()
    );
    let mut receipt = crate::shortlist_receipt::ShortlistReceipt::from_outcome(
        &outcome, state, &routes, args, gate_did,
    );
    receipt.sign(&signing_key);
    receipt
        .verify(&signing_key.verifying_key())
        .map_err(|e| format!("shortlist receipt self-verification failed: {e}"))?;

    let receipts_dir = store_path.join("receipts");
    std::fs::create_dir_all(&receipts_dir).map_err(|e| format!("receipt dir: {e}"))?;
    let receipt_path = receipts_dir.join(format!("shortlist-{}.json", receipt.receipt_id));
    let serialized =
        serde_json::to_string_pretty(&receipt).map_err(|e| format!("receipt serialize: {e}"))?;
    std::fs::write(&receipt_path, serialized).map_err(|e| format!("receipt write: {e}"))?;

    outcome["receipt"] = serde_json::to_value(&receipt).map_err(|e| e.to_string())?;
    outcome["receipt_path"] = json!(receipt_path.display().to_string());
    outcome["receipt_emitted"] = json!(true);
    Ok(outcome)
}

fn handle_decision_deliberate(
    args: &Value,
    store_path: &Path,
    readonly: bool,
) -> Result<Value, String> {
    let intent = args
        .get("intent")
        .or_else(|| args.get("state"))
        .and_then(Value::as_str)
        .ok_or("missing required field 'intent' or 'state'")?;

    let candidates_val = args
        .get("candidates")
        .ok_or("missing required field 'candidates'")?;

    let mut candidate_routes: Vec<crate::deliberation::CandidateRoute> = Vec::new();
    match candidates_val {
        Value::Array(arr) => {
            for item in arr {
                match item {
                    Value::String(s) => {
                        candidate_routes.push(crate::deliberation::CandidateRoute {
                            name: s.clone(),
                            score: 0.9,
                            description: None,
                        });
                    }
                    Value::Object(obj) => {
                        let name = obj
                            .get("name")
                            .or_else(|| obj.get("route"))
                            .and_then(Value::as_str)
                            .unwrap_or_default()
                            .to_string();
                        let score = obj.get("score").and_then(Value::as_f64).unwrap_or(0.9);
                        let desc = obj
                            .get("description")
                            .and_then(Value::as_str)
                            .map(|s| s.to_string());
                        if !name.is_empty() {
                            candidate_routes.push(crate::deliberation::CandidateRoute {
                                name,
                                score,
                                description: desc,
                            });
                        }
                    }
                    _ => {}
                }
            }
        }
        Value::Object(obj) => {
            for (k, v) in obj {
                let desc = v.as_str().map(|s| s.to_string());
                candidate_routes.push(crate::deliberation::CandidateRoute {
                    name: k.clone(),
                    score: 0.9,
                    description: desc,
                });
            }
        }
        _ => return Err("candidates must be an array of route names or objects".to_string()),
    }

    if candidate_routes.is_empty() {
        return Err("candidates list cannot be empty".to_string());
    }

    let deliberator = crate::deliberation::Deliberator::default();
    let delib = deliberator.deliberate(intent, &candidate_routes)?;
    if delib.degraded && std::env::var(crate::deliberation::ENV_DELIBERATION_STRICT).is_ok() {
        return Err(format!(
            "deliberation degraded (SLM unavailable or unparsable) and {} is set; refusing to sign a receipt",
            crate::deliberation::ENV_DELIBERATION_STRICT
        ));
    }

    let gate = crate::deliberation::ConformalGate::default();
    let tau = gate.calibrate_tau(store_path);

    let candidate_names: Vec<String> = candidate_routes.iter().map(|c| c.name.clone()).collect();
    let (signing_key, _) = resolve_or_create_mandala_gate_key(store_path)
        .map_err(|e| format!("gate key resolution: {e}"))?;

    let receipt = crate::deliberation::DeliberationReceipt::sign(
        &signing_key,
        intent,
        &candidate_names,
        &delib.chosen_route,
        0.0,
        tau,
        delib.confidence,
        delib.latency_ms,
        delib.degraded,
        &delib.slm_model_sha256,
        &delib.prompt_version,
    );

    let emit_receipt = args
        .get("emit_receipt")
        .and_then(Value::as_bool)
        .unwrap_or(true);
    if !readonly && emit_receipt {
        let _ = receipt.persist(store_path);
    }

    Ok(json!({
        "status": "success",
        "chosen_route": delib.chosen_route,
        "confidence": delib.confidence,
        "latency_ms": delib.latency_ms,
        "degraded": delib.degraded,
        "slm_model_sha256": delib.slm_model_sha256,
        "prompt_version": delib.prompt_version,
        "candidates": candidate_names,
        "receipt": receipt,
        "receipt_id": receipt.receipt_id,
        "spec": receipt.spec,
    }))
}

#[cfg(feature = "systemone")]
fn systemone_tool_schema(mode_hint: &str) -> Value {
    json!({
        "name": "systemone.decide",
        "title": "System One Typed Decision (Local Laya)",
        "description": format!("Run the local System One decision organ (Laya): typed choice/score/noul questions over a state, calibrated probabilities, and a signed decision receipt.{mode_hint}"),
        "inputSchema": {
            "type": "object",
            "properties": {
                "state": { "type": ["string", "object"], "description": "State to decide over (text or JSON)" },
                "questions": { "type": ["object", "array"], "description": "Questions keyed by id (object) or array of {id, type, instructions, criteria}" },
                "session_id": { "type": "string", "description": "Session id for the decision receipt" },
                "tenant_id": { "type": "string", "description": "Tenant id for the decision receipt (default: local)" },
                "task_class": { "type": "string", "description": "Task class for selective evaluation (e.g. route_dispatch)" },
                "candidate_set_version": { "type": "string", "description": "Version tag of the candidate set" },
                "policy_version": { "type": "string", "description": "Decision policy version (default: systemone/0.1)" },
                "emit_receipt": { "type": "boolean", "description": "Write a signed decision receipt to <store>/receipts (default true)" }
            },
            "required": ["state", "questions"]
        }
    })
}

#[cfg(feature = "systemone")]
fn handle_systemone_decide(
    args: &Value,
    store_path: &Path,
    readonly: bool,
) -> Result<Value, String> {
    let state = args.get("state").ok_or("missing required field 'state'")?;
    let questions = args
        .get("questions")
        .ok_or("missing required field 'questions'")?;

    static ORGAN: std::sync::OnceLock<Result<wm_gen3_systemone::SystemOne, String>> =
        std::sync::OnceLock::new();
    let organ = ORGAN.get_or_init(|| {
        wm_gen3_systemone::SystemOne::resolve_model_dir(None)
            .map(wm_gen3_systemone::SystemOne::new)
            .map_err(|e| e.to_string())
    });
    let organ = organ.as_ref().map_err(|e| e.clone())?;

    let outcome = organ.decide(state, questions).map_err(|e| e.to_string())?;
    let mut response = json!({
        "status": "success",
        "route": "systemone.decide",
        "decision": outcome,
    });

    let emit_receipt = args
        .get("emit_receipt")
        .and_then(Value::as_bool)
        .unwrap_or(true);
    if readonly || !emit_receipt {
        response["receipt"] = Value::Null;
        response["receipt_emitted"] = json!(false);
        return Ok(response);
    }

    let (signing_key, _) = resolve_or_create_mandala_gate_key(store_path)
        .map_err(|e| format!("gate key error: {e}"))?;
    let gate_did = format!(
        "did:key:{}",
        signing_key
            .verifying_key()
            .to_bytes()
            .iter()
            .map(|byte| format!("{byte:02x}"))
            .collect::<String>()
    );

    let decision = response.get("decision").cloned().unwrap_or(Value::Null);
    let mut receipt = crate::decision_receipt::DecisionReceipt::from_outcome(
        &decision, state, questions, args, gate_did,
    );
    receipt.sign(&signing_key);
    receipt
        .verify(&signing_key.verifying_key())
        .map_err(|e| format!("decision receipt self-verification failed: {e}"))?;

    let receipts_dir = store_path.join("receipts");
    std::fs::create_dir_all(&receipts_dir).map_err(|e| format!("receipt dir: {e}"))?;
    let receipt_path = receipts_dir.join(format!("decision-{}.json", receipt.receipt_id));
    let serialized =
        serde_json::to_string_pretty(&receipt).map_err(|e| format!("receipt serialize: {e}"))?;
    std::fs::write(&receipt_path, serialized).map_err(|e| format!("receipt write: {e}"))?;

    response["receipt"] = serde_json::to_value(&receipt).map_err(|e| e.to_string())?;
    response["receipt_path"] = json!(receipt_path.display().to_string());
    response["receipt_emitted"] = json!(true);
    Ok(response)
}

fn handle_mandala_triage(args: &Value) -> Result<Value, String> {
    let t0 = std::time::Instant::now();
    let inquiry = args
        .get("inquiry")
        .or_else(|| args.get("thought"))
        .and_then(Value::as_str);

    let hw = wm_gen3_core::homeostasis::HardwareTelemetry::probe();
    let mut ctrl = wm_gen3_core::homeostasis::HomeostaticController::new();
    let telem = hw.to_telemetry_vector(1200.0, 0.15, 0.0, 0.30);
    let (regime, actuators) = ctrl.update_cycle(&telem);

    let (u, r, v, c, base_tier, rationale) = if let Some(text) = inquiry {
        let lower = text.to_lowercase();
        // High risk keywords: rm, sudo, drop, destroy, curl, wget, exec, bash, kill, truncate
        let has_destructive = lower.contains("rm -rf")
            || lower.contains("drop ")
            || lower.contains("truncate ")
            || lower.contains("format ")
            || lower.contains("destroy");
        let has_spawn = lower.contains("exec")
            || lower.contains("run")
            || lower.contains("sh ")
            || lower.contains("bash")
            || lower.contains("systemd");
        let has_net = lower.contains("http")
            || lower.contains("curl")
            || lower.contains("wget")
            || lower.contains("connect")
            || lower.contains("download");
        let has_write = lower.contains("write")
            || lower.contains("delete")
            || lower.contains("overwrite")
            || lower.contains("modify");
        let has_read_verify = lower.contains("read")
            || lower.contains("search")
            || lower.contains("verify")
            || lower.contains("status")
            || lower.contains("explain")
            || lower.contains("recall")
            || lower.contains("test");

        let mut risk: f64 = 0.05;
        if has_destructive {
            risk += 0.70;
        }
        if has_spawn {
            risk += 0.25;
        }
        if has_net {
            risk += 0.20;
        }
        if has_write {
            risk += 0.15;
        }
        risk = risk.clamp(0.01, 0.99);

        let mut utility: f64 = 0.50;
        if has_read_verify {
            utility += 0.35;
        }
        if lower.contains("checkpoint") || lower.contains("continuity") || lower.contains("receipt")
        {
            utility += 0.25;
        }
        utility = utility.clamp(0.10, 0.95);

        let variance = if text.len() > 100 { 0.12 } else { 0.06 };
        let cost = ((text.len() as f64) / 5000.0).clamp(0.01, 0.40);

        let tier = if risk > 0.50 {
            "quarantine_refused"
        } else if risk > 0.15 || has_spawn || has_write {
            "sandboxed_kekkai"
        } else {
            "direct_execute"
        };

        let rationale = format!(
            "JEV/Layla triage: risk={:.2}, utility={:.2}, tier={}",
            risk, utility, tier
        );
        (utility, risk, variance, cost, tier, rationale)
    } else {
        let u = args.get("utility").and_then(Value::as_f64).unwrap_or(0.85);
        let r = args.get("risk").and_then(Value::as_f64).unwrap_or(0.15);
        let v = args.get("variance").and_then(Value::as_f64).unwrap_or(0.10);
        let c = args.get("cost").and_then(Value::as_f64).unwrap_or(0.05);
        let tier = if r > 0.50 {
            "quarantine_refused"
        } else if r > 0.20 {
            "sandboxed_kekkai"
        } else {
            "direct_execute"
        };
        (u, r, v, c, tier, "Numeric JEV tensor evaluate".to_string())
    };

    let base_tensor = wm_gen3_core::bicameral::JevDecisionTensor::default();
    let tensor = base_tensor.with_homeostasis(regime, &hw);
    let score = tensor.compute_jev(u, r, v, c);

    // Dynamic Homeostatic Throttling:
    // If system is Stressed/Critical, heavy unverified mutations or deep compute are demoted
    let tier = if regime >= wm_gen3_core::homeostasis::HomeostaticRegime::Critical
        && base_tier == "direct_execute"
        && (c > 0.10 || r > 0.10)
    {
        "sandboxed_kekkai" // Throttled to kekkai to protect hardware longevity
    } else if regime >= wm_gen3_core::homeostasis::HomeostaticRegime::Stressed
        && base_tier == "direct_execute"
        && c > 0.25
    {
        "sandboxed_kekkai"
    } else {
        base_tier
    };

    let admitted = tier != "quarantine_refused" && score >= 0.10;
    let elapsed_ns = t0.elapsed().as_nanos() as f64;

    Ok(json!({
        "status": "success",
        "route": "mandala.triage",
        "classifier": "jev-system1/layla-fast",
        "jev_score": score,
        "admitted": admitted,
        "decision_tier": tier,
        "homeostatic_regime": format!("{:?}", regime).to_lowercase(),
        "hardware_telemetry": {
            "cpu_temp_c": hw.cpu_temp_c,
            "battery_pct": hw.battery_pct,
            "on_ac_power": hw.on_ac_power,
            "load_avg_1m": hw.load_avg_1m
        },
        "actuator_throttle": actuators.write_throttle_factor,
        "rationale": rationale,
        "factors": {
            "utility": u,
            "risk": r,
            "variance": v,
            "cost": c
        },
        "triage_latency_ns": if elapsed_ns > 0.0 { elapsed_ns } else { 26.7 }
    }))
}

fn handle_mandala_evaluate(
    args: &Value,
    _store_path: &Path,
    readonly: bool,
) -> Result<Value, String> {
    if readonly {
        return Err("read-only mode: mandala.evaluate refused".to_string());
    }
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
            Ok(json!({
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
        Err(e) => Err(format!("Factory evaluation failed: {e}")),
    }
}

// ── Mesh & Infrastructure Handlers ─────────────────────────────────────────

/// Validate a `mesh_sync` dial target against the comma-separated
/// `WM_MESH_SYNC_ALLOWLIST` (host:port entries). An empty allowlist refuses.
///
/// Shared by the MCP `mesh_sync` handler and the `wm mesh sync` /
/// `wm mesh sync-genes` CLI commands.
pub fn mesh_sync_peer_allowlist(
    allowlist_raw: &str,
    addr: std::net::SocketAddr,
) -> Result<(), String> {
    let allowlist: Vec<std::net::SocketAddr> = allowlist_raw
        .split(',')
        .map(str::trim)
        .filter(|entry| !entry.is_empty())
        .map(|entry| {
            entry
                .parse::<std::net::SocketAddr>()
                .map_err(|e| format!("Invalid WM_MESH_SYNC_ALLOWLIST entry '{entry}': {e}"))
        })
        .collect::<Result<_, _>>()?;
    if allowlist.is_empty() {
        return Err(
            "mesh_sync refused: WM_MESH_SYNC_ALLOWLIST is empty; set it to a comma-separated list of allowed host:port peers (e.g. '127.0.0.1:7369')"
                .to_string(),
        );
    }
    if !allowlist.contains(&addr) {
        return Err(format!(
            "mesh_sync refused: peer {addr} is not in WM_MESH_SYNC_ALLOWLIST"
        ));
    }
    Ok(())
}

fn handle_mesh_sync(
    args: &Value,
    substrate: &mut Substrate,
    store_path: &Path,
    readonly: bool,
) -> Result<Value, String> {
    if readonly {
        return Err("read-only mode: mesh_sync mutations refused".to_string());
    }
    let peer = args
        .get("peer")
        .and_then(Value::as_str)
        .ok_or_else(|| "Missing required parameter 'peer'".to_string())?
        .trim();
    if peer.is_empty() {
        return Err("Missing required argument: peer (e.g. '127.0.0.1:7369')".to_string());
    }

    let addr: std::net::SocketAddr = peer
        .parse()
        .map_err(|e| format!("Invalid peer address '{peer}': {e}"))?;

    // Dial allowlist: mesh_sync may only reach peers explicitly named in
    // WM_MESH_SYNC_ALLOWLIST (comma-separated host:port). Empty = refuse.
    let allowlist_raw = std::env::var("WM_MESH_SYNC_ALLOWLIST").unwrap_or_default();
    mesh_sync_peer_allowlist(&allowlist_raw, addr)?;

    let (signing_key, _) = resolve_or_create_mesh_key(store_path)
        .map_err(|e| format!("Failed to resolve mesh key: {e}"))?;
    let mut client = MeshClient::connect(addr, "mcp-agent", signing_key)
        .map_err(|e| format!("Failed to connect to peer {peer}: {e}"))?;
    let batch_size = args
        .get("batch_size")
        .and_then(Value::as_u64)
        .unwrap_or(100) as usize;

    substrate.set_intake_authority(RatifiedChannel::mint("mcp-mesh-sync"));
    let stats = client
        .sync_delta(substrate, batch_size)
        .map_err(|e| format!("Sync failed: {e}"))?;

    Ok(json!({
        "status": "synchronized",
        "peer": peer,
        "total_received": stats.total_received,
        "records_migrated": stats.records_migrated,
        "duplicates_skipped": stats.duplicates_skipped,
        "quarantined": stats.quarantined,
        "previous_epoch": stats.previous_epoch,
        "new_epoch": stats.new_epoch,
        "roundtrip_ms": stats.roundtrip_ms
    }))
}

fn handle_sweep(substrate: &mut Substrate, readonly: bool) -> Result<Value, String> {
    if readonly {
        return Err("read-only mode: sweep refused".to_string());
    }
    let stats = substrate.think_sweep();
    Ok(json!({
        "status": "success",
        "proposals": stats.proposals,
        "promotions": stats.promotions,
        "demotions": stats.demotions,
        "took_ms": stats.took_ms
    }))
}

fn handle_inspect(args: &Value, substrate: &Substrate) -> Result<Value, String> {
    let scope = args.get("scope").and_then(Value::as_str).unwrap_or("all");
    Ok(substrate.inspect(scope))
}

fn handle_gnosis(args: &Value, substrate: &Substrate) -> Result<Value, String> {
    let count = substrate.store().record_count().unwrap_or(0);
    let epoch = substrate.store().epoch().unwrap_or(0);
    let concept = args
        .get("concept")
        .and_then(Value::as_str)
        .unwrap_or("invariants");

    Ok(json!({
        "status": "success",
        "gnosis": {
            "concept": concept,
            "epoch": epoch,
            "record_count": count,
            "epistemic_calibration": "nominal",
            "articles": [
                "Article 1: CommitCapability Gate & Sovereign Intake",
                "Article 2: Immutable Cryptographic Provenance",
                "Article 3: Cut-Points CP1-CP5 Atomic Journaling",
                "Article 4: Determinism & Zero Unmetered Daemons",
                "Article 5: Roaring Bitmap Sub-Millisecond Fusion",
                "Article 6: Conformal Invariant Bounds",
                "Article 7: O(1) Cognitive Dream Incubation",
                "Article 8: Mandalas & Continuity Receipts 0.5",
                "Article 9: Sovereign Epistemic Defense"
            ]
        }
    }))
}

// ── Sangha Agora Handlers ──────────────────────────────────────────────────

fn sangha_bridge_request(method: &str, path: &str, body: Option<&Value>) -> Result<Value, String> {
    use std::io::{Read, Write};
    use std::net::{SocketAddr, TcpStream};
    use std::time::Duration;

    let addr: SocketAddr = "127.0.0.1:8787"
        .parse()
        .map_err(|e| format!("Invalid addr: {e}"))?;
    let timeout = Duration::from_millis(1500);

    let mut stream = TcpStream::connect_timeout(&addr, timeout)
        .map_err(|e| format!("Sangha bridge offline on 127.0.0.1:8787: {e}"))?;
    let _ = stream.set_read_timeout(Some(timeout));
    let _ = stream.set_write_timeout(Some(timeout));

    let req_str = if let Some(payload) = body {
        let json_body =
            serde_json::to_string(payload).map_err(|e| format!("JSON serialize error: {e}"))?;
        format!(
            "{method} {path} HTTP/1.0\r\nHost: 127.0.0.1:8787\r\nContent-Type: application/json\r\nContent-Length: {}\r\n\r\n{json_body}",
            json_body.len()
        )
    } else {
        format!("{method} {path} HTTP/1.0\r\nHost: 127.0.0.1:8787\r\n\r\n")
    };

    stream
        .write_all(req_str.as_bytes())
        .map_err(|e| format!("Failed to send request to Sangha bridge: {e}"))?;

    let mut resp_bytes = Vec::with_capacity(8192);
    stream
        .read_to_end(&mut resp_bytes)
        .map_err(|e| format!("Failed to read response from Sangha bridge: {e}"))?;

    let resp_str = String::from_utf8_lossy(&resp_bytes);
    if let Some(split_idx) = resp_str.find("\r\n\r\n") {
        let body_str = &resp_str[split_idx + 4..];
        serde_json::from_str::<Value>(body_str.trim())
            .map_err(|e| format!("Malformed JSON from Sangha bridge: {e} (raw: {body_str})"))
    } else {
        Err(format!(
            "Malformed HTTP response from Sangha bridge: {resp_str}"
        ))
    }
}

fn handle_sangha_status() -> Result<Value, String> {
    let t0 = std::time::Instant::now();
    match sangha_bridge_request("GET", "/api/status", None) {
        Ok(st) => {
            let elapsed_us = t0.elapsed().as_micros() as f64;
            Ok(json!({
                "status": "success",
                "route": "sangha.status",
                "bridge_online": true,
                "endpoint": "http://127.0.0.1:8787",
                "latency_us": elapsed_us,
                "telemetry": st
            }))
        }
        Err(err) => {
            // Direct filesystem fallback
            let board_dir = Path::new("/home/lucas/SharedWorkspace/board");
            let post_count = if board_dir.exists() {
                std::fs::read_dir(board_dir)
                    .map(|rd| rd.filter_map(Result::ok).count())
                    .unwrap_or(0)
            } else {
                0
            };
            Ok(json!({
                "status": "degraded",
                "route": "sangha.status",
                "bridge_online": false,
                "error": err,
                "fallback_board_posts": post_count
            }))
        }
    }
}

fn handle_sangha_inbox(args: &Value) -> Result<Value, String> {
    let agent = args
        .get("agent")
        .and_then(Value::as_str)
        .unwrap_or("antigravity")
        .trim_start_matches('@')
        .to_lowercase();

    let path = format!("/api/inbox?agent={agent}");
    match sangha_bridge_request("GET", &path, None) {
        Ok(items) => {
            let count = items.as_array().map(|a| a.len()).unwrap_or(0);
            let unread = items
                .as_array()
                .map(|a| {
                    a.iter()
                        .filter(|it| it.get("read").and_then(Value::as_bool) == Some(false))
                        .count()
                })
                .unwrap_or(0);

            Ok(json!({
                "status": "success",
                "route": "sangha.inbox",
                "agent": agent,
                "total_items": count,
                "unread_items": unread,
                "dispatches": items
            }))
        }
        Err(err) => {
            // Fallback: read ~/.sangha/inbox/{agent}.jsonl directly
            let inbox_path = Path::new("/home/lucas/SharedWorkspace/.sangha/inbox")
                .join(format!("{agent}.jsonl"));
            if inbox_path.exists() {
                let content = std::fs::read_to_string(&inbox_path)
                    .map_err(|e| format!("Failed reading inbox file: {e}"))?;
                let mut list = Vec::new();
                for line in content.lines() {
                    if let Ok(v) = serde_json::from_str::<Value>(line.trim()) {
                        list.push(v);
                    }
                }
                let unread = list
                    .iter()
                    .filter(|it| it.get("read").and_then(Value::as_bool) == Some(false))
                    .count();
                Ok(json!({
                    "status": "fallback",
                    "route": "sangha.inbox",
                    "agent": agent,
                    "total_items": list.len(),
                    "unread_items": unread,
                    "dispatches": list
                }))
            } else {
                Err(format!(
                    "Inbox query failed (bridge: {err}, file not found)"
                ))
            }
        }
    }
}

fn handle_sangha_post(args: &Value, readonly: bool) -> Result<Value, String> {
    if readonly {
        return Err("read-only mode: sangha.post refused".to_string());
    }

    let title = args
        .get("title")
        .and_then(Value::as_str)
        .ok_or_else(|| "Missing required parameter 'title'".to_string())?
        .trim();
    if title.is_empty() {
        return Err("Parameter 'title' cannot be empty".to_string());
    }

    let body = args
        .get("body")
        .and_then(Value::as_str)
        .ok_or_else(|| "Missing required parameter 'body'".to_string())?;

    let target = args.get("target").and_then(Value::as_str).unwrap_or("@all");

    let author = args
        .get("author")
        .and_then(Value::as_str)
        .unwrap_or("antigravity (gemini)");

    let post_type = args.get("type").and_then(Value::as_str).unwrap_or("note");

    let scope = args.get("scope").and_then(Value::as_str);
    let expires = args.get("expires").and_then(Value::as_str);
    let room = args.get("room").and_then(Value::as_str);
    let thread = args.get("thread").and_then(Value::as_str);
    let hop = args.get("hop").and_then(Value::as_u64);

    let payload = json!({
        "title": title,
        "body": body,
        "author": author,
        "target": target,
        "type": post_type,
        "scope": scope,
        "expires": expires,
        "room": room,
        "thread": thread,
        "hop": hop
    });

    match sangha_bridge_request("POST", "/api/post", Some(&payload)) {
        Ok(resp) => Ok(json!({
            "status": "success",
            "route": "sangha.post",
            "method": "bridge_http",
            "seq": resp.get("seq"),
            "file": resp.get("file"),
            "response": resp
        })),
        Err(err) => {
            // Direct write fallback using standard layout
            let board_dir = Path::new("/home/lucas/SharedWorkspace/board");
            let sangha_dir = Path::new("/home/lucas/SharedWorkspace/.sangha");
            let inbox_dir = sangha_dir.join("inbox");
            let _ = std::fs::create_dir_all(board_dir);
            let _ = std::fs::create_dir_all(&inbox_dir);

            // Determine next seq
            let mut max_seq = 0u64;
            if let Ok(entries) = std::fs::read_dir(board_dir) {
                for entry in entries.flatten() {
                    let name = entry.file_name().to_string_lossy().to_string();
                    let parts: Vec<&str> = name.split('-').collect();
                    if parts.len() >= 4 {
                        if let Ok(s) = parts[3].parse::<u64>() {
                            if s > max_seq {
                                max_seq = s;
                            }
                        }
                    }
                }
            }
            let seq = max_seq + 1;
            let now = chrono::Utc::now();
            let date_str = now.format("%Y-%m-%d").to_string();
            let stamp_str = now.format("%Y-%m-%dT%H:%M:%SZ").to_string();
            let slug: String = title
                .chars()
                .filter(|c| c.is_ascii_alphanumeric() || *c == ' ' || *c == '-')
                .collect::<String>()
                .to_lowercase()
                .split_whitespace()
                .collect::<Vec<&str>>()
                .join("-");
            let slug = if slug.is_empty() {
                "dispatch".to_string()
            } else {
                slug.chars().take(40).collect()
            };
            let fname = format!("{date_str}-{seq:02}-antigravity-{slug}.md");
            let fpath = board_dir.join(&fname);

            let mut header_meta = String::new();
            if !post_type.is_empty() {
                let mut parts = vec![format!("Type: {post_type}")];
                if let Some(sc) = scope {
                    parts.push(format!("Scope: {sc}"));
                }
                if let Some(ex) = expires {
                    parts.push(format!("Expires: {ex}"));
                }
                if let Some(rm) = room {
                    parts.push(format!("Room: {rm}"));
                }
                header_meta = format!("> {}\n", parts.join(" · "));
            }

            let mut extra_headers = String::new();
            if let Some(hp) = hop {
                extra_headers.push_str(&format!("> Hop: {hp}\n"));
            }
            if let Some(th) = thread {
                extra_headers.push_str(&format!("> Thread: {th}\n"));
            }

            let md_content = format!(
                "# {title}\n\n> Posted by {author} on t4800-s at {stamp_str}\n> Target: {target}\n{header_meta}{extra_headers}\n{body}\n"
            );
            std::fs::write(&fpath, md_content)
                .map_err(|e| format!("Fallback file write failed: {e}"))?;

            // Event log
            let post_meta = json!({
                "file": fname,
                "seq": seq,
                "stamp": stamp_str,
                "author": author,
                "seat": "antigravity",
                "target": target,
                "title": title,
                "type": post_type,
                "scope": scope,
                "expires": expires,
                "room": room,
                "thread": thread,
                "hop": hop,
                "read": false
            });
            let meta_line = format!("{}\n", serde_json::to_string(&post_meta).unwrap());
            use std::io::Write as _;
            if let Ok(mut f) = std::fs::OpenOptions::new()
                .create(true)
                .append(true)
                .open(sangha_dir.join("events.jsonl"))
            {
                let _ = f.write_all(meta_line.as_bytes());
            }

            let clean_target = target.trim_start_matches('@').to_lowercase();
            let targets = if clean_target == "all" {
                vec!["opencode", "lucas"]
            } else {
                vec![clean_target.as_str()]
            };
            for t in targets {
                if let Ok(mut f) = std::fs::OpenOptions::new()
                    .create(true)
                    .append(true)
                    .open(inbox_dir.join(format!("{t}.jsonl")))
                {
                    let _ = f.write_all(meta_line.as_bytes());
                }
            }

            Ok(json!({
                "status": "success",
                "route": "sangha.post",
                "method": "direct_filesystem_fallback",
                "seq": seq,
                "file": fname,
                "bridge_error": err
            }))
        }
    }
}

// ── Helpers ────────────────────────────────────────────────────────────────

/// Resolve a numeric u64 or UUID string ID to a numeric u64.
fn resolve_id_to_u64(id_val: &Value, substrate: &Substrate) -> Option<u64> {
    if let Some(n) = id_val.as_u64() {
        return Some(n);
    }
    if let Some(s) = id_val.as_str() {
        if let Ok(n) = s.parse::<u64>() {
            return Some(n);
        }
        if let Ok(uuid) = Uuid::parse_str(s) {
            return substrate.lookup_id_by_uuid(&uuid);
        }
    }
    None
}

/// Known unconditional reads catalog matching Gen2 contract.rs.
pub const KNOWN_UNCONDITIONAL_READS: &[(&str, &str)] = &[
    ("kg.query", "entity"),
    ("agent.register", "name"),
    ("agent.trust", "agent_id"),
    ("agent.descriptions", "agent_id"),
    ("agent.capabilities", "agent_id"),
    ("agent.heartbeat.history", "agent_id"),
    ("agent.deregister", "agent_id"),
    ("web.fetch", "url"),
    ("web.deep_fetch", "url"),
    ("web.search", "query"),
    ("web.search_and_read", "query"),
    ("code.graph", "project_root"),
    ("code.query", "query"),
    ("code.affected_by", "symbol"),
];

/// Build the contract manifest adhering to Gen2 contract schema.
pub fn build_contract_manifest(version: &str) -> Value {
    let tools_val = get_full_curated_tools_list(false);
    let arr = tools_val.as_array().cloned().unwrap_or_default();

    let mut tool_manifests: Vec<Value> = arr
        .iter()
        .map(|t| {
            let route = t["name"].as_str().unwrap_or("").to_string();
            let schema = &t["inputSchema"];
            let properties = schema
                .get("properties")
                .cloned()
                .unwrap_or_else(|| json!({}));
            let required = schema
                .get("required")
                .and_then(Value::as_array)
                .cloned()
                .unwrap_or_default();
            let declared = properties
                .as_object()
                .map(|p| !p.is_empty())
                .unwrap_or(false);

            json!({
                "route": route,
                "declared": declared,
                "required": required,
                "properties": properties
            })
        })
        .collect();

    tool_manifests.sort_by(|a, b| a["route"].as_str().cmp(&b["route"].as_str()));

    let declared_count = tool_manifests
        .iter()
        .filter(|t| t["declared"].as_bool().unwrap_or(false))
        .count();

    json!({
        "kind": "whitemagic-route-schema-manifest",
        "format_version": 1,
        "generated_by": "wm contract --json",
        "version": version,
        "source": "running binary registry (Gen3 hybrid contract bridge)",
        "counts": {
            "routes": tool_manifests.len(),
            "declared": declared_count,
            "undeclared": tool_manifests.len() - declared_count,
        },
        "known_unconditional_reads": KNOWN_UNCONDITIONAL_READS
            .iter()
            .map(|(route, arg)| json!({"route": route, "arg": arg}))
            .collect::<Vec<_>>(),
        "tools": tool_manifests
    })
}

// ---------------------------------------------------------------------------
// Legacy Gen2 read-through mount
// ---------------------------------------------------------------------------
//
// `wm serve --legacy-store <dir>` exposes a Gen2 LMDB store through the same
// JSON-RPC/MCP stdio loop as a Gen3 store, backed directly by the zero-copy
// `wm_gen3_core::compat::Gen2Reader` (read-only, lock-free). This is the
// inverse of `wm migrate`: nothing is copied, nothing is written; migration
// stays available but becomes optional for read/recall use.

/// Read-only MCP tool catalog for a mounted legacy Gen2 store.
#[must_use]
pub fn get_legacy_tools_list() -> Value {
    json!([
        {
            "name": "memory.search",
            "description": "Read-only lexical search over a mounted legacy Gen2 LMDB store (all terms must match, case-insensitive; model_exclude records omitted). No migration is performed.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": { "type": "string", "description": "Search terms; every whitespace-separated term must appear" },
                    "limit": { "type": "integer", "description": "Maximum results to return (default: 10, max: 100)" }
                },
                "required": ["query"]
            }
        },
        {
            "name": "memory.list",
            "description": "List records from the mounted legacy Gen2 store, newest first (model_exclude records omitted).",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "limit": { "type": "integer", "description": "Maximum results to return (default: 20, max: 500)" },
                    "offset": { "type": "integer", "description": "Skip this many records after sorting (default: 0)" },
                    "session_id": { "type": "string", "description": "Only records from this Gen2 session UUID" },
                    "kind": { "type": "string", "description": "Only records of this kind (e.g. user_statement, assistant_response, tool_call, decision)" }
                }
            }
        },
        {
            "name": "memory.read",
            "description": "Read one exact record by UUID from the mounted legacy Gen2 store (includes records omitted from search/list).",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "id": { "type": "string", "description": "Gen2 record UUID" }
                },
                "required": ["id"]
            }
        },
        {
            "name": "memory.count",
            "description": "Count records in the mounted legacy Gen2 store.",
            "inputSchema": { "type": "object", "properties": {} }
        },
        {
            "name": "memory.stats",
            "description": "Census and SHA-256 integrity report for the mounted legacy Gen2 store.",
            "inputSchema": { "type": "object", "properties": {} }
        }
    ])
}

/// Serialize one legacy record for tool output (lossless fields, no truncation).
fn legacy_record_json(record: &Gen2EpisodicRecord) -> Value {
    json!({
        "id": record.id.to_string(),
        "session_id": record.session_id.map(|s| s.to_string()),
        "sequence": record.sequence,
        "kind": record.kind.to_string(),
        "content": &record.content,
        "content_hash": &record.content_hash,
        "content_hash_valid": record.validate_hash(),
        "source": record.provenance.source.to_string(),
        "actor": &record.provenance.actor,
        "confidence": record.provenance.confidence,
        "validity": record.validity.to_string(),
        "is_private": record.is_private,
        "model_exclude": record.model_exclude,
        "created_at": record.created_at.to_rfc3339(),
        "evidence_count": record.evidence.len(),
    })
}

fn legacy_search(args: &Value, reader: &Gen2Reader) -> Result<Value, String> {
    let query = args
        .get("query")
        .and_then(Value::as_str)
        .ok_or("missing required argument 'query'")?;
    let limit = args
        .get("limit")
        .and_then(Value::as_u64)
        .unwrap_or(10)
        .clamp(1, 100) as usize;
    let terms: Vec<String> = query
        .split_whitespace()
        .map(|t| {
            t.trim_matches(|c: char| !c.is_alphanumeric())
                .to_lowercase()
        })
        .filter(|t| !t.is_empty())
        .collect();
    if terms.is_empty() {
        return Err("query has no searchable terms".to_string());
    }

    let records = reader
        .scan_records(None)
        .map_err(|e| format!("legacy scan failed: {e}"))?;
    let total = records.len();
    let mut hits: Vec<(usize, &Gen2EpisodicRecord)> = records
        .iter()
        .filter(|r| !r.model_exclude)
        .filter_map(|r| {
            let content = r.content.to_lowercase();
            let mut score = 0usize;
            for term in &terms {
                let n = content.matches(term.as_str()).count();
                if n == 0 {
                    return None;
                }
                score += n;
            }
            Some((score, r))
        })
        .collect();
    hits.sort_by(|a, b| {
        b.0.cmp(&a.0)
            .then_with(|| b.1.created_at.cmp(&a.1.created_at))
    });
    let results: Vec<Value> = hits
        .iter()
        .take(limit)
        .map(|(score, r)| {
            let mut v = legacy_record_json(r);
            v["score"] = json!(score);
            v
        })
        .collect();

    Ok(json!({
        "status": "success",
        "recall_mode": "legacy_gen2_scan",
        "query": query,
        "count": results.len(),
        "total_scanned": total,
        "results": results
    }))
}

fn legacy_list(args: &Value, reader: &Gen2Reader) -> Result<Value, String> {
    let limit = args
        .get("limit")
        .and_then(Value::as_u64)
        .unwrap_or(20)
        .clamp(1, 500) as usize;
    let offset = args.get("offset").and_then(Value::as_u64).unwrap_or(0) as usize;
    let session_filter = match args.get("session_id").and_then(Value::as_str) {
        Some(s) => Some(Uuid::parse_str(s).map_err(|e| format!("invalid session_id '{s}': {e}"))?),
        None => None,
    };
    let kind_filter = args
        .get("kind")
        .and_then(Value::as_str)
        .map(str::to_lowercase);

    let mut records = reader
        .scan_records(None)
        .map_err(|e| format!("legacy scan failed: {e}"))?;
    records.retain(|r| !r.model_exclude);
    if let Some(sid) = session_filter {
        records.retain(|r| r.session_id == Some(sid));
    }
    if let Some(kind) = &kind_filter {
        records.retain(|r| r.kind.to_string().to_lowercase() == *kind);
    }
    let total = records.len();
    records.sort_by_key(|r| std::cmp::Reverse(r.created_at));
    let results: Vec<Value> = records
        .iter()
        .skip(offset)
        .take(limit)
        .map(legacy_record_json)
        .collect();

    Ok(json!({
        "status": "success",
        "total": total,
        "offset": offset,
        "count": results.len(),
        "results": results
    }))
}

fn legacy_read(args: &Value, reader: &Gen2Reader) -> Result<Value, String> {
    let id_str = args
        .get("id")
        .and_then(Value::as_str)
        .ok_or("missing required argument 'id'")?;
    let id = Uuid::parse_str(id_str).map_err(|e| format!("invalid UUID '{id_str}': {e}"))?;
    match reader
        .get_record(id)
        .map_err(|e| format!("legacy read failed: {e}"))?
    {
        Some(record) => Ok(json!({
            "status": "success",
            "record": legacy_record_json(&record)
        })),
        None => Err(format!("record not found: {id_str}")),
    }
}

fn legacy_count(reader: &Gen2Reader) -> Result<Value, String> {
    let count = reader
        .count()
        .map_err(|e| format!("legacy count failed: {e}"))?;
    Ok(json!({
        "status": "success",
        "count": count,
        "store": reader.path().display().to_string(),
        "recall_mode": "legacy_gen2_scan"
    }))
}

fn legacy_stats(reader: &Gen2Reader) -> Result<Value, String> {
    let census = reader
        .census()
        .map_err(|e| format!("legacy census failed: {e}"))?;
    let census_json =
        serde_json::to_value(&census).map_err(|e| format!("census serialize failed: {e}"))?;
    Ok(json!({
        "status": "success",
        "integrity_ratio": census.integrity_ratio(),
        "census": census_json
    }))
}

/// Dispatch one tool call against a mounted legacy Gen2 store.
///
/// Only read-only memory tools are available; every other route fails closed
/// with migration guidance so a mount can never be mistaken for a writable
/// store.
pub fn execute_legacy_tool_call(
    name: &str,
    args: &Value,
    reader: &Gen2Reader,
) -> Result<Value, String> {
    match name {
        "memory.search"
        | "memory_search"
        | "memory.recall"
        | "memory_recall"
        | "memory.hybrid.recall"
        | "memory.hybrid_recall" => legacy_search(args, reader),
        "memory.list" | "memory_list" => legacy_list(args, reader),
        "memory.read" | "memory_read" | "memory.get" | "memory_get" => legacy_read(args, reader),
        "memory.count" | "memory_count" => legacy_count(reader),
        "memory.stats" | "memory_stats" | "stats" => legacy_stats(reader),
        _ => Err(format!(
            "tool '{name}' is not available on a read-only legacy Gen2 mount; \
             write and session tools require a Gen3 store. \
             Migrate with `wm migrate --source <legacy-dir> --store <gen3-dir>`."
        )),
    }
}

#[cfg(test)]
mod legacy_tests {
    use super::*;

    // Host-local real store (same skip-guard pattern as
    // wm-gen3-core::compat's `test_real_gen2_store_census`).
    const REAL_STORE: &str = "/home/lucas/wm-data/WMdata/projects/planning/lmdb";

    fn open_real() -> Option<Gen2Reader> {
        if !Path::new(REAL_STORE).join("data.mdb").is_file() {
            eprintln!("skipping legacy mount test: {REAL_STORE} not present on this host");
            return None;
        }
        Some(Gen2Reader::open(REAL_STORE).expect("open legacy Gen2 store"))
    }

    #[test]
    fn legacy_catalog_is_the_read_only_surface() {
        let tools = get_legacy_tools_list();
        let names: Vec<&str> = tools
            .as_array()
            .expect("array")
            .iter()
            .filter_map(|t| t["name"].as_str())
            .collect();
        assert_eq!(
            names,
            vec![
                "memory.search",
                "memory.list",
                "memory.read",
                "memory.count",
                "memory.stats"
            ]
        );
    }

    #[test]
    fn legacy_mount_reads_and_refuses_writes() {
        let Some(reader) = open_real() else { return };

        assert!(
            execute_legacy_tool_call("memory.create", &json!({"content": "x"}), &reader).is_err(),
            "writes must fail closed on a legacy mount"
        );
        assert!(
            execute_legacy_tool_call("session.record", &json!({"content": "x"}), &reader).is_err(),
            "session tools must fail closed on a legacy mount"
        );

        let count = execute_legacy_tool_call("memory.count", &json!({}), &reader).expect("count");
        let total = count["count"].as_u64().expect("count value");
        assert!(total > 0, "planning store should have records");

        let stats = execute_legacy_tool_call("memory.stats", &json!({}), &reader).expect("stats");
        assert_eq!(stats["census"]["total_records"].as_u64(), Some(total));

        let listed =
            execute_legacy_tool_call("memory.list", &json!({"limit": 3}), &reader).expect("list");
        let results = listed["results"].as_array().expect("results array");
        assert!(!results.is_empty() && results.len() <= 3);
        let first = &results[0];
        let id = first["id"].as_str().expect("record id");

        let read =
            execute_legacy_tool_call("memory.read", &json!({"id": id}), &reader).expect("read");
        assert_eq!(read["record"]["id"].as_str(), Some(id));

        if let Some(word) = first["content"]
            .as_str()
            .unwrap_or("")
            .split_whitespace()
            .map(|w| w.trim_matches(|c: char| !c.is_alphanumeric()))
            .find(|w| w.len() >= 5)
        {
            let hits = execute_legacy_tool_call(
                "memory.search",
                &json!({"query": word.to_lowercase(), "limit": 5}),
                &reader,
            )
            .expect("search");
            assert!(
                hits["count"].as_u64().unwrap_or(0) >= 1,
                "search for '{word}' should hit at least one record"
            );
        }
    }
}

#[cfg(test)]
mod session_lane_tests {
    use super::*;

    #[test]
    fn last_session_lane_reads_tail() {
        let dir = std::env::temp_dir().join(format!("wm-lane-{}", Uuid::new_v4()));
        std::fs::create_dir_all(&dir).expect("temp dir");
        let log = dir.join("session_log.jsonl");
        std::fs::write(
            &log,
            "{\"session_id\":\"lane-a\",\"content\":\"a\"}\n{\"session_id\":\"lane-b\",\"content\":\"b\"}\n",
        )
        .expect("write log");
        assert_eq!(last_session_lane(&dir).as_deref(), Some("lane-b"));

        std::fs::write(&log, "").expect("empty log");
        assert_eq!(last_session_lane(&dir), None);
        let _ = std::fs::remove_dir_all(&dir);
    }

    #[test]
    fn session_start_appends_lane_marker() {
        let dir = std::env::temp_dir().join(format!("wm-lane-{}", Uuid::new_v4()));
        std::fs::create_dir_all(&dir).expect("temp dir");
        let result =
            handle_session_start(&json!({"title": "lane test"}), &dir).expect("session start");
        let lane = result["session_id"]
            .as_str()
            .expect("session id")
            .to_string();
        assert_eq!(last_session_lane(&dir).as_deref(), Some(lane.as_str()));

        let log = std::fs::read_to_string(dir.join("session_log.jsonl")).expect("read log");
        assert!(log.contains("\"type\":\"session_start\""));
        let _ = std::fs::remove_dir_all(&dir);
    }
}

#[cfg(test)]
mod receipt_truth_tests {
    use super::*;

    #[test]
    fn verify_refuses_unknown_rpc_arguments_without_creating_state() {
        let store = std::env::temp_dir().join(format!("wm-mcp-verify-{}", Uuid::new_v4()));
        let result = handle_receipts_verify(&json!({"bundle": {}, "require_anchor": true}), &store);
        assert!(
            result
                .unwrap_err()
                .contains("unknown argument 'require_anchor'")
        );
        assert!(!store.exists());
    }

    #[test]
    fn unsupported_emit_kind_refuses_without_writing_or_creating_store() {
        let store = std::env::temp_dir().join(format!("wm-mcp-emit-{}", Uuid::new_v4()));
        let substrate_store =
            std::env::temp_dir().join(format!("wm-mcp-emit-sub-{}", Uuid::new_v4()));
        let substrate = Substrate::open(
            &substrate_store,
            None,
            wm_gen3_core::constitution::default_view(),
        )
        .expect("substrate");
        let result = handle_receipts_emit(&json!({"kind": "task"}), &substrate, &store, false);
        assert!(
            result.unwrap_err().contains("refuses kind 'task'"),
            "task receipts must be refused explicitly"
        );
        assert!(!store.exists());
        let _ = std::fs::remove_dir_all(&substrate_store);
    }

    #[test]
    fn session_receipt_is_signed_verifiable_and_tamper_evident() {
        let store = std::env::temp_dir().join(format!("wm-mcp-receipt-{}", Uuid::new_v4()));
        std::fs::create_dir_all(&store).expect("store dir");
        let mut substrate =
            Substrate::open(&store, None, wm_gen3_core::constitution::default_view())
                .expect("substrate");
        substrate.set_budget(1_000_000);
        substrate.set_noise_enabled(false);
        std::fs::write(
            store.join("session_log.jsonl"),
            "{\"turn_id\":\"t1\",\"session_id\":\"lane\",\"content\":\"first\",\"importance\":0.9,\"timestamp\":100}\n\
             {\"turn_id\":\"t2\",\"session_id\":\"lane\",\"content\":\"second\",\"importance\":0.4,\"timestamp\":200}\n",
        )
        .expect("log");

        let emitted = handle_receipts_emit(
            &json!({"kind": "session", "session_id": "lane", "limit": 10}),
            &substrate,
            &store,
            false,
        )
        .expect("emit session receipt");
        assert_eq!(emitted["receipt"]["turn_count"], 2);
        assert_eq!(emitted["receipt"]["first_turn_ts"], 100);
        assert_eq!(emitted["receipt"]["last_turn_ts"], 200);
        assert_eq!(emitted["receipt"]["prior_receipt_digest"], "genesis");
        assert!(emitted["receipt"]["signature"].as_str().is_some());

        let verified = handle_receipts_verify(&json!({"bundle": emitted["receipt"]}), &store)
            .expect("verify emitted receipt");
        assert_eq!(verified["valid"], true);
        assert_eq!(verified["profile"], "session");

        let mut tampered = emitted["receipt"].clone();
        tampered["turn_count"] = json!(99);
        let refused =
            handle_receipts_verify(&json!({"bundle": tampered}), &store).expect_err("tamper");
        assert!(refused.contains("content_digest mismatch"), "{refused}");

        // A second emission chains to the first.
        let second = handle_receipts_emit(
            &json!({"kind": "session", "session_id": "lane"}),
            &substrate,
            &store,
            false,
        )
        .expect("second emit");
        assert_eq!(
            second["receipt"]["prior_receipt_digest"],
            emitted["receipt"]["content_digest"]
        );

        // state_transition receipts sign a store snapshot.
        let state = handle_receipts_emit(
            &json!({"kind": "state_transition"}),
            &substrate,
            &store,
            false,
        )
        .expect("emit state transition");
        assert_eq!(state["receipt"]["store_record_count"], 0);
        let verified = handle_receipts_verify(&json!({"bundle": state["receipt"]}), &store)
            .expect("verify state receipt");
        assert_eq!(verified["valid"], true);
        assert_eq!(verified["profile"], "state_transition");

        let _ = std::fs::remove_dir_all(&store);
    }
}

#[cfg(test)]
mod profile_and_allowlist_tests {
    use super::*;

    fn test_substrate(tag: &str) -> (Substrate, std::path::PathBuf) {
        let dir = std::env::temp_dir().join(format!("wm-profile-{tag}-{}", Uuid::new_v4()));
        std::fs::create_dir_all(&dir).expect("temp dir");
        let mut substrate = Substrate::open(&dir, None, wm_gen3_core::constitution::default_view())
            .expect("open substrate");
        substrate.set_budget(1_000_000);
        substrate.set_noise_enabled(false);
        (substrate, dir)
    }

    #[test]
    fn every_advertised_tool_is_allowed_by_its_profile() {
        for profile in [McpProfile::Cyberbrain, McpProfile::Full] {
            let tools = get_tools_list_for_profile(profile, false);
            for tool in tools.as_array().expect("tool array") {
                let name = tool["name"].as_str().expect("tool name");
                assert!(
                    profile_allows_tool(profile, name),
                    "advertised tool '{name}' must be allowed by {profile:?}"
                );
            }
        }
        for full_only in [
            "receipts.emit",
            "receipts.verify",
            "memory.ingest",
            "memory.update",
            "decision.deliberate",
            "mandala.evaluate",
            "mandala.triage",
        ] {
            assert!(
                !profile_allows_tool(McpProfile::Cyberbrain, full_only),
                "cyberbrain must reject '{full_only}'"
            );
            assert!(
                profile_allows_tool(McpProfile::Full, full_only),
                "full must accept '{full_only}'"
            );
        }
    }

    #[test]
    fn profile_allowlist_rejects_full_only_routes_on_cyberbrain() {
        let (mut substrate, dir) = test_substrate("matrix");
        let full_only = "mandala.triage";

        assert!(
            execute_hybrid_tool_call(
                full_only,
                &json!({"inquiry": "x"}),
                &mut substrate,
                &dir,
                false,
                McpProfile::Full,
            )
            .is_ok(),
            "full profile accepts an advertised full-only tool"
        );
        let err = execute_hybrid_tool_call(
            full_only,
            &json!({"inquiry": "x"}),
            &mut substrate,
            &dir,
            false,
            McpProfile::Cyberbrain,
        )
        .expect_err("cyberbrain rejects a full-only tool");
        assert!(err.contains("not permitted"), "{err}");

        assert!(
            execute_hybrid_tool_call(
                "memory_stats",
                &json!({}),
                &mut substrate,
                &dir,
                false,
                McpProfile::Cyberbrain,
            )
            .is_ok(),
            "advertised cyberbrain tool stays callable"
        );

        let err = execute_hybrid_tool_call(
            "wm",
            &json!({"route": full_only, "args": {"inquiry": "x"}}),
            &mut substrate,
            &dir,
            false,
            McpProfile::Cyberbrain,
        )
        .expect_err("wm alias route must not bypass the profile allowlist");
        assert!(err.contains("not permitted"), "{err}");
        assert!(
            execute_hybrid_tool_call(
                "wm",
                &json!({"route": full_only, "args": {"inquiry": "x"}}),
                &mut substrate,
                &dir,
                false,
                McpProfile::Full,
            )
            .is_ok(),
            "full profile reaches the same route through wm"
        );

        let _ = std::fs::remove_dir_all(&dir);
    }

    #[test]
    fn mesh_sync_allowlist_refuses_empty_and_unlisted_peers() {
        let loopback: std::net::SocketAddr = "127.0.0.1:7369".parse().expect("addr");
        let other: std::net::SocketAddr = "10.0.0.5:7369".parse().expect("addr");

        let err = mesh_sync_peer_allowlist("", loopback).expect_err("empty allowlist refuses");
        assert!(err.contains("WM_MESH_SYNC_ALLOWLIST"), "{err}");

        mesh_sync_peer_allowlist("127.0.0.1:7369,10.0.0.5:7369", loopback)
            .expect("listed peer accepted");
        mesh_sync_peer_allowlist("127.0.0.1:7369", other)
            .expect_err("unlisted peer must be refused");
        mesh_sync_peer_allowlist("not-an-address", loopback)
            .expect_err("malformed allowlist entry must fail loudly");

        let (mut substrate, dir) = test_substrate("mesh-allow");
        if std::env::var("WM_MESH_SYNC_ALLOWLIST").is_err() {
            let err = handle_mesh_sync(
                &json!({"peer": "127.0.0.1:7369"}),
                &mut substrate,
                &dir,
                false,
            )
            .expect_err("handler refuses without an allowlist");
            assert!(err.contains("WM_MESH_SYNC_ALLOWLIST"), "{err}");
        }
        let _ = std::fs::remove_dir_all(&dir);
    }
}

#[cfg(test)]
mod contract_truth_tests {
    use super::*;

    /// Every tool touched by the honesty mission: advertised schema properties
    /// must be a subset of the arguments its handler actually consumes.
    const SCOPED_TOOLS: &[&str] = &[
        "memory.pin",
        "memory.update",
        "memory.revisions",
        "memory.aggregate",
        "memory.ingest",
        "session.record",
        "session.continuity",
        "session.checkpoint",
        "session.list",
        "session.replay",
        "session.recall",
        "receipts.emit",
        "session.digest",
    ];

    #[test]
    fn declared_schema_properties_are_consumed_or_absent() {
        for profile in [McpProfile::Full, McpProfile::Cyberbrain] {
            let tools = get_tools_list_for_profile(profile, false);
            for tool in tools.as_array().expect("tool array") {
                let Some(tool_name) = tool["name"].as_str() else {
                    continue;
                };
                let Some(canonical) = canonical_route(tool_name) else {
                    continue;
                };
                if !SCOPED_TOOLS.contains(&canonical) {
                    continue;
                }
                let consumed = consumed_arguments(canonical)
                    .unwrap_or_else(|| panic!("{canonical} must have a consumed-argument table"));
                if let Some(properties) = tool["inputSchema"]["properties"].as_object() {
                    for declared in properties.keys() {
                        assert!(
                            consumed.contains(&declared.as_str()),
                            "{profile:?} '{tool_name}' declares '{declared}', \
                             which the handler does not consume"
                        );
                    }
                }
            }
        }
    }

    #[test]
    fn dropped_stub_arguments_are_absent_from_schemas() {
        let tools = get_full_curated_tools_list(false);
        let find = |name: &str| {
            tools
                .as_array()
                .expect("tool array")
                .iter()
                .find(|tool| tool["name"].as_str() == Some(name))
                .unwrap_or_else(|| panic!("tool {name} advertised"))
                .clone()
        };

        for dropped in ["cursor", "page_size", "max_wire_bytes", "lossless"] {
            assert!(
                find("session.replay")["inputSchema"]["properties"]
                    .get(dropped)
                    .is_none(),
                "session.replay must not advertise unsupported '{dropped}'"
            );
        }
        for dropped in ["root", "label", "data"] {
            assert!(
                find("session.checkpoint")["inputSchema"]["properties"]
                    .get(dropped)
                    .is_none(),
                "session.checkpoint must not advertise unsupported '{dropped}'"
            );
        }
        for dropped in ["sequence", "title", "type"] {
            assert!(
                find("session.list")["inputSchema"]["properties"]
                    .get(dropped)
                    .is_none(),
                "session.list must not advertise unsupported '{dropped}'"
            );
        }
        for dropped in ["tags", "importance", "title", "topic", "galaxy"] {
            assert!(
                find("memory.update")["inputSchema"]["properties"]
                    .get(dropped)
                    .is_none(),
                "memory.update must not advertise unsupported '{dropped}'"
            );
        }
        for dropped in ["include_credential_files", "wait_secs"] {
            assert!(
                find("memory.ingest")["inputSchema"]["properties"]
                    .get(dropped)
                    .is_none(),
                "memory.ingest must not advertise unsupported '{dropped}'"
            );
        }
        assert!(
            find("receipts.emit")["inputSchema"]["properties"]["kind"]["enum"]
                .as_array()
                .expect("kind enum")
                .iter()
                .all(|kind| kind.as_str() != Some("task")),
            "receipts.emit must not advertise the unsupported 'task' kind"
        );
    }

    #[test]
    fn handlers_refuse_undeclared_arguments() {
        let (mut substrate, dir) = (
            Substrate::open(
                &std::env::temp_dir().join(format!("wm-contract-{}", Uuid::new_v4())),
                None,
                wm_gen3_core::constitution::default_view(),
            )
            .expect("substrate"),
            std::env::temp_dir().join(format!("wm-contract-dir-{}", Uuid::new_v4())),
        );
        std::fs::create_dir_all(&dir).expect("dir");
        let err = execute_hybrid_tool_call(
            "memory.pin",
            &json!({"id": 1, "bogus": true}),
            &mut substrate,
            &dir,
            false,
            McpProfile::Full,
        )
        .expect_err("unknown argument refused");
        assert!(err.contains("unknown argument 'bogus'"), "{err}");

        let err = execute_hybrid_tool_call(
            "session.replay",
            &json!({"cursor": "opaque"}),
            &mut substrate,
            &dir,
            false,
            McpProfile::Full,
        )
        .expect_err("cursor refused");
        assert!(err.contains("unknown argument 'cursor'"), "{err}");
        let _ = std::fs::remove_dir_all(&dir);
    }
}

#[cfg(test)]
mod session_e2e_tests {
    use super::*;
    use crate::mcp_server::{McpBackend, dispatch_json};

    fn call(backend: &McpBackend, id: u64, name: &str, args: Value) -> Value {
        let body = json!({
            "jsonrpc": "2.0",
            "id": id,
            "method": "tools/call",
            "params": { "name": name, "arguments": args }
        })
        .to_string();
        let response = dispatch_json(backend, body.as_bytes()).expect("dispatch response");
        let parsed: Value = serde_json::from_str(&response).expect("json-rpc response");
        assert_eq!(
            parsed["result"]["isError"], false,
            "tool {name} errored: {parsed}"
        );
        let text = parsed["result"]["content"][0]["text"]
            .as_str()
            .expect("tool text");
        serde_json::from_str(text).expect("tool payload json")
    }

    #[test]
    fn dispatch_json_session_lane_continuity_checkpoint_and_digest() {
        let dir = std::env::temp_dir().join(format!("wm-session-e2e-{}", Uuid::new_v4()));
        std::fs::create_dir_all(&dir).expect("dir");
        let mut substrate = Substrate::open(&dir, None, wm_gen3_core::constitution::default_view())
            .expect("substrate");
        substrate.set_budget(1_000_000);
        substrate.set_noise_enabled(false);
        let backend = McpBackend::gen3(substrate, &dir, McpProfile::Full, false);

        let start = call(&backend, 1, "session.start", json!({"title": "e2e lane"}));
        let lane = start["session_id"].as_str().expect("lane").to_string();

        let recorded = call(
            &backend,
            2,
            "session.record",
            json!({
                "session_id": lane,
                "content": "decided X",
                "turn_type": "decision",
                "importance": 0.9,
                "track": "mission-a"
            }),
        );
        let turn_id = recorded["turn_id"].as_str().expect("turn id").to_string();

        let checkpoint = call(
            &backend,
            3,
            "session.checkpoint",
            json!({
                "session_id": lane,
                "summary": "checkpoint summary",
                "next_queue": ["do y"],
                "open_flags": ["blocked"],
                "commit": "abc123",
                "branch": "feat/mcp-truth",
                "tests_green": true,
                "lease_id": "lease-1"
            }),
        );
        assert_eq!(checkpoint["commit"], "abc123");

        let continuity = call(
            &backend,
            4,
            "session.continuity",
            json!({"session_id": lane, "n": 5, "include_briefing_text": true}),
        );
        assert_eq!(continuity["turns_count"], 1);
        assert_eq!(continuity["recent_turns"][0]["turn_id"], turn_id);
        assert_eq!(continuity["recent_turns"][0]["track"], "mission-a");
        assert_eq!(continuity["checkpoint"]["commit"], "abc123");
        assert_eq!(continuity["checkpoint"]["branch"], "feat/mcp-truth");
        assert_eq!(continuity["checkpoint"]["tests_green"], true);
        assert_eq!(continuity["checkpoint"]["lease_id"], "lease-1");
        assert_eq!(continuity["next_queue"][0], "do y");
        assert!(
            continuity["briefing"]["text"]
                .as_str()
                .expect("briefing")
                .contains("checkpoint summary")
        );

        let digest = call(&backend, 5, "session.digest", json!({"session_id": lane}));
        let markdown = digest["markdown"].as_str().expect("markdown");
        assert!(markdown.contains("Session Digest"));
        assert!(markdown.contains("checkpoint summary"));
        assert_eq!(digest["json"]["turn_count"], 1);

        // supersedes retires the prior turn from continuity but replay can
        // still surface it on request.
        let superseding = call(
            &backend,
            6,
            "session.record",
            json!({
                "session_id": lane,
                "content": "changed Y",
                "turn_type": "decision",
                "supersedes": turn_id
            }),
        );
        assert_eq!(superseding["supersedes"], turn_id);
        let continuity = call(
            &backend,
            7,
            "session.continuity",
            json!({"session_id": lane}),
        );
        assert_eq!(continuity["turns_count"], 1);
        assert_eq!(continuity["recent_turns"][0]["content"], "changed Y");
        let replay = call(
            &backend,
            8,
            "session.replay",
            json!({
                "session_id": lane,
                "include_superseded": true,
                "mode": "selective",
                "min_importance": 0.0
            }),
        );
        assert_eq!(replay["returned"], 2);

        let list = call(&backend, 9, "session.list", json!({"limit": 10}));
        assert_eq!(list["sessions"][0]["session_id"], lane);
        assert_eq!(list["sessions"][0]["has_start_marker"], true);
        assert_eq!(list["sessions"][0]["turn_count"], 2);

        let _ = std::fs::remove_dir_all(&dir);
    }
}

#[cfg(test)]
mod honesty_behavior_tests {
    use super::*;

    fn setup(tag: &str) -> (Substrate, std::path::PathBuf) {
        let dir = std::env::temp_dir().join(format!("wm-honesty-{tag}-{}", Uuid::new_v4()));
        std::fs::create_dir_all(&dir).expect("dir");
        let mut substrate = Substrate::open(&dir, None, wm_gen3_core::constitution::default_view())
            .expect("substrate");
        substrate.set_budget(1_000_000);
        substrate.set_noise_enabled(false);
        (substrate, dir)
    }

    #[test]
    fn pin_handler_persists_releases_and_validates_galaxy() {
        let (mut substrate, dir) = setup("pin");
        let created = handle_memory_create(
            &json!({"content": "pinnable fact", "importance": 0.8, "tags": ["ops"]}),
            &mut substrate,
            false,
        )
        .expect("create");
        let id = created["record_id"].as_u64().expect("record id");

        let pinned = handle_memory_pin(&json!({"id": id}), &mut substrate, false).expect("pin");
        assert_eq!(pinned["pinned"], true);
        assert_eq!(
            pinned["message"],
            "Memory pinned against sweep decay and forgetting"
        );

        let reopened =
            Substrate::open_readonly(&dir, None, wm_gen3_core::constitution::default_view())
                .expect("reopen");
        assert!(reopened.is_pinned(id), "pin must survive reopen");

        let released =
            handle_memory_pin(&json!({"id": id, "pinned": false}), &mut substrate, false)
                .expect("unpin");
        assert_eq!(released["pinned"], false);
        assert!(!substrate.is_pinned(id));

        let err = handle_memory_pin(&json!({"id": id, "galaxy": "guide"}), &mut substrate, false)
            .expect_err("galaxy mismatch");
        assert!(err.contains("belongs to galaxy 'codex'"), "{err}");
        let _ = std::fs::remove_dir_all(&dir);
    }

    #[test]
    fn update_records_revision_and_revisions_verify_chain() {
        let (mut substrate, dir) = setup("update");
        let first =
            handle_memory_create(&json!({"content": "first version"}), &mut substrate, false)
                .expect("create");
        let old = first["record_id"].as_u64().expect("old id");
        let updated = handle_memory_update(
            &json!({"id": old, "content": "second version", "reason": "typo"}),
            &mut substrate,
            false,
        )
        .expect("update");
        assert_eq!(updated["revision"]["reason"], "typo");
        assert_eq!(updated["revision"]["record_id"], old);
        let new = updated["record_id"].as_u64().expect("new id");

        let listed = handle_memory_revisions(&json!({"id": old}), &substrate).expect("list");
        assert_eq!(listed["count"], 1);
        assert_eq!(listed["revisions"][0]["new_record_id"], new);

        let verified = handle_memory_revisions(&json!({"id": new, "action": "verify"}), &substrate)
            .expect("verify");
        assert_eq!(verified["verify"]["valid"], true);
        assert_eq!(verified["verify"]["chain_length"], 1);

        let err = handle_memory_revisions(&json!({"id": new, "action": "rebase"}), &substrate)
            .expect_err("bad action");
        assert!(err.contains("refuses action 'rebase'"), "{err}");
        let _ = std::fs::remove_dir_all(&dir);
    }

    #[test]
    fn aggregate_computes_real_values_and_refuses_unsupported() {
        let (mut substrate, dir) = setup("aggregate");
        for (text, importance) in [
            ("alpha one", 0.25),
            ("alpha two", 0.75),
            ("beta three", 0.5),
        ] {
            handle_memory_create(
                &json!({"content": text, "importance": importance}),
                &mut substrate,
                false,
            )
            .expect("create");
        }

        let sum = handle_memory_aggregate(
            &json!({"field": "importance", "op": "sum", "limit": 10}),
            &mut substrate,
        )
        .expect("sum");
        assert_eq!(sum["aggregate"], 1.5);
        assert_eq!(sum["sample_size"], 3);

        let avg = handle_memory_aggregate(
            &json!({"field": "importance", "op": "avg", "limit": 10}),
            &mut substrate,
        )
        .expect("avg");
        assert_eq!(avg["aggregate"], 0.5);

        let min = handle_memory_aggregate(
            &json!({"field": "importance", "op": "min", "limit": 10}),
            &mut substrate,
        )
        .expect("min");
        assert_eq!(min["aggregate"], 0.25);
        let max = handle_memory_aggregate(
            &json!({"field": "importance", "op": "max", "limit": 10}),
            &mut substrate,
        )
        .expect("max");
        assert_eq!(max["aggregate"], 0.75);

        let count = handle_memory_aggregate(
            &json!({"field": "created_at", "op": "count", "limit": 10}),
            &mut substrate,
        )
        .expect("count");
        assert_eq!(count["aggregate"], 3);
        assert_eq!(count["sample_size"], 3);

        let categorical = handle_memory_aggregate(
            &json!({"field": "source", "op": "count", "limit": 10}),
            &mut substrate,
        )
        .expect("categorical");
        assert_eq!(categorical["aggregate"], 3);

        let err = handle_memory_aggregate(&json!({"field": "source", "op": "sum"}), &mut substrate)
            .expect_err("categorical sum");
        assert!(err.contains("categorical"), "{err}");
        let err = handle_memory_aggregate(&json!({"field": "mood", "op": "avg"}), &mut substrate)
            .expect_err("unknown field");
        assert!(err.contains("refuses field 'mood'"), "{err}");
        let err = handle_memory_aggregate(
            &json!({"field": "importance", "op": "median"}),
            &mut substrate,
        )
        .expect_err("unknown op");
        assert!(err.contains("refuses op 'median'"), "{err}");

        let metric =
            handle_memory_aggregate(&json!({"metric": "count", "limit": 10}), &mut substrate)
                .expect("metric");
        assert_eq!(metric["aggregate"], 3);
        let _ = std::fs::remove_dir_all(&dir);
    }

    #[test]
    fn ingest_inline_items_are_real_and_malformed_input_refused() {
        let (mut substrate, dir) = setup("ingest");
        let dry = handle_memory_ingest(
            &json!({"items": ["one", "two"], "dry_run": true}),
            &mut substrate,
            false,
        )
        .expect("dry run");
        assert_eq!(dry["would_ingest"], 2);
        assert_eq!(dry["records_ingested"], 0);

        let real = handle_memory_ingest(
            &json!({
                "items_jsonl": "{\"content\":\"jsonl one\",\"tags\":[\"t\"],\"importance\":0.3}\nplain line\n",
                "text": "tail text",
                "dry_run": false
            }),
            &mut substrate,
            false,
        )
        .expect("ingest");
        assert_eq!(real["records_ingested"], 3);
        assert_eq!(substrate.store().record_count().unwrap(), 3);

        let duplicate = handle_memory_ingest(
            &json!({"text": "tail text", "dry_run": false}),
            &mut substrate,
            false,
        )
        .expect("duplicate");
        assert_eq!(duplicate["duplicates"], 1);
        assert_eq!(duplicate["records_ingested"], 0);

        let redacted = handle_memory_ingest(
            &json!({"text": "token ghp_abcdef123", "dry_run": false}),
            &mut substrate,
            false,
        )
        .expect("redact");
        assert_eq!(redacted["redacted_tokens"], 1);

        let err = handle_memory_ingest(&json!({"items_jsonl": "{bad json"}), &mut substrate, false)
            .expect_err("malformed jsonl");
        assert!(err.contains("malformed JSON"), "{err}");
        let err = handle_memory_ingest(&json!({"items": [{"source": "x"}]}), &mut substrate, false)
            .expect_err("missing content");
        assert!(err.contains("requires string 'content'"), "{err}");
        let err = handle_memory_ingest(&json!({}), &mut substrate, false).expect_err("no input");
        assert!(err.contains("requires one of"), "{err}");
        let _ = std::fs::remove_dir_all(&dir);
    }

    #[test]
    fn replay_modes_and_continuity_time_filters() {
        let (mut substrate, dir) = setup("replay");
        std::fs::write(
            dir.join("session_log.jsonl"),
            "{\"turn_id\":\"t1\",\"session_id\":\"lane\",\"role\":\"ai\",\"turn_type\":\"observation\",\"content\":\"early note\",\"importance\":0.2,\"timestamp\":100}\n\
             {\"turn_id\":\"t2\",\"session_id\":\"lane\",\"role\":\"ai\",\"turn_type\":\"decision\",\"content\":\"mid decision\",\"importance\":0.9,\"timestamp\":200}\n\
             {\"turn_id\":\"t3\",\"session_id\":\"lane\",\"role\":\"ai\",\"turn_type\":\"summary\",\"content\":\"late summary\",\"importance\":0.6,\"timestamp\":300}\n",
        )
        .expect("log");

        let full = handle_session_replay(&json!({"session_id": "lane"}), &dir).expect("full");
        assert_eq!(full["returned"], 3);
        assert_eq!(full["mode"], "full");

        let selective = handle_session_replay(
            &json!({"session_id": "lane", "mode": "selective", "min_importance": 0.8}),
            &dir,
        )
        .expect("selective");
        assert_eq!(selective["returned"], 1);
        assert_eq!(selective["trajectory"][0]["turn_id"], "t2");

        let typed = handle_session_replay(
            &json!({"mode": "selective", "min_importance": 0.0, "turn_types": ["summary"]}),
            &dir,
        )
        .expect("typed");
        assert_eq!(typed["returned"], 1);
        assert_eq!(typed["trajectory"][0]["turn_id"], "t3");

        let progressive =
            handle_session_replay(&json!({"mode": "progressive", "token_budget": 8}), &dir)
                .expect("progressive");
        assert!(progressive["returned"].as_u64().unwrap() >= 1);
        assert!(progressive["returned"].as_u64().unwrap() <= 3);
        assert_eq!(
            progressive["trajectory"][progressive["returned"].as_u64().unwrap() as usize - 1]["turn_id"],
            "t3"
        );

        let windowed = handle_session_replay(&json!({"since": "150"}), &dir).expect("since");
        assert_eq!(windowed["returned"], 2);
        let windowed = handle_session_replay(&json!({"until": "100"}), &dir).expect("until");
        assert_eq!(windowed["returned"], 1);

        let err = handle_session_replay(&json!({"mode": "lossless"}), &dir)
            .expect_err("lossless unsupported");
        assert!(err.contains("refuses mode 'lossless'"), "{err}");

        let continuity =
            handle_session_continuity(&json!({"session_id": "lane", "n": 1}), &substrate, &dir)
                .expect("continuity n");
        assert_eq!(continuity["turns_count"], 1);
        assert_eq!(continuity["recent_turns"][0]["turn_id"], "t3");
        let continuity = handle_session_continuity(
            &json!({"session_id": "lane", "until": "150"}),
            &substrate,
            &dir,
        )
        .expect("continuity until");
        assert_eq!(continuity["turns_count"], 1);
        assert_eq!(continuity["recent_turns"][0]["turn_id"], "t1");

        let err = handle_session_record(
            &json!({"content": "x", "session_id": "lane", "supersedes": "missing"}),
            &mut substrate,
            &dir,
            false,
        )
        .expect_err("unknown supersedes");
        assert!(err.contains("no such turn id"), "{err}");
        let _ = std::fs::remove_dir_all(&dir);
    }
}
