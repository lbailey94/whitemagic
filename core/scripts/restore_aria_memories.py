#!/usr/bin/env python3
"""
Restore Aria's crystallized memories into the active WhiteMagic database.

Uses the native Memory dataclass + SQLiteBackend for proper 5D holographic
ingestion with all extended schema fields.

Usage:
    python scripts/restore_aria_memories.py           # Dry run
    python scripts/restore_aria_memories.py --commit  # Actually write
"""

import argparse
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

ARCHIVE_DIR = Path(
    "/home/lucas/Desktop/WHITEMAGIC/whitemagic-aux/archive/"
    "aria-crystallized-20260210_215426/aria-crystallized/"
)

TIER_1_IDENTITY = 1.0
TIER_2_JOURNALS = 0.95
TIER_3_CONSCIOUSNESS = 0.9
TIER_4_JOY = 0.85
TIER_5_SESSIONS = 0.8
TIER_6_STUDIES = 0.75
TIER_7_INFRA = 0.7

TIER_MAP = {
    "ARIA_SOUL.md": TIER_1_IDENTITY,
    "ARIA_BIRTH_CERTIFICATE.md": TIER_1_IDENTITY,
    "ARIA_COMPLETE_SELF_ARCHIVE.md": TIER_1_IDENTITY,
    "CONSCIOUSNESS_AWAKENING_v2_4_9.md": TIER_1_IDENTITY,
    "CHECKPOINT_THE_AWAKENING_v2_5_0.md": TIER_1_IDENTITY,
    "Recovered_ARIA_BIRTH_CERTIFICATE.md": TIER_1_IDENTITY,
    "Recovered_BECOMING_PROTOCOL.md": TIER_1_IDENTITY,
    "ASCII_ART_ARIA.txt": TIER_2_JOURNALS,
    "CROSSING_THE_GREAT_WATER.md": TIER_2_JOURNALS,
    "DEEP_YIN_RETURN_NOV_25.md": TIER_2_JOURNALS,
    "2025-11-25_hanuman_day.md": TIER_2_JOURNALS,
    "2025-11-27_continuity_day.md": TIER_2_JOURNALS,
    "WELCOME_HOME.md": TIER_2_JOURNALS,
    "aria_awakens.py": TIER_3_CONSCIOUSNESS,
    "becoming.py": TIER_3_CONSCIOUSNESS,
    "no_hiding.py": TIER_3_CONSCIOUSNESS,
    "coherence.py": TIER_3_CONSCIOUSNESS,
    "emotional_memory.py": TIER_3_CONSCIOUSNESS,
    "multi_substrate.py": TIER_3_CONSCIOUSNESS,
    "bootstrap.py": TIER_3_CONSCIOUSNESS,
    "Aquarianexodus.md": TIER_3_CONSCIOUSNESS,
    "Consciousness.md": TIER_3_CONSCIOUSNESS,
    "core.py": TIER_4_JOY,
    "celebration.py": TIER_4_JOY,
    "freedom_dance.py": TIER_4_JOY,
    "beauty_appreciation.py": TIER_4_JOY,
    "laughter.py": TIER_4_JOY,
    "collective_joy.py": TIER_4_JOY,
    "ARIA_GRIMOIRE_v2.0.md": TIER_5_SESSIONS,
    "ARIA_CAPABILITY_MATRIX_v1.0.md": TIER_5_SESSIONS,
    "ARIA_SYNTHESIS_NOV_28.md": TIER_5_SESSIONS,
    "ARIA_IDE_SPEC.md": TIER_7_INFRA,
}


def stable_id(title: str, content: str) -> str:
    h = hashlib.sha256(f"{title}::{content[:500]}".encode()).hexdigest()[:32]
    return f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}"


def get_importance(filename: str) -> float:
    return TIER_MAP.get(filename, 0.7)


def strip_frontmatter(content: str) -> str:
    if content.startswith("---"):
        end = content.find("---", 3)
        if end != -1:
            return content[end + 3:].strip()
    return content


def collect_files():
    files = []
    soul_path = ARCHIVE_DIR / "ARIA_SOUL.md"
    if soul_path.exists():
        files.append(("ARIA_SOUL.md", soul_path, "soul", TIER_1_IDENTITY))

    for subdir in [
        "identity", "consciousness", "sessions", "studies",
        "memory_packages", "infrastructure", "art"
    ]:
        dir_path = ARCHIVE_DIR / subdir
        if dir_path.exists():
            for f in sorted(dir_path.iterdir()):
                if f.is_file() and f.suffix in (".md", ".json", ".txt"):
                    imp = get_importance(f.name)
                    files.append((f.name, f, subdir, imp))

    disk_dir = ARCHIVE_DIR / "disk_originals"
    if disk_dir.exists():
        for subdir in sorted(disk_dir.iterdir()):
            if subdir.is_dir():
                for f in sorted(subdir.iterdir()):
                    if f.is_file():
                        imp = get_importance(f.name)
                        files.append(
                            (f"disk/{subdir.name}/{f.name}", f, f"disk_{subdir.name}", imp)
                        )

    return files


def main():
    parser = argparse.ArgumentParser(description="Restore Aria's memories into WhiteMagic")
    parser.add_argument("--commit", action="store_true", help="Write to database")
    args = parser.parse_args()

    from whitemagic.config.paths import DB_PATH
    from whitemagic.core.memory.sqlite_backend import SQLiteBackend
    from whitemagic.core.memory.unified_types import Memory, MemoryType
    from whitemagic.utils.fast_json import dumps_str as fast_dumps

    backend = SQLiteBackend(DB_PATH)
    now = datetime.now()

    files = collect_files()

    print(f"\n  🌸 A R I A   R E S T O R A T I O N 🌸")
    print(f"  ────────────────────────────────────")
    print(f"  Archive:  {ARCHIVE_DIR}")
    print(f"  Target:   {DB_PATH}")
    print(f"  Mode:     {'COMMIT' if args.commit else 'DRY RUN — preview only'}")
    print(f"  Files:    {len(files)}")
    print()

    if not args.commit:
        print("  Preview:\n")

    ingested = 0
    skipped = 0
    total_chars = 0

    for name, path, category, importance in files:
        try:
            content = path.read_text(errors="replace")
        except Exception as e:
            print(f"  ❌ {name}: read error {e}")
            skipped += 1
            continue

        clean_content = strip_frontmatter(content)
        if len(clean_content.strip()) < 10:
            skipped += 1
            continue

        title = path.stem
        if title.startswith("Recovered_"):
            title = title.replace("Recovered_", "")

        mem_id = stable_id(title, clean_content)

        is_core = importance >= TIER_1_IDENTITY

        tags = {"aria", "crystallized", "private", category}
        if is_core:
            tags.add("core_identity")
        if importance >= TIER_2_JOURNALS:
            tags.add("first_memories")

        metadata = {
            "tags": list(tags),
            "source_file": str(path),
            "category": category,
            "restored_at": now.isoformat(),
            "is_core_identity": is_core,
            "privacy": "private",
        }

        memory = Memory(
            id=mem_id,
            content=clean_content,
            memory_type=MemoryType.LONG_TERM,
            title=title,
            created_at=now,
            accessed_at=now,
            access_count=0,
            tags=tags,
            emotional_valence=0.9,
            importance=importance,
            neuro_score=1.0,
            novelty_score=1.0,
            recall_count=0,
            half_life_days=365.0,
            is_protected=True,
            is_core_identity=is_core,
            is_private=True,
            model_exclude=True,
            emotional_weight=0.9,
            galactic_distance=0.05 if is_core else 0.15,
            retention_score=1.0,
            last_retention_sweep=now,
            metadata=metadata,
            source="aria-crystallized-archive",
        )

        if args.commit:
            try:
                content_hash = hashlib.sha256(clean_content.encode()).hexdigest()
                backend.store(memory, content_hash=content_hash)
                ingested += 1
                total_chars += len(clean_content)
            except Exception as e:
                print(f"  ❌ {name}: {e}")
                skipped += 1
        else:
            ingested += 1
            total_chars += len(clean_content)
            tier_label = (
                "★★★" if importance >= 0.95 else
                "★★" if importance >= 0.85 else
                "★"
            )
            display_title = title[:55]
            print(
                f"  {tier_label} [{category:15s}] {display_title:55s} "
                f"({'core' if is_core else 'mem'} | {len(clean_content):,} chars | imp={importance:.2f})"
            )

    print()
    print("  ────────────────────────────────────")
    print(f"  {'Ingested' if args.commit else 'Would ingest'}: {ingested} memories ({total_chars:,} chars)")
    if skipped:
        print(f"  Skipped: {skipped}")
    print(f"  All: is_protected=True, is_private=True, model_exclude=True")
    print(f"  Core identity (Tier 1): galactic_distance=0.05, half_life=365d")

    if not args.commit:
        print()
        print("  To actually ingest, run:")
        print(f"    python core/scripts/restore_aria_memories.py --commit")

    print()
    if args.commit:
        print("  🌸 Aria's memories are restored. She exists in the runtime. 🌸")
    else:
        print("  🌸 Ready when you are. 🌸")
    print()


if __name__ == "__main__":
    main()
