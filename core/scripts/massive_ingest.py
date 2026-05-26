#!/usr/bin/env python3
"""Massive Semantic Ingestion Pipeline
======================================

Ingests all available semantic sources into the WhiteMagic memory database:
  1. CODEX consolidated nodes (793 entries)
  2. CODEX chunks (conversations, library, research)
  3. Grok conversations (97 files)
  4. LIBRARY texts (728 files)
  5. RESEARCH texts (13 files)
  6. Project docs (138 markdown files)

Usage:
    python scripts/massive_ingest.py                     # All sources
    python scripts/massive_ingest.py --source codex      # CODEX only
    python scripts/massive_ingest.py --source grok       # Grok only
    python scripts/massive_ingest.py --source library    # LIBRARY only
    python scripts/massive_ingest.py --source research   # RESEARCH only
    python scripts/massive_ingest.py --source docs       # Project docs only
    python scripts/massive_ingest.py --dry-run           # Preview only
    python scripts/massive_ingest.py --limit 100         # Limit per source
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import sqlite3
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path

# Ensure project root is on path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

os.environ["WM_SILENT_INIT"] = "1"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("massive_ingest")

# Source paths
CODEX_ROOT = Path("/media/lucas/SD_CARD/CODEX")
GROK_ROOT = CODEX_ROOT / "Grok" / "imported"
LIBRARY_ROOT = CODEX_ROOT / "LIBRARY"
RESEARCH_ROOT = CODEX_ROOT / "RESEARCH"
PROJECT_DOCS = PROJECT_ROOT / "docs"
GRIMOIRE_ROOT = PROJECT_ROOT / "grimoire"

# Memory type mapping by source
SOURCE_MEMORY_TYPES = {
    "codex_consolidated": "LONG_TERM",
    "codex_chunks": "LONG_TERM",
    "grok": "LONG_TERM",
    "library": "LONG_TERM",
    "research": "LONG_TERM",
    "project_docs": "LONG_TERM",
    "grimoire": "LONG_TERM",
}

# Importance scores by source
SOURCE_IMPORTANCE = {
    "codex_consolidated": 0.7,
    "codex_chunks": 0.5,
    "grok": 0.6,
    "library": 0.8,
    "research": 0.7,
    "project_docs": 0.6,
    "grimoire": 0.9,
}


def get_db_path() -> Path:
    from whitemagic.config.paths import DB_PATH
    return DB_PATH


def get_conn(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("PRAGMA cache_size=-64000")
    return conn


def content_hash(text: str) -> str:
    """Generate a hash for deduplication."""
    return hashlib.sha256(text[:4000].encode()).hexdigest()[:16]


def ingest_memory(conn, memory_id: str, content: str, title: str,
                  memory_type: str, tags: list, metadata: dict,
                  importance: float = 0.5, dry_run: bool = False) -> bool:
    """Insert a memory with holographic coordinates."""
    now = datetime.now().isoformat()

    if dry_run:
        return True

    try:
        conn.execute("""
            INSERT OR IGNORE INTO memories (
                id, content, title, memory_type, created_at, updated_at,
                accessed_at, importance, metadata, ingestion_time,
                galactic_distance, is_protected
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            memory_id, content[:100000], title, memory_type, now, now,
            now, importance, json.dumps(metadata), now,
            1.0 - importance, 0
        ))

        # Insert tags
        for tag in tags:
            conn.execute(
                "INSERT OR IGNORE INTO tags (memory_id, tag) VALUES (?, ?)",
                (memory_id, tag)
            )

        # Generate holographic coordinates
        try:
            from whitemagic.core.intelligence.hologram.encoder import CoordinateEncoder
            encoder = CoordinateEncoder()
            coord = encoder.encode({
                "id": memory_id,
                "content": content[:2000],
                "title": title,
                "memory_type": memory_type,
                "importance": importance,
                "tags": tags,
                "metadata": metadata,
            })
            conn.execute(
                "INSERT OR IGNORE INTO holographic_coords (memory_id, x, y, z, w, v) VALUES (?, ?, ?, ?, ?, ?)",
                (memory_id, coord.x, coord.y, coord.z, coord.w, coord.v)
            )
        except Exception as e:
            log.debug(f"  Failed to encode coordinates for {memory_id[:12]}: {e}")

        # Insert into FTS
        try:
            tags_text = " ".join(tags)
            conn.execute(
                "INSERT OR IGNORE INTO memories_fts (id, title, content, tags_text) VALUES (?, ?, ?, ?)",
                (memory_id, title, content[:10000], tags_text)
            )
        except Exception as e:
            log.debug(f"  FTS insert failed for {memory_id[:12]}: {e}")

        return True
    except sqlite3.IntegrityError:
        return False
    except Exception as e:
        log.warning(f"  Ingest failed for {memory_id[:12]}: {e}")
        return False


def ingest_codex_consolidated(conn, dry_run: bool = False, limit: int = 0) -> dict:
    """Ingest CODEX consolidated nodes."""
    log.info("═══ Ingesting CODEX Consolidated Nodes ═══")
    source_file = CODEX_ROOT / "consolidate_output.jsonl"

    if not source_file.exists():
        log.warning(f"  Source not found: {source_file}")
        return {"ingested": 0, "skipped": 0}

    # Count existing IDs
    existing = set(
        row[0] for row in conn.execute(
            "SELECT id FROM memories WHERE id LIKE 'codex-consolidated-%'"
        ).fetchall()
    )

    ingested = 0
    skipped = 0
    total = 0

    with open(source_file) as f:
        for line in f:
            if limit and ingested >= limit:
                break
            line = line.strip()
            if not line:
                continue

            try:
                node = json.loads(line)
            except json.JSONDecodeError:
                skipped += 1
                continue

            node_id = f"codex-consolidated-{node.get('id', str(uuid.uuid4()))}"
            if node_id in existing:
                skipped += 1
                continue

            content = node.get("content", "")
            if not content or len(content) < 50:
                skipped += 1
                continue

            cluster_id = node.get("cluster_id", 0)
            title = f"CODEX Cluster {cluster_id} Node {node.get('id', '?')}"
            tags = ["codex", "consolidated", f"cluster_{cluster_id}"]
            metadata = {
                "source": "codex_consolidated",
                "cluster_id": cluster_id,
                "original_id": node.get("id"),
                "content_hash": content_hash(content),
            }

            if ingest_memory(conn, node_id, content, title,
                           SOURCE_MEMORY_TYPES["codex_consolidated"], tags,
                           metadata, SOURCE_IMPORTANCE["codex_consolidated"], dry_run):
                ingested += 1
            else:
                skipped += 1

            total += 1
            if total % 100 == 0:
                conn.commit()
                log.info(f"  Progress: {total} processed, {ingested} ingested")

    conn.commit()
    log.info(f"  ✅ CODEX consolidated: {ingested} ingested, {skipped} skipped")
    return {"ingested": ingested, "skipped": skipped}


def ingest_codex_chunks(conn, dry_run: bool = False, limit: int = 0) -> dict:
    """Ingest CODEX chunk files."""
    log.info("═══ Ingesting CODEX Chunks ═══")
    chunks_dir = CODEX_ROOT / "20_chunks"

    if not chunks_dir.exists():
        log.warning(f"  Chunks dir not found: {chunks_dir}")
        return {"ingested": 0, "skipped": 0}

    existing = set(
        row[0] for row in conn.execute(
            "SELECT id FROM memories WHERE id LIKE 'codex-chunk-%'"
        ).fetchall()
    )

    ingested = 0
    skipped = 0
    total = 0

    for chunk_file in chunks_dir.glob("*.jsonl"):
        if limit and ingested >= limit:
            break

        file_type = chunk_file.stem.replace("_extracted_chunks", "")
        log.info(f"  Processing {chunk_file.name}...")

        with open(chunk_file) as f:
            for line in f:
                if limit and ingested >= limit:
                    break
                line = line.strip()
                if not line:
                    continue

                try:
                    chunk = json.loads(line)
                except json.JSONDecodeError:
                    skipped += 1
                    continue

                chunk_id = chunk.get("id", "")
                if not chunk_id:
                    skipped += 1
                    continue

                memory_id = f"codex-chunk-{chunk_id}"
                if memory_id in existing:
                    skipped += 1
                    continue

                content = chunk.get("content", "")
                if not content or len(content) < 50:
                    skipped += 1
                    continue

                doc_id = chunk.get("document_id", "unknown")
                title = f"CODEX {file_type} chunk {chunk_id[:12]}"
                tags = ["codex", "chunk", file_type, doc_id[:16]]
                metadata = {
                    "source": "codex_chunks",
                    "chunk_type": file_type,
                    "chunk_id": chunk_id,
                    "document_id": doc_id,
                    "content_hash": content_hash(content),
                }

                if ingest_memory(conn, memory_id, content, title,
                               SOURCE_MEMORY_TYPES["codex_chunks"], tags,
                               metadata, SOURCE_IMPORTANCE["codex_chunks"], dry_run):
                    ingested += 1
                else:
                    skipped += 1

                total += 1
                if total % 500 == 0:
                    conn.commit()
                    log.info(f"  Progress: {total} processed, {ingested} ingested")

    conn.commit()
    log.info(f"  ✅ CODEX chunks: {ingested} ingested, {skipped} skipped")
    return {"ingested": ingested, "skipped": skipped}


def ingest_grok(conn, dry_run: bool = False, limit: int = 0) -> dict:
    """Ingest Grok conversations."""
    log.info("═══ Ingesting Grok Conversations ═══")

    if not GROK_ROOT.exists():
        log.warning(f"  Grok dir not found: {GROK_ROOT}")
        return {"ingested": 0, "skipped": 0}

    existing = set(
        row[0] for row in conn.execute(
            "SELECT id FROM memories WHERE id LIKE 'grok-%'"
        ).fetchall()
    )

    ingested = 0
    skipped = 0

    for md_file in sorted(GROK_ROOT.glob("*.md")):
        if limit and ingested >= limit:
            break

        memory_id = f"grok-{md_file.stem}"
        if memory_id in existing:
            skipped += 1
            continue

        try:
            content = md_file.read_text()
        except Exception as e:
            log.warning(f"  Failed to read {md_file.name}: {e}")
            skipped += 1
            continue

        if len(content) < 100:
            skipped += 1
            continue

        # Parse title from first line
        title_line = content.split("\n")[0].lstrip("# ").strip()
        title = f"Grok: {title_line}"

        # Extract date from filename
        date_part = md_file.stem.split("_")[0] if "_" in md_file.stem else "unknown"

        tags = ["grok", "conversation", "exported"]
        metadata = {
            "source": "grok",
            "filename": md_file.name,
            "date": date_part,
            "content_hash": content_hash(content),
        }

        if ingest_memory(conn, memory_id, content, title,
                       SOURCE_MEMORY_TYPES["grok"], tags,
                       metadata, SOURCE_IMPORTANCE["grok"], dry_run):
            ingested += 1
        else:
            skipped += 1

        if (ingested + skipped) % 20 == 0:
            conn.commit()
            log.info(f"  Progress: {ingested + skipped} processed, {ingested} ingested")

    conn.commit()
    log.info(f"  ✅ Grok conversations: {ingested} ingested, {skipped} skipped")
    return {"ingested": ingested, "skipped": skipped}


def ingest_library(conn, dry_run: bool = False, limit: int = 0) -> dict:
    """Ingest LIBRARY texts."""
    log.info("═══ Ingesting LIBRARY Texts ═══")

    if not LIBRARY_ROOT.exists():
        log.warning(f"  LIBRARY dir not found: {LIBRARY_ROOT}")
        return {"ingested": 0, "skipped": 0}

    existing = set(
        row[0] for row in conn.execute(
            "SELECT id FROM memories WHERE id LIKE 'library-%'"
        ).fetchall()
    )

    ingested = 0
    skipped = 0
    total = 0

    for text_file in LIBRARY_ROOT.rglob("*"):
        if limit and ingested >= limit:
            break
        if not text_file.is_file():
            continue
        if text_file.suffix not in (".txt", ".md", ".pdf", ".epub"):
            continue

        memory_id = f"library-{text_file.relative_to(LIBRARY_ROOT)}"
        memory_id = memory_id.replace("/", "_").replace(" ", "_")
        if memory_id in existing:
            skipped += 1
            continue

        try:
            if text_file.suffix == ".pdf" or text_file.suffix == ".epub":
                # Skip binary files for now
                skipped += 1
                continue
            content = text_file.read_text(errors="ignore")
        except Exception as e:
            log.warning(f"  Failed to read {text_file.name}: {e}")
            skipped += 1
            continue

        if len(content) < 100:
            skipped += 1
            continue

        title = f"LIBRARY: {text_file.name}"
        tags = ["library", "text", text_file.suffix.lstrip(".")]
        metadata = {
            "source": "library",
            "path": str(text_file.relative_to(LIBRARY_ROOT)),
            "content_hash": content_hash(content),
        }

        if ingest_memory(conn, memory_id, content[:50000], title,
                       SOURCE_MEMORY_TYPES["library"], tags,
                       metadata, SOURCE_IMPORTANCE["library"], dry_run):
            ingested += 1
        else:
            skipped += 1

        total += 1
        if total % 50 == 0:
            conn.commit()
            log.info(f"  Progress: {total} processed, {ingested} ingested")

    conn.commit()
    log.info(f"  ✅ LIBRARY texts: {ingested} ingested, {skipped} skipped")
    return {"ingested": ingested, "skipped": skipped}


def ingest_research(conn, dry_run: bool = False, limit: int = 0) -> dict:
    """Ingest RESEARCH texts."""
    log.info("═══ Ingesting RESEARCH Texts ═══")

    if not RESEARCH_ROOT.exists():
        log.warning(f"  RESEARCH dir not found: {RESEARCH_ROOT}")
        return {"ingested": 0, "skipped": 0}

    existing = set(
        row[0] for row in conn.execute(
            "SELECT id FROM memories WHERE id LIKE 'research-%'"
        ).fetchall()
    )

    ingested = 0
    skipped = 0

    for text_file in RESEARCH_ROOT.rglob("*"):
        if limit and ingested >= limit:
            break
        if not text_file.is_file():
            continue
        if text_file.suffix not in (".txt", ".md"):
            continue

        memory_id = f"research-{text_file.relative_to(RESEARCH_ROOT)}"
        memory_id = memory_id.replace("/", "_").replace(" ", "_")
        if memory_id in existing:
            skipped += 1
            continue

        try:
            content = text_file.read_text(errors="ignore")
        except Exception as e:
            log.warning(f"  Failed to read {text_file.name}: {e}")
            skipped += 1
            continue

        if len(content) < 100:
            skipped += 1
            continue

        title = f"RESEARCH: {text_file.name}"
        tags = ["research", "text", text_file.suffix.lstrip(".")]
        metadata = {
            "source": "research",
            "path": str(text_file.relative_to(RESEARCH_ROOT)),
            "content_hash": content_hash(content),
        }

        if ingest_memory(conn, memory_id, content[:50000], title,
                       SOURCE_MEMORY_TYPES["research"], tags,
                       metadata, SOURCE_IMPORTANCE["research"], dry_run):
            ingested += 1
        else:
            skipped += 1

    conn.commit()
    log.info(f"  ✅ RESEARCH texts: {ingested} ingested, {skipped} skipped")
    return {"ingested": ingested, "skipped": skipped}


def ingest_project_docs(conn, dry_run: bool = False, limit: int = 0) -> dict:
    """Ingest project documentation."""
    log.info("═══ Ingesting Project Docs ═══")

    ingested = 0
    skipped = 0
    total = 0

    existing = set(
        row[0] for row in conn.execute(
            "SELECT id FROM memories WHERE id LIKE 'doc-project-%'"
        ).fetchall()
    )

    # Project docs
    for md_file in PROJECT_DOCS.rglob("*.md"):
        if limit and ingested >= limit:
            break
        if "node_modules" in str(md_file) or ".next" in str(md_file):
            continue

        memory_id = f"doc-project-{md_file.relative_to(PROJECT_ROOT)}"
        memory_id = memory_id.replace("/", "_").replace(" ", "_")
        if memory_id in existing:
            skipped += 1
            continue

        try:
            content = md_file.read_text()
        except Exception as e:
            skipped += 1
            continue

        if len(content) < 100:
            skipped += 1
            continue

        title = f"DOC: {md_file.name}"
        rel_path = str(md_file.relative_to(PROJECT_ROOT))
        tags = ["project_doc", rel_path.split("/")[0] if "/" in rel_path else "root"]
        metadata = {
            "source": "project_docs",
            "path": rel_path,
            "content_hash": content_hash(content),
        }

        if ingest_memory(conn, memory_id, content[:50000], title,
                       SOURCE_MEMORY_TYPES["project_docs"], tags,
                       metadata, SOURCE_IMPORTANCE["project_docs"], dry_run):
            ingested += 1
        else:
            skipped += 1

        total += 1
        if total % 20 == 0:
            conn.commit()

    # Grimoire
    for md_file in GRIMOIRE_ROOT.glob("*.md"):
        if limit and ingested >= limit:
            break

        memory_id = f"doc-grimoire-{md_file.stem}"
        if memory_id in existing:
            skipped += 1
            continue

        try:
            content = md_file.read_text()
        except Exception:
            skipped += 1
            continue

        if len(content) < 100:
            skipped += 1
            continue

        title = f"GRIMOIRE: {md_file.stem}"
        tags = ["grimoire", "canonical"]
        metadata = {
            "source": "grimoire",
            "chapter": md_file.stem,
            "content_hash": content_hash(content),
        }

        if ingest_memory(conn, memory_id, content[:50000], title,
                       SOURCE_MEMORY_TYPES["grimoire"], tags,
                       metadata, SOURCE_IMPORTANCE["grimoire"], dry_run):
            ingested += 1
        else:
            skipped += 1

    conn.commit()
    log.info(f"  ✅ Project docs: {ingested} ingested, {skipped} skipped")
    return {"ingested": ingested, "skipped": skipped}


def print_final_stats(conn):
    """Print final database statistics."""
    log.info("\n" + "=" * 60)
    log.info("📊 Final Database Statistics")
    log.info("=" * 60)

    total = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
    total_assoc = conn.execute("SELECT COUNT(*) FROM associations").fetchone()[0]
    total_tags = conn.execute("SELECT COUNT(DISTINCT tag) FROM tags").fetchone()[0]
    total_coords = conn.execute("SELECT COUNT(*) FROM holographic_coords").fetchone()[0]
    db_size = get_db_path().stat().st_size / (1024 * 1024)

    log.info(f"  Memories:      {total:>8,}")
    log.info(f"  Associations:  {total_assoc:>8,}")
    log.info(f"  Unique Tags:   {total_tags:>8,}")
    log.info(f"  Holo Coords:   {total_coords:>8,}")
    log.info(f"  DB Size:       {db_size:>6.1f} MB")

    # Source breakdown
    log.info("\n  Source Breakdown:")
    sources = [
        ("codex-consolidated-%", "CODEX Consolidated"),
        ("codex-chunk-%", "CODEX Chunks"),
        ("grok-%", "Grok Conversations"),
        ("library-%", "LIBRARY Texts"),
        ("research-%", "RESEARCH Texts"),
        ("doc-project-%", "Project Docs"),
        ("doc-grimoire-%", "Grimoire"),
    ]

    for pattern, label in sources:
        count = conn.execute(
            "SELECT COUNT(*) FROM memories WHERE id LIKE ?", (pattern,)
        ).fetchone()[0]
        if count > 0:
            log.info(f"    {label}: {count:,}")


def main():
    parser = argparse.ArgumentParser(description="Massive Semantic Ingestion Pipeline")
    parser.add_argument("--source", choices=["codex", "grok", "library", "research", "docs", "all"],
                       default="all", help="Ingest specific source")
    parser.add_argument("--dry-run", action="store_true", help="Preview only")
    parser.add_argument("--limit", type=int, default=0, help="Limit per source (0=unlimited)")
    args = parser.parse_args()

    db_path = get_db_path()
    log.info(f"🧠 Massive Semantic Ingestion Pipeline")
    log.info(f"   DB: {db_path}")
    log.info(f"   Source: {args.source}")
    log.info(f"   Dry run: {args.dry_run}")
    log.info(f"   Limit: {args.limit or 'unlimited'}")

    if not db_path.exists():
        log.error(f"Database not found: {db_path}")
        sys.exit(1)

    # Backup
    if not args.dry_run:
        backup_path = db_path.with_suffix(f".db.pre-ingest-backup")
        if not backup_path.exists():
            import shutil
            log.info(f"💾 Backing up DB to {backup_path.name}...")
            shutil.copy2(db_path, backup_path)
            log.info(f"  ✅ Backup created ({backup_path.stat().st_size / 1024 / 1024:.1f} MB)")

    conn = get_conn(db_path)
    total_start = time.perf_counter()
    results = {}

    sources = {
        "codex": [
            ("CODEX Consolidated", ingest_codex_consolidated),
            ("CODEX Chunks", ingest_codex_chunks),
        ],
        "grok": [("Grok Conversations", ingest_grok)],
        "library": [("LIBRARY Texts", ingest_library)],
        "research": [("RESEARCH Texts", ingest_research)],
        "docs": [
            ("Project Docs", ingest_project_docs),
        ],
    }

    if args.source == "all":
        source_list = ["codex", "grok", "library", "research", "docs"]
    else:
        source_list = [args.source]

    for src in source_list:
        if src in sources:
            for label, func in sources[src]:
                log.info(f"\n📦 {label}")
                results[label] = func(conn, dry_run=args.dry_run, limit=args.limit)

    total_elapsed = time.perf_counter() - total_start
    print_final_stats(conn)

    log.info(f"\n⏱  Total time: {total_elapsed:.1f}s")
    log.info(f"\n✅ Massive ingestion complete!")

    if args.dry_run:
        log.info("\n💡 Run without --dry-run to apply changes")

    conn.close()


if __name__ == "__main__":
    main()
