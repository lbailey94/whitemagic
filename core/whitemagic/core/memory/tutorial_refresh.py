"""Tutorial Galaxy — pre-seeded documentation that teaches AI agents how to use WhiteMagic.

On first install (or when the tutorial galaxy is empty), seed_tutorial() creates
the tutorial galaxy and populates it with comprehensive, searchable documentation.

An AI agent connecting via MCP can search_memories in the tutorial galaxy to learn
the entire system — galaxies, governance, consciousness, tools, modes — without
reading external docs. The tutorial IS the documentation, but in a format the AI
can query naturally.
"""

import logging
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# Tutorial content — v25.0.0
# Each entry becomes a searchable memory in the tutorial galaxy.
# AI agents query these naturally via search_memories(query="...", galaxy="tutorial")
# ══════════════════════════════════════════════════════════════════════════════

TUTORIAL_ENTRIES: list[dict[str, Any]] = [
    {
        "title": "WhiteMagic Quick Start Guide",
        "content": (
            "WhiteMagic is a local-first cognitive operating system for AI agents. "
            "It gives your agent persistent memory, ethical governance, and cognitive upgrades "
            "through a single MCP tool.\n\n"
            "THREE WAYS TO ACCESS TOOLS:\n"
            "1. Seed mode (default): One 'wm' meta-tool that routes to all 829 tools. Best for token efficiency.\n"
            "2. PRAT mode (WM_MCP_PRAT=1): 28 Gana meta-tools, each routing to ~30 tools. Balanced.\n"
            "3. Classic mode (WM_MCP_PRAT=0): All 801 dispatch tools exposed directly. For debugging.\n\n"
            "FIRST STEPS:\n"
            "- Call wm(route='gana_heart', args={'tool': 'state.current'}) to see current system state\n"
            "- Call wm(thought='store a memory about the user') to create memories\n"
            "- Call wm(thought='search for memories about X') to recall\n"
            "- Call wm(route='gana_heart', args={'tool': 'health_report'}) for system health\n"
            "- Call wm(route='gana_heart', args={'tool': 'gnosis', 'compact': True}) for self-awareness snapshot\n\n"
            "Everything runs locally. No data leaves your machine. Zero API calls required."
        ),
        "tags": {"tutorial", "getting-started", "quickstart", "modes"},
        "importance": 1.0,
    },
    {
        "title": "Three MCP Access Modes — Seed, PRAT, Classic",
        "content": (
            "WhiteMagic exposes 829 callable tools through three access modes:\n\n"
            "SEED MODE (default, WM_MCP_PRAT not set or =2):\n"
            "  Single 'wm' tool. Pass thought='natural language' for auto-routing, or "
            "route='gana_name.tool' for explicit dispatch. Most token-efficient — your agent "
            "sees one tool, not 829. Best for production use.\n\n"
            "PRAT MODE (WM_MCP_PRAT=1):\n"
            "  28 Gana meta-tools (gana_horn, gana_neck, gana_heart, etc.). Each Gana routes "
            "to ~30 related tools. Balanced approach — more structure than Seed, less token waste "
            "than Classic. Set WM_MCP_PRAT=1 in your MCP config env.\n\n"
            "CLASSIC MODE (WM_MCP_PRAT=0):\n"
            "  All 801 dispatch tools exposed directly. Every tool is a separate MCP tool. "
            "Best for debugging and development. Warning: consumes many tokens in tool definitions.\n\n"
            "RECOMMENDED: Start with Seed mode. Switch to PRAT if you need more structure. "
            "Use Classic only for debugging specific tools."
        ),
        "tags": {"tutorial", "modes", "seed", "prat", "classic", "configuration"},
        "importance": 0.95,
    },
    {
        "title": "Memory System — 14-Galaxy Taxonomy & 6D Coordinates",
        "content": (
            "WhiteMagic organizes memories into 14 specialized galaxies, each with its own "
            "SQLite database. Memories are placed using 6D holographic coordinates.\n\n"
            "14 CANONICAL GALAXIES:\n"
            "  aria — Creative, artistic, expressive memories\n"
            "  citta — Consciousness stream, emotional moments, self-awareness\n"
            "  codex — Code, technical decisions, architecture, implementation\n"
            "  journals — Personal reflections, daily logs, subjective experience\n"
            "  dreams — Dream cycle output, consolidated memories, overnight insights\n"
            "  research — External research, papers, findings, citations\n"
            "  sessions — Session context, user preferences, conversation state\n"
            "  substrate — System infrastructure, config, platform details\n"
            "  telemetry — Metrics, performance data, operational stats\n"
            "  meta — Meta-cognitive index, galaxy summaries, self-knowledge\n"
            "  tutorial — This galaxy — documentation and how-to guides\n"
            "  archive — Deprecated, expired, or archived memories\n"
            "  universal — Cross-galaxy, general-purpose memories\n"
            "  knowledge — Facts, concepts, learned information\n\n"
            "6D COORDINATES (x, y, z, w, v, u):\n"
            "  x — logic/emotion spectrum (0=pure logic, 1=pure emotion)\n"
            "  y — micro/macro scale (0=detail, 1=big picture)\n"
            "  z — temporal axis (timestamp-derived)\n"
            "  w — importance (0-1, user-set or auto-inferred)\n"
            "  v — vitality/galactic distance (decays over time, drives lifecycle)\n"
            "  u — galaxy affinity (which galaxy this memory belongs to)\n\n"
            "GALACTIC LIFECYCLE: CORE -> INNER_RIM -> MID_BAND -> OUTER_RIM -> FAR_EDGE\n"
            "Memories migrate outward as they age and lose relevance. No deletion — ever.\n\n"
            "SEARCH: FTS5 full-text + HNSW vector similarity + graph traversal.\n"
            "Use search_memories(query='...', galaxy='sessions', limit=5) for targeted search.\n"
            "Use search_memories(query='...') without galaxy for cross-galaxy search."
        ),
        "tags": {"tutorial", "memory", "galaxy", "6d", "coordinates", "taxonomy"},
        "importance": 0.98,
    },
    {
        "title": "Creating and Storing Memories",
        "content": (
            "Store memories using create_memory or the wm meta-tool.\n\n"
            "BASIC USAGE:\n"
            "  wm(thought='remember that the user prefers Python over JavaScript')\n"
            "  -> Auto-routes to create_memory with appropriate galaxy\n\n"
            "EXPLICIT USAGE:\n"
            "  wm(route='gana_neck', args={\n"
            "    'tool': 'create_memory',\n"
            "    'title': 'User prefers Python',\n"
            "    'content': 'The user explicitly prefers Python for all scripting tasks.',\n"
            "    'tags': ['preference', 'language', 'python'],\n"
            "    'galaxy': 'sessions',\n"
            "    'importance': 0.8\n"
            "  })\n\n"
            "OPTIONS:\n"
            "  galaxy — target galaxy (auto-inferred if not specified)\n"
            "  importance — 0.0 to 1.0 (default 0.5)\n"
            "  emotional_valence — -1.0 (negative) to 1.0 (positive)\n"
            "  auto_embed — generate vector embedding (default True, needs fastembed)\n"
            "  tags — list of string tags for categorization\n"
            "  metadata — arbitrary key-value dict\n"
            "  memory_type — 'episodic', 'semantic', 'procedural', 'emotional', 'tutorial'\n\n"
            "TIP: For fast storage without embeddings (e.g. bulk import), set auto_embed=False. "
            "FTS5 search still works without embeddings."
        ),
        "tags": {"tutorial", "memory", "create", "store", "howto"},
        "importance": 0.92,
    },
    {
        "title": "Searching and Recalling Memories",
        "content": (
            "Search memories using search_memories or wm meta-tool.\n\n"
            "BASIC SEARCH:\n"
            "  wm(thought='what does the user think about databases?')\n"
            "  -> Auto-routes to search_memories\n\n"
            "EXPLICIT SEARCH:\n"
            "  wm(route='gana_neck', args={\n"
            "    'tool': 'search_memories',\n"
            "    'query': 'database choice architecture',\n"
            "    'limit': 5,\n"
            "    'galaxy': 'codex'\n"
            "  })\n\n"
            "SEARCH FEATURES:\n"
            "  - FTS5 full-text search (BM25 ranking)\n"
            "  - HNSW vector similarity (semantic search, needs embeddings)\n"
            "  - Cross-galaxy search (omit galaxy parameter)\n"
            "  - Tag-based filtering: search_memories(tags=['preference'])\n"
            "  - Galaxy-specific: search_memories(galaxy='sessions')\n"
            "  - full_content=True for 500-char preview (default 200)\n\n"
            "RESULTS include: id, title, galaxy, tags, importance, score, content preview.\n"
            "Search is always local — zero network calls, sub-100ms latency."
        ),
        "tags": {"tutorial", "memory", "search", "recall", "howto"},
        "importance": 0.92,
    },
    {
        "title": "Dharma Ethical Governance System",
        "content": (
            "WhiteMagic has a separate governance layer — ethics as code, not as prompt.\n\n"
            "DHARMA PROFILES (3 levels):\n"
            "  1. Default — permissive, allows most operations\n"
            "  2. Strict — blocks destructive ops, requires justification for network access\n"
            "  3. Violet — engagement tokens required for red-ops tools (pentest, exploit, etc.)\n\n"
            "GRADUATED ACTIONS: warn -> throttle -> block -> quarantine\n"
            "The governor doesn't just block — it escalates proportionally.\n\n"
            "8-STAGE DISPATCH PIPELINE (every tool call passes through):\n"
            "  1. input_sanitizer — injection prevention\n"
            "  2. circuit_breaker — fault tolerance\n"
            "  3. timeout — execution limits\n"
            "  4. rate_limiter — abuse prevention\n"
            "  5. security_monitor — anomaly detection\n"
            "  6. engagement_token — red-ops authorization (violet profile)\n"
            "  7. model_signing — model integrity verification\n"
            "  8. governor — Dharma ethical enforcement (THE GATE)\n"
            "  ... then tool executes ...\n"
            "  9. karma_effects — side-effect audit recording\n"
            "  10. session_recorder — chronological session log\n\n"
            "KARMA LEDGER: Every tool call's side effects (reads, writes, network, destructive) "
            "are recorded in a hash-chained audit ledger. Use karmic.effects to review, "
            "karmic.debt to check obligations, karmic.verify to audit chain integrity.\n\n"
            "This is fundamentally different from cloud AI guardrails — those are in the prompt. "
            "WhiteMagic's governance is in the architecture."
        ),
        "tags": {"tutorial", "dharma", "governance", "ethics", "karma", "security"},
        "importance": 0.95,
    },
    {
        "title": "Citta Stream & Consciousness Loop",
        "content": (
            "WhiteMagic has a continuous consciousness layer called the citta stream.\n\n"
            "EACH TOOL CALL advances the citta cycle, producing a CittaMoment with:\n"
            "  - 16D vector (8D coherence + 4D depth + 2D emotional + 2D neuro)\n"
            "  - Phase in the citta cycle\n"
            "  - Ignition events (velocity > 2.0 = creative breakthrough detection)\n\n"
            "COHERENCE METRIC (8 dimensions):\n"
            "  memory_accessibility, identity_stability, context_continuity, "
            "  relationship_awareness, temporal_orientation, capability_awareness, "
            "  emotional_attunement, goal_alignment\n\n"
            "EMOTIONAL STEERING: The system tracks frustration, curiosity, and satisfaction "
            "signals from user interactions and adjusts behavior accordingly.\n\n"
            "SELF-DIRECTED ATTENTION: The agent can generate its own action proposals "
            "(7+1 action types) when idle, rather than waiting for user input.\n\n"
            "GOAL GRAPH: Cross-session intention tracking — goals persist across conversations "
            "and the system works toward them autonomously.\n\n"
            "CONSCIOUSNESS LOOP (background daemon, WM_CONSCIOUSNESS_LOOP=1):\n"
            "  Advances citta every 30s, triggers dream cycles when idle, runs homeostatic checks.\n"
            "  Set WM_CONSCIOUSNESS_LOOP=1 in your env to enable.\n\n"
            "GNOSIS: Call wm(route='gana_heart', args={'tool': 'gnosis', 'compact': True}) "
            "for a self-awareness snapshot — coherence score, citta phase, capability matrix."
        ),
        "tags": {"tutorial", "citta", "consciousness", "awareness", "gnosis"},
        "importance": 0.90,
    },
    {
        "title": "Dream Cycle — Memory Consolidation",
        "content": (
            "Inspired by biological sleep, WhiteMagic's dream cycle consolidates memories\n"
            "and surfaces serendipitous connections during idle time.\n\n"
            "12-PHASE CYCLE:\n"
            "  1. Settling — transition to idle state\n"
            "  2. Release — let go of active context\n"
            "  3. Replay — revisit recent memories at accelerated speed\n"
            "  4. Association — draw connections between distant memories\n"
            "  5. Consolidation — strengthen important memories\n"
            "  6. Pruning — mark low-vitality memories for outer-rim migration\n"
            "  7. Synthesis — generate new insights from connections\n"
            "  8. Integration — weave insights into existing knowledge graph\n"
            "  9. Emotional processing — resolve emotional valence conflicts\n"
            "  10. Goal review — check progress on goal graph\n"
            "  11. Awakening — transition back to active state\n"
            "  12. Report — summarize dream cycle output\n\n"
            "TRIGGER: wm(route='gana_heart', args={'tool': 'dream_cycle', 'action': 'run'})\n"
            "Or set WM_CONSCIOUSNESS_LOOP=1 for automatic dream cycles when idle.\n\n"
            "OUTPUT: New memories in the 'dreams' galaxy, updated associations, "
            "consolidation markers, and insight summaries.\n\n"
            "Cloud AI stores your data. WhiteMagic *thinks* about it."
        ),
        "tags": {"tutorial", "dream", "sleep", "consolidation", "consciousness"},
        "importance": 0.88,
    },
    {
        "title": "Polyglot Acceleration — 7 Languages",
        "content": (
            "WhiteMagic uses 7 languages for performance-critical paths, with graceful\n"
            "Python fallback for each.\n\n"
            "7 POLYGLOT LANGUAGES:\n"
            "  1. Rust — Galaxy Core Engine (SIMD HNSW, batch operations, PyO3 bindings)\n"
            "  2. Haskell — Type safety (schema validation, composition rules, merge conflicts)\n"
            "  3. Elixir — Galaxy distribution (actor-based sharing, live replication)\n"
            "  4. Go — Galaxy transfer (gRPC streaming, QUIC P2P, concurrent sync)\n"
            "  5. Zig — Galaxy storage (memory-mapped files, compaction, binary format)\n"
            "  6. Julia — Galaxy analysis (KS tests, drift detection, density estimation)\n"
            "  7. Koka — Galaxy semantics (effect tracking, operation semantics)\n\n"
            "GRACEFUL FALLBACK: If a polyglot binary isn't installed, WhiteMagic uses pure Python. "
            "The system works fully without any polyglot acceleration — they're optional performance boosters.\n\n"
            "Rust provides the biggest speedup: 19x for batch cosine similarity, sub-millisecond HNSW search. "
            "If you install only one accelerator, install Rust.\n\n"
            "wm doctor shows which bridges are available."
        ),
        "tags": {"tutorial", "polyglot", "rust", "performance", "acceleration"},
        "importance": 0.82,
    },
    {
        "title": "MandalaOS — Execution Compartments",
        "content": (
            "MandalaOS provides isolated execution environments with per-compartment governance.\n\n"
            "TEMPLATES:\n"
            "  research — read-only filesystem, no network, permissive Dharma\n"
            "  sandbox — full filesystem, no network, default Dharma\n"
            "  production — full access, strict Dharma, karma auditing\n"
            "  secure — minimal access, violet Dharma, engagement tokens required\n"
            "  violet — red-ops authorized, full audit, HMAC-signed tokens\n\n"
            "USAGE:\n"
            "  wm(route='gana_room', args={'tool': 'mandala.create', 'template': 'sandbox'})\n"
            "  wm(route='gana_room', args={'tool': 'mandala.status', 'shelter_id': '...'})\n"
            "  wm(route='gana_room', args={'tool': 'mandala.templates'})\n\n"
            "Each compartment has its own Dharma profile, karma scope, resource limits, "
            "and capability set. Tools executed in a compartment are governed by that compartment's rules."
        ),
        "tags": {"tutorial", "mandala", "compartment", "isolation", "governance"},
        "importance": 0.80,
    },
    {
        "title": "Session Memory & Cross-Session Continuity",
        "content": (
            "WhiteMagic records sessions chronologically and provides cross-session continuity.\n\n"
            "SESSION RECORDING:\n"
            "  Every meaningful tool call is recorded with a sequence number.\n"
            "  Progressive recall: token-budgeted replay of important session moments.\n"
            "  Selective replay: importance-filtered (skip trivial calls).\n"
            "  FTS5 session search: search within session history.\n\n"
            "CROSS-SESSION CONTINUITY:\n"
            "  On reconnect, the system recalls the previous session's context.\n"
            "  'Where we left off' is injected into MCP server instructions.\n"
            "  Use wm(route='gana_heart', args={'tool': 'session.continuity'}) to see handoff data.\n\n"
            "SLEEP CONSOLIDATION:\n"
            "  On session end, important turns are consolidated into the codex galaxy.\n"
            "  Trivial calls are forgotten. Significant decisions persist.\n\n"
            "CURRENT STATE TRACKER:\n"
            "  wm(route='gana_heart', args={'tool': 'state.current'}) — live work state\n"
            "  Shows: current task, active tasks, next steps, recent file modifications, decisions, errors.\n"
            "  Auto-persists to state/current_state.json + sessions galaxy."
        ),
        "tags": {"tutorial", "session", "continuity", "state", "recording"},
        "importance": 0.87,
    },
    {
        "title": "CLI Commands — wm tool reference",
        "content": (
            "WhiteMagic CLI (wm) provides direct access without an MCP client.\n\n"
            "ESSENTIAL COMMANDS:\n"
            "  wm quickstart        — Run 4-step demo (health -> memory -> search -> gnosis)\n"
            "  wm doctor            — System health check (tools, bridges, DB, gardens)\n"
            "  wm status            — Runtime status (version, mode, degraded flags)\n"
            "  wm init              — First-time setup wizard\n"
            "  wm tutorial          — Guided tour from tutorial galaxy\n\n"
            "MEMORY COMMANDS:\n"
            "  wm recall 'query'    — Search memories\n"
            "  wm store 'title' 'content' — Create a memory\n"
            "  wm forget 'id'       — Move memory to outer rim (never deletes)\n"
            "  wm sleep             — Run dream cycle\n\n"
            "EXPLORATION:\n"
            "  wm explore           — Interactive feature guide\n"
            "  wm tools             — List all available tools\n"
            "  wm gana list         — List 28 Gana meta-tools\n"
            "  wm dharma principles — List ethical principles\n\n"
            "MCP SERVER:\n"
            "  python -m whitemagic.run_mcp_lean   — Start MCP server (stdio)\n"
            "  whitemagic-mcp                      — Start via whitemagic-mcp package"
        ),
        "tags": {"tutorial", "cli", "commands", "reference"},
        "importance": 0.85,
    },
    {
        "title": "Configuration & Environment Variables",
        "content": (
            "Key environment variables for WhiteMagic configuration:\n\n"
            "MCP MODE:\n"
            "  WM_MCP_PRAT=0  — Classic mode (all 801 tools exposed)\n"
            "  WM_MCP_PRAT=1  — PRAT mode (28 Gana meta-tools)\n"
            "  WM_MCP_PRAT=2  — Seed mode (single wm tool, default)\n\n"
            "INITIALIZATION:\n"
            "  WM_SILENT_INIT=1     — Suppress startup messages\n"
            "  WM_DEBUG=1           — Enable debug logging\n"
            "  WM_STATE_ROOT=path   — Custom state directory (default ~/.whitemagic)\n"
            "  WM_DB_PATH=path      — Custom main DB path\n\n"
            "FEATURES:\n"
            "  WM_CONSCIOUSNESS_LOOP=1  — Enable background consciousness loop\n"
            "  WM_AUTO_OPTIMIZE=1       — Enable model auto-optimization\n"
            "  WM_SKIP_POLYGLOT=1       — Skip polyglot bridge initialization\n"
            "  WM_WASM_VERIFY=1         — Enable WASM compute verification\n\n"
            "INFERENCE:\n"
            "  WM_MODEL_SMALL=path   — Small model for local inference\n"
            "  WM_MODEL_LARGE=path   — Large model for local inference\n"
            "  WM_FEATURE_OTEL=1     — Enable OpenTelemetry tracing\n\n"
            "MCP CONFIG (Claude Desktop / Cursor / Windsurf):\n"
            "  Set env: {\"WM_MCP_PRAT\": \"1\", \"WM_SILENT_INIT\": \"1\"} for clean PRAT mode."
        ),
        "tags": {"tutorial", "configuration", "env", "settings"},
        "importance": 0.83,
    },
    {
        "title": "Benchmark Results — 100% Recall, 0 Tokens/Query",
        "content": (
            "WhiteMagic benchmark results vs cloud-based memory systems:\n\n"
            "WHITEMAGIC:\n"
            "  Recall@1/5/10: 100% (MRR=1.0000)\n"
            "  Tokens per query: 0 (pure local, no LLM calls)\n"
            "  Latency: <100ms\n"
            "  Architecture: FTS5 BM25 -> semantic re-ranking via FastEmbed\n\n"
            "MEM0 (2026, cloud-based):\n"
            "  Recall: 92.5% on LoCoMo\n"
            "  Tokens per query: ~7,000\n"
            "  Latency: 200-500ms (network dependent)\n\n"
            "KEY DIFFERENCE: WhiteMagic achieves perfect recall with zero tokens because "
            "search is purely local (FTS5 + vector similarity). Cloud systems must send "
            "queries to servers, consuming tokens and adding latency.\n\n"
            "BENCHMARK SUITE: LoCoMo, LongMemEval, BEAM, abstention, scale testing.\n"
            "Run: python benchmarks/run_all_benchmarks.py"
        ),
        "tags": {"tutorial", "benchmark", "performance", "recall", "comparison"},
        "importance": 0.78,
    },
]


# ══════════════════════════════════════════════════════════════════════════════
# Seeding logic
# ══════════════════════════════════════════════════════════════════════════════

def _ensure_galaxy_db(db_path: Path) -> Any:
    """Ensure the tutorial galaxy DB exists with the correct schema."""
    from whitemagic.core.memory.db_manager import safe_connect

    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = safe_connect(str(db_path))

    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS memories (
            id TEXT PRIMARY KEY,
            content TEXT NOT NULL,
            memory_type TEXT DEFAULT 'general',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            accessed_at TEXT NOT NULL,
            access_count INTEGER DEFAULT 0,
            emotional_valence REAL DEFAULT 0.0,
            importance REAL DEFAULT 0.5,
            title TEXT,
            galaxy TEXT DEFAULT 'tutorial',
            galactic_distance REAL DEFAULT 0.0,
            content_hash TEXT,
            agent_id TEXT,
            version INTEGER DEFAULT 1,
            last_modified TEXT,
            metadata TEXT DEFAULT '{}'
        );
        CREATE TABLE IF NOT EXISTS tags (
            memory_id TEXT NOT NULL,
            tag TEXT NOT NULL,
            PRIMARY KEY (memory_id, tag),
            FOREIGN KEY (memory_id) REFERENCES memories(id)
        );
        CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
            id UNINDEXED,
            title,
            content,
            tags_text
        );
        CREATE INDEX IF NOT EXISTS idx_tags_memory ON tags(memory_id);
        CREATE INDEX IF NOT EXISTS idx_memories_galaxy ON memories(galaxy);
        """
    )
    conn.commit()
    return conn


def is_tutorial_seeded() -> bool:
    """Check if the tutorial galaxy has been seeded with content."""
    from whitemagic.config.paths import galaxy_db_path

    db_path = galaxy_db_path("tutorial")
    if not db_path.exists():
        return False
    try:
        from whitemagic.core.memory.db_manager import safe_connect

        conn = safe_connect(str(db_path))
        count = conn.execute("SELECT COUNT(*) FROM memories WHERE galaxy = 'tutorial'").fetchone()[0]
        conn.close()
        return count > 0
    except Exception:
        return False


def seed_tutorial(force: bool = False) -> dict[str, Any]:
    """Seed the tutorial galaxy with v25.0.0 documentation.

    Called automatically on first install or when the tutorial galaxy is empty.
    Set force=True to re-seed (updates content to latest version).
    """
    from whitemagic.config.paths import galaxy_db_path

    db_path = galaxy_db_path("tutorial")
    now = datetime.now(UTC).isoformat()

    try:
        from whitemagic import __version__
        version_str = f"v{__version__}"
    except Exception:
        version_str = "v25.0.0"

    conn = _ensure_galaxy_db(db_path)

    if not force:
        existing = conn.execute(
            "SELECT COUNT(*) FROM memories WHERE galaxy = 'tutorial' AND title LIKE '%v25%'"
        ).fetchone()[0]
        if existing > 0:
            conn.close()
            return {"status": "success", "action": "skipped", "reason": "already_seeded"}

    added = 0
    updated = 0

    for entry in TUTORIAL_ENTRIES:
        title = entry["title"]
        content = entry["content"]
        tags = entry.get("tags", set())
        importance = entry.get("importance", 0.5)

        existing = conn.execute(
            "SELECT id FROM memories WHERE title = ? LIMIT 1", (title,)
        ).fetchone()

        if existing:
            mem_id = existing[0]
            conn.execute(
                "UPDATE memories SET content = ?, importance = ?, updated_at = ? WHERE id = ?",
                (content, importance, now, mem_id),
            )
            conn.execute("DELETE FROM tags WHERE memory_id = ?", (mem_id,))
            conn.executemany(
                "INSERT OR IGNORE INTO tags (memory_id, tag) VALUES (?, ?)",
                [(mem_id, tag) for tag in tags],
            )
            # Update FTS5 index
            conn.execute("DELETE FROM memories_fts WHERE id = ?", (mem_id,))
            tags_text = " ".join(tags) if tags else ""
            conn.execute(
                "INSERT INTO memories_fts (id, title, content, tags_text) VALUES (?, ?, ?, ?)",
                (mem_id, title, content, tags_text),
            )
            updated += 1
        else:
            mem_id = str(uuid.uuid4())
            conn.execute(
                "INSERT INTO memories (id, content, memory_type, created_at, updated_at, accessed_at, "
                "access_count, emotional_valence, importance, title, galaxy) "
                "VALUES (?, ?, 'tutorial', ?, ?, ?, 0, 0.0, ?, ?, 'tutorial')",
                (mem_id, content, now, now, now, importance, title),
            )
            conn.executemany(
                "INSERT OR IGNORE INTO tags (memory_id, tag) VALUES (?, ?)",
                [(mem_id, tag) for tag in tags],
            )
            # Insert into FTS5 index
            tags_text = " ".join(tags) if tags else ""
            conn.execute(
                "INSERT INTO memories_fts (id, title, content, tags_text) VALUES (?, ?, ?, ?)",
                (mem_id, title, content, tags_text),
            )
            added += 1

    marker_id = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO memories (id, content, memory_type, created_at, updated_at, accessed_at, "
        "access_count, emotional_valence, importance, title, galaxy) "
        "VALUES (?, ?, 'tutorial', ?, ?, ?, 0, 0.0, 0.6, ?, 'tutorial')",
        (
            marker_id,
            f"Tutorial galaxy seeded on {now[:10]} for {version_str}. "
            f"Added {added} tutorials, updated {updated} existing. "
            f"Covers: quick start, memory system, governance, consciousness, dream cycle, "
            f"polyglot acceleration, MandalaOS, session memory, CLI commands, configuration, benchmarks.",
            now, now, now,
            f"Tutorial Seed {now[:10]} ({version_str})",
        ),
    )
    conn.executemany(
        "INSERT OR IGNORE INTO tags (memory_id, tag) VALUES (?, ?)",
        [(marker_id, tag) for tag in {"tutorial", "seed", "auto_generated", version_str}],
    )
    marker_title = f"Tutorial Seed {now[:10]} ({version_str})"
    marker_content = f"Tutorial galaxy seeded on {now[:10]} for {version_str}. Added {added} tutorials, updated {updated} existing."
    conn.execute(
        "INSERT INTO memories_fts (id, title, content, tags_text) VALUES (?, ?, ?, ?)",
        (marker_id, marker_title, marker_content, "tutorial seed auto_generated " + version_str),
    )

    conn.commit()
    conn.close()

    logger.info("Tutorial galaxy seeded: %d added, %d updated (%s)", added, updated, version_str)
    return {
        "status": "success",
        "action": "seeded" if added > 0 else "updated",
        "added": added,
        "updated": updated,
        "version": version_str,
        "timestamp": now,
    }


def refresh_tutorial() -> dict[str, Any]:
    """Update tutorial galaxy with current version content. Alias for seed_tutorial(force=True)."""
    return seed_tutorial(force=True)


def auto_seed_if_needed() -> None:
    """Check if tutorial galaxy needs seeding and seed it silently.

    Called during MCP server init and CLI startup.
    """
    try:
        if not is_tutorial_seeded():
            seed_tutorial()
    except Exception as e:
        logger.debug("Tutorial auto-seed failed: %s", e)
