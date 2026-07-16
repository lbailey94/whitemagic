"""Tutorial Galaxy Refresh — keeps tutorial content current with WhiteMagic version.

Called on version bumps or major feature additions to update the tutorial galaxy
with accurate, up-to-date content covering the latest capabilities.
"""

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


TUTORIAL_UPDATES = [
    {
        "title": "Multi-Galaxy Architecture (v24)",
        "content": (
            "WhiteMagic organizes memories into separate galaxies, each with its own "
            "SQLite database at ~/.whitemagic/users/local/galaxies/{name}/whitemagic.db. "
            "The canonical 10-galaxy taxonomy: sessions, meta, codex, archive, research, "
            "universal, knowledge, dreams, aria, citta. Additional galaxies: telemetry, "
            "tutorial, insight, creative_solutions, openai_archives. "
            "Each galaxy has independent memories, tags, associations, holographic coords, "
            "and FTS5 search. The GalaxyRouter routes new memories to the appropriate galaxy "
            "based on content, tags, and metadata. Use galaxy.create, galaxy.list, "
            "galaxy.switch, and galaxy.export to manage galaxies."
        ),
        "tags": {"tutorial", "galaxy", "architecture", "v24"},
        "importance": 0.95,
    },
    {
        "title": "MandalaOS Compartments & Dharma Profiles (v24.2)",
        "content": (
            "MandalaOS provides isolated execution compartments with per-compartment Dharma "
            "profiles. Templates: research, sandbox, production, secure, violet. Each template "
            "defines capabilities (fs_read, fs_write, network_read, network_write), resource "
            "limits (timeout, memory), and Dharma governance profile. The violet template "
            "enforces engagement tokens for red-ops tools. Karmic effect types (Pure, Local, "
            "Network, Destructive, Observation) are tracked for every tool call via the effect "
            "registry. Use mandala.create, mandala.status, mandala.templates to manage compartments."
        ),
        "tags": {"tutorial", "mandala", "dharma", "governance", "v24"},
        "importance": 0.92,
    },
    {
        "title": "Citta Stream & Consciousness Loop (v24)",
        "content": (
            "The citta stream is WhiteMagic's continuous consciousness layer. Each MCP tool "
            "call advances the citta cycle, producing a CittaMoment with a 16D vector "
            "(8D coherence + 4D depth + 2D emotional + 2D neuro). The CittaTrajectory tracks "
            "the vector sequence and detects ignition events (velocity > 2.0). The "
            "ConsciousnessLoop daemon runs in background (WM_CONSCIOUSNESS_LOOP=1) advancing "
            "citta every 30s, triggering dream cycles when idle, and running homeostatic checks. "
            "CoherenceMetric measures 8 dimensions: memory_accessibility, identity_stability, "
            "context_continuity, relationship_awareness, temporal_orientation, "
            "capability_awareness, emotional_attunement, goal_alignment."
        ),
        "tags": {"tutorial", "citta", "consciousness", "v24"},
        "importance": 0.90,
    },
    {
        "title": "GunaBalanceMetric & Biorhythmic Correction (v24)",
        "content": (
            "The GunaBalanceMetric tracks the sattvic/rajasic/tamasic ratio in the citta stream. "
            "Target biorhythm: 1:2:3 (sattvic:rajasic:tamasic) = ~17%:33%:50%. When deviation "
            "exceeds 12% tolerance, auto-correction triggers: dream cycles for tamasic deficit, "
            "self-directed attention for sattvic deficit, active processing for rajasic deficit. "
            "The ApotheosisEngine monitors 12 health metrics including inflammation index, "
            "antibody diversity, signal-to-noise ratio, setpoint deviation, and guna balance."
        ),
        "tags": {"tutorial", "guna", "biorhythm", "health", "v24"},
        "importance": 0.85,
    },
    {
        "title": "MetaGalaxy & Knowledge Gap Loop (v24)",
        "content": (
            "MetaGalaxy is the top-down meta-cognitive index of all galaxies. It auto-refreshes "
            "with 60s cache TTL, detecting empty galaxies, sparse galaxies, low importance, "
            "and temporal staleness. It generates strategic priorities from gap analysis. "
            "The KnowledgeGapActionLoop detects gaps (missing_memory, missing_code, "
            "missing_strategy, missing_knowledge) and routes to action: seed_memory_from_template, "
            "generate_code_from_vault, synthesize_strategy_from_meta_galaxy, search_and_ingest. "
            "The PossibilitySpaceExplorer runs Monte Carlo simulation for cognitive parameter "
            "optimization across 4 spaces: guna_balance, coherence, emergence_thresholds, "
            "health_setpoints."
        ),
        "tags": {"tutorial", "meta_galaxy", "knowledge_gap", "v24"},
        "importance": 0.82,
    },
    {
        "title": "Local Model Inference & Speculative Decoding (v24)",
        "content": (
            "WhiteMagic's 4-tier inference router: edge → local_small → local_large → cloud. "
            "The local backend uses llama.cpp (LlamaCppBackend) with env-var model selection "
            "(WM_MODEL_SMALL, WM_MODEL_LARGE). Speculative decoding uses a draft model "
            "(e.g. SmolLM2-360M) and verify model (e.g. Qwen3-4B) with token-level "
            "accept/reject. BitNet ternary (-1, 0, +1) models supported via BitMamba. "
            "ModelDiscovery auto-detects 13 model env vars with preferred order list. "
            "DualModelManager supports background/foreground model pairing."
        ),
        "tags": {"tutorial", "inference", "llama_cpp", "speculative", "v24"},
        "importance": 0.80,
    },
    {
        "title": "Engagement Tokens & Violet Profile (v24.3)",
        "content": (
            "The violet Dharma profile enforces engagement tokens for red-ops tools "
            "(red_*, pentest_*, exploit_*, fuzz_*, brute_*, nmap_*, recon_*, vuln_*, poc_*). "
            "Tokens use HMAC-SHA256 signing with 30s TTL, single-use nonces, and ROE-hash "
            "binding (SHA-256 of Dharma profile rules at issue time). The transaction firewall "
            "enforces per-agent spend limits, rate limiting, and recipient allowlist/blocklist. "
            "Model signing middleware blocks unsigned/tampered model loading under violet profile."
        ),
        "tags": {"tutorial", "security", "engagement_token", "violet", "v24"},
        "importance": 0.78,
    },
    {
        "title": "PWA & WASM Substrate (v23.2+)",
        "content": (
            "WhiteMagic provides a browser-first PWA with WASM compute substrate. "
            "Rust WASM bindings: MemoryStore (CRUD + search), DharmaEngine (4 safety rules), "
            "KarmaLedger (append-only tracking), GnosisSnapshot (self-awareness). "
            "TypeScript SDK LocalTransport routes tool calls to WASM module (zero network). "
            "Service worker with WASM cache-first strategy and offline fallback. "
            "Multi-user galaxy isolation with per-user SQLite namespaces and X-User-Id header."
        ),
        "tags": {"tutorial", "pwa", "wasm", "browser", "v24"},
        "importance": 0.75,
    },
]


def refresh_tutorial() -> dict[str, Any]:
    """Update tutorial galaxy with current v24.3.x content.
    
    Adds new tutorial memories for features added since v23 and updates
    existing tutorial memory content where outdated.
    """
    import uuid
    from pathlib import Path
    from whitemagic.core.memory.db_manager import safe_connect

    from whitemagic.config.paths import galaxy_db_path

    db_path = galaxy_db_path("tutorial")
    now = datetime.now(timezone.utc).isoformat()

    added = 0
    updated = 0
    skipped = 0

    conn = safe_connect(str(db_path))

    for entry in TUTORIAL_UPDATES:
        title = entry["title"]
        content = entry["content"]
        tags = entry["tags"]
        importance = entry["importance"]

        # Check if a memory with this title already exists
        existing = conn.execute(
            "SELECT id FROM memories WHERE title = ? LIMIT 1", (title,)
        ).fetchone()

        if existing:
            mem_id = existing[0]
            conn.execute(
                "UPDATE memories SET content = ?, importance = ?, updated_at = ? WHERE id = ?",
                (content, importance, now, mem_id),
            )
            # Update tags — delete old and insert new
            conn.execute("DELETE FROM tags WHERE memory_id = ?", (mem_id,))
            conn.executemany(
                "INSERT OR IGNORE INTO tags (memory_id, tag) VALUES (?, ?)",
                [(mem_id, tag) for tag in tags],
            )
            updated += 1
            logger.info("Updated tutorial: %s", title)
        else:
            mem_id = str(uuid.uuid4())
            conn.execute(
                "INSERT INTO memories (id, content, memory_type, created_at, updated_at, accessed_at, access_count, emotional_valence, importance, title, galaxy) VALUES (?, ?, 'tutorial', ?, ?, ?, 0, 0.0, ?, ?, 'tutorial')",
                (mem_id, content, now, now, now, importance, title),
            )
            conn.executemany(
                "INSERT OR IGNORE INTO tags (memory_id, tag) VALUES (?, ?)",
                [(mem_id, tag) for tag in tags],
            )
            added += 1
            logger.info("Added tutorial: %s", title)

    # Add a refresh marker memory
    try:
        from whitemagic.config import VERSION
        version_str = f"v{VERSION}"
    except Exception:
        version_str = "v24.3.x"

    marker_id = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO memories (id, content, memory_type, created_at, updated_at, accessed_at, access_count, emotional_valence, importance, title, galaxy) VALUES (?, ?, 'tutorial', ?, ?, ?, 0, 0.0, 0.6, ?, 'tutorial')",
        (
            marker_id,
            f"Tutorial galaxy refreshed on {now[:10]} for {version_str}. "
            f"Added {added} new tutorials, updated {updated} existing. "
            "Covers: multi-galaxy architecture, MandalaOS, citta stream, guna balance, "
            "MetaGalaxy, local model inference, engagement tokens, PWA/WASM substrate.",
            now, now, now,
            f"Tutorial Refresh {now[:10]} ({version_str})",
        ),
    )
    conn.executemany(
        "INSERT OR IGNORE INTO tags (memory_id, tag) VALUES (?, ?)",
        [(marker_id, tag) for tag in {"tutorial", "refresh", "auto_generated", version_str}],
    )

    conn.commit()
    conn.close()

    return {
        "status": "success",
        "added": added,
        "updated": updated,
        "skipped": skipped,
        "version": version_str,
        "timestamp": now,
    }
