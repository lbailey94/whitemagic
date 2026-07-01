#!/usr/bin/env python3
"""WhiteMagic Dream Cycle Daemon
=================================

Background process that runs the dream consolidation pipeline:
1. Scans for low-confidence creative bridges
2. Generates dream YAML artifacts
3. Runs nightly consolidation (promote/expire dreams)
4. Updates dream status for the dashboard

Usage:
    python scripts/dream_cycle_daemon.py              # Run once
    python scripts/dream_cycle_daemon.py --daemon      # Run as daemon
    python scripts/dream_cycle_daemon.py --interval 3600  # Custom interval
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

os.environ["WM_SILENT_INIT"] = "1"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("dream_daemon")


def get_db_path() -> Path:
    from whitemagic.config.paths import DB_PATH

    return DB_PATH


def get_conn(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def get_dream_dir() -> Path:
    from whitemagic.config.paths import DREAMS_DIR

    DREAMS_DIR.mkdir(parents=True, exist_ok=True)
    return DREAMS_DIR


# Dream Generation


def generate_dream_artifacts(conn: sqlite3.Connection, limit: int = 50) -> list[dict]:
    """Generate dream artifacts from low-confidence memory associations."""
    # Find memories with low importance but high association count
    # These are "subconscious" connections worth dreaming about
    rows = conn.execute(
        """
        SELECT m.id, m.title, m.content, m.importance, m.galactic_distance,
               m.emotional_valence,
               (SELECT COUNT(*) FROM associations a
                WHERE a.source_id = CAST(m.id AS TEXT) OR a.target_id = CAST(m.id AS TEXT)) as assoc_count
        FROM memories m
        WHERE m.is_protected = 0
        ORDER BY assoc_count DESC, m.emotional_valence DESC
        LIMIT ?
    """,
        (limit,),
    ).fetchall()

    dreams = []
    dream_dir = get_dream_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    for row in rows:
        # Generate dream content based on memory properties
        dream_type = _classify_dream(row)
        dream_content = _generate_dream_content(row, dream_type)

        dream = {
            "dream_id": f"dream_{timestamp}_{row['id']}",
            "source_memory_id": str(row["id"]),
            "dream_type": dream_type,
            "emotional_tone": _emotional_tone(row["emotional_valence"]),
            "content": dream_content,
            "created_at": datetime.now().isoformat(),
            "revisit_count": 0,
            "promoted": False,
            "expires_at": _calculate_expiry(dream_type),
        }

        dreams.append(dream)

        dream_file = dream_dir / f"{dream['dream_id']}.json"
        dream_file.write_text(json.dumps(dream, indent=2))

    return dreams


def _classify_dream(row: sqlite3.Row) -> str:
    """Classify dream type based on memory properties."""
    importance = float(row["importance"] or 0.5)
    distance = float(row["galactic_distance"] or 0.5)
    emotion = float(row["emotional_valence"] or 0.0)
    assoc_count = int(row["assoc_count"] or 0)

    if emotion > 0.5 and assoc_count > 5:
        return "lucid"  # High emotion + many connections
    elif distance > 0.7 and importance < 0.2:
        return "fragment"  # Far edge, low importance
    elif assoc_count > 10:
        return "pattern"  # Many associations = pattern recognition
    elif emotion < -0.3:
        return "shadow"  # Negative emotion
    else:
        return "ephemeral"  # Default


def _generate_dream_content(row: sqlite3.Row, dream_type: str) -> str:
    """Generate dream narrative content."""
    title = str(row["title"] or "")[:100]
    emotion = float(row["emotional_valence"] or 0.0)

    narratives = {
        "lucid": f"Clear vision of '{title}' — emotional resonance {emotion:.2f}. Pattern emerging from subconscious connections.",
        "fragment": f"Faded echo of '{title}' at galactic distance {row['galactic_distance']:.2f}. Memory fragment seeking integration.",
        "pattern": f"Recurring pattern around '{title}' — {row['assoc_count']} associations suggest hidden structure.",
        "shadow": f"Shadow reflection of '{title}' — emotional valence {emotion:.2f}. Unprocessed material.",
        "ephemeral": f"Fleeting impression of '{title}' — surface-level resonance, may consolidate or fade.",
    }

    return narratives.get(dream_type, f"Dream fragment: '{title}'")


def _emotional_tone(valence: float) -> str:
    """Map emotional valence to tone."""
    v = float(valence or 0.0)
    if v > 0.5:
        return "euphoric"
    elif v > 0.2:
        return "positive"
    elif v > -0.2:
        return "neutral"
    elif v > -0.5:
        return "melancholic"
    else:
        return "disturbing"


def _calculate_expiry(dream_type: str) -> str:
    """Calculate when dream expires."""
    from datetime import timedelta

    expiry_map = {
        "lucid": timedelta(days=30),
        "pattern": timedelta(days=21),
        "shadow": timedelta(days=14),
        "ephemeral": timedelta(days=7),
        "fragment": timedelta(days=3),
    }

    expiry = datetime.now() + expiry_map.get(dream_type, timedelta(days=7))
    return expiry.isoformat()


# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------


def run_consolidation() -> dict:
    """Run nightly dream consolidation."""
    dream_dir = get_dream_dir()
    dream_files = list(dream_dir.glob("dream_*.json"))

    if not dream_files:
        return {"status": "no_dreams", "promoted": 0, "expired": 0}

    promoted = 0
    expired = 0
    now = datetime.now()

    for dream_file in dream_files:
        try:
            dream = json.loads(dream_file.read_text())
        except Exception:
            continue

        expires_at = datetime.fromisoformat(dream.get("expires_at", ""))
        if now > expires_at:
            # Expire: delete the dream file
            dream_file.unlink()
            expired += 1
            continue

        if dream.get("revisit_count", 0) >= 3 and not dream.get("promoted"):
            # Promote to memory
            _promote_dream(dream)
            dream["promoted"] = True
            dream_file.write_text(json.dumps(dream, indent=2))
            promoted += 1

    return {
        "status": "complete",
        "total_dreams": len(dream_files),
        "promoted": promoted,
        "expired": expired,
        "remaining": len(dream_files) - expired,
    }


def _promote_dream(dream: dict):
    """Promote a dream to actual memory."""
    conn = get_conn(get_db_path())

    # Update the source memory's importance
    source_id = dream.get("source_memory_id")
    if source_id:
        conn.execute(
            """
            UPDATE memories
            SET importance = MIN(1.0, importance + 0.1),
                recall_count = recall_count + 1
            WHERE id = ?
        """,
            (source_id,),
        )
        conn.commit()

    conn.close()
    log.info("Promoted dream %s to memory", dream["dream_id"])


# ---------------------------------------------------------------------------
# Dream Status
# ---------------------------------------------------------------------------


def get_dream_status() -> dict:
    """Get current dream cycle status."""
    dream_dir = get_dream_dir()
    dream_files = list(dream_dir.glob("dream_*.json"))

    now = datetime.now()
    active_dreams = 0
    by_type = {}

    for dream_file in dream_files:
        try:
            dream = json.loads(dream_file.read_text())
            expires_at = datetime.fromisoformat(dream.get("expires_at", ""))
            if now < expires_at:
                active_dreams += 1
                dream_type = dream.get("dream_type", "unknown")
                by_type[dream_type] = by_type.get(dream_type, 0) + 1
        except Exception:
            continue

    return {
        "running": True,
        "dreaming": active_dreams > 0,
        "current_phase": "consolidation" if active_dreams > 5 else "idle",
        "total_cycles": 1,
        "idle_seconds": 0,
        "active_dreams": active_dreams,
        "dreams_by_type": by_type,
        "recent_phases": [],
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def run_cycle() -> dict:
    """Run a single dream cycle."""
    log.info("═══ Dream Cycle Starting ═══")

    conn = get_conn(get_db_path())

    # Phase 1: Generate dream artifacts
    log.info("Phase 1: Generating dream artifacts...")
    dreams = generate_dream_artifacts(conn, limit=50)
    log.info(f"  Generated {len(dreams)} dream artifacts")

    # Phase 2: Run consolidation
    log.info("Phase 2: Running consolidation...")
    consolidation = run_consolidation()
    log.info(
        "  Promoted: %s, Expired: %s",
        consolidation["promoted"],
        consolidation["expired"],
    )

    conn.close()

    # Phase 3: Get status
    status = get_dream_status()

    log.info("═══ Dream Cycle Complete: %s active dreams ═══", status["active_dreams"])

    return {
        "dreams_generated": len(dreams),
        "consolidation": consolidation,
        "status": status,
    }


def main():
    parser = argparse.ArgumentParser(description="WhiteMagic Dream Cycle Daemon")
    parser.add_argument("--daemon", action="store_true", help="Run as daemon")
    parser.add_argument(
        "--interval", type=int, default=3600, help="Daemon interval (seconds)"
    )
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    args = parser.parse_args()

    if args.daemon or args.once:
        if args.once:
            result = run_cycle()
            print(json.dumps(result, indent=2))
        else:
            log.info("Starting dream daemon (interval: %ss)", args.interval)
            while True:
                try:
                    run_cycle()
                except Exception as e:
                    log.error("Dream cycle error: %s", e)
                time.sleep(args.interval)
    else:
        # Default: run once
        result = run_cycle()
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
