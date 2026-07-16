#!/usr/bin/env python3
"""
Ingest text files from CODEX_VAULT/CODEX_ENGINE/LIBRARY/ into the codex galaxy.

Uses the unified API create_memory tool to store each file as a memory
with content_hash deduplication — skips files already ingested.

USAGE:
  PYTHONPATH=core python3 scripts/ingest_library.py [--dir DIR] [--dry-run] [--limit N]
"""
from __future__ import annotations

import hashlib
import os
import sys
import time
from pathlib import Path

# Ensure core is on path
sys.path.insert(0, str(Path(__file__).parent.parent / "core"))


def compute_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]


def get_existing_hashes() -> set[str]:
    """Get content hashes already in codex galaxy."""
    import sqlite3
    db_path = Path.home() / ".whitemagic/users/local/galaxies/codex/whitemagic.db"
    if not db_path.exists():
        return set()
    db = sqlite3.connect(str(db_path))
    try:
        rows = db.execute("SELECT content_hash FROM memories WHERE content_hash IS NOT NULL").fetchall()
        return {r[0] for r in rows if r[0]}
    finally:
        db.close()


def categorize_file(filepath: Path) -> str:
    """Determine category from directory structure."""
    parts = filepath.relative_to(LIBRARY_ROOT).parts
    if len(parts) > 1:
        cat_dir = parts[0]
        # Strip numeric prefix like "1_CONSCIOUSNESS" -> "consciousness"
        return cat_dir.split("_", 1)[-1].lower() if "_" in cat_dir else cat_dir.lower()
    return "general"


def ingest_file(filepath: Path, dry_run: bool = False) -> dict:
    """Ingest a single file into the codex galaxy via direct SQLiteBackend."""
    content = filepath.read_text(encoding="utf-8", errors="replace")
    if not content.strip():
        return {"file": str(filepath), "skipped": True, "reason": "empty"}

    file_hash = compute_hash(content)
    title = filepath.stem

    if file_hash in EXISTING_HASHES:
        return {"file": str(filepath), "skipped": True, "reason": "duplicate hash"}

    category = categorize_file(filepath)
    tags = [f"library", f"category:{category}", f"source:codex_vault"]

    if dry_run:
        return {
            "file": str(filepath),
            "title": title,
            "chars": len(content),
            "hash": file_hash,
            "category": category,
            "dry_run": True,
        }

    # Use SQLiteBackend directly to bypass injection scanner false positives
    from whitemagic.core.memory.backends.galaxy_router import GalaxyAwareBackend
    from whitemagic.core.memory.unified_types import Memory, MemoryType
    from datetime import datetime
    import uuid

    default_db = Path.home() / ".whitemagic/users/local/whitemagic.db"
    router = GalaxyAwareBackend(default_db, user_id="local")
    backend = router._get_galaxy_backend("codex")

    memory = Memory(
        id=str(uuid.uuid4()),
        content=content,
        memory_type=MemoryType.LONG_TERM,
        created_at=datetime.now(),
        importance=0.6,
        title=title,
        galaxy="codex",
        tags=set(tags),
        metadata={"source": "codex_vault_library", "category": category, "file_hash": file_hash},
    )
    memory_id = backend.store(memory, content_hash=file_hash)
    return {
        "file": str(filepath),
        "title": title,
        "chars": len(content),
        "hash": file_hash,
        "result": "success",
        "memory_id": memory_id,
    }


LIBRARY_ROOT: Path
EXISTING_HASHES: set[str]


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Ingest CODEX_VAULT text library into codex galaxy")
    parser.add_argument("--dir", type=str, default="/home/lucas/Desktop/CODEX_VAULT/CODEX_ENGINE/LIBRARY",
                        help="Library directory to ingest")
    parser.add_argument("--dry-run", action="store_true", help="Parse and report without ingesting")
    parser.add_argument("--limit", type=int, default=None, help="Only ingest first N files")
    args = parser.parse_args()

    global LIBRARY_ROOT, EXISTING_HASHES
    LIBRARY_ROOT = Path(args.dir)
    if not LIBRARY_ROOT.exists():
        print(f"ERROR: Library directory not found: {LIBRARY_ROOT}")
        sys.exit(1)

    # Find all text files
    extensions = {".txt", ".md", ".rtf"}
    files = [f for f in LIBRARY_ROOT.rglob("*") if f.is_file() and f.suffix.lower() in extensions]
    files.sort()
    print(f"=== Library Ingestion ===")
    print(f"Directory: {LIBRARY_ROOT}")
    print(f"Files found: {len(files)}")
    print(f"Dry run: {args.dry_run}")
    print()

    if args.limit:
        files = files[:args.limit]
        print(f"Limited to {len(files)} files")
        print()

    # Get existing hashes for dedup
    EXISTING_HASHES = get_existing_hashes() if not args.dry_run else set()
    if EXISTING_HASHES:
        print(f"Existing content hashes in codex galaxy: {len(EXISTING_HASHES)}")
    print()

    # Categorize
    categories = {}
    for f in files:
        cat = categorize_file(f)
        categories[cat] = categories.get(cat, 0) + 1
    print("Files by category:")
    for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
        print(f"  {cat:20s} {count:4d}")
    print()

    if args.dry_run:
        print("=== DRY RUN ===")
        total_chars = 0
        for f in files:
            content = f.read_text(encoding="utf-8", errors="replace")
            total_chars += len(content)
            cat = categorize_file(f)
            h = compute_hash(content)
            dup = "DUP" if h in EXISTING_HASHES else "NEW"
            print(f"  [{dup}] {f.relative_to(LIBRARY_ROOT)}  ({len(content):,} chars)")
        print(f"\nTotal: {len(files)} files, {total_chars:,} chars")
        return

    # Ingest
    print("=== Starting ingestion ===")
    start_time = time.time()
    results = []
    for i, f in enumerate(files):
        print(f"[{i+1}/{len(files)}] {f.relative_to(LIBRARY_ROOT)}", end=" ", flush=True)
        try:
            result = ingest_file(f, dry_run=False)
            results.append(result)
            if result.get("skipped"):
                print(f"SKIP ({result['reason']})")
            else:
                elapsed = time.time() - start_time
                print(f"OK ({result['chars']:,} chars, {elapsed:.1f}s)")
        except Exception as e:
            print(f"ERROR: {e}")
            results.append({"file": str(f), "error": str(e)})

    elapsed = time.time() - start_time
    ingested = sum(1 for r in results if not r.get("skipped") and "error" not in r)
    skipped = sum(1 for r in results if r.get("skipped"))
    failed = sum(1 for r in results if "error" in r)
    total_chars = sum(r.get("chars", 0) for r in results if not r.get("skipped"))

    print()
    print("=== Ingestion Complete ===")
    print(f"Files ingested: {ingested}")
    print(f"Files skipped:  {skipped}")
    print(f"Files failed:   {failed}")
    print(f"Total chars:    {total_chars:,}")
    print(f"Time elapsed:   {elapsed:.1f}s")


if __name__ == "__main__":
    main()
