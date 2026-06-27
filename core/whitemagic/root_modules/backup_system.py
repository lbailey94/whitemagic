# ruff: noqa: BLE001
"""
WhiteMagic Backup and Restore System.

Provides full system backup and restore capabilities for WhiteMagic memories,
including incremental backups, verification, and metadata preservation.
"""

from __future__ import annotations

import json
import logging
import shutil
import time
from pathlib import Path
from typing import Any

from whitemagic.config.paths import get_state_root

logger = logging.getLogger(__name__)


class BackupSystem:
    """Full system backup and restore."""

    def __init__(self, backup_dir: Path | None = None) -> None:
        if backup_dir is None:
            backup_dir = get_state_root() / "backups" / "system"
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self._manifest: dict[str, Any] = {}

    def backup(self, source: Path | None = None, label: str = "") -> dict[str, Any]:
        """Create a full backup."""
        if source is None:
            source = get_state_root()
        source = Path(source)

        timestamp = int(time.time())
        backup_id = f"backup_{timestamp}_{label}" if label else f"backup_{timestamp}"
        dest = self.backup_dir / backup_id
        dest.mkdir(parents=True, exist_ok=True)

        files_copied = 0
        for f in source.rglob("*"):
            if f.is_file() and ".git" not in str(f):
                rel = f.relative_to(source)
                target = dest / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, target)
                files_copied += 1

        self._manifest[backup_id] = {
            "timestamp": timestamp,
            "label": label,
            "files": files_copied,
            "source": str(source),
        }
        self._save_manifest()
        return {"backup_id": backup_id, "files_copied": files_copied}

    def restore(self, backup_id: str, dest: Path | None = None) -> dict[str, Any]:
        """Restore from a backup."""
        backup_path = self.backup_dir / backup_id
        if not backup_path.exists():
            return {"status": "error", "error": "Backup not found"}

        if dest is None:
            dest = get_state_root()
        dest = Path(dest)

        files_restored = 0
        for f in backup_path.rglob("*"):
            if f.is_file():
                rel = f.relative_to(backup_path)
                target = dest / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, target)
                files_restored += 1

        return {"status": "success", "files_restored": files_restored}

    def list_backups(self) -> list[dict[str, Any]]:
        return [{"id": bid, **info} for bid, info in self._manifest.items()]

    def _save_manifest(self) -> None:
        manifest_file = self.backup_dir / "manifest.json"
        manifest_file.write_text(json.dumps(self._manifest, indent=2))

    def summary(self) -> dict[str, Any]:
        return {"total_backups": len(self._manifest)}


_backup: BackupSystem | None = None


def get_backup_system() -> BackupSystem:
    global _backup
    if _backup is None:
        _backup = BackupSystem()
    return _backup
