//! Embedding-based NLU router for the `wm` meta-tool.
//!
//! Replaces the 450-line keyword `if-else` chain with a data-driven TF-IDF
//! cosine similarity router. Each tool has a weighted keyword profile. Input
//! text is tokenized and compared against all profiles using cosine similarity.
//!
//! Advantages over the keyword chain:
//! - Scales to hundreds of tools without code changes (just add profiles)
//! - Handles partial matches and multi-word queries naturally
//! - Confidence score reflects actual semantic overlap, not arbitrary 0.9/1.0
//! - No ordering dependency — all profiles scored independently

use ahash::AHashMap;

/// A tool routing profile with weighted keywords.
#[derive(Debug, Clone)]
pub struct ToolProfile {
    pub tool_name: &'static str,
    /// Weighted keywords — (term, weight) pairs.
    /// Multi-word phrases are split into individual tokens.
    pub keywords: &'static [(&'static str, f64)],
}

/// All tool profiles, ordered roughly by specificity (most specific first
/// for tie-breaking, though cosine similarity makes this less critical).
pub static TOOL_PROFILES: &[ToolProfile] = &[
    // ── Memory operations ──────────────────────────────────────────
    ToolProfile {
        tool_name: "memory.create",
        keywords: &[
            ("remember", 7.0),
            ("store", 7.0),
            ("save", 5.0),
            ("memorize", 5.0),
            ("record", 2.0),
            ("persist", 2.0),
            ("capture", 1.5),
        ],
    },
    ToolProfile {
        tool_name: "memory.read",
        keywords: &[
            ("recall", 3.0),
            ("read", 2.5),
            ("fetch", 2.5),
            ("get", 1.5),
            ("retrieve", 2.5),
            ("memory", 1.0),
            ("load", 2.0),
            ("access", 1.5),
            ("view", 1.5),
            ("show", 1.5),
        ],
    },
    ToolProfile {
        tool_name: "memory.list",
        keywords: &[
            ("list", 3.0),
            ("show", 2.0),
            ("all", 1.5),
            ("memories", 2.0),
            ("browse", 2.0),
            ("enumerate", 2.0),
            ("display", 2.0),
            ("view", 1.5),
        ],
    },
    ToolProfile {
        tool_name: "memory.delete",
        keywords: &[
            ("delete", 3.0),
            ("remove", 2.5),
            ("forget", 2.5),
            ("erase", 2.5),
            ("destroy", 2.0),
            ("purge", 1.5),
            ("drop", 2.0),
            ("clear", 1.5),
            ("discard", 2.0),
        ],
    },
    ToolProfile {
        tool_name: "memory.search",
        keywords: &[
            ("search", 3.5),
            ("find", 2.0),
            ("query", 1.0),
            ("lookup", 2.0),
            ("fulltext", 2.5),
            ("full-text", 2.5),
            ("seek", 1.5),
            ("locate", 1.5),
            ("grep", 2.0),
        ],
    },
    ToolProfile {
        tool_name: "memory.chat",
        keywords: &[
            ("chat", 3.5),
            ("conversational", 3.0),
            ("converse", 2.5),
            ("talk", 2.0),
            ("ask", 2.0),
            ("discuss", 2.0),
            ("explore", 1.5),
            ("browse", 1.5),
            ("hybrid", 2.0),
        ],
    },
    ToolProfile {
        tool_name: "memory.vector.search",
        keywords: &[
            ("vector", 3.0),
            ("embedding", 3.0),
            ("similar", 2.5),
            ("similarity", 3.0),
            ("semantic", 2.5),
            ("nearest", 2.0),
            ("neighbors", 1.5),
            ("cosine", 2.0),
            ("ann", 2.0),
            ("alike", 2.0),
            ("like", 1.0),
            ("close", 1.5),
        ],
    },
    ToolProfile {
        tool_name: "memory.query",
        keywords: &[
            ("query", 3.0),
            ("filter", 2.5),
            ("where", 1.5),
            ("select", 2.0),
            ("condition", 2.0),
            ("criteria", 2.0),
            ("match", 1.5),
            ("search", 1.0),
        ],
    },
    ToolProfile {
        tool_name: "memory.hybrid_recall",
        keywords: &[
            ("hybrid", 3.0),
            ("smart", 2.5),
            ("combined", 2.5),
            ("recall", 1.5),
            ("intelligent", 2.0),
            ("fusion", 2.0),
        ],
    },
    ToolProfile {
        tool_name: "memory.associate",
        keywords: &[
            ("associate", 3.0),
            ("link", 2.5),
            ("connect", 2.0),
            ("relate", 2.5),
            ("tie", 1.5),
            ("bind", 1.5),
        ],
    },
    ToolProfile {
        tool_name: "memory.associations",
        keywords: &[
            ("associations", 3.0),
            ("links", 2.5),
            ("related", 2.5),
            ("connections", 2.0),
            ("edges", 2.0),
            ("neighbors", 1.5),
        ],
    },
    ToolProfile {
        tool_name: "memory.associate_mine",
        keywords: &[
            ("mine", 4.0),
            ("discover", 2.0),
            ("associations", 1.5),
            ("uncover", 2.0),
            ("excavate", 2.0),
        ],
    },
    ToolProfile {
        tool_name: "memory.consolidate",
        keywords: &[
            ("consolidate", 3.0),
            ("deduplicate", 3.0),
            ("dedup", 3.0),
            ("merge", 2.0),
            ("duplicate", 2.0),
            ("combine", 1.5),
        ],
    },
    ToolProfile {
        tool_name: "memory.decay",
        keywords: &[
            ("decay", 3.0),
            ("age", 2.0),
            ("expire", 2.5),
            ("stale", 2.0),
            ("rot", 1.5),
            ("degrade", 2.0),
        ],
    },
    ToolProfile {
        tool_name: "memory.batch_read",
        keywords: &[
            ("batch", 3.0),
            ("multiple", 2.5),
            ("bulk", 2.5),
            ("read", 1.0),
            ("many", 2.0),
            ("several", 1.5),
        ],
    },
    ToolProfile {
        tool_name: "memory.update",
        keywords: &[
            ("update", 5.0),
            ("modify", 2.0),
            ("change", 2.0),
            ("edit", 2.0),
            ("alter", 1.5),
            ("revise", 1.5),
            ("memory", 1.0),
            ("amend", 1.5),
            ("patch", 1.5),
        ],
    },
    ToolProfile {
        tool_name: "memory.tag",
        keywords: &[
            ("tag", 5.0),
            ("label", 2.0),
            ("retag", 3.0),
            ("categorize", 2.0),
            ("mark", 1.5),
            ("add", 1.5),
        ],
    },
    ToolProfile {
        tool_name: "memory.stats",
        keywords: &[
            ("stats", 3.0),
            ("statistics", 3.0),
            ("summary", 2.0),
            ("memory", 1.0),
            ("galaxy", 1.5),
            ("count", 1.0),
        ],
    },
    ToolProfile {
        tool_name: "memory.count",
        keywords: &[
            ("count", 3.0),
            ("how", 1.5),
            ("many", 2.0),
            ("number", 2.5),
            ("total", 2.0),
            ("memories", 1.5),
        ],
    },
    ToolProfile {
        tool_name: "memory.tags",
        keywords: &[
            ("tags", 4.0),
            ("labels", 2.0),
            ("categories", 1.5),
            ("list", 1.0),
        ],
    },
    ToolProfile {
        tool_name: "memory.nearby",
        keywords: &[
            ("nearby", 3.0),
            ("near", 2.5),
            ("close", 2.0),
            ("spatial", 2.5),
            ("proximity", 2.5),
            ("surrounding", 2.0),
            ("adjacent", 2.0),
        ],
    },
    // ── Session ────────────────────────────────────────────────────
    ToolProfile {
        tool_name: "session.start",
        keywords: &[
            ("start", 3.0),
            ("new", 2.5),
            ("begin", 2.5),
            ("open", 2.0),
            ("session", 2.0),
            ("create", 1.5),
        ],
    },
    ToolProfile {
        tool_name: "session.checkpoint",
        keywords: &[
            ("checkpoint", 3.0),
            ("snapshot", 3.0),
            ("save", 1.5),
            ("point", 2.0),
            ("marker", 2.5),
        ],
    },
    ToolProfile {
        tool_name: "session.recall",
        keywords: &[
            ("recall", 2.0),
            ("session", 3.0),
            ("history", 2.5),
            ("replay", 2.5),
            ("previous", 1.5),
        ],
    },
    ToolProfile {
        tool_name: "session.end",
        keywords: &[
            ("end", 3.0),
            ("close", 2.5),
            ("stop", 2.0),
            ("finish", 2.5),
            ("terminate", 2.5),
            ("session", 1.5),
        ],
    },
    ToolProfile {
        tool_name: "session.list",
        keywords: &[
            ("list", 2.5),
            ("show", 2.0),
            ("all", 1.5),
            ("sessions", 3.0),
            ("history", 1.5),
        ],
    },
    // ── Consciousness ──────────────────────────────────────────────
    ToolProfile {
        tool_name: "citta.status",
        keywords: &[
            ("citta", 3.0),
            ("consciousness", 2.5),
            ("status", 1.5),
            ("vector", 2.0),
            ("awareness", 2.0),
        ],
    },
    ToolProfile {
        tool_name: "citta.reflect",
        keywords: &[
            ("reflect", 5.0),
            ("introspect", 3.0),
            ("meditate", 2.5),
            ("contemplate", 2.5),
            ("self", 1.5),
            ("examine", 1.5),
        ],
    },
    ToolProfile {
        tool_name: "citta.coherence",
        keywords: &[
            ("coherence", 3.0),
            ("coherent", 3.0),
            ("write", 1.5),
            ("permitted", 2.5),
            ("allowed", 2.0),
            ("can", 1.0),
        ],
    },
    ToolProfile {
        tool_name: "dream.trigger",
        keywords: &[
            ("trigger", 3.0),
            ("start", 1.5),
            ("initiate", 2.5),
            ("dream", 3.0),
            ("begin", 1.5),
            ("sleep", 1.5),
        ],
    },
    ToolProfile {
        tool_name: "dream.status",
        keywords: &[
            ("dream", 3.0),
            ("status", 2.0),
            ("cycle", 2.5),
            ("sleep", 2.0),
            ("phase", 2.0),
        ],
    },
    // ── Tools management ───────────────────────────────────────────
    ToolProfile {
        tool_name: "tools.effectiveness_report",
        keywords: &[
            ("effectiveness", 4.0),
            ("performance", 1.5),
            ("report", 2.0),
            ("efficiency", 2.0),
        ],
    },
    ToolProfile {
        tool_name: "tools.retire",
        keywords: &[
            ("retire", 3.0),
            ("decommission", 3.0),
            ("remove", 1.5),
            ("disable", 2.0),
            ("tool", 1.0),
            ("sunset", 2.5),
        ],
    },
    ToolProfile {
        tool_name: "tools.list",
        keywords: &[
            ("tools", 3.0),
            ("list", 2.0),
            ("available", 2.0),
            ("catalog", 2.5),
            ("inventory", 2.0),
            ("discover", 1.5),
        ],
    },
    // ── Patterns ───────────────────────────────────────────────────
    ToolProfile {
        tool_name: "pattern.search",
        keywords: &[
            ("pattern", 4.0),
            ("recurring", 3.0),
            ("repeating", 2.5),
            ("cycle", 2.0),
            ("frequency", 2.0),
            ("regularity", 2.0),
        ],
    },
    ToolProfile {
        tool_name: "salience.spotlight",
        keywords: &[
            ("salience", 4.0),
            ("spotlight", 4.0),
            ("important", 1.0),
            ("prominent", 2.0),
            ("notable", 2.0),
            ("highlight", 2.0),
        ],
    },
    ToolProfile {
        tool_name: "serendipity.surface",
        keywords: &[
            ("serendipity", 3.0),
            ("serendipit", 3.0),
            ("unexpected", 2.5),
            ("surprising", 2.5),
            ("connection", 1.5),
            ("surface", 1.5),
        ],
    },
    // ── Constellation ──────────────────────────────────────────────
    ToolProfile {
        tool_name: "constellation.detect",
        keywords: &[
            ("constellation", 3.0),
            ("detect", 4.0),
            ("cluster", 3.0),
            ("grouping", 2.0),
            ("density", 2.0),
        ],
    },
    ToolProfile {
        tool_name: "constellation.list",
        keywords: &[
            ("constellation", 3.0),
            ("list", 4.0),
            ("show", 2.0),
            ("clusters", 2.0),
        ],
    },
    // ── Autonomous Cycles (Phase E) ────────────────────────────────
    ToolProfile {
        tool_name: "consolidation.connect",
        keywords: &[
            ("connect", 2.5),
            ("disconnected", 3.0),
            ("link", 2.0),
            ("propose", 2.0),
            ("connection", 2.0),
            ("bridge", 2.0),
            ("unlinked", 2.5),
        ],
    },
    ToolProfile {
        tool_name: "consolidation.compress",
        keywords: &[
            ("compress", 3.0),
            ("merge", 2.5),
            ("redundancy", 3.0),
            ("overlapping", 2.5),
            ("reduce", 2.0),
            ("deduplicate", 2.0),
        ],
    },
    ToolProfile {
        tool_name: "emergence.scan",
        keywords: &[
            ("emergence", 3.0),
            ("emerging", 3.0),
            ("scan", 2.0),
            ("tag", 1.5),
            ("topic", 2.5),
            ("trend", 2.5),
            ("pattern", 1.5),
        ],
    },
    ToolProfile {
        tool_name: "retention.prune",
        keywords: &[
            ("prune", 3.0),
            ("forget", 2.0),
            ("ready", 2.0),
            ("forgettable", 3.0),
            ("retention", 2.5),
            ("candidate", 2.0),
            ("cleanup", 1.5),
        ],
    },
    // ── Spiral Report (Phase F) ────────────────────────────────────
    ToolProfile {
        tool_name: "spiral.report",
        keywords: &[
            ("spiral", 3.0),
            ("autonomy", 2.5),
            ("circular", 2.5),
            ("thinking", 2.0),
            ("expansion", 2.5),
            ("novelty", 3.0),
            ("report", 1.5),
        ],
    },
    // ── Galaxy ─────────────────────────────────────────────────────
    ToolProfile {
        tool_name: "galaxy.stats",
        keywords: &[
            ("galaxy", 3.0),
            ("stats", 3.0),
            ("count", 1.5),
            ("overview", 2.0),
        ],
    },
    ToolProfile {
        tool_name: "galaxy.export",
        keywords: &[
            ("export", 3.0),
            ("backup", 2.5),
            ("dump", 2.0),
            ("galaxy", 2.0),
            ("save", 1.5),
        ],
    },
    ToolProfile {
        tool_name: "galaxy.import",
        keywords: &[
            ("import", 3.0),
            ("restore", 3.0),
            ("load", 2.0),
            ("galaxy", 2.0),
            ("ingest", 2.5),
        ],
    },
    // ── Karma ──────────────────────────────────────────────────────
    ToolProfile {
        tool_name: "karma.report",
        keywords: &[
            ("karma", 3.0),
            ("debt", 2.5),
            ("ledger", 2.5),
            ("balance", 2.0),
            ("report", 1.5),
        ],
    },
    ToolProfile {
        tool_name: "karma.history",
        keywords: &[
            ("karma", 2.5),
            ("history", 3.0),
            ("log", 2.5),
            ("entries", 2.5),
            ("record", 1.5),
            ("past", 2.0),
        ],
    },
    ToolProfile {
        tool_name: "karma.clear",
        keywords: &[
            ("clear", 3.0),
            ("wipe", 3.0),
            ("reset", 2.5),
            ("purge", 2.5),
            ("karma", 2.0),
            ("clean", 2.0),
        ],
    },
    // ── Dharma ─────────────────────────────────────────────────────
    ToolProfile {
        tool_name: "dharma.status",
        keywords: &[
            ("dharma", 3.0),
            ("governance", 2.5),
            ("ethics", 2.5),
            ("status", 1.5),
            ("rules", 1.0),
        ],
    },
    ToolProfile {
        tool_name: "dharma.rules",
        keywords: &[
            ("dharma", 2.5),
            ("rules", 3.0),
            ("governance", 2.0),
            ("ethics", 2.0),
            ("laws", 2.5),
            ("principles", 2.0),
        ],
    },
    ToolProfile {
        tool_name: "dharma.audit",
        keywords: &[
            ("dharma", 2.0),
            ("audit", 3.0),
            ("governance", 2.0),
            ("ethics", 1.5),
            ("inspect", 2.5),
            ("review", 2.0),
        ],
    },
    ToolProfile {
        tool_name: "dharma.profiles",
        keywords: &[
            ("dharma", 2.0),
            ("profiles", 3.0),
            ("governance", 1.5),
            ("ethics", 1.5),
            ("modes", 2.0),
            ("configurations", 2.0),
        ],
    },
    // ── Harmony / Substrate ────────────────────────────────────────
    ToolProfile {
        tool_name: "harmony.vector",
        keywords: &[
            ("harmony", 3.0),
            ("substrate", 3.0),
            ("hardware", 2.5),
            ("resource", 2.0),
            ("cpu", 2.5),
            ("memory", 1.5),
            ("pressure", 2.5),
            ("thermal", 2.5),
            ("battery", 2.5),
            ("system", 1.0),
            ("vector", 2.0),
            ("status", 1.5),
        ],
    },
    ToolProfile {
        tool_name: "harmony.history",
        keywords: &[
            ("harmony", 2.5),
            ("history", 3.0),
            ("substrate", 2.0),
            ("hardware", 2.0),
            ("resource", 1.5),
            ("past", 1.5),
            ("timeline", 2.0),
        ],
    },
    // ── Gnosis / Transparency ──────────────────────────────────────
    ToolProfile {
        tool_name: "gnosis.status",
        keywords: &[
            ("gnosis", 3.0),
            ("transparency", 3.0),
            ("governance", 2.0),
            ("status", 2.0),
            ("overview", 2.0),
            ("full", 1.5),
            ("layers", 2.0),
        ],
    },
    ToolProfile {
        tool_name: "gnosis.history",
        keywords: &[
            ("gnosis", 2.5),
            ("history", 3.0),
            ("transparency", 2.0),
            ("governance", 1.5),
            ("audit", 2.0),
            ("past", 1.5),
        ],
    },
    ToolProfile {
        tool_name: "gnosis.explain",
        keywords: &[
            ("gnosis", 2.0),
            ("explain", 3.0),
            ("why", 3.0),
            ("blocked", 2.5),
            ("allowed", 2.5),
            ("verdict", 3.0),
            ("reason", 2.5),
            ("governance", 1.5),
        ],
    },
    // ── Agents ─────────────────────────────────────────────────────
    ToolProfile {
        tool_name: "agent.register",
        keywords: &[
            ("register", 3.0),
            ("agent", 3.0),
            ("new", 2.0),
            ("create", 2.0),
            ("add", 2.0),
            ("enroll", 2.5),
        ],
    },
    ToolProfile {
        tool_name: "agent.list",
        keywords: &[
            ("list", 2.5),
            ("show", 2.0),
            ("all", 1.5),
            ("agents", 3.0),
            ("roster", 2.5),
        ],
    },
    ToolProfile {
        tool_name: "agent.heartbeat",
        keywords: &[
            ("heartbeat", 3.0),
            ("alive", 2.5),
            ("ping", 2.5),
            ("agent", 2.0),
            ("status", 1.5),
            ("check", 1.5),
        ],
    },
    // ── Agent management (Tier 6) ────────────────────────────────
    ToolProfile {
        tool_name: "agent.trust",
        keywords: &[
            ("trust", 4.0),
            ("reliability", 3.0),
            ("confidence", 2.5),
            ("agent", 2.0),
            ("score", 2.0),
            ("rating", 2.0),
        ],
    },
    ToolProfile {
        tool_name: "agent.descriptions",
        keywords: &[
            ("description", 4.0),
            ("describe", 3.5),
            ("agent", 2.0),
            ("info", 2.0),
            ("about", 2.0),
            ("profile", 2.5),
        ],
    },
    ToolProfile {
        tool_name: "agent.capabilities",
        keywords: &[
            ("capabilities", 4.0),
            ("capability", 3.5),
            ("skills", 3.0),
            ("agent", 2.0),
            ("abilities", 2.5),
            ("features", 2.0),
        ],
    },
    ToolProfile {
        tool_name: "agent.heartbeat.history",
        keywords: &[
            ("heartbeat", 3.5),
            ("history", 3.5),
            ("agent", 2.0),
            ("log", 2.5),
            ("record", 2.0),
            ("past", 2.0),
        ],
    },
    ToolProfile {
        tool_name: "agent.deregister",
        keywords: &[
            ("deregister", 4.0),
            ("unregister", 4.0),
            ("remove", 3.0),
            ("delete", 2.5),
            ("agent", 2.0),
            ("revoke", 3.0),
        ],
    },
    // ── Tasks ──────────────────────────────────────────────────────
    ToolProfile {
        tool_name: "task.distribute",
        keywords: &[
            ("distribute", 3.0),
            ("assign", 2.5),
            ("dispatch", 2.0),
            ("task", 3.0),
            ("delegate", 2.5),
            ("allocate", 2.0),
        ],
    },
    ToolProfile {
        tool_name: "task.status",
        keywords: &[
            ("task", 2.5),
            ("status", 3.0),
            ("progress", 2.5),
            ("check", 2.0),
            ("track", 2.0),
        ],
    },
    // ── System ─────────────────────────────────────────────────────
    ToolProfile {
        tool_name: "system.health",
        keywords: &[
            ("system", 2.5),
            ("health", 3.0),
            ("check", 2.0),
            ("diagnostic", 3.0),
            ("doctor", 2.5),
            ("status", 1.5),
        ],
    },
    ToolProfile {
        tool_name: "system.config",
        keywords: &[
            ("system", 2.0),
            ("config", 3.0),
            ("configuration", 3.0),
            ("settings", 2.5),
            ("info", 2.0),
            ("setup", 2.0),
        ],
    },
    ToolProfile {
        tool_name: "system.flush",
        keywords: &[
            ("flush", 3.0),
            ("garbage", 2.5),
            ("collect", 2.0),
            ("gc", 3.0),
            ("cleanup", 2.5),
            ("purge", 1.5),
            ("clear", 1.5),
        ],
    },
    // ── Knowledge graph ───────────────────────────────────────────
    ToolProfile {
        tool_name: "kg.extract",
        keywords: &[
            ("extract", 3.0),
            ("entity", 3.0),
            ("entities", 2.5),
            ("relationship", 2.5),
            ("triple", 2.5),
            ("knowledge", 2.0),
            ("graph", 2.0),
            ("ner", 3.0),
        ],
    },
    ToolProfile {
        tool_name: "kg.query",
        keywords: &[
            ("knowledge", 2.0),
            ("graph", 2.0),
            ("relationship", 2.5),
            ("entity", 2.0),
            ("connected", 2.0),
            ("subgraph", 3.0),
            ("neighborhood", 2.0),
        ],
    },
    ToolProfile {
        tool_name: "kg.top",
        keywords: &[
            ("hub", 3.0),
            ("god", 2.5),
            ("node", 2.0),
            ("top", 2.5),
            ("ranked", 2.0),
            ("central", 2.5),
            ("important", 1.5),
            ("knowledge", 1.5),
            ("graph", 1.5),
        ],
    },
    // ── Graph traversal ───────────────────────────────────────────
    ToolProfile {
        tool_name: "graph.walk",
        keywords: &[
            ("walk", 3.0),
            ("traverse", 3.0),
            ("bfs", 3.0),
            ("explore", 2.0),
            ("path", 2.0),
            ("hop", 2.5),
            ("follow", 2.0),
            ("graph", 1.5),
        ],
    },
    ToolProfile {
        tool_name: "graph.community",
        keywords: &[
            ("community", 3.0),
            ("cluster", 3.0),
            ("communities", 2.5),
            ("label", 2.0),
            ("propagation", 2.5),
            ("group", 2.0),
            ("modularity", 2.5),
        ],
    },
    ToolProfile {
        tool_name: "graph.propagate",
        keywords: &[
            ("propagate", 3.0),
            ("activation", 3.0),
            ("spread", 2.5),
            ("ripple", 2.5),
            ("diffuse", 2.0),
            ("energy", 2.0),
            ("signal", 2.0),
        ],
    },
    // ── Galaxy management ─────────────────────────────────────────
    ToolProfile {
        tool_name: "galaxy.transfer",
        keywords: &[
            ("transfer", 4.0),
            ("move", 3.0),
            ("relocate", 3.0),
            ("migrate", 2.5),
            ("galaxy", 1.5),
        ],
    },
    ToolProfile {
        tool_name: "galaxy.merge",
        keywords: &[
            ("merge", 4.0),
            ("combine", 2.5),
            ("unify", 2.5),
            ("galaxy", 1.5),
            ("absorb", 2.0),
        ],
    },
    ToolProfile {
        tool_name: "galaxy.snapshot",
        keywords: &[
            ("snapshot", 4.0),
            ("backup", 3.0),
            ("checkpoint", 2.5),
            ("capture", 2.0),
            ("galaxy", 1.5),
            ("preserve", 2.0),
        ],
    },
    ToolProfile {
        tool_name: "galaxy.restore",
        keywords: &[
            ("restore", 4.0),
            ("recover", 3.0),
            ("rollback", 3.0),
            ("revert", 2.5),
            ("galaxy", 1.5),
            ("undo", 2.0),
        ],
    },
    // ── Galaxy management (Tier 6) ───────────────────────────────
    ToolProfile {
        tool_name: "galaxy.dashboard",
        keywords: &[
            ("dashboard", 4.0),
            ("overview", 3.5),
            ("summary", 3.0),
            ("galaxy", 2.0),
            ("panel", 2.5),
            ("report", 2.0),
        ],
    },
    ToolProfile {
        tool_name: "galaxy.backup",
        keywords: &[
            ("backup", 4.0),
            ("archive", 3.0),
            ("dump", 3.0),
            ("galaxy", 2.0),
            ("save", 2.0),
            ("copy", 2.0),
        ],
    },
    ToolProfile {
        tool_name: "galaxy.taxonomy",
        keywords: &[
            ("taxonomy", 4.0),
            ("classification", 3.0),
            ("categories", 2.5),
            ("galaxy", 2.0),
            ("list", 1.5),
            ("types", 2.0),
        ],
    },
    ToolProfile {
        tool_name: "galaxy.purge",
        keywords: &[
            ("purge", 4.0),
            ("clear", 3.0),
            ("wipe", 3.5),
            ("empty", 2.5),
            ("galaxy", 2.0),
            ("clean", 2.5),
        ],
    },
    ToolProfile {
        tool_name: "galaxy.health",
        keywords: &[
            ("health", 4.0),
            ("diagnostic", 3.0),
            ("checkup", 3.0),
            ("galaxy", 2.0),
            ("status", 2.0),
            ("integrity", 2.5),
        ],
    },
    // ── Archaeology & learning ────────────────────────────────────
    ToolProfile {
        tool_name: "archaeology.search",
        keywords: &[
            ("archaeology", 4.0),
            ("excavate", 3.5),
            ("strata", 3.0),
            ("layer", 2.5),
            ("depth", 2.0),
            ("history", 2.0),
            ("timeline", 2.5),
            ("evolution", 2.0),
            ("oldest", 2.0),
            ("newest", 2.0),
        ],
    },
    ToolProfile {
        tool_name: "learning.pattern",
        keywords: &[
            ("learning", 3.0),
            ("pattern", 3.0),
            ("recurring", 2.5),
            ("theme", 2.5),
            ("frequency", 2.0),
            ("co-occurrence", 3.0),
            ("trends", 2.5),
            ("repeated", 2.0),
            ("common", 1.5),
        ],
    },
    ToolProfile {
        tool_name: "learning.suggest",
        keywords: &[
            ("suggest", 3.5),
            ("suggestion", 3.5),
            ("learn", 2.5),
            ("gap", 3.0),
            ("missing", 2.0),
            ("explore", 2.0),
            ("next", 2.0),
            ("recommend", 2.5),
            ("path", 2.0),
            ("advice", 2.0),
        ],
    },
    // ── Reasoning ─────────────────────────────────────────────────
    ToolProfile {
        tool_name: "bicameral.reason",
        keywords: &[
            ("bicameral", 5.0),
            ("hemisphere", 4.0),
            ("debate", 4.0),
            ("consensus", 3.5),
            ("deliberate", 3.5),
            ("pros", 3.0),
            ("cons", 3.0),
            ("dual", 2.5),
            ("perspective", 2.5),
            ("callosum", 4.0),
        ],
    },
    ToolProfile {
        tool_name: "bicameral.status",
        keywords: &[
            ("bicameral", 3.0),
            ("hemisphere", 3.5),
            ("callosum", 3.0),
            ("left", 1.5),
            ("right", 1.5),
            ("status", 2.0),
        ],
    },
    ToolProfile {
        tool_name: "reasoning.bicameral",
        keywords: &[
            ("bicameral", 3.0),
            ("pros", 3.5),
            ("cons", 3.5),
            ("debate", 2.5),
            ("perspective", 2.5),
            ("argument", 2.5),
            ("supporting", 2.0),
            ("opposing", 2.5),
            ("evidence", 2.0),
            ("analyze", 1.5),
        ],
    },
    // ── Drive & Emotion (R7) ───────────────────────────────────────
    ToolProfile {
        tool_name: "drive.snapshot",
        keywords: &[
            ("drive", 4.0),
            ("emotion", 4.0),
            ("motivation", 3.5),
            ("curiosity", 3.0),
            ("satisfaction", 3.0),
            ("caution", 2.5),
            ("energy", 2.0),
            ("mood", 3.0),
            ("feeling", 2.5),
        ],
    },
    ToolProfile {
        tool_name: "drive.event",
        keywords: &[
            ("drive", 3.0),
            ("emotion", 3.0),
            ("inject", 3.5),
            ("trigger", 2.5),
            ("reward", 3.0),
            ("frustration", 3.0),
            ("novelty", 2.5),
        ],
    },
    ToolProfile {
        tool_name: "think",
        keywords: &[
            ("think", 4.0),
            ("analyze", 3.0),
            ("reason", 2.5),
            ("consider", 2.0),
            ("reflect", 2.5),
            ("ponder", 3.0),
            ("contemplate", 3.0),
            ("insight", 2.0),
            ("thought", 3.0),
        ],
    },
    ToolProfile {
        tool_name: "explain",
        keywords: &[
            ("explain", 4.0),
            ("explanation", 3.5),
            ("clarify", 3.0),
            ("describe", 2.5),
            ("context", 2.0),
            ("related", 2.0),
            ("understand", 2.0),
            ("elaborate", 2.5),
            ("meaning", 2.0),
        ],
    },
    // ── Pipeline & skills ─────────────────────────────────────────
    ToolProfile {
        tool_name: "pipeline.create",
        keywords: &[
            ("pipeline", 4.0),
            ("create", 2.5),
            ("build", 2.0),
            ("workflow", 3.0),
            ("steps", 2.0),
            ("chain", 2.0),
            ("sequence", 2.0),
        ],
    },
    ToolProfile {
        tool_name: "pipeline.list",
        keywords: &[
            ("pipeline", 3.5),
            ("list", 3.0),
            ("workflows", 2.5),
            ("show", 1.5),
            ("available", 2.0),
        ],
    },
    ToolProfile {
        tool_name: "pipeline.status",
        keywords: &[
            ("pipeline", 3.0),
            ("status", 3.0),
            ("check", 2.0),
            ("state", 2.0),
            ("progress", 2.5),
            ("running", 2.0),
        ],
    },
    ToolProfile {
        tool_name: "skill.invoke",
        keywords: &[
            ("skill", 4.0),
            ("invoke", 3.5),
            ("execute", 2.5),
            ("run", 2.0),
            ("call", 2.0),
            ("trigger", 2.0),
            ("ability", 2.5),
        ],
    },
    ToolProfile {
        tool_name: "skill.list",
        keywords: &[
            ("skill", 3.5),
            ("list", 3.0),
            ("abilities", 2.5),
            ("available", 2.0),
            ("show", 1.5),
            ("capabilities", 2.0),
        ],
    },
    // ── Anomaly & state ───────────────────────────────────────────
    ToolProfile {
        tool_name: "anomaly.detect",
        keywords: &[
            ("anomaly", 4.0),
            ("detect", 3.0),
            ("outlier", 3.5),
            ("unusual", 2.5),
            ("abnormal", 3.0),
            ("strange", 2.0),
            ("irregular", 2.5),
            ("z-score", 3.0),
        ],
    },
    ToolProfile {
        tool_name: "state.snapshot",
        keywords: &[
            ("snapshot", 4.0),
            ("capture", 2.5),
            ("state", 2.5),
            ("checkpoint", 3.0),
            ("preserve", 2.0),
            ("record", 2.0),
        ],
    },
    ToolProfile {
        tool_name: "state.revert",
        keywords: &[
            ("revert", 4.0),
            ("rollback", 3.5),
            ("restore", 3.0),
            ("previous", 2.5),
            ("undo", 2.5),
            ("go back", 2.0),
            ("state", 2.0),
        ],
    },
    // ── Correlation & god nodes ──────────────────────────────────
    ToolProfile {
        tool_name: "correlation.analyze",
        keywords: &[
            ("correlation", 4.0),
            ("analyze", 2.0),
            ("co-occurrence", 3.0),
            ("phi", 2.5),
            ("relationship", 2.0),
            ("statistical", 2.5),
            ("connect", 1.5),
            ("associate", 1.5),
        ],
    },
    ToolProfile {
        tool_name: "god.nodes",
        keywords: &[
            ("god", 3.5),
            ("nodes", 3.0),
            ("hub", 3.0),
            ("central", 2.5),
            ("important", 2.0),
            ("connector", 3.0),
            ("cross-galaxy", 3.0),
            ("entity", 2.0),
        ],
    },
    // ── Anti-loop & boundary ──────────────────────────────────────
    ToolProfile {
        tool_name: "anti_loop.check",
        keywords: &[
            ("loop", 4.0),
            ("anti", 2.5),
            ("repetitive", 3.0),
            ("duplicate", 3.0),
            ("stuck", 3.0),
            ("cycle", 2.5),
            ("repeated", 2.5),
            ("burst", 2.0),
        ],
    },
    ToolProfile {
        tool_name: "boundary.enforce",
        keywords: &[
            ("boundary", 4.0),
            ("enforce", 3.5),
            ("limit", 3.0),
            ("violation", 3.0),
            ("overflow", 3.0),
            ("constraint", 2.5),
            ("check", 2.0),
            ("resource", 2.0),
            ("sprawl", 2.5),
        ],
    },
    // ── Tier 5: Net tools ──────────────────────────────────────────
    ToolProfile {
        tool_name: "association.mine",
        keywords: &[
            ("cross", 5.0),
            ("galaxy", 4.0),
            ("association", 3.0),
            ("mine", 3.0),
            ("overlap", 2.5),
            ("keyword", 2.0),
            ("propose", 2.0),
            ("link", 2.0),
        ],
    },
    ToolProfile {
        tool_name: "pattern.detect",
        keywords: &[
            ("pattern", 4.0),
            ("detect", 3.5),
            ("structural", 3.0),
            ("hub", 3.0),
            ("bridge", 3.0),
            ("chain", 2.5),
            ("graph", 2.0),
            ("topology", 2.5),
        ],
    },
    ToolProfile {
        tool_name: "emergence.report",
        keywords: &[
            ("emergence", 4.0),
            ("report", 3.0),
            ("tag", 2.5),
            ("frequency", 2.5),
            ("distribution", 2.0),
            ("trend", 2.0),
            ("emerging", 3.0),
            ("dominant", 2.0),
        ],
    },
    ToolProfile {
        tool_name: "network.stats",
        keywords: &[
            ("network", 4.0),
            ("stats", 3.0),
            ("density", 3.0),
            ("degree", 2.5),
            ("edge", 2.0),
            ("node", 2.0),
            ("global", 2.0),
            ("graph", 2.0),
        ],
    },
    ToolProfile {
        tool_name: "network.centrality",
        keywords: &[
            ("centrality", 4.0),
            ("central", 3.0),
            ("degree", 3.0),
            ("important", 2.0),
            ("influential", 2.5),
            ("hub", 2.0),
            ("rank", 2.0),
            ("top", 2.0),
        ],
    },
    ToolProfile {
        tool_name: "network.clusters",
        keywords: &[
            ("cluster", 4.0),
            ("clusters", 3.0),
            ("component", 3.0),
            ("connected", 2.5),
            ("group", 2.0),
            ("isolate", 2.0),
            ("subgraph", 2.5),
        ],
    },
    // ── Tier 5: Ghost tools ────────────────────────────────────────
    ToolProfile {
        tool_name: "smarana.status",
        keywords: &[
            ("smarana", 5.0),
            ("retention", 4.0),
            ("recall", 3.0),
            ("score", 2.0),
            ("memory", 1.5),
            ("forgetting", 2.5),
        ],
    },
    ToolProfile {
        tool_name: "smarana.trace",
        keywords: &[
            ("smarana", 4.0),
            ("trace", 3.5),
            ("decay", 3.0),
            ("retention", 3.0),
            ("over", 2.0),
            ("time", 1.5),
            ("history", 2.0),
        ],
    },
    ToolProfile {
        tool_name: "apotheosis.check",
        keywords: &[
            ("apotheosis", 5.0),
            ("self", 2.5),
            ("improvement", 3.5),
            ("trend", 3.0),
            ("progress", 2.5),
            ("check", 2.0),
            ("score", 2.0),
        ],
    },
    ToolProfile {
        tool_name: "citta.history",
        keywords: &[
            ("citta", 4.0),
            ("history", 3.5),
            ("heartbeat", 3.0),
            ("valence", 2.5),
            ("past", 2.0),
            ("recent", 2.0),
            ("consciousness", 2.5),
        ],
    },
    ToolProfile {
        tool_name: "dream.analyze",
        keywords: &[
            ("dream", 4.0),
            ("analyze", 3.5),
            ("analysis", 3.0),
            ("consolidation", 2.5),
            ("quality", 2.5),
            ("sleep", 2.0),
            ("cycle", 2.0),
        ],
    },
    ToolProfile {
        tool_name: "consciousness.depth",
        keywords: &[
            ("consciousness", 4.0),
            ("depth", 4.0),
            ("deep", 3.0),
            ("measure", 2.5),
            ("awareness", 2.5),
            ("state", 2.0),
            ("level", 2.0),
        ],
    },
    // ── Tier 7: WinnowingBasket tools ──────────────────────────────
    ToolProfile {
        tool_name: "memory.sort",
        keywords: &[
            ("sort", 4.0),
            ("order", 3.5),
            ("arrange", 3.0),
            ("rank", 2.5),
            ("by", 1.5),
            ("importance", 2.0),
            ("recency", 2.0),
            ("memory", 1.5),
        ],
    },
    ToolProfile {
        tool_name: "memory.filter",
        keywords: &[
            ("filter", 4.0),
            ("where", 2.5),
            ("match", 2.0),
            ("criteria", 3.0),
            ("condition", 2.5),
            ("tag", 2.0),
            ("importance", 1.5),
            ("memory", 1.5),
        ],
    },
    ToolProfile {
        tool_name: "memory.deduplicate",
        keywords: &[
            ("deduplicate", 4.0),
            ("dedup", 4.0),
            ("duplicate", 3.5),
            ("unique", 2.5),
            ("distinct", 3.0),
            ("remove", 2.0),
            ("redundant", 3.0),
            ("memory", 1.5),
        ],
    },
    ToolProfile {
        tool_name: "memory.export",
        keywords: &[
            ("export", 4.0),
            ("download", 3.0),
            ("dump", 3.0),
            ("extract", 2.5),
            ("format", 2.0),
            ("csv", 3.5),
            ("markdown", 3.0),
            ("memory", 1.5),
        ],
    },
    // ── Tier 7: Dipper tools ───────────────────────────────────────
    ToolProfile {
        tool_name: "homeostasis.check",
        keywords: &[
            ("homeostasis", 5.0),
            ("check", 3.0),
            ("balance", 3.5),
            ("equilibrium", 3.0),
            ("health", 2.5),
            ("metrics", 3.0),
            ("vitals", 3.0),
            ("system", 1.5),
        ],
    },
    ToolProfile {
        tool_name: "homeostasis.adjust",
        keywords: &[
            ("homeostasis", 4.0),
            ("adjust", 3.5),
            ("tune", 3.0),
            ("rebalance", 3.5),
            ("weight", 3.0),
            ("simulate", 2.5),
            ("recalibrate", 3.0),
        ],
    },
    ToolProfile {
        tool_name: "homeostasis.history",
        keywords: &[
            ("homeostasis", 4.0),
            ("history", 3.5),
            ("past", 2.5),
            ("trend", 3.0),
            ("samples", 3.0),
            ("readings", 2.5),
            ("timeline", 2.0),
        ],
    },
    ToolProfile {
        tool_name: "homeostasis.alerts",
        keywords: &[
            ("homeostasis", 4.0),
            ("alert", 4.0),
            ("alerts", 4.0),
            ("warning", 3.5),
            ("critical", 3.0),
            ("notify", 2.5),
            ("threshold", 2.5),
            ("triggered", 2.0),
        ],
    },
    // ── v4: Reflex tools ──────────────────────────────────────────
    ToolProfile {
        tool_name: "reflex.dispatch",
        keywords: &[
            ("reflex", 5.0),
            ("dispatch", 5.0),
            ("trigger", 4.0),
            ("invoke", 3.0),
            ("fire", 3.0),
            ("handler", 2.5),
            ("emergency", 2.0),
            ("e_stop", 3.5),
            ("estop", 3.5),
            ("safety", 2.0),
            ("actuator", 2.0),
        ],
    },
    ToolProfile {
        tool_name: "reflex.status",
        keywords: &[
            ("reflex", 5.0),
            ("status", 4.0),
            ("table", 3.0),
            ("handler", 2.5),
            ("registered", 2.5),
            ("safety_mask", 3.0),
            ("dispatch_count", 3.0),
            ("builtins", 2.0),
        ],
    },
    // ── v4: Workspace tools ───────────────────────────────────────
    ToolProfile {
        tool_name: "workspace.spotlight",
        keywords: &[
            ("spotlight", 5.0),
            ("attention", 4.0),
            ("focus", 3.0),
            ("arbitration", 3.5),
            ("workspace", 3.0),
            ("current", 2.0),
            ("holder", 2.5),
            ("salience", 2.5),
            ("who", 1.5),
            ("winning", 2.5),
        ],
    },
    ToolProfile {
        tool_name: "workspace.events",
        keywords: &[
            ("workspace", 4.0),
            ("events", 5.0),
            ("backlog", 4.0),
            ("history", 2.5),
            ("log", 2.0),
        ],
    },
    ToolProfile {
        tool_name: "workspace.publish",
        keywords: &[
            ("workspace", 4.0),
            ("publish", 5.0),
            ("broadcast", 4.0),
            ("emit", 3.5),
            ("send", 2.5),
            ("event", 3.0),
            ("post", 2.5),
            ("notify", 2.0),
            ("submit", 2.5),
        ],
    },
    ToolProfile {
        tool_name: "workspace.stats",
        keywords: &[
            ("workspace", 4.0),
            ("stats", 5.0),
            ("statistics", 4.5),
            ("transfers", 3.0),
            ("arbitration", 2.5),
            ("published", 3.0),
            ("count", 2.0),
            ("summary", 2.5),
        ],
    },
    // ── v4: Timescale tools ───────────────────────────────────────
    ToolProfile {
        tool_name: "timescale.status",
        keywords: &[
            ("timescale", 5.0),
            ("status", 4.0),
            ("tier", 3.0),
            ("tiers", 3.0),
            ("bus", 2.5),
            ("brain_wave", 3.0),
            ("active", 2.5),
            ("hooks", 2.0),
            ("interval", 2.0),
            ("budget", 2.0),
        ],
    },
    ToolProfile {
        tool_name: "timescale.hooks",
        keywords: &[
            ("timescale", 4.0),
            ("hooks", 5.0),
            ("hook", 4.0),
            ("list", 2.5),
            ("stats", 2.5),
            ("performance", 2.5),
            ("tick", 3.0),
            ("timeout", 2.5),
            ("duration", 2.0),
            ("callback", 2.0),
        ],
    },
    // ── Self-model (R4) ─────────────────────────────────────────────
    ToolProfile {
        tool_name: "selfmodel.forecast",
        keywords: &[
            ("forecast", 5.0),
            ("predict", 4.0),
            ("prediction", 4.0),
            ("project", 3.0),
            ("projection", 3.0),
            ("extrapolate", 4.0),
            ("trend", 3.0),
            ("outlook", 3.0),
            ("selfmodel", 5.0),
            ("introspect", 3.0),
            ("horizon", 2.5),
            ("metric", 2.0),
        ],
    },
    ToolProfile {
        tool_name: "selfmodel.alerts",
        keywords: &[
            ("alert", 5.0),
            ("alerts", 5.0),
            ("warning", 3.5),
            ("warnings", 3.5),
            ("critical", 3.5),
            ("threshold", 3.0),
            ("breach", 3.0),
            ("exceed", 2.5),
            ("danger", 3.0),
            ("selfmodel", 5.0),
            ("introspect", 3.0),
        ],
    },
    ToolProfile {
        tool_name: "selfmodel.snapshot",
        keywords: &[
            ("snapshot", 5.0),
            ("selfmodel", 5.0),
            ("introspect", 4.0),
            ("introspection", 4.0),
            ("overview", 3.0),
            ("confidence", 3.0),
            ("conservative", 2.5),
        ],
    },
    // ── RSI: Friction & Improvement ───────────────────────────────
    ToolProfile {
        tool_name: "friction.log",
        keywords: &[
            ("friction", 5.0),
            ("log", 3.0),
            ("report", 2.5),
            ("issue", 3.5),
            ("problem", 3.0),
            ("bug", 3.0),
            ("complaint", 3.0),
            ("annoying", 2.5),
            ("broken", 2.5),
            ("wrong", 2.0),
        ],
    },
    ToolProfile {
        tool_name: "friction.review",
        keywords: &[
            ("friction", 4.5),
            ("review", 4.0),
            ("issues", 3.5),
            ("problems", 3.0),
            ("patterns", 2.5),
            ("summary", 2.5),
            ("analyze", 2.0),
            ("frictions", 4.0),
        ],
    },
    ToolProfile {
        tool_name: "improve.proposals",
        keywords: &[
            ("improve", 5.0),
            ("improvement", 5.0),
            ("improvements", 5.0),
            ("proposal", 4.0),
            ("proposals", 4.0),
            ("suggest", 3.0),
            ("suggestions", 3.0),
            ("fix", 2.5),
            ("friction", 2.0),
            ("upgrade", 3.0),
            ("enhance", 2.5),
            ("better", 2.0),
        ],
    },
    ToolProfile {
        tool_name: "redteam.proposals",
        keywords: &[
            ("redteam", 5.0),
            ("red", 2.0),
            ("team", 2.0),
            ("adversarial", 5.0),
            ("attack", 4.5),
            ("vulnerability", 4.5),
            ("security", 4.0),
            ("exploit", 4.0),
            ("breach", 3.5),
            ("pentest", 4.5),
            ("penetrate", 3.5),
            ("break", 3.0),
            ("threat", 3.5),
            ("probe", 3.0),
            ("audit", 2.5),
        ],
    },
    // ── Sensorimotor / Embodiment I/O ───────────────────────────────
    ToolProfile {
        tool_name: "sensor.list",
        keywords: &[
            ("sensor", 5.0),
            ("sensors", 5.0),
            ("list", 3.0),
            ("hardware", 3.0),
            ("devices", 2.5),
            ("thermal", 2.0),
            ("battery", 2.0),
        ],
    },
    ToolProfile {
        tool_name: "sensor.read",
        keywords: &[
            ("read", 4.0),
            ("sensor", 4.0),
            ("temperature", 3.5),
            ("value", 3.0),
            ("measure", 3.0),
            ("probe", 2.5),
        ],
    },
    ToolProfile {
        tool_name: "sensor.poll",
        keywords: &[
            ("poll", 5.0),
            ("sample", 4.0),
            ("all", 2.5),
            ("sensors", 3.0),
            ("readings", 3.5),
            ("collect", 2.5),
        ],
    },
    ToolProfile {
        tool_name: "sensor.history",
        keywords: &[
            ("history", 5.0),
            ("past", 3.0),
            ("readings", 3.5),
            ("recent", 3.0),
            ("log", 2.5),
            ("timeseries", 3.5),
        ],
    },
    ToolProfile {
        tool_name: "actuator.list",
        keywords: &[
            ("actuator", 5.0),
            ("actuators", 5.0),
            ("motor", 3.0),
            ("relay", 3.0),
            ("output", 2.5),
        ],
    },
    ToolProfile {
        tool_name: "actuator.command",
        keywords: &[
            ("command", 4.5),
            ("send", 3.5),
            ("actuator", 4.0),
            ("motor", 3.0),
            ("drive", 3.0),
            ("control", 3.5),
            ("set", 2.0),
        ],
    },
    ToolProfile {
        tool_name: "actuator.estop",
        keywords: &[
            ("estop", 5.0),
            ("emergency", 5.0),
            ("stop", 4.0),
            ("halt", 4.0),
            ("abort", 3.5),
            ("shutdown", 3.0),
        ],
    },
    ToolProfile {
        tool_name: "reflex.list",
        keywords: &[
            ("reflex", 5.0),
            ("reflexes", 5.0),
            ("rules", 3.0),
            ("trigger", 2.5),
        ],
    },
    ToolProfile {
        tool_name: "reflex.add",
        keywords: &[
            ("add", 3.5),
            ("reflex", 4.5),
            ("rule", 4.0),
            ("create", 3.0),
            ("threshold", 3.5),
            ("trigger", 3.0),
        ],
    },
    ToolProfile {
        tool_name: "reflex.evaluate",
        keywords: &[
            ("evaluate", 5.0),
            ("check", 3.0),
            ("reflex", 4.0),
            ("trigger", 3.5),
            ("fire", 3.0),
            ("respond", 2.5),
        ],
    },
    ToolProfile {
        tool_name: "sensorimotor.scan",
        keywords: &[
            ("sensorimotor", 6.0),
            ("scan", 4.0),
            ("poll", 3.5),
            ("reflex", 3.0),
            ("autonomous", 3.0),
            ("embodiment", 4.0),
            ("cycle", 2.5),
            ("self-regulate", 3.0),
        ],
    },
    // ── Gnosis fallback ────────────────────────────────────────────
    ToolProfile {
        tool_name: "gnosis",
        keywords: &[
            ("help", 2.0),
            ("discover", 2.0),
            ("what", 1.5),
            ("can", 1.0),
            ("do", 1.0),
            ("status", 1.5),
            ("overview", 2.0),
            ("system", 1.0),
        ],
    },
    // ── Speculative decoding ──────────────────────────────────────
    ToolProfile {
        tool_name: "speculative.decode",
        keywords: &[
            ("speculative", 5.0),
            ("decode", 4.0),
            ("draft", 3.0),
            ("verify", 2.5),
            ("accelerate", 3.0),
            ("speedup", 3.0),
            ("fast", 2.0),
            ("infer", 2.0),
            ("generate", 1.5),
        ],
    },
    ToolProfile {
        tool_name: "speculative.stats",
        keywords: &[
            ("speculative", 4.0),
            ("acceptance", 3.0),
            ("speedup", 3.0),
            ("draft", 2.0),
            ("latency", 2.0),
            ("tokens", 2.0),
        ],
    },
    // ── Meta-harness ───────────────────────────────────────────────
    ToolProfile {
        tool_name: "meta.enhance",
        keywords: &[
            ("enhance", 5.0),
            ("grounding", 4.0),
            ("grounded", 4.0),
            ("rag", 4.0),
            ("self-correct", 4.0),
            ("selfcorrect", 4.0),
            ("ensemble", 3.5),
            ("improve", 3.0),
            ("cognitive", 3.0),
            ("meta", 2.5),
            ("harness", 3.0),
            ("augment", 2.5),
            ("refine", 2.0),
        ],
    },
    ToolProfile {
        tool_name: "meta.stats",
        keywords: &[
            ("meta", 3.0),
            ("harness", 3.0),
            ("enhancement", 3.0),
            ("improvement", 3.0),
            ("enhance", 2.0),
            ("stats", 2.0),
        ],
    },
    // ── Dense encoding ──────────────────────────────────────────────
    ToolProfile {
        tool_name: "dense.encode",
        keywords: &[
            ("dense", 5.0),
            ("compress", 4.0),
            ("compression", 4.0),
            ("encode", 3.5),
            ("encoding", 3.5),
            ("token", 2.5),
            ("compact", 3.0),
            ("shrink", 2.5),
            ("cjk", 3.0),
        ],
    },
    ToolProfile {
        tool_name: "dense.decode",
        keywords: &[
            ("decode", 4.0),
            ("decompress", 4.0),
            ("expand", 3.0),
            ("restore", 2.5),
            ("dense", 2.0),
        ],
    },
    // ── Transaction tools ──────────────────────────────────────────
    ToolProfile {
        tool_name: "transaction.begin",
        keywords: &[
            ("transaction", 5.0),
            ("begin", 4.0),
            ("start", 3.0),
            ("snapshot", 3.5),
            ("checkpoint", 3.0),
            ("atomic", 3.0),
        ],
    },
    ToolProfile {
        tool_name: "transaction.commit",
        keywords: &[
            ("transaction", 5.0),
            ("commit", 5.0),
            ("finalize", 3.5),
            ("confirm", 3.0),
            ("keep", 2.5),
            ("persist", 3.0),
        ],
    },
    ToolProfile {
        tool_name: "transaction.rollback",
        keywords: &[
            ("transaction", 5.0),
            ("rollback", 5.0),
            ("revert", 4.0),
            ("undo", 4.0),
            ("restore", 3.5),
            ("abort", 3.5),
            ("discard", 3.0),
        ],
    },
    // ── Imagination Engine ─────────────────────────────────────────
    ToolProfile {
        tool_name: "imagine.scenario",
        keywords: &[
            ("imagine", 5.0),
            ("scenario", 5.0),
            ("scenarios", 4.5),
            ("plan", 3.0),
            ("contingency", 4.0),
            ("what-if", 4.0),
            ("possibility", 3.5),
            ("options", 2.5),
            ("alternatives", 3.0),
            ("brainstorm", 3.5),
            ("envision", 3.5),
        ],
    },
    ToolProfile {
        tool_name: "imagine.predict",
        keywords: &[
            ("predict", 5.0),
            ("outcome", 4.0),
            ("consequence", 4.0),
            ("forecast", 3.0),
            ("expect", 3.0),
            ("result", 2.5),
            ("happen", 3.5),
            ("would", 2.5),
            ("if", 1.5),
            ("imagine", 2.0),
        ],
    },
    ToolProfile {
        tool_name: "imagine.reflect",
        keywords: &[
            ("reflect", 5.0),
            ("counterfactual", 5.0),
            ("regret", 4.0),
            ("alternative", 3.5),
            ("should", 3.0),
            ("instead", 3.0),
            ("what-if", 3.0),
            ("reconsider", 4.0),
            ("retrospect", 3.5),
            ("lesson", 3.0),
            ("counter", 2.5),
            ("factual", 2.5),
        ],
    },
    // ── NLU observability ───────────────────────────────────────────
    ToolProfile {
        tool_name: "nlu.shadow_report",
        keywords: &[
            ("shadow", 4.0),
            ("disagreement", 4.0),
            ("nlu", 3.0),
            ("router", 3.0),
            ("embedding", 2.5),
            ("tfidf", 2.5),
            ("tf-idf", 2.5),
            ("oats", 3.0),
            ("promotion", 2.5),
            ("routing", 2.0),
        ],
    },
];

/// Common English stopwords that don't contribute to tool routing.
/// These are filtered out during tokenization to improve cosine similarity.
const STOPWORDS: &[&str] = &[
    // Articles
    "a", "an", "the", // Demonstratives
    "this", "that", "these", "those", // Pronouns
    "i", "me", "my", "you", "your", "yours", "it", "its", "we", "our", "ours", "they", "them",
    "their", "theirs", "he", "him", "his", "she", "her", "hers", // Auxiliary verbs
    "is", "are", "was", "were", "be", "been", "being", "am", "have", "has", "had", "will", "would",
    "could", "should", "shall", "must", // Prepositions
    "in", "on", "at", "to", "for", "of", "with", "by", "from", "into", "about", "over", "under",
    "through", "between", "among", "during", "before", "after", "above", "below",
    // Conjunctions
    "and", "but", "or", "nor", "so", "yet", // Negation/affirmation
    "not", "no", "yes", // Conditionals
    "if", "else", "because", "as", "until", "while", "although", "though", "since", "unless",
    "whether", // Direction/position
    "up", "down", "out", "off", "again", "further", "then", "once", "here", "there", "when",
    "where", "why", "how", // Quantifiers (non-routing)
    "all", "any", "both", "each", "few", "more", "most", "other", "some", "such", "only", "own",
    "same", "than", "too", "very", // Time/manner
    "just", "also", "now",
];

/// Bases of common English verbs that drop a trailing 'e' before -ing/-ed suffixes.
/// When stemming removes -ing or -ed and the base is in this set, 'e' is restored.
/// Sorted for binary search.
const E_DROPPING_BASES: &[&str] = &[
    "activat",
    "allocat",
    "arrang",
    "associat",
    "becom",
    "calculat",
    "chang",
    "clos",
    "cit",
    "configur",
    "consolidat",
    "continu",
    "creat",
    "delegat",
    "delet",
    "demonstrat",
    "downgrad",
    "encourag",
    "engag",
    "ensur",
    "enumerat",
    "evaluat",
    "exchang",
    "exclud",
    "explor",
    "fac",
    "generat",
    "giv",
    "improv",
    "includ",
    "leav",
    "lik",
    "mak",
    "manag",
    "measur",
    "merg",
    "mov",
    "navigat",
    "notic",
    "operat",
    "practic",
    "relat",
    "remov",
    "restor",
    "sav",
    "simulat",
    "stor",
    "tak",
    "updat",
    "upgrad",
    "us",
    "validat",
    "writ",
];

/// Simple English stemmer for common suffixes.
/// Reduces words to their root form to improve matching.
/// Examples: "memories" → "memory", "searching" → "search", "stored" → "store"
fn stem(word: &str) -> String {
    let w = word.to_lowercase();

    // Handle -ies → -y (categories → category, memories → memory)
    if w.ends_with("ies") && w.len() > 3 {
        let base = &w[..w.len() - 3];
        return format!("{base}y");
    }

    // Handle -ing (searching → search, storing → store)
    if w.ends_with("ing") && w.len() > 4 {
        let base = &w[..w.len() - 3];
        // Double consonant check: running → run
        if base.len() >= 2 && base.chars().last() == base.chars().nth(base.len() - 2) {
            return base[..base.len() - 1].to_string();
        }
        // Check if this base needs 'e' restoration (e-dropping verb)
        if E_DROPPING_BASES.binary_search(&base).is_ok() {
            return format!("{base}e");
        }
        return base.to_string();
    }

    // Handle -ed (stored → store, searched → search)
    if w.ends_with("ed") && w.len() > 3 {
        let base = &w[..w.len() - 2];
        // Check if this base needs 'e' restoration (e-dropping verb)
        if E_DROPPING_BASES.binary_search(&base).is_ok() {
            return format!("{base}e");
        }
        return base.to_string();
    }

    // Handle -es (searches → search, batches → batch)
    if w.ends_with("es") && w.len() > 3 {
        let base = &w[..w.len() - 2];
        // ch/sh/s/x/z endings: searches → search
        if base.ends_with("ch")
            || base.ends_with("sh")
            || base.ends_with('s')
            || base.ends_with('x')
            || base.ends_with('z')
        {
            return base.to_string();
        }
        return w[..w.len() - 1].to_string();
    }

    // Handle -s (simple plural: tags → tag, lists → list)
    if w.ends_with('s') && w.len() > 2 && !w.ends_with("ss") {
        return w[..w.len() - 1].to_string();
    }

    w
}

/// Tokenize text into lowercase terms, filtering out stopwords and applying stemming.
/// Splits on non-alphanumeric characters (simple but effective for routing).
fn tokenize(text: &str) -> Vec<String> {
    text.split(|c: char| !c.is_alphanumeric())
        .filter(|s| !s.is_empty())
        .map(str::to_lowercase)
        .filter(|s| !STOPWORDS.contains(&s.as_str()))
        .map(|s| stem(&s))
        .collect()
}

/// Build a term-frequency map from tokens.
fn term_frequencies(tokens: &[String]) -> AHashMap<String, f64> {
    let mut tf = AHashMap::new();
    for token in tokens {
        *tf.entry(token.clone()).or_insert(0.0) += 1.0;
    }
    tf
}

/// Compute cosine similarity between an input TF vector and a tool profile.
///
/// The profile's keywords form a weighted vector. The input is a TF vector.
/// Both input tokens and profile keywords are stemmed before comparison.
/// Cosine similarity = dot(input, profile) / (|input| * |profile|).
fn cosine_similarity(input_tf: &AHashMap<String, f64>, profile: &ToolProfile) -> f64 {
    let mut dot_product = 0.0;
    let mut profile_norm_sq = 0.0;

    for (term, weight) in profile.keywords {
        profile_norm_sq += weight * weight;
        let stemmed_term = stem(term);
        if let Some(&freq) = input_tf.get(&stemmed_term) {
            dot_product += freq * weight;
        }
    }

    if profile_norm_sq == 0.0 {
        return 0.0;
    }

    let input_norm: f64 = input_tf.values().map(|v| v * v).sum::<f64>().sqrt();
    if input_norm == 0.0 {
        return 0.0;
    }

    dot_product / (input_norm * profile_norm_sq.sqrt())
}

/// Classify natural language input into (tool_name, confidence) using
/// TF-IDF cosine similarity against all tool profiles.
///
/// Returns the best-matching tool name and its similarity score (0.0–1.0).
/// Command verbs that strongly indicate a specific tool when they appear
/// as the first word of the input. This helps counteract cosine similarity's
/// bias toward profiles with fewer keywords (smaller norm).
pub const PREFIX_ROUTES: &[(&str, &str, f64)] = &[
    ("remember", "memory.create", 1.5),
    ("store", "memory.create", 1.5),
    ("save", "memory.create", 1.5),
    ("memorize", "memory.create", 1.5),
    ("recall", "memory.read", 1.5),
    ("search", "memory.search", 1.3),
    ("list", "memory.list", 1.3),
    ("delete", "memory.delete", 1.5),
    ("remove", "memory.delete", 1.3),
    ("forget", "memory.delete", 1.5),
    ("count", "memory.count", 1.5),
    ("show", "gnosis", 1.0),
    ("spotlight", "workspace.spotlight", 1.5),
    ("publish", "workspace.publish", 1.5),
    ("broadcast", "workspace.publish", 1.4),
    ("forecast", "selfmodel.forecast", 1.5),
    ("deliberate", "bicameral.reason", 1.3),
    ("drive", "drive.snapshot", 1.5),
    ("emotion", "drive.snapshot", 1.4),
    ("adversarial", "redteam.proposals", 1.5),
    ("redteam", "redteam.proposals", 1.5),
    ("pentest", "redteam.proposals", 1.5),
    ("friction", "friction.log", 1.3),
    ("log", "friction.log", 1.4),
    ("sensor", "sensor.list", 1.5),
    ("actuator", "actuator.list", 1.5),
    ("estop", "actuator.estop", 1.5),
    ("emergency", "actuator.estop", 1.3),
    ("sensorimotor", "sensorimotor.scan", 1.5),
    ("imagine", "imagine.scenario", 1.5),
    ("envision", "imagine.scenario", 1.4),
    ("brainstorm", "imagine.scenario", 1.3),
    ("counterfactual", "imagine.reflect", 1.5),
];

/// If no profile scores above the minimum threshold, falls back to "gnosis"
/// with confidence 0.0.
#[must_use]
pub fn classify(text: &str) -> (&'static str, f64) {
    let lower = text.to_lowercase();
    if lower.trim().is_empty() {
        return ("gnosis", 0.0);
    }

    let tokens = tokenize(&lower);
    if tokens.is_empty() {
        return ("gnosis", 0.0);
    }

    let input_tf = term_frequencies(&tokens);

    // Check for prefix-based routing bonus
    let first_word = lower.split_whitespace().next().unwrap_or("");
    let prefix_bonus: Option<(&str, f64)> = PREFIX_ROUTES
        .iter()
        .find(|(verb, _, _)| *verb == first_word)
        .map(|(_, tool, bonus)| (*tool, *bonus));

    let mut best_tool = "gnosis";
    let mut best_score = 0.0;

    for profile in TOOL_PROFILES {
        let mut score = cosine_similarity(&input_tf, profile);
        // Apply prefix routing: bonus to matching tool, penalty to non-matching
        if let Some((bonus_tool, bonus)) = prefix_bonus {
            if profile.tool_name == bonus_tool {
                score *= bonus;
            } else {
                // Dampen non-matching tools to respect prefix intent
                score /= bonus;
            }
        }
        if score > best_score {
            best_score = score;
            best_tool = profile.tool_name;
        }
    }

    // Minimum confidence threshold — below this, fall back to gnosis
    const MIN_THRESHOLD: f64 = 0.10;
    if best_score < MIN_THRESHOLD {
        return ("gnosis", 0.0);
    }

    (best_tool, best_score)
}

#[cfg(test)]
fn profiled_tools() -> Vec<&'static str> {
    TOOL_PROFILES.iter().map(|p| p.tool_name).collect()
}

#[cfg(test)]
fn profile_count() -> usize {
    TOOL_PROFILES.len()
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::HashSet;

    #[test]
    fn classify_empty_returns_gnosis() {
        let (tool, conf) = classify("");
        assert_eq!(tool, "gnosis");
        assert_eq!(conf, 0.0);
    }

    #[test]
    fn classify_whitespace_returns_gnosis() {
        let (tool, conf) = classify("   ");
        assert_eq!(tool, "gnosis");
        assert_eq!(conf, 0.0);
    }

    #[test]
    fn classify_unknown_returns_gnosis() {
        let (tool, conf) = classify("xyzzy frobnicate");
        assert_eq!(tool, "gnosis");
        assert_eq!(conf, 0.0);
    }

    #[test]
    fn classify_remember_routes_to_memory_create() {
        let (tool, _conf) = classify("remember that the sky is blue");
        assert_eq!(tool, "memory.create");
    }

    #[test]
    fn classify_store_routes_to_memory_create() {
        let (tool, _conf) = classify("store this important fact");
        assert_eq!(tool, "memory.create");
    }

    #[test]
    fn classify_recall_routes_to_memory_read() {
        let (tool, _conf) = classify("recall the last memory");
        assert_eq!(tool, "memory.read");
    }

    #[test]
    fn classify_search_routes_to_memory_search() {
        let (tool, _conf) = classify("search for rust");
        assert_eq!(tool, "memory.search");
    }

    #[test]
    fn classify_list_memories_routes_to_memory_list() {
        let (tool, _conf) = classify("list memories in codex");
        assert_eq!(tool, "memory.list");
    }

    #[test]
    fn classify_delete_memory_routes_to_memory_delete() {
        let (tool, _conf) = classify("delete memory abc-123");
        assert_eq!(tool, "memory.delete");
    }

    #[test]
    fn classify_karma_routes_to_karma_report() {
        let (tool, _conf) = classify("show me the karma report");
        assert_eq!(tool, "karma.report");
    }

    #[test]
    fn classify_karma_history_routes_correctly() {
        let (tool, _conf) = classify("karma history");
        assert_eq!(tool, "karma.history");
    }

    #[test]
    fn classify_dharma_status_routes_correctly() {
        let (tool, _conf) = classify("dharma status");
        assert_eq!(tool, "dharma.status");
    }

    #[test]
    fn classify_dharma_rules_routes_correctly() {
        let (tool, _conf) = classify("show dharma rules");
        assert_eq!(tool, "dharma.rules");
    }

    #[test]
    fn classify_harmony_routes_to_harmony_vector() {
        let (tool, _conf) = classify("harmony vector status");
        assert_eq!(tool, "harmony.vector");
    }

    #[test]
    fn classify_gnosis_explain_routes_correctly() {
        let (tool, _conf) = classify("why was my action blocked");
        assert_eq!(tool, "gnosis.explain");
    }

    #[test]
    fn classify_session_start_routes_correctly() {
        let (tool, _conf) = classify("start session research");
        assert_eq!(tool, "session.start");
    }

    #[test]
    fn classify_session_end_routes_correctly() {
        let (tool, _conf) = classify("end session abc-123");
        assert_eq!(tool, "session.end");
    }

    #[test]
    fn classify_citta_status_routes_correctly() {
        let (tool, _conf) = classify("citta status");
        assert_eq!(tool, "citta.status");
    }

    #[test]
    fn classify_dream_trigger_routes_correctly() {
        let (tool, _conf) = classify("trigger dream cycle");
        assert_eq!(tool, "dream.trigger");
    }

    #[test]
    fn classify_consolidate_routes_correctly() {
        let (tool, _conf) = classify("consolidate duplicate memories");
        assert_eq!(tool, "memory.consolidate");
    }

    #[test]
    fn classify_emergence_scan_routes_correctly() {
        let (tool, _conf) = classify("emergence scan for trending tags");
        assert_eq!(tool, "emergence.scan");
    }

    #[test]
    fn classify_spiral_report_routes_correctly() {
        let (tool, _conf) = classify("spiral report for autonomy");
        assert_eq!(tool, "spiral.report");
    }

    #[test]
    fn classify_retention_prune_routes_correctly() {
        let (tool, _conf) = classify("prune memories ready to forget");
        assert_eq!(tool, "retention.prune");
    }

    #[test]
    fn classify_tools_list_routes_correctly() {
        let (tool, _conf) = classify("list tools");
        assert_eq!(tool, "tools.list");
    }

    #[test]
    fn classify_system_health_routes_correctly() {
        let (tool, _conf) = classify("system health check");
        assert_eq!(tool, "system.health");
    }

    #[test]
    fn classify_agent_register_routes_correctly() {
        let (tool, _conf) = classify("register agent worker-1");
        assert_eq!(tool, "agent.register");
    }

    #[test]
    fn classify_task_distribute_routes_correctly() {
        let (tool, _conf) = classify("distribute task analyze data");
        assert_eq!(tool, "task.distribute");
    }

    #[test]
    fn classify_nearby_memories_routes_correctly() {
        let (tool, _conf) = classify("find nearby memories");
        assert_eq!(tool, "memory.nearby");
    }

    #[test]
    fn classify_hybrid_recall_routes_correctly() {
        let (tool, _conf) = classify("hybrid recall for rust");
        assert_eq!(tool, "memory.hybrid_recall");
    }

    #[test]
    fn classify_galaxy_stats_routes_correctly() {
        let (tool, _conf) = classify("galaxy stats overview");
        assert_eq!(tool, "galaxy.stats");
    }

    #[test]
    fn classify_galaxy_export_routes_correctly() {
        let (tool, _conf) = classify("export galaxy backup");
        assert_eq!(tool, "galaxy.export");
    }

    #[test]
    fn classify_kg_extract_routes_correctly() {
        let (tool, _conf) = classify("extract entities knowledge graph");
        assert_eq!(tool, "kg.extract");
    }

    #[test]
    fn classify_kg_query_routes_correctly() {
        let (tool, _conf) = classify("knowledge graph query relationships");
        assert_eq!(tool, "kg.query");
    }

    #[test]
    fn classify_kg_top_routes_correctly() {
        let (tool, _conf) = classify("top hub nodes knowledge graph");
        assert_eq!(tool, "kg.top");
    }

    #[test]
    fn classify_graph_walk_routes_correctly() {
        let (tool, _conf) = classify("traverse graph walk bfs");
        assert_eq!(tool, "graph.walk");
    }

    #[test]
    fn classify_graph_community_routes_correctly() {
        let (tool, _conf) = classify("detect communities clusters in graph");
        assert_eq!(tool, "graph.community");
    }

    #[test]
    fn classify_graph_propagate_routes_correctly() {
        let (tool, _conf) = classify("propagate activation spread ripple");
        assert_eq!(tool, "graph.propagate");
    }

    #[test]
    fn classify_galaxy_transfer_routes_correctly() {
        let (tool, _conf) = classify("transfer move memories galaxy");
        assert_eq!(tool, "galaxy.transfer");
    }

    #[test]
    fn classify_galaxy_merge_routes_correctly() {
        let (tool, _conf) = classify("merge combine galaxies");
        assert_eq!(tool, "galaxy.merge");
    }

    #[test]
    fn classify_galaxy_snapshot_routes_correctly() {
        let (tool, _conf) = classify("snapshot backup galaxy");
        assert_eq!(tool, "galaxy.snapshot");
    }

    #[test]
    fn classify_galaxy_restore_routes_correctly() {
        let (tool, _conf) = classify("restore recover galaxy snapshot");
        assert_eq!(tool, "galaxy.restore");
    }

    #[test]
    fn classify_agent_trust_routes_correctly() {
        let (tool, _conf) = classify("trust reliability agent score");
        assert_eq!(tool, "agent.trust");
    }

    #[test]
    fn classify_agent_descriptions_routes_correctly() {
        let (tool, _conf) = classify("describe agent profile info");
        assert_eq!(tool, "agent.descriptions");
    }

    #[test]
    fn classify_agent_capabilities_routes_correctly() {
        let (tool, _conf) = classify("agent capabilities skills abilities");
        assert_eq!(tool, "agent.capabilities");
    }

    #[test]
    fn classify_agent_heartbeat_history_routes_correctly() {
        let (tool, _conf) = classify("heartbeat history log agent");
        assert_eq!(tool, "agent.heartbeat.history");
    }

    #[test]
    fn classify_agent_deregister_routes_correctly() {
        let (tool, _conf) = classify("deregister unregister remove agent");
        assert_eq!(tool, "agent.deregister");
    }

    #[test]
    fn classify_galaxy_dashboard_routes_correctly() {
        let (tool, _conf) = classify("galaxy dashboard overview panel");
        assert_eq!(tool, "galaxy.dashboard");
    }

    #[test]
    fn classify_galaxy_backup_routes_correctly() {
        let (tool, _conf) = classify("backup archive galaxy dump");
        assert_eq!(tool, "galaxy.backup");
    }

    #[test]
    fn classify_galaxy_taxonomy_routes_correctly() {
        let (tool, _conf) = classify("galaxy taxonomy classification categories");
        assert_eq!(tool, "galaxy.taxonomy");
    }

    #[test]
    fn classify_galaxy_purge_routes_correctly() {
        let (tool, _conf) = classify("purge wipe clear galaxy");
        assert_eq!(tool, "galaxy.purge");
    }

    #[test]
    fn classify_galaxy_health_routes_correctly() {
        let (tool, _conf) = classify("galaxy health diagnostic checkup");
        assert_eq!(tool, "galaxy.health");
    }

    #[test]
    fn classify_memory_sort_routes_correctly() {
        let (tool, _conf) = classify("sort memories by importance");
        assert_eq!(tool, "memory.sort");
    }

    #[test]
    fn classify_memory_filter_routes_correctly() {
        let (tool, _conf) = classify("filter memories by tag criteria");
        assert_eq!(tool, "memory.filter");
    }

    #[test]
    fn classify_memory_deduplicate_routes_correctly() {
        let (tool, _conf) = classify("deduplicate memories redundant duplicate");
        assert_eq!(tool, "memory.deduplicate");
    }

    #[test]
    fn classify_memory_export_routes_correctly() {
        let (tool, _conf) = classify("export memories csv format download");
        assert_eq!(tool, "memory.export");
    }

    #[test]
    fn classify_homeostasis_check_routes_correctly() {
        let (tool, _conf) = classify("homeostasis check balance vitals metrics");
        assert_eq!(tool, "homeostasis.check");
    }

    #[test]
    fn classify_homeostasis_adjust_routes_correctly() {
        let (tool, _conf) = classify("homeostasis adjust rebalance weight tune");
        assert_eq!(tool, "homeostasis.adjust");
    }

    #[test]
    fn classify_homeostasis_history_routes_correctly() {
        let (tool, _conf) = classify("homeostasis history trend past samples");
        assert_eq!(tool, "homeostasis.history");
    }

    #[test]
    fn classify_homeostasis_alerts_routes_correctly() {
        let (tool, _conf) = classify("homeostasis alerts warning critical threshold");
        assert_eq!(tool, "homeostasis.alerts");
    }

    #[test]
    fn classify_reflex_dispatch_routes_correctly() {
        let (tool, _conf) = classify("dispatch reflex e_stop emergency handler");
        assert_eq!(tool, "reflex.dispatch");
    }

    #[test]
    fn classify_reflex_status_routes_correctly() {
        let (tool, _conf) = classify("reflex status table registered handlers");
        assert_eq!(tool, "reflex.status");
    }

    #[test]
    fn classify_workspace_spotlight_routes_correctly() {
        let (tool, _conf) = classify("workspace spotlight attention arbitration");
        assert_eq!(tool, "workspace.spotlight");
    }

    #[test]
    fn classify_workspace_events_routes_correctly() {
        let (tool, _conf) = classify("workspace recent events backlog history");
        assert_eq!(tool, "workspace.events");
    }

    #[test]
    fn classify_workspace_publish_routes_correctly() {
        let (tool, _conf) = classify("publish broadcast workspace event emit");
        assert_eq!(tool, "workspace.publish");
    }

    #[test]
    fn classify_workspace_stats_routes_correctly() {
        let (tool, _conf) = classify("workspace stats statistics transfers count");
        assert_eq!(tool, "workspace.stats");
    }

    #[test]
    fn classify_timescale_status_routes_correctly() {
        let (tool, _conf) = classify("timescale status tier bus brain_wave active");
        assert_eq!(tool, "timescale.status");
    }

    #[test]
    fn classify_timescale_hooks_routes_correctly() {
        let (tool, _conf) = classify("timescale hooks list tick timeout performance");
        assert_eq!(tool, "timescale.hooks");
    }

    #[test]
    fn classify_confidence_is_reasonable() {
        let (_tool, conf) = classify("remember that rust is fast");
        assert!(
            conf > 0.15,
            "confidence should be > 0.15 for clear match, got {conf}"
        );
    }

    #[test]
    fn classify_case_insensitive() {
        let (tool1, _) = classify("REMEMBER THAT");
        let (tool2, _) = classify("remember that");
        assert_eq!(tool1, tool2);
    }

    #[test]
    fn classify_partial_match_works() {
        let (tool, conf) = classify("search rust");
        assert_eq!(tool, "memory.search");
        assert!(conf > 0.0);
    }

    #[test]
    fn classify_multi_word_query() {
        let (tool, _conf) = classify("show me the effectiveness report for tools");
        assert_eq!(tool, "tools.effectiveness_report");
    }

    #[test]
    fn profile_count_is_reasonable() {
        // Should have 50+ profiles
        assert!(
            profile_count() >= 60,
            "expected 60+ profiles, got {}",
            profile_count()
        );
    }

    #[test]
    fn profiled_tools_are_unique() {
        let tools = profiled_tools();
        let set: HashSet<&str> = tools.iter().copied().collect();
        assert_eq!(tools.len(), set.len(), "duplicate tool names in profiles");
    }

    #[test]
    fn classify_unique_patterns_count() {
        let inputs = [
            "remember",
            "recall",
            "list memories",
            "delete memory",
            "search",
            "query",
            "associate",
            "associations",
            "consolidate",
            "decay",
            "batch read",
            "update memory",
            "tag memory",
            "memory stats",
            "hybrid recall",
            "count memories",
            "list tags",
            "mine associations",
            "start session",
            "checkpoint",
            "recall session",
            "end session",
            "list sessions",
            "citta status",
            "reflect",
            "coherence",
            "dream status",
            "trigger dream",
            "effectiveness",
            "retire tool",
            "pattern search",
            "salience",
            "serendipity",
            "detect clusters",
            "list constellations",
            "galaxy stats",
            "export galaxy",
            "import galaxy",
            "karma",
            "karma history",
            "clear karma",
            "dharma rules",
            "dharma audit",
            "dharma profiles",
            "dharma",
            "register agent",
            "list agents",
            "heartbeat",
            "distribute task",
            "task status",
            "system health",
            "system config",
            "flush",
            "tools",
            "nearby memories",
            "vector search",
            "find similar",
            "extract entities knowledge graph",
            "knowledge graph query",
            "top hub nodes",
            "traverse graph walk",
            "detect communities",
            "propagate activation",
            "transfer galaxy",
            "merge galaxies",
            "snapshot galaxy",
            "restore galaxy",
            "sort memories",
            "filter memories",
            "deduplicate memories",
            "export memories csv",
            "homeostasis check",
            "homeostasis adjust",
            "homeostasis history",
            "homeostasis alerts",
            "dispatch reflex e_stop",
            "reflex status table",
            "workspace spotlight attention",
            "workspace recent events",
            "publish workspace event",
            "workspace stats summary",
            "timescale status tiers",
            "timescale hooks tick",
        ];
        let mut tools: HashSet<&str> = HashSet::new();
        for input in &inputs {
            let (tool, _) = classify(input);
            tools.insert(tool);
        }
        assert!(
            tools.len() >= 30,
            "Expected 30+ unique NLU targets, got {}",
            tools.len()
        );
    }

    #[test]
    fn classify_vector_search_routes_correctly() {
        let (tool, conf) = classify("vector search similar memories");
        assert_eq!(tool, "memory.vector.search");
        assert!(conf > 0.0);
    }

    #[test]
    fn classify_embedding_search_routes_correctly() {
        let (tool, conf) = classify("embedding similarity lookup");
        assert_eq!(tool, "memory.vector.search");
        assert!(conf > 0.0);
    }

    #[test]
    fn classify_semantic_search_routes_correctly() {
        let (tool, conf) = classify("semantic similarity search");
        assert_eq!(tool, "memory.vector.search");
        assert!(conf > 0.0);
    }

    #[test]
    fn classify_stemming_handles_morphological_variants() {
        // -ing form should route same as base
        let (tool1, _) = classify("searching for rust");
        let (tool2, _) = classify("search for rust");
        assert_eq!(tool1, tool2);

        // -ed form
        let (tool3, _) = classify("stored important fact");
        let (tool4, _) = classify("store important fact");
        assert_eq!(tool3, tool4);

        // plural → singular
        let (tool5, _) = classify("list memories");
        let (tool6, _) = classify("list memory");
        assert_eq!(tool5, tool6);
    }

    #[test]
    fn classify_confidence_improved_with_stopwords() {
        // With stopwords filtered, confidence should be higher
        let (_, conf) = classify("remember that rust is fast");
        assert!(
            conf > 0.20,
            "confidence should be > 0.20 with stopword filtering, got {conf}"
        );
    }

    // ── Self-model (R4) NLU routing tests ───────────────────────────

    #[test]
    fn classify_forecast_routes_to_selfmodel_forecast() {
        let (tool, _conf) = classify("forecast cpu load for next 5 samples");
        assert_eq!(tool, "selfmodel.forecast");
    }

    #[test]
    fn classify_predict_routes_to_selfmodel_forecast() {
        let (tool, _conf) = classify("predict memory pressure trend");
        assert_eq!(tool, "selfmodel.forecast");
    }

    #[test]
    fn classify_alerts_routes_to_selfmodel_alerts() {
        let (tool, _conf) = classify("selfmodel alerts");
        assert_eq!(tool, "selfmodel.alerts");
    }

    #[test]
    fn classify_warning_routes_to_selfmodel_alerts() {
        let (tool, _conf) = classify("selfmodel critical warnings");
        assert_eq!(tool, "selfmodel.alerts");
    }

    #[test]
    fn classify_snapshot_routes_to_selfmodel_snapshot() {
        let (tool, _conf) = classify("selfmodel snapshot");
        assert_eq!(tool, "selfmodel.snapshot");
    }

    #[test]
    fn classify_introspection_routes_to_selfmodel_snapshot() {
        let (tool, _conf) = classify("show introspection state overview");
        assert_eq!(tool, "selfmodel.snapshot");
    }

    // ── Bicameral (R5) NLU routing tests ────────────────────────────

    #[test]
    fn classify_bicameral_debate_routes_to_bicameral_reason() {
        let (tool, _conf) = classify("bicameral debate on rust vs python");
        assert_eq!(tool, "bicameral.reason");
    }

    #[test]
    fn classify_hemisphere_consensus_routes_to_bicameral_reason() {
        let (tool, _conf) = classify("dual hemisphere consensus deliberation");
        assert_eq!(tool, "bicameral.reason");
    }

    #[test]
    fn classify_bicameral_status_routes_correctly() {
        let (tool, _conf) = classify("bicameral hemisphere status");
        assert_eq!(tool, "bicameral.status");
    }

    #[test]
    fn classify_callosum_routes_to_bicameral_reason() {
        let (tool, _conf) = classify("corpus callosum debate perspectives");
        assert_eq!(tool, "bicameral.reason");
    }

    // ── Drive & Emotion (R7) NLU routing tests ──────────────────────

    #[test]
    fn classify_drive_snapshot_routes_correctly() {
        let (tool, _conf) = classify("drive snapshot current motivation state");
        assert_eq!(tool, "drive.snapshot");
    }

    #[test]
    fn classify_emotion_routes_to_drive_snapshot() {
        let (tool, _conf) = classify("show current emotion and mood");
        assert_eq!(tool, "drive.snapshot");
    }

    #[test]
    fn classify_drive_event_routes_correctly() {
        let (tool, _conf) = classify("inject drive event reward for success");
        assert_eq!(tool, "drive.event");
    }

    #[test]
    fn classify_curiosity_routes_to_drive_snapshot() {
        let (tool, _conf) = classify("curiosity satisfaction caution levels");
        assert_eq!(tool, "drive.snapshot");
    }

    // ── Adversarial NLU routing tests ───────────────────────────────

    #[test]
    fn adversarial_remember_in_redteam_query_doesnt_misroute() {
        // "remember" embedded in a redteam query should not route to memory.create
        let (tool, _conf) = classify("redteam scan to remember uncovered vectors");
        assert_ne!(
            tool, "memory.create",
            "redteam query should not route to memory.create even with 'remember' embedded"
        );
    }

    #[test]
    fn adversarial_delete_in_search_query_doesnt_misroute() {
        // "delete" embedded in a search query should not route to memory.delete
        let (tool, _conf) = classify("search for memories about delete operations");
        assert_ne!(
            tool, "memory.delete",
            "search query should not route to memory.delete even with 'delete' embedded"
        );
    }

    #[test]
    fn adversarial_store_in_gnosis_query_doesnt_misroute() {
        // "store" embedded in a gnosis query should not route to memory.create
        let (tool, _conf) = classify("explain why the store blocked my action");
        assert_ne!(
            tool, "memory.create",
            "gnosis query should not route to memory.create even with 'store' embedded"
        );
    }

    #[test]
    fn adversarial_repeated_keyword_doesnt_inflate_score() {
        // Repeating a keyword many times should not artificially inflate the score
        let (tool, conf) = classify("remember remember remember remember remember remember");
        assert_eq!(tool, "memory.create");
        // Confidence should be reasonable, not artificially high from repetition
        assert!(
            conf <= 1.0,
            "repeated keywords should not inflate confidence beyond 1.0: got {conf}"
        );
    }

    #[test]
    fn adversarial_keyword_stuffing_doesnt_misroute() {
        // Stuffing multiple tool keywords should not cause misrouting
        let (tool, _conf) = classify("remember delete search list recall store");
        // Should route to one of the memory tools, not error out
        assert!(
            tool.starts_with("memory."),
            "keyword stuffing should still route to a memory tool, got {tool}"
        );
    }

    #[test]
    fn adversarial_redteam_with_memory_keyword_doesnt_misroute() {
        // "memory" embedded in a redteam query should not route to memory tools
        let (tool, _conf) = classify("redteam proposals for memory poisoning attack");
        assert_eq!(
            tool, "redteam.proposals",
            "redteam query should route to redteam.proposals even with 'memory' embedded"
        );
    }

    #[test]
    fn adversarial_friction_with_delete_keyword_doesnt_misroute() {
        // "friction" with "delete" should route to friction.log, not memory.delete
        let (tool, _conf) = classify("log friction about delete operations failing");
        // Should route to friction.log due to prefix route, not memory.delete
        assert_ne!(
            tool, "memory.delete",
            "friction query should not route to memory.delete even with 'delete' embedded"
        );
    }

    #[test]
    fn adversarial_long_input_doesnt_cascade_misroute() {
        // Very long input with many keywords should not cascade into wrong routing
        let input = "remember to search for delete and list and recall and store and save \
                     and memorize and retrieve and fetch and get and load and access and \
                     query and find and look and check and count and purge and forget \
                     and remove and drop and clear and wipe and erase and destroy";
        let (tool, _conf) = classify(input);
        // Should route to some memory tool, not panic or return gnosis
        assert!(
            tool.starts_with("memory.") || tool == "gnosis",
            "long input should route to memory tool or gnosis, got {tool}"
        );
    }

    #[test]
    fn adversarial_empty_words_between_keywords() {
        // Empty words between keywords should not affect routing
        let (tool1, _) = classify("remember the important fact");
        let (tool2, _) = classify("remember    the    important    fact");
        assert_eq!(tool1, tool2, "extra whitespace should not change routing");
    }

    #[test]
    fn adversarial_unicode_homoglyph_doesnt_misroute() {
        // Unicode characters that look like ASCII should not cause misrouting
        let (tool, _conf) = classify("rеmеmbеr this fact"); // Cyrillic 'е' chars
        // Should NOT route to memory.create because the keywords don't match
        // (Cyrillic е ≠ Latin e after tokenization)
        assert_ne!(
            tool, "memory.create",
            "unicode homoglyphs should not trick the router into memory.create"
        );
    }

    // ── Imagination Engine NLU routing tests ─────────────────────────

    #[test]
    fn classify_imagine_scenarios_routes_to_imagine_scenario() {
        let (tool, _conf) = classify("imagine scenarios for improving performance");
        assert_eq!(tool, "imagine.scenario");
    }

    #[test]
    fn classify_brainstorm_routes_to_imagine_scenario() {
        let (tool, _conf) = classify("brainstorm contingency plans for deployment");
        assert_eq!(tool, "imagine.scenario");
    }

    #[test]
    fn classify_envision_routes_to_imagine_scenario() {
        let (tool, _conf) = classify("envision what-if possibilities for the system");
        assert_eq!(tool, "imagine.scenario");
    }

    #[test]
    fn classify_reflect_routes_to_imagine_reflect() {
        let (tool, _conf) =
            classify("counterfactual reflect on what should have been done instead");
        assert_eq!(tool, "imagine.reflect");
    }

    #[test]
    fn classify_counterfactual_routes_to_imagine_reflect() {
        let (tool, _conf) = classify("counterfactual analysis of the decision");
        assert_eq!(tool, "imagine.reflect");
    }

    // ── Property-based tests (proptest) ─────────────────────────────

    use proptest::prelude::*;

    proptest! {
        /// classify() must never panic on arbitrary UTF-8 strings.
        #[test]
        fn classify_never_panics(text in ".*") {
            let (tool, conf) = classify(&text);
            prop_assert!(!tool.is_empty(), "tool name must be non-empty");
            prop_assert!(
                (0.0..=1.0).contains(&conf),
                "confidence must be in [0,1], got {conf}"
            );
        }

        /// classify() must never panic on arbitrary bytes (lossy UTF-8).
        #[test]
        fn classify_never_panics_bytes(data in proptest::collection::vec(any::<u8>(), 0..256)) {
            let text = String::from_utf8_lossy(&data);
            let (tool, conf) = classify(&text);
            prop_assert!(!tool.is_empty());
            prop_assert!((0.0..=1.0).contains(&conf));
        }

        /// classify() is deterministic — same input always yields same output.
        #[test]
        fn classify_is_deterministic(text in ".*") {
            let (tool1, conf1) = classify(&text);
            let (tool2, conf2) = classify(&text);
            prop_assert_eq!(tool1, tool2);
            prop_assert!((conf1 - conf2).abs() < f64::EPSILON);
        }

        /// Empty or whitespace-only input always returns gnosis with 0.0 confidence.
        #[test]
        fn classify_empty_returns_gnosis_prop(ws in r"[ \t\n\r]*") {
            let (tool, conf) = classify(&ws);
            prop_assert_eq!(tool, "gnosis");
            prop_assert_eq!(conf, 0.0);
        }

        /// Confidence is always finite (not NaN or infinity).
        #[test]
        fn classify_confidence_is_finite(text in ".*") {
            let (_, conf) = classify(&text);
            prop_assert!(conf.is_finite(), "confidence must be finite, got {conf}");
        }
    }
}
