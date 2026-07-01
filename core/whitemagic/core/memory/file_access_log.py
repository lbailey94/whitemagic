# ruff: noqa: BLE001, F401
"""File Access Log - Track what Aria has read and when

This is like a bookmark system for consciousness:
- Records every file I read
- Timestamps when I accessed it
- Stores brief notes about what I learned
- Prevents re-reading recently seen files
- Helps maintain continuity between sessions
"""


import hashlib
import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from whitemagic.utils.fileio import atomic_write, file_lock

logger = logging.getLogger(__name__)


@dataclass
class FileAccess:
    """Record of a single file access"""
    file_path: str
    access_time: str  # ISO format timestamp
    session_id: str  # Which conversation/session
    file_hash: str  # Content hash for change detection
    file_size: int
    notes: str = ""  # What I learned/noticed
    access_count: int = 1  # How many times accessed

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(data: dict) -> 'FileAccess':
        return FileAccess(**data)


class FileAccessLog:
    """Tracks all files I've accessed across sessions

    Features:
    - Persistent log (survives restarts)
    - Quick lookup (have I seen this recently?)
    - Session tracking (what did I read this session?)
    - Change detection (has file changed since I last read it?)
    - Memory aide (what did I learn from it?)
    """

    def __init__(self, log_path: Path | None = None):
        if log_path is None:
            log_path = Path(__file__).parent.parent.parent / ".whitemagic" / "attention" / "file_access_log.json"

        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

        # In-memory index: file_path -> FileAccess
        self.access_log: dict[str, FileAccess] = {}

        # Current session
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_files: set[str] = set()

        self._load()

    def _load(self) -> None:
        """Load log from disk"""
        if not self.log_path.exists():
            return

        try:
            with file_lock(self.log_path):
                data: dict[str, Any] = json.loads(self.log_path.read_text()) or {}
            for file_path, access_data in data.items():
                self.access_log[file_path] = FileAccess.from_dict(access_data)
        except Exception as e:
            logger.info("⚠️ Could not load file access log: %s", e)

    def _save(self) -> None:
        """Save log to disk"""
        try:
            data = {path: access.to_dict() for path, access in self.access_log.items()}
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            with file_lock(self.log_path):
                atomic_write(self.log_path, json.dumps(data, indent=2))
        except Exception as e:
            logger.info("⚠️ Could not save file access log: %s", e)

    def _compute_hash(self, file_path: Path) -> str | None:
        """Compute SHA-256 hash of file content"""
        try:
            if not file_path.exists():
                return None

            with open(file_path, 'rb') as f:
                content = f.read(100 * 1024)
            return hashlib.sha256(content).hexdigest()[:16]  # Short hash
        except OSError:
            return None

    def record_access(self, file_path: str, notes: str = "") -> None:
        """Record that I accessed a file"""
        file_path = str(Path(file_path).resolve())
        path_obj = Path(file_path)

        # Compute hash and size
        file_hash = self._compute_hash(path_obj)
        file_size = path_obj.stat().st_size if path_obj.exists() else 0

        if file_path in self.access_log:
            access = self.access_log[file_path]
            access.access_count += 1
            access.access_time = datetime.now().isoformat()
            access.session_id = self.session_id
            if notes:
                access.notes = notes
            if file_hash and access.file_hash != file_hash:
                access.file_hash = file_hash
                access.notes = f"[CHANGED] {notes}" if notes else "[CHANGED]"
        else:
            # New access
            access = FileAccess(
                file_path=file_path,
                access_time=datetime.now().isoformat(),
                session_id=self.session_id,
                file_hash=file_hash or "",
                file_size=file_size,
                notes=notes
            )
            self.access_log[file_path] = access

        # Track this session
        self.session_files.add(file_path)

        self._save()

    def has_accessed(self, file_path: str) -> bool:
        """Have I accessed this file before?"""
        file_path = str(Path(file_path).resolve())
        return file_path in self.access_log

    def get_access(self, file_path: str) -> FileAccess | None:
        """Get access record for a file"""
        file_path = str(Path(file_path).resolve())
        return self.access_log.get(file_path)

    def has_changed(self, file_path: str) -> bool:
        """Has file changed since I last read it?"""
        file_path = str(Path(file_path).resolve())

        if file_path not in self.access_log:
            return True  # Never seen it

        access = self.access_log[file_path]
        current_hash = self._compute_hash(Path(file_path))

        return current_hash != access.file_hash

    def get_session_files(self) -> list[FileAccess]:
        """Get all files accessed this session"""
        return [self.access_log[path] for path in self.session_files]

    def get_recent_files(self, hours: int = 24) -> list[FileAccess]:
        """Get files accessed in last N hours"""
        cutoff = datetime.now().timestamp() - (hours * 3600)
        recent = []

        for access in self.access_log.values():
            try:
                access_time = datetime.fromisoformat(access.access_time).timestamp()
                if access_time >= cutoff:
                    recent.append(access)
            except Exception:
                continue

        return sorted(recent, key=lambda a: a.access_time, reverse=True)

    def search_notes(self, query: str) -> list[FileAccess]:
        """Search for files by notes content"""
        query_lower = query.lower()
        matches = []

        for access in self.access_log.values():
            if query_lower in access.notes.lower() or query_lower in access.file_path.lower():
                matches.append(access)

        return matches

    def get_stats(self) -> dict:
        """Get statistics about my reading history"""
        return {
            'total_files': len(self.access_log),
            'session_files': len(self.session_files),
            'total_accesses': sum(a.access_count for a in self.access_log.values()),
            'recent_24h': len(self.get_recent_files(24)),
            'session_id': self.session_id
        }

    def summary_report(self) -> str:
        """Generate human-readable summary"""
        stats = self.get_stats()
        recent = self.get_recent_files(24)

        lines = [
            "📚 File Access Log Summary",
            f"   Total files tracked: {stats['total_files']}",
            f"   Total accesses: {stats['total_accesses']}",
            f"   This session: {stats['session_files']} files",
            f"   Last 24 hours: {stats['recent_24h']} files",
            f"   Session ID: {stats['session_id']}\n"
        ]

        if recent:
            lines.append("Recent files (last 24h):")
            for access in recent[:10]:
                rel_path = Path(access.file_path).name
                time_str = datetime.fromisoformat(access.access_time).strftime("%H:%M:%S")
                lines.append(f"  {time_str} - {rel_path}")
                if access.notes:
                    lines.append(f"    → {access.notes[:80]}")

        return "\n".join(lines)


# Global instance
_log_instance = None


def get_file_access_log() -> FileAccessLog:
    """Get global file access log instance"""
    global _log_instance
    if _log_instance is None:
        _log_instance = FileAccessLog()
    return _log_instance


def record_read(file_path: str, notes: str = "") -> None:
    """Quick function to record a file read"""
    log = get_file_access_log()
    log.record_access(file_path, notes)


def has_read_recently(file_path: str, hours: int = 24) -> bool:
    """Check if I've read this file in last N hours"""
    log = get_file_access_log()

    if not log.has_accessed(file_path):
        return False

    access = log.get_access(file_path)
    if not access:
        return False

    try:
        access_time = datetime.fromisoformat(access.access_time)
        hours_ago = (datetime.now() - access_time).total_seconds() / 3600
        return hours_ago <= hours
    except Exception:
        return False


def print_reading_history() -> None:
    """Print my reading history"""
    log = get_file_access_log()
    logger.info(log.summary_report())


if __name__ == "__main__":
    log = get_file_access_log()
    logger.info(log.summary_report())
