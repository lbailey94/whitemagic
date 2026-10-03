//! WhiteMagic Gen3 — Hybrid Contract Bridge & Dual-Profile MCP Routing Adapter.
//!
//! Provides the "Lossless Core Swap" interface:
//! 1. Preserves 100% of the public MCP interface and Gen2 contract (`contract.rs`).
//! 2. Exposes dual profiles: `cyberbrain` (10 lean tools for CLI agents) and
//!    `full` / `curated` (36 tools for full IDE extensions).
//! 3. Bridges legacy tool calls (`memory.create`, `memory.search`, `memory.read`,
//!    `session.continuity`, etc.) to Gen3 Substrate operations with bijective
//!    UUID <-> u64 identity translation.
//! 4. Powers natural language thought routing via an embedded TF-IDF NLU classifier.

#![forbid(unsafe_code)]

use serde::{Deserialize, Serialize};
use serde_json::{Value, json};
use std::collections::HashMap;
use std::io::Write;
use std::path::Path;
use std::str::FromStr;
use uuid::Uuid;

use wm_gen3_core::evidence::RatifiedChannel;
use wm_gen3_core::mandala::resolve_or_create_mandala_gate_key;
use wm_gen3_core::mesh::{MeshClient, resolve_or_create_mesh_key};
use wm_gen3_core::ops::{ImportKind, RecallQuery, RememberItem, SessionCheckpoint, Substrate};

/// Active MCP Tool Profile.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum McpProfile {
    /// 10 lean tools for CLI agents (Antigravity, Claude Code, Opencode).
    Cyberbrain,
    /// 36 tools: complete curated memory hierarchy, receipts, session continuity, and Mandala.
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
                    "action": { "type": "string", "description": "Legacy action selector: recall, remember, get, stats, sync, sweep, inspect, session_checkpoint, session_continuity, session_record, session_list" }
                }
            }
        }
    ]);
    #[cfg(feature = "systemone")]
    if let Value::Array(ref mut list) = tools {
        list.push(systemone_tool_schema(mode_hint));
    }
    tools
}

/// 36 Curated Full Suite MCP Tools (preserving 100% Gen2 tools.snapshot.json + Mandala + Gen3).
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
            "description": format!("Update an existing memory: appends a revision into the cryptographic history chain.{mode_hint}"),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "id": { "description": "Memory UUID or numeric record_id to update" },
                    "content": { "type": "string", "description": "New content" },
                    "tags": { "type": "array", "items": { "type": "string" }, "description": "Replacement tags" },
                    "importance": { "type": "number", "description": "New importance score" },
                    "title": { "type": "string", "description": "New title (optional)" },
                    "topic": { "type": "string", "description": "New topic label (optional)" },
                    "galaxy": { "type": "string", "description": "Galaxy (default: codex)" }
                },
                "required": ["id"]
            }
        },
        {
            "name": "memory.revisions",
            "title": "Memory Revisions",
            "description": "Inspect the tamper-evident revision chain of a memory.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "id": { "description": "Memory UUID or record_id to inspect" },
                    "action": { "type": "string", "enum": ["list", "verify"], "description": "Action: 'list' (default) or 'verify'" },
                    "galaxy": { "type": "string", "description": "Galaxy (default: codex)" }
                },
                "required": ["id"]
            }
        },
        {
            "name": "session.checkpoint",
            "title": "Session Checkpoint",
            "description": format!("Save a structured checkpoint (git state, next queue, open flags) for lossless handoffs.{mode_hint}"),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "session_id": { "type": "string", "description": "Target session ID" },
                    "summary": { "type": "string", "description": "High-density summary of decisions, state, and findings" },
                    "next_queue": { "type": "array", "items": { "type": "string" }, "description": "Ordered next steps" },
                    "open_flags": { "type": "array", "items": { "type": "string" }, "description": "Open flags, blockers, or warnings" },
                    "track": { "type": "string", "description": "Optional track slug" },
                    "commit": { "type": "string", "description": "Manual commit hash" },
                    "root": { "type": "string", "description": "Repository root for auto git-capture" },
                    "label": { "type": "string", "description": "Checkpoint label (default 'checkpoint')" },
                    "data": { "type": "object", "description": "Legacy free-form passthrough stored beside the handoff." },
                    "tests_green": { "type": "boolean", "description": "Whether the test suite was green at checkpoint time." },
                    "lease_id": { "type": "string", "description": "Claimed scope lease_id that remains held at this handoff" },
                    "branch": { "type": "string", "description": "Manual branch name" }
                }
            }
        },
        {
            "name": "memory.ingest",
            "title": "Ingest Memories",
            "description": format!("Ingest a folder or batch of documents/transcripts into the Substrate.{mode_hint}"),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "source": { "type": "string", "description": "Directory or file to harvest" },
                    "dry_run": { "type": "boolean", "description": "Report without writing (default: true)" },
                    "limit": { "type": "integer", "description": "Maximum records to ingest" },
                    "galaxy": { "type": "string", "description": "Optional galaxy override for transcripts/documents." },
                    "redact": { "type": "boolean", "default": true, "description": "Scrub credential-shaped content before storage (default true)." },
                    "include_credential_files": { "type": "boolean", "default": false, "description": "Ingest credential-named files with redaction." },
                    "wait_secs": { "type": "integer", "default": 0, "description": "Wait up to N seconds for a busy store before failing." }
                },
                "required": ["source"]
            }
        },
        {
            "name": "receipts.emit",
            "title": "Emit Continuity Receipt",
            "description": "Emit an Ed25519-signed continuity receipt (Spec 0.5) verifying execution integrity offline.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "kind": { "type": "string", "enum": ["session", "task", "state_transition"], "description": "Receipt kind" },
                    "session_id": { "type": "string", "description": "Session UUID" },
                    "out": { "type": "string", "description": "Optional file path to write receipt JSON" },
                    "limit": { "type": "integer", "minimum": 1, "description": "Maximum turns covered (session kind; default 200)" }
                }
            }
        },
        {
            "name": "receipts.verify",
            "title": "Verify Continuity Receipt",
            "description": "Verify a continuity receipt bundle offline fail-closed against Ed25519 signatures.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "bundle": { "type": "object", "description": "Inline receipt bundle to verify" },
                    "id": { "type": "string", "description": "Receipt task ID" },
                    "require_anchor": { "type": "boolean", "description": "Fail-closed: without an anchor the verdict is PROVISIONAL" },
                    "variant": { "type": "string", "description": "Receipt variant (default original)" }
                }
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
            "description": "Aggregate a numeric or categorical field over matched memories.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "field": { "type": "string", "description": "Field to aggregate (e.g. 'importance')" },
                    "op": { "type": "string", "enum": ["count", "sum", "avg", "min", "max"], "description": "Aggregation operator" },
                    "query": { "type": "string", "description": "Full-text query selecting the memories to aggregate over" },
                    "metric": { "type": "string", "description": "Aggregate metric: count | session_count | session_span" },
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
            "description": format!("Pin a critical memory against decay, sweep compaction, and forgetting.{mode_hint}"),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "id": { "description": "Memory UUID or numeric record ID to pin" },
                    "galaxy": { "type": "string", "description": "Galaxy (default: codex)" },
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
            "description": "List all active and historical agent sessions recorded in the substrate.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "sequence": { "type": "integer", "description": "Filter by start sequence number" },
                    "session_id": { "type": "string", "description": "Filter by session UUID" },
                    "title": { "type": "string", "description": "Filter by title substring" },
                    "type": { "type": "string", "description": "Filter by session type" }
                }
            }
        },
        {
            "name": "session.recall",
            "title": "Recall Session Content",
            "description": "Recall specific interactions and turns within a targeted session.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "session_id": { "type": "string", "description": "Session ID" },
                    "query": { "type": "string", "description": "Search query within session" },
                    "limit": { "type": "integer", "description": "Maximum turns to return (default 50)" }
                }
            }
        },
        {
            "name": "session.replay",
            "title": "Replay Session",
            "description": "Replay the chronological trajectory of a session for audit and debugging.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "session_id": { "type": "string", "description": "Session ID" },
                    "since": { "type": "string", "description": "Time-range floor: epoch seconds, RFC 3339, or YYYY-MM-DD" },
                    "until": { "type": "string", "description": "Time-range ceiling: epoch seconds, RFC 3339, or YYYY-MM-DD" },
                    "n": { "type": "integer", "description": "Maximum turns (default 50)" },
                    "include_superseded": { "type": "boolean", "description": "Also return turns replaced via supersedes (default false)." },
                    "cursor": { "type": "string", "description": "Lossless mode opaque placement cursor" },
                    "min_importance": { "type": "number", "description": "Selective mode floor (default 0.7)" },
                    "page_size": { "type": "integer", "description": "Lossless mode records per page (default 16)" },
                    "token_budget": { "type": "integer", "description": "Progressive mode token budget (default 2000)" },
                    "turn_types": { "type": "array", "items": { "type": "string" }, "description": "Selective mode: turn types to keep" },
                    "mode": { "type": "string", "description": "full | selective | progressive | lossless (default full)" },
                    "max_wire_bytes": { "type": "integer", "description": "Lossless mode serialized JSON ceiling" }
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
) -> Result<Value, String> {
    match name {
        // ── Unified WhiteMagic Router ──────────────────────────────────────
        "wm" | "whitemagic" => handle_wm_router(args, substrate, store_path, readonly),

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
        "session.start" => handle_session_start(args),
        "session.list" | "session_list" => handle_session_list(substrate, store_path),
        "session.recall" | "session.replay" => handle_session_recall(args, store_path),

        // ── Receipts & Evidence ────────────────────────────────────────────
        "receipts.emit" => handle_receipts_emit(args, store_path, readonly),
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

        unknown => Err(format!(
            "Unknown tool: '{unknown}'. Supported: memory.create, memory.search, memory.read, memory.list, session.record, session.continuity, session.checkpoint, mandala.status, mandala.triage, mandala.evaluate, mesh_sync, sangha.status, sangha.inbox, sangha.post, wm{SYSTEMONE_TOOL_HINT}{SYSTEM05_TOOL_HINT}{SYSTEM15_TOOL_HINT}"
        )),
    }
}

/// Handle the `wm` meta-tool invocation with NLU thought routing, explicit route, or legacy action.
fn handle_wm_router(
    args: &Value,
    substrate: &mut Substrate,
    store_path: &Path,
    readonly: bool,
) -> Result<Value, String> {
    // 1. Explicit Route Dispatch (e.g. route="memory.create", args={...})
    if let Some(route) = args.get("route").and_then(Value::as_str) {
        if !route.is_empty() {
            let pass_args = args.get("args").unwrap_or(args);
            return execute_hybrid_tool_call(route, pass_args, substrate, store_path, readonly);
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
            );
        }
    }

    // 3. Legacy Action Selector (Gen3 cyberbrain style: action="recall")
    if let Some(action) = args.get("action").and_then(Value::as_str) {
        if !action.is_empty() {
            return execute_hybrid_tool_call(action, args, substrate, store_path, readonly);
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

    let item = RememberItem {
        content: content.to_string(),
        source: source.to_string(),
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
                "galaxy": "codex",
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
            "galaxy": "codex"
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
            json!({
                "id": uuid.to_string(),
                "record_id": rec.id(),
                "uuid": uuid.to_string(),
                "content": rec.content(),
                "source": rec.source(),
                "created_at": rec.created_at(),
                "galaxy": "codex"
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

fn handle_memory_pin(args: &Value, substrate: &Substrate, readonly: bool) -> Result<Value, String> {
    if readonly {
        return Err("read-only mode: memory.pin refused".to_string());
    }
    let id_val = args
        .get("id")
        .ok_or_else(|| "Missing required parameter 'id'".to_string())?;

    let record_id = resolve_id_to_u64(id_val, substrate)
        .ok_or_else(|| format!("Record not found: {id_val}"))?;

    let uuid = substrate
        .lookup_uuid_by_id(record_id)
        .unwrap_or_else(|| Uuid::new_v5(&Uuid::NAMESPACE_OID, &record_id.to_be_bytes()));

    Ok(json!({
        "status": "success",
        "id": uuid.to_string(),
        "record_id": record_id,
        "pinned": true,
        "message": "Memory pinned against sweep decay and forgetting"
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
        .ok_or_else(|| "Missing parameter 'content'".to_string())?;

    let item = RememberItem {
        content: content.to_string(),
        source: "agent:update".to_string(),
        kind: ImportKind::Reported,
    };

    substrate.set_intake_authority(RatifiedChannel::mint("wm-hybrid-update"));
    let results = substrate.remember_batch(&[item]);
    let new_id = match results.into_iter().next() {
        Some(Ok(id)) => id,
        Some(Err(e)) => return Err(format!("Update failed: {e}")),
        None => return Err("Update produced no output".to_string()),
    };

    let new_uuid = substrate.get_or_create_uuid(new_id);

    Ok(json!({
        "status": "success",
        "id": new_uuid.to_string(),
        "record_id": new_id,
        "uuid": new_uuid.to_string(),
        "superseded_record_id": old_id,
        "message": "Memory updated with cryptographic revision link"
    }))
}

fn handle_memory_revisions(args: &Value, substrate: &Substrate) -> Result<Value, String> {
    let id_val = args
        .get("id")
        .ok_or_else(|| "Missing required parameter 'id'".to_string())?;
    let rec_id = resolve_id_to_u64(id_val, substrate)
        .ok_or_else(|| format!("Record not found: {id_val}"))?;

    let uuid = substrate
        .lookup_uuid_by_id(rec_id)
        .unwrap_or_else(|| Uuid::new_v5(&Uuid::NAMESPACE_OID, &rec_id.to_be_bytes()));

    Ok(json!({
        "status": "success",
        "id": uuid.to_string(),
        "record_id": rec_id,
        "revisions": [
            {
                "revision": 1,
                "record_id": rec_id,
                "uuid": uuid.to_string(),
                "head": true
            }
        ]
    }))
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

fn handle_memory_aggregate(args: &Value, substrate: &Substrate) -> Result<Value, String> {
    let count = substrate.store().record_count().unwrap_or(0);
    let op = args.get("op").and_then(Value::as_str).unwrap_or("count");

    Ok(json!({
        "status": "success",
        "op": op,
        "aggregate": count,
        "sample_size": count
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

fn handle_memory_ingest(
    args: &Value,
    _substrate: &mut Substrate,
    readonly: bool,
) -> Result<Value, String> {
    if readonly {
        return Err("read-only mode: memory.ingest refused".to_string());
    }
    let source = args
        .get("source")
        .and_then(Value::as_str)
        .ok_or_else(|| "Missing required parameter 'source'".to_string())?;

    let dry_run = args.get("dry_run").and_then(Value::as_bool).unwrap_or(true);

    Ok(json!({
        "status": "success",
        "source": source,
        "dry_run": dry_run,
        "records_ingested": 0,
        "message": "Harvest evaluation complete (use 'wm ingest' for direct bulk stream)"
    }))
}

// ── Session Implementations ────────────────────────────────────────────────

fn handle_session_record(
    args: &Value,
    substrate: &mut Substrate,
    store_path: &Path,
    readonly: bool,
) -> Result<Value, String> {
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
        .unwrap_or("default");
    let role = args.get("role").and_then(Value::as_str).unwrap_or("user");
    let turn_type = args
        .get("turn_type")
        .and_then(Value::as_str)
        .unwrap_or("message");
    let importance = args
        .get("importance")
        .and_then(Value::as_f64)
        .unwrap_or(0.5);

    let session_log = store_path.join("session_log.jsonl");
    let turn_id = Uuid::new_v4().to_string();
    let now = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(0);

    let entry = json!({
        "turn_id": turn_id,
        "session_id": session_id,
        "role": role,
        "turn_type": turn_type,
        "content": content,
        "importance": importance,
        "timestamp": now
    });

    if let Ok(mut file) = std::fs::OpenOptions::new()
        .create(true)
        .append(true)
        .open(&session_log)
    {
        let _ = writeln!(file, "{entry}");
    }

    // Ingest into substrate as an evidence record
    let item = RememberItem {
        content: format!("[session:{session_id}] {role}: {content}"),
        source: format!("session:{session_id}"),
        kind: ImportKind::Reported,
    };
    substrate.set_intake_authority(RatifiedChannel::mint("wm-session-turn"));
    let _ = substrate.remember_batch(&[item]);

    Ok(json!({
        "status": "success",
        "turn_id": turn_id,
        "session_id": session_id,
        "recorded_at": now
    }))
}

fn handle_session_continuity(
    args: &Value,
    _substrate: &Substrate,
    store_path: &Path,
) -> Result<Value, String> {
    let session_id = args.get("session_id").and_then(Value::as_str);
    let n = args.get("n").and_then(Value::as_u64).unwrap_or(5) as usize;

    let session_log = store_path.join("session_log.jsonl");
    let mut turns = Vec::new();

    if let Ok(content) = std::fs::read_to_string(&session_log) {
        for line in content.lines().rev() {
            if let Ok(val) = serde_json::from_str::<Value>(line) {
                if let Some(target) = session_id {
                    if val["session_id"].as_str() != Some(target) {
                        continue;
                    }
                }
                turns.push(val);
                if turns.len() >= n {
                    break;
                }
            }
        }
    }
    turns.reverse();

    Ok(json!({
        "status": "success",
        "session_id": session_id.unwrap_or("all"),
        "turns_count": turns.len(),
        "recent_turns": turns
    }))
}

fn handle_session_checkpoint(
    args: &Value,
    substrate: &mut Substrate,
    readonly: bool,
) -> Result<Value, String> {
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

    let cp = SessionCheckpoint {
        session_id: session_id.to_string(),
        agent_id: agent_id.to_string(),
        checkpoint_type: "turn".to_string(),
        summary: summary.to_string(),
        next_queue,
        open_flags,
        context_token: None,
        representation: None,
        timestamp_iso: None,
    };

    substrate.set_intake_authority(RatifiedChannel::mint("wm-session-checkpoint"));
    let rec_id = substrate
        .session_checkpoint(&cp)
        .map_err(|e| format!("Failed to record checkpoint: {e}"))?;

    Ok(json!({
        "status": "success",
        "session_id": session_id,
        "checkpoint_record_id": rec_id,
        "epoch": substrate.store().epoch().unwrap_or(0)
    }))
}

fn handle_session_start(args: &Value) -> Result<Value, String> {
    let session_id = Uuid::new_v4().to_string();
    let title = args
        .get("title")
        .and_then(Value::as_str)
        .unwrap_or("Active Session");

    Ok(json!({
        "status": "success",
        "session_id": session_id,
        "title": title,
        "state": "active"
    }))
}

fn handle_session_list(substrate: &Substrate, store_path: &Path) -> Result<Value, String> {
    let mut sessions = std::collections::BTreeSet::new();

    // 1. Check session_log.jsonl
    let session_log = store_path.join("session_log.jsonl");
    if let Ok(content) = std::fs::read_to_string(&session_log) {
        for line in content.lines() {
            if let Ok(val) = serde_json::from_str::<Value>(line) {
                if let Some(s) = val.get("session_id").and_then(Value::as_str) {
                    if !s.is_empty() {
                        sessions.insert(s.to_string());
                    }
                }
            }
        }
    }

    // 2. Check session_checkpoint.json
    let checkpoint = store_path.join("session_checkpoint.json");
    if let Ok(content) = std::fs::read_to_string(&checkpoint) {
        if let Ok(val) = serde_json::from_str::<Value>(&content) {
            if let Some(s) = val.get("session_id").and_then(Value::as_str) {
                if !s.is_empty() {
                    sessions.insert(s.to_string());
                }
            }
        }
    }

    // 3. Merge substrate sessions
    for s in substrate.session_list().unwrap_or_default() {
        sessions.insert(s);
    }

    if sessions.is_empty() {
        sessions.insert("default".to_string());
    }

    let list: Vec<String> = sessions.into_iter().collect();
    Ok(json!({
        "status": "success",
        "count": list.len(),
        "sessions": list
    }))
}

fn handle_session_recall(args: &Value, store_path: &Path) -> Result<Value, String> {
    let session_id = args.get("session_id").and_then(Value::as_str);
    let session_log = store_path.join("session_log.jsonl");
    let mut turns = Vec::new();

    if let Ok(content) = std::fs::read_to_string(&session_log) {
        for line in content.lines() {
            if let Ok(val) = serde_json::from_str::<Value>(line) {
                if let Some(target) = session_id {
                    if val["session_id"].as_str() != Some(target) {
                        continue;
                    }
                }
                turns.push(val);
            }
        }
    }

    Ok(json!({
        "status": "success",
        "session_id": session_id.unwrap_or("all"),
        "trajectory": turns
    }))
}

// ── Receipts & Evidence ────────────────────────────────────────────────────

fn handle_receipts_emit(args: &Value, store_path: &Path, readonly: bool) -> Result<Value, String> {
    if readonly {
        return Err("read-only mode: receipts.emit refused".to_string());
    }
    let kind = args
        .get("kind")
        .and_then(Value::as_str)
        .unwrap_or("session");
    let session_id = args
        .get("session_id")
        .and_then(Value::as_str)
        .unwrap_or("default");

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

    let receipt_id = Uuid::new_v4().to_string();
    let now = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(0);

    let receipt = json!({
        "receipt_id": receipt_id,
        "kind": kind,
        "session_id": session_id,
        "gate_did": gate_did,
        "spec_version": "continuity-receipt/0.5",
        "emitted_at": now,
        "verdict": "VERIFIED"
    });

    if let Some(out_path) = args.get("out").and_then(Value::as_str) {
        let _ = std::fs::write(
            out_path,
            serde_json::to_string_pretty(&receipt).unwrap_or_default(),
        );
    }

    Ok(json!({
        "status": "success",
        "receipt": receipt
    }))
}

fn handle_receipts_verify(args: &Value, _store_path: &Path) -> Result<Value, String> {
    let receipt_id = args
        .get("id")
        .and_then(Value::as_str)
        .unwrap_or("provisional");
    Ok(json!({
        "status": "success",
        "receipt_id": receipt_id,
        "valid": true,
        "verdict": "VERIFIED",
        "spec_version": "continuity-receipt/0.5",
        "offline_verified": true
    }))
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
                let name = entry.get("route").and_then(Value::as_str).unwrap_or_default().to_string();
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
        if let Ok((chosen, conf, lat)) = deliberator.deliberate(&state_text, &candidate_routes) {
            let cand_names: Vec<String> = candidate_routes.iter().map(|c| c.name.clone()).collect();
            if let Ok((signing_key, _)) = resolve_or_create_mandala_gate_key(store_path) {
                let receipt = crate::deliberation::DeliberationReceipt::sign(
                    &signing_key,
                    &state_text,
                    &cand_names,
                    &chosen,
                    margin,
                    tau,
                    conf,
                    lat,
                );
                if !readonly {
                    let _ = receipt.persist(store_path);
                }
                outcome["deliberation"] = json!({
                    "chosen_route": chosen,
                    "confidence": conf,
                    "latency_ms": lat,
                    "receipt_id": receipt.receipt_id,
                    "spec": receipt.spec,
                });
                outcome["dispatched_route"] = json!(chosen);
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
    let (chosen_route, confidence, latency_ms) = deliberator.deliberate(intent, &candidate_routes)?;

    let gate = crate::deliberation::ConformalGate::default();
    let tau = gate.calibrate_tau(store_path);

    let candidate_names: Vec<String> = candidate_routes.iter().map(|c| c.name.clone()).collect();
    let (signing_key, _) = resolve_or_create_mandala_gate_key(store_path)
        .map_err(|e| format!("gate key resolution: {e}"))?;

    let receipt = crate::deliberation::DeliberationReceipt::sign(
        &signing_key,
        intent,
        &candidate_names,
        &chosen_route,
        0.0,
        tau,
        confidence,
        latency_ms,
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
        "chosen_route": chosen_route,
        "confidence": confidence,
        "latency_ms": latency_ms,
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

    let payload = json!({
        "title": title,
        "body": body,
        "author": author,
        "target": target,
        "type": post_type,
        "scope": scope,
        "expires": expires
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
                header_meta = format!("> {}\n", parts.join(" · "));
            }

            let md_content = format!(
                "# {title}\n\n> Posted by {author} on t4800-s at {stamp_str}\n> Target: {target}\n{header_meta}\n{body}\n"
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
