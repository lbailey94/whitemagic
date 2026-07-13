#!/usr/bin/env python3
"""Namespace Migration Tool — Migrate legacy local databases to namespaced structure.

Phase 2 §11: Provides tooling to migrate existing local databases from the
pre-namespace layout (flat MEMORY_DIR) to the per-user namespace layout
(WM_ROOT/users/<user_id>/galaxies/<name>/).

Usage:
    python scripts/namespace_migration.py --dry-run          # Preview changes
    python scripts/namespace_migration.py --user local       # Migrate for user "local"
    python scripts/namespace_migration.py --user alice --backup  # Migrate with backup
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from datetime import datetime


def find_legacy_galaxies(memory_dir: Path) -> list[dict[str, Any]]:
    """Find legacy galaxy databases in the flat layout.

    Legacy layout: MEMORY_DIR/galaxies/<name>/whitemagic.db
    Namespace layout: WM_ROOT/users/<user_id>/galaxies/<name>/whitemagic.db
    """
    galaxies = []
    legacy_galaxies_dir = memory_dir / "galaxies"
    if not legacy_galaxies_dir.exists():
        return galaxies

    for galaxy_dir in legacy_galaxies_dir.iterdir():
        if not galaxy_dir.is_dir():
            continue
        db_path = galaxy_dir / "whitemagic.db"
        if db_path.exists():
            galaxies.append({
                "name": galaxy_dir.name,
                "legacy_path": str(db_path),
                "legacy_dir": str(galaxy_dir),
                "size_bytes": db_path.stat().st_size,
            })
    return galaxies


def find_legacy_hnsw(memory_dir: Path) -> list[dict[str, Any]]:
    """Find legacy HNSW index files in the flat layout."""
    files = []
    for pattern in ["hnsw_index.bin", "hnsw_ids.json", "hnsw_cold_index.bin", "hnsw_cold_ids.json"]:
        p = memory_dir / pattern
        if p.exists():
            files.append({
                "name": pattern,
                "legacy_path": str(p),
                "size_bytes": p.stat().st_size,
            })
    return files


def find_legacy_main_db(memory_dir: Path) -> dict[str, Any] | None:
    """Find the legacy main database."""
    db_path = memory_dir / "whitemagic.db"
    if db_path.exists():
        return {
            "legacy_path": str(db_path),
            "size_bytes": db_path.stat().st_size,
        }
    return None


def migrate(
    memory_dir: Path,
    user_id: str = "local",
    *,
    dry_run: bool = False,
    backup: bool = False,
) -> dict[str, Any]:
    """Migrate legacy databases to the namespaced layout.

    Args:
        memory_dir: The legacy MEMORY_DIR path.
        user_id: The user namespace to migrate into.
        dry_run: If True, only report what would be done.
        backup: If True, create a backup before migrating.

    Returns:
        Summary dict with migration details.
    """
    from whitemagic.core.user_profile import get_user_dir

    user_dir = get_user_dir(user_id)
    target_galaxies_dir = user_dir / "galaxies"

    report: dict[str, Any] = {
        "user_id": user_id,
        "dry_run": dry_run,
        "timestamp": datetime.now().isoformat(),
        "galaxies_migrated": 0,
        "hnsw_files_migrated": 0,
        "main_db_migrated": False,
        "backups_created": [],
        "errors": [],
        "details": [],
    }

    # ── Migrate galaxy databases ──
    galaxies = find_legacy_galaxies(memory_dir)
    for g in galaxies:
        name = g["name"]
        legacy_path = Path(g["legacy_path"])
        target_dir = target_galaxies_dir / name
        target_db = target_dir / "whitemagic.db"

        if target_db.exists():
            report["details"].append(f"SKIP galaxy '{name}' — already exists at {target_db}")
            continue

        if dry_run:
            report["details"].append(f"WOULD MIGRATE galaxy '{name}': {legacy_path} → {target_db}")
            report["galaxies_migrated"] += 1
            continue

        try:
            target_dir.mkdir(parents=True, exist_ok=True)
            if backup:
                backup_path = legacy_path.with_suffix(f".db.bak.{datetime.now().strftime('%Y%m%d%H%M%S')}")
                shutil.copy2(legacy_path, backup_path)
                report["backups_created"].append(str(backup_path))
            shutil.copy2(legacy_path, target_db)
            report["details"].append(f"MIGRATED galaxy '{name}': {legacy_path} → {target_db}")
            report["galaxies_migrated"] += 1
        except Exception as e:
            report["errors"].append(f"Failed to migrate galaxy '{name}': {e}")

    # ── Migrate HNSW index files ──
    hnsw_files = find_legacy_hnsw(memory_dir)
    for f in hnsw_files:
        name = f["name"]
        legacy_path = Path(f["legacy_path"])
        target_path = user_dir / name

        if target_path.exists():
            report["details"].append(f"SKIP HNSW '{name}' — already exists at {target_path}")
            continue

        if dry_run:
            report["details"].append(f"WOULD MIGRATE HNSW '{name}': {legacy_path} → {target_path}")
            report["hnsw_files_migrated"] += 1
            continue

        try:
            if backup:
                backup_path = legacy_path.with_name(f"{name}.bak.{datetime.now().strftime('%Y%m%d%H%M%S')}")
                shutil.copy2(legacy_path, backup_path)
                report["backups_created"].append(str(backup_path))
            shutil.copy2(legacy_path, target_path)
            report["details"].append(f"MIGRATED HNSW '{name}': {legacy_path} → {target_path}")
            report["hnsw_files_migrated"] += 1
        except Exception as e:
            report["errors"].append(f"Failed to migrate HNSW '{name}': {e}")

    # ── Migrate main database ──
    main_db = find_legacy_main_db(memory_dir)
    if main_db:
        legacy_path = Path(main_db["legacy_path"])
        target_path = user_dir / "whitemagic.db"

        if target_path.exists():
            report["details"].append(f"SKIP main DB — already exists at {target_path}")
        else:
            if dry_run:
                report["details"].append(f"WOULD MIGRATE main DB: {legacy_path} → {target_path}")
                report["main_db_migrated"] = True
            else:
                try:
                    if backup:
                        backup_path = legacy_path.with_suffix(f".db.bak.{datetime.now().strftime('%Y%m%d%H%M%S')}")
                        shutil.copy2(legacy_path, backup_path)
                        report["backups_created"].append(str(backup_path))
                    shutil.copy2(legacy_path, target_path)
                    report["details"].append(f"MIGRATED main DB: {legacy_path} → {target_path}")
                    report["main_db_migrated"] = True
                except Exception as e:
                    report["errors"].append(f"Failed to migrate main DB: {e}")

    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrate legacy databases to namespaced layout")
    parser.add_argument("--user", default="local", help="User ID to migrate for (default: local)")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without executing")
    parser.add_argument("--backup", action="store_true", help="Create backups before migrating")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    try:
        from whitemagic.config.paths import MEMORY_DIR
    except ImportError:
        print("Error: Cannot import whitemagic.config.paths. Run from the project root with venv activated.")
        return 1

    report = migrate(MEMORY_DIR, user_id=args.user, dry_run=args.dry_run, backup=args.backup)

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"\nNamespace Migration Report")
        print(f"=" * 60)
        print(f"User: {report['user_id']}")
        print(f"Dry run: {report['dry_run']}")
        print(f"Timestamp: {report['timestamp']}")
        print(f"\nGalaxies migrated: {report['galaxies_migrated']}")
        print(f"HNSW files migrated: {report['hnsw_files_migrated']}")
        print(f"Main DB migrated: {report['main_db_migrated']}")
        if report["backups_created"]:
            print(f"\nBackups created:")
            for b in report["backups_created"]:
                print(f"  - {b}")
        if report["errors"]:
            print(f"\nErrors:")
            for e in report["errors"]:
                print(f"  - {e}")
        print(f"\nDetails:")
        for d in report["details"]:
            print(f"  - {d}")

    return 0 if not report["errors"] else 1


if __name__ == "__main__":
    sys.exit(main())
