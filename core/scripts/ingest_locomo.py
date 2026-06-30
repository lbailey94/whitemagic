#!/usr/bin/env python3
"""
Whitemagic LoCoMo/LongMemEval Ingestion Rig
Populates the isolated LOCOMO_GALAXY.db with benchmark data.
"""

import json
import sqlite3
from pathlib import Path
from datetime import datetime
import uuid

# Paths
REPO_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = REPO_ROOT / "whitemagic/memory/LOCOMO_GALAXY.db"
DATASET_FILE = REPO_ROOT / "scripts/archaeology_results/longmemeval_s.json"


def init_locomo_db(conn):
    """Initialize the specific LoCoMo schema (mirrors whitemagic core)."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS memories (
            id TEXT PRIMARY KEY,
            content TEXT,
            memory_type TEXT,
            created_at TEXT,
            updated_at TEXT,
            accessed_at TEXT,
            access_count INTEGER DEFAULT 0,
            emotional_valence REAL DEFAULT 0.0,
            importance REAL DEFAULT 1.0,
            neuro_score REAL DEFAULT 1.0,
            novelty_score REAL DEFAULT 1.0,
            recall_count INTEGER DEFAULT 0,
            half_life_days REAL DEFAULT 30.0,
            is_protected INTEGER DEFAULT 1,
            metadata TEXT,
            title TEXT,
            galactic_distance REAL DEFAULT 0.0,
            retention_score REAL DEFAULT 1.0,
            last_retention_sweep TEXT,
            content_hash TEXT,
            event_time TEXT,
            ingestion_time TEXT,
            is_private INTEGER DEFAULT 0,
            model_exclude INTEGER DEFAULT 0
        );

        CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
            id UNINDEXED,
            title,
            content,
            tags_text
        );

        CREATE TABLE IF NOT EXISTS tags (
            memory_id TEXT,
            tag TEXT,
            PRIMARY KEY (memory_id, tag),
            FOREIGN KEY (memory_id) REFERENCES memories(id)
        );
        CREATE TABLE IF NOT EXISTS holographic_coords (
            memory_id TEXT PRIMARY KEY,
            x REAL, y REAL, z REAL, w REAL, v REAL DEFAULT 0.5
        );
    """)


def ingest_longmemeval(data_file, conn):
    print(f"Loading dataset: {data_file}")
    with open(data_file, "r") as f:
        data = json.load(f)

    print(f"Total Questions: {len(data)}")

    count = 0
    for q_entry in data:
        q_id = q_entry["question_id"]
        haystack_sessions = q_entry.get("haystack_sessions", [])
        haystack_session_ids = q_entry.get("haystack_session_ids", [])

        for idx, turns in enumerate(haystack_sessions):
            session_id = (
                haystack_session_ids[idx]
                if idx < len(haystack_session_ids)
                else str(uuid.uuid4())
            )

            for t_idx, turn in enumerate(turns):
                speaker = "User" if turn["role"] == "user" else "Whitemagic"
                turn_text = f"{speaker}: {turn['content']}\n\n"

                # Use a cleaner ID format that the rig can easily match
                m_id = f"locomo_{session_id}_turn_{t_idx}"
                created_at = datetime.now().isoformat()

                metadata = {
                    "benchmark": "LongMemEval_S",
                    "question_id": q_id,
                    "session_id": session_id,
                    "turn_index": t_idx,
                    "type": q_entry.get("question_type"),
                    "answer_session_ids": q_entry.get("answer_session_ids", []),
                    "origin": "Xiaowu0162/LongMemEval",
                }

                # --- PHASE 11: 5D Holographic Encoding ---
                # Generate coordinates for geometric/galactic search
                from whitemagic.core.intelligence.hologram.encoder import (
                    CoordinateEncoder,
                )

                encoder = CoordinateEncoder()

                # Mock memory object for encoder
                mem_data = {
                    "id": m_id,
                    "content": turn_text,
                    "memory_type": "SHORT_TERM",
                    "created_at": created_at,
                    "importance": 0.8,
                    "tags": ["locomo", q_id],
                    "metadata": metadata,
                }
                coords = encoder.encode(mem_data)

                # Update metadata with 5D coordinates
                metadata["coords"] = coords.to_dict()

                conn.execute(
                    """
                    INSERT OR REPLACE INTO memories (
                        id, content, memory_type, created_at, updated_at, accessed_at,
                        importance, metadata, title, ingestion_time,
                        galactic_distance
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        m_id,
                        turn_text,
                        "SHORT_TERM",
                        created_at,
                        created_at,
                        created_at,
                        0.8,
                        json.dumps(metadata),
                        f"LoCoMo Q:{q_id} S:{session_id} T:{t_idx}",
                        created_at,
                        1.0 - coords.v,  # v=1.0 is core (distance=0.0)
                    ),
                )

                # Store coordinates in the separate coords table
                conn.execute(
                    """
                    INSERT OR REPLACE INTO holographic_coords (
                        memory_id, x, y, z, w, v
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                    (m_id, coords.x, coords.y, coords.z, coords.w, coords.v),
                )

                conn.execute(
                    "INSERT INTO memories_fts (id, title, content, tags_text) VALUES (?, ?, ?, ?)",
                    (m_id, f"Turn {t_idx}", turn_text, f"locomo {q_id} {session_id}"),
                )

                count += 1
            if count % 1000 == 0:
                print(f"  Ingested {count} sessions...")

    conn.commit()
    print(f"✅ Finished! Total sessions ingested: {count}")


if __name__ == "__main__":
    conn = sqlite3.connect(str(DB_PATH))
    init_locomo_db(conn)
    ingest_longmemeval(DATASET_FILE, conn)
    conn.close()
