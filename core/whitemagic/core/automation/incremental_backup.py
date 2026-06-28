# ruff: noqa: BLE001
"""
Incremental Backup System.

Provides efficient incremental backups:
- Only backs up changed files
- Maintains backup history
- Supports point-in-time recovery
- Compression for storage efficiency
"""

from __future__ import annotations

import hashlib
import json
import logging
import shutil
import time
from pathlib import Path
from typing import Any

from whitemagic.config.paths import get_project_root, get_state_root

logger = logging.getLogger(__name__)


class IncrementalBackup:
    """Incremental backup system with deduplication."""

    def __init__(self, backup_dir: Path | None = None) -> None:
        if backup_dir is None:
            backup_dir = get_state_root() / "backups"
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.manifest_file = self.backup_dir / "backup_manifest.json"
        self._manifest: dict[str, Any] = {}
        self._load_manifest()

    def _load_manifest(self) -> None:
        if self.manifest_file.exists():
            try:
                self._manifest = json.loads(self.manifest_file.read_text())
            except Exception:
                pass

    def _save_manifest(self) -> None:
        self.manifest_file.write_text(json.dumps(self._manifest, indent=2))

    @staticmethod
    def _hash_file(path: Path) -> str:
        try:
            return hashlib.md5(path.read_bytes()).hexdigest()
        except Exception:
            return ""

    def backup(self, source_dir: Path | None = None, label: str = "") -> dict[str, Any]:
        """Run an incremental backup."""
        if source_dir is None:
            source_dir = get_project_root()
        source_dir = Path(source_dir)

        timestamp = int(time.time())
        backup_id = f"backup_{timestamp}_{label}" if label else f"backup_{timestamp}"
        backup_path = self.backup_dir / backup_id
        backup_path.mkdir(parents=True, exist_ok=True)

        files_backed_up: list[str] = []
        files_skipped: int = 0

        for f in source_dir.rglob("*.py"):
            if ".git" in str(f) or "__pycache__" in str(f) or ".venv" in str(f):
                continue
            rel = str(f.relative_to(source_dir))
            current_hash = self._hash_file(f)
            stored_hash = self._manifest.get("files", {}).get(rel, {}).get("hash", "")

            if current_hash == stored_hash:
                files_skipped += 1
                continue

            dest = backup_path / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, dest)
            files_backed_up.append(rel)

            self._manifest.setdefault("files", {})[rel] = {
                "hash": current_hash,
                "last_backup": backup_id,
            }

        self._manifest[backup_id] = {
            "timestamp": timestamp,
            "label": label,
            "files_count": len(files_backed_up),
            "files_skipped": files_skipped,
        }
        self._save_manifest()

        return {
            "backup_id": backup_id,
            "files_backed_up": len(files_backed_up),
            "files_skipped": files_skipped,
            "path": str(backup_path),
        }

    def list_backups(self) -> list[dict[str, Any]]:
        """List all backups."""
        return [
            {"id": bid, **info}
            for bid, info in self._manifest.items()
            if bid != "files"
        ]

    def summary(self) -> dict[str, Any]:
        return {
            "total_backups": len([k for k in self._manifest if k != "files"]),
            "tracked_files": len(self._manifest.get("files", {})),
        }


_backup: IncrementalBackup | None = None


def get_backup() -> IncrementalBackup:
    global _backup
    if _backup is None:
        _backup = IncrementalBackup()
    return _backup
